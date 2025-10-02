"""Instrument Entity Resolution
--------------------------------

Implements multi-stage blocking and scoring for ticker reference resolution:
  1. Regex detection for known ticker patterns
  2. Source hint filtering
  3. Prefix matching on ticker_norm
  4. Fuzzy scoring on ticker + name + aliases
  5. Material crosswalk boost

API:
  resolve_instrument(text, df, source_hint=None, threshold=92) -> Series | None
  topk_matches(text, df, k=5) -> list[(Series, score)]
"""

from __future__ import annotations
import re
from typing import Optional
import pandas as pd

try:
    from rapidfuzz import process, fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e

from entityidentity.utils.normalize import normalize_name


# ---- Ticker Pattern Regexes ----
TICKER_PATTERNS = {
    "Fastmarkets": re.compile(r"^MB-[A-Z0-9]+-\d+$", re.IGNORECASE),
    "LME": re.compile(r"^LME[_-][A-Z]{2,3}[_-]\w+$", re.IGNORECASE),
    "CME": re.compile(r"^[A-Z]{1,3}\d*$"),  # HG, SI, GC, etc.
    "Bloomberg": re.compile(r"^[A-Z]{2,6}(Y|[0-9])?$"),  # LMCADY, etc.
    "Argus": re.compile(r"^PA\d{7}$", re.IGNORECASE),  # PA0026990
}


def normalize_ticker(s: str) -> str:
    """Normalize ticker for matching.

    Args:
        s: Raw ticker string

    Returns:
        Normalized ticker (lowercase, alphanumeric + hyphens/underscores)

    Examples:
        >>> normalize_ticker("MB-CO-0005")
        'mb-co-0005'

        >>> normalize_ticker("LME_AL_CASH")
        'lme_al_cash'
    """
    return normalize_name(s, allowed_chars=r"a-z0-9\-_")


def normalize_instrument_name(s: str) -> str:
    """Normalize instrument name for matching.

    Args:
        s: Raw instrument name

    Returns:
        Normalized name (lowercase, alphanumeric + spaces/hyphens/parens/percent)

    Examples:
        >>> normalize_instrument_name("Cobalt standard grade in-whs Rotterdam")
        'cobalt standard grade in-whs rotterdam'

        >>> normalize_instrument_name("APT 88.5% WO3 min")
        'apt 88 5 wo3 min'
    """
    return normalize_name(s, allowed_chars=r"a-z0-9\s\-/()%")


# ---- Helper: Detect ticker pattern ----
def _detect_ticker_pattern(text: str) -> Optional[str]:
    """Detect if text matches a known ticker pattern.

    Args:
        text: Input text to check

    Returns:
        Source name if pattern matches, None otherwise

    Examples:
        >>> _detect_ticker_pattern("MB-CO-0005")
        'Fastmarkets'

        >>> _detect_ticker_pattern("LME_AL_CASH")
        'LME'

        >>> _detect_ticker_pattern("some random text")
        None
    """
    text_clean = text.strip()
    for source, pattern in TICKER_PATTERNS.items():
        if pattern.match(text_clean):
            return source
    return None


# ---- Helper: Build candidate pool ----
def _build_candidate_pool(
    df: pd.DataFrame,
    query_norm: str,
    source_hint: Optional[str] = None,
    ticker_pattern_source: Optional[str] = None,
) -> pd.DataFrame:
    """Apply blocking strategy to filter candidate instruments.

    Blocking sequence:
      1. If ticker pattern detected, filter to that source
      2. If source_hint provided, filter/prioritize that source
      3. Prefix match on ticker_norm (first 3 chars)
      4. If still too many, prefix match on name_norm

    Args:
        df: Full instruments DataFrame
        query_norm: Normalized query string
        source_hint: Optional source to filter/boost
        ticker_pattern_source: Detected source from ticker pattern

    Returns:
        Filtered DataFrame of candidate instruments
    """
    candidates = df.copy()

    # Step 1: Filter by detected ticker pattern source
    if ticker_pattern_source and "Source" in candidates.columns:
        mask = candidates["Source"].str.lower() == ticker_pattern_source.lower()
        pattern_matches = candidates.loc[mask]
        if len(pattern_matches) > 0:
            candidates = pattern_matches

    # Step 2: Apply source_hint filter if provided
    elif source_hint and "Source" in candidates.columns:
        mask = candidates["Source"].str.lower() == source_hint.lower()
        hint_matches = candidates.loc[mask]
        if len(hint_matches) > 0:
            candidates = hint_matches

    # Step 3: Prefix blocking on ticker_norm
    if len(query_norm) >= 2 and "ticker_norm" in candidates.columns:
        # Try exact match first
        mask = candidates["ticker_norm"] == query_norm
        exact = candidates.loc[mask]
        if len(exact) > 0:
            return exact

        # Then prefix match
        if len(query_norm) >= 3:
            prefix = query_norm[:3]
            mask = candidates["ticker_norm"].str.startswith(prefix, na=False)
            prefix_matches = candidates.loc[mask]
            if len(prefix_matches) > 0:
                candidates = prefix_matches

    # Step 4: If still too many (>100), try name prefix
    if len(candidates) > 100 and len(query_norm) >= 4 and "name_norm" in candidates.columns:
        name_prefix = query_norm[:4]
        mask = candidates["name_norm"].str.contains(name_prefix, case=False, na=False)
        name_matches = candidates.loc[mask]
        if len(name_matches) > 0:
            candidates = name_matches

    return candidates


# ---- Helper: Get searchable text for an instrument ----
def _get_searchable_text(row: pd.Series) -> str:
    """Build searchable text from instrument row.

    Combines ticker, name, and any aliases for fuzzy matching.

    Args:
        row: Instrument row from DataFrame

    Returns:
        Combined searchable text
    """
    parts = []

    # Add ticker
    if "ticker_norm" in row and pd.notna(row["ticker_norm"]):
        parts.append(row["ticker_norm"])

    # Add name
    if "name_norm" in row and pd.notna(row["name_norm"]):
        parts.append(row["name_norm"])

    # Add original ticker (if different)
    if "asset_id" in row and pd.notna(row["asset_id"]):
        ticker_orig_norm = normalize_ticker(str(row["asset_id"]))
        if ticker_orig_norm not in parts:
            parts.append(ticker_orig_norm)

    # Add any Name column
    for col in ["Name", "name", "instrument_name"]:
        if col in row and pd.notna(row[col]):
            name_orig_norm = normalize_instrument_name(str(row[col]))
            if name_orig_norm not in parts:
                parts.append(name_orig_norm)

    return " ".join(parts)


# ---- Helper: Score a single candidate ----
def _score_candidate(
    row: pd.Series,
    query_norm: str,
    source_hint: Optional[str] = None,
    material_hint: Optional[str] = None,
) -> float:
    """Score a candidate instrument against the query.

    Uses RapidFuzz WRatio for fuzzy matching, with boosts for:
      - Source matching source_hint (+5)
      - Material matching material_hint (+2)

    Args:
        row: Candidate instrument row
        query_norm: Normalized query string
        source_hint: Optional source to boost
        material_hint: Optional material to boost

    Returns:
        Score from 0-100+ (can exceed 100 with boosts)
    """
    searchable = _get_searchable_text(row)

    # Base fuzzy score
    score = fuzz.WRatio(query_norm, searchable)

    # Source boost
    if source_hint and "Source" in row:
        if str(row["Source"]).lower() == source_hint.lower():
            score += 5

    # Material boost
    if material_hint and "material_id" in row:
        if pd.notna(row["material_id"]):
            # Simple substring match for now
            if material_hint.lower() in str(row["material_id"]).lower():
                score += 2

    return score


# ---- Main Resolution Function ----
def resolve_instrument(
    text: str,
    df: pd.DataFrame,
    *,
    source_hint: Optional[str] = None,
    threshold: int = 92,
) -> Optional[pd.Series]:
    """Resolve text to an instrument using blocking and fuzzy matching.

    Args:
        text: Input text (ticker, name, or description)
        df: Instruments DataFrame (from load_instruments)
        source_hint: Optional data source to filter/boost
        threshold: Minimum score required for match (default 92)

    Returns:
        Best matching instrument row or None if no match above threshold

    Examples:
        >>> resolve_instrument("MB-CO-0005", df)
        Series(asset_id="MB-CO-0005", Name="Cobalt standard grade...", ...)

        >>> resolve_instrument("LME aluminum", df, source_hint="LME")
        Series(asset_id="LME_AL_CASH", Name="LME Aluminium Cash", ...)
    """
    if text is None or not text or text.strip() == "":
        return None

    # Normalize query
    query_norm = normalize_ticker(text.strip())

    # Detect ticker pattern
    ticker_pattern_source = _detect_ticker_pattern(text.strip())

    # Build candidate pool
    candidates = _build_candidate_pool(
        df,
        query_norm,
        source_hint=source_hint,
        ticker_pattern_source=ticker_pattern_source,
    )

    if candidates.empty:
        return None

    # Score all candidates
    scores = []
    for idx, row in candidates.iterrows():
        score = _score_candidate(row, query_norm, source_hint=source_hint)
        scores.append((idx, score))

    # Sort by score
    scores.sort(key=lambda x: x[1], reverse=True)

    # Return best if above threshold
    best_idx, best_score = scores[0]
    if best_score >= threshold:
        return df.loc[best_idx]

    return None


# ---- Top-K Matches Function ----
def topk_matches(
    text: str,
    df: pd.DataFrame,
    *,
    k: int = 5,
    source_hint: Optional[str] = None,
) -> list[tuple[pd.Series, float]]:
    """Get top-K matching instruments with scores.

    Args:
        text: Input text to match
        df: Instruments DataFrame
        k: Number of top matches to return
        source_hint: Optional source to filter/boost

    Returns:
        List of (instrument_row, score) tuples, sorted by score descending

    Examples:
        >>> matches = topk_matches("cobalt", df, k=3)
        >>> for instrument, score in matches:
        ...     print(f"{instrument['asset_id']}: {score}")
        MB-CO-0005: 95
        MB-CO-0001: 92
        MB-BMS-0002: 88
    """
    if not text or text.strip() == "":
        return []

    # Normalize query
    query_norm = normalize_ticker(text.strip())

    # Detect ticker pattern
    ticker_pattern_source = _detect_ticker_pattern(text.strip())

    # Build candidate pool
    candidates = _build_candidate_pool(
        df,
        query_norm,
        source_hint=source_hint,
        ticker_pattern_source=ticker_pattern_source,
    )

    if candidates.empty:
        return []

    # Score all candidates
    results = []
    for idx, row in candidates.iterrows():
        score = _score_candidate(row, query_norm, source_hint=source_hint)
        results.append((row, score))

    # Sort by score and return top-k
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:k]
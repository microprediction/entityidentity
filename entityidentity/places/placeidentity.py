"""Place Entity Resolution
------------------------

Implements country-based blocking strategy for admin1 regions:
  1. Extract country via country_identifier() (reuse existing)
  2. Filter admin1 by country if found (5000 → ~50 per country)
  3. Prefix match on admin1_name + aliases
  4. RapidFuzz WRatio scoring on names + aliases

API:
  resolve_place(name, df, country_hint=None, threshold=90) -> Series | None
  topk_matches(name, df, k=5, country_hint=None) -> list[(Series, score)]
"""

from __future__ import annotations
from typing import Optional
import pandas as pd

try:
    from rapidfuzz import process, fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e

from entityidentity.places.placenormalize import normalize_place_name
from entityidentity.utils.resolver import get_aliases, score_candidate


# ---- Helper: Extract alias columns as list ----
def _get_aliases(row: pd.Series) -> list[str]:
    """
    Extract all non-null alias values from alias1...alias10 columns.

    This is a wrapper around the shared get_aliases function that applies
    place-specific normalization.

    Args:
        row: DataFrame row with alias1, alias2, ..., alias10 columns

    Returns:
        List of normalized alias strings (non-null, non-empty)

    Examples:
        >>> row = pd.Series({'alias1': 'WA', 'alias2': 'West Australia', 'alias3': None})
        >>> _get_aliases(row)
        ['wa', 'west australia']
    """
    return get_aliases(row, normalize_place_name)


# ---- Helper: Build candidate pool for scoring ----
def _build_candidate_pool(
    df: pd.DataFrame,
    query_norm: str,
    country_hint: Optional[str] = None,
) -> pd.DataFrame:
    """Apply blocking strategy to filter candidate places.

    Blocking sequence:
      1. Country filter (if country_hint provided) - reduces 5000 → ~50
      2. Prefix match on admin1_norm (first 3 chars)

    Args:
        df: Full places DataFrame
        query_norm: Normalized query string
        country_hint: Optional ISO 3166-1 alpha-2 country code (e.g., "ZA", "AU")

    Returns:
        Filtered DataFrame of candidate places
    """
    candidates = df.copy()

    # Block 1: Country filter
    if country_hint:
        country_upper = country_hint.upper()
        candidates = candidates[candidates['country'] == country_upper]

        # If no matches and country hint is >2 chars, try country resolution
        if candidates.empty and len(country_hint) > 2:
            # Import here to avoid circular dependency
            try:
                from entityidentity.countries import country_identifier
                resolved_country = country_identifier(country_hint)
                if resolved_country:
                    candidates = df[df['country'] == resolved_country]
            except ImportError:
                pass  # country module not available

    # Block 2: Prefix match (first 3 chars)
    if len(query_norm) >= 3:
        prefix = query_norm[:3]
        candidates = candidates[
            candidates['admin1_norm'].str.startswith(prefix, na=False)
        ]

    return candidates


# ---- Helper: Score a single candidate ----
def _score_place(row: pd.Series, query_norm: str) -> int:
    """
    Score a place candidate using WRatio on name + aliases.

    This is a wrapper around the shared score_candidate function.

    Args:
        row: DataFrame row with admin1_norm and alias columns
        query_norm: Normalized query string

    Returns:
        Best score (0-100) from name or aliases
    """
    # Use admin1_norm instead of name_norm for places
    return score_candidate(
        row,
        query_norm,
        normalize_fn=normalize_place_name,
        name_column='admin1_norm',
        max_aliases=10
    )


# ---- Main resolution function ----
def resolve_place(
    name: str,
    df: pd.DataFrame,
    country_hint: Optional[str] = None,
    threshold: int = 90,
) -> Optional[pd.Series]:
    """
    Resolve a place name to a canonical admin1 region.

    Args:
        name: Place name query (e.g., "Limpopo", "Western Australia", "WA")
        df: Places DataFrame loaded from places.parquet
        country_hint: Optional ISO 3166-1 alpha-2 country code (e.g., "ZA", "AU")
        threshold: Minimum fuzzy match score (0-100, default 90)

    Returns:
        Matched place row (Series) or None if no match above threshold

    Examples:
        >>> df = pd.read_parquet("places.parquet")
        >>> resolve_place("Limpopo", df, country_hint="ZA")
        Series(place_id='...', country='ZA', admin1='Limpopo', ...)

        >>> resolve_place("Western Australia", df)
        Series(place_id='...', country='AU', admin1='Western Australia', ...)

        >>> resolve_place("WA", df, country_hint="AU")
        Series(place_id='...', country='AU', admin1='Western Australia', ...)
    """
    if df.empty:
        return None

    # Normalize query
    query_norm = normalize_place_name(name)
    if not query_norm:
        return None

    # Build candidate pool
    candidates = _build_candidate_pool(df, query_norm, country_hint)

    if candidates.empty:
        return None

    # Exact match on normalized admin1
    exact_match = candidates[candidates['admin1_norm'] == query_norm]
    if not exact_match.empty:
        return exact_match.iloc[0]

    # Exact match on aliases
    for idx, row in candidates.iterrows():
        aliases = _get_aliases(row)
        if query_norm in aliases:
            return row

    # Fuzzy matching with RapidFuzz WRatio
    scores = []
    for idx, row in candidates.iterrows():
        score = _score_place(row, query_norm)
        if score >= threshold:
            scores.append((idx, score))

    if not scores:
        return None

    # Return best match
    scores.sort(key=lambda x: x[1], reverse=True)
    best_idx = scores[0][0]
    return candidates.loc[best_idx]


# ---- Top-k matches function ----
def topk_matches(
    name: str,
    df: pd.DataFrame,
    k: int = 5,
    country_hint: Optional[str] = None,
) -> list[tuple[pd.Series, int]]:
    """
    Return top-k place matches with scores.

    Args:
        name: Place name query
        df: Places DataFrame
        k: Number of top matches to return (default 5)
        country_hint: Optional ISO 3166-1 alpha-2 country code

    Returns:
        List of (place_row, score) tuples, sorted by score descending

    Examples:
        >>> df = pd.read_parquet("places.parquet")
        >>> topk_matches("Limpopo", df, k=3)
        [(Series(admin1='Limpopo', ...), 100), (Series(admin1='Limpopo Norte', ...), 85), ...]
    """
    if df.empty:
        return []

    # Normalize query
    query_norm = normalize_place_name(name)
    if not query_norm:
        return []

    # Build candidate pool
    candidates = _build_candidate_pool(df, query_norm, country_hint)

    if candidates.empty:
        return []

    # Score all candidates
    scores = []
    for idx, row in candidates.iterrows():
        score = _score_place(row, query_norm)
        scores.append((row, score))

    # Sort by score descending and return top-k
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:k]


__all__ = [
    "resolve_place",
    "topk_matches",
]

"""Basket Entity Resolution
-------------------------

Implements a 3-step blocking strategy for basket resolution:
  1. Exact basket_id match (if query looks like an ID)
  2. Name prefix (first 3 chars normalized)
  3. RapidFuzz WRatio scoring on names + aliases

Blocking reduces search space by ~99% before fuzzy matching.

API:
  resolve_basket(name, df, threshold=90) -> Series | None
  topk_matches(name, df, k=5) -> list[(Series, score)]
"""

from __future__ import annotations
from typing import Optional
import pandas as pd

try:
    from rapidfuzz import process, fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e

from entityidentity.baskets.basketnormalize import normalize_basket_name
from entityidentity.utils.resolver import get_aliases, score_candidate


# ---- Helper: Extract alias columns as list ----
def _get_aliases(row: pd.Series) -> list[str]:
    """Extract all non-null alias values from alias1...alias10 columns.

    Args:
        row: DataFrame row with alias1, alias2, ..., alias10 columns

    Returns:
        List of normalized alias strings (non-null, non-empty)

    Examples:
        >>> row = pd.Series({'alias1': '4E PGM', 'alias2': 'Four Element PGM', 'alias3': None})
        >>> _get_aliases(row)
        ['4e pgm', 'four element pgm']
    """
    return get_aliases(row, normalize_basket_name)


# ---- Helper: Build candidate pool for scoring ----
def _build_candidate_pool(
    df: pd.DataFrame,
    query_norm: str,
) -> pd.DataFrame:
    """Apply blocking strategy to filter candidate baskets.

    Blocking sequence:
      1. Exact basket_id match (if query looks like ID format: ALL_CAPS_UNDERSCORE)
      2. Name prefix (first 3 chars normalized) - reduces search space by ~99%

    This blocking strategy is simpler than metals because:
      - No symbols (baskets don't have single-letter abbreviations)
      - No categories (basket count is small, ~5-20 baskets)
      - No clusters (baskets are flat namespace)

    Args:
        df: Full baskets DataFrame
        query_norm: Normalized query string

    Returns:
        Filtered DataFrame of candidate baskets for fuzzy scoring
    """
    # Step 1: Exact basket_id match (if query looks like an ID)
    # basket_ids are uppercase with underscores (e.g., "PGM_4E", "BATTERY_PACK")
    if query_norm.replace("_", "").replace(" ", "").isupper() and "_" in query_norm:
        id_matches = df[df["basket_id"].str.lower() == query_norm.lower()].copy()
        if not id_matches.empty:
            return id_matches

    # Step 2: Name prefix blocking (first 3 chars normalized)
    # This reduces search space dramatically for fuzzy matching
    # Example: "pgm" prefix blocks to only PGM baskets, not REE or Battery
    if len(query_norm) >= 3:
        prefix = query_norm[:3]
        # Filter using prefix
        candidates = df[df["name_norm"].str.startswith(prefix, na=False)].copy()

        # If prefix blocking eliminated everything, fall back to full search
        # (happens with very short queries or typos in first chars)
        if candidates.empty:
            return df.copy()
        return candidates

    # For very short queries, return full dataframe
    return df.copy()


# ---- Helper: Score a single candidate against query ----
def _score_candidate(row: pd.Series, query_norm: str) -> float:
    """Score a candidate basket row against normalized query.

    Uses RapidFuzz WRatio scorer (same as metals module).
    Checks both name_norm and all alias columns.

    Args:
        row: Candidate basket row
        query_norm: Normalized query string

    Returns:
        Best fuzzy match score (0-100) across name and aliases

    Examples:
        >>> row = pd.Series({'name_norm': 'pgm 4e', 'alias1': '4e pgm', 'alias2': 'platinum group 4e'})
        >>> _score_candidate(row, 'pgm 4e')
        100.0

        >>> _score_candidate(row, '4e')
        90.0  # partial match
    """
    return score_candidate(row, query_norm, normalize_basket_name)


# ---- Main resolution function ----
def resolve_basket(
    name: str,
    df: pd.DataFrame,
    *,
    threshold: int = 90,
) -> Optional[pd.Series]:
    """Resolve basket name to canonical basket row.

    Implements 3-step blocking strategy with RapidFuzz scoring:
      1. Exact basket_id match (if query looks like an ID)
      2. Name prefix (first 3 chars) - reduces search space by ~99%
      3. RapidFuzz WRatio scoring on name + aliases

    Args:
        name: Basket query (name or alias)
        df: Full baskets DataFrame
        threshold: Minimum fuzzy match score (0-100)

    Returns:
        Best-matching basket row as Series, or None if no match above threshold

    Examples:
        >>> resolve_basket("PGM 4E", df)
        Series([..., name='PGM 4E', basket_id='PGM_4E', ...])

        >>> resolve_basket("4e pgm", df)
        Series([..., name='PGM 4E', basket_id='PGM_4E', ...])

        >>> resolve_basket("ndpr", df)
        Series([..., name='NdPr', basket_id='NDPR', ...])

        >>> resolve_basket("battery metals", df)
        Series([..., name='Battery Pack', basket_id='BATTERY_PACK', ...])
    """
    if not name or not str(name).strip():
        return None

    # Normalize query
    query_norm = normalize_basket_name(str(name))

    if not query_norm:
        return None

    # Build candidate pool using blocking strategy
    candidates = _build_candidate_pool(
        df=df,
        query_norm=query_norm,
    )

    if candidates.empty:
        return None

    # If we have exact basket_id match and only one candidate, return it
    if len(candidates) == 1:
        id_match = candidates.iloc[0]
        if pd.notna(id_match["basket_id"]) and \
           id_match["basket_id"].lower() == query_norm.replace(" ", "_").lower():
            return id_match

    # Score all candidates using RapidFuzz WRatio
    scores = []
    for idx, row in candidates.iterrows():
        score = _score_candidate(row, query_norm)
        scores.append((idx, score))

    if not scores:
        return None

    # Sort by score descending, take best
    scores.sort(key=lambda x: x[1], reverse=True)
    best_idx, best_score = scores[0]

    if best_score < threshold:
        return None

    return candidates.loc[best_idx]


# ---- Top-K matches for review UIs ----
def topk_matches(
    name: str,
    df: pd.DataFrame,
    *,
    k: int = 5,
) -> list[tuple[pd.Series, float]]:
    """Return top-K basket candidates with scores.

    Useful for interactive review UIs and understanding resolution decisions.

    Args:
        name: Basket query (name or alias)
        df: Full baskets DataFrame
        k: Number of top candidates to return

    Returns:
        List of (basket_row, score) tuples, ordered by descending score

    Examples:
        >>> matches = topk_matches("pgm", df, k=3)
        >>> for row, score in matches:
        ...     print(f"{row['name']} - {score:.1f}")
        PGM 4E - 95.0
        PGM 5E - 95.0
        ...
    """
    if not name or not str(name).strip():
        return []

    # Normalize query
    query_norm = normalize_basket_name(str(name))

    if not query_norm:
        return []

    # For top-K, use all candidates (no blocking)
    # Since basket count is small (~5-20), we can afford full search
    candidates = df.copy()

    if candidates.empty:
        return []

    # Score all candidates
    scored = []
    for idx, row in candidates.iterrows():
        score = _score_candidate(row, query_norm)
        scored.append((row.copy(), score))

    # Sort by score descending, take top-K
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


__all__ = [
    "resolve_basket",
    "topk_matches",
]

"""Shared entity resolution utilities.

This module provides generic resolution helpers used across
metals, baskets, and other entity resolution modules.
"""

from __future__ import annotations
from typing import Callable, Optional
import pandas as pd

try:
    from rapidfuzz import fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e


def get_aliases(
    row: pd.Series,
    normalize_fn: Callable[[str], str],
    max_aliases: int = 10,
) -> list[str]:
    """Extract and normalize alias columns from a DataFrame row.

    Looks for alias1, alias2, ..., aliasN columns and returns normalized values.

    Args:
        row: DataFrame row with alias1, alias2, ..., aliasN columns
        normalize_fn: Function to normalize alias strings
        max_aliases: Maximum number of alias columns to check (default: 10)

    Returns:
        List of normalized alias strings (non-null, non-empty)

    Examples:
        >>> row = pd.Series({'alias1': 'Pt', 'alias2': 'platinum', 'alias3': None})
        >>> get_aliases(row, lambda s: s.lower())
        ['pt', 'platinum']
    """
    aliases = []
    for i in range(1, max_aliases + 1):
        col = f"alias{i}"
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            aliases.append(normalize_fn(str(row[col])))
    return aliases


def score_candidate(
    row: pd.Series,
    query_norm: str,
    normalize_fn: Callable[[str], str],
    name_column: str = "name_norm",
    max_aliases: int = 10,
) -> float:
    """Score a candidate row against a normalized query using fuzzy matching.

    Uses RapidFuzz WRatio scorer to check both the name column and all alias columns.

    Args:
        row: Candidate entity row
        query_norm: Normalized query string
        normalize_fn: Function to normalize alias strings
        name_column: Name of the column containing the normalized name (default: "name_norm")
        max_aliases: Maximum number of alias columns to check (default: 10)

    Returns:
        Best fuzzy match score (0-100) across name and aliases

    Examples:
        >>> row = pd.Series({'name_norm': 'platinum', 'alias1': 'pt', 'alias2': 'plat'})
        >>> score_candidate(row, 'platinum', lambda s: s.lower())
        100.0
    """
    # Collect all searchable strings: name + aliases
    searchable = [row[name_column]]
    searchable.extend(get_aliases(row, normalize_fn, max_aliases))

    # Score query against all searchable strings, take best
    best_score = 0.0
    for s in searchable:
        if pd.notna(s) and str(s).strip():
            score = fuzz.WRatio(query_norm, str(s).lower())
            best_score = max(best_score, score)

    return best_score


def score_all_candidates(
    candidates: pd.DataFrame,
    query_norm: str,
    normalize_fn: Callable[[str], str],
    name_column: str = "name_norm",
    max_aliases: int = 10,
) -> list[tuple[int, float]]:
    """Score all candidate rows against a normalized query.

    Args:
        candidates: DataFrame of candidate entities
        query_norm: Normalized query string
        normalize_fn: Function to normalize alias strings
        name_column: Name of the column containing the normalized name (default: "name_norm")
        max_aliases: Maximum number of alias columns to check (default: 10)

    Returns:
        List of (index, score) tuples, unsorted

    Examples:
        >>> candidates = pd.DataFrame({'name_norm': ['platinum', 'palladium']})
        >>> scores = score_all_candidates(candidates, 'plat', lambda s: s.lower())
        >>> scores
        [(0, 95.0), (1, 85.0)]
    """
    scores = []
    for idx, row in candidates.iterrows():
        score = score_candidate(row, query_norm, normalize_fn, name_column, max_aliases)
        scores.append((idx, score))
    return scores


def find_best_match(
    candidates: pd.DataFrame,
    query_norm: str,
    normalize_fn: Callable[[str], str],
    threshold: int = 90,
    name_column: str = "name_norm",
    max_aliases: int = 10,
) -> Optional[pd.Series]:
    """Find the best matching candidate above a threshold.

    Scores all candidates and returns the best match if it exceeds the threshold.

    Args:
        candidates: DataFrame of candidate entities
        query_norm: Normalized query string
        normalize_fn: Function to normalize alias strings
        threshold: Minimum fuzzy match score (0-100, default: 90)
        name_column: Name of the column containing the normalized name (default: "name_norm")
        max_aliases: Maximum number of alias columns to check (default: 10)

    Returns:
        Best-matching row as Series, or None if no match above threshold

    Examples:
        >>> candidates = pd.DataFrame({'name_norm': ['platinum', 'palladium']})
        >>> match = find_best_match(candidates, 'plat', lambda s: s.lower(), threshold=90)
        >>> match['name_norm']
        'platinum'
    """
    if candidates.empty:
        return None

    # Score all candidates
    scores = score_all_candidates(
        candidates, query_norm, normalize_fn, name_column, max_aliases
    )

    if not scores:
        return None

    # Sort by score descending, take best
    scores.sort(key=lambda x: x[1], reverse=True)
    best_idx, best_score = scores[0]

    if best_score < threshold:
        return None

    return candidates.loc[best_idx]


def topk_matches(
    candidates: pd.DataFrame,
    query_norm: str,
    normalize_fn: Callable[[str], str],
    k: int = 5,
    name_column: str = "name_norm",
    max_aliases: int = 10,
) -> list[tuple[pd.Series, float]]:
    """Return top-K matching candidates with scores.

    Useful for interactive review UIs and understanding resolution decisions.

    Args:
        candidates: DataFrame of candidate entities
        query_norm: Normalized query string
        normalize_fn: Function to normalize alias strings
        k: Number of top candidates to return (default: 5)
        name_column: Name of the column containing the normalized name (default: "name_norm")
        max_aliases: Maximum number of alias columns to check (default: 10)

    Returns:
        List of (row, score) tuples, ordered by descending score

    Examples:
        >>> candidates = pd.DataFrame({'name_norm': ['platinum', 'palladium', 'plutonium']})
        >>> matches = topk_matches(candidates, 'plat', lambda s: s.lower(), k=2)
        >>> [(row['name_norm'], score) for row, score in matches]
        [('platinum', 95.0), ('palladium', 85.0)]
    """
    if candidates.empty:
        return []

    # Score all candidates
    scored = []
    for idx, row in candidates.iterrows():
        score = score_candidate(row, query_norm, normalize_fn, name_column, max_aliases)
        scored.append((row.copy(), score))

    # Sort by score descending, take top-K
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


__all__ = [
    "get_aliases",
    "score_candidate",
    "score_all_candidates",
    "find_best_match",
    "topk_matches",
]

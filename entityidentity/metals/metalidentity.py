"""Metal Entity Resolution
------------------------

Implements the 5-step blocking strategy from section 6 of METALS_ONTOLOGY_PLAN.md:
  1. Exact symbol match
  2. Category bucket filter
  3. Name prefix (first 3 chars normalized)
  4. Optional cluster filter
  5. RapidFuzz WRatio scoring on names + aliases

Supports "metal:form" suffix parsing (e.g., "lithium:carbonate")

API:
  resolve_metal(name, df, cluster=None, category=None, threshold=90) -> Series | None
  topk_matches(name, df, k=5) -> list[(Series, score)]
"""

from __future__ import annotations
from typing import Optional
import pandas as pd

try:
    from rapidfuzz import process, fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e

from entityidentity.metals.metalnormalize import normalize_name


# ---- Helper: Parse "metal:form" hints ----
def _parse_metal_form_hint(query: str) -> tuple[str, Optional[str]]:
    """Parse "metal:form" suffix hints.

    Args:
        query: Input string, possibly with ":form" suffix

    Returns:
        (metal_part, form_hint) tuple

    Examples:
        >>> _parse_metal_form_hint("lithium:carbonate")
        ('lithium', 'carbonate')

        >>> _parse_metal_form_hint("platinum")
        ('platinum', None)

        >>> _parse_metal_form_hint("Li:carbonate")
        ('Li', 'carbonate')
    """
    if ":" not in query:
        return query, None

    parts = query.split(":", 1)
    metal_part = parts[0].strip()
    form_hint = parts[1].strip() if len(parts) > 1 else None

    return metal_part, form_hint


# ---- Helper: Extract alias columns as list ----
def _get_aliases(row: pd.Series) -> list[str]:
    """Extract all non-null alias values from alias1...alias10 columns.

    Args:
        row: DataFrame row with alias1, alias2, ..., alias10 columns

    Returns:
        List of normalized alias strings (non-null, non-empty)

    Examples:
        >>> row = pd.Series({'alias1': 'Pt', 'alias2': 'platinum', 'alias3': None})
        >>> _get_aliases(row)
        ['pt', 'platinum']
    """
    aliases = []
    for i in range(1, 11):  # alias1 through alias10
        col = f"alias{i}"
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            aliases.append(normalize_name(str(row[col])))
    return aliases


# ---- Helper: Build candidate pool for scoring ----
def _build_candidate_pool(
    df: pd.DataFrame,
    query_norm: str,
    form_hint: Optional[str] = None,
    cluster: Optional[str] = None,
    category: Optional[str] = None,
) -> pd.DataFrame:
    """Apply blocking strategy to filter candidate metals.

    Blocking sequence (section 6):
      1. Exact symbol match (if query is short and uppercase-ish)
      2. Category bucket filter (if specified)
      3. Name prefix (first 3 chars normalized)
      4. Optional cluster filter (if specified)
      5. Form hint filter (if provided)

    Args:
        df: Full metals DataFrame
        query_norm: Normalized query string
        form_hint: Optional form hint from "metal:form" syntax
        cluster: Optional cluster_id filter
        category: Optional category_bucket filter

    Returns:
        Filtered DataFrame of candidate metals for fuzzy scoring
    """
    candidates = df.copy()

    # Step 1: Exact symbol match (short, uppercase-looking queries)
    # If query matches a symbol exactly, return just that row
    if len(query_norm) <= 3:
        symbol_matches = candidates[
            candidates["symbol"].notna() &
            (candidates["symbol"].str.lower() == query_norm.lower())
        ]
        if not symbol_matches.empty:
            return symbol_matches

    # Step 2: Category bucket filter
    if category is not None:
        candidates = candidates[candidates["category_bucket"] == category]

    # Step 3: Name prefix blocking (first 3 chars normalized)
    if len(query_norm) >= 3:
        prefix = query_norm[:3]
        candidates = candidates[
            candidates["name_norm"].str.startswith(prefix, na=False)
        ]

    # Step 4: Optional cluster filter
    if cluster is not None:
        candidates = candidates[candidates["cluster_id"] == cluster]

    # Step 5: Form hint filter (if provided via "metal:form" syntax)
    if form_hint is not None:
        form_norm = normalize_name(form_hint)
        # Filter to rows where name_norm contains the form hint
        candidates = candidates[
            candidates["name_norm"].str.contains(form_norm, case=False, na=False)
        ]

    return candidates


# ---- Helper: Score a single candidate against query ----
def _score_candidate(row: pd.Series, query_norm: str) -> float:
    """Score a candidate metal row against normalized query.

    Uses RapidFuzz WRatio scorer as specified in section 6.
    Checks both name_norm and all alias columns.

    Args:
        row: Candidate metal row
        query_norm: Normalized query string

    Returns:
        Best fuzzy match score (0-100) across name and aliases
    """
    # Collect all searchable strings: name_norm + aliases
    searchable = [row["name_norm"]]
    searchable.extend(_get_aliases(row))

    # Score query against all searchable strings, take best
    best_score = 0.0
    for s in searchable:
        if pd.notna(s) and str(s).strip():
            score = fuzz.WRatio(query_norm, str(s).lower())
            best_score = max(best_score, score)

    return best_score


# ---- Main resolution function ----
def resolve_metal(
    name: str,
    df: pd.DataFrame,
    *,
    cluster: Optional[str] = None,
    category: Optional[str] = None,
    threshold: int = 90,
) -> Optional[pd.Series]:
    """Resolve metal name to canonical metal row.

    Implements 5-step blocking strategy with RapidFuzz scoring:
      1. Exact symbol match
      2. Category bucket filter
      3. Name prefix (first 3 chars)
      4. Optional cluster filter
      5. RapidFuzz WRatio scoring on name + aliases

    Supports "metal:form" syntax (e.g., "lithium:carbonate")

    Args:
        name: Metal query (name, symbol, form, spec)
        df: Full metals DataFrame
        cluster: Optional cluster_id filter
        category: Optional category_bucket filter
        threshold: Minimum fuzzy match score (0-100)

    Returns:
        Best-matching metal row as Series, or None if no match above threshold

    Examples:
        >>> resolve_metal("Pt", df)
        Series([..., name='Platinum', symbol='Pt', ...])

        >>> resolve_metal("lithium:carbonate", df)
        Series([..., name='Lithium carbonate', formula='Li2CO3', ...])

        >>> resolve_metal("APT", df, category="specialty")
        Series([..., name='Ammonium paratungstate', code='WO3', ...])
    """
    if not name or not str(name).strip():
        return None

    # Parse "metal:form" hints
    metal_part, form_hint = _parse_metal_form_hint(str(name))
    query_norm = normalize_name(metal_part)

    if not query_norm:
        return None

    # Build candidate pool using blocking strategy
    candidates = _build_candidate_pool(
        df=df,
        query_norm=query_norm,
        form_hint=form_hint,
        cluster=cluster,
        category=category,
    )

    if candidates.empty:
        return None

    # If we have exact symbol match and only one candidate, return it
    if len(candidates) == 1 and len(query_norm) <= 3:
        symbol_match = candidates.iloc[0]
        if pd.notna(symbol_match["symbol"]) and \
           symbol_match["symbol"].lower() == query_norm.lower():
            return symbol_match

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
    """Return top-K metal candidates with scores.

    Useful for interactive review UIs and understanding resolution decisions.

    Args:
        name: Metal query (name, symbol, form, spec)
        df: Full metals DataFrame
        k: Number of top candidates to return

    Returns:
        List of (metal_row, score) tuples, ordered by descending score

    Examples:
        >>> matches = topk_matches("tungsten", df, k=3)
        >>> for row, score in matches:
        ...     print(f"{row['name']} - {score:.1f}")
        Tungsten - 100.0
        Ammonium paratungstate - 85.0
        ...
    """
    if not name or not str(name).strip():
        return []

    # Parse "metal:form" hints
    metal_part, form_hint = _parse_metal_form_hint(str(name))
    query_norm = normalize_name(metal_part)

    if not query_norm:
        return []

    # Build candidate pool (no threshold, we want top-K regardless)
    # Use broader blocking for top-K (no cluster/category filters)
    candidates = df.copy()

    # Apply prefix blocking if query is long enough
    if len(query_norm) >= 3:
        prefix = query_norm[:3]
        candidates = candidates[
            candidates["name_norm"].str.startswith(prefix, na=False)
        ]

    # Apply form hint if provided
    if form_hint is not None:
        form_norm = normalize_name(form_hint)
        candidates = candidates[
            candidates["name_norm"].str.contains(form_norm, case=False, na=False)
        ]

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
    "resolve_metal",
    "topk_matches",
]

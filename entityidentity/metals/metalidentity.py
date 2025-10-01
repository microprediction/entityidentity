"""
Robust Metal Entity Resolution
-------------------------------

Multi-stage blocking and fuzzy matching pipeline for metal entity resolution:
  1) Exact symbol match (Pt, Pd, Cu, etc.)
  2) Category bucket filtering (if specified)
  3) Name prefix blocking (first 3 chars normalized)
  4) Supply-chain cluster filtering (if specified)
  5) RapidFuzz WRatio scoring over names + aliases

Supports "metal:form" hints for disambiguation (e.g., "lithium:carbonate")

API:
  resolve_metal(name, df, cluster=None, category=None, threshold=90) -> pd.Series | None
  topk_matches(name, df, k=5) -> list[tuple[pd.Series, float]]

Examples:
  >>> df = load_metals()
  >>> resolve_metal("Pt", df)
  Series(...) # Platinum row

  >>> resolve_metal("lithium:carbonate", df)
  Series(...) # Lithium carbonate row

  >>> topk_matches("tungsten", df, k=3)
  [(Series(...), 100.0), (Series(...), 85.0), ...]
"""

from __future__ import annotations
from typing import Optional
import pandas as pd

# ---- Optional imports with helpful error messages ----
try:
    from rapidfuzz import process, fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e

from entityidentity.metals.metalnormalize import normalize_name


def _parse_colon_hint(name: str) -> tuple[str, Optional[str]]:
    """
    Parse "metal:form" hints for disambiguation.

    Examples:
        "lithium:carbonate" -> ("lithium", "carbonate")
        "lithium:hydroxide" -> ("lithium", "hydroxide")
        "platinum" -> ("platinum", None)

    Returns:
        (metal_part, form_hint)
    """
    if ":" not in name:
        return name, None

    parts = name.split(":", 1)
    return parts[0].strip(), parts[1].strip()


def _build_search_strings(row: pd.Series) -> list[str]:
    """
    Build list of searchable strings from a metal row.

    Includes:
      - name (primary)
      - name_norm (normalized)
      - symbol (if present)
      - aliases (alias1...alias10, if present)

    Args:
        row: Metal entity Series from DataFrame

    Returns:
        List of normalized search strings
    """
    strings = []

    # Primary name
    if pd.notna(row.get("name")):
        strings.append(normalize_name(str(row["name"])))

    # Normalized name (if different)
    if pd.notna(row.get("name_norm")):
        norm = str(row["name_norm"])
        if norm not in strings:
            strings.append(norm)

    # Symbol (case-sensitive exact match handled separately, but include for fuzzy)
    if pd.notna(row.get("symbol")):
        strings.append(normalize_name(str(row["symbol"])))

    # Aliases (alias1...alias10)
    for i in range(1, 11):
        alias_col = f"alias{i}"
        if alias_col in row.index and pd.notna(row[alias_col]):
            alias = normalize_name(str(row[alias_col]))
            if alias and alias not in strings:
                strings.append(alias)

    return strings


def _exact_symbol_match(symbol: str, df: pd.DataFrame) -> Optional[pd.Series]:
    """
    Fast exact symbol match (case-sensitive).

    Args:
        symbol: Element symbol (e.g., "Pt", "Pd", "Cu")
        df: Metals DataFrame

    Returns:
        Matching row as Series, or None
    """
    matches = df[df["symbol"] == symbol]
    if len(matches) == 1:
        return matches.iloc[0]
    elif len(matches) > 1:
        # Multiple matches (shouldn't happen in well-formed data)
        # Return first match
        return matches.iloc[0]
    return None


def _block_candidates(
    df: pd.DataFrame,
    name_norm: str,
    *,
    category: Optional[str] = None,
    cluster: Optional[str] = None,
) -> pd.DataFrame:
    """
    Block candidate metals for fuzzy matching.

    Blocking strategy:
      1. Category bucket filter (if specified)
      2. Name prefix (first 3 chars normalized)
      3. Supply-chain cluster filter (if specified)

    Args:
        df: Full metals DataFrame
        name_norm: Normalized query name
        category: Optional category bucket filter
        cluster: Optional cluster_id filter

    Returns:
        Filtered DataFrame of candidates
    """
    candidates = df.copy()

    # Category filter
    if category is not None:
        candidates = candidates[candidates["category_bucket"] == category]

    # Cluster filter
    if cluster is not None:
        candidates = candidates[candidates["cluster_id"] == cluster]

    # Name prefix blocking (first 3 chars)
    if len(name_norm) >= 3:
        prefix = name_norm[:3]
        # Filter to rows where name_norm starts with prefix
        candidates = candidates[
            candidates["name_norm"].str.startswith(prefix, na=False)
        ]

    return candidates


def resolve_metal(
    name: str,
    df: pd.DataFrame,
    *,
    cluster: Optional[str] = None,
    category: Optional[str] = None,
    threshold: int = 90,
) -> Optional[pd.Series]:
    """
    Resolve a metal name/symbol/form to canonical metal entity.

    Multi-stage pipeline:
      1. Parse "metal:form" hints
      2. Exact symbol match (fast path)
      3. Block candidates by category/cluster/prefix
      4. Fuzzy match with RapidFuzz WRatio over names + aliases
      5. Return best match if score >= threshold

    Args:
        name: Metal query (name, symbol, form, spec)
        df: Metals DataFrame from load_metals()
        cluster: Optional supply-chain cluster filter
        category: Optional category bucket filter
        threshold: Minimum fuzzy match score (0-100)

    Returns:
        Best matching row as Series, or None if no match above threshold

    Examples:
        >>> df = load_metals()
        >>> resolve_metal("Pt", df)
        Series(...) # Platinum

        >>> resolve_metal("lithium:carbonate", df)
        Series(...) # Lithium carbonate

        >>> resolve_metal("APT", df, category="specialty")
        Series(...) # Ammonium paratungstate
    """
    if not name or not str(name).strip():
        return None

    query = str(name).strip()

    # Parse colon hints
    metal_part, form_hint = _parse_colon_hint(query)

    # If form hint present, search for combined form
    if form_hint:
        query = f"{metal_part} {form_hint}"

    # Normalize query
    query_norm = normalize_name(query)

    # Fast path: exact symbol match (case-sensitive)
    # Try original query first (e.g., "Pt")
    if len(query) <= 3 and query[0].isupper():
        result = _exact_symbol_match(query, df)
        if result is not None:
            # Apply category/cluster filters if specified
            if category is not None and result.get("category_bucket") != category:
                pass  # Filter out
            elif cluster is not None and result.get("cluster_id") != cluster:
                pass  # Filter out
            else:
                return result

    # Block candidates
    candidates = _block_candidates(
        df=df,
        name_norm=query_norm,
        category=category,
        cluster=cluster,
    )

    if candidates.empty:
        return None

    # Build search corpus: for each candidate, all searchable strings
    # We'll use a flat list approach with indices to track back to rows
    search_corpus = []
    row_indices = []

    for idx, row in candidates.iterrows():
        search_strings = _build_search_strings(row)
        for s in search_strings:
            search_corpus.append(s)
            row_indices.append(idx)

    if not search_corpus:
        return None

    # Fuzzy match with RapidFuzz WRatio
    match = process.extractOne(
        query_norm,
        search_corpus,
        scorer=fuzz.WRatio,
    )

    if match is None:
        return None

    matched_string, score, corpus_idx = match

    if score < threshold:
        return None

    # Map back to original row
    matched_row_idx = row_indices[corpus_idx]
    return candidates.loc[matched_row_idx]


def topk_matches(
    name: str,
    df: pd.DataFrame,
    *,
    k: int = 5,
) -> list[tuple[pd.Series, float]]:
    """
    Return top-K metal candidates with scores.

    Useful for review UIs, disambiguation, and understanding resolution decisions.

    Args:
        name: Metal query (name, symbol, form, spec)
        df: Metals DataFrame from load_metals()
        k: Number of top candidates to return

    Returns:
        List of (row, score) tuples, ordered by descending score

    Examples:
        >>> df = load_metals()
        >>> matches = topk_matches("tungsten", df, k=3)
        >>> for row, score in matches:
        ...     print(f"{row['name']} - {score:.1f}")
        Tungsten - 100.0
        Ammonium paratungstate - 85.0
        ...
    """
    if not name or not str(name).strip():
        return []

    query = str(name).strip()

    # Parse colon hints
    metal_part, form_hint = _parse_colon_hint(query)
    if form_hint:
        query = f"{metal_part} {form_hint}"

    query_norm = normalize_name(query)

    # Build search corpus from all metals
    search_corpus = []
    row_indices = []

    for idx, row in df.iterrows():
        search_strings = _build_search_strings(row)
        for s in search_strings:
            search_corpus.append(s)
            row_indices.append(idx)

    if not search_corpus:
        return []

    # Extract top K matches
    matches = process.extract(
        query_norm,
        search_corpus,
        scorer=fuzz.WRatio,
        limit=k * 3,  # Get extra to deduplicate rows
    )

    # Deduplicate by row index, keeping best score per row
    seen_indices = {}
    for matched_string, score, corpus_idx in matches:
        row_idx = row_indices[corpus_idx]
        if row_idx not in seen_indices:
            seen_indices[row_idx] = score
        else:
            # Keep highest score
            seen_indices[row_idx] = max(seen_indices[row_idx], score)

    # Sort by score descending and take top K
    top_k_indices = sorted(
        seen_indices.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:k]

    # Build result list
    results = []
    for row_idx, score in top_k_indices:
        row = df.loc[row_idx]
        results.append((row, float(score)))

    return results


__all__ = [
    "resolve_metal",
    "topk_matches",
]

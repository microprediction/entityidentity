"""Candidate blocking strategies for company matching."""

from __future__ import annotations
from typing import Optional

import pandas as pd

from entityidentity.companies.companynormalize import normalize_name


def block_candidates(
    df: pd.DataFrame,
    query_norm: str,
    country: Optional[str] = None,
    max_candidates: int = 50_000,
) -> pd.DataFrame:
    """Filter candidates using cheap blocking strategies.
    
    Strategies:
    1. Country filter (if provided)
    2. First token prefix match (if query has 3+ char token)
    """
    candidates = df

    # Country blocking
    if country:
        country_upper = country.upper()
        country_matches = candidates["country"].str.upper() == country_upper
        if country_matches.any():
            candidates = candidates[country_matches]

    # First token blocking
    tokens = query_norm.split()
    if tokens and len(tokens[0]) >= 3:
        first_token = tokens[0]

        # Check name_norm starts with first token
        name_mask = candidates["name_norm"].str.startswith(first_token)

        # Check any alias starts with first token (alias1-alias5)
        alias_mask = pd.Series([False] * len(candidates), index=candidates.index)
        for i in range(1, 6):
            alias_col = f"alias{i}"
            if alias_col in candidates.columns:
                alias_mask |= candidates[alias_col].notna() & candidates[alias_col].apply(
                    lambda alias: normalize_name(str(alias)).startswith(first_token) if pd.notna(alias) else False
                )

        combined_mask = name_mask | alias_mask
        if combined_mask.any():
            candidates = candidates[combined_mask]

    return candidates.head(max_candidates)


__all__ = ["block_candidates"]



"""Candidate scoring for company matching."""

from __future__ import annotations
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process

from entityidentity.companies.companynormalize import normalize_company_name


def score_candidates(
    df: pd.DataFrame,
    query_norm: str,
    country: Optional[str] = None,
    k: int = 10,
) -> pd.DataFrame:
    """Score candidates using RapidFuzz with boosts.
    
    Scoring:
    - Base: WRatio between query and name_norm
    - Alias boost: Best match among aliases
    - Country match: +2 points
    - Has LEI: +1 point
    """
    if df.empty:
        return df

    # Mark country matches
    if country:
        df = df.assign(country_match=(df["country"].str.upper() == country.upper()))
    else:
        df = df.assign(country_match=False)

    # Mark LEI presence
    df = df.assign(has_lei=df["lei"].notna() & df["lei"].ne(""))

    # Primary score: name_norm vs query
    choices = df["name_norm"].tolist()
    scores = process.cdist([query_norm], choices, scorer=fuzz.WRatio)[0]
    df = df.assign(score_primary=scores)

    # Alias score: best alias match (alias1-alias5)
    alias_scores: list[int] = []
    for idx in range(len(df)):
        best_alias_score = 0
        row = df.iloc[idx]
        for i in range(1, 6):
            alias_col = f"alias{i}"
            if alias_col in df.columns:
                alias = row[alias_col]
                if pd.notna(alias):
                    alias_norm = normalize_company_name(str(alias))
                    alias_score = fuzz.WRatio(query_norm, alias_norm)
                    best_alias_score = max(best_alias_score, alias_score)
        alias_scores.append(best_alias_score)
    df = df.assign(score_alias=alias_scores)

    # Combined score: max of primary and alias
    df = df.assign(score=df[["score_primary", "score_alias"]].max(axis=1))

    # Apply boosts
    boost = 0
    if "country_match" in df.columns:
        boost += df["country_match"].astype(int) * 2
    if "has_lei" in df.columns:
        boost += df["has_lei"].astype(int) * 1
    df = df.assign(score=df["score"] + boost)

    # Cap at 100
    df["score"] = df["score"].clip(upper=100.0)

    # Sort and return top K (at least)
    df = df.sort_values("score", ascending=False)
    return df.head(max(k, 10))


__all__ = ["score_candidates"]



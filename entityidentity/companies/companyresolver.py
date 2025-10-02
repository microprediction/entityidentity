"""Company resolution orchestrator.

Coordinates loading, blocking, scoring, and decision logic.
"""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from entityidentity.companies.companynormalize import (
    normalize_company_name,
    LEGAL_RE,
)
from entityidentity.companies.companyblocking import block_candidates
from entityidentity.companies.companyscoring import score_candidates


@lru_cache(maxsize=1)
def load_companies(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load companies snapshot into memory with caching.

    Data Loading Priority:
    1. Explicit path (if data_path provided)
    2. Package data: entityidentity/data/companies/ (~500 sample companies)
    3. Development data: tables/companies/ (full database, if built)

    Args:
        data_path: Optional path to companies database. If None, searches standard locations.

    Returns:
        DataFrame with company data

    Raises:
        FileNotFoundError: If no companies data found in any location

    See Also:
        DATA_LOCATIONS.md for detailed explanation of data directories
    """
    if data_path is None:
        # Priority 1: Package data (distributed with pip, always available)
        pkg_dir = Path(__file__).parent.parent
        data_dir = pkg_dir / "data" / "companies"
        for candidate in ["companies.parquet", "companies.csv"]:
            p = data_dir / candidate
            if p.exists():
                data_path = str(p)
                break

        # Priority 2: Development data (built locally, comprehensive)
        if data_path is None:
            tables_dir = pkg_dir.parent / "tables" / "companies"
            for candidate in ["companies.parquet", "companies.csv"]:
                p = tables_dir / candidate
                if p.exists():
                    data_path = str(p)
                    break

        # Not found in any location
        if data_path is None:
            raise FileNotFoundError(
                "No companies data found in standard locations.\n\n"
                "Searched:\n"
                f"  1. Package data: {data_dir}\n"
                f"  2. Development data: {tables_dir}\n\n"
                "To fix:\n"
                "  • For sample data (~500 companies):\n"
                "      python scripts/companies/update_companies_db.py --use-samples\n\n"
                "  • For full database (100K+ companies, 30-60 min):\n"
                "      python scripts/companies/update_companies_db.py\n\n"
                "See DATA_LOCATIONS.md for details on data organization."
            )

    path = Path(data_path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    if "name_norm" not in df.columns:
        df["name_norm"] = df["name"].map(normalize_company_name)

    for i in range(1, 6):
        col = f"alias{i}"
        if col not in df.columns:
            df[col] = None

    return df


def resolve_company(
    name: str,
    country: Optional[str] = None,
    address_hint: Optional[str] = None,
    use_llm_tiebreak: bool = False,
    llm_pick_fn: Optional[Callable] = None,
    k: int = 5,
    data_path: Optional[str] = None,
    high_conf_threshold: float = 88.0,
    high_conf_gap: float = 6.0,
    uncertain_threshold: float = 76.0,
) -> Dict[str, Any]:
    """Resolve company name to canonical entity with decision logic."""
    df = load_companies(data_path)

    query_norm = normalize_company_name(name)
    candidates = block_candidates(df, query_norm, country)
    scored = score_candidates(candidates, query_norm, country, k)

    result = {
        "query": {
            "name": name,
            "name_norm": query_norm,
            "country": country,
            "address_hint": address_hint,
        },
        "matches": [
            {
                "name": row["name"],
                "score": float(row["score"]),
                "country": row.get("country"),
                "lei": row.get("lei"),
                "wikidata_qid": row.get("wikidata_qid"),
                "aliases": [row.get(f"alias{i}") for i in range(1, 6) if pd.notna(row.get(f"alias{i}"))],
                "explain": {
                    "name_norm": row["name_norm"],
                    "country_match": bool(row.get("country_match", False)),
                    "has_lei": bool(row.get("has_lei", False)),
                    "score_primary": float(row.get("score_primary", 0)),
                    "score_alias": float(row.get("score_alias", 0)),
                },
            }
            for _, row in scored.head(k).iterrows()
        ],
        "final": None,
        "decision": "no_match",
    }

    if not result["matches"]:
        return result

    best_score = result["matches"][0]["score"]
    second_score = result["matches"][1]["score"] if len(result["matches"]) > 1 else 0.0
    gap = best_score - second_score

    if best_score >= high_conf_threshold and gap >= high_conf_gap:
        result["final"] = result["matches"][0]
        result["decision"] = "auto_high_conf"
        return result

    if uncertain_threshold <= best_score < high_conf_threshold:
        if use_llm_tiebreak and llm_pick_fn is not None:
            try:
                pick = llm_pick_fn(result["matches"], result["query"])
                result["final"] = pick or result["matches"][0]
                result["decision"] = "llm_tiebreak"
                return result
            except Exception:
                pass

    result["decision"] = "needs_hint_or_llm"
    return result


def match_company(name: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    result = resolve_company(name, country=country)
    return result.get("final")


def list_companies(
    country: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    data_path: Optional[str] = None,
) -> pd.DataFrame:
    df = load_companies(data_path=data_path)

    if country:
        df = df[df['country'] == country.upper()]
    if search:
        search_lower = search.lower()
        mask = (
            df['name'].str.lower().str.contains(search_lower, na=False) |
            df['name_norm'].str.contains(search_lower, na=False)
        )
        df = df[mask]
    if limit:
        df = df.head(limit)
    return df


__all__ = [
    "LEGAL_RE",
    "normalize_name",
    "load_companies",
    "resolve_company",
    "match_company",
    "list_companies",
]



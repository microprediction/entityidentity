"""Company name resolution and entity matching.

This module provides on-the-fly company name resolution using:
- Deterministic blocking and fuzzy scoring
- Optional LLM tie-breaking for ambiguous matches
- Aggressive caching for performance

Architecture: No database required for <300k companies. Load from Parquet/CSV.
"""

from __future__ import annotations
import re
import unicodedata
from functools import lru_cache
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

# Common legal suffixes across jurisdictions
LEGAL_SUFFIXES = (
    r"(incorporated|corporation|inc|corp|co|company|ltd|plc|sa|ag|gmbh|spa|oyj|kgaa|"
    r"sarl|s\.r\.o\.|pte|llc|lp|bv|nv|ab|as|oy|sas|s\.a\.|s\.p\.a\.|"
    r"limited|limitada|ltda|l\.l\.c\.|jsc|p\.l\.c\.)"
)
LEGAL_RE = re.compile(rf"\b{LEGAL_SUFFIXES}\b\.?", re.IGNORECASE)


def normalize_name(name: str) -> str:
    """Normalize company name for matching.
    
    Steps:
    1. Unicode normalization (NFKD)
    2. ASCII transliteration
    3. Lowercase
    4. Remove legal suffixes (before punctuation removal!)
    5. Remove punctuation (keep &, -, alphanumeric)
    6. Collapse whitespace
    
    Args:
        name: Raw company name
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    
    # Unicode normalization and ASCII conversion
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    
    # Lowercase
    name = name.lower()
    
    # Remove legal suffixes FIRST (while periods are still intact)
    # This allows patterns like "s.a." and "s.p.a." to match properly
    name = LEGAL_RE.sub("", name)
    
    # Remove punctuation except &, -, and alphanumeric
    name = re.sub(r"[^a-z0-9&\-\s]", " ", name)
    
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    
    return name


@lru_cache(maxsize=1)
def load_companies(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load companies snapshot into memory with caching.
    
    Expected columns:
    - name: Official company name
    - name_norm: Pre-normalized name (created if missing)
    - country: ISO2/3 country code
    - lei: Legal Entity Identifier (optional)
    - wikidata_qid: Wikidata Q-ID (optional)
    - aliases: List of alternate names (optional)
    - address: Full address (optional)
    
    Args:
        data_path: Path to companies.parquet or companies.csv
        
    Returns:
        DataFrame with company data
        
    Raises:
        ImportError: If pandas not installed
        FileNotFoundError: If data file not found
    """
    if pd is None:
        raise ImportError("pandas is required. Install with: pip install pandas")
    
    if data_path is None:
        # Look for companies data in tables/companies directory
        # Start from package root and go up to find project root
        pkg_dir = Path(__file__).parent.parent.parent  # Go up to project root
        tables_dir = pkg_dir / "tables" / "companies"
        
        for candidate in ["companies.parquet", "companies.csv"]:
            candidate_path = tables_dir / candidate
            if candidate_path.exists():
                data_path = str(candidate_path)
                break
        
        if data_path is None:
            raise FileNotFoundError(
                f"No companies data found in {tables_dir}. "
                f"Run: python scripts/companies/update_companies_db.py --use-samples"
            )
    
    # Load data
    path = Path(data_path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)
    
    # Ensure name_norm exists
    if "name_norm" not in df.columns:
        df["name_norm"] = df["name"].map(normalize_name)
    
    # Ensure aliases is a list
    if "aliases" not in df.columns:
        df["aliases"] = [[] for _ in range(len(df))]
    else:
        df["aliases"] = df["aliases"].apply(lambda x: x if isinstance(x, list) else [])
    
    return df


def block_candidates(
    df: pd.DataFrame, 
    query_norm: str, 
    country: Optional[str] = None,
    max_candidates: int = 50_000
) -> pd.DataFrame:
    """Filter candidates using cheap blocking strategies.
    
    Strategies:
    1. Country filter (if provided)
    2. First token prefix match (if query has 3+ char token)
    
    Args:
        df: Full companies DataFrame
        query_norm: Normalized query string
        country: Optional ISO2/3 country code
        max_candidates: Maximum candidates to return
        
    Returns:
        Filtered DataFrame of candidates
    """
    candidates = df
    
    # Country blocking
    if country:
        country_upper = country.upper()
        country_matches = candidates["country"].str.upper() == country_upper
        if country_matches.any():
            candidates = candidates[country_matches]
        # If no matches, fall back to all (maybe wrong country code)
    
    # First token blocking
    tokens = query_norm.split()
    if tokens and len(tokens[0]) >= 3:
        first_token = tokens[0]
        
        # Check name_norm starts with first token
        name_mask = candidates["name_norm"].str.startswith(first_token)
        
        # Check any alias starts with first token
        if "aliases" in candidates.columns:
            alias_mask = candidates["aliases"].apply(
                lambda aliases: any(
                    normalize_name(alias).startswith(first_token) 
                    for alias in aliases
                )
            )
            combined_mask = name_mask | alias_mask
        else:
            combined_mask = name_mask
        
        if combined_mask.any():
            candidates = candidates[combined_mask]
    
    # Limit size for performance
    return candidates.head(max_candidates)


def score_candidates(
    df: pd.DataFrame,
    query_norm: str,
    country: Optional[str] = None,
    k: int = 10
) -> pd.DataFrame:
    """Score candidates using RapidFuzz with boosts.
    
    Scoring:
    - Base: WRatio between query and name_norm
    - Alias boost: Best match among aliases
    - Country match: +2 points
    - Has LEI: +1 point
    
    Args:
        df: Candidates DataFrame
        query_norm: Normalized query string
        country: Optional country for match boost
        k: Number of top candidates to keep (minimum)
        
    Returns:
        DataFrame with scores, sorted by score descending
        
    Raises:
        ImportError: If rapidfuzz not installed
    """
    if fuzz is None or process is None:
        raise ImportError("rapidfuzz is required. Install with: pip install rapidfuzz")
    
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
    
    # Alias score: best alias match
    alias_scores = []
    for aliases in df["aliases"].tolist():
        best_alias_score = 0
        for alias in (aliases or []):
            alias_norm = normalize_name(alias)
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
    """Resolve company name to canonical entity.
    
    Decision logic:
    1. If best score >= 88 and gap to #2 >= 6: auto-accept (high confidence)
    2. If best score in [76, 88) and use_llm_tiebreak: call LLM
    3. Otherwise: return shortlist, needs disambiguation
    
    Args:
        name: Company name to resolve
        country: Optional ISO2/3 country code hint
        address_hint: Optional address for disambiguation (future)
        use_llm_tiebreak: Whether to use LLM for uncertain matches
        llm_pick_fn: Callable(candidates, query) -> selected_match
        k: Number of matches to return
        data_path: Optional path to companies data
        high_conf_threshold: Minimum score for auto-accept (default 88.0)
        high_conf_gap: Minimum gap to #2 for auto-accept (default 6.0)
        uncertain_threshold: Minimum score for LLM tiebreak (default 76.0)
        
    Returns:
        Dictionary with:
        - query: Original query data
        - matches: List of top K matches with scores
        - final: Selected match (if confident)
        - decision: Decision type (auto_high_conf, llm_tiebreak, needs_hint_or_llm)
        
    Example:
        >>> result = resolve_company("Apple Inc", country="US")
        >>> result["final"]["name"]
        'Apple Inc.'
        >>> result["decision"]
        'auto_high_conf'
    """
    # Load companies
    df = load_companies(data_path)
    
    # Normalize query
    query_norm = normalize_name(name)
    
    # Block candidates
    candidates = block_candidates(df, query_norm, country)
    
    # Score candidates
    scored = score_candidates(candidates, query_norm, country, k)
    
    # Build result structure
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
                "aliases": row.get("aliases", []),
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
    
    # Decision logic
    best_score = result["matches"][0]["score"]
    second_score = result["matches"][1]["score"] if len(result["matches"]) > 1 else 0.0
    gap = best_score - second_score
    
    # High confidence: auto-accept
    if best_score >= high_conf_threshold and gap >= high_conf_gap:
        result["final"] = result["matches"][0]
        result["decision"] = "auto_high_conf"
        return result
    
    # Uncertain band: try LLM tie-break
    if uncertain_threshold <= best_score < high_conf_threshold:
        if use_llm_tiebreak and llm_pick_fn is not None:
            try:
                pick = llm_pick_fn(result["matches"], result["query"])
                result["final"] = pick or result["matches"][0]
                result["decision"] = "llm_tiebreak"
                return result
            except Exception:
                # Fall through if LLM fails
                pass
    
    # Low confidence or LLM not available: return shortlist
    result["decision"] = "needs_hint_or_llm"
    return result


# Convenience function for simple usage
def match_company(name: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Simple interface: return best match or None.
    
    Args:
        name: Company name to match
        country: Optional country code
        
    Returns:
        Match dict or None if no confident match
    """
    result = resolve_company(name, country=country)
    return result.get("final")


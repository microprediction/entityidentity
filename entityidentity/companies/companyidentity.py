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
        # Look for companies data in package data directory
        # This works both in development and when installed from PyPI
        pkg_dir = Path(__file__).parent.parent  # entityidentity package root
        data_dir = pkg_dir / "data" / "companies"
        
        # Try package data directory first (works when installed)
        for candidate in ["companies.parquet", "companies.csv"]:
            candidate_path = data_dir / candidate
            if candidate_path.exists():
                data_path = str(candidate_path)
                break
        
        # Fall back to tables/companies for development
        if data_path is None:
            tables_dir = pkg_dir.parent / "tables" / "companies"
            for candidate in ["companies.parquet", "companies.csv"]:
                candidate_path = tables_dir / candidate
                if candidate_path.exists():
                    data_path = str(candidate_path)
                    break
        
        if data_path is None:
            raise FileNotFoundError(
                f"No companies data found.\n"
                f"Tried:\n"
                f"  - {data_dir}/companies.{{parquet,csv}}\n"
                f"  - {tables_dir}/companies.{{parquet,csv}}\n"
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
    
    # Ensure alias columns exist (flat structure instead of lists)
    for i in range(1, 6):  # alias1 through alias5
        col = f"alias{i}"
        if col not in df.columns:
            df[col] = None
    
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
    
    # Alias score: best alias match (alias1-alias5)
    alias_scores = []
    for idx in range(len(df)):
        best_alias_score = 0
        row = df.iloc[idx]
        for i in range(1, 6):
            alias_col = f"alias{i}"
            if alias_col in df.columns:
                alias = row[alias_col]
                if pd.notna(alias):
                    alias_norm = normalize_name(str(alias))
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
        country: Optional country code (e.g., "US", "GB") - helps improve accuracy
        
    Returns:
        Match dict or None if no confident match
        
    Note:
        Country is optional but recommended. When provided, it:
        - Filters candidates to that country (faster)
        - Boosts match scores for same-country matches
        - Reduces false positives from similar names in different countries
    """
    result = resolve_company(name, country=country)
    return result.get("final")


def list_companies(
    country: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    data_path: Optional[str] = None,
) -> pd.DataFrame:
    """List companies from the database with optional filtering.
    
    Args:
        country: Optional country code to filter by (e.g., "US", "GB")
        search: Optional search term to filter company names (case-insensitive)
        limit: Optional maximum number of companies to return
        data_path: Optional path to companies data file
        
    Returns:
        DataFrame with company data
        
    Examples:
        >>> # List all companies
        >>> companies = list_companies()
        
        >>> # List US companies
        >>> us_companies = list_companies(country="US")
        
        >>> # Search for mining companies
        >>> mining = list_companies(search="mining")
        
        >>> # Get top 10 Australian companies
        >>> top_au = list_companies(country="AU", limit=10)
    """
    df = load_companies(data_path=data_path)
    
    # Filter by country
    if country:
        df = df[df['country'] == country.upper()]
    
    # Filter by search term
    if search:
        search_lower = search.lower()
        # Search in name and normalized name
        mask = (
            df['name'].str.lower().str.contains(search_lower, na=False) |
            df['name_norm'].str.contains(search_lower, na=False)
        )
        df = df[mask]
    
    # Apply limit
    if limit:
        df = df.head(limit)
    
    return df


def extract_companies(
    text: str,
    country_hint: Optional[str] = None,
    min_confidence: float = 0.75,
    data_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract company mentions from text and resolve to canonical identifiers.
    
    This function:
    1. Identifies potential company names in the text (capitalized phrases, legal suffixes)
    2. Infers country context from the text if not provided
    3. Attempts to match each candidate to the company database
    4. Returns matches above the confidence threshold
    
    Args:
        text: Text to extract companies from
        country_hint: Optional country code to prioritize (e.g., "US", "GB")
        min_confidence: Minimum match score to include (0.0-1.0, default 0.75)
        data_path: Optional path to companies data file
        
    Returns:
        List of matched company dictionaries with keys:
        - mention: Original text mention
        - name: Canonical company name
        - country: Company country
        - lei: Legal Entity Identifier (if available)
        - score: Match confidence score
        - context: Surrounding text snippet
        
    Examples:
        >>> text = "Apple and Microsoft are leaders in tech. BHP operates in Australia."
        >>> companies = extract_companies(text)
        >>> for co in companies:
        ...     print(f"{co['mention']} -> {co['name']} ({co['country']})")
        Apple -> Apple Inc. (US)
        Microsoft -> Microsoft Corporation (US)
        BHP -> BHP Group Limited (AU)
    """
    if not text:
        return []
    
    # Country name to code mapping
    COUNTRY_NAMES = {
        'united states': 'US', 'usa': 'US', 'america': 'US', 'american': 'US',
        'united kingdom': 'GB', 'uk': 'GB', 'britain': 'GB', 'british': 'GB',
        'australia': 'AU', 'australian': 'AU',
        'canada': 'CA', 'canadian': 'CA',
        'germany': 'DE', 'german': 'DE',
        'france': 'FR', 'french': 'FR',
        'japan': 'JP', 'japanese': 'JP',
        'china': 'CN', 'chinese': 'CN',
        'india': 'IN', 'indian': 'IN',
        'brazil': 'BR', 'brazilian': 'BR',
        'south africa': 'ZA',
        'switzerland': 'CH', 'swiss': 'CH',
        'netherlands': 'NL', 'dutch': 'NL',
        'sweden': 'SE', 'swedish': 'SE',
        'norway': 'NO', 'norwegian': 'NO',
        'denmark': 'DK', 'danish': 'DK',
        'spain': 'ES', 'spanish': 'ES',
        'italy': 'IT', 'italian': 'IT',
    }
    
    # Infer country from text if not provided
    inferred_countries = []
    if not country_hint:
        text_lower = text.lower()
        for country_name, code in COUNTRY_NAMES.items():
            if country_name in text_lower:
                inferred_countries.append(code)
        # Use most common inferred country if found
        if inferred_countries:
            country_hint = max(set(inferred_countries), key=inferred_countries.count)
    
    # Extract potential company names
    # Look for:
    # 1. Capitalized phrases (2-6 words)
    # 2. Phrases with legal suffixes (Inc., Ltd, Corp, etc.)
    # 3. Single capitalized words that might be brand names
    
    candidates = []
    
    # Pattern 1: Phrases with legal suffixes
    legal_pattern = re.compile(
        r'\b([A-Z][A-Za-z0-9&\-]+(?:\s+[A-Z][A-Za-z0-9&\-]+)*)\s+(Inc\.?|Ltd\.?|Corp\.?|Corporation|Limited|Company|plc|LLC|L\.L\.C\.)\b',
        re.IGNORECASE
    )
    for match in legal_pattern.finditer(text):
        full_match = match.group(0)
        start = match.start()
        end = match.end()
        context = text[max(0, start-30):min(len(text), end+30)]
        candidates.append({
            'mention': full_match.strip(),
            'start': start,
            'end': end,
            'context': context.strip()
        })
    
    # Pattern 2: Capitalized phrases (2-4 consecutive capitalized words)
    cap_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b')
    for match in cap_pattern.finditer(text):
        mention = match.group(0)
        start = match.start()
        end = match.end()
        
        # Skip if already captured by legal suffix pattern
        if any(c['start'] <= start < c['end'] or c['start'] < end <= c['end'] for c in candidates):
            continue
        
        # Skip common words that aren't companies
        skip_words = {'The', 'This', 'That', 'These', 'Those', 'There', 'When', 'Where', 'What', 'Which'}
        if mention.split()[0] in skip_words:
            continue
        
        context = text[max(0, start-30):min(len(text), end+30)]
        candidates.append({
            'mention': mention,
            'start': start,
            'end': end,
            'context': context.strip()
        })
    
    # Deduplicate overlapping candidates (keep longer ones)
    filtered_candidates = []
    for candidate in sorted(candidates, key=lambda x: (x['start'], -(x['end'] - x['start']))):
        if not any(
            c['start'] <= candidate['start'] < c['end'] or 
            c['start'] < candidate['end'] <= c['end']
            for c in filtered_candidates
        ):
            filtered_candidates.append(candidate)
    
    # Try to match each candidate
    results = []
    seen = set()  # Avoid duplicates
    
    for candidate in filtered_candidates:
        mention = candidate['mention']
        
        # Try to match with country hint
        result = resolve_company(mention, country=country_hint, data_path=data_path)
        
        if result['final'] and result['final']['score'] >= min_confidence:
            company = result['final']
            
            # Deduplicate by company name
            if company['name'] in seen:
                continue
            seen.add(company['name'])
            
            results.append({
                'mention': mention,
                'name': company['name'],
                'country': company.get('country'),
                'lei': company.get('lei'),
                'wikidata_qid': company.get('wikidata_qid'),
                'score': company['score'],
                'context': candidate['context'],
                'decision': result['decision'],
            })
    
    # Sort by position in text
    results.sort(key=lambda x: text.index(x['mention']))
    
    return results


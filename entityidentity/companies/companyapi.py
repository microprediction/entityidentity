"""Clean, user-facing API for company resolution.

This module provides a simple interface to company identity resolution.
Implementation details are in the helper modules.
"""

from typing import List, Optional, Dict, Any
import pandas as pd

from entityidentity.companies.companyidentity import (
    normalize_name as _normalize_name,
    resolve_company as _resolve_company,
    load_companies as _load_companies,
)


def normalize_name(name: str) -> str:
    """Normalize company name for matching.
    
    Args:
        name: Company name to normalize
        
    Returns:
        Normalized string (lowercase, no punctuation, legal suffixes removed)
    """
    return _normalize_name(name)


def match_company(name: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find best matching company or None.
    
    Args:
        name: Company name to match
        country: Optional country code (e.g., "US", "GB") - improves accuracy
        
    Returns:
        Company dict with name, country, lei, etc. or None if no confident match
    """
    result = _resolve_company(name, country=country)
    return result.get("final")


def resolve_company(name: str, country: Optional[str] = None) -> Dict[str, Any]:
    """Resolve company with full details and match scores.
    
    Args:
        name: Company name to resolve
        country: Optional country code hint
        
    Returns:
        Dict with 'final' (best match), 'decision' (how matched), 'matches' (all candidates)
    """
    return _resolve_company(name, country=country)


def list_companies(
    country: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """List companies with optional filtering.
    
    Args:
        country: Filter by country code (e.g., "US", "GB")
        search: Search term for company names
        limit: Maximum number of results
        
    Returns:
        DataFrame with company data
        
    Examples:
        >>> list_companies(country="US")
        >>> list_companies(search="mining")
        >>> list_companies(country="AU", limit=10)
    """
    df = _load_companies()
    
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


def extract_companies(
    text: str,
    country_hint: Optional[str] = None,
    min_confidence: float = 0.75,
) -> List[Dict[str, Any]]:
    """Extract company mentions from text.
    
    Identifies company names in text, infers country context, and resolves
    to canonical company identifiers.
    
    Args:
        text: Text to extract companies from
        country_hint: Optional country code to prioritize
        min_confidence: Minimum match score (0.0-1.0, default 0.75)
        
    Returns:
        List of dicts with 'mention', 'name', 'country', 'lei', 'score', 'context'
        
    Examples:
        >>> text = "Apple and Microsoft lead tech. BHP operates in Australia."
        >>> companies = extract_companies(text)
        >>> for co in companies:
        ...     print(f"{co['mention']} -> {co['name']} ({co['country']})")
    """
    from entityidentity.companies.companyextractor import extract_companies_from_text
    return extract_companies_from_text(text, country_hint, min_confidence)


def get_company_id(company: Dict[str, Any], safe: bool = False) -> str:
    """Get a consistent, human-readable identifier for a company.
    
    Returns "name:country" - readable, unique, and terse.
    Company names are unique within each country in our database.
    
    Args:
        company: Company dict with 'name' and 'country'
        safe: If True, return database/filesystem-safe identifier (replaces special chars with _)
        
    Returns:
        Identifier string in format "name:country" (average ~22 chars)
        
    Examples:
        >>> company = {'name': 'Apple Inc', 'country': 'US'}
        >>> get_company_id(company)
        'Apple Inc:US'
        
        >>> company = {'name': 'AT&T Corporation', 'country': 'US'}
        >>> get_company_id(company)
        'AT&T Corporation:US'
        >>> get_company_id(company, safe=True)
        'AT_T_Corporation_US'
        
    Note:
        - Use safe=True for SQL table names, file names, or URLs
        - LEI is available in company['lei'] for ~23% of companies
    """
    name = company.get('name', 'Unknown')
    country = company.get('country', 'XX')
    
    if safe:
        # Replace all non-alphanumeric chars with underscore for database/filesystem safety
        import re
        safe_name = re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')
        return f"{safe_name}_{country}"
    
    return f"{name}:{country}"


__all__ = [
    "normalize_name",
    "match_company",
    "resolve_company",
    "list_companies",
    "extract_companies",
    "get_company_id",
]


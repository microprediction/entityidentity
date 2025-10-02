"""Clean, user-facing API for company resolution.

This module provides a simple interface to company identity resolution.
Implementation details are in the helper modules.
"""

from typing import List, Optional, Dict, Any, Tuple
import pandas as pd

from entityidentity.companies.companynormalize import (
    normalize_company_name as _normalize_company_name,
    canonicalize_company_name as _canonicalize_company_name,
)
from entityidentity.companies.companyresolver import (
    resolve_company,
    load_companies,
    list_companies,
)


def company_identifier(name: str, country: Optional[str] = None) -> Optional[str]:
    """Get canonical global identifier for a company.
    
    This is the main entry point for company entity resolution.
    Takes any variation of a company name and returns a stable, globally unique identifier.
    
    Args:
        name: Company name in any format (e.g., "MSFT", "Microsoft Corp", "Microsoft")
        country: Optional country code hint (e.g., "US", "GB") - improves accuracy
        
    Returns:
        Canonical identifier string in format "name:country" (e.g., "Microsoft Corporation:US")
        Returns None if no confident match found
        
    Examples:
        >>> company_identifier("Apple")
        'Apple Inc:US'
        
        >>> company_identifier("BHP", country="AU")
        'BHP Group Limited:AU'
        
        >>> company_identifier("Anglo American")
        'Anglo American plc:GB'
    """
    result = resolve_company(name, country=country)
    final = result.get("final")
    
    if final:
        return get_company_id(final)
    return None


# Alias for backwards compatibility
get_identifier = company_identifier


def normalize_company_name(name: str) -> str:
    """Normalize company name for fuzzy matching.

    This function performs aggressive normalization for matching purposes:
    - Converts to lowercase
    - Removes legal suffixes (Inc, Corp, Ltd, etc.)
    - Removes punctuation
    - Normalizes whitespace

    Args:
        name: Company name to normalize

    Returns:
        Normalized string for matching (lowercase, simplified)

    Examples:
        >>> normalize_company_name("Apple Inc.")
        'apple'
        >>> normalize_company_name("AT&T Corporation")
        'at&t'

    Note:
        For display/identifier purposes, use canonicalize_company_name() instead.
    """
    return _normalize_company_name(name)


def canonicalize_company_name(name: str) -> str:
    """Canonicalize company name for display and identifiers.

    This function preserves readability while making names safe for identifiers:
    - Preserves case (Apple Inc, not APPLE INC)
    - Removes problematic punctuation
    - Normalizes legal suffixes
    - Converts unicode to ASCII

    Args:
        name: Company name to canonicalize

    Returns:
        Canonicalized name safe for identifiers (preserves case)

    Examples:
        >>> canonicalize_company_name("Apple, Inc.")
        'Apple Inc'
        >>> canonicalize_company_name("Société Générale")
        'Societe Generale'

    Note:
        For fuzzy matching, use normalize_company_name() instead.
    """
    return _canonicalize_company_name(name)


# Deprecated alias - kept for backwards compatibility
def normalize_name(name: str) -> str:
    """Normalize company name for matching.

    DEPRECATED: Use normalize_company_name() instead.
    This alias will be removed in v1.0.0.

    Args:
        name: Company name to normalize

    Returns:
        Normalized string (lowercase, no punctuation, legal suffixes removed)
    """
    import warnings
    warnings.warn(
        "normalize_name() is deprecated and will be removed in v1.0.0. "
        "Use normalize_company_name() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _normalize_company_name(name)


def match_company(name: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find best matching company or None.
    
    Args:
        name: Company name to match
        country: Optional country code (e.g., "US", "GB") - improves accuracy
        
    Returns:
        Company dict with name, country, lei, etc. or None if no confident match
    """
    result = resolve_company(name, country=country)
    return result.get("final")






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
    "company_identifier",         # Primary API
    "get_identifier",            # Alias for backwards compatibility
    "normalize_company_name",    # Primary normalization function
    "canonicalize_company_name", # Primary canonicalization function
    "normalize_name",            # Deprecated alias (backwards compatibility)
    "match_company",
    "resolve_company",
    "list_companies",
    "extract_companies",
    "get_company_id",
]


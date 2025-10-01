"""Country entity resolution API.

Simple wrapper around the robust fuzzycountry implementation.
This provides a clean, simple API for users who just want ISO2 codes.
"""

from typing import Optional, Iterable, List

# Import robust implementation from fuzzycountry
from entityidentity.countries.fuzzycountry import (
    country_identifier as _country_identifier,
    country_identifiers as _country_identifiers,
)


def country_identifier(name: str) -> Optional[str]:
    """Get canonical ISO identifier for a country.
    
    Resolves country names, codes, and common variations to ISO 3166-1 alpha-2 codes.
    
    Uses a robust multi-stage pipeline:
    1. country_converter (handles many aliases)
    2. pycountry (official ISO 3166)
    3. Manual alias catalog (England, Holland, etc.)
    4. Fuzzy matching with RapidFuzz (typo tolerance)
    
    Args:
        name: Country name or code in any format (e.g., "USA", "United States", "US")
        
    Returns:
        ISO 3166-1 alpha-2 code (e.g., "US") or None if not recognized
        
    Examples:
        >>> country_identifier("United States")
        'US'
        
        >>> country_identifier("USA")
        'US'
        
        >>> country_identifier("America")
        'US'
        
        >>> country_identifier("United Kingdom")
        'GB'
        
        >>> country_identifier("UK")
        'GB'
        
        >>> country_identifier("England")
        'GB'
        
        >>> country_identifier("Holland")
        'NL'
        
        >>> country_identifier("Untied States")  # Typo
        'US'
    """
    return _country_identifier(name, to='ISO2')


def country_identifiers(names: Iterable[str]) -> List[Optional[str]]:
    """Batch resolve country names to ISO 3166-1 alpha-2 codes.
    
    Args:
        names: Iterable of country names or codes
        
    Returns:
        List of ISO 3166-1 alpha-2 codes (or None for unrecognized names)
        
    Examples:
        >>> country_identifiers(["USA", "Holland", "England"])
        ['US', 'NL', 'GB']
    """
    return _country_identifiers(names, to='ISO2')


__all__ = [
    "country_identifier",
    "country_identifiers",
]


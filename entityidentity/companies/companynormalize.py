"""Company name normalization for canonical identifiers.

This module provides robust normalization to ensure company names can
be safely used in identifiers without special character conflicts.
"""

import re
import unicodedata


def canonicalize_name(name: str) -> str:
    """Canonicalize company name for DISPLAY and IDENTIFIERS.

    This function preserves readability while ensuring names are safe for identifiers.
    Use this for: display names, database identifiers, user-facing output.
    DO NOT use this for: fuzzy matching or deduplication.

    For matching/deduplication, use companyidentity.normalize_name()

    Ensures the name is safe to use in the identifier format "name:country"
    by removing/normalizing special characters that could cause parsing issues.

    Rules:
    1. Remove commas before legal suffixes ("Tesla, Inc." -> "Tesla Inc")
    2. Remove periods from legal suffixes ("Inc." -> "Inc")
    3. Normalize unicode to ASCII
    4. Keep only: letters, numbers, spaces, hyphens, ampersands
    5. Collapse multiple spaces
    6. Trim whitespace
    7. PRESERVES CASE (unlike normalize_name which lowercases)

    Args:
        name: Original company name

    Returns:
        Canonicalized name safe for use in identifiers (preserves case)

    Examples:
        >>> canonicalize_name("Apple Inc.")
        'Apple Inc'
        >>> canonicalize_name("Tesla, Inc.")
        'Tesla Inc'
        >>> canonicalize_name("AT&T Corp.")
        'AT&T Corp'
        >>> canonicalize_name("Société Générale")
        'Societe Generale'
    """
    if not name:
        return name
    
    # Step 1: Remove comma before legal suffixes
    # "Tesla, Inc." -> "Tesla Inc."
    name = re.sub(
        r',\s+(Inc\.?|Corp\.?|Corporation\.?|Ltd\.?|Limited\.?|LLC\.?|L\.L\.C\.?|plc\.?|S\.A\.?|S\.p\.A\.?)',
        r' \1',
        name,
        flags=re.IGNORECASE
    )
    
    # Step 2: Remove periods from legal suffixes
    # "Apple Inc." -> "Apple Inc"
    # "Corp." -> "Corp"
    name = re.sub(
        r'\b(Inc|Corp|Corporation|Ltd|Limited|LLC|L\.L\.C|plc|S\.A|S\.p\.A)\.',
        r'\1',
        name,
        flags=re.IGNORECASE
    )
    
    # Step 3: Unicode normalization to ASCII
    # "Société" -> "Societe"
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    
    # Step 4: Keep only safe characters
    # Keep: letters, numbers, spaces, hyphens, ampersands
    # Remove/replace everything else
    name = re.sub(r'[^A-Za-z0-9\s\-&]', ' ', name)
    
    # Step 5: Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Step 6: Trim
    name = name.strip()
    
    return name


def validate_canonical_name(name: str) -> bool:
    """Validate that a name is safe for use in identifiers.
    
    Args:
        name: Name to validate
        
    Returns:
        True if name contains only safe characters
    """
    if not name:
        return False
    
    # Only allow: letters, numbers, spaces, hyphens, ampersands
    return bool(re.match(r'^[A-Za-z0-9\s\-&]+$', name))


__all__ = ['canonicalize_name', 'validate_canonical_name']


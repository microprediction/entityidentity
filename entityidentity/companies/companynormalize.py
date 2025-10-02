"""Company name normalization utilities.

Contains two complementary utilities:
- canonicalize_name: for safe identifier strings (keep case & readability)
- normalize_name: for fuzzy matching (lowercased, simplified)
"""

import re
import unicodedata


def canonicalize_company_name(name: str) -> str:
    """Canonicalize company name for DISPLAY and IDENTIFIERS.

    This function preserves readability while ensuring names are safe for identifiers.
    Use this for: display names, database identifiers, user-facing output.
    DO NOT use this for: fuzzy matching or deduplication.

    For matching/deduplication, use normalize_company_name()

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


# Common legal suffixes across jurisdictions (for normalize_name)
LEGAL_SUFFIXES = (
    r"(incorporated|corporation|inc|corp|co|company|ltd|plc|sa|ag|gmbh|spa|oyj|kgaa|"
    r"sarl|s\.r\.o\.|pte|llc|lp|bv|nv|ab|as|oy|sas|s\.a\.|s\.p\.a\.|"
    r"limited|limitada|ltda|l\.l\.c\.|jsc|p\.l\.c\.)"
)
LEGAL_RE = re.compile(rf"\b{LEGAL_SUFFIXES}\b\.?", re.IGNORECASE)


def normalize_company_name(name: str) -> str:
    """Normalize company name for fuzzy matching.
    
    Steps:
    1. Unicode normalization (NFKD) and ASCII transliteration
    2. Lowercase
    3. Remove legal suffixes (before punctuation removal)
    4. Remove punctuation (keep &, -, alphanumeric)
    5. Collapse whitespace
    """
    if not name:
        return ""
    # Unicode normalization and ASCII conversion
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    name = name.lower()
    # Remove legal suffixes first
    name = LEGAL_RE.sub("", name)
    # Remove punctuation except &, -, and alphanumeric
    name = re.sub(r"[^a-z0-9&\-\s]", " ", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


import warnings
from functools import wraps
from typing import Callable


def _deprecated_alias(original_func: Callable, new_name: str) -> Callable:
    """Create a deprecated alias for a function."""
    @wraps(original_func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{wrapper.__name__} is deprecated and will be removed in v1.0.0. "
            f"Use {new_name} instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return original_func(*args, **kwargs)
    return wrapper


__all__ = [
    # Primary functions (use these)
    'canonicalize_company_name',
    'normalize_company_name',
    'validate_canonical_name',
    'LEGAL_RE',
    # Deprecated aliases (for backwards compatibility)
    'canonicalize_name',
    'normalize_name',
]

# Deprecated aliases with warnings
canonicalize_name = _deprecated_alias(canonicalize_company_name, 'canonicalize_company_name')
canonicalize_name.__name__ = 'canonicalize_name'
canonicalize_name.__doc__ = """DEPRECATED: Use canonicalize_company_name() instead.

This function will be removed in v1.0.0.
"""

normalize_name = _deprecated_alias(normalize_company_name, 'normalize_company_name')
normalize_name.__name__ = 'normalize_name'
normalize_name.__doc__ = """DEPRECATED: Use normalize_company_name() instead.

This function will be removed in v1.0.0.
"""


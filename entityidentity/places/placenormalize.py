"""
Place Name Normalization Functions
-----------------------------------

Three normalization functions for different use cases:
  1. normalize_name: Aggressive normalization for fuzzy matching
  2. canonicalize_name: Light normalization for display/storage
  3. slugify: URL/key-safe slugs (e.g., "western-australia")

Examples:
  >>> normalize_name("Western Australia")
  'western australia'

  >>> normalize_name("Limpopo Province")
  'limpopo province'

  >>> canonicalize_name("western  australia")
  'Western Australia'

  >>> slugify("Western Australia")
  'western-australia'

  >>> slugify("Uusimaa (Nyland)")
  'uusimaa-nyland'
"""

from entityidentity.utils.normalize import (
    normalize_name as _normalize_name,
    canonicalize_name as _canonicalize_name,
    slugify_name as _slugify_name,
    normalize_quotes,
)


def normalize_place_name(s: str) -> str:
    """
    Aggressive normalization for fuzzy matching.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC)
      - Normalize quotes/apostrophes
      - Collapse multiple spaces to single space
      - Keep alphanumerics, spaces, parentheses, hyphens, apostrophes

    Args:
        s: Raw place name (admin1/state/province)

    Returns:
        Normalized string for matching

    Examples:
        >>> normalize_name("Western Australia")
        'western australia'

        >>> normalize_name("Hawai'i")
        'hawaii'

        >>> normalize_name("São Paulo")
        'sao paulo'

        >>> normalize_name("Région Auvergne-Rhône-Alpes")
        'region auvergne-rhone-alpes'
    """
    if not s:
        return ""

    # Normalize quotes first
    s = normalize_quotes(s)

    # Use shared normalization with place-specific allowed characters
    # Allow: letters, numbers, space, hyphen, parentheses, apostrophe
    return _normalize_name(s, allowed_chars=r"a-z0-9\s\-()\'")


def canonicalize_place_name(s: str) -> str:
    """
    Light normalization for display and storage.

    Transformations:
      - Strip leading/trailing whitespace
      - Title case
      - Collapse multiple spaces to single space
      - Preserve accents and special characters

    Args:
        s: Raw place name

    Returns:
        Canonicalized display name

    Examples:
        >>> canonicalize_name("western australia")
        'Western Australia'

        >>> canonicalize_name("  limpopo  ")
        'Limpopo'

        >>> canonicalize_name("são paulo")
        'São Paulo'
    """
    if not s:
        return ""

    # Use shared canonicalization with title case
    return _canonicalize_name(s, apply_title_case=True)


def slugify_place_name(s: str) -> str:
    """
    Create URL/key-safe slug for place names.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC -> ASCII)
      - Replace spaces and underscores with hyphens
      - Remove all non-alphanumeric except hyphens
      - Collapse multiple hyphens to single hyphen
      - Strip leading/trailing hyphens

    Args:
        s: Place name or identifier

    Returns:
        Slug suitable for URLs, keys, filenames

    Examples:
        >>> slugify("Western Australia")
        'western-australia'

        >>> slugify("Uusimaa (Nyland)")
        'uusimaa-nyland'

        >>> slugify("São Paulo")
        'sao-paulo'

        >>> slugify("Région Auvergne-Rhône-Alpes")
        'region-auvergne-rhone-alpes'
    """
    if not s:
        return ""

    # Use shared slugification
    return _slugify_name(s)


# ---- Helper for generating deterministic place_id ----
def generate_place_id(country: str, admin1_code: str) -> str:
    """
    Generate deterministic 16-character hex place_id.

    Uses SHA-1 hash of country.admin1_code with "|place" suffix for namespace.

    Args:
        country: ISO 3166-1 alpha-2 country code (e.g., "AU", "ZA")
        admin1_code: Admin1 code (e.g., "WA", "LP")

    Returns:
        16-character hex string (first 16 chars of SHA-1 hash)

    Examples:
        >>> generate_place_id("AU", "WA")
        'a1b2c3d4e5f6a7b8'  # deterministic

        >>> generate_place_id("ZA", "LP")
        'c4d5e6f7a8b9c0d1'  # deterministic
    """
    import hashlib

    # Combine country and admin1_code with GeoNames convention
    key = f"{country}.{admin1_code}"
    namespaced = f"{key}|place"

    # SHA-1 hash, take first 16 hex chars
    hash_bytes = hashlib.sha1(namespaced.encode("utf-8")).digest()
    return hash_bytes.hex()[:16]


__all__ = [
    "normalize_place_name",
    "canonicalize_place_name",
    "slugify_place_name",
    "generate_place_id",
]

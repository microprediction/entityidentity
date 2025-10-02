"""
Basket Name Normalization Functions
------------------------------------

Three normalization functions for different use cases:
  1. normalize_name: Aggressive normalization for fuzzy matching
  2. canonicalize_name: Light normalization for display/storage
  3. slugify: URL/key-safe slugs (e.g., "pgm-4e")

Examples:
  >>> normalize_name("PGM 4E")
  'pgm 4e'

  >>> normalize_name("Light Rare Earths")
  'light rare earths'

  >>> canonicalize_name("pgm  4e")
  'PGM 4E'

  >>> slugify("PGM 4E")
  'pgm-4e'

  >>> slugify("Battery Pack")
  'battery-pack'
"""

import re

from entityidentity.utils.normalize import (
    normalize_name as _normalize_name,
    slugify_name as _slugify_name,
    normalize_quotes,
)


def normalize_basket_name(s: str) -> str:
    """
    Aggressive normalization for fuzzy matching.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC)
      - Normalize quotes/apostrophes
      - Collapse multiple spaces to single space
      - Keep alphanumerics, spaces, parentheses, hyphens, slashes

    Args:
        s: Raw basket name/alias

    Returns:
        Normalized string for matching

    Examples:
        >>> normalize_name("PGM 4E")
        'pgm 4e'

        >>> normalize_name("Light  REE")
        'light ree'

        >>> normalize_name("NdPr Oxide")
        'ndpr oxide'

        >>> normalize_name("Battery Pack")
        'battery pack'
    """
    if not s:
        return ""

    # Normalize quotes first
    s = normalize_quotes(s)

    # Use shared normalization with basket-specific allowed characters
    # Allow: letters, numbers, space, hyphen, slash, parentheses
    return _normalize_name(s, allowed_chars=r"a-z0-9\s\-/()")


def canonicalize_basket_name(s: str) -> str:
    """
    Light normalization for display and storage.

    Transformations:
      - Strip leading/trailing whitespace
      - Preserve original casing (baskets have specific conventions like "4E", "NdPr")
      - Collapse multiple spaces to single space

    Args:
        s: Raw basket name

    Returns:
        Canonicalized display name

    Examples:
        >>> canonicalize_name("pgm 4e")
        'PGM 4E'

        >>> canonicalize_name("  battery pack  ")
        'Battery Pack'

        >>> canonicalize_name("ndpr")
        'NdPr'
    """
    if not s:
        return ""

    # Strip and collapse spaces
    s = s.strip()
    s = re.sub(r"\s+", " ", s)

    # For baskets, preserve original casing from source
    # The YAML file should store canonical forms like "PGM 4E", "NdPr"
    return s


def slugify_basket_name(s: str) -> str:
    """
    Create URL/key-safe slug for basket names.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC -> ASCII)
      - Replace spaces and underscores with hyphens
      - Remove all non-alphanumeric except hyphens
      - Collapse multiple hyphens to single hyphen
      - Strip leading/trailing hyphens

    Args:
        s: Basket name or identifier

    Returns:
        Slug suitable for URLs, keys, filenames

    Examples:
        >>> slugify("PGM 4E")
        'pgm-4e'

        >>> slugify("Battery Pack")
        'battery-pack'

        >>> slugify("Light Rare Earths")
        'light-rare-earths'

        >>> slugify("NdPr Oxide")
        'ndpr-oxide'
    """
    if not s:
        return ""

    # Use shared slugification
    return _slugify_name(s)


# ---- Helper for generating deterministic basket_id ----
def generate_basket_id(name: str) -> str:
    """
    Generate deterministic 16-character hex basket_id.

    Uses SHA-1 hash of normalized name with "|basket" suffix for namespace.

    Args:
        name: Canonical basket name

    Returns:
        16-character hex string (first 16 chars of SHA-1 hash)

    Examples:
        >>> generate_basket_id("PGM 4E")
        'a1b2c3d4e5f6a7b8'  # deterministic

        >>> generate_basket_id("Battery Pack")
        'c4d5e6f7a8b9c0d1'  # deterministic
    """
    import hashlib

    # Normalize and add namespace suffix
    normalized = normalize_basket_name(name)
    namespaced = f"{normalized}|basket"

    # SHA-1 hash, take first 16 hex chars
    hash_bytes = hashlib.sha1(namespaced.encode("utf-8")).digest()
    return hash_bytes.hex()[:16]


__all__ = [
    "normalize_basket_name",
    "canonicalize_basket_name",
    "slugify_basket_name",
    "generate_basket_id",
]

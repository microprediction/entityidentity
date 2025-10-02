"""
Metal Name Normalization Functions
-----------------------------------

Three normalization functions for different use cases:
  1. normalize_name: Aggressive normalization for fuzzy matching
  2. canonicalize_name: Light normalization for display/storage
  3. slugify: URL/key-safe slugs (e.g., "lithium-carbonate")

Examples:
  >>> normalize_name("Lithium Carbonate")
  'lithium carbonate'

  >>> normalize_name("APT 88.5%")
  'apt 88.5%'

  >>> canonicalize_name("lithium  carbonate")
  'Lithium Carbonate'

  >>> slugify("Lithium Carbonate")
  'lithium-carbonate'

  >>> slugify("Ammonium paratungstate (APT)")
  'ammonium-paratungstate-apt'
"""

from entityidentity.utils.normalize import (
    normalize_name as _normalize_name,
    canonicalize_name as _canonicalize_name,
    slugify_name as _slugify_name,
    normalize_quotes,
)


def normalize_metal_name(s: str) -> str:
    """
    Aggressive normalization for fuzzy matching.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC)
      - Normalize quotes/apostrophes
      - Collapse multiple spaces to single space
      - Keep alphanumerics, spaces, parentheses, hyphens, slashes, percent

    Args:
        s: Raw metal name/symbol/alias

    Returns:
        Normalized string for matching

    Examples:
        >>> normalize_name("Lithium Carbonate")
        'lithium carbonate'

        >>> normalize_name("FeCr  HC")
        'fecr hc'

        >>> normalize_name("APT 88.5%")
        'apt 88.5%'

        >>> normalize_name("Pt/Pd")
        'pt/pd'
    """
    if not s:
        return ""

    # Normalize quotes first
    s = normalize_quotes(s)

    # Use shared normalization with metal-specific allowed characters
    # Allow: letters, numbers, space, hyphen, slash, parentheses, percent
    return _normalize_name(s, allowed_chars=r"a-z0-9\s\-/()%")


def canonicalize_metal_name(s: str) -> str:
    """
    Light normalization for display and storage.

    Transformations:
      - Strip leading/trailing whitespace
      - Title case (preserve internal casing like "NdPr", "FeCr")
      - Collapse multiple spaces to single space
      - Preserve symbols, formulas, and chemical notation

    Args:
        s: Raw metal name

    Returns:
        Canonicalized display name

    Examples:
        >>> canonicalize_name("lithium carbonate")
        'Lithium Carbonate'

        >>> canonicalize_name("  platinum  ")
        'Platinum'

        >>> canonicalize_name("FeCr HC")
        'Fecr Hc'  # Note: loses original casing; preserve manually if needed

        >>> canonicalize_name("ammonium paratungstate")
        'Ammonium Paratungstate'
    """
    if not s:
        return ""

    # Use shared canonicalization with title case
    return _canonicalize_name(s, apply_title_case=True)


def slugify_metal_name(s: str) -> str:
    """
    Create URL/key-safe slug for metal names.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC -> ASCII)
      - Replace spaces and underscores with hyphens
      - Remove all non-alphanumeric except hyphens
      - Collapse multiple hyphens to single hyphen
      - Strip leading/trailing hyphens

    Args:
        s: Metal name or identifier

    Returns:
        Slug suitable for URLs, keys, filenames

    Examples:
        >>> slugify("Lithium Carbonate")
        'lithium-carbonate'

        >>> slugify("Ammonium paratungstate (APT)")
        'ammonium-paratungstate-apt'

        >>> slugify("FeCr HC 65%")
        'fecr-hc-65'

        >>> slugify("Pt/Pd")
        'pt-pd'

        >>> slugify("Rare earth oxide (REO)")
        'rare-earth-oxide-reo'
    """
    if not s:
        return ""

    # Use shared slugification
    return _slugify_name(s)


# ---- Helper for generating deterministic metal_id ----
def generate_metal_id(name: str) -> str:
    """
    Generate deterministic 16-character hex metal_id.

    Uses SHA-1 hash of normalized name with "|metal" suffix for namespace.

    Args:
        name: Canonical metal name

    Returns:
        16-character hex string (first 16 chars of SHA-1 hash)

    Examples:
        >>> generate_metal_id("Platinum")
        'a1b2c3d4e5f6a7b8'  # deterministic

        >>> generate_metal_id("Lithium Carbonate")
        'c4d5e6f7a8b9c0d1'  # deterministic
    """
    import hashlib

    # Normalize and add namespace suffix
    normalized = normalize_metal_name(name)
    namespaced = f"{normalized}|metal"

    # SHA-1 hash, take first 16 hex chars
    hash_bytes = hashlib.sha1(namespaced.encode("utf-8")).digest()
    return hash_bytes.hex()[:16]


__all__ = [
    "normalize_metal_name",
    "canonicalize_metal_name",
    "slugify_metal_name",
    "generate_metal_id",
]

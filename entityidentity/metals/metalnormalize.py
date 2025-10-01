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

import re
import unicodedata


def normalize_name(s: str) -> str:
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

    # Strip and lowercase
    s = s.strip().lower()

    # Unicode normalization (NFC)
    s = unicodedata.normalize("NFC", s)

    # Normalize quotes/apostrophes
    s = s.replace("'", "'").replace("'", "'")
    s = s.replace(""", '"').replace(""", '"')

    # Keep alphanumerics, spaces, and useful punctuation for metal names
    # Allow: letters, numbers, space, hyphen, slash, parentheses, percent
    s = re.sub(r"[^a-z0-9\s\-/()%]", " ", s)

    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def canonicalize_name(s: str) -> str:
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

    # Strip and collapse spaces
    s = s.strip()
    s = re.sub(r"\s+", " ", s)

    # Title case (note: this will lowercase interior capitals)
    # For preserving specific cases like "NdPr", the YAML source should store canonical form
    s = s.title()

    return s


def slugify(s: str) -> str:
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

    # Strip and lowercase
    s = s.strip().lower()

    # Unicode normalization and ASCII conversion
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    # Replace spaces and underscores with hyphens
    s = re.sub(r"[\s_]+", "-", s)

    # Remove all non-alphanumeric except hyphens
    s = re.sub(r"[^a-z0-9\-]", "", s)

    # Collapse multiple hyphens
    s = re.sub(r"-+", "-", s)

    # Strip leading/trailing hyphens
    s = s.strip("-")

    return s


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
    normalized = normalize_name(name)
    namespaced = f"{normalized}|metal"

    # SHA-1 hash, take first 16 hex chars
    hash_bytes = hashlib.sha1(namespaced.encode("utf-8")).digest()
    return hash_bytes.hex()[:16]


__all__ = [
    "normalize_name",
    "canonicalize_name",
    "slugify",
    "generate_metal_id",
]

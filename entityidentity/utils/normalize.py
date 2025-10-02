"""Shared text normalization utilities.

This module provides generic normalization functions used across
companies, metals, baskets, and other entity resolution modules.
"""

import re
import unicodedata


def normalize_name(
    s: str,
    *,
    allowed_chars: str = r"a-z0-9\s\-",
    remove_legal_suffixes: bool = False,
    legal_suffix_pattern: str = None,
) -> str:
    """Generic normalization for fuzzy matching.

    Transformations:
      1. Unicode normalization (NFKD) and ASCII transliteration
      2. Lowercase
      3. Remove legal suffixes (if enabled)
      4. Remove punctuation (keep only allowed_chars)
      5. Collapse whitespace

    Args:
        s: Raw text to normalize
        allowed_chars: Regex character class for allowed characters (default: alphanumeric, space, hyphen)
        remove_legal_suffixes: Whether to remove legal suffixes (default: False)
        legal_suffix_pattern: Compiled regex pattern for legal suffixes (required if remove_legal_suffixes=True)

    Returns:
        Normalized string for matching

    Examples:
        >>> normalize_name("Apple Inc.", allowed_chars=r"a-z0-9&\-\s")
        'apple inc'

        >>> normalize_name("Lithium Carbonate", allowed_chars=r"a-z0-9\s\-/()%")
        'lithium carbonate'

        >>> normalize_name("PGM 4E", allowed_chars=r"a-z0-9\s\-/()")
        'pgm 4e'
    """
    if not s:
        return ""

    # Unicode normalization and ASCII conversion
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    s = s.lower()

    # Remove legal suffixes (optional, for companies)
    if remove_legal_suffixes and legal_suffix_pattern:
        s = legal_suffix_pattern.sub("", s)

    # Remove punctuation except allowed characters
    s = re.sub(rf"[^{allowed_chars}]", " ", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    return s


def canonicalize_name(
    s: str,
    *,
    allowed_chars: str = r"A-Za-z0-9\s\-&",
    apply_title_case: bool = False,
    remove_comma_before_legal: bool = False,
    remove_period_from_legal: bool = False,
    legal_suffix_comma_pattern: str = None,
    legal_suffix_period_pattern: str = None,
) -> str:
    """Light normalization for display and identifiers.

    Preserves readability while ensuring names are safe for identifiers.
    Use this for: display names, database identifiers, user-facing output.
    DO NOT use this for: fuzzy matching or deduplication.

    Transformations:
      1. Remove commas before legal suffixes (optional, for companies)
      2. Remove periods from legal suffixes (optional, for companies)
      3. Unicode normalization to ASCII
      4. Keep only safe characters
      5. Collapse multiple spaces
      6. Trim whitespace
      7. Apply title case (optional, for metals/baskets)

    Args:
        s: Original text
        allowed_chars: Regex character class for allowed characters
        apply_title_case: Whether to apply title case (default: False)
        remove_comma_before_legal: Remove comma before legal suffixes (default: False)
        remove_period_from_legal: Remove periods from legal suffixes (default: False)
        legal_suffix_comma_pattern: Regex pattern for comma removal (required if remove_comma_before_legal=True)
        legal_suffix_period_pattern: Regex pattern for period removal (required if remove_period_from_legal=True)

    Returns:
        Canonicalized name safe for use in identifiers

    Examples:
        >>> canonicalize_name("Apple Inc.", allowed_chars=r"A-Za-z0-9\s\-&")
        'Apple Inc'

        >>> canonicalize_name("lithium carbonate", apply_title_case=True)
        'Lithium Carbonate'
    """
    if not s:
        return s

    # Step 1: Remove comma before legal suffixes (optional, for companies)
    if remove_comma_before_legal and legal_suffix_comma_pattern:
        s = re.sub(legal_suffix_comma_pattern, r' \1', s, flags=re.IGNORECASE)

    # Step 2: Remove periods from legal suffixes (optional, for companies)
    if remove_period_from_legal and legal_suffix_period_pattern:
        s = re.sub(legal_suffix_period_pattern, r'\1', s, flags=re.IGNORECASE)

    # Step 3: Unicode normalization to ASCII
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')

    # Step 4: Keep only safe characters
    s = re.sub(rf'[^{allowed_chars}]', ' ', s)

    # Step 5: Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s)

    # Step 6: Trim
    s = s.strip()

    # Step 7: Apply title case (optional, for metals/baskets)
    if apply_title_case:
        s = s.title()

    return s


def slugify_name(s: str) -> str:
    """Create URL/key-safe slug.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFKD -> ASCII)
      - Replace spaces and underscores with hyphens
      - Remove all non-alphanumeric except hyphens
      - Collapse multiple hyphens to single hyphen
      - Strip leading/trailing hyphens

    Args:
        s: Text to slugify

    Returns:
        Slug suitable for URLs, keys, filenames

    Examples:
        >>> slugify_name("Lithium Carbonate")
        'lithium-carbonate'

        >>> slugify_name("PGM 4E")
        'pgm-4e'

        >>> slugify_name("Ammonium paratungstate (APT)")
        'ammonium-paratungstate-apt'
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


def normalize_quotes(s: str) -> str:
    """Normalize various quote types to standard ASCII quotes.

    Args:
        s: Text with Unicode quotes

    Returns:
        Text with normalized quotes

    Examples:
        >>> normalize_quotes("'curly'")
        "'curly'"

        >>> normalize_quotes('"smart quotes"')
        '"smart quotes"'
    """
    # Normalize quotes/apostrophes
    s = s.replace("'", "'").replace("'", "'")
    s = s.replace(""", '"').replace(""", '"')
    return s


__all__ = [
    "normalize_name",
    "canonicalize_name",
    "slugify_name",
    "normalize_quotes",
]

"""
Shared Utility Functions
------------------------

Common functions used across multiple entity modules (metals, baskets, etc.).
This module consolidates duplicate code to reduce maintenance burden.

Functions:
  - slugify_name: URL/key-safe slug generation
  - generate_entity_id: Deterministic 16-character hex ID generation
  - get_aliases: Extract alias columns from DataFrame row
  - score_candidate: RapidFuzz scoring for entity resolution
  - expand_aliases: Expand alias list into alias1...alias10 columns
  - load_yaml_file: Load and parse YAML file
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    from rapidfuzz import fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e


def slugify_name(s: str) -> str:
    """
    Create URL/key-safe slug for entity names.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC -> ASCII)
      - Replace spaces and underscores with hyphens
      - Remove all non-alphanumeric except hyphens
      - Collapse multiple hyphens to single hyphen
      - Strip leading/trailing hyphens

    Args:
        s: Entity name or identifier

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


def generate_entity_id(name: str, namespace: str, normalize_func) -> str:
    """
    Generate deterministic 16-character hex entity ID.

    Uses SHA-1 hash of normalized name with namespace suffix.

    Args:
        name: Canonical entity name
        namespace: Namespace suffix (e.g., "metal", "basket")
        normalize_func: Normalization function to apply to name

    Returns:
        16-character hex string (first 16 chars of SHA-1 hash)

    Examples:
        >>> from entityidentity.metals.metalnormalize import normalize_metal_name
        >>> generate_entity_id("Platinum", "metal", normalize_metal_name)
        'a1b2c3d4e5f6a7b8'  # deterministic

        >>> from entityidentity.baskets.basketnormalize import normalize_basket_name
        >>> generate_entity_id("PGM 4E", "basket", normalize_basket_name)
        'c4d5e6f7a8b9c0d1'  # deterministic
    """
    import hashlib

    # Normalize and add namespace suffix
    normalized = normalize_func(name)
    namespaced = f"{normalized}|{namespace}"

    # SHA-1 hash, take first 16 hex chars
    hash_bytes = hashlib.sha1(namespaced.encode("utf-8")).digest()
    return hash_bytes.hex()[:16]


def get_aliases(row: pd.Series) -> list[str]:
    """
    Extract all non-null alias values from alias1...alias10 columns.

    Args:
        row: DataFrame row with alias1, alias2, ..., alias10 columns

    Returns:
        List of alias strings (non-null, non-empty, NOT normalized)

    Examples:
        >>> row = pd.Series({'alias1': 'Pt', 'alias2': 'platinum', 'alias3': None})
        >>> get_aliases(row)
        ['Pt', 'platinum']
    """
    aliases = []
    for i in range(1, 11):  # alias1 through alias10
        col = f"alias{i}"
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            aliases.append(str(row[col]))
    return aliases


def score_candidate(
    row: pd.Series,
    query_norm: str,
    normalize_func,
    name_column: str = "name_norm"
) -> float:
    """
    Score a candidate entity row against normalized query.

    Uses RapidFuzz WRatio scorer.
    Checks both the name column and all alias columns.

    Args:
        row: Candidate entity row
        query_norm: Normalized query string
        normalize_func: Normalization function to apply to aliases
        name_column: Column name containing normalized name (default: "name_norm")

    Returns:
        Best fuzzy match score (0-100) across name and aliases

    Examples:
        >>> from entityidentity.metals.metalnormalize import normalize_metal_name
        >>> row = pd.Series({'name_norm': 'platinum', 'alias1': 'Pt', 'alias2': 'platina'})
        >>> score_candidate(row, 'platinum', normalize_metal_name)
        100.0

        >>> score_candidate(row, 'pt', normalize_metal_name)
        100.0  # matches alias1
    """
    # Collect all searchable strings: name_norm + normalized aliases
    searchable = [row[name_column]]

    # Get aliases and normalize them
    for alias in get_aliases(row):
        searchable.append(normalize_func(alias))

    # Score query against all searchable strings, take best
    best_score = 0.0
    for s in searchable:
        if pd.notna(s) and str(s).strip():
            score = fuzz.WRatio(query_norm, str(s).lower())
            best_score = max(best_score, score)

    return best_score


def expand_aliases(aliases: Optional[List[str]], max_columns: int = 10) -> Dict[str, str]:
    """
    Expand aliases list into alias1...alias10 columns.

    Args:
        aliases: List of alias strings
        max_columns: Maximum number of alias columns to generate (default: 10)

    Returns:
        Dictionary mapping alias1...alias{max_columns} to values

    Examples:
        >>> expand_aliases(['Pt', 'platinum', 'platina'])
        {'alias1': 'Pt', 'alias2': 'platinum', 'alias3': 'platina',
         'alias4': '', 'alias5': '', ...}

        >>> expand_aliases(None)
        {'alias1': '', 'alias2': '', ...}
    """
    result = {}
    if not aliases:
        aliases = []

    for i in range(1, max_columns + 1):
        col_name = f"alias{i}"
        if i <= len(aliases):
            result[col_name] = str(aliases[i - 1])
        else:
            result[col_name] = ""

    return result


def load_yaml_file(path: Path) -> dict:
    """
    Load and parse YAML file.

    Args:
        path: Path to YAML file

    Returns:
        Parsed YAML data as dictionary

    Raises:
        FileNotFoundError: If file does not exist

    Examples:
        >>> data = load_yaml_file(Path("config.yaml"))
        >>> data['version']
        '1.0'
    """
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, 'r') as f:
        return yaml.safe_load(f)


__all__ = [
    "slugify_name",
    "generate_entity_id",
    "get_aliases",
    "score_candidate",
    "expand_aliases",
    "load_yaml_file",
]
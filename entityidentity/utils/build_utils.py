"""
Build Utility Functions
-----------------------

Common functions used in data build scripts (metals, baskets, companies).
This module provides utilities for loading YAML files and expanding columns.

Functions:
  - load_yaml_file: Load and parse YAML file
  - expand_aliases: Expand alias list into alias1...alias10 columns
  - expand_components: Expand component list into component1...component10 columns
"""

from pathlib import Path
from typing import Dict, List, Optional


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


def expand_components(components: Optional[List[dict]], max_columns: int = 10) -> Dict[str, str]:
    """
    Expand components list into component1...component10 columns.

    Each component is stored as: "symbol" or "symbol:weight_pct" if weight is known.
    Used primarily by baskets module.

    Args:
        components: List of component dictionaries with 'symbol' and optional 'weight_pct'
        max_columns: Maximum number of component columns to generate (default: 10)

    Returns:
        Dictionary mapping component1...component{max_columns} to values

    Examples:
        >>> components = [
        ...     {'symbol': 'Pt', 'weight_pct': 0.33},
        ...     {'symbol': 'Pd', 'weight_pct': 0.33},
        ...     {'symbol': 'Rh'},
        ... ]
        >>> expand_components(components)
        {'component1': 'Pt:0.33', 'component2': 'Pd:0.33', 'component3': 'Rh',
         'component4': '', ...}
    """
    result = {}
    if not components:
        components = []

    for i in range(1, max_columns + 1):
        col_name = f"component{i}"
        if i <= len(components):
            comp = components[i - 1]
            symbol = comp.get('symbol', '')
            weight_pct = comp.get('weight_pct')

            if weight_pct is not None:
                result[col_name] = f"{symbol}:{weight_pct}"
            else:
                result[col_name] = symbol
        else:
            result[col_name] = ""

    return result


__all__ = [
    "load_yaml_file",
    "expand_aliases",
    "expand_components",
]

"""Shared data loading utilities for companies and metals modules.

This module provides common data loading patterns with fallback search
across package data and development directories.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd


def find_data_file(
    module_file: str,
    subdirectory: str,
    filenames: List[str],
    search_dev_tables: bool = True,
    module_local_data: bool = False,
) -> Optional[Path]:
    """Find data file by searching standard locations.

    Search priority:
    1. Module-local data: {module_dir}/data/ (if module_local_data=True)
    2. Package data: entityidentity/data/{subdirectory}/
    3. Development data: tables/{subdirectory}/ (if search_dev_tables=True)

    Args:
        module_file: __file__ from the calling module (e.g., __file__)
        subdirectory: Subdirectory name (e.g., 'companies', 'metals')
        filenames: List of candidate filenames to search for (e.g., ['data.parquet', 'data.csv'])
        search_dev_tables: Whether to search tables/ directory for dev data
        module_local_data: If True, search module_dir/data/ first (e.g., for metals)

    Returns:
        Path to found file, or None if not found

    Examples:
        >>> # From companies/companyresolver.py
        >>> path = find_data_file(__file__, 'companies', ['companies.parquet', 'companies.csv'])

        >>> # From metals/metalapi.py (data is in metals/data/, not entityidentity/data/metals/)
        >>> path = find_data_file(__file__, 'metals', ['metals.parquet'],
        ...                       search_dev_tables=False, module_local_data=True)
    """
    # Priority 0: Module-local data (e.g., entityidentity/metals/data/)
    if module_local_data:
        module_dir = Path(module_file).parent
        data_dir = module_dir / "data"
        for filename in filenames:
            p = data_dir / filename
            if p.exists():
                return p

    # Priority 1: Package data (distributed with pip, always available)
    pkg_dir = Path(module_file).parent.parent
    data_dir = pkg_dir / "data" / subdirectory

    for filename in filenames:
        p = data_dir / filename
        if p.exists():
            return p

    # Priority 2: Development data (built locally, comprehensive)
    if search_dev_tables:
        tables_dir = pkg_dir.parent / "tables" / subdirectory
        for filename in filenames:
            p = tables_dir / filename
            if p.exists():
                return p

    return None


def load_parquet_or_csv(file_path: Path) -> pd.DataFrame:
    """Load DataFrame from parquet or CSV file based on extension.

    Args:
        file_path: Path to parquet or CSV file

    Returns:
        Loaded DataFrame

    Raises:
        ValueError: If file extension is not .parquet or .csv
    """
    if file_path.suffix == ".parquet":
        return pd.read_parquet(file_path)
    elif file_path.suffix == ".csv":
        return pd.read_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}. Use .parquet or .csv")


def format_not_found_error(
    subdirectory: str,
    searched_locations: List[Tuple[str, Path]],
    fix_instructions: List[str],
) -> str:
    """Format a helpful FileNotFoundError message.

    Args:
        subdirectory: Data subdirectory name (e.g., 'companies', 'metals')
        searched_locations: List of (description, path) tuples for locations searched
        fix_instructions: List of commands/instructions to fix the issue

    Returns:
        Formatted error message string
    """
    lines = [f"No {subdirectory} data found in standard locations.\n"]

    lines.append("Searched:")
    for i, (desc, path) in enumerate(searched_locations, 1):
        lines.append(f"  {i}. {desc}: {path}")

    lines.append("\nTo fix:")
    for instruction in fix_instructions:
        lines.append(f"  • {instruction}")

    return "\n".join(lines)


__all__ = [
    "find_data_file",
    "load_parquet_or_csv",
    "format_not_found_error",
]
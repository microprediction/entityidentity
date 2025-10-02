"""Shared utilities for EntityIdentity package."""

from entityidentity.utils.dataloader import (
    find_data_file,
    load_parquet_or_csv,
    format_not_found_error,
)

__all__ = [
    "find_data_file",
    "load_parquet_or_csv",
    "format_not_found_error",
]
"""Instruments module for ticker reference resolution.

This module provides functionality for loading and resolving
financial instrument ticker references with crosswalk to metals.
"""

from .instrumentloaders import load_instruments, clear_cache
from .instrumentapi import (
    instrument_identifier,
    match_instruments,
    list_instruments,
)

__all__ = [
    # Primary API
    "instrument_identifier",
    "match_instruments",
    "list_instruments",
    "load_instruments",
    # Utilities
    "clear_cache",
]
"""Metals entity resolution and identification."""

# Clean API that wraps the robust metalidentity implementation
from entityidentity.metals.metalapi import (
    load_metals,
    metal_identifier,
    match_metal,
    list_metals,
)

__all__ = [
    "load_metals",
    "metal_identifier",
    "match_metal",
    "list_metals",
]

"""Baskets module for composite commodity resolution.

This module provides entity resolution for commodity baskets - composite
products made up of multiple metals or materials (e.g., PGM 4E, NdPr, Battery Pack).

Public API:
    basket_identifier(name, threshold=90) -> dict | None
        Resolve basket name to canonical basket entity

    match_basket(name, k=5) -> list[dict]
        Get top-K basket candidates with scores

    list_baskets() -> DataFrame
        List all available baskets

    get_basket_components(name, threshold=90) -> list[str] | None
        Get component symbols for a basket

Examples:
    >>> from entityidentity.baskets import basket_identifier, get_basket_components
    >>>
    >>> basket_identifier("PGM 4E")
    {'basket_id': 'PGM_4E', 'name': 'PGM 4E', ...}
    >>>
    >>> get_basket_components("PGM 4E")
    ['Pt', 'Pd', 'Rh', 'Au']
"""

from entityidentity.baskets.basketapi import (
    basket_identifier,
    match_basket,
    list_baskets,
    get_basket_components,
    load_baskets,
)

__all__ = [
    "basket_identifier",
    "match_basket",
    "list_baskets",
    "get_basket_components",
    "load_baskets",
]

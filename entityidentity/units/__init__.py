"""Units module for unit normalization and conversion.

This module provides functionality for normalizing metal prices to canonical
units with proper basis enforcement.

Public API:
    normalize_unit(raw) -> dict
        Normalize value/unit/basis to canonical form

    get_canonical_unit(material) -> dict
        Get canonical unit and basis for a material

    validate_conversion_inputs(material, raw) -> dict
        Validate that all required parameters are present

Key Principles:
1. Always preserve raw input
2. Convert only when all required parameters present
3. Warn when conversion impossible
4. Never guess missing parameters

Examples:
    >>> from entityidentity.units import normalize_unit
    >>>
    >>> # FeCr with complete parameters - successful conversion
    >>> result = normalize_unit({
    ...     "value": 2150,
    ...     "unit": "USD/t alloy",
    ...     "grade": {"Cr_pct": 65.0},
    ...     "ton_system": "metric",
    ...     "material": "FeCr"
    ... })
    >>> result["norm"]
    {'value': 1.5, 'unit': 'USD/lb', 'basis': 'Cr contained'}
    >>> result["warning"]
    None
    >>>
    >>> # APT without grade - warns and preserves raw
    >>> result = normalize_unit({
    ...     "value": 450,
    ...     "unit": "USD/t APT",
    ...     "grade": None,
    ...     "material": "APT"
    ... })
    >>> result["warning"]
    'APT conversion requires WO3_pct in grade. Cannot convert to canonical $/mtu WO3 basis.'
"""

from .unitapi import (
    normalize_unit,
    get_canonical_unit,
    validate_conversion_inputs,
)

__all__ = [
    "normalize_unit",
    "get_canonical_unit",
    "validate_conversion_inputs",
]
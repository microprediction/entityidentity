"""Public API for unit normalization.

This module provides the main entry point for normalizing metal prices
to canonical units with proper basis enforcement.

Key Design Principles:
1. Always preserve raw input for audit trail
2. Convert only when all required parameters are present
3. Warn explicitly when conversion is impossible
4. Never guess or assume missing parameters
"""

from typing import Dict, Any, Optional

from .unitnorm import normalize_unit_value


def normalize_unit(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize value/unit/basis to canonical form.

    This function takes raw price data and attempts to normalize it to
    canonical units (e.g., $/lb Cr for FeCr, $/mtu WO3 for APT).

    It will ONLY convert when all required parameters are present.
    It will WARN when conversion is impossible due to missing data.
    It will NEVER guess or assume missing parameters.

    Args:
        raw: Dictionary with price data:
            - value (float): Price value (required)
            - unit (str): Unit string like "USD/t alloy", "USD/lb" (required)
            - basis (Optional[str]): Basis description (e.g., "Cr contained")
            - grade (Optional[Dict]): Grade composition (e.g., {"Cr_pct": 65.0})
            - ton_system (Optional[str]): "metric" | "short" | "long"
            - material (Optional[str]): Material hint (e.g., "FeCr", "APT")

    Returns:
        Dictionary with three sections:
        {
            "raw": {...},              # Original input preserved exactly
            "norm": {                  # Normalized/converted values
                "value": float,
                "unit": str,
                "basis": Optional[str]
            },
            "warning": Optional[str]   # Warning if conversion impossible
        }

    Examples:
        >>> # FeCr with complete parameters - successful conversion
        >>> result = normalize_unit({
        ...     "value": 2150,
        ...     "unit": "USD/t alloy",
        ...     "basis": None,
        ...     "grade": {"Cr_pct": 65.0},
        ...     "ton_system": "metric",
        ...     "material": "FeCr"
        ... })
        >>> result["norm"]
        {'value': 1.5, 'unit': 'USD/lb', 'basis': 'Cr contained'}
        >>> result["warning"]
        None

        >>> # APT without grade - warns and preserves raw
        >>> result = normalize_unit({
        ...     "value": 450,
        ...     "unit": "USD/t APT",
        ...     "basis": None,
        ...     "grade": None,
        ...     "material": "APT"
        ... })
        >>> result["norm"]["value"]
        450
        >>> result["warning"]
        'APT conversion requires WO3_pct in grade. Cannot convert to canonical $/mtu WO3 basis.'

        >>> # Ambiguous ton system - warns
        >>> result = normalize_unit({
        ...     "value": 2150,
        ...     "unit": "USD/t alloy",
        ...     "grade": {"Cr_pct": 65.0},
        ...     "ton_system": None,
        ...     "material": "FeCr"
        ... })
        >>> result["warning"]
        'FeCr conversion requires ton_system (metric/short/long). Cannot convert without knowing ton type.'

        >>> # Simple metal with assumed metric ton
        >>> result = normalize_unit({
        ...     "value": 9000,
        ...     "unit": "USD/t",
        ...     "material": "Copper"
        ... })
        >>> result["norm"]["unit"]
        'USD/lb'
        >>> result["warning"]
        'Assumed metric ton for conversion. Specify ton_system explicitly if using short/long ton.'
    """
    # Extract material hint if provided
    material = raw.get("material")

    # Call core normalization function
    return normalize_unit_value(raw, material=material)


def get_canonical_unit(material: str) -> Dict[str, str]:
    """Get canonical unit and basis for a material.

    Useful for determining what parameters are needed for conversion.

    Args:
        material: Material name (e.g., "FeCr", "APT", "Copper")

    Returns:
        Dictionary with:
        {
            "canonical_unit": str,      # e.g., "USD/lb", "USD/mtu WO3"
            "canonical_basis": str,     # e.g., "Cr contained", "WO3 basis"
            "requires": List[str]       # Required parameters for conversion
        }

    Examples:
        >>> get_canonical_unit("FeCr")
        {'canonical_unit': 'USD/lb', 'canonical_basis': 'Cr contained',
         'requires': ['Cr_pct', 'ton_system']}

        >>> get_canonical_unit("APT")
        {'canonical_unit': 'USD/mtu WO3', 'canonical_basis': 'WO3 basis',
         'requires': ['WO3_pct']}

        >>> get_canonical_unit("Copper")
        {'canonical_unit': 'USD/lb', 'canonical_basis': 'Cu contained',
         'requires': []}
    """
    # Load config from unitconfig.yaml
    from .unitnorm import _load_config

    config = _load_config()

    # Look up material
    material_upper = material.upper()

    # Handle common aliases
    material_key = material
    if material_upper in ["FECR", "FERROCHROME"]:
        material_key = "FeCr"
    elif material_upper in ["APT", "AMMONIUM PARATUNGSTATE"]:
        material_key = "APT"
    elif material_upper in ["CU", "COPPER"]:
        material_key = "Copper"
    elif material_upper in ["AL", "ALUMINUM", "ALUMINIUM"]:
        material_key = "Aluminum"
    elif material_upper in ["NI", "NICKEL"]:
        material_key = "Nickel"
    elif material_upper in ["AU", "GOLD"]:
        material_key = "Gold"
    elif material_upper in ["AG", "SILVER"]:
        material_key = "Silver"
    elif material_upper in ["PT", "PLATINUM"]:
        material_key = "Platinum"
    elif material_upper in ["PD", "PALLADIUM"]:
        material_key = "Palladium"

    if material_key in config:
        mat_config = config[material_key]
        return {
            "canonical_unit": mat_config.get("canonical_unit", ""),
            "canonical_basis": mat_config.get("canonical_basis", ""),
            "requires": mat_config.get("requires", [])
        }

    # Unknown material
    return {
        "canonical_unit": "Unknown",
        "canonical_basis": "Unknown",
        "requires": []
    }


def validate_conversion_inputs(
    material: str,
    raw: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate that all required parameters are present for conversion.

    Useful for checking inputs before attempting conversion.

    Args:
        material: Material name (e.g., "FeCr", "APT")
        raw: Raw input dictionary

    Returns:
        Dictionary with validation result:
        {
            "valid": bool,              # True if all required params present
            "missing": List[str],       # List of missing parameters
            "message": str              # Human-readable validation message
        }

    Examples:
        >>> # Complete FeCr inputs
        >>> validate_conversion_inputs("FeCr", {
        ...     "value": 2150,
        ...     "unit": "USD/t alloy",
        ...     "grade": {"Cr_pct": 65.0},
        ...     "ton_system": "metric"
        ... })
        {'valid': True, 'missing': [], 'message': 'All required parameters present'}

        >>> # Missing grade for FeCr
        >>> validate_conversion_inputs("FeCr", {
        ...     "value": 2150,
        ...     "unit": "USD/t alloy",
        ...     "ton_system": "metric"
        ... })
        {'valid': False, 'missing': ['Cr_pct'], 'message': 'Missing required parameters: Cr_pct'}

        >>> # Missing ton_system for FeCr
        >>> validate_conversion_inputs("FeCr", {
        ...     "value": 2150,
        ...     "unit": "USD/t alloy",
        ...     "grade": {"Cr_pct": 65.0}
        ... })
        {'valid': False, 'missing': ['ton_system'], 'message': 'Missing required parameters: ton_system'}
    """
    # Get canonical unit info
    canonical = get_canonical_unit(material)
    required_params = canonical["requires"]

    if not required_params:
        # No special requirements
        return {
            "valid": True,
            "missing": [],
            "message": "No special parameters required"
        }

    # Check for missing parameters
    missing = []

    for param in required_params:
        if param == "ton_system":
            if not raw.get("ton_system"):
                missing.append("ton_system")
        else:
            # Assume it's a grade parameter (e.g., Cr_pct, WO3_pct)
            grade = raw.get("grade")
            if not grade or param not in grade:
                missing.append(param)

    if missing:
        return {
            "valid": False,
            "missing": missing,
            "message": f"Missing required parameters: {', '.join(missing)}"
        }

    return {
        "valid": True,
        "missing": [],
        "message": "All required parameters present"
    }


__all__ = [
    "normalize_unit",
    "get_canonical_unit",
    "validate_conversion_inputs",
]
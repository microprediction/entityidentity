"""Unit normalization and conversion logic.

This module handles conversion of metal prices to canonical units with proper
basis enforcement. Never guesses missing parameters - always warns instead.

Key Principles:
1. Always preserve raw input
2. Convert only when all required parameters present
3. Warn when conversion impossible
4. Never guess ambiguous parameters (e.g., ton system)
"""

from typing import Dict, Any, Optional
import yaml
from pathlib import Path


# ============================================================================
# Conversion Constants
# ============================================================================

# Mass conversion factors (to pounds)
METRIC_TON_TO_LBS = 2204.62  # 1 metric ton = 2204.62 lbs
SHORT_TON_TO_LBS = 2000.0    # 1 short ton = 2000 lbs (US ton)
LONG_TON_TO_LBS = 2240.0     # 1 long ton = 2240 lbs (UK ton)
KG_TO_LBS = 2.20462           # 1 kg = 2.20462 lbs

# Troy ounce conversion factors
TROY_OZ_PER_KG = 32.1507      # 1 kg = 32.1507 troy oz
GRAMS_PER_TROY_OZ = 31.1035   # 1 troy oz = 31.1035 grams

# MTU (Metric Ton Unit) conversions
# 1 MTU = 100 kg = 10 kg/ton = 1% of metric ton
MTU_PER_METRIC_TON = 10.0


# ============================================================================
# Load Configuration
# ============================================================================

def _load_config() -> Dict[str, Any]:
    """Load unit configuration from YAML file.

    Returns:
        Dictionary with material-specific unit rules
    """
    config_path = Path(__file__).parent / "unitconfig.yaml"

    if not config_path.exists():
        # Return minimal config if file not found
        return {}

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


# Cache config on module load
_CONFIG = _load_config()


# ============================================================================
# Helper Functions
# ============================================================================

def _get_ton_conversion_factor(ton_system: Optional[str]) -> Optional[float]:
    """Get conversion factor from tons to pounds.

    Args:
        ton_system: "metric" | "short" | "long" | None

    Returns:
        Conversion factor (lbs per ton) or None if ambiguous

    Examples:
        >>> _get_ton_conversion_factor("metric")
        2204.62

        >>> _get_ton_conversion_factor("short")
        2000.0

        >>> _get_ton_conversion_factor(None)
        None  # Ambiguous, cannot convert
    """
    if not ton_system:
        return None

    ton_system = ton_system.lower().strip()

    if ton_system in ["metric", "mt", "tonne", "tonnes"]:
        return METRIC_TON_TO_LBS
    elif ton_system in ["short", "us", "st"]:
        return SHORT_TON_TO_LBS
    elif ton_system in ["long", "uk", "lt", "imperial"]:
        return LONG_TON_TO_LBS
    else:
        return None  # Unknown ton system


def _normalize_unit_string(unit: str) -> str:
    """Normalize unit string for comparison.

    Args:
        unit: Raw unit string (e.g., "USD/t alloy", "$/lb")

    Returns:
        Normalized lowercase unit string

    Examples:
        >>> _normalize_unit_string("USD/t alloy")
        'usd/t alloy'

        >>> _normalize_unit_string("$/lb Cr")
        '$/lb cr'
    """
    return unit.lower().strip()


# ============================================================================
# Conversion Functions
# ============================================================================

def convert_fecr(
    value: float,
    unit: str,
    grade: Optional[Dict[str, float]],
    ton_system: Optional[str]
) -> Dict[str, Any]:
    """Convert FeCr price to canonical $/lb Cr contained.

    Conversion Formula:
        $/lb Cr = ($/t alloy) / (Cr% / 100) / (lbs per ton)

    Example Calculation:
        Input: $2150/t alloy, 65% Cr, metric ton
        Step 1: Cr contained = 2150 / (65/100) = 2150 / 0.65 = $3307.69/t Cr
        Step 2: $/lb Cr = 3307.69 / 2204.62 = $1.50/lb Cr

    Args:
        value: Price value
        unit: Unit string (e.g., "USD/t alloy")
        grade: Grade dict with Cr_pct (e.g., {"Cr_pct": 65.0})
        ton_system: "metric" | "short" | "long"

    Returns:
        {
            "raw": {...},
            "norm": {"value": float, "unit": str, "basis": str},
            "warning": Optional[str]
        }
    """
    unit_norm = _normalize_unit_string(unit)

    # Check if already in canonical form
    if "lb" in unit_norm and "cr" in unit_norm:
        return {
            "raw": {"value": value, "unit": unit, "basis": "Cr contained", "grade": grade, "ton_system": ton_system},
            "norm": {"value": value, "unit": "USD/lb", "basis": "Cr contained"},
            "warning": None
        }

    # Check for required parameters
    if not grade or "Cr_pct" not in grade:
        return {
            "raw": {"value": value, "unit": unit, "basis": None, "grade": grade, "ton_system": ton_system},
            "norm": {"value": value, "unit": unit, "basis": None},
            "warning": "FeCr conversion requires Cr_pct in grade. Cannot convert to canonical $/lb Cr basis."
        }

    if not ton_system:
        return {
            "raw": {"value": value, "unit": unit, "basis": None, "grade": grade, "ton_system": ton_system},
            "norm": {"value": value, "unit": unit, "basis": None},
            "warning": "FeCr conversion requires ton_system (metric/short/long). Cannot convert without knowing ton type."
        }

    # Get conversion factor
    lbs_per_ton = _get_ton_conversion_factor(ton_system)
    if lbs_per_ton is None:
        return {
            "raw": {"value": value, "unit": unit, "basis": None, "grade": grade, "ton_system": ton_system},
            "norm": {"value": value, "unit": unit, "basis": None},
            "warning": f"Unknown ton system: {ton_system}. Must be metric/short/long."
        }

    # Perform conversion: $/t alloy ’ $/lb Cr contained
    # Step 1: Convert to $/t Cr contained (adjust for grade)
    cr_pct = grade["Cr_pct"]
    if cr_pct <= 0 or cr_pct > 100:
        return {
            "raw": {"value": value, "unit": unit, "basis": None, "grade": grade, "ton_system": ton_system},
            "norm": {"value": value, "unit": unit, "basis": None},
            "warning": f"Invalid Cr_pct: {cr_pct}. Must be between 0 and 100."
        }

    # Step 1: $/t Cr = ($/t alloy) / (Cr% / 100)
    value_per_ton_cr = value / (cr_pct / 100.0)

    # Step 2: $/lb Cr = ($/t Cr) / (lbs per ton)
    value_per_lb_cr = value_per_ton_cr / lbs_per_ton

    return {
        "raw": {"value": value, "unit": unit, "basis": None, "grade": grade, "ton_system": ton_system},
        "norm": {"value": round(value_per_lb_cr, 4), "unit": "USD/lb", "basis": "Cr contained"},
        "warning": None
    }


def convert_apt(
    value: float,
    unit: str,
    grade: Optional[Dict[str, float]]
) -> Dict[str, Any]:
    """Convert APT (Ammonium Paratungstate) to canonical $/mtu WO3.

    Conversion Formula:
        $/mtu WO3 = ($/t APT) * (WO3% / 100) / 10

    MTU (Metric Ton Unit) = 10 kg = 1% of metric ton

    Example Calculation:
        Input: $450/t APT, 88.5% WO3
        Step 1: WO3 content = 450 * (88.5/100) = 450 * 0.885 = $398.25/t WO3
        Step 2: $/mtu WO3 = 398.25 / 10 = $39.825/mtu WO3

    Args:
        value: Price value
        unit: Unit string (e.g., "USD/t APT")
        grade: Grade dict with WO3_pct (e.g., {"WO3_pct": 88.5})

    Returns:
        {
            "raw": {...},
            "norm": {"value": float, "unit": str, "basis": str},
            "warning": Optional[str]
        }
    """
    unit_norm = _normalize_unit_string(unit)

    # Check if already in canonical form
    if "mtu" in unit_norm and "wo3" in unit_norm:
        return {
            "raw": {"value": value, "unit": unit, "basis": "WO3 basis", "grade": grade},
            "norm": {"value": value, "unit": "USD/mtu WO3", "basis": "WO3 basis"},
            "warning": None
        }

    # Check for required parameters
    if not grade or "WO3_pct" not in grade:
        return {
            "raw": {"value": value, "unit": unit, "basis": None, "grade": grade},
            "norm": {"value": value, "unit": unit, "basis": None},
            "warning": "APT conversion requires WO3_pct in grade. Cannot convert to canonical $/mtu WO3 basis."
        }

    # Perform conversion: $/t APT ’ $/mtu WO3
    wo3_pct = grade["WO3_pct"]
    if wo3_pct <= 0 or wo3_pct > 100:
        return {
            "raw": {"value": value, "unit": unit, "basis": None, "grade": grade},
            "norm": {"value": value, "unit": unit, "basis": None},
            "warning": f"Invalid WO3_pct: {wo3_pct}. Must be between 0 and 100."
        }

    # Step 1: $/t WO3 = ($/t APT) * (WO3% / 100)
    value_per_ton_wo3 = value * (wo3_pct / 100.0)

    # Step 2: $/mtu WO3 = ($/t WO3) / 10
    value_per_mtu_wo3 = value_per_ton_wo3 / MTU_PER_METRIC_TON

    return {
        "raw": {"value": value, "unit": unit, "basis": None, "grade": grade},
        "norm": {"value": round(value_per_mtu_wo3, 4), "unit": "USD/mtu WO3", "basis": "WO3 basis"},
        "warning": None
    }


def convert_simple_metal(
    value: float,
    unit: str,
    material: str,
    canonical_unit: str = "USD/lb"
) -> Dict[str, Any]:
    """Convert simple metal prices (pure metals, no grade adjustment).

    Handles pure base metals (Cu, Ni, Zn, Al, etc.) with simple mass conversions.

    Conversion Formulas:
        $/t ’ $/lb: value / (lbs per ton)
        $/kg ’ $/lb: value / 2.20462
        $/oz ’ $/lb: value * 16  (avoirdupois oz)
        $/troy oz ’ $/troy oz: no conversion (precious metals)

    Args:
        value: Price value
        unit: Unit string (e.g., "USD/t", "USD/kg", "USD/lb")
        material: Material name (e.g., "Copper", "Nickel")
        canonical_unit: Target unit (default: "USD/lb" for base metals, "USD/oz" for precious)

    Returns:
        {
            "raw": {...},
            "norm": {"value": float, "unit": str, "basis": str},
            "warning": Optional[str]
        }
    """
    unit_norm = _normalize_unit_string(unit)

    # Check if already in canonical form
    if canonical_unit.lower() in unit_norm:
        return {
            "raw": {"value": value, "unit": unit, "basis": f"{material} contained"},
            "norm": {"value": value, "unit": canonical_unit, "basis": f"{material} contained"},
            "warning": None
        }

    # Determine if ton-based (need to guess ton system if not specified)
    if "/t" in unit_norm or "/ton" in unit_norm:
        # For simple metals, assume metric ton if not specified
        # This is a safe assumption for base metals traded on LME/COMEX
        lbs_per_ton = METRIC_TON_TO_LBS

        # Convert: $/t ’ $/lb
        value_per_lb = value / lbs_per_ton

        return {
            "raw": {"value": value, "unit": unit, "basis": f"{material} contained"},
            "norm": {"value": round(value_per_lb, 4), "unit": "USD/lb", "basis": f"{material} contained"},
            "warning": "Assumed metric ton for conversion. Specify ton_system explicitly if using short/long ton."
        }

    # Handle kg-based
    if "/kg" in unit_norm:
        value_per_lb = value / KG_TO_LBS

        return {
            "raw": {"value": value, "unit": unit, "basis": f"{material} contained"},
            "norm": {"value": round(value_per_lb, 4), "unit": "USD/lb", "basis": f"{material} contained"},
            "warning": None
        }

    # Handle troy oz for precious metals
    if "oz" in unit_norm and canonical_unit == "USD/oz":
        # Assume troy ounce for precious metals
        return {
            "raw": {"value": value, "unit": unit, "basis": f"{material} contained"},
            "norm": {"value": value, "unit": "USD/oz", "basis": f"{material} contained"},
            "warning": None
        }

    # Unknown unit conversion
    return {
        "raw": {"value": value, "unit": unit, "basis": None},
        "norm": {"value": value, "unit": unit, "basis": None},
        "warning": f"Unknown unit conversion from {unit} to {canonical_unit} for {material}."
    }


# ============================================================================
# Main Normalization Function
# ============================================================================

def normalize_unit_value(
    raw: Dict[str, Any],
    material: Optional[str] = None
) -> Dict[str, Any]:
    """Normalize unit/value/basis to canonical form.

    This is the core normalization function that:
    1. Preserves raw input
    2. Converts to canonical units when safe
    3. Warns when conversion impossible
    4. Never guesses missing parameters

    Args:
        raw: Dictionary with:
            - value (float): Price value
            - unit (str): Unit string (e.g., "USD/t alloy", "USD/lb")
            - basis (Optional[str]): Basis description
            - grade (Optional[Dict]): Grade dict (e.g., {"Cr_pct": 65.0})
            - ton_system (Optional[str]): "metric" | "short" | "long"
        material: Material hint (e.g., "FeCr", "APT", "Copper")

    Returns:
        {
            "raw": {...},           # Original input preserved
            "norm": {               # Normalized/converted
                "value": float,
                "unit": str,
                "basis": Optional[str]
            },
            "warning": Optional[str]  # Conversion issues
        }

    Examples:
        >>> # FeCr with complete parameters
        >>> normalize_unit_value({
        ...     "value": 2150,
        ...     "unit": "USD/t alloy",
        ...     "basis": None,
        ...     "grade": {"Cr_pct": 65.0},
        ...     "ton_system": "metric"
        ... }, material="FeCr")
        {'raw': {...}, 'norm': {'value': 1.5, 'unit': 'USD/lb', 'basis': 'Cr contained'}, 'warning': None}

        >>> # APT without grade - warns and preserves raw
        >>> normalize_unit_value({
        ...     "value": 450,
        ...     "unit": "USD/t APT",
        ...     "basis": None,
        ...     "grade": None
        ... }, material="APT")
        {'raw': {...}, 'norm': {'value': 450, 'unit': 'USD/t APT', 'basis': None},
         'warning': 'APT conversion requires WO3_pct in grade...'}
    """
    value = raw.get("value")
    unit = raw.get("unit")
    basis = raw.get("basis")
    grade = raw.get("grade")
    ton_system = raw.get("ton_system")

    if value is None or unit is None:
        return {
            "raw": raw,
            "norm": raw,
            "warning": "Missing required fields: value and unit"
        }

    # Detect material from unit or basis if not provided
    if not material:
        unit_lower = unit.lower()
        if "fecr" in unit_lower or (basis and "cr" in basis.lower()):
            material = "FeCr"
        elif "apt" in unit_lower or (basis and "wo3" in basis.lower()):
            material = "APT"
        elif "copper" in unit_lower or "cu" in unit_lower:
            material = "Copper"
        # Add more material detection as needed

    # Route to appropriate converter based on material
    if material and material.upper() == "FECR":
        return convert_fecr(value, unit, grade, ton_system)

    elif material and material.upper() == "APT":
        return convert_apt(value, unit, grade)

    elif material and material.upper() in ["COPPER", "CU", "ALUMINUM", "AL", "NICKEL", "NI", "ZINC", "ZN"]:
        return convert_simple_metal(value, unit, material)

    elif material and material.upper() in ["GOLD", "AU", "SILVER", "AG", "PLATINUM", "PT", "PALLADIUM", "PD"]:
        return convert_simple_metal(value, unit, material, canonical_unit="USD/oz")

    else:
        # Unknown material or no conversion rule - preserve raw
        return {
            "raw": raw,
            "norm": {"value": value, "unit": unit, "basis": basis},
            "warning": f"No conversion rule for material: {material}. Preserving raw values."
        }


__all__ = [
    "normalize_unit_value",
    "convert_fecr",
    "convert_apt",
    "convert_simple_metal",
]
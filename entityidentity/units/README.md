# Units Module

Unit normalization and conversion for metal prices with basis enforcement.

## Overview

The units module normalizes metal prices to canonical units (e.g., $/lb Cr for FeCr, $/mtu WO3 for APT) while enforcing proper basis calculations. It follows a strict "never guess" policy: conversions only occur when all required parameters are present.

## Key Principles

1. **Always Preserve Raw**: Original input always preserved for audit trail
2. **Convert When Safe**: Only convert when all required parameters present
3. **Warn Explicitly**: Clear warnings when conversion impossible
4. **Never Guess**: Never assume or guess missing parameters

## Quick Start

```python
from entityidentity.units import normalize_unit

# FeCr with complete parameters - successful conversion
result = normalize_unit({
    "value": 2150,
    "unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0},
    "ton_system": "metric",
    "material": "FeCr"
})

# Result:
# {
#     "raw": {"value": 2150, "unit": "USD/t alloy", ...},
#     "norm": {"value": 1.5, "unit": "USD/lb", "basis": "Cr contained"},
#     "warning": None
# }

# APT without grade - warns and preserves raw
result = normalize_unit({
    "value": 450,
    "unit": "USD/t APT",
    "grade": None,
    "material": "APT"
})

# Result:
# {
#     "raw": {"value": 450, "unit": "USD/t APT", ...},
#     "norm": {"value": 450, "unit": "USD/t APT", "basis": None},
#     "warning": "APT conversion requires WO3_pct in grade..."
# }
```

## Supported Materials

### 1. FeCr (Ferrochrome)

**Canonical Form**: `USD/lb Cr contained`

**Required Parameters**:
- `Cr_pct`: Chromium percentage (e.g., 65.0 for 65% Cr)
- `ton_system`: `"metric"` | `"short"` | `"long"`

**Conversion Formula**:
```
Step 1: $/t Cr = ($/t alloy) / (Cr% / 100)
Step 2: $/lb Cr = ($/t Cr) / (lbs per ton)

Where:
- Metric ton = 2204.62 lbs
- Short ton = 2000 lbs
- Long ton = 2240 lbs
```

**Example**:
```python
# Input: $2150/t alloy, 65% Cr, metric ton
# Step 1: $2150 / 0.65 = $3307.69/t Cr
# Step 2: $3307.69 / 2204.62 = $1.50/lb Cr

normalize_unit({
    "value": 2150,
    "unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0},
    "ton_system": "metric",
    "material": "FeCr"
})
# ’ {"norm": {"value": 1.5, "unit": "USD/lb", "basis": "Cr contained"}}
```

### 2. APT (Ammonium Paratungstate)

**Canonical Form**: `USD/mtu WO3`

**Required Parameters**:
- `WO3_pct`: WO3 percentage (e.g., 88.5 for 88.5% WO3)

**Conversion Formula**:
```
Step 1: $/t WO3 = ($/t APT) * (WO3% / 100)
Step 2: $/mtu WO3 = ($/t WO3) / 10

Where:
- MTU (Metric Ton Unit) = 100 kg = 10 kg/ton = 1% of metric ton
```

**Example**:
```python
# Input: $450/t APT, 88.5% WO3
# Step 1: $450 * 0.885 = $398.25/t WO3
# Step 2: $398.25 / 10 = $39.825/mtu WO3

normalize_unit({
    "value": 450,
    "unit": "USD/t APT",
    "grade": {"WO3_pct": 88.5},
    "material": "APT"
})
# ’ {"norm": {"value": 39.825, "unit": "USD/mtu WO3", "basis": "WO3 basis"}}
```

### 3. Base Metals (Cu, Ni, Zn, Al, etc.)

**Canonical Form**: `USD/lb` (metal contained)

**Required Parameters**: None (pure metals, simple mass conversion)

**Conversion Formula**:
```
$/lb = ($/t) / (lbs per ton)

For simple metals, assumes metric ton if not specified
```

**Example**:
```python
# Copper: $9000/t ’ $/lb
# $9000 / 2204.62 = $4.08/lb

normalize_unit({
    "value": 9000,
    "unit": "USD/t",
    "material": "Copper"
})
# ’ {"norm": {"value": 4.08, "unit": "USD/lb", "basis": "Cu contained"},
#    "warning": "Assumed metric ton for conversion..."}
```

### 4. Precious Metals (Au, Ag, Pt, Pd)

**Canonical Form**: `USD/oz` (troy ounce)

**Required Parameters**: None

**Conversion Constants**:
```
1 troy oz = 31.1035 grams
1 kg = 32.1507 troy oz
```

**Example**:
```python
normalize_unit({
    "value": 2000,
    "unit": "USD/oz",
    "material": "Gold"
})
# ’ {"norm": {"value": 2000, "unit": "USD/oz", "basis": "Au contained"}}
```

## API Reference

### `normalize_unit(raw)`

Normalize value/unit/basis to canonical form.

**Parameters**:
- `raw` (dict): Raw price data with:
  - `value` (float): Price value **(required)**
  - `unit` (str): Unit string like "USD/t alloy" **(required)**
  - `basis` (str, optional): Basis description
  - `grade` (dict, optional): Grade composition (e.g., `{"Cr_pct": 65.0}`)
  - `ton_system` (str, optional): `"metric"` | `"short"` | `"long"`
  - `material` (str, optional): Material hint (e.g., "FeCr", "APT")

**Returns**:
```python
{
    "raw": {...},              # Original input preserved exactly
    "norm": {                  # Normalized/converted values
        "value": float,
        "unit": str,
        "basis": Optional[str]
    },
    "warning": Optional[str]   # Warning if conversion impossible
}
```

**Examples**:
```python
# Successful conversion
result = normalize_unit({
    "value": 2150,
    "unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0},
    "ton_system": "metric",
    "material": "FeCr"
})
assert result["norm"]["value"] == 1.5
assert result["warning"] is None

# Missing grade - warns
result = normalize_unit({
    "value": 450,
    "unit": "USD/t APT",
    "material": "APT"
})
assert result["warning"] == "APT conversion requires WO3_pct in grade..."
assert result["norm"]["value"] == 450  # Preserved raw

# Ambiguous ton system - warns
result = normalize_unit({
    "value": 2150,
    "unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0},
    "material": "FeCr"
})
assert "ton_system" in result["warning"]
```

### `get_canonical_unit(material)`

Get canonical unit and basis for a material.

**Parameters**:
- `material` (str): Material name (e.g., "FeCr", "APT", "Copper")

**Returns**:
```python
{
    "canonical_unit": str,      # e.g., "USD/lb", "USD/mtu WO3"
    "canonical_basis": str,     # e.g., "Cr contained", "WO3 basis"
    "requires": List[str]       # Required parameters for conversion
}
```

**Examples**:
```python
get_canonical_unit("FeCr")
# ’ {"canonical_unit": "USD/lb", "canonical_basis": "Cr contained",
#    "requires": ["Cr_pct", "ton_system"]}

get_canonical_unit("APT")
# ’ {"canonical_unit": "USD/mtu WO3", "canonical_basis": "WO3 basis",
#    "requires": ["WO3_pct"]}

get_canonical_unit("Copper")
# ’ {"canonical_unit": "USD/lb", "canonical_basis": "Cu contained",
#    "requires": []}
```

### `validate_conversion_inputs(material, raw)`

Validate that all required parameters are present for conversion.

**Parameters**:
- `material` (str): Material name
- `raw` (dict): Raw input dictionary

**Returns**:
```python
{
    "valid": bool,              # True if all required params present
    "missing": List[str],       # List of missing parameters
    "message": str              # Human-readable validation message
}
```

**Examples**:
```python
# Complete inputs
validate_conversion_inputs("FeCr", {
    "value": 2150,
    "grade": {"Cr_pct": 65.0},
    "ton_system": "metric"
})
# ’ {"valid": True, "missing": [], "message": "All required parameters present"}

# Missing grade
validate_conversion_inputs("FeCr", {
    "value": 2150,
    "ton_system": "metric"
})
# ’ {"valid": False, "missing": ["Cr_pct"], "message": "Missing required parameters: Cr_pct"}
```

## Conversion Constants

### Mass Conversions (to pounds)

```python
METRIC_TON_TO_LBS = 2204.62   # 1 metric ton = 2204.62 lbs
SHORT_TON_TO_LBS = 2000.0     # 1 short ton = 2000 lbs (US ton)
LONG_TON_TO_LBS = 2240.0      # 1 long ton = 2240 lbs (UK ton)
KG_TO_LBS = 2.20462           # 1 kg = 2.20462 lbs
```

### Troy Ounce Conversions

```python
TROY_OZ_PER_KG = 32.1507      # 1 kg = 32.1507 troy oz
GRAMS_PER_TROY_OZ = 31.1035   # 1 troy oz = 31.1035 grams
```

### MTU (Metric Ton Unit)

```python
MTU_PER_METRIC_TON = 10.0     # 1 MTU = 100 kg = 10% of metric ton
```

## Configuration

Material-specific rules are defined in `unitconfig.yaml`:

```yaml
FeCr:
  canonical_unit: "USD/lb"
  canonical_basis: "Cr contained"
  requires:
    - "Cr_pct"
    - "ton_system"
  conversion_note: "Convert $/t alloy ’ $/lb Cr contained"
  source: "Fastmarkets FeCr specifications"

APT:
  canonical_unit: "USD/mtu WO3"
  canonical_basis: "WO3 basis"
  requires:
    - "WO3_pct"
  conversion_note: "Convert $/t APT ’ $/mtu WO3"
  source: "Fastmarkets APT specifications"
```

## Error Handling

The module uses warnings rather than exceptions for conversion failures:

```python
# Missing required parameter
result = normalize_unit({
    "value": 2150,
    "unit": "USD/t alloy",
    "material": "FeCr"
    # Missing: grade and ton_system
})

# Returns with warning, preserves raw
assert result["warning"] is not None
assert result["norm"]["value"] == 2150  # Raw preserved
```

## Common Use Cases

### 1. Normalize FeCr Prices

```python
# Convert spot price to canonical form
raw_price = {
    "value": 2150,
    "unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0},
    "ton_system": "metric",
    "material": "FeCr"
}

result = normalize_unit(raw_price)

# Use normalized price for comparison
canonical_price = result["norm"]["value"]  # 1.5 USD/lb Cr
```

### 2. Handle Missing Grade Data

```python
# APT price without grade information
raw_price = {
    "value": 450,
    "unit": "USD/t APT",
    "material": "APT"
}

result = normalize_unit(raw_price)

# Check for warnings
if result["warning"]:
    print(f"Warning: {result['warning']}")
    # Use raw price for now, flag for manual review
    price = result["raw"]["value"]
else:
    # Use normalized price
    price = result["norm"]["value"]
```

### 3. Validate Before Conversion

```python
# Check if conversion is possible before attempting
validation = validate_conversion_inputs("FeCr", {
    "value": 2150,
    "unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0},
    # Missing: ton_system
})

if not validation["valid"]:
    print(f"Cannot convert: {validation['message']}")
    print(f"Missing: {validation['missing']}")
    # Prompt user for missing parameters
```

## Testing

```bash
# Run unit tests
pytest tests/units/ -v

# Specific test file
pytest tests/units/test_unitapi.py -v
```

## Dependencies

```bash
pip install pyyaml  # For loading unitconfig.yaml
```

## Limitations

1. **Ton System Ambiguity**: When ton system not specified for alloys, cannot convert safely
2. **Material Detection**: Must specify material explicitly or it's inferred from unit string
3. **Custom Alloys**: Only supports materials defined in `unitconfig.yaml`
4. **Currency**: Assumes USD, no currency conversion

## Future Enhancements

- Multi-currency support
- Custom alloy definitions via API
- Automatic material detection from context
- Historical price normalization
- Batch conversion API
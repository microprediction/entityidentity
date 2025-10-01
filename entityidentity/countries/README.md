# Country Entity Resolution

Robust country name resolution to canonical ISO codes.

## Overview

This module provides a multi-stage pipeline for resolving messy country names, codes, and variations to standard ISO 3166-1 alpha-2 codes.

## Architecture

```
countryapi.py (clean wrapper)
    ↓
fuzzycountry.py (robust implementation)
    ├── 1. country_converter (handles many aliases)
    ├── 2. pycountry (official ISO 3166 database)
    ├── 3. manual catalog (colloquialisms: England, Holland, etc.)
    └── 4. rapidfuzz (fuzzy matching for typos)
```

## Usage

```python
from entityidentity import country_identifier, country_identifiers

# Single resolution
country_identifier("USA")              # → 'US'
country_identifier("United Kingdom")   # → 'GB'
country_identifier("Holland")          # → 'NL'
country_identifier("England")          # → 'GB'
country_identifier("Untied States")    # → 'US' (typo tolerance!)

# Batch resolution
country_identifiers(["USA", "Holland", "England"])  # → ['US', 'NL', 'GB']
```

## Features

### 1. Multiple Input Formats
- **ISO codes**: `US`, `USA`, `840`
- **Official names**: `United States`, `United Kingdom`
- **Colloquial names**: `America`, `England`, `Holland`
- **Cultural variants**: `Deutschland`, `México`, `Brasil`
- **Typo tolerance**: `Untied States` → `US`

### 2. Output Formats
```python
from entityidentity.countries.fuzzycountry import country_identifier

country_identifier("USA", to="ISO2")     # → 'US'
country_identifier("USA", to="ISO3")     # → 'USA'
country_identifier("USA", to="numeric")  # → '840'
```

### 3. Configurable Behavior
```python
# Disable user-assigned codes (e.g., Kosovo 'XK')
country_identifier("Kosovo", allow_user_assigned=False)  # → None

# Disable fuzzy matching
country_identifier("Untied States", fuzzy=False)  # → None

# Adjust fuzzy threshold (0-100)
country_identifier("Grmany", fuzzy_threshold=80)  # → 'DE'
```

## Resolution Pipeline

### Stage 1: country_converter
- Handles official ISO names and many common aliases
- Fast direct code conversion (US → US, USA → US, DEU → DE)
- Includes regional and historical names

### Stage 2: pycountry
- Official ISO 3166 database
- Exact matching on official names, common names, and alternate names
- Most authoritative source for official country data

### Stage 3: Manual Catalog
Handles colloquialisms and culturally common names:
- **Regions**: `England`, `Scotland`, `Wales` → `GB`
- **Informal**: `Holland` → `NL`, `America` → `US`
- **Historical**: `Burma` → `MM`, `Swaziland` → `SZ`
- **Cultural**: `Deutschland` → `DE`, `México` → `MX`
- **Special**: `Kosovo` → `XK` (user-assigned code)

### Stage 4: Fuzzy Matching
- Uses RapidFuzz for typo tolerance
- Default threshold: 85% similarity
- Examples:
  - `Untied States` → `United States` → `US`
  - `Grmany` → `Germany` → `DE`

## Dependencies

- **country_converter** (`pip install country-converter`)
  - Multi-source country mappings (ISO, UN, World Bank, etc.)
  - Extensive alias database
  
- **pycountry** (`pip install pycountry`)
  - Official ISO 3166-1 database
  - Always up-to-date with ISO standards
  
- **rapidfuzz** (already included for company matching)
  - Fast fuzzy string matching
  - Used for typo tolerance

## Implementation Details

### Files

- **`countryapi.py`**: Clean, simple wrapper for users who just want ISO2 codes
- **`fuzzycountry.py`**: Full implementation with all features and configuration options
- **`__init__.py`**: Package exports

### Why This Approach?

1. **Don't reinvent the wheel**: Uses established libraries (`country_converter`, `pycountry`)
2. **Layered fallback**: Each stage handles what it does best
3. **Configurable**: Advanced users can access full `fuzzycountry` API
4. **Fast**: Most queries resolve in first two stages (no fuzzy matching needed)
5. **Robust**: Handles real-world messy data (typos, colloquialisms, cultural variants)

## Examples

### Basic Usage
```python
from entityidentity import country_identifier

# ISO codes
country_identifier("US")      # → 'US'
country_identifier("USA")     # → 'US'
country_identifier("840")     # → 'US'

# Official names
country_identifier("United States")         # → 'US'
country_identifier("Korea, Republic of")    # → 'KR'
country_identifier("Iran, Islamic Republic of")  # → 'IR'

# Colloquial names
country_identifier("America")      # → 'US'
country_identifier("England")      # → 'GB'
country_identifier("Holland")      # → 'NL'

# Cultural variants
country_identifier("Deutschland")  # → 'DE'
country_identifier("México")       # → 'MX'
country_identifier("Brasil")       # → 'BR'

# Typos
country_identifier("Untied States")  # → 'US'
country_identifier("Grmany")         # → 'DE'
```

### Advanced Usage
```python
from entityidentity.countries.fuzzycountry import country_identifier, country_identifiers

# Different output formats
country_identifier("USA", to="ISO3")     # → 'USA'
country_identifier("USA", to="numeric")  # → '840'

# Batch processing
names = ["USA", "England", "Holland", "Germany"]
codes = country_identifiers(names, to="ISO2")
# → ['US', 'GB', 'NL', 'DE']

# Strict mode (no fuzzy matching)
country_identifier("Untied States", fuzzy=False)  # → None

# Custom threshold
country_identifier("Grmany", fuzzy_threshold=70)  # → 'DE'
```

## Testing

Run country resolution tests:
```bash
pytest tests/test_api.py::TestCountryIdentifier -v
pytest tests/test_api.py::TestCountryIdentifiers -v
```

## See Also

- [ISO 3166-1 alpha-2 codes](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)
- [country_converter documentation](https://github.com/konstantinstadler/country_converter)
- [pycountry documentation](https://github.com/flyingcircusio/pycountry)


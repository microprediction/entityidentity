# Places Module

Entity resolution for geographic administrative regions (admin1 level: states, provinces, regions) following the entityidentity functional, DataFrame-first design patterns.

## Overview

The places module provides deterministic entity resolution for admin1-level administrative divisions globally. It uses GeoNames as the authoritative source, compiles to Parquet for fast runtime lookups, and provides pure functional APIs over DataFrames.

## Features

- **Global Coverage**: ~5,000 admin1 regions across 250+ countries from GeoNames
- **Country Blocking**: 99%+ search space reduction via country-based filtering
- **Fast Resolution**: Cached Parquet with RapidFuzz scoring for robust matching
- **Alias Support**: Handles abbreviations and alternate names (e.g., "WA" → "Western Australia")
- **Deterministic IDs**: SHA-1 based place_id from country.admin1_code
- **Attribution**: CC-BY 4.0 compliant with GeoNames attribution

## Implementation Status

### ✅ Completed
- **Core modules**: All Python modules implemented (`placeapi.py`, `placeidentity.py`, `placenormalize.py`)
- **Data loader**: GeoNames admin1CodesASCII.txt downloader and parser
- **Build system**: Functional GeoNames → Parquet compilation pipeline
- **Resolution engine**: RapidFuzz-based matching with country blocking
- **Package integration**: Full integration with main entityidentity package

### Coverage Examples

| Country | Admin1 Examples | Count |
|---------|----------------|-------|
| **USA** | California, Texas, New York, ... | 51 |
| **Australia** | Western Australia, New South Wales, Queensland, ... | 8 |
| **South Africa** | Limpopo, Gauteng, Western Cape, ... | 9 |
| **Canada** | Ontario, Quebec, British Columbia, ... | 13 |
| **Brazil** | São Paulo, Minas Gerais, Pará, ... | 27 |

### 📋 Minor TODOs
- Add lat/lon coordinates from GeoNames allCountries.txt (optional)
- CLI tool for interactive place lookup
- Example notebooks demonstrating usage

## Installation

```bash
# Install entityidentity package
pip install -e .  # From entityidentity root

# Build the places database (downloads GeoNames data automatically)
cd entityidentity/places/data
python build_admin1.py
```

## Usage

### Basic Resolution

```python
from entityidentity import place_identifier

# Resolve with country hint (recommended)
result = place_identifier("Limpopo", country_hint="ZA")
# {'place_id': '...', 'country': 'ZA', 'admin1': 'Limpopo', 'admin1_code': 'LP', ...}

# Resolve abbreviation
result = place_identifier("WA", country_hint="AU")
# {'country': 'AU', 'admin1': 'Western Australia', 'admin1_code': 'WA', ...}

# Resolve without country hint (searches all countries)
result = place_identifier("Western Australia")
# {'country': 'AU', 'admin1': 'Western Australia', ...}

# US states
result = place_identifier("California", country_hint="US")
# {'country': 'US', 'admin1': 'California', 'admin1_code': 'CA', ...}
```

### Top-K Matching

```python
from entityidentity import match_place

# Get top candidates with scores
matches = match_place("Limpopo", k=3, country_hint="ZA")
# [
#   {'admin1': 'Limpopo', 'country': 'ZA', 'score': 100, ...},
#   ...
# ]

# Disambiguate abbreviations
matches = match_place("WA", k=3)  # Without country hint
# [
#   {'admin1': 'Western Australia', 'country': 'AU', 'score': 100, ...},
#   {'admin1': 'Washington', 'country': 'US', 'score': 100, ...},
#   ...
# ]
```

### Listing and Filtering

```python
from entityidentity import list_places

# List all admin1 regions in a country
za_places = list_places(country="ZA")
# DataFrame with 9 South African provinces

au_places = list_places(country="AU")
# DataFrame with 8 Australian states/territories

# List all places (no filter)
all_places = list_places()
# DataFrame with ~5,000 admin1 regions globally
```

### Text Extraction

```python
from entityidentity import extract_location

# Extract first place mention from text
text = "Mining operations in Limpopo province are expanding."
result = extract_location(text, country_hint="ZA")
# {'country': 'ZA', 'admin1': 'Limpopo', ...}

text = "Western Australia mining output increased."
result = extract_location(text, country_hint="AU")
# {'country': 'AU', 'admin1': 'Western Australia', ...}
```

## Data Model

### Core Fields

| Field | Description | Example |
|-------|-------------|---------|
| `place_id` | 16-hex deterministic hash | `a1b2c3d4e5f67890` |
| `place_key` | Human-readable slug | `za-limpopo`, `au-western-australia` |
| `country` | ISO 3166-1 alpha-2 code | `ZA`, `AU`, `US` |
| `admin1` | Display name | `Limpopo`, `Western Australia` |
| `admin1_norm` | Normalized name | `limpopo`, `western australia` |
| `admin1_code` | GeoNames admin1 code | `LP`, `WA`, `CA` |
| `ascii_name` | ASCII-safe name | Same as admin1 for ASCII names |
| `geonameid` | GeoNames ID | `964137`, `2058645` |
| `lat`, `lon` | Coordinates | (optional, future) |
| `attribution` | Data source | `Data from GeoNames (geonames.org)` |

### Alias Fields

- `alias1`, `alias2`, ..., `alias10`: Common abbreviations and alternate names
- Examples: "WA" for Western Australia, "CA" for California

## Architecture

```
places/
├── __init__.py              # Module exports
├── placeapi.py              # Public API (functional)
├── placeidentity.py         # Resolution logic with RapidFuzz
├── placenormalize.py        # Name normalization utilities
└── data/
    ├── build_admin1.py      # GeoNames → Parquet compiler
    ├── admin1CodesASCII.txt # Downloaded from GeoNames (auto)
    └── places.parquet       # Compiled database
```

## Resolution Strategy

1. **Country Blocking**: Filter by country_hint (5000 → ~50 candidates)
   - If country_hint not provided, tries country_identifier() first
   - Falls back to global search if no country match

2. **Prefix Blocking**: Filter by first 3 normalized characters

3. **Exact Matching**: Check normalized admin1 and aliases

4. **Fuzzy Scoring**: RapidFuzz WRatio on names + aliases

5. **Threshold**: Return match if score ≥ 90 (configurable)

## Development

### Rebuilding the Database

```bash
cd entityidentity/places/data
python build_admin1.py
```

This will:
1. Download `admin1CodesASCII.txt` from GeoNames (if not present)
2. Parse and validate the data
3. Generate place_id hashes
4. Expand aliases
5. Write `places.parquet`

### Running Tests

```bash
# Run all place tests
pytest tests/places/ -v

# Run with coverage
pytest tests/places/ --cov=entityidentity.places
```

## Data Source

### GeoNames (Priority 1)

- **URL**: https://download.geonames.org/export/dump/admin1CodesASCII.txt
- **Coverage**: ~5,000 admin1 regions globally
- **License**: CC-BY 4.0 (requires attribution)
- **Attribution**: "Data from GeoNames (geonames.org)"
- **Update**: Daily exports available
- **Format**: Tab-separated (country.admin1_code, name, ascii_name, geonameid)

### Attribution Compliance

All outputs include `attribution` field with:
```
Data from GeoNames (geonames.org)
```

This is required by the CC-BY 4.0 license.

## Performance

- **Load time**: <100ms (cached via lru_cache)
- **Query latency**: <50ms with country hint, <200ms without
- **Memory footprint**: ~2-5MB (Parquet + DataFrame)
- **Blocking efficiency**: 99%+ reduction (5000 → ~50 with country hint)

## Country Integration

The places module integrates with the countries module for flexible country resolution:

```python
from entityidentity import place_identifier

# Works with country names (resolved via country_identifier)
place_identifier("Limpopo", country_hint="South Africa")
# Resolves "South Africa" → "ZA", then matches Limpopo

# Works with ISO codes
place_identifier("Limpopo", country_hint="ZA")
# Direct country code match
```

## Related Documentation

- [DATA_SOURCES.md](../../../DATA_SOURCES.md) - Data source details and licensing
- [IMPLEMENTATION_PLAN.md](../../../IMPLEMENTATION_PLAN.md) - Section B.4 (Places API)
- [entityidentity README](../../../README.md) - Main package documentation

## License

Same as entityidentity package. Data attribution per GeoNames CC-BY 4.0.

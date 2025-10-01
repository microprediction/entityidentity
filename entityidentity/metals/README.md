# Metals Ontology Module

Entity resolution and ontology for metals, alloys, and metal compounds following the entityidentity functional, DataFrame-first design patterns.

## Overview

The metals module provides deterministic entity resolution for metal names, symbols, forms, and commercial specifications. It uses YAML as the source of truth, compiles to Parquet for fast runtime lookups, and provides pure functional APIs over DataFrames.

## Features

- **Deterministic Resolution**: Consistent metal identification across symbols, names, aliases, and trade terms
- **Supply Chain Clustering**: Metals organized by geological co-occurrence and processing chains (e.g., porphyry copper → Mo, Re, Se, Te)
- **Commercial Standards**: Proper units and pricing basis (e.g., APT in $/mtu WO₃, ferrochrome in $/lb Cr contained)
- **Multi-form Support**: Elements, compounds, alloys (e.g., Li metal vs Li₂CO₃, tungsten vs APT)
- **Fast Resolution**: Cached Parquet with RapidFuzz scoring for robust matching
- **Text Extraction**: Extract metal references from unstructured text

## Installation

```bash
# Build the metals database from YAML source
cd entityidentity/metals/data
python build_metals.py

# This creates metals.parquet from metals.yaml
```

## Core API Functions (Section 5 of METALS_ONTOLOGY_PLAN.md)

### metal_identifier(name, *, cluster=None, category=None, threshold=90) -> dict | None

Resolve a metal name to its canonical form.

```python
from entityidentity import metal_identifier

# Simple resolution
result = metal_identifier("Pt")
# Returns: {'metal_id': '...', 'name': 'Platinum', 'symbol': 'Pt', ...}

# Resolution with hints
result = metal_identifier("chrome", category="ferroalloy")
# Returns: {'name': 'Ferrochrome', 'code': 'FeCr', ...}

# Resolution with cluster hint
result = metal_identifier("gold", cluster="porphyry_copper_chain")
# Returns gold entry with cluster context

# Returns None if no match above threshold
result = metal_identifier("unobtainium", threshold=95)
# Returns: None
```

### match_metal(name, *, k=5) -> list[dict]

Get top-K candidate matches with scores for review UIs.

```python
from entityidentity import match_metal

candidates = match_metal("tungsten", k=3)
# Returns: [
#   {'name': 'Tungsten', 'score': 100, ...},
#   {'name': 'Ferrotungsten', 'score': 85, ...},
#   {'name': 'Ammonium paratungstate', 'score': 70, ...}
# ]
```

### list_metals(cluster=None, category=None) -> pd.DataFrame

List metals filtered by cluster or category.

```python
from entityidentity import list_metals
import pandas as pd

# List all PGM metals
pgm_metals = list_metals(category="pgm")
# Returns DataFrame with Pt, Pd, Rh, Ru, Ir, Os

# List metals in porphyry copper chain
copper_chain = list_metals(cluster="porphyry_copper_chain")
# Returns DataFrame with Cu, Mo, Re, Se, Te, Au

# List all battery metals
battery_metals = list_metals(category="battery")
# Returns DataFrame with Li, Co, Ni, graphite forms, etc.
```

### load_metals(path=None) -> pd.DataFrame

Load the compiled metals database. This is cached after first call using @lru_cache.

```python
from entityidentity import load_metals

# Load default database
df = load_metals()

# Load custom database
df = load_metals("path/to/custom/metals.parquet")
```

## Text Extraction API (Section 8)

```python
from entityidentity.metals import metal_identifier

# Resolve by symbol
result = metal_identifier("Pt")
# {'metal_id': 'abc123...', 'name': 'Platinum', 'symbol': 'Pt', ...}

# Resolve by name
result = metal_identifier("copper")
# {'metal_id': 'def456...', 'name': 'Copper', 'symbol': 'Cu', ...}

# Resolve trade specifications
result = metal_identifier("APT 88.5%")
# {'name': 'Ammonium paratungstate', 'code': 'WO3', 'default_basis': '$/mtu WO3', ...}

# Resolve with hints
result = metal_identifier("lithium", category="battery")
# Returns lithium metal or compounds based on context
```

### Top-K Matching

```python
from entityidentity.metals import match_metal

# Get top 5 candidates with scores
matches = match_metal("wolfram", k=5)
# [{'name': 'Tungsten', 'score': 95, ...}, ...]
```

### Listing and Filtering

```python
from entityidentity.metals import list_metals

# List all PGM metals
pgms = list_metals(cluster="pgm_complex")
# DataFrame with Pt, Pd, Rh, Ru, Ir, Os

# List battery metals
battery = list_metals(category="battery")
# DataFrame with Li forms, Co, Ni, graphite, etc.
```

## Data Model

### Metal Fields

| Field | Description | Example |
|-------|-------------|---------|
| `metal_id` | 16-hex deterministic hash | `a1b2c3d4e5f67890` |
| `metal_key` | Human-readable slug | `lithium-carbonate` |
| `symbol` | IUPAC element symbol | `Pt`, `Cu`, `Li` |
| `name` | Display name | `Platinum`, `Ammonium paratungstate` |
| `formula` | Chemical formula | `Li2CO3`, `(NH4)10[H2W12O42]·xH2O` |
| `code` | Commercial code | `WO3` for APT, `Li2CO3` |
| `category_bucket` | Category taxonomy | `precious`, `base`, `battery`, `pgm`, `ree` |
| `cluster_id` | Supply chain cluster | `porphyry_copper_chain`, `pgm_complex` |
| `default_unit` | Standard trade unit | `toz`, `lb`, `mtu`, `kg` |
| `default_basis` | Pricing basis | `$/toz`, `$/mtu WO3`, `$/lb Cr contained` |

### Supply Chain Clusters

Metals are organized by geological co-occurrence and processing chains:

- **pgm_complex**: Pt, Pd, Rh, Ru, Ir, Os (Bushveld/Great Dyke)
- **porphyry_copper_chain**: Cu → Mo → Re; Cu anode slimes → Se/Te/Au
- **lead_zinc_chain**: Pb-Zn → Ag, Cd, In, Ge, Bi, Sb (smelter by-products)
- **rare_earth_chain**: REE deposits & ion-adsorption clays
- **lithium_chain**: Li brines & hard-rock sources
- **ferroalloy_chain**: Chromite/Mn/VTM → ferroalloys

See `data/supply_chain_clusters.yaml` for complete mapping.

## Current Metal Coverage

### Precious & PGMs (8 metals)
- ✅ Platinum, Palladium, Rhodium, Ruthenium, Iridium, Osmium
- ✅ Gold, Silver

### Base Metals & Copper Chain (7 metals)
- ✅ Copper, Molybdenum, Rhenium (by-product)
- ✅ Selenium, Tellurium (from Cu anode slimes)
- ⏳ Gold (as co-product)

### Lead-Zinc Chain (7 metals)
- ✅ Zinc, Lead
- ✅ Cadmium, Indium, Germanium, Bismuth, Antimony

### Battery Metals (2 metals)
- ✅ Lithium carbonate
- ⏳ Lithium metal, hydroxide
- ⏳ Cobalt, Nickel forms
- ⏳ Graphite

### Specialty/Industrial (2 metals)
- ✅ Ammonium paratungstate (APT)
- ✅ Ferrochrome
- ⏳ Other ferroalloys

### Rare Earths (1 metal)
- ✅ Neodymium-Praseodymium (NdPr)
- ⏳ Individual REEs

## Architecture

```
metals/
├── __init__.py              # Module exports
├── metalapi.py              # Public API (functional)
├── metalidentity.py         # Resolution logic
├── metalnormalize.py        # Name normalization
├── metalextractor.py        # Text extraction (TODO)
└── data/
    ├── metals.yaml          # Source of truth
    ├── supply_chain_clusters.yaml
    ├── build_metals.py      # YAML → Parquet compiler
    └── metals.parquet       # Compiled data
```

## Resolution Strategy

1. **Blocking**: Narrow candidates via symbol, category, name prefix, cluster
2. **Scoring**: RapidFuzz WRatio on names and aliases
3. **Threshold**: Return match if score ≥ 90 (configurable)
4. **Hints**: Support "metal:form" syntax (e.g., "lithium:carbonate")

## Development

### Building the Parquet file

```bash
cd entityidentity/metals/data
python build_metals.py
```

This validates the YAML and generates `metals.parquet`.

### Adding new metals

1. Edit `data/metals.yaml` following the schema
2. Run `build_metals.py` to compile and validate
3. Test resolution with the new entries

### Running tests

```bash
pytest tests/test_metals.py  # TODO: Create test suite
```

## Standards & Sources

- **Element names/symbols**: IUPAC periodic table
- **By-product relationships**: USGS mineral commodity summaries
- **Trade units/basis**: Fastmarkets price specifications
- **HS codes**: WCO HS 2022 (6-digit)

## Contributing

When adding metals:
1. Verify element symbols against IUPAC
2. Document by-product relationships with USGS citations
3. Use market-standard units/basis (check Fastmarkets)
4. Assign to single supply chain cluster
5. Include common aliases and trade terms

## Related Documentation

- [METALS_ONTOLOGY_PLAN.md](../../../METALS_ONTOLOGY_PLAN.md) - Complete technical specification
- [METALS_IMPLEMENTATION_PROMPTS.md](../../../METALS_IMPLEMENTATION_PROMPTS.md) - Implementation guide
- [entityidentity README](../../../README.md) - Main package documentation

## License

Same as entityidentity package.
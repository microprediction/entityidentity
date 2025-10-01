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

## Current Implementation Status

### ✅ Completed (All 12 Prompts)
- **Core modules**: All Python modules implemented (`metalapi.py`, `metalidentity.py`, `metalnormalize.py`, `metalextractor.py`)
- **Data schemas**: YAML source files with 50 metals and 14 supply chain clusters
- **Build system**: Functional YAML → Parquet compilation pipeline
- **Resolution engine**: RapidFuzz-based matching with blocking strategies
- **Text extraction**: NER-style metal detection from unstructured text
- **Test suite**: Comprehensive tests in `test_metals.py`
- **Package integration**: Full integration with main entityidentity package

### Metal Coverage (50 metals implemented)

#### Precious & PGMs (8 metals) ✅
- All 6 PGMs: Platinum, Palladium, Rhodium, Ruthenium, Iridium, Osmium
- Precious: Gold, Silver

#### Base & Copper Chain (7 metals) ✅
- Copper, Molybdenum, Rhenium (by-product)
- Selenium, Tellurium (from Cu anode slimes)
- Gold (as co-product in porphyry copper)

#### Lead-Zinc Chain (7 metals) ✅
- Primary: Zinc, Lead
- By-products: Silver, Cadmium, Indium, Germanium, Bismuth, Antimony

#### Battery Metals (11 forms/metals) ✅
- Lithium (3 forms): metal, carbonate, hydroxide
- Cobalt (2 forms): metal, sulfate
- Nickel (2 forms): metal, sulfate
- Graphite (2 forms): natural, synthetic

#### Rare Earths (12 metals) ✅
- Light REEs: Lanthanum, Cerium, Praseodymium, Neodymium, Samarium
- Heavy REEs: Europium, Gadolinium, Terbium, Dysprosium, Yttrium
- Mixed: Neodymium-Praseodymium (NdPr)

#### Ferroalloys (5 metals) ✅
- Ferrochrome, Ferromanganese, Ferrovanadium
- Ferrotungsten, Ferromolybdenum

#### Specialty Metals (5 metals) ✅
- Tungsten, Ammonium paratungstate (APT)
- Tantalum, Niobium, Vanadium

### 📋 Minor TODOs
- Example notebooks demonstrating usage
- CLI tool for interactive resolution
- Additional HS codes and PRA references
- More metal forms and compounds (e.g., oxides, chlorides)

## Installation

```bash
# Install entityidentity package
pip install -e .  # From entityidentity root

# Build/rebuild the metals database
cd entityidentity/metals/data
python build_metals.py
```

## Usage

### Basic Resolution

```python
from entityidentity import metal_identifier

# Resolve by symbol
result = metal_identifier("Pt")
# {'metal_id': '...', 'name': 'Platinum', 'symbol': 'Pt', ...}

# Resolve by name
result = metal_identifier("copper")
# {'name': 'Copper', 'symbol': 'Cu', ...}

# Resolve trade specifications
result = metal_identifier("APT 88.5%")
# {'name': 'Ammonium paratungstate', 'code': 'WO3', 'default_basis': '$/mtu WO3', ...}

# Resolve with category hint
result = metal_identifier("chrome", category="ferroalloy")
# {'name': 'Ferrochrome', 'code': 'FeCr', ...}
```

### Top-K Matching

```python
from entityidentity import match_metal

# Get top candidates with scores
matches = match_metal("wolfram", k=3)
# [
#   {'name': 'Tungsten', 'score': 100, ...},
#   {'name': 'Ferrotungsten', 'score': 85, ...},
#   {'name': 'Ammonium paratungstate', 'score': 70, ...}
# ]
```

### Listing and Filtering

```python
from entityidentity import list_metals

# List all PGM metals
pgms = list_metals(category="pgm")
# DataFrame with Pt, Pd, Rh, Ru, Ir, Os

# List metals in a supply chain
copper_chain = list_metals(cluster="porphyry_copper_chain")
# DataFrame with Cu, Mo, Re, Se, Te, Au

# List battery metals
battery = list_metals(category="battery")
# DataFrame with Li, Co, Ni, graphite forms
```

### Text Extraction

```python
from entityidentity import extract_metals_from_text

text = "The battery uses NMC cathodes with high nickel content and lithium carbonate from Chile."
metals = extract_metals_from_text(text)
# [
#   {'query': 'nickel', 'span': (40, 46), 'hint': 'element'},
#   {'query': 'lithium carbonate', 'span': (59, 76), 'hint': 'compound'}
# ]
```

## Data Model

### Core Fields

| Field | Description | Example |
|-------|-------------|---------|
| `metal_id` | 16-hex deterministic hash | `a1b2c3d4e5f67890` |
| `metal_key` | Human-readable slug | `lithium-carbonate` |
| `symbol` | IUPAC element symbol | `Pt`, `Cu`, `Li` |
| `name` | Display name | `Platinum`, `Ammonium paratungstate` |
| `formula` | Chemical formula | `Li2CO3`, `(NH4)10[H2W12O42]·xH2O` |
| `code` | Commercial code | `WO3`, `FeCr`, `NdPr` |
| `category_bucket` | Category | `precious`, `base`, `battery`, `pgm`, `ree`, `ferroalloy`, `specialty` |
| `cluster_id` | Supply chain cluster | `porphyry_copper_chain`, `pgm_complex` |
| `default_unit` | Trade unit | `toz`, `lb`, `mtu`, `kg`, `mt` |
| `default_basis` | Pricing basis | `$/toz`, `$/mtu WO3`, `$/lb Cr contained` |

### Supply Chain Clusters (14 clusters)

- **pgm_complex**: Pt, Pd, Rh, Ru, Ir, Os
- **porphyry_copper_chain**: Cu → Mo → Re; Se/Te/Au from anode slimes
- **lead_zinc_chain**: Pb-Zn → Ag, Cd, In, Ge, Bi, Sb
- **nickel_cobalt_chain**: Ni-Co sulfides & laterites
- **rare_earth_chain**: REE deposits & ion-adsorption clays
- **lithium_chain**: Li brines & hard-rock
- **ferroalloy_chain**: Chromite/Mn/VTM → ferroalloys
- **sn_ta_nb_w_chain**: Sn-Ta-Nb-W pegmatite/skarn
- **carbon_silicon_chain**: Graphite & silicon
- Plus 5 others (see `data/supply_chain_clusters.yaml`)

## Architecture

```
metals/
├── __init__.py              # Module exports
├── metalapi.py              # Public API (functional)
├── metalidentity.py         # Resolution logic with RapidFuzz
├── metalnormalize.py        # Name normalization utilities
├── metalextractor.py        # Text extraction and NER
└── data/
    ├── metals.yaml          # Source of truth (50 metals)
    ├── supply_chain_clusters.yaml  # Cluster definitions
    ├── build_metals.py      # YAML → Parquet compiler
    └── metals.parquet       # Compiled database
```

## Resolution Strategy (Section 6)

1. **Blocking**: Filter candidates by symbol, category, name prefix, cluster
2. **Scoring**: RapidFuzz WRatio on names and aliases
3. **Threshold**: Return match if score ≥ 90 (configurable)
4. **Hints**: Support "metal:form" syntax (e.g., "lithium:carbonate")

## Development

### Adding New Metals

1. Edit `data/metals.yaml` following the schema
2. Run `python build_metals.py` to compile and validate
3. Test with `pytest tests/test_metals.py`

### Running Tests

```bash
# Run all metal tests
pytest tests/test_metals.py -v

# Run with coverage
pytest tests/test_metals.py --cov=entityidentity.metals
```

## Standards & Sources

- **Element names/symbols**: IUPAC periodic table
- **By-product relationships**: USGS mineral commodity summaries
- **Trade units/basis**: Fastmarkets price specifications
- **HS codes**: WCO HS 2022 (when available)

## Contributing

When adding metals:
1. Verify element symbols against IUPAC
2. Document by-product relationships with USGS citations
3. Use market-standard units/basis (check Fastmarkets)
4. Assign to single supply chain cluster
5. Include common aliases and trade terms
6. Run tests to ensure no regressions

## Related Documentation

- [METALS_ONTOLOGY_PLAN.md](../../../METALS_ONTOLOGY_PLAN.md) - Complete technical specification
- [METALS_IMPLEMENTATION_PROMPTS.md](../../../METALS_IMPLEMENTATION_PROMPTS.md) - Implementation guide
- [entityidentity README](../../../README.md) - Main package documentation

## License

Same as entityidentity package.
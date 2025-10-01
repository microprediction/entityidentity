# Metals Ontology Plan for entityidentity

This document outlines the complete plan for adding a metals ontology to the entityidentity repository, following the existing functional, DataFrame-first design patterns.

## Overview

The metals ontology provides deterministic entity resolution for metal names, symbols, forms, and commercial specifications. It follows the entityidentity pattern of using YAML as source-of-truth, compiling to Parquet for fast runtime lookups, and providing pure functional APIs over DataFrames.

## Why This Architecture

- **Functional, no classes**: Pure functions over `pd.DataFrame`, cached loaders, deterministic merges
- **YAML → Parquet**: Small `metals.yaml` (easy to diff/review) compiled to `metals.parquet` for fast, memory-resident lookups with `@lru_cache`
- **Deterministic + human-readable IDs**:
  - `metal_id = sha1(normalize(name) + "|metal")[:16]` for stable joins
  - `metal_key` (slug) for readable keys in logs/URIs
- **Effective blocking**: Exact symbol, category bucket, name prefix, optional supply-chain cluster; final pick via `RapidFuzz process.extractOne(..., scorer=fuzz.WRatio)`
- **Standards-anchored**:
  - Canonical element names/symbols = IUPAC
  - By-product & chain facts = USGS
  - HS 2022 codes = WCO HS
  - PRA spec field shape & units = Fastmarkets

## 1. Repository Layout

```
entityidentity/
  metals/
    __init__.py
    metalapi.py              # public API (pure functions)
    metalidentity.py         # block/score/decide
    metalnormalize.py        # normalize_name(), canonicalize_name(), slugify()
    metalextractor.py        # optional NER-ish text helpers
    data/
      metals.yaml            # SOURCE OF TRUTH (hand-edited)
      supply_chain_clusters.yaml
      build_metals.py        # compiles YAML -> metals.parquet (and validates)
      metals.parquet         # compiled, flat, cached by API
```

## 2. YAML Schema (data/metals.yaml)

```yaml
version: 0.2
metals:
  - name: "Platinum"
    symbol: "Pt"
    metal_key: "platinum"
    formula: null             # elements: usually null
    code: null                # use for non-elements e.g., "WO3", "Li2CO3", "NdPr"
    category_bucket: "pgm"    # "precious|base|battery|pgm|ree|ferroalloy|specialty|industrial"
    cluster_id: "pgm_complex" # single supply-chain cluster
    default_unit: "toz"
    default_basis: "$/toz"
    hs6: null
    pra_hint: null
    aliases:
      - "Pt"
    notes: ""
    sources: ["IUPAC"]
  - name: "Ammonium paratungstate"
    symbol: null
    metal_key: "apt"
    formula: "(NH4)10[H2W12O42]·xH2O"
    code: "WO3"                 # commercial basis uses contained WO3
    category_bucket: "specialty"
    cluster_id: "sn_ta_nb_w_chain"
    default_unit: "mtu"         # metric tonne unit
    default_basis: "$/mtu WO3"  # market standard basis for APT quotes
    hs6: null
    pra_hint: "MB-W-0001"       # Fastmarkets APT cif Rotterdam/Baltimore
    aliases: ["APT", "APT 88.5%"]
    notes: "Spec usually ≥88.5% WO3"
    sources: ["Fastmarkets","USGS"]
```

### Key Fields

- `category_bucket`: Light taxonomy for blocking
- `formula` + `code`: Distinguish chemical form vs commercial code
- `default_unit` + `default_basis`: Canonical market quotation standards
- `cluster_id`: Single supply-chain cluster assignment

## 3. Compiled Parquet Schema (metals.parquet)

All columns are strings (flat, denormalized, Parquet-friendly):

| Column | Purpose |
|--------|---------|
| metal_id | 16-hex deterministic hash |
| metal_key | Human-readable slug (e.g., lithium-carbonate, tungsten-apt) |
| symbol | IUPAC element symbol where applicable |
| name, name_norm | Display & aggressive match forms |
| formula, code | Chemical formula; commercial short code |
| category_bucket | precious\|base\|battery\|pgm\|ree\|ferroalloy\|specialty\|industrial |
| cluster_id | Single supply-chain cluster ID |
| group_name | Optional family label |
| default_unit, default_basis | Canonical unit/basis |
| hs6 | WCO HS 2022 code (6-digit, optional) |
| pra_hint | Optional PRA handle |
| alias1...alias10 | Common aliases |
| notes | Free text |
| source_priority | Merged provenance |

## 4. Supply-Chain Clusters

Single assignment per metal for shock propagation modeling:

```yaml
clusters:
  pgm_complex: "Bushveld/Great Dyke + Ni-Cu sulfide co-products"
  porphyry_copper_chain: "Cu→Mo→Re; Cu anode slimes → Se/Te/Au"
  lead_zinc_chain: "Pb-Zn smelter by-products (Ag,Cd,In,Ge,Bi,Sb)"
  nickel_cobalt_chain: "Ni–Co sulfides & laterites (+Sc residues)"
  mineral_sands_chain: "Ilmenite/Rutile/Zircon (Ti/Zr; Hf separation)"
  ferroalloy_chain: "Chromite/Mn/VTM → ferroalloys"
  sn_ta_nb_w_chain: "Sn–Ta–Nb–W pegmatite/skarn belts"
  rare_earth_chain: "REE deposits & ion-adsorption clays"
  aluminum_chain: "Bauxite→Alumina→Al (Ga from Bayer liquor)"
  lithium_chain: "Li brines & hard-rock"
  evaporite_chain: "K/Na/Mg from evaporites & brines"
  carbon_silicon_chain: "Graphite & silicon (quartz reduction)"
  specialty_industrials: "Be,Ba,Sr,Ca,Cs,Rb stand-alone routes"
  nuclear_chain: "Uranium mining/milling"
```

### Key Co-Product Relationships (USGS-backed)

- **Re** from Mo roaster flue dust (porphyry Cu)
- **Se/Te** recovered from Cu anode slimes
- **In** mainly from Zn processing residues
- **Ga** from Bayer liquor (Al production)
- **Hf** separated from Zr downstream

## 5. Public API

```python
# metalapi.py
from functools import lru_cache
import pandas as pd

@lru_cache(maxsize=1)
def load_metals(path: str | None = None) -> pd.DataFrame:
    """Load compiled metals.parquet into memory"""
    pass

def metal_identifier(name: str, *, cluster: str | None = None,
                     category: str | None = None, threshold: int = 90) -> dict | None:
    """Return canonical metal row as dict or None."""
    pass

def match_metal(name: str, *, k: int = 5) -> list[dict]:
    """Top-K candidates + scores (for review UIs)."""
    pass

def list_metals(cluster: str | None = None, category: str | None = None) -> pd.DataFrame:
    """List metals filtered by cluster/category"""
    pass
```

## 6. Resolution Strategy

Blocking approach (metalidentity.py):
1. Exact symbol match
2. Category bucket filter
3. Name prefix (first 3 chars normalized)
4. Optional cluster_id filter
5. Final scoring via RapidFuzz WRatio on names + aliases

Support for "metal:form" hints (e.g., "lithium:carbonate")

## 7. Normalization Functions

```python
# metalnormalize.py
def normalize_name(s: str) -> str:  # aggressive for matching
def canonicalize_name(s: str) -> str:  # for display
def slugify(s: str) -> str:  # "Lithium carbonate" -> "lithium-carbonate"
```

## 8. Text Extraction

Optional helper for extracting metals from unstructured text:

```python
# metalextractor.py
def extract_metals_from_text(text: str, cluster_hint: str | None = None) -> list[dict]:
    """
    Heuristics:
      - Element symbols & slashes: "Pt/Pd", "Cu", "Ni-Co"
      - Trade specs: "APT 88.5%", "P1020 aluminum", "SHG zinc"
      - Chemical forms: "lithium carbonate", "NdPr"
    Return: [{query:"pt", span:(...), hint:"symbol"}, ...]
    """
```

## 9. Validation

Unit/basis consistency checks:

```python
def validate_basis(unit: str, basis: str) -> bool:
    """
    Examples:
      - APT: unit="mtu", basis="$ / mtu WO3" (OK)
      - FeCr: unit="lb",  basis="$ / lb Cr contained" (OK)
      - Precious: unit="toz", basis="$ / toz" (OK)
    """
```

## 10. Source Priority

Deterministic merge hierarchy:

```python
SOURCE_PRIORITY = {
  "IUPAC": 1,        # element names & symbols
  "USGS":  2,        # chains / by-products / deposit models
  "WCO-HS":3,        # HS 2022
  "Fastmarkets": 4,  # PRA price spec hooks
  "Other": 5,
}
```

## 11. Build Process

`data/build_metals.py`:
1. Load metals.yaml, supply_chain_clusters.yaml
2. Normalize & slugify names; compute metal_id
3. Expand aliases into alias1…alias10
4. Validate (unit,basis) combos
5. Write metals.parquet (string dtypes)
6. Emit validation report

## 12. Testing Strategy

Core test cases:
- `test_symbol_exact()` — Pt → Platinum
- `test_aliases()` — "wolfram" → tungsten
- `test_trade_terms()` — "APT 88.5%" → APT with correct basis
- `test_colon_hints()` — "lithium:carbonate" → lithium carbonate
- `test_cluster_filtering()` — resolve within specific cluster
- `test_unit_basis_validation()` — verify market standards

## 13. Initial Seed Data

Priority metals to include:
1. **PGM complex**: Pt, Pd, Rh, Ru, Ir, Os
2. **Porphyry copper chain**: Cu, Mo, Re, Se, Te
3. **Lead-zinc chain**: Zn, Pb, Ag, Cd, In, Ge, Bi, Sb
4. **Battery metals**: Li (metal, carbonate, hydroxide), Co, Ni, Graphite
5. **REE chain**: La, Ce, Pr, Nd, Sm, Eu, Gd, Tb, Dy, Y, NdPr
6. **Ferroalloys**: FeCr, FeMn, FeV, FeW, FeMo
7. **Specialty**: W, APT, Ta, Nb, V, Ti, Zr, Hf

## 14. Future Extensions

- Cross-references: xref_cas, xref_wikidata columns
- Product specifications layer (separate from base metals)
- Snowflake/BigQuery warehouse schema
- Review UI for alias approval
- Integration with existing entityidentity patterns

## Implementation Notes

- Follow entityidentity/countries/ patterns exactly
- Keep everything functional and DataFrame-based
- Use @lru_cache for performance
- Maintain deterministic behavior
- Prioritize simplicity and maintainability

## References

- **IUPAC**: Periodic table, element names/symbols
- **USGS**: Supply chains, by-product relationships, deposit models
- **Fastmarkets**: Market price specifications, units/basis standards
- **WCO**: HS 2022 classification codes
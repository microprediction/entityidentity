# EntityIdentity Extension Plan - New Entity Modules

**Status**: Planning
**Target**: EntityIdentity v0.2.0
**Aligned with**: Current repo structure (companies/, countries/, metals/ pattern)

---

## Executive Summary

This plan extends EntityIdentity to resolve **6 new entity types** critical for metals market intelligence:

1. **Baskets** - Multi-metal composites (PGM 4E/5E, NdPr, etc.) with partial splits
2. **Periods** - Temporal normalization (quarters, halves, weeks, ISO dates)
3. **Places** - Geographic entity resolution (countries + admin1 states/provinces)
4. **Units** - Unit conversion + basis enforcement (FeCr $/lb Cr, APT $/mtu WO3)
5. **Instruments** - Price ticker resolution from ticker_references.parquet ground truth
6. **Facilities** - Probabilistic facility linking (company + location → specific site)

All modules **mirror existing patterns** (companies/, metals/, countries/) with consistent APIs, blocking strategies, LRU caching, and comprehensive tests.

---

## A. Repository Structure (New Modules)

Following existing pattern: `entityidentity/{entity_type}/{module_files} + data/ + tests/`

```
entityidentity/
  companies/           # ✓ Existing - no changes
  countries/           # ✓ Existing - no changes
  metals/              # ✓ Existing - no changes

  baskets/             # ⭐ NEW
    __init__.py
    basketapi.py       # public API (basket_identifier, match_basket, list_baskets, load_baskets)
    basketidentity.py  # blocking/scoring/decision pipeline
    basketnormalize.py # normalize_basket_name(), canonicalize_basket_name()
    data/
      baskets.yaml     # source of truth (named baskets & splits)
      build_baskets.py # YAML → baskets.parquet builder
      baskets.parquet  # generated data (git ignored)
      samples/         # sample baskets for tests
    README.md          # basket module docs

  period/              # ⭐ NEW
    __init__.py
    periodapi.py       # public API (period_identifier, extract_periods)
    periodidentity.py  # text → canonical Period resolver
    periodnormalize.py # normalization helpers
    README.md

  places/              # ⭐ NEW
    __init__.py
    placeapi.py        # public API (place_identifier, extract_location)
    placeidentity.py   # admin1 matching + geocoding
    placenormalize.py  # normalization helpers
    data/
      admin1.parquet   # ~5000 states/provinces worldwide
      build_admin1.py  # Natural Earth → parquet builder
      samples/         # sample data for tests
    README.md

  units/               # ⭐ NEW
    __init__.py
    unitapi.py         # public API (normalize_unit)
    unitnorm.py        # conversion + canonical basis enforcement
    unitconfig.yaml    # metal-specific basis rules (FeCr, APT, etc.)
    README.md

  instruments/         # ⭐ NEW
    __init__.py
    instrumentapi.py   # public API (instrument_identifier, match_instruments, list_instruments, load_instruments)
    instrumentidentity.py  # blocking/scoring on tickers & names
    instrumentloaders.py   # loads gs://gsmc-market-data/ticker_references.parquet
    README.md

  facilities/          # ⭐ NEW (linker, not resolver)
    __init__.py
    facilityapi.py     # public API (link_facility)
    facilitylink.py    # probabilistic linker: company/place → facility
    README.md

tests/
  companies/           # ✓ Existing
  baskets/             # ⭐ NEW
    test_basketapi.py
    test_normalization.py
  test_period.py       # ⭐ NEW
  test_places.py       # ⭐ NEW
  test_units.py        # ⭐ NEW
  test_instruments.py  # ⭐ NEW
  test_facilities.py   # ⭐ NEW (skip if no facilities master)
```

---

## B. Public APIs (Signatures & Behavior)

All modules expose **consistent patterns** mirroring companies/metals:
- `{entity}_identifier()` - Primary API
- `match_{entity}()` - Get candidates with scores
- `list_{entity}s()` - Browse/filter database
- `load_{entity}s()` - Load full DataFrame

### 1. Metals API (Existing - Minor Additions Only)

**Current State**: ✓ Already implemented
**Changes**: Add optional cluster/category hints (already in your report)

```python
# metals/metalapi.py (KEEP EXISTING, verify signatures)
metal_identifier(
    name: str,
    *,
    cluster: Optional[str] = None,      # "battery", "porphyry_copper", etc.
    category: Optional[str] = None,     # "base", "precious", "rare_earth", "specialty"
    threshold: int = 90
) -> Optional[dict]

match_metal(name: str, *, k: int = 5) -> list[dict]
list_metals(cluster: Optional[str] = None, category: Optional[str] = None) -> pd.DataFrame
load_metals(path: Optional[Union[str, Path]] = None) -> pd.DataFrame
```

**Form Hints**: Already supported ("lithium:carbonate" → Li2CO3)

**Returns**:
```python
{
    "name": "Lithium carbonate",
    "symbol": None,
    "formula": "Li2CO3",
    "category_bucket": "specialty",
    "cluster_id": "battery",
    "score": 100
}
```

---

### 2. Baskets API (NEW - Named Multi-Metal Specs)

**Purpose**: Resolve "PGM 4E", "NdPr", "REE basket" to constituent metals with splits (when known).

```python
# baskets/basketapi.py
def basket_identifier(name: str) -> Optional[dict]:
    """Resolve basket name to canonical basket with metals.

    Examples:
        basket_identifier("PGM 4E")  # Pt, Pd, Rh, Au (equal splits unknown)
        basket_identifier("NdPr")    # Nd, Pr (ratio varies by source)

    Returns:
        {
            "basket_id": "PGM_4E",
            "label": "PGM 4E",
            "metals": [
                {"metal_id": "Pt", "share": None},
                {"metal_id": "Pd", "share": None},
                {"metal_id": "Rh", "share": None},
                {"metal_id": "Au", "share": None}
            ],
            "unknown_share": None,  # Fraction of basket with unspecified metals
            "score": 98
        }
    """

def match_basket(name: str, k: int = 5) -> list[dict]:
    """Get top-K basket candidates with scores."""

def list_baskets(search: Optional[str] = None) -> pd.DataFrame:
    """List available baskets, optionally filtered."""

def load_baskets(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load baskets database."""
```

**Data Source**: `baskets/data/baskets.yaml` (human-editable)

**Schema** (baskets.parquet):
```
basket_id: str           # Primary key (slugified label)
label: str               # Display name ("PGM 4E")
alias1-5: Optional[str]  # Variations
metals_json: str         # JSON list: [{"metal_id": "Pt", "share": null}, ...]
notes: Optional[str]     # Comments/source
```

**Blocking Strategy**:
- Prefix match on normalized label + aliases
- Optional fuzzy scoring if needed (baskets list is small ~20-50)

**Facility Overrides** (v2):
- Baskets return `share=None` for unknown splits
- Facility-specific prill splits can override (e.g., Mogalakwena's 4E ratio)
- This is handled by `facilities/facilitylink.py`, not baskets resolver

---

### 3. Period API (NEW - Temporal Normalization)

**Purpose**: Resolve any date-ish text to canonical Period with start/end timestamps.

```python
# period/periodapi.py
def period_identifier(
    text: str,
    *,
    asof_ts: Optional[datetime] = None  # For resolving "last quarter"
) -> Optional[dict]:
    """Resolve text to canonical Period.

    Examples:
        period_identifier("H2 2026")
        # → {"period_type": "half", "period_id": "2026H2",
        #    "start_ts": "2026-07-01T00:00:00Z", "end_ts": "2026-12-31T23:59:59Z"}

        period_identifier("Q1–Q2 2026")
        # → {"period_type": "date_range", "period_id": "2026Q1-2026Q2", ...}

        period_identifier("2025-W02")
        # → {"period_type": "week", "period_id": "2025-W02",
        #    "start_ts": "2025-01-06T00:00:00Z", ...}  # ISO Monday start

    Returns:
        {
            "period_type": "week|month|quarter|half|year|date_range",
            "period_id": "2026Q1" | "2025-01" | "2025-W02" | "2026H2" | "2025",
            "start_ts": "2026-01-01T00:00:00Z",
            "end_ts": "2026-03-31T23:59:59Z",
            "year": 2026,
            "quarter": 1,         # Only if applicable
            "month": None,
            "asof_ts": "2025-10-02T...",  # When query was resolved
            "timezone": "UTC",
            "score": 95
        }
    """

def extract_periods(text: str, *, asof_ts: Optional[datetime] = None) -> list[dict]:
    """Extract multiple periods from text."""
```

**Period Types**:
- `year`: "2025", "FY2026"
- `half`: "H1 2026", "2025H2"
- `quarter`: "Q1 2026", "2025Q3"
- `month`: "Jan 2026", "2025-01"
- `week`: "2025-W02" (ISO week, Monday start)
- `date_range`: "Q1–Q2 2026", "Jan-Mar 2025"

**Key Rules**:
1. **H1/H2 as single period**: "H2 2026" → one `period_type="half"` (downstream can expand to Q3+Q4)
2. **Ranges preserve endpoints**: "Q1–Q2" → `date_range` with proper start/end
3. **Relative periods**: "last quarter" uses `asof_ts` to compute
4. **ISO weeks**: "2025-W02" starts Monday (ISO 8601)
5. **Fiscal year labels** (v2): "FY2026" → calendar 2026 (customize per market)

**No Data Table**: Pure resolver (regex + dateutil)

---

### 4. Places API (NEW - Geographic Entity Resolution)

**Purpose**: Resolve geographic locations (country + admin1 state/province) from text.

```python
# places/placeapi.py
def place_identifier(
    name: str,
    *,
    country_hint: Optional[str] = None,
    threshold: int = 85
) -> Optional[dict]:
    """Resolve place name to canonical location.

    Examples:
        place_identifier("Limpopo", country_hint="ZA")
        # → {"country": "ZA",
        #    "admin1": "Limpopo",
        #    "admin1_code": "ZA-LP",
        #    "lat": -24.0,
        #    "lon": 29.5,
        #    "score": 98}

        place_identifier("Western Australia")
        # → {"country": "AU",
        #    "admin1": "Western Australia",
        #    "admin1_code": "AU-WA",
        #    "lat": -26.0,
        #    "lon": 121.0,
        #    "score": 100}

        place_identifier("California", country_hint="US")
        # → {"country": "US",
        #    "admin1": "California",
        #    "admin1_code": "US-CA",
        #    "lat": 37.0,
        #    "lon": -120.0,
        #    "score": 100}

    Returns:
        {
            "country": str,          # ISO2 code via country_identifier
            "admin1": str,           # State/province name
            "admin1_code": str,      # ISO 3166-2 (ZA-LP, AU-WA, US-CA)
            "lat": float,            # Centroid latitude
            "lon": float,            # Centroid longitude
            "score": int             # Match confidence 0-100
        }
    """

def extract_location(text: str) -> Optional[dict]:
    """Extract location from text (country + admin1).

    Examples:
        extract_location("Anglo American's mine in Limpopo province, South Africa")
        # → {"country": "ZA",
        #    "admin1": "Limpopo",
        #    "admin1_code": "ZA-LP",
        #    "lat": -24.0,
        #    "lon": 29.5,
        #    "mentions": ["Limpopo province", "South Africa"],
        #    "confidence": 0.92}

        extract_location("BHP's operations in Western Australia")
        # → {"country": "AU",
        #    "admin1": "Western Australia",
        #    "admin1_code": "AU-WA", ...}

    Returns:
        {
            "country": str,
            "admin1": Optional[str],
            "admin1_code": Optional[str],
            "lat": Optional[float],
            "lon": Optional[float],
            "mentions": list[str],   # Matched text spans
            "confidence": float      # 0.0-1.0
        }
    """

def list_places(
    country: Optional[str] = None,
    search: Optional[str] = None
) -> pd.DataFrame:
    """List available admin1 regions, optionally filtered."""

def load_places(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load admin1 database."""
```

**Data Sources** (Priority Order):

1. **GeoNames** (Priority 1) - Primary global coverage
   - Source: allCountries.zip daily dump
   - Filter: Feature class P (populated places) + admin codes
   - Coverage: ~12M places globally with coordinates
   - License: CC-BY 4.0 (attribution required)
   - Files: allCountries.txt, featureCodes_en.txt, countryInfo.txt, admin1CodesASCII.txt
   - Update: Daily export available
   - URL: https://download.geonames.org/export/dump/

2. **OSM Overpass** (Priority 2) - Regional deltas (optional)
   - Source: OpenStreetMap via Overpass API or pyrosm
   - Filter: place=city|town|village|hamlet
   - Use case: Fresh changes for specific regions
   - License: ODbL

3. **Geocoding Fallback** (Priority 3) - One-off resolves only
   - Source: geopy/Nominatim
   - Use case: Runtime resolution for missing places
   - Rate limited: Not for bulk loading

**Schema** (places.parquet - built from GeoNames):
```
# From GeoNames admin1CodesASCII.txt
country: str              # ISO2 code
admin1_code: str          # ISO 3166-2 (ZA.09 → ZA-LP after mapping)
admin1_name: str          # Official name from GeoNames
admin1_name_ascii: str    # ASCII version for matching
alias1-5: str             # From alternateNames (WA, West Aus, etc.)
name_norm: str            # Normalized for matching

# From GeoNames features
geoname_id: int           # GeoNames ID for reference
feature_code: str         # ADM1, ADM2, etc.
lat: float                # Centroid latitude
lon: float                # Centroid longitude
population: int           # For disambiguation
elevation: int            # Meters (optional)

# Metadata
source: str               # "geonames" or "osm"
source_priority: int      # 1=GeoNames, 2=OSM
last_updated: str         # ISO date
```

**Coverage**: ~5000 admin1 + ~50K admin2 (optional) from GeoNames

**Data Size**:
- Admin1 only: ~500KB parquet
- Admin1 + cities >1000 pop: ~5MB parquet
- Full allCountries: ~400MB parquet (optional, for completeness)

**Blocking Strategy**:
1. **Extract country** first via `country_identifier()` (reuse existing)
2. **Filter admin1** by country if found
3. **Prefix match** on admin1_name + aliases
4. **Fuzzy scoring** with RapidFuzz (handle "WA" vs "Western Australia")

**Resolution Algorithm**:
```
Input: "Limpopo", country_hint="ZA"

Stage 1: Normalize
  "Limpopo" → "limpopo"

Stage 2: Load admin1 database (LRU cached)
  ~5000 regions loaded

Stage 3: Block by country
  If country_hint: filter to ZA admin1 only
  5000 → ~9 provinces

Stage 4: Score candidates
  Exact match: "limpopo" == "limpopo" → score 100
  Alias match: "limpopo" in ["limpopo province", "limpopo prov"]

Stage 5: Return best if score ≥ threshold
  {"country": "ZA", "admin1": "Limpopo", "admin1_code": "ZA-LP", ...}
```

**Extract Location Algorithm**:
```
Input: "Anglo American's mine in Limpopo province, South Africa"

Stage 1: Extract country mentions
  country_identifier("South Africa") → "ZA"

Stage 2: Extract admin1 candidates
  Regex for province/state patterns
  "Limpopo province" → candidate "Limpopo"

Stage 3: Resolve with country hint
  place_identifier("Limpopo", country_hint="ZA")
  → {"country": "ZA", "admin1": "Limpopo", ...}

Stage 4: Return with metadata
  {"country": "ZA", "admin1": "Limpopo",
   "mentions": ["Limpopo province", "South Africa"],
   "confidence": 0.92}
```

**Coverage**: ~5000 admin1 regions worldwide (all countries with subdivisions)

**Data Size**: ~500KB parquet file

**Use Case**: Powers `facilities/` module with place_hint parameter

---

### 5. Units API (NEW - Conversion + Basis Enforcement)

**Purpose**: Normalize value/unit/basis; convert when safe; preserve raw + warnings.

```python
# units/unitapi.py
def normalize_unit(raw: dict) -> dict:
    """Normalize and convert units to canonical basis.

    Examples:
        # FeCr with known grade → convert to $/lb Cr contained
        normalize_unit({
            "value": 2150,
            "unit": "USD/t alloy",
            "basis": None,
            "grade": {"Cr_pct": 65.0},
            "ton_system": "metric"
        })
        # → {"raw": {...},
        #    "norm": {"value": 1.52, "unit": "USD/lb", "basis": "Cr contained"},
        #    "warning": None}

        # APT without grade → no conversion, warning
        normalize_unit({
            "value": 450,
            "unit": "USD/t APT",
            "basis": None,
            "grade": None
        })
        # → {"raw": {...},
        #    "norm": {"value": 450, "unit": "USD/t APT", "basis": None},
        #    "warning": "APT basis requires WO3_pct for conversion to $/mtu"}

    Args:
        raw: {
            "value": float,
            "unit": str,                    # "USD/t alloy", "USD/lb", "USD/mtu WO3"
            "basis": Optional[str],         # "Cr contained", "WO3 basis"
            "grade": Optional[dict],        # {"Cr_pct": 65.0} | {"WO3_pct": 88.5}
            "ton_system": Optional[str]     # "metric" | "short" | "long"
        }

    Returns:
        {
            "raw": {...},                   # Original input preserved
            "norm": {                       # Normalized/converted
                "value": float,
                "unit": str,
                "basis": Optional[str]
            },
            "warning": Optional[str]        # Conversion issues
        }
    """
```

**Canonical Basis Rules** (unitconfig.yaml):
```yaml
FeCr:
  canonical_unit: "USD/lb"
  canonical_basis: "Cr contained"
  requires: ["Cr_pct", "ton_system"]

APT:
  canonical_unit: "USD/mtu WO3"
  canonical_basis: "WO3 basis"
  requires: ["WO3_pct"]

Copper:
  canonical_unit: "USD/lb"
  canonical_basis: "Cu contained"
  # Simple conversion, no grade needed for pure metal
```

**Conversion Rules**:
1. **FeCr**: `$/t alloy` → `$/lb Cr` (requires Cr%, ton system)
2. **APT**: `$/t APT` → `$/mtu WO3` (requires WO3%)
3. **No guessing**: Ambiguous ton system → no conversion, warn
4. **Preserve raw**: Always keep original for audit trail

**No Data Table**: Pure functions + config

---

### 6. Instruments API (NEW - Ticker Ground Truth)

**Purpose**: Resolve news mentions to price instruments first, then map to metals/clusters.

```python
# instruments/instrumentapi.py
def instrument_identifier(
    text: str,
    *,
    source_hint: Optional[str] = None,  # "Fastmarkets", "LME", etc.
    threshold: int = 92
) -> Optional[dict]:
    """Resolve text to price instrument from ticker_references.parquet.

    Examples:
        instrument_identifier("MB-CO-0005")
        # → {"entity_type": "instrument",
        #    "instrument_id": "a3f2c8...",
        #    "provider": "Fastmarkets",
        #    "ticker": "MB-CO-0005",
        #    "instrument_name": "Cobalt standard grade in-whs Rotterdam",
        #    "currency": "USD",
        #    "unit": "USD/lb",
        #    "basis": None,
        #    "material_id": "Co",
        #    "cluster_id": "nickel_cobalt_chain",
        #    "score": 99}

        instrument_identifier("APT 88.5% in-whs Europe", source_hint="Fastmarkets")
        # → Instrument if found, else fallback to metal WO3

    Returns: See above (or None if no match)
    """

def match_instruments(text: str, k: int = 5) -> list[dict]:
    """Get top-K instrument candidates with scores."""

def list_instruments(
    source: Optional[str] = None,
    search: Optional[str] = None
) -> pd.DataFrame:
    """List instruments, optionally filtered by provider or search term."""

def load_instruments(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load ticker_references.parquet with crosswalk to metals/clusters."""
```

**Data Source**: `gs://gsmc-market-data/ticker_references.parquet` (ground truth)

**Loader Behavior** (load_instruments):
```python
# Default path: GCS bucket (override via env GSMC_TICKERS_PATH)
# Also support local files & find_data_file() for dev tables
df = load_instruments()  # Auto-loads from GCS or local

# Add computed columns:
# - instrument_id = sha1(normalize(source + "|" + ticker))[:16]
# - ticker_norm, name_norm
# - material_id via metal_identifier(material_hint)
# - cluster_id from material_id → metals cluster
```

**Schema** (ticker_references.parquet):
```
ticker: str              # Provider-specific code (MB-CO-0005, LME_AL_CASH)
source: str              # Fastmarkets, LME, CME, Argus
instrument_name: str     # Human-readable name
currency: str            # USD, EUR, CNY
unit: str                # USD/lb, USD/t, CNY/t
basis: Optional[str]     # Cr contained, WO3 basis, etc.
material_hint: Optional[str]  # "Cobalt", "Tungsten APT", etc.
# Computed columns (added by loader):
instrument_id: str       # Stable hash ID
ticker_norm: str         # Normalized for matching
name_norm: str
material_id: Optional[str]    # Resolved from material_hint
cluster_id: Optional[str]     # From material's cluster
```

**Blocking & Scoring**:
1. **Regex/prefix detection**: `MB-\w+-\d+`, `LME_[A-Z]{2,3}_\w+`, etc.
2. **Source hint bias**: Boost scores for hinted provider
3. **RapidFuzz WRatio**: Over ticker, name_norm, aliases
4. **Return best** if score ≥ threshold

**Precedence Rule** (for callers):
- Query `instrument_identifier()` first (more specific)
- Fallback to `metal_identifier()` if no instrument match
- **No global orchestrator needed** - callers handle precedence

---

### 7. Facilities API (NEW - Probabilistic Linker)

**Purpose**: Given company/place hints, return most likely facility (not just company).

```python
# facilities/facilityapi.py
def link_facility(
    *,
    company_hint: Optional[str] = None,
    place_hint: Optional[dict] = None,      # {"country": "ZA", "admin1": "Limpopo", "city": None}
    metal_hint: Optional[str] = None,       # "PGM", "copper"
    process_stage_hint: Optional[str] = None  # "mining", "refining", "smelting"
) -> dict:
    """Probabilistic facility linker: company + location → specific facility.

    Examples:
        link_facility(
            company_hint="Anglo American",
            place_hint={"country": "ZA", "admin1": "Limpopo"},
            metal_hint="PGM"
        )
        # → {"facility_id": "mogalakwena_001",
        #    "facility_name": "Mogalakwena Mine",
        #    "company_id": "Anglo American Platinum Limited:ZA",
        #    "link_score": 92,
        #    "features": {
        #        "name_score": 85,
        #        "company_match": true,
        #        "geo_distance_km": 0,
        #        "stage_compatible": true,
        #        "commodity_overlap": 1.0,
        #        "active": true
        #    },
        #    "geo": {
        #        "lat": -24.2234,
        #        "lon": 28.3456,
        #        "country_iso2": "ZA",
        #        "admin1": "Limpopo",
        #        "city": "Mokopane"
        #    }}

    Returns:
        {
            "facility_id": str,           # Primary facility ID
            "facility_name": str,
            "company_id": str,            # Fallback if link_score low
            "link_score": 0-100,          # Confidence in facility match
            "features": {...},            # Feature breakdown
            "geo": {...}                  # Location details
        }
    """
```

**Blocking Strategy**:
1. **Company** (operator/owner via company_identifier)
2. **Country/admin1** (if place_hint provided)
3. **Process stage** (mining/refining/smelting)
4. **Commodity** (metal_hint → cluster)

**Scoring Features**:
- `name_score`: Fuzzy match on facility name/aliases
- `company_match`: Boolean (company_id matches operator/owner)
- `geo_distance_km`: Haversine distance if lat/lon available
- `stage_compatible`: Process stage matches facility type
- `commodity_overlap`: Jaccard similarity of materials
- `active`: Facility status (operating vs closed)

**Decision Logic**:
- Return **top-1** if `link_score ≥ threshold` (default 80)
- Otherwise return **top candidate + company fallback** (lower confidence)
- Downstream can still use company-only resolution if needed

**Data** (facilities master - optional in repo):
```
facility_id: str
facility_name: str
company_id: str              # Via company_identifier
status: str                  # "operating", "closed", "development"
process_stage: str           # "mining", "refining", "smelting"
country_iso2: str
admin1: Optional[str]
city: Optional[str]
lat: Optional[float]
lon: Optional[float]
materials_json: str          # JSON list of metal_ids
aliases_json: Optional[str]
```

**Implementation Notes**:
- If no facilities master available yet, **stub this module** with company-only fallback
- Add tests that **skip when data missing** (like existing `pytest.mark.skipif`)

---

## C. Implementation Patterns (Reuse Existing)

All new modules follow established patterns from companies/, metals/, countries/:

### 1. Normalization Functions

```python
# baskets/basketnormalize.py
def normalize_basket_name(name: str) -> str:
    """Aggressive normalization for matching."""

def canonicalize_basket_name(name: str) -> str:
    """Readable canonicalization for display."""

# period/periodnormalize.py
def normalize_period_text(text: str) -> str:
    """Normalize period expressions for parsing."""

# Similar pattern for all entities
```

### 2. LRU Caching (Minimize Latency)

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def load_baskets(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load baskets database (cached for session)."""
    # First load: ~0.1s
    # Subsequent: instant
```

**Target**: <100ms query latency (like companies/metals)

### 3. Blocking → Scoring → Decision Pipeline

All resolvers use 3-stage pipeline:

```python
# Example: baskets/basketidentity.py
def resolve_basket(name: str, k: int = 5) -> dict:
    # Stage 1: Normalize
    name_norm = normalize_basket_name(name)

    # Stage 2: Block (reduce search space 99%+)
    df = load_baskets()
    candidates = block_candidates(df, name_norm)  # Prefix match

    # Stage 3: Score
    scored = score_candidates(candidates, name_norm, k=k)

    # Stage 4: Decide
    if scored[0]['score'] >= threshold:
        return scored[0]  # High confidence
    else:
        return {"matches": scored}  # Uncertain
```

### 4. Data Loading Utilities

```python
# Reuse existing utilities from entityidentity/utils/
from ..utils import find_data_file, load_parquet_or_csv

def load_baskets(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    if path is None:
        path = find_data_file(
            module_file=__file__,
            subdirectory="data",
            filenames=["baskets.parquet", "baskets.csv"],
            search_dev_tables=True,      # Check tables/baskets/ in dev
            module_local_data=True        # Check baskets/data/ for static
        )
    return load_parquet_or_csv(path)
```

**Search Order**:
1. Explicit `path` argument
2. Module-local `data/` directory (for static data)
3. Package data directory (installed samples)
4. Development `tables/` directory (full builds)

### 5. Stable ID Generation

Follow existing patterns:

```python
# metals: generate_metal_id() (already exists)
# baskets: basket_id = slugify(label)
from ..utils import slugify

def generate_basket_id(label: str) -> str:
    return slugify(label)  # "PGM 4E" → "pgm_4e"

# periods: period_id from ISO format
def generate_period_id(period_type: str, **kwargs) -> str:
    if period_type == "quarter":
        return f"{kwargs['year']}Q{kwargs['quarter']}"  # "2026Q1"
    elif period_type == "half":
        return f"{kwargs['year']}H{kwargs['half']}"     # "2026H2"
    # etc.

# instruments: hash-based
import hashlib

def generate_instrument_id(source: str, ticker: str) -> str:
    key = f"{source.lower()}|{ticker}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]

# facilities: use provided facility_id from master table
```

---

## D. Testing Strategy

Mirror existing test structure with comprehensive coverage:

### 1. Baskets Tests

```python
# tests/baskets/test_basketapi.py
def test_basket_identifier_pgm_4e():
    result = basket_identifier("PGM 4E")
    assert result['basket_id'] == "pgm_4e"
    assert len(result['metals']) == 4
    assert {m['metal_id'] for m in result['metals']} == {'Pt', 'Pd', 'Rh', 'Au'}

def test_basket_partial_splits():
    """Baskets can have unknown splits."""
    result = basket_identifier("NdPr")
    assert result['metals'][0]['share'] is None  # Ratio varies by source

def test_basket_normalization():
    """Different phrasings resolve to same basket."""
    assert basket_identifier("PGM-4E")['basket_id'] == \
           basket_identifier("PGM 4 element")['basket_id']
```

### 2. Period Tests

```python
# tests/test_period.py
def test_period_h2_2026():
    """H2 kept as single half period."""
    result = period_identifier("H2 2026")
    assert result['period_type'] == "half"
    assert result['period_id'] == "2026H2"
    assert result['start_ts'] == "2026-07-01T00:00:00Z"
    assert result['end_ts'] == "2026-12-31T23:59:59Z"

def test_period_iso_week():
    """ISO week starts Monday."""
    result = period_identifier("2025-W02")
    assert result['period_type'] == "week"
    # Week 2 of 2025 starts Monday 2025-01-06
    assert result['start_ts'] == "2025-01-06T00:00:00Z"

def test_period_range():
    """Q1–Q2 becomes date_range."""
    result = period_identifier("Q1–Q2 2026")
    assert result['period_type'] == "date_range"
    assert result['start_ts'] == "2026-01-01T00:00:00Z"
    assert result['end_ts'] == "2026-06-30T23:59:59Z"

def test_period_relative():
    """'last quarter' uses asof_ts."""
    asof = datetime(2025, 10, 2, tzinfo=timezone.utc)
    result = period_identifier("last quarter", asof_ts=asof)
    assert result['period_id'] == "2025Q3"
```

### 3. Places Tests

```python
# tests/test_places.py
def test_place_identifier_with_country_hint():
    """Resolve admin1 with country hint."""
    result = place_identifier("Limpopo", country_hint="ZA")
    assert result['country'] == "ZA"
    assert result['admin1'] == "Limpopo"
    assert result['admin1_code'] == "ZA-LP"
    assert result['lat'] is not None
    assert result['lon'] is not None

def test_place_identifier_unambiguous():
    """Unique place name resolves without hint."""
    result = place_identifier("Western Australia")
    assert result['country'] == "AU"
    assert result['admin1_code'] == "AU-WA"

def test_place_identifier_abbreviation():
    """Handle common abbreviations."""
    result = place_identifier("CA", country_hint="US")
    assert result['admin1'] == "California"
    assert result['admin1_code'] == "US-CA"

def test_extract_location_full():
    """Extract country + admin1 from text."""
    text = "Anglo American's mine in Limpopo province, South Africa"
    result = extract_location(text)
    assert result['country'] == "ZA"
    assert result['admin1'] == "Limpopo"
    assert "Limpopo" in result['mentions']
    assert result['confidence'] > 0.8

def test_extract_location_country_only():
    """Gracefully handle admin1 not found."""
    text = "Mining operations in Chile"
    result = extract_location(text)
    assert result['country'] == "CL"
    assert result['admin1'] is None

def test_list_places_by_country():
    """Filter places by country."""
    places = list_places(country="US")
    assert len(places) == 50  # 50 US states
    assert all(p['country'] == 'US' for _, p in places.iterrows())

def test_load_places_caching():
    """LRU cache works."""
    df1 = load_places()
    df2 = load_places()
    assert df1 is df2  # Same object (cached)
```

### 4. Units Tests

```python
# tests/test_units.py
def test_unit_fecr_conversion():
    """FeCr with grade converts to $/lb Cr."""
    result = normalize_unit({
        "value": 2150,
        "unit": "USD/t alloy",
        "basis": None,
        "grade": {"Cr_pct": 65.0},
        "ton_system": "metric"
    })
    assert result['norm']['unit'] == "USD/lb"
    assert result['norm']['basis'] == "Cr contained"
    assert result['warning'] is None

def test_unit_apt_missing_grade():
    """APT without WO3% cannot convert."""
    result = normalize_unit({
        "value": 450,
        "unit": "USD/t APT",
        "basis": None,
        "grade": None
    })
    assert result['norm']['value'] == 450  # No conversion
    assert "WO3_pct" in result['warning']

def test_unit_ambiguous_ton():
    """Ambiguous ton system prevents conversion."""
    result = normalize_unit({
        "value": 1000,
        "unit": "USD/t",
        "ton_system": None
    })
    assert "ton system" in result['warning']
```

### 5. Instruments Tests

```python
# tests/test_instruments.py
def test_instrument_identifier_fastmarkets():
    """Resolve Fastmarkets ticker to instrument."""
    result = instrument_identifier("MB-CO-0005")
    assert result['provider'] == "Fastmarkets"
    assert result['material_id'] == "Co"
    assert result['unit'] == "USD/lb"

def test_instrument_crosswalk_to_metals():
    """Instruments map to metals via material_hint."""
    df = load_instruments()
    apt_row = df[df['ticker'].str.contains('APT', na=False)].iloc[0]
    assert apt_row['material_id'] == "W"  # Tungsten via metal_identifier

def test_instrument_precedence():
    """Instruments preferred over metals when both match."""
    # Caller pattern:
    inst = instrument_identifier("Cobalt standard grade")
    if inst is None:
        metal = metal_identifier("Cobalt")
    # inst should match first (more specific)
    assert inst is not None
```

### 6. Facilities Tests

```python
# tests/test_facilities.py
@pytest.mark.skipif(not FACILITIES_DATA_AVAILABLE, reason="No facilities master")
def test_facility_link_mogalakwena():
    """Company + Limpopo → Mogalakwena."""
    result = link_facility(
        company_hint="Anglo American",
        place_hint={"country": "ZA", "admin1": "Limpopo"},
        metal_hint="PGM"
    )
    assert "mogalakwena" in result['facility_id'].lower()
    assert result['link_score'] > 80

@pytest.mark.skipif(not FACILITIES_DATA_AVAILABLE, reason="No facilities master")
def test_facility_link_company_fallback():
    """Low confidence returns company fallback."""
    result = link_facility(
        company_hint="Unknown Mining Co",
        place_hint={"country": "XX"}
    )
    assert result['link_score'] < 80
    assert result['company_id'] is not None  # Fallback available
```

**Test Coverage Targets**:
- Baskets: 15+ tests (normalization, splits, aliases)
- Period: 20+ tests (all types, relative, ISO weeks, ranges)
- Units: 15+ tests (conversions, warnings, edge cases)
- Instruments: 12+ tests (providers, crosswalk, blocking)
- Facilities: 10+ tests (blocking, features, fallback) - skip if no data

---

## E. Authoritative Data Sources (Ground Truth Hierarchies)

This section documents canonical, maintainable sources for each entity type, organized by priority (like Companies uses GLEIF → Wikidata → Exchanges).

### 1. Metals / Materials

**Source Priority**:

1. **IUPAC** (Priority 1) - Chemical elements
   - Source: IUPAC Periodic Table (official element names, symbols, atomic numbers)
   - Coverage: 118 elements with canonical names + historic aliases (W=Wolfram, etc.)
   - License: Open (IUPAC public data)
   - URL: https://iupac.org/what-we-do/periodic-table-of-elements/
   - Update: Stable (new elements rare)

2. **ChEBI + PubChem** (Priority 2) - Chemical forms & compounds
   - ChEBI: Chemical Entities of Biological Interest ontology
     - Coverage: ~200K compounds with synonyms (Li₂CO₃, WO₃, etc.)
     - License: CC BY 4.0
     - URL: https://www.ebi.ac.uk/chebi/downloadsForward.do
     - Update: Monthly releases
   - PubChem: NLM database with synonym lists
     - Access: PUG-REST API for synonym lookups
     - URL: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
     - Use case: Map market terms → ChEBI IDs

3. **USGS Mineral Commodity Summaries** (Priority 3) - Supply chain clusters & by-products
   - Source: Annual commodity summaries + technical pages
   - Coverage: Cu→Mo→Re, Cu anode slimes→Se/Te, Zn smelter→Cd/In/Ge, etc.
   - License: US Government public domain
   - URL: https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries
   - Update: Annual (January release)
   - Use case: Cluster tags (battery metals, porphyry copper byproducts)

**Loader Precedence**: IUPAC (elements) → ChEBI/PubChem (forms/aliases) → USGS (cluster metadata)

**Implementation**: `metals/data/build_metals.py`
```python
def consolidate_metals():
    # Load IUPAC elements
    elements_df = load_iupac_elements()  # Priority 1

    # Augment with ChEBI compounds
    compounds_df = load_chebi_compounds()  # Priority 2

    # Add USGS cluster metadata
    clusters_df = load_usgs_clusters()  # Priority 3

    # Merge with source_priority
    return merge_with_priority([elements_df, compounds_df, clusters_df])
```

---

### 2. Places / Geographic Entities

**Source Priority**:

1. **GeoNames** (Priority 1) - Global coverage
   - Source: allCountries.zip daily dump
   - Filter: Feature class P (populated places) + admin codes (ADM1/ADM2)
   - Coverage: ~12M places, ~5K admin1, ~50K admin2
   - License: CC-BY 4.0 (attribution: "Data from GeoNames (geonames.org)")
   - Files:
     - allCountries.txt (full dump) or cities1000.txt (cities >1K pop)
     - admin1CodesASCII.txt (admin1 regions)
     - featureCodes_en.txt (feature definitions)
     - countryInfo.txt (country metadata)
   - URL: https://download.geonames.org/export/dump/
   - Update: Daily exports

2. **OpenStreetMap** (Priority 2) - Regional deltas (optional)
   - Source: Overpass API or pyrosm extracts
   - Filter: place=city|town|village|hamlet
   - License: ODbL (share-alike)
   - URL: https://wiki.openstreetmap.org/wiki/Overpass_API
   - Use case: Fresh changes for specific regions between GeoNames updates

3. **Nominatim/Geocoder** (Priority 3) - Runtime fallback only
   - Source: geopy + Nominatim
   - Use case: One-off resolution for places missing from tables
   - Rate limit: Max 1 req/sec (not for bulk)
   - URL: https://nominatim.org/release-docs/latest/api/Search/

**Loader Precedence**: GeoNames → OSM deltas (optional) → Nominatim (runtime only)

**Implementation**: `places/data/build_admin1.py`
```python
def build_places_parquet():
    # Load GeoNames admin1
    admin1_df = load_geonames_admin1()  # Priority 1

    # Optional: augment with OSM for fresh data
    if OSM_DELTAS_ENABLED:
        osm_df = load_osm_places()  # Priority 2
        admin1_df = merge_with_priority([admin1_df, osm_df])

    # Save with attribution
    admin1_df['source'] = 'geonames'
    admin1_df['attribution'] = 'Data from GeoNames (geonames.org)'
    return admin1_df
```

---

### 3. Baskets (Multi-Metal Composites)

**Source Priority**:

1. **Issuer Definitions** (Priority 1) - From RNS/MD&A/Technical Reports
   - PGM 4E: Pt+Pd+Rh+Au (Anglo American/Amplats standard)
   - PGM 5E+Au: Pt+Pd+Rh+Ru+Ir+Au (Amplats variant)
   - PGM 6E: Pt+Pd+Rh+Ru+Ir+Os (full basket)
   - NdPr: Nd+Pr (didymium, ratio varies by deposit)
   - REE Light: La+Ce+Pr+Nd
   - Sources:
     - Anglo American Platinum annual reports
     - Sibanye-Stillwater technical updates
     - Northern Minerals REE definitions
   - URL examples:
     - https://www.angloamerican platinum.com (RNS announcements)
     - Industry technical reports (cite per basket)

2. **Industry Standards** (Priority 2) - WPIC, certification labs
   - World Platinum Investment Council (WPIC) definitions
   - AMIS certification kits (analytical standards for 4E/6E in concentrates)
   - URL: https://www.platinuminvestment.com/
   - Use case: Validate basket definitions, not primary source

3. **Facility-Specific Overrides** (Priority 3) - Prill splits
   - Source: Site-specific assay reports, concentrate specs
   - Example: Mogalakwena 4E prill ratio differs from Mototolo
   - Storage: Facility table can override default basket shares
   - Use case: Actual production splits when known

**Loader Precedence**: Issuer docs (RNS/MD&A) → Industry groups (WPIC) → Facility overrides (in facility table)

**Implementation**: `baskets/data/baskets.yaml`
```yaml
baskets:
  - basket_id: pgm_4e
    label: "PGM 4E"
    source: "Anglo American Platinum definition"
    source_url: "https://www.angloamericanplatinum.com"
    metals:
      - metal_id: Pt
        share: null  # Unknown default split
      - metal_id: Pd
        share: null
      - metal_id: Rh
        share: null
      - metal_id: Au
        share: null
```

---

### 4. Units & Basis

**Source Priority**:

1. **SI / BIPM** (Priority 1) - Base units
   - Source: SI Brochure (9th edition, 2019, updated 2025)
   - Coverage: Canonical definitions for meter, kilogram, second, etc.
   - License: CC BY 4.0
   - URL: https://www.bipm.org/en/publications/si-brochure
   - Use case: Validate unit symbols, derive conversions

2. **UCUM** (Priority 2) - Unit grammar
   - Source: Unified Code for Units of Measure
   - Coverage: Programmatic grammar for unit strings, semantic equality
   - License: Open specification
   - URL: https://ucum.org/ucum
   - Use case: Robust parsing, equivalence checking

3. **Market Basis Standards** (Priority 3) - Commodity-specific conventions
   - **FeCr**: $/lb Cr contained (industry standard)
     - Source: Fastmarkets/Argus spec sheets
     - Conversion: $/t alloy → $/lb Cr requires Cr% + ton system
   - **APT**: $/mtu WO₃ (tungsten market standard)
     - Source: Fastmarkets APT specifications
     - Conversion: $/t APT → $/mtu WO₃ requires WO₃%
   - **Copper**: $/lb Cu contained (simple, pure metal)
   - URLs:
     - https://www.fastmarkets.com/commodities/ferro-alloys
     - https://www.argusmedia.com/metals

**Loader Precedence**: SI/UCUM (base units) → Market basis rules (unitconfig.yaml)

**Implementation**: `units/unitconfig.yaml`
```yaml
FeCr:
  canonical_unit: "USD/lb"
  canonical_basis: "Cr contained"
  requires: ["Cr_pct", "ton_system"]
  conversion_note: "Convert $/t alloy → $/lb Cr only when grade + ton system known"
  source: "Fastmarkets FeCr specifications"
  source_url: "https://www.fastmarkets.com/commodities/ferro-alloys"
```

---

### 5. Instruments (Price Tickers)

**Source Priority**:

1. **ticker_references.parquet** (Priority 1) - Internal ground truth
   - Source: gs://gsmc-market-data/ticker_references.parquet
   - Coverage: Curated tickers from Fastmarkets, LME, CME, Argus
   - Schema: ticker, source, instrument_name, currency, unit, basis, material_hint
   - Update: Internal cadence

2. **LME Brand Lists** (Priority 2) - Deliverable brands
   - Source: LME approved brand lists (updated regularly)
   - Coverage: Brands deliverable against LME contracts (Cu, Ni, Zn, Al, etc.)
   - URL: https://www.lme.com/en/trading/approved-brands
   - Use case: Validate instrument names, cross-reference tickers

3. **CME/COMEX Product Directories** (Priority 3) - Futures tickers
   - Source: CME Group product codes
   - Coverage: Unified symbols for futures (HG=copper, SI=silver, GC=gold)
   - URL: https://www.cmegroup.com/markets/metals.html
   - Use case: Map tickers to metals

4. **Fastmarkets Spec Pages** (Priority 4) - Price assessment metadata
   - Source: Fastmarkets methodology pages
   - Example: MB-CO-0005 = "Cobalt standard grade, in-whs Rotterdam, $/lb"
   - URL: https://www.fastmarkets.com/commodities/base-metals
   - Use case: Confirm unit/basis for assessments

**Loader Precedence**: Internal parquet → LME brands (cross-ref) → CME directory → Fastmarkets specs

**Implementation**: `instruments/instrumentloaders.py`
```python
def load_instruments():
    # Load primary source
    df = load_parquet_from_gcs()  # Priority 1

    # Augment with LME brand metadata
    lme_brands = load_lme_brands()  # Priority 2
    df = df.merge(lme_brands, on='ticker', how='left')

    # Add CME product mappings
    cme_products = load_cme_directory()  # Priority 3
    df = augment_with_cme(df, cme_products)

    # Crosswalk to metals
    df['material_id'] = df['material_hint'].apply(metal_identifier)

    return df
```

---

### 6. Facilities (Mines, Smelters, Refineries)

**Source Priority**:

1. **USGS Facility Datasets** (Priority 1) - Regional/commodity maps
   - Source: USGS Mineral Resources publications
   - Examples:
     - "Mineral Facilities of Europe" (1,700+ mines/plants, 2013)
     - "World Copper Smelters" (locations, capacity, process)
     - "Principal Gold-Producing Districts of the United States"
   - License: US Government public domain
   - URL: https://mrdata.usgs.gov/general/map-global.html
   - Update: Irregular (archive but authoritative)

2. **USGS MRDS/USMIN** (Priority 2) - Deposit localities
   - MRDS: Mineral Resources Data System (global deposits)
   - USMIN: US mineral deposit database
   - Coverage: Deposit IDs, coordinates, commodity tags, references
   - URL: https://mrdata.usgs.gov/mrds/
   - Use case: Tie facilities to deposit IDs

3. **Curated Additions** (Priority 3) - From issuer reports, EITI, filings
   - Source: Company technical reports, EITI disclosures, NI 43-101 filings
   - Provenance: Must cite source per record
   - Examples:
     - Anglo American technical update for Mogalakwena
     - EITI South Africa mining cadastre
   - Storage: curated_facilities.parquet with explicit `source_url` column

4. **Mindat** (Reference Only) - Per-record citations
   - Source: https://www.mindat.org
   - Coverage: Comprehensive locality database
   - License: Bulk export restricted; use for per-record lookups with citation
   - Use case: Validate coordinates, cross-reference names

**Loader Precedence**: USGS datasets → MRDS/USMIN → Curated (with provenance) → Mindat (cite per query)

**Implementation**: `facilities/data/build_facilities.py`
```python
def consolidate_facilities():
    # Load USGS facility maps
    usgs_facilities = load_usgs_facilities_europe()  # Priority 1

    # Augment with MRDS deposits
    mrds = load_usgs_mrds()  # Priority 2
    facilities = usgs_facilities.merge(mrds, on='deposit_id', how='left')

    # Add curated records with provenance
    curated = load_curated_facilities()  # Priority 3
    facilities = pd.concat([facilities, curated])

    # Deduplicate by (name_norm, lat, lon, company_id)
    facilities = deduplicate_facilities(facilities)

    return facilities
```

---

### 7. Periods / Calendars

**Source Priority**:

1. **ISO 8601** (Priority 1) - Calendar weeks & date/time standards
   - Source: ISO 8601:2004 (Date and time format)
   - Coverage: Week-date format, calendar arithmetic
   - Rules:
     - Week starts Monday
     - Week 1 contains first Thursday of year
     - Format: 2025-W02 (year, week number)
   - URL: https://en.wikipedia.org/wiki/ISO_8601
   - License: Open standard

2. **Unicode CLDR** (Priority 2) - Localized names (optional)
   - Source: Common Locale Data Repository
   - Coverage: Month/quarter names in 700+ locales
   - URL: https://cldr.unicode.org
   - Use case: Localized period labels (if needed)

**Loader Precedence**: ISO 8601 (week logic) → CLDR (localized labels, optional)

**Implementation**: `period/periodidentity.py`
```python
from isoweek import Week
from datetime import date

def period_identifier(text: str):
    if "2025-W02" in text:
        # ISO 8601 week (starts Monday)
        week = Week(2025, 2)
        return {
            "period_type": "week",
            "period_id": "2025-W02",
            "start_ts": week.monday().isoformat() + "T00:00:00Z",
            "end_ts": week.sunday().isoformat() + "T23:59:59Z"
        }
```

---

## F. Data Contracts (Flat, Parquet-Friendly)

### 1. baskets.parquet

**Source**: `baskets/data/baskets.yaml` (human-editable)
**Builder**: `baskets/data/build_baskets.py` (YAML → Parquet)

**Schema**:
```
basket_id: str           # Primary key (slugified label)
label: str               # Display name ("PGM 4E", "NdPr")
alias1-5: str            # Variations ("PGM-4E", "4E PGM", etc.)
metals_json: str         # JSON: [{"metal_id": "Pt", "share": null}, ...]
unknown_share: float     # Fraction of basket with unspecified metals
notes: str               # Comments/source references
```

**Sample YAML**:
```yaml
baskets:
  - basket_id: pgm_4e
    label: "PGM 4E"
    aliases:
      - "PGM-4E"
      - "4E PGM"
      - "Four-element PGM"
    metals:
      - metal_id: Pt
        share: null  # Unknown split
      - metal_id: Pd
        share: null
      - metal_id: Rh
        share: null
      - metal_id: Au
        share: null
    unknown_share: null
    notes: "Standard 4-element platinum group basket"

  - basket_id: ndpr
    label: "NdPr"
    aliases:
      - "Nd-Pr"
      - "Neodymium-Praseodymium"
    metals:
      - metal_id: Nd
        share: null  # Ratio varies by ore source
      - metal_id: Pr
        share: null
    unknown_share: null
    notes: "Didymium, Nd:Pr ratio typically 3-4:1 but source-dependent"
```

### 2. admin1.parquet (places)

**Source**: Natural Earth admin1 boundaries + GeoNames
**Builder**: `places/data/build_admin1.py`

**Schema**:
```
country: str              # ISO2 code
admin1_name: str          # Official name ("Limpopo", "California", "Western Australia")
admin1_code: str          # ISO 3166-2 (ZA-LP, US-CA, AU-WA)
alias1-3: str             # Variations ("WA", "West Aus", "Limpopo Province")
name_norm: str            # Normalized for matching
lat: float                # Centroid latitude
lon: float                # Centroid longitude
population: int           # For disambiguation (optional)
area_km2: float           # For context (optional)
```

**Coverage**: ~5000 admin1 regions worldwide

**Data Size**: ~500KB parquet

### 3. ticker_references.parquet

**Source**: `gs://gsmc-market-data/ticker_references.parquet` (ground truth)
**Override**: Environment variable `GSMC_TICKERS_PATH` for local dev

**Schema** (input):
```
ticker: str              # MB-CO-0005, LME_AL_CASH
source: str              # Fastmarkets, LME, CME, Argus
instrument_name: str     # "Cobalt standard grade in-whs Rotterdam"
currency: str            # USD, EUR, CNY
unit: str                # USD/lb, USD/t, CNY/t
basis: str               # "Cr contained", "WO3 basis", null
material_hint: str       # "Cobalt", "Tungsten APT", null
```

**Computed Columns** (added by loader):
```
instrument_id: str       # sha1(normalize(source + "|" + ticker))[:16]
ticker_norm: str         # Normalized ticker for matching
name_norm: str           # Normalized instrument name
material_id: str         # Resolved via metal_identifier(material_hint)
cluster_id: str          # From material's cluster_id
```

### 4. facilities master (optional - external or future)

**Location**: TBD (could be `tables/facilities/facilities.parquet` or external DB)

**Schema**:
```
facility_id: str         # Primary key
facility_name: str
company_id: str          # Via company_identifier
status: str              # "operating", "closed", "development", "care_maintenance"
process_stage: str       # "mining", "concentrator", "smelter", "refinery"
country_iso2: str
admin1: str              # State/province
city: str
lat: float
lon: float
materials_json: str      # JSON list: ["Pt", "Pd", "Rh", "Au"]
aliases_json: str        # JSON list of facility name variations
operator_company_id: str # If different from owner
commissioning_year: int
capacity_tpa: float      # Tonnes per annum (material-dependent)
```

### 5. period (no table)

Period resolution is **pure computation** (regex + dateutil), no data table needed.

### 6. units (config only)

`units/unitconfig.yaml` - metal-specific basis rules:
```yaml
FeCr:
  canonical_unit: "USD/lb"
  canonical_basis: "Cr contained"
  requires: ["Cr_pct", "ton_system"]
  conversion_formula: "value / (Cr_pct / 100) / (2000 if ton_system=='short' else 2204.6)"

APT:
  canonical_unit: "USD/mtu WO3"
  canonical_basis: "WO3 basis"
  requires: ["WO3_pct"]
  conversion_formula: "value * (WO3_pct / 100) / 10"  # mtu = metric ton unit / 10

Copper:
  canonical_unit: "USD/lb"
  canonical_basis: "Cu contained"
  requires: []  # Simple conversion for pure metal
```

---

## F. Package Integration (Backwards Compatible)

Update `entityidentity/__init__.py` to export new APIs:

```python
# entityidentity/__init__.py

__version__ = "0.2.0"

# ============================================================================
# Existing APIs (NO CHANGES)
# ============================================================================
from .companies.companyapi import (
    company_identifier, match_company, resolve_company, list_companies,
    extract_companies, get_company_id, normalize_company_name,
    canonicalize_company_name, get_identifier
)

from .countries.countryapi import (
    country_identifier, country_identifiers
)

from .metals.metalapi import (
    metal_identifier, match_metal, list_metals, load_metals
)

from .metals.metalextractor import (
    extract_metals_from_text, extract_metal_pairs
)

# ============================================================================
# NEW APIS (v0.2.0)
# ============================================================================
from .baskets.basketapi import (
    basket_identifier, match_basket, list_baskets, load_baskets
)

from .period.periodapi import (
    period_identifier, extract_periods
)

from .places.placeapi import (
    place_identifier, extract_location, list_places, load_places
)

from .units.unitapi import (
    normalize_unit
)

from .instruments.instrumentapi import (
    instrument_identifier, match_instruments, list_instruments, load_instruments
)

from .facilities.facilityapi import (
    link_facility
)

__all__ = [
    # Version
    "__version__",

    # ========================================================================
    # PRIMARY APIS
    # ========================================================================
    "company_identifier",
    "country_identifier",
    "metal_identifier",
    "basket_identifier",       # NEW
    "period_identifier",       # NEW
    "place_identifier",        # NEW
    "instrument_identifier",   # NEW

    # ========================================================================
    # Company Resolution
    # ========================================================================
    "match_company", "resolve_company", "list_companies", "extract_companies",
    "get_company_id", "normalize_company_name", "canonicalize_company_name",
    "get_identifier",

    # ========================================================================
    # Country Resolution
    # ========================================================================
    "country_identifiers",

    # ========================================================================
    # Metal Resolution
    # ========================================================================
    "match_metal", "list_metals", "load_metals",
    "extract_metals_from_text", "extract_metal_pairs",

    # ========================================================================
    # Basket Resolution (NEW)
    # ========================================================================
    "match_basket", "list_baskets", "load_baskets",

    # ========================================================================
    # Period Normalization (NEW)
    # ========================================================================
    "extract_periods",

    # ========================================================================
    # Place Resolution (NEW)
    # ========================================================================
    "extract_location", "list_places", "load_places",

    # ========================================================================
    # Unit Normalization (NEW)
    # ========================================================================
    "normalize_unit",

    # ========================================================================
    # Instrument Resolution (NEW)
    # ========================================================================
    "match_instruments", "list_instruments", "load_instruments",

    # ========================================================================
    # Facility Linking (NEW)
    # ========================================================================
    "link_facility",
]
```

**No Breaking Changes**: All existing APIs remain unchanged.

---

## G. Resolution Precedence (Caller Guidance)

When multiple entity types could match text, use this precedence:

```python
# 1. Instruments first (ticker ground truth - most specific)
instrument = instrument_identifier("MB-CO-0005")
if instrument:
    # Use provider, ticker, unit, basis, material_id
    pass

# 2. Baskets (multi-metal composites)
elif basket := basket_identifier("PGM 4E"):
    # Expands to constituent metals
    metals = basket['metals']

# 3. Metals (elements/compounds)
elif metal := metal_identifier("lithium carbonate"):
    # Single metal with form
    pass

# 4. Facilities (probabilistic, requires hints)
facility = link_facility(
    company_hint=extracted_company,
    place_hint=extracted_location,
    metal_hint=metal['metal_id'] if metal else None
)
# Returns facility or company fallback

# 5. Period (always normalize time references)
period = period_identifier("H2 2026")

# 6. Units (normalize all value/unit pairs)
normalized = normalize_unit({
    "value": 2150,
    "unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0}
})
```

**No Global Orchestrator**: Each module is independent; callers handle precedence logic.

---

## H. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**PR #1: Baskets Module**
- [ ] Create `entityidentity/baskets/` structure
- [ ] Implement `basketapi.py` (identifier, match, list, load)
- [ ] Implement `basketidentity.py` (blocking/scoring pipeline)
- [ ] Implement `basketnormalize.py`
- [ ] Create `data/baskets.yaml` with ~20 common baskets
- [ ] Implement `data/build_baskets.py` (YAML → Parquet builder)
- [ ] Add tests: `tests/baskets/test_basketapi.py`, `test_normalization.py`
- [ ] Update package `__init__.py` exports
- [ ] Update README with baskets section

**PR #2: Period Module**
- [ ] Create `entityidentity/period/` structure
- [ ] Implement `periodapi.py` (identifier, extract)
- [ ] Implement `periodidentity.py` (text → Period resolver)
- [ ] Implement `periodnormalize.py`
- [ ] Add tests: `tests/test_period.py` (20+ test cases)
- [ ] Update package `__init__.py` exports
- [ ] Update README with period section

**PR #3: Places Module**
- [ ] Create `entityidentity/places/` structure
- [ ] Implement `placeapi.py` (identifier, extract_location, list, load)
- [ ] Implement `placeidentity.py` (admin1 matching with country blocking)
- [ ] Implement `placenormalize.py`
- [ ] Create `data/build_admin1.py` (Natural Earth → Parquet)
- [ ] Build `data/admin1.parquet` (~5000 regions)
- [ ] Add tests: `tests/test_places.py` (15+ test cases)
- [ ] Update package `__init__.py` exports
- [ ] Update README with places section

### Phase 2: Conversion & Ground Truth (Week 3-4)

**PR #4: Units Module**
- [ ] Create `entityidentity/units/` structure
- [ ] Implement `unitapi.py` (normalize_unit)
- [ ] Implement `unitnorm.py` (conversion logic)
- [ ] Create `unitconfig.yaml` (FeCr, APT, etc. rules)
- [ ] Add tests: `tests/test_units.py` (15+ test cases)
- [ ] Update package `__init__.py` exports
- [ ] Update README with units section

**PR #5: Instruments Module**
- [ ] Create `entityidentity/instruments/` structure
- [ ] Implement `instrumentapi.py` (identifier, match, list, load)
- [ ] Implement `instrumentloaders.py` (GCS + local loading)
- [ ] Implement `instrumentidentity.py` (blocking/scoring with regex)
- [ ] Add crosswalk: material_hint → metal_identifier → cluster_id
- [ ] Add tests: `tests/test_instruments.py` (12+ test cases)
- [ ] Update package `__init__.py` exports
- [ ] Update README with instruments section

### Phase 3: Facilities (Week 5 - Optional)

**PR #6: Facilities Module (Stub or Full)**
- [ ] Create `entityidentity/facilities/` structure
- [ ] Implement `facilityapi.py` (link_facility)
- [ ] Implement `facilitylink.py` (blocking, feature scoring, decision)
- [ ] Add tests: `tests/test_facilities.py` (skip if no data)
- [ ] Update package `__init__.py` exports
- [ ] Update README with facilities section

**Note**: If facilities master data not available, implement as **stub** with company-only fallback.

### Phase 4: Integration & Documentation (Week 6)

**PR #7: Final Integration**
- [ ] Comprehensive integration tests across all modules
- [ ] Performance benchmarks (ensure <100ms target)
- [ ] Update CLAUDE.md with new entity architectures
- [ ] Create MIGRATION.md (v0.1 → v0.2 guide)
- [ ] Update main README with complete API reference
- [ ] Version bump to v0.2.0
- [ ] Release notes

---

## I. Success Criteria

### Functional
- ✅ All 6 modules pass comprehensive tests (120+ new tests)
- ✅ APIs mirror existing patterns (company/metal/country consistency)
- ✅ Data loaders handle GCS + local + dev tables seamlessly
- ✅ Blocking/scoring achieves 99%+ reduction like existing modules

### Performance
- ✅ Query latency <100ms for all resolvers (warm cache)
- ✅ First load <1s for all data tables
- ✅ Memory footprint <500MB total (all modules loaded)

### Quality
- ✅ Test coverage ≥85% for all new modules
- ✅ No breaking changes to existing APIs
- ✅ Comprehensive documentation (README, module READMEs)
- ✅ Clean separation of concerns (no cross-module dependencies except utils)

### Integration
- ✅ Backwards compatible (v0.1 code works unchanged)
- ✅ Package exports clean and intuitive
- ✅ Works with existing CI/CD pipeline

---

## J. Dependencies & Requirements

### New Python Packages

```python
# requirements.txt additions

# Core entity resolution
pyyaml>=6.0                 # For baskets.yaml parsing
python-dateutil>=2.8        # For period parsing
isoweek>=1.3                # For ISO week handling (ISO 8601 weeks)

# Data loading & processing
google-cloud-storage>=2.10  # For GCS ticker_references access
requests>=2.28              # For HTTP downloads (GeoNames, USGS, etc.)
beautifulsoup4>=4.11        # For HTML scraping (LME brands, CME directory)

# Geographic utilities
geopy>=2.3                  # For geocoding fallback & haversine distance
pyrosm>=0.6                 # For OSM regional extracts (optional)

# Chemical/scientific data
# Note: ChEBI/PubChem accessed via direct HTTP/FTP (no special libs needed)
# IUPAC data scraped from static HTML (BeautifulSoup sufficient)

# Existing dependencies (already in repo)
pandas>=1.5
pyarrow>=10.0               # For parquet I/O
rapidfuzz>=2.13             # For fuzzy matching
```

### Data Download Dependencies

**One-time setup scripts** (not in requirements.txt):
```bash
# GeoNames data download
wget https://download.geonames.org/export/dump/admin1CodesASCII.txt
wget https://download.geonames.org/export/dump/cities1000.zip

# ChEBI (requires free registration)
# Manual download from: https://www.ebi.ac.uk/chebi/downloadsForward.do

# USGS datasets (varies by commodity/region)
# Downloaded via scripts in facilities/data/
```

### Environment Variables

```bash
# Data source overrides
export GSMC_TICKERS_PATH=/path/to/local/ticker_references.parquet
export ENTITYIDENTITY_FACILITIES_PATH=/path/to/facilities.parquet
export GEONAMES_DATA_DIR=/path/to/geonames/dumps  # For custom GeoNames location

# Feature flags
export ENTITYIDENTITY_USE_OSM_DELTAS=true  # Enable OSM augmentation (default: false)
export ENTITYIDENTITY_TEST_LIVE=1          # Enable live API tests (GeoNames, Nominatim)

# Attribution (for output files)
export ENTITYIDENTITY_ATTRIBUTION_FOOTER="Data sources: GeoNames, USGS, ChEBI (see DATA_SOURCES.md)"
```

### Data Requirements by Module

| Module | Required Data | Size | Source | Committed? |
|--------|--------------|------|--------|-----------|
| **baskets** | baskets.yaml | ~10KB | Manual curation | ✅ Yes |
| **baskets** | baskets.parquet | ~50KB | Built from YAML | ❌ No (generated) |
| **period** | None | - | Pure computation | - |
| **places** | admin1.parquet | ~500KB | GeoNames | ❌ No (built) |
| **places** | samples/admin1_sample.parquet | ~50KB | Subset for tests | ✅ Yes |
| **units** | unitconfig.yaml | ~5KB | Manual rules | ✅ Yes |
| **instruments** | ticker_references.parquet | ~2MB | GCS | ❌ No (external) |
| **facilities** | facilities.parquet | ~10MB | USGS + curated | ❌ No (built/optional) |
| **metals** | metals.parquet | ~500KB | IUPAC + ChEBI + USGS | ❌ No (built) |

### License Compliance Files

**Required attribution files**:
```
LICENSE_GEONAMES.txt        # CC-BY 4.0 attribution
LICENSE_CHEBI.txt           # CC-BY 4.0 attribution
LICENSE_OSM.txt             # ODbL (if using OSM deltas)
LICENSE_USGS.txt            # Public domain notice
```

Content for `LICENSE_GEONAMES.txt`:
```
This package uses data from GeoNames (geonames.org), licensed under
CC-BY 4.0. See https://creativecommons.org/licenses/by/4.0/

GeoNames data is available from: https://download.geonames.org/export/dump/

Please preserve this attribution when redistributing data derived from GeoNames.
```

### Data Source Attribution in Code

All loaders must include attribution:

```python
# places/data/build_admin1.py
def load_geonames_admin1():
    df = pd.read_csv("admin1CodesASCII.txt", sep='\t', ...)

    # Add attribution (required by CC-BY 4.0)
    df['source'] = 'geonames'
    df['attribution'] = 'Data from GeoNames (geonames.org)'
    df['license'] = 'CC-BY 4.0'

    return df
```

### Data Refresh Procedures

See `DATA_SOURCES.md` for update cadences:
- **GeoNames**: Optional daily refresh
- **ChEBI**: Optional monthly refresh
- **USGS**: Annual check (January for commodity summaries)
- **Instruments**: Internal cadence (GCS parquet)
- **Baskets**: Manual updates when issuer definitions change

---

## K. Open Questions & Decisions

### 1. Facilities Data Source
- **Option A**: External database (Postgres, BigQuery)
- **Option B**: Parquet file in `tables/facilities/`
- **Option C**: Stub module until data available
- **Decision**: Start with **Option C** (stub), add skip tests, implement full when data ready

### 2. Ticker References Update Frequency
- **Question**: How often to refresh `ticker_references.parquet` from GCS?
- **Proposal**: Daily check via GitHub Actions, cache locally for 24h
- **Decision**: TBD (defer to v0.2.1)

### 3. Fiscal Year Handling
- **Question**: Support non-calendar fiscal years in period module?
- **Proposal**: v0.2.0 uses calendar years only, add fiscal config in v0.3.0
- **Decision**: **Defer to v0.3.0**

### 4. Unit Conversion Safety
- **Question**: When ton system ambiguous, guess or warn?
- **Decision**: **Never guess** - always warn and preserve raw

---

## L. Migration Guide (v0.1 → v0.2)

### Backwards Compatibility
All v0.1 APIs remain unchanged:
```python
# v0.1 code works unchanged in v0.2
from entityidentity import company_identifier, metal_identifier

company_id = company_identifier("Apple")  # ✅ Still works
metal = metal_identifier("lithium")        # ✅ Still works
```

### New Capabilities
```python
# v0.2 additions
from entityidentity import (
    basket_identifier,       # NEW
    period_identifier,       # NEW
    instrument_identifier,   # NEW
    normalize_unit,          # NEW
    link_facility            # NEW
)

# Resolve baskets
basket = basket_identifier("PGM 4E")

# Normalize periods
period = period_identifier("H2 2026")

# Resolve tickers
inst = instrument_identifier("MB-CO-0005")

# Convert units
norm = normalize_unit({"value": 2150, "unit": "USD/t alloy", ...})

# Link facilities
facility = link_facility(company_hint="Anglo", place_hint={"country": "ZA"})
```

### Import Changes
**None required** - new exports are additive to `__init__.py`

---

## M. Appendix: Example Workflows

### Workflow 1: Extract Entities from News Article

```python
from entityidentity import (
    extract_companies, extract_metals_from_text, extract_periods,
    instrument_identifier, basket_identifier, period_identifier,
    normalize_unit, link_facility
)

text = """
Anglo American's Mogalakwena mine in Limpopo province reported
PGM 4E production of 450,000 oz in H2 2026. Fastmarkets assessed
MB-CO-0005 at USD 15.50/lb, up from USD 14.20/lb in Q2.
"""

# 1. Extract companies
companies = extract_companies(text, country_hint="ZA")
# → [{"name": "Anglo American Platinum Limited", "country": "ZA", ...}]

# 2. Extract metals (try instruments first)
inst = instrument_identifier("MB-CO-0005")  # Cobalt standard grade
if inst is None:
    metals = extract_metals_from_text(text)
# → Instrument found, use that

# 3. Extract baskets
basket = basket_identifier("PGM 4E")
# → {"basket_id": "pgm_4e", "metals": [{"metal_id": "Pt", ...}, ...]}

# 4. Extract periods
periods = extract_periods(text)
# → [{"period_id": "2026H2", ...}, {"period_id": "2026Q2", ...}]

# 5. Extract location
from entityidentity import extract_location

location = extract_location(text)
# → {"country": "ZA", "admin1": "Limpopo", "mentions": ["Limpopo province"], ...}

# 6. Link facility
facility = link_facility(
    company_hint=companies[0]['name'],
    place_hint=location,
    metal_hint="PGM"
)
# → {"facility_id": "mogalakwena_001", "link_score": 92, ...}

# 7. Normalize units
price = normalize_unit({
    "value": 15.50,
    "unit": "USD/lb",
    "basis": None  # Cobalt is simple, no conversion needed
})
# → {"norm": {"value": 15.50, "unit": "USD/lb"}, "warning": None}
```

### Workflow 2: Build Structured Database Record

```python
# Input: Messy news/email data
raw_data = {
    "company_name": "BHP Group Ltd.",
    "location": "Pilbara, Western Australia",
    "commodity": "iron ore",
    "time_period": "Q1-Q2 2026",
    "price": 2150,
    "price_unit": "USD/t alloy",
    "grade": {"Cr_pct": 65.0}
}

# Output: Canonical structured record
from entityidentity import (
    company_identifier, place_identifier, metal_identifier,
    period_identifier, normalize_unit, link_facility
)

# Resolve location
location = place_identifier("Western Australia")
# → {"country": "AU", "admin1": "Western Australia", "admin1_code": "AU-WA", ...}

record = {
    "company_id": company_identifier(raw_data["company_name"], "AU"),
    # → "BHP Group Limited:AU"

    "location": location,
    # → {"country": "AU", "admin1": "Western Australia", ...}

    "material_id": metal_identifier(raw_data["commodity"]),
    # → {"name": "Iron ore", "symbol": "Fe", ...}

    "period": period_identifier(raw_data["time_period"]),
    # → {"period_type": "date_range", "period_id": "2026Q1-2026Q2", ...}

    "price_normalized": normalize_unit({
        "value": raw_data["price"],
        "unit": raw_data["price_unit"],
        "grade": raw_data["grade"]
    }),
    # → {"norm": {"value": 1.52, "unit": "USD/lb", "basis": "Cr contained"}}

    "facility": link_facility(
        company_hint=raw_data["company_name"],
        place_hint=location,
        metal_hint="Fe"
    )
    # → {"facility_id": "pilbara_iron_ore_001", "link_score": 88, ...}
}
```

---

## End of Implementation Plan

**Next Steps**:
1. Review and approve this plan
2. Begin Phase 1 (Baskets + Period modules)
3. Iterate with feedback
4. Target v0.2.0 release in 6 weeks

**Questions?** Open issues on GitHub or discuss in team channel.
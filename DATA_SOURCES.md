# EntityIdentity Data Sources - Authoritative References

**Purpose**: Quick reference for all ground truth data sources used across entity modules.

**Pattern**: Each entity module follows the **source priority** pattern (like Companies: GLEIF → Wikidata → Exchanges) to ensure stable, authoritative identifiers.

---

## Source Priority Table

| Entity | Priority 1 | Priority 2 | Priority 3 | Priority 4 |
|--------|-----------|-----------|-----------|-----------|
| **Metals** | IUPAC elements | ChEBI/PubChem forms | USGS clusters | - |
| **Places** | GeoNames admin1 | OSM deltas (optional) | Nominatim fallback | - |
| **Baskets** | Issuer definitions | WPIC/AMIS standards | Facility overrides | - |
| **Units** | SI/BIPM | UCUM grammar | Market basis rules | - |
| **Instruments** | ticker_references.parquet | LME brand lists | CME product directory | Fastmarkets specs |
| **Facilities** | USGS facility datasets | USGS MRDS/USMIN | Curated (provenance) | Mindat (cite only) |
| **Periods** | ISO 8601 | Unicode CLDR (optional) | - | - |

---

## Detailed Source Documentation

### 1. Metals / Materials

**IUPAC** (Priority 1) - Chemical elements
- URL: https://iupac.org/what-we-do/periodic-table-of-elements/
- Coverage: 118 elements, canonical names, symbols
- License: Open
- Update: Stable
- Builder: `metals/data/build_metals.py → load_iupac_elements()`

**ChEBI** (Priority 2) - Chemical compounds
- URL: https://www.ebi.ac.uk/chebi/downloadsForward.do
- Coverage: ~200K compounds (Li₂CO₃, WO₃, FeCr, etc.)
- License: CC BY 4.0
- Update: Monthly releases
- Builder: `metals/data/build_metals.py → load_chebi_compounds()`

**PubChem** (Priority 2) - Synonyms
- URL: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- Coverage: Synonym lists for market terms
- License: PUG-REST API (free)
- Use: Map "APT" → Ammonium paratungstate, etc.

**USGS Mineral Commodity Summaries** (Priority 3) - Supply chain metadata
- URL: https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries
- Coverage: Cluster tags (Cu→Mo→Re, porphyry copper byproducts)
- License: Public domain
- Update: Annual (January)
- Builder: `metals/data/build_metals.py → load_usgs_clusters()`

---

### 2. Places / Geographic Entities

**GeoNames** (Priority 1) - Global coverage
- URL: https://download.geonames.org/export/dump/
- Files:
  - `allCountries.txt` - Full dump (12M places)
  - `admin1CodesASCII.txt` - Admin1 regions (~5K)
  - `cities1000.txt` - Cities >1K population (~50K)
  - `featureCodes_en.txt` - Feature definitions
  - `countryInfo.txt` - Country metadata
- Coverage: ~12M places globally
- License: CC-BY 4.0 (attribution: "Data from GeoNames (geonames.org)")
- Update: Daily exports
- Builder: `places/data/build_admin1.py → load_geonames_admin1()`

**OpenStreetMap** (Priority 2) - Regional deltas (optional)
- URL: https://wiki.openstreetmap.org/wiki/Overpass_API
- Filter: `place=city|town|village|hamlet`
- License: ODbL (share-alike)
- Use: Fresh changes between GeoNames updates

**Nominatim** (Priority 3) - Runtime fallback only
- URL: https://nominatim.org/release-docs/latest/api/Search/
- Rate limit: 1 req/sec max
- Use: One-off resolution for missing places

---

### 3. Baskets (Multi-Metal Composites)

**Issuer Definitions** (Priority 1) - From RNS/MD&A/technical reports
- Sources:
  - Anglo American Platinum annual reports
  - Sibanye-Stillwater technical updates
  - Northern Minerals REE definitions
- Examples:
  - PGM 4E: Pt+Pd+Rh+Au (Amplats standard)
  - PGM 5E+Au: Pt+Pd+Rh+Ru+Ir+Au
  - NdPr: Nd+Pr (didymium)
- URL: https://www.angloamericanplatinum.com (RNS announcements)
- Builder: `baskets/data/baskets.yaml` (manual curation with citations)

**WPIC** (Priority 2) - World Platinum Investment Council
- URL: https://www.platinuminvestment.com/
- Use: Validate definitions, industry context

**AMIS** (Priority 2) - Analytical standards
- URL: https://www.amis.co.za
- Use: Certification kits for 4E/6E in concentrates

**Facility Overrides** (Priority 3) - Site-specific prill ratios
- Storage: `facilities.parquet` with basket_overrides column
- Example: Mogalakwena 4E ratio ≠ Mototolo 4E ratio

---

### 4. Units & Basis

**SI/BIPM** (Priority 1) - Base units
- URL: https://www.bipm.org/en/publications/si-brochure
- Coverage: SI Brochure (9th ed., 2019, updated 2025)
- License: CC BY 4.0
- Use: Validate unit symbols, conversions

**UCUM** (Priority 2) - Unit grammar
- URL: https://ucum.org/ucum
- Coverage: Programmatic grammar for unit strings
- License: Open specification
- Use: Robust parsing, semantic equality

**Market Basis Rules** (Priority 3) - Commodity-specific conventions
- **FeCr**: $/lb Cr contained
  - Source: Fastmarkets/Argus spec sheets
  - URL: https://www.fastmarkets.com/commodities/ferro-alloys
- **APT**: $/mtu WO₃
  - Source: Fastmarkets APT specifications
- **Copper**: $/lb Cu contained
- Builder: `units/unitconfig.yaml` (hard-coded rules)

---

### 5. Instruments (Price Tickers)

**ticker_references.parquet** (Priority 1) - Internal ground truth
- Source: `gs://gsmc-market-data/ticker_references.parquet`
- Coverage: Curated tickers from Fastmarkets, LME, CME, Argus
- Schema: ticker, source, instrument_name, currency, unit, basis, material_hint
- Update: Internal cadence
- Loader: `instruments/instrumentloaders.py → load_parquet_from_gcs()`

**LME Brand Lists** (Priority 2) - Deliverable brands
- URL: https://www.lme.com/en/trading/approved-brands
- Coverage: Brands deliverable against LME contracts
- Use: Validate instrument names, cross-reference

**CME/COMEX Product Directory** (Priority 3) - Futures tickers
- URL: https://www.cmegroup.com/markets/metals.html
- Coverage: Unified symbols (HG=copper, SI=silver, GC=gold)
- Use: Map tickers to metals

**Fastmarkets Spec Pages** (Priority 4) - Price assessment metadata
- URL: https://www.fastmarkets.com/commodities/base-metals
- Example: MB-CO-0005 = "Cobalt standard grade, in-whs Rotterdam, $/lb"
- Use: Confirm unit/basis for assessments

---

### 6. Facilities (Mines, Smelters, Refineries)

**USGS Facility Datasets** (Priority 1) - Regional/commodity maps
- URL: https://mrdata.usgs.gov/general/map-global.html
- Examples:
  - "Mineral Facilities of Europe" (1,700+ mines/plants, 2013)
  - "World Copper Smelters" (locations, capacity, process)
  - "Principal Gold-Producing Districts of the United States"
- License: Public domain
- Update: Irregular (archive but authoritative)
- Builder: `facilities/data/build_facilities.py → load_usgs_facilities_europe()`

**USGS MRDS/USMIN** (Priority 2) - Deposit localities
- URL: https://mrdata.usgs.gov/mrds/
- Coverage: Global deposits with IDs, coordinates, commodity tags
- Use: Tie facilities to deposit IDs

**Curated Additions** (Priority 3) - From issuer reports, EITI, NI 43-101
- Sources:
  - Company technical reports
  - EITI disclosures (e.g., South Africa mining cadastre)
  - NI 43-101 filings
- Storage: `curated_facilities.parquet` with `source_url` column
- Requirement: Must cite source per record

**Mindat** (Reference Only) - Per-record lookups with citation
- URL: https://www.mindat.org
- Coverage: Comprehensive locality database
- License: Bulk export restricted
- Use: Validate coordinates, cross-reference names (cite per query)

---

### 7. Periods / Calendars

**ISO 8601** (Priority 1) - Calendar weeks & date/time standards
- URL: https://en.wikipedia.org/wiki/ISO_8601
- Rules:
  - Week starts Monday
  - Week 1 contains first Thursday of year
  - Format: 2025-W02
- License: Open standard
- Implementation: `period/periodidentity.py` uses `isoweek` library

**Unicode CLDR** (Priority 2) - Localized names (optional)
- URL: https://cldr.unicode.org
- Coverage: Month/quarter names in 700+ locales
- Use: Localized period labels (if needed)

---

## License Compliance

### Attribution Required

**CC-BY 4.0** (require attribution):
- **GeoNames**: "Data from GeoNames (geonames.org)"
- **ChEBI**: "Data from ChEBI (www.ebi.ac.uk/chebi)"
- **BIPM**: "SI units from BIPM (www.bipm.org)"

Include attribution in:
1. Data files: `attribution` column in parquet
2. Package metadata: `__init__.py` or `README.md`
3. Generated output: Footer/metadata when exporting

### ODbL (Share-Alike)
- **OpenStreetMap**: If using OSM deltas, derived data must be ODbL
- **Mitigation**: Make OSM use optional, document license requirement

### Public Domain
- **USGS**: All USGS data is public domain (no attribution required)
- **IUPAC**: Open public data

### Restricted
- **Mindat**: Bulk export restricted; use only for per-record lookups with citation

---

## Update Cadences

| Source | Cadence | Auto-Update? | Manual Review? |
|--------|---------|--------------|----------------|
| IUPAC elements | Rare (new elements) | No | Yes (when new element announced) |
| ChEBI | Monthly releases | Optional | Recommended (monthly) |
| PubChem | Continuous API | Runtime | No |
| USGS summaries | Annual (January) | Optional | Yes (January update) |
| GeoNames | Daily exports | Optional | No (stable) |
| OSM | Continuous | Optional | No |
| WPIC/AMIS | Ad-hoc | Manual | Yes (when baskets change) |
| SI/UCUM | Stable | No | No |
| LME brand lists | Regular (exchange updates) | Optional | Yes (quarterly check) |
| CME directory | Regular | Optional | No |
| USGS facilities | Irregular | Manual | Yes (when new datasets released) |
| ISO 8601 | Stable | No | No |

---

## Builder Scripts Summary

| Entity | Builder Script | Primary Source | Output |
|--------|---------------|----------------|--------|
| Metals | `metals/data/build_metals.py` | IUPAC + ChEBI + USGS | `metals.parquet` |
| Places | `places/data/build_admin1.py` | GeoNames admin1CodesASCII.txt | `places.parquet` |
| Baskets | `baskets/data/build_baskets.py` | `baskets.yaml` (manual) | `baskets.parquet` |
| Units | N/A (config only) | `unitconfig.yaml` (manual) | - |
| Instruments | `instruments/instrumentloaders.py` | GCS parquet + augments | Runtime (LRU cached) |
| Facilities | `facilities/data/build_facilities.py` | USGS datasets + curated | `facilities.parquet` |
| Periods | N/A (pure computation) | ISO 8601 logic | Runtime |

---

## Quick Reference: Data Download URLs

```bash
# GeoNames
wget https://download.geonames.org/export/dump/allCountries.zip
wget https://download.geonames.org/export/dump/admin1CodesASCII.txt
wget https://download.geonames.org/export/dump/cities1000.zip

# ChEBI (requires free registration)
# https://www.ebi.ac.uk/chebi/downloadsForward.do
# Download: compounds.tsv.gz, names.tsv.gz

# USGS Mineral Commodity Summaries
# https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries
# Annual PDF + data tables

# USGS MRDS
# https://mrdata.usgs.gov/mrds/
# GeoJSON/CSV downloads by region

# LME Brand Lists (HTML scrape or PDF)
# https://www.lme.com/en/trading/approved-brands

# CME Product Directory (HTML/JSON)
# https://www.cmegroup.com/markets/metals.html
```

---

## Notes & Caveats

1. **Mindat**: Excellent for lookups, but bulk redistribution restricted. Cite per record.
2. **USGS facilities**: Some datasets are older (2013 for Europe). Keep `last_updated` field.
3. **ISO 8601 weeks**: Differ from US week numbering. Use `isoweek` library for correct Monday-start logic.
4. **FeCr/APT conversions**: Never guess ton system or grade. Return raw with warning if insufficient data.
5. **GeoNames attribution**: Required by CC-BY 4.0. Include in all outputs.
6. **OSM ODbL**: Share-alike license. If using OSM deltas, derived data must be ODbL.

---

**End of Data Sources Reference**

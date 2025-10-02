# EntityIdentity [![Tests](https://github.com/microprediction/entityidentity-installtest/actions/workflows/tests_312.yml/badge.svg)](https://github.com/microprediction/entityidentity-installtest/actions/workflows/tests_312.yml) [![License](https://img.shields.io/badge/license-MIT-blue)]()


**Resolve any company name to a globally unique identifier.**

Takes messy company names (tickers, abbreviations, variations) and returns stable canonical identifiers.

Fast, in-memory resolution using fuzzy matching and smart normalization. No server required.

## Installation

```bash
pip install entityidentity
```

## Quick Start

```python
from entityidentity import company_identifier, country_identifier

# Company resolution - main use case
identifier = company_identifier("Apple")
print(identifier)  # → 'Apple Inc:US'

# Works with variations
company_identifier("Apple Inc.")      # → 'Apple Inc:US'
company_identifier("Apple Computer")  # → 'Apple Inc:US'  
company_identifier("BHP", "AU")       # → 'BHP Group Limited:AU'

# Major mining companies
company_identifier("Anglo American")  # → 'Anglo American plc:GB'
company_identifier("Glencore")        # → 'Glencore plc:GB'
company_identifier("Barrick Gold")    # → 'Barrick Gold Corporation:CA'

# Returns None if no confident match
company_identifier("Unknown XYZ")     # → None

# Country resolution - robust with fuzzy matching
country_identifier("USA")                # → 'US'
country_identifier("United Kingdom")     # → 'GB'
country_identifier("England")            # → 'GB'
country_identifier("Holland")            # → 'NL'
country_identifier("Untied States")      # → 'US' (typo tolerance!)

# Batch resolution
from entityidentity import country_identifiers
country_identifiers(["USA", "Holland", "England"])  # → ['US', 'NL', 'GB']

# Metal resolution - NEW! Resolve metal names, symbols, and forms
from entityidentity import metal_identifier
metal_identifier("Pt")                   # → {'name': 'Platinum', 'symbol': 'Pt', ...}
metal_identifier("copper")               # → {'name': 'Copper', 'symbol': 'Cu', ...}
metal_identifier("APT 88.5%")           # → {'name': 'Ammonium paratungstate', ...}
metal_identifier("lithium carbonate")    # → {'name': 'Lithium carbonate', 'formula': 'Li2CO3', ...}
```

**That's it!** One function call returns a stable, globally unique identifier.

## Why Use This?

**Problem**: Company names are messy
- Tickers: "BHP", "AAL", "ABX"
- Variations: "Apple Inc", "Apple Inc.", "Apple Computer"
- Formats: "APPLE INC" vs "Apple Inc" vs "Apple, Inc."

**Solution**: Canonical identifiers
```python
company_identifier("Apple Inc.")     # All resolve to
company_identifier("Apple Computer") # → 'Apple Inc:US'
company_identifier("Apple")          # (same identifier)
```

**Current Dataset**: The pre-built dataset focuses on **mining, metals, and manufacturing** companies (~655 companies from GLEIF, Wikidata, and major stock exchanges). Perfect for supply chain analysis, mining industry research, and commodity tracking.

### API Functions

Three primary resolution functions:
- **`company_identifier(name, country=None)`** - Resolve company names to canonical identifiers
- **`country_identifier(name)`** - Resolve country names/codes to ISO 3166-1 alpha-2
  - Multi-stage pipeline: `country_converter` → `pycountry` → fuzzy matching
  - Handles typos, colloquialisms, and cultural variations (e.g., "Holland", "England")
  - Configurable output formats (ISO2, ISO3, numeric)
- **`metal_identifier(name, category=None, cluster=None)`** - Resolve metal names/symbols to canonical forms
  - 50 metals: elements, alloys, compounds (Li, Li₂CO₃, FeCr, APT, etc.)
  - Supply chain clustering (porphyry copper → Mo, Re, Se, Te)
  - Commercial forms and trade specifications

Batch processing:
- **`country_identifiers(names)`** - Resolve multiple countries at once

Plus supporting functions:
- **`list_companies()`** - Browse available companies
- **`extract_companies(text)`** - Find company mentions in text
- **`normalize_company_name(name)`** - Normalize company names for matching
- **`list_metals(category=None, cluster=None)`** - List metals by category/cluster
- **`match_metal(name, k=5)`** - Get top-K metal candidates with scores
- **`extract_metals_from_text(text)`** - Extract metal references from text

For more data:
- 🔄 Build your own dataset with `scripts/companies/build_filtered_dataset.sh`
- 📦 Or use the API with your own company database

## Features

- **One function call**: `company_identifier(name, country)` returns stable ID
- **Fast**: <100ms for most queries, no server required
- **Smart matching**: Handles abbreviations, legal suffixes, unicode
- **Multiple sources**: GLEIF LEI, Wikidata, stock exchanges
- **Stable**: Same company always gets same identifier, regardless of source

## Advanced Usage

### Get Full Company Details

```python
from entityidentity import match_company

# Get complete company record
company = match_company("Microsoft", country="US")
if company:
    print(f"Name: {company['name']}")
    print(f"Country: {company['country']}")
    print(f"LEI: {company.get('lei', 'N/A')}")
```

### See Match Alternatives

```python
from entityidentity import resolve_company

# Get all potential matches with scores
result = resolve_company("Tesla")
print(f"Best match: {result['final']['name']}")
print(f"Confidence: {result['decision']}")

# Review alternatives
for match in result['matches']:
    print(f"  {match['name']} ({match['country']}) - Score: {match['score']}")
```

## Data Sources

The package includes pre-built company data from:

- **GLEIF LEI**: Global Legal Entity Identifier database
- **Wikidata**: Rich company metadata and aliases
- **Stock Exchanges**: ASX, LSE, TSX listings

Sample data is included in the package for immediate use.

## Company Identifiers

### How Company Names are Derived

Each company has a canonical identifier in the format: `{name}:{country}`

**Examples:**
- `Apple Inc:US`
- `BHP Group Limited:AU`
- `Anglo American plc:GB`

### Country Codes

We use **ISO 3166-1 alpha-2** standard (2-letter country codes):

| Code | Country | Code | Country |
|------|---------|------|---------|
| US | United States | GB | United Kingdom |
| AU | Australia | CA | Canada |
| DE | Germany | FR | France |
| IN | India | CN | China |
| JP | Japan | BR | Brazil |
| IT | Italy | ES | Spain |
| MX | Mexico | SE | Sweden |

[Full ISO 3166-1 list](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)

### Name Canonicalization Process

To ensure consistent identifiers regardless of load order or source formatting, company names go through canonicalization:

1. **Remove commas before legal suffixes**: `"Tesla, Inc."` → `"Tesla Inc."`
2. **Remove periods from legal suffixes**: `"Apple Inc."` → `"Apple Inc"`
3. **Normalize unicode to ASCII**: `"Société Générale"` → `"Societe Generale"`
4. **Keep essential characters**: Letters, numbers, spaces, hyphens, ampersands
5. **Collapse multiple spaces**: `"BHP  Group"` → `"BHP Group"`

This is handled by `canonicalize_company_name()` in `entityidentity.companies.companynormalize`.

### Source Priority System

When the same company appears in multiple data sources (e.g., GLEIF and ASX), we use **deterministic source priority** to ensure the same name is always selected, regardless of load order:

**Priority (highest to lowest):**
1. **GLEIF** (Priority 1) - Official legal names from regulatory filings
2. **Wikidata** (Priority 2) - Crowdsourced but well-curated
3. **Stock Exchanges** (Priority 3) - Often inconsistent formatting (ALL CAPS, etc.)
   - ASX, LSE, TSX

**Why This Matters:**

Without priority, the identifier could drift based on load order:
- Load GLEIF first: `"Apple Inc:US"` 
- Load ASX first: `"APPLE INC:US"` ❌ Different identifier!

With priority, GLEIF always wins:
- Any load order: `"Apple Inc:US"` ✅ Stable identifier!

This ensures that:
- **Identifiers are stable** across different database builds
- **Names are readable** (not ALL CAPS from exchanges)
- **Load order doesn't matter** - same company always gets same name

### Deduplication Strategy

Companies are deduplicated in two passes:

1. **By LEI** (if available): Companies with the same LEI are considered identical
   - Keeps the record from the highest-priority source
   
2. **By (name_norm, country)**: For companies without LEI
   - Uses normalized name matching
   - Keeps the record from the highest-priority source

This ensures that even if a company is listed on multiple exchanges, it appears only once with the most authoritative name.

## API Reference

### Primary Functions

#### `company_identifier(name, country=None)`

**Primary company API**: Get canonical identifier for a company.

**Parameters**:
- `name` (str): Company name in any format
- `country` (str, optional): ISO 2-letter country code hint (improves accuracy)

**Returns**: String identifier in format `"name:country"` or `None` if no confident match

**Examples**:
```python
company_identifier("Apple")                  # → 'Apple Inc:US'
company_identifier("BHP", country="AU")      # → 'BHP Group Limited:AU'
company_identifier("Anglo American")         # → 'Anglo American plc:GB'
company_identifier("Glencore")               # → 'Glencore plc:GB'
company_identifier("Unknown Company XYZ")    # → None (no match)
```

#### `country_identifier(name)`

**Primary country API**: Resolve country names/codes to ISO 3166-1 alpha-2.

**Parameters**:
- `name` (str): Country name or code in any format

**Returns**: ISO 3166-1 alpha-2 code (e.g., "US") or `None` if not recognized

**Examples**:
```python
country_identifier("USA")              # → 'US'
country_identifier("United Kingdom")   # → 'GB'
country_identifier("Holland")          # → 'NL'
country_identifier("England")          # → 'GB'
country_identifier("Untied States")    # → 'US' (typo tolerance!)
```

**Advanced**: For full control, use `entityidentity.countries.fuzzycountry.country_identifier()` with options:
- `to="ISO2"` (default), `"ISO3"`, or `"numeric"`
- `fuzzy=True` (default) - enable typo tolerance
- `fuzzy_threshold=85` (default) - minimum similarity score

#### `country_identifiers(names)`

**Batch country resolution**: Resolve multiple countries at once.

**Parameters**:
- `names` (iterable): List of country names or codes

**Returns**: List of ISO codes (or `None` for unrecognized entries)

**Example**:
```python
country_identifiers(["USA", "Holland", "England"])  # → ['US', 'NL', 'GB']
```

#### `get_identifier(name, country=None)`

**Backwards compatibility alias** for `company_identifier()`. Use `company_identifier()` in new code.

### `match_company(name, country=None)`

Get full company record with all metadata.

**Parameters**:
- `name` (str): Company name to match
- `country` (str, optional): ISO 2-letter country code

**Returns**: Dictionary with company data, or `None` if no good match found

**Example**:
```python
company = match_company("BHP", "AU")
# Returns: {'name': 'BHP Group Limited', 'country': 'AU', 'lei': '...', ...}
```

### `resolve_company(name, country=None, **kwargs)`

Advanced: Full resolution with all match candidates and scores.

**Parameters**:
- `name` (str): Company name to resolve
- `country` (str, optional): ISO 2-letter country code

**Returns**: Dictionary with:
- `final`: Best matched company (if confident)
- `decision`: Decision type ('auto_high_conf', 'needs_hint_or_llm', etc.)
- `matches`: List of all potential matches with scores

**Example**:
```python
result = resolve_company("Anglo American")
print(result['final'])    # Best match
print(result['matches'])  # All candidates with scores
```

### `list_companies(country=None, search=None, limit=None, data_path=None)`

List companies with optional filtering.

**Parameters**:
- `country` (str, optional): ISO 2-letter country code filter
- `search` (str, optional): Search term for company names
- `limit` (int, optional): Maximum number of results
- `data_path` (str, optional): Path to custom data file

**Returns**: pandas DataFrame with filtered company data

**Examples**:
```python
# List all US companies
us = list_companies(country="US")

# Search for mining companies
mining = list_companies(search="mining")

# Top 10 Australian companies
top_au = list_companies(country="AU", limit=10)
```

### `load_companies(data_path=None)`

Load full company database into memory.

**Parameters**:
- `data_path` (str, optional): Path to custom data file

**Returns**: pandas DataFrame with all company data

## Performance

- **Query speed**: <100ms for most lookups
- **Database size**: ~10-50MB (compressed Parquet format)
- **Memory usage**: ~200-500MB when loaded

### Supporting Functions

#### `normalize_company_name(name)`

Normalize company name for matching (removes legal suffixes, unicode, etc.)

**Example**:
```python
normalize_company_name("Apple Inc.")  # → 'apple'
```

## Advanced Usage

### Use Custom Data

```python
from entityidentity import load_companies, match_company

# Load your own company data
df = load_companies("path/to/your/companies.parquet")

# Then use normally
match = match_company("Company Name")
```

### List Companies

```python
from entityidentity import list_companies

# List all companies
all_companies = list_companies()

# List companies by country
us_companies = list_companies(country="US")
au_companies = list_companies(country="AU")

# Search for companies
mining = list_companies(search="mining")
tech = list_companies(search="tech")

# Combine filters
uk_tech = list_companies(country="GB", search="tech", limit=10)

# Access data
for _, company in uk_tech.iterrows():
    print(f"{company['name']} - {company['country']}")
```

### Access Raw Data

```python
from entityidentity import load_companies

# Get full DataFrame for advanced filtering
companies = load_companies()

# Custom filtering
filtered = companies[
    (companies['country'] == 'US') & 
    (companies['name_norm'].str.contains('tech'))
]
```

## Support

- **Development**: See [CLAUDE.md](CLAUDE.md) for architecture and development notes
- **Maintenance**: See [MAINTENANCE.md](MAINTENANCE.md) for maintenance procedures
- **Issues**: Report bugs on GitHub
- **License**: MIT

## Author

Peter Cotton

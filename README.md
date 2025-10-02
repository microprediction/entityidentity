# EntityIdentity [![Tests](https://github.com/microprediction/entityidentity-installtest/actions/workflows/tests_312.yml/badge.svg)](https://github.com/microprediction/entityidentity-installtest/actions/workflows/tests_312.yml) [![License](https://img.shields.io/badge/license-MIT-blue)]()

**Resolve any company name to a globally unique identifier.**

Fast, in-memory entity resolution for companies, countries, and metals using fuzzy matching and smart normalization. Takes messy names (tickers, abbreviations, variations) and returns stable canonical identifiers in <100ms. No server required.

## Installation

```bash
pip install entityidentity
```

## Quick Start

```python
from entityidentity import company_identifier, country_identifier, metal_identifier
from entityidentity import basket_identifier, period_identifier

# Company resolution - main use case
company_identifier("Apple")              # → 'Apple Inc:US'
company_identifier("BHP", "AU")          # → 'BHP Group Limited:AU'
company_identifier("Anglo American")     # → 'Anglo American plc:GB'

# Country resolution - robust with fuzzy matching
country_identifier("USA")                # → 'US'
country_identifier("United Kingdom")     # → 'GB'
country_identifier("Untied States")      # → 'US' (typo tolerance!)

# Metal resolution - elements, alloys, compounds
metal_identifier("Pt")                   # → {'name': 'Platinum', 'symbol': 'Pt', ...}
metal_identifier("lithium carbonate")    # → {'name': 'Lithium carbonate', 'formula': 'Li2CO3', ...}

# Basket resolution - metal combinations
basket_identifier("PGM 4E")              # → {'basket_id': 'pgm-4e', 'name': 'PGM 4E', ...}

# Period resolution - temporal normalization
period_identifier("H2 2026")             # → {'period_type': 'half', 'period_id': '2026H2', ...}
period_identifier("Q1 2026")             # → {'period_type': 'quarter', 'period_id': '2026Q1', ...}
```

**That's it!** One function call returns a stable, globally unique identifier.

---

## Table of Contents

1. [Why Use This?](#why-use-this)
2. [Core Features](#core-features)
3. [Complete API Reference](#complete-api-reference)
4. [Architecture & Algorithms](#architecture--algorithms)
5. [Data Sources](#data-sources)
6. [Performance & Benchmarks](#performance--benchmarks)
7. [Advanced Usage](#advanced-usage)
8. [Development](#development)

---

## Why Use This?

**Problem**: Entity names are messy across data sources
- **Companies**: "BHP" vs "BHP Group" vs "BHP Group Limited" vs "Broken Hill Proprietary"
- **Countries**: "USA" vs "United States" vs "US" vs "Untied States" (typos)
- **Metals**: "Li" vs "lithium" vs "lithium carbonate" vs "Li₂CO₃"

**Solution**: Canonical identifiers that work across all variations
```python
# All these resolve to the same identifier
company_identifier("Apple Inc.")      # → 'Apple Inc:US'
company_identifier("Apple Computer")  # → 'Apple Inc:US'
company_identifier("AAPL")            # → 'Apple Inc:US'
```

**Current Dataset**: Pre-filtered for **mining, metals, and manufacturing** (~655 companies from GLEIF, Wikidata, and major stock exchanges). Perfect for:
- Supply chain analysis
- Mining industry research
- Commodity tracking
- Financial analysis
- Trade document processing

---

## Core Features

### Multi-Entity Resolution
- **Companies**: 655+ pre-filtered (or build 100K+ full database)
- **Countries**: 249 ISO-compliant with fuzzy matching
- **Metals**: 50+ elements, alloys, compounds with supply chain clustering

### Fast Performance
- **<100ms** query latency (99%+ search space reduction via blocking)
- **In-memory** operation (~50-200MB RAM)
- **Zero infrastructure** - pure Python, no database server

### Intelligent Matching
- **Fuzzy scoring** with RapidFuzz (handles typos, abbreviations)
- **Multi-stage blocking** (country filter → prefix match → fuzzy score)
- **Domain-specific normalization** (legal suffixes, unicode, case folding)
- **Source priority system** ensures stable identifiers regardless of load order

### Production Ready
- **1,679 lines of tests** (131 test cases)
- **Clean API** - 3 primary functions, comprehensive reference
- **LRU caching** - loads once per session, minimal latency
- **Extensive documentation** - architecture, algorithms, integration patterns

---

## Complete API Reference

### Primary Functions

#### Company Resolution

##### `company_identifier(name, country=None)`
**Primary API**: Get canonical identifier for a company.

**Parameters**:
- `name` (str): Company name in any format
- `country` (str, optional): ISO 2-letter country code hint (improves accuracy)

**Returns**: String `"canonical_name:country"` or `None` if no confident match

**Examples**:
```python
company_identifier("Apple")                  # → 'Apple Inc:US'
company_identifier("BHP", country="AU")      # → 'BHP Group Limited:AU'
company_identifier("Anglo American")         # → 'Anglo American plc:GB'
company_identifier("Glencore")               # → 'Glencore plc:GB'
company_identifier("Unknown XYZ")            # → None
```

##### `match_company(name, country=None)`
Get full company record with metadata.

**Returns**: Dictionary with `name`, `country`, `lei`, `wikidata_qid`, `aliases`, etc.

```python
company = match_company("BHP", "AU")
# {'name': 'BHP Group Limited', 'country': 'AU', 'lei': '...', ...}
```

##### `resolve_company(name, country=None, **kwargs)`
Advanced: Full resolution with all candidates and scores.

**Returns**: Dictionary with `final`, `decision`, `matches`, `explanation`

**Advanced Parameters**:
- `use_llm_tiebreak` (bool): Use LLM for ambiguous cases
- `k` (int): Number of candidates to return (default 5)
- `high_conf_threshold` (float): Auto-select threshold (default 88.0)
- `uncertain_threshold` (float): Minimum viable score (default 76.0)

```python
result = resolve_company("Tesla")
print(result['final'])         # Best match
print(result['decision'])      # 'auto_high_conf', 'needs_hint_or_llm', etc.
print(result['matches'])       # All candidates with scores
```

##### `list_companies(country=None, search=None, limit=None)`
Browse/filter company database.

```python
us_mining = list_companies(country="US", search="mining", limit=10)
```

##### `extract_companies(text, country_hint=None, min_confidence=0.75)`
Extract company mentions from text.

```python
text = "BHP and Rio Tinto announced new copper projects in Chile."
companies = extract_companies(text)
# [{'name': 'BHP Group Limited', 'country': 'AU', ...}, ...]
```

#### Country Resolution

##### `country_identifier(name, to="ISO2", fuzzy=True, fuzzy_threshold=85)`
**Primary API**: Resolve country names/codes to ISO standards.

**Parameters**:
- `name` (str): Country name or code in any format
- `to` (str): Output format - "ISO2" (default), "ISO3", or "numeric"
- `fuzzy` (bool): Enable typo tolerance (default True)
- `fuzzy_threshold` (int): Minimum similarity score (default 85)

**Returns**: ISO code (e.g., "US") or `None`

**Examples**:
```python
country_identifier("USA")              # → 'US'
country_identifier("United Kingdom")   # → 'GB'
country_identifier("Holland")          # → 'NL'  (colloquialism)
country_identifier("England")          # → 'GB'  (cultural variation)
country_identifier("Untied States")    # → 'US'  (typo tolerance!)
```

**Multi-stage pipeline**:
1. `country_converter` - 250+ name variations
2. `pycountry` - Official ISO 3166 database
3. Fuzzy matching - RapidFuzz for typos

##### `country_identifiers(names, **kwargs)`
Batch processing for multiple countries.

```python
country_identifiers(["USA", "Holland", "England"])  # → ['US', 'NL', 'GB']
```

#### Metal Resolution

##### `metal_identifier(name, category=None, cluster=None, threshold=90)`
**Primary API**: Resolve metal names/symbols to canonical forms.

**Parameters**:
- `name` (str): Metal name, symbol, or commercial form
- `category` (str, optional): Filter by "base", "precious", "rare_earth", "specialty"
- `cluster` (str, optional): Filter by supply chain cluster ("battery", "steel", "porphyry_copper", etc.)
- `threshold` (int): Minimum fuzzy match score (default 90)

**Returns**: Dictionary with `name`, `symbol`, `formula`, `category_bucket`, `cluster_id`, etc.

**Examples**:
```python
metal_identifier("Pt")                    # → {'name': 'Platinum', 'symbol': 'Pt', ...}
metal_identifier("copper")                # → {'name': 'Copper', 'symbol': 'Cu', ...}
metal_identifier("lithium carbonate")     # → {'name': 'Lithium carbonate', 'formula': 'Li2CO3', ...}
metal_identifier("APT 88.5%")            # → {'name': 'Ammonium paratungstate', ...}
metal_identifier("lithium:carbonate")     # Form hint syntax → Li2CO3
```

**Supply Chain Clustering**:
```python
# Find battery metals
battery_metals = list_metals(cluster="battery")
# → Lithium, Cobalt, Nickel, Graphite, Manganese

# Find porphyry copper byproducts
porphyry = list_metals(cluster="porphyry_copper")
# → Molybdenum, Rhenium, Selenium, Tellurium
```

##### `match_metal(name, k=5)`
Get top-K metal candidates with scores.

```python
candidates = match_metal("plat", k=3)
# [{'name': 'Platinum', 'score': 95}, {'name': 'Platinum group metals', 'score': 88}, ...]
```

##### `list_metals(cluster=None, category=None)`
Browse/filter metal database.

```python
# All precious metals
precious = list_metals(category="precious")

# All battery supply chain metals
battery = list_metals(cluster="battery")
```

##### `extract_metals_from_text(text, cluster_hint=None)`
Extract metal references from text.

```python
text = "Lithium carbonate and cobalt sulfate prices rose on battery demand."
metals = extract_metals_from_text(text, cluster_hint="battery")
# [{'name': 'Lithium carbonate', ...}, {'name': 'Cobalt', ...}]
```

##### `extract_metal_pairs(text)`
Find metal combinations/alloys.

```python
text = "The copper-nickel alloy showed excellent corrosion resistance."
pairs = extract_metal_pairs(text)
# [('copper', 'nickel')]
```

### Normalization Functions

#### `normalize_company_name(name)` / `canonicalize_company_name(name)`
Two-layer normalization for different purposes.

```python
# Aggressive normalization for matching
normalize_company_name("BHP Group Limited")  # → 'bhp group'

# Readable canonicalization for identifiers
canonicalize_company_name("BHP GROUP LTD.")  # → 'BHP GROUP LTD'
```

#### `normalize_metal_name(name)` / `canonicalize_metal_name(name)` / `slugify_metal_name(name)`
Metal-specific normalization suite.

```python
normalize_metal_name("Lithium Carbonate")     # → 'lithium carbonate'  (matching)
canonicalize_metal_name("lithium carbonate")  # → 'Lithium carbonate'  (display)
slugify_metal_name("Lithium carbonate")       # → 'lithium-carbonate'  (URLs)
```

### Utility Functions

#### `get_company_id(company, safe=False)`
Generate stable identifier from company dictionary.

```python
company = match_company("BHP", "AU")
company_id = get_company_id(company)  # → 'BHP Group Limited:AU'
```

#### `load_companies(data_path=None)` / `load_metals(path=None)`
Load full databases into memory.

```python
companies_df = load_companies()      # Load all companies
metals_df = load_metals()            # Load all metals
```

---

## Architecture & Algorithms

### Company Resolution Algorithm

**6-Stage Pipeline** (resolve_company):

#### 1. Normalization
```
Input: "BHP Group Ltd."
→ Canonical: "BHP Group Ltd" (for display)
→ Normalized: "bhp group" (for matching)

Actions:
- Remove legal suffixes (Ltd, Inc, GmbH, etc.)
- Unicode → ASCII
- Lowercase, remove punctuation
- Collapse whitespace
```

#### 2. Data Loading
```
Strategy:
1. Check LRU cache (instant if loaded)
2. Load from Parquet (~0.3s for 50MB)
3. Add computed columns (name_norm, aliases)

Result: ~655 companies (sample) or 100K+ (full) in memory
```

#### 3. Blocking (99%+ reduction)
```
block_candidates(df, query_norm, country)

Filter 1: Country hint
  2M companies → 50K (if country="AU")

Filter 2: First-token prefix match
  name_norm starts with "bhp" OR
  any alias starts with "bhp"
  50K → ~10 candidates

Result: 99.95% reduction, <1ms
```

#### 4. Scoring
```
score_candidates(df, query_norm, country, k=5)

For each candidate:
  score_name = RapidFuzz.WRatio(query, name_norm)
  score_alias = max(WRatio(query, alias) for alias in aliases)
  base_score = max(score_name, score_alias)

  # Boosts
  if candidate.country == country: base_score += 2
  if candidate.has_lei: base_score += 1

Return top-K by score
```

#### 5. Decision Logic
```
Thresholds:
- High Confidence: score ≥ 88 AND gap ≥ 6
- Uncertain: 76 ≤ score < 88
- No Match: score < 76

If high confidence:
  → Auto-select best match
Elif uncertain:
  → Return candidates (needs hint or LLM)
Else:
  → Return None
```

#### 6. Result Formatting
```
{
  'query': 'bhp',
  'final': {'name': 'BHP Group Limited', 'country': 'AU', ...},
  'decision': 'auto_high_conf',
  'matches': [
    {'name': 'BHP Group Limited', 'score': 95.0, ...},
    {'name': 'BHP Billiton', 'score': 92.0, ...},
  ],
  'explanation': 'High confidence match (score=95.0, gap=3.0)'
}
```

### Metal Resolution Algorithm

**5-Step Blocking Strategy** (resolve_metal):

```
1. Exact Symbol Match (for queries ≤3 chars)
   "Li" → Lithium (immediate return)

2. Category Filter (if provided)
   category="precious" → Gold, Silver, Platinum, etc.
   (~75% reduction)

3. Name Prefix Blocking
   First 3 chars of normalized name
   "plat*" → Platinum, Platinum group metals
   (~95% reduction)

4. Cluster Filter (if provided)
   cluster="battery" → Li, Co, Ni, Graphite, Mn
   (supply chain grouping)

5. Fuzzy Scoring
   RapidFuzz.WRatio on remaining candidates
   Check name + 10 alias columns
   Return best if score ≥ threshold (default 90)
```

**Form Hint Parsing**:
```python
"lithium:carbonate" → metal="lithium", form="carbonate"
                   → Match "Lithium carbonate" (Li2CO3)

"tungsten:apt"     → metal="tungsten", form="apt"
                   → Match "Ammonium paratungstate"
```

### Country Resolution Algorithm

**3-Stage Fallback Pipeline** (country_identifier):

```
Stage 1: country_converter
  - Handles 250+ country name variations
  - Fast dictionary lookup
  - Includes historical names, common aliases

Stage 2: pycountry
  - Official ISO 3166 database
  - ISO2, ISO3, numeric codes
  - Authoritative but strict

Stage 3: Fuzzy Matching
  - RapidFuzz for typo tolerance
  - "Untied States" → "United States" → "US"
  - Configurable threshold (default 85%)

Manual Aliases:
  "england" → "GB"
  "scotland" → "GB"
  "wales" → "GB"
  "holland" → "NL"
  "czechia" → "CZ"
```

### LLM Classification System

**For building custom filtered datasets** (optional, not required for basic usage):

#### Classification Engine
```python
filter_companies_llm(df, provider="openai", model="gpt-4o-mini", ...)
```

**Process**:
1. Load configuration with sector definitions
2. Check cache for previously classified companies
3. Batch process unclassified companies (~100 at a time)
4. LLM analyzes each company:
   - Relevance to metals value chain?
   - Category: supply/demand/neither
   - Metal intensity: high/medium/low
   - Key activities extraction
5. Cache results (prevents re-classification)
6. Filter DataFrame by confidence threshold

#### Sector Definitions

**Supply Side (Metal Producers)**:
- Mining & Extraction: Underground/open-pit, exploration, development
- Recycling: Scrap metal, e-waste, circular economy

**Demand Side (Metal Consumers)**:
- Automotive: OEMs, Tier 1/2 suppliers, EV manufacturers
- Manufacturing: Heavy industry, machinery, equipment
- Construction: Steel structures, infrastructure
- Electronics: Semiconductors, PCBs, consumer electronics
- Appliances: White goods, HVAC, industrial equipment

#### Cost Optimization
```python
# Strategy 1: LLM-only (most accurate, expensive)
filter_companies(df, strategy="llm")
# → 95%+ precision, ~3 companies/sec, $0.23 per 1000 companies

# Strategy 2: Keyword-only (fast, less accurate)
filter_companies(df, strategy="keyword")
# → 70-80% precision, ~10,000/sec, free

# Strategy 3: Hybrid (recommended)
filter_companies(df, strategy="hybrid")
# → Keywords pre-filter (90% reduction)
# → LLM refines ambiguous cases
# → 80-90% cost reduction, 85-90% precision
```

---

## Data Sources

### Multi-Source Integration

#### GLEIF (Priority 1)
- **Source**: Global Legal Entity Identifier Foundation
- **Coverage**: 2.5M+ legal entities with LEI codes
- **Features**: Official regulatory data, parent/child relationships
- **API**: REST with pagination, 60 req/min rate limit
- **Processing**: 30-60 minutes for full download

```python
from entityidentity.companies.companygleif import load_gleif_lei
df = load_gleif_lei(max_records=10000)
```

#### Wikidata (Priority 2)
- **Source**: Wikidata knowledge graph via SPARQL
- **Coverage**: ~100K companies with rich metadata
- **Features**: Founded dates, industries, relationships
- **Query**: Optimized SPARQL with country/status filters

```python
from entityidentity.companies.companywikidata import load_wikidata_companies
df = load_wikidata_companies(limit=10000, country_codes=["US", "GB"])
```

#### Stock Exchanges (Priority 3)
- **ASX**: ~2000 Australian listings
- **LSE**: ~3000 London listings
- **TSX**: ~3000 Toronto listings
- **Challenge**: Inconsistent ALL CAPS formatting (hence lower priority)

```python
from entityidentity.companies.companyexchanges import load_asx, load_lse, load_tsx
asx_df = load_asx()
lse_df = load_lse()
tsx_df = load_tsx()
```

### Consolidation & Deduplication

**Source Priority System** ensures stable identifiers:

```python
consolidate_companies(use_samples=False)

Process:
1. Load all sources in priority order (GLEIF → Wikidata → Exchanges)
2. Normalize to common schema (name, country, lei, wikidata_qid, aliases)
3. Deduplicate by LEI (if available)
4. Deduplicate by (name_norm, country) for non-LEI entities
5. Apply source priority to resolve conflicts

Result: Same identifier regardless of build order
```

**Why Priority Matters**:
```
Without priority:
  Load GLEIF first: "Apple Inc:US"
  Load ASX first:   "APPLE INC:US" ❌ Different identifier!

With priority:
  Any load order:   "Apple Inc:US" ✅ Stable identifier!
```

### Database Schema

#### Companies Table
```python
{
  'name': str,                    # Canonical company name
  'country': str,                 # ISO2 country code
  'lei': Optional[str],           # Legal Entity Identifier
  'wikidata_qid': Optional[str],  # Wikidata entity ID
  'ticker': Optional[str],        # Primary stock ticker
  'alias1-5': Optional[str],      # Alternative names
  'name_norm': str,               # Normalized for matching
  'address': Optional[str],       # Headquarters address
  'industry': Optional[str],      # Industry classification
  'founded': Optional[str],       # Founding year
  'dissolved': Optional[bool],    # Still active?
  'source': str,                  # gleif/wikidata/exchange
  'source_priority': int          # Deduplication priority
}
```

#### Metals Table
```python
{
  'name': str,                     # Common name
  'symbol': Optional[str],         # Chemical symbol
  'formula': Optional[str],        # Chemical formula
  'category_bucket': str,          # base/precious/rare_earth/specialty
  'cluster_id': Optional[str],     # Supply chain cluster
  'name_norm': str,                # Normalized name
  'alias1-10': Optional[str],      # Alternative names
  'atomic_number': Optional[int],  # For elements
  'density': Optional[float],      # Physical properties
  'melting_point': Optional[float]
}
```

---

## Performance & Benchmarks

### Query Latency

| Dataset Size | Load Time | Memory | Query Time | QPS |
|-------------|-----------|--------|------------|-----|
| 500 companies | 0.1s | 10MB | 20ms | 50 |
| 10K companies | 0.3s | 50MB | 50ms | 20 |
| 100K companies | 1.5s | 200MB | 80ms | 12 |
| 1M companies | 8s | 1GB | 100ms | 10 |

### Blocking Effectiveness

```
Original candidates: 100,000
→ Country filter:      5,000 (95% reduction)
→ Prefix filter:          50 (99.95% reduction)
→ Fuzzy scoring:          50 candidates only

Time breakdown:
- Blocking: <1ms
- Scoring: 5-10ms
- Total: <20ms (cached), <100ms (first query)
```

### Caching Impact

```
First query:          100ms (includes loading)
Subsequent queries:    50ms (from cache)
With warmed cache:     20ms (hot path)
```

### Batch Processing

```python
# Slow: Individual queries
for name in names:
    company_identifier(name)  # 100ms each

# Fast: Batch processing
companies_df = pd.DataFrame(names)
resolve_batch(companies_df)   # 5ms per company
```

### Optimization Strategies

#### 1. Horizontal Scaling
```python
from multiprocessing import Pool

def parallel_resolve(names, n_workers=4):
    with Pool(n_workers) as pool:
        return pool.map(company_identifier, names)
```

#### 2. Database Partitioning
```python
# Partition by country for large datasets
databases = {
    'US': load_companies('us_companies.parquet'),
    'EU': load_companies('eu_companies.parquet'),
    'APAC': load_companies('apac_companies.parquet'),
}
```

#### 3. Approximate Matching
```python
# Trade accuracy for speed
resolve_company(
    name,
    high_conf_threshold=85,    # Lower threshold
    k=3,                       # Fewer candidates
    max_candidates=1000        # Smaller blocking
)
```

---

## Advanced Usage

### Extract Companies from Text

```python
from entityidentity import extract_companies

text = """
BHP and Rio Tinto announced increased copper production from their
Chilean operations. The Melbourne-based miners reported strong demand
from EV manufacturers like Tesla.
"""

companies = extract_companies(text, country_hint="AU")
# [
#   {'name': 'BHP Group Limited', 'country': 'AU', 'confidence': 0.95, ...},
#   {'name': 'Rio Tinto', 'country': 'AU', 'confidence': 0.92, ...},
#   {'name': 'Tesla Inc', 'country': 'US', 'confidence': 0.88, ...}
# ]
```

**Features**:
- Regex patterns for company-like strings (capitalized sequences, known suffixes, tickers)
- Country inference from surrounding text ("based in Australia" → country hint = "AU")
- Confidence filtering (min_confidence threshold)

### Extract Metals from Text

```python
from entityidentity import extract_metals_from_text, extract_metal_pairs

text = """
Lithium carbonate and cobalt sulfate prices rose on battery demand.
The copper-nickel alloy showed excellent corrosion resistance.
"""

# Extract individual metals
metals = extract_metals_from_text(text, cluster_hint="battery")
# [
#   {'name': 'Lithium carbonate', 'formula': 'Li2CO3', ...},
#   {'name': 'Cobalt', 'symbol': 'Co', ...},
#   {'name': 'Copper', 'symbol': 'Cu', ...},
#   {'name': 'Nickel', 'symbol': 'Ni', ...}
# ]

# Extract metal pairs/alloys
pairs = extract_metal_pairs(text)
# [('copper', 'nickel')]
```

### Use Custom Company Data

```python
import pandas as pd
from entityidentity import match_company

# Load your own dataset
custom_df = pd.read_parquet("my_companies.parquet")

# Must have columns: name, country, name_norm
# Optional: lei, wikidata_qid, ticker, alias1-5

# Use with API
match = match_company("Company Name", data_path="my_companies.parquet")
```

### Build Custom Filtered Dataset

```bash
# Sample data (quick, ~50KB)
python scripts/companies/update_companies_db.py --use-samples

# Full data (~2-3GB download, 30-60 min)
python scripts/companies/update_companies_db.py

# With LLM filtering for metals/mining (hybrid strategy)
bash scripts/companies/build_filtered_dataset.sh
```

### Integration Patterns

#### 1. Data Pipeline Enrichment
```python
def enrich_trade_data(df):
    """Add canonical IDs to trade data"""
    df['exporter_id'] = df.apply(
        lambda row: company_identifier(row['exporter_name'], row['export_country']),
        axis=1
    )
    df['importer_id'] = df.apply(
        lambda row: company_identifier(row['importer_name'], row['import_country']),
        axis=1
    )
    return df
```

#### 2. Real-time API
```python
from flask import Flask, jsonify, request
from entityidentity import company_identifier

app = Flask(__name__)

@app.route('/resolve/company')
def resolve_company_endpoint():
    name = request.args.get('name')
    country = request.args.get('country')
    result = company_identifier(name, country)
    return jsonify({'id': result})
```

#### 3. Streaming Processing
```python
import json
from entityidentity import company_identifier

def process_stream(stream):
    for line in stream:
        doc = json.loads(line)
        doc['company_id'] = company_identifier(
            doc.get('company_name'),
            doc.get('country')
        )
        yield json.dumps(doc)
```

---

## Development

### Quick Start

```bash
# Install in development mode
git clone https://github.com/microprediction/entityidentity
cd entityidentity
pip install -e .

# Build sample database
python scripts/companies/update_companies_db.py --use-samples

# Run tests
pytest
pytest --cov=entityidentity --cov-report=term-missing
```

### Testing

```bash
# Standard run (skips tests requiring data)
pytest

# With coverage
pytest --cov=entityidentity --cov-report=term-missing

# Skip integration tests
pytest -m "not integration"

# Enable live API tests
ENTITYIDENTITY_TEST_LIVE=1 pytest
```

**Test Coverage**: 131 tests across 11 files (1,679 lines)
- `test_api.py`: Integration tests (28 tests)
- `companies/`: Company resolution tests (65 tests)
- `test_metals.py`: Metal resolution tests (33 tests)
- `test_utils.py`: Utility tests (6 tests)

### Architecture Details

See [CLAUDE.md](CLAUDE.md) for:
- Complete function signatures
- Data loading utilities
- Normalization layers
- Caching architecture
- Known issues & TODOs

### Maintenance

See [MAINTENANCE.md](MAINTENANCE.md) for:
- Database rebuild procedures
- Data update workflows
- Classification cache management
- Release processes

---

## Support

- **Documentation**: You're reading it! Also see [CLAUDE.md](CLAUDE.md) for development details
- **Issues**: Report bugs on [GitHub Issues](https://github.com/microprediction/entityidentity/issues)
- **License**: MIT
- **Author**: Peter Cotton

---

## Appendix: Company Identifier Format

### Format Specification

All company identifiers follow: `{canonical_name}:{country_code}`

**Examples**:
- `Apple Inc:US`
- `BHP Group Limited:AU`
- `Anglo American plc:GB`

### Country Codes

We use **ISO 3166-1 alpha-2** standard (2-letter codes):

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

### Name Canonicalization

To ensure consistent identifiers regardless of load order or source formatting:

**Process**:
1. Remove commas before legal suffixes: `"Tesla, Inc."` → `"Tesla Inc."`
2. Remove periods from legal suffixes: `"Apple Inc."` → `"Apple Inc"`
3. Normalize unicode to ASCII: `"Société Générale"` → `"Societe Generale"`
4. Keep essential characters: Letters, numbers, spaces, hyphens, ampersands
5. Collapse multiple spaces: `"BHP  Group"` → `"BHP Group"`

**Implementation**: `canonicalize_company_name()` in [entityidentity/companies/companynormalize.py](entityidentity/companies/companynormalize.py)

### Stability Guarantee

The **source priority system** ensures identifiers never change:

**Priority (highest to lowest)**:
1. **GLEIF** (Priority 1) - Official regulatory data
2. **Wikidata** (Priority 2) - Well-curated crowdsourced
3. **Stock Exchanges** (Priority 3) - Often inconsistent formatting

**Result**: Same identifier regardless of database build order or date.
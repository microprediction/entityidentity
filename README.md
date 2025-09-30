# EntityIdentity

Entity resolution and identity matching for companies.

Fast, in-memory company name resolution using fuzzy matching and smart normalization. No server required.

## Installation

```bash
pip install entityidentity
```

## Quick Start

```python
from entityidentity import resolve_company, match_company

# Simple matching - returns best match or None
match = match_company("Apple Inc", country="US")
if match:
    print(f"Matched: {match['name']}")
    print(f"Country: {match['country']}")
    print(f"LEI: {match.get('lei', 'N/A')}")

# Full resolution with details
result = resolve_company("BHP Group", country="AU")
print(result['final'])      # Best match
print(result['decision'])   # How it was matched
print(result['matches'])    # All top matches with scores
```

## Features

- **Fast in-memory lookups**: <100ms for most queries
- **Multiple data sources**: GLEIF LEI, Wikidata, stock exchanges
- **Smart normalization**: Handles legal suffixes, punctuation, unicode
- **Fuzzy matching**: RapidFuzz scoring with intelligent blocking
- **No dependencies**: Works out of the box

## Basic Usage

### Normalize Company Names

```python
from entityidentity import normalize_name

# Normalize for matching
normalized = normalize_name("Apple Inc.")
# Returns: "apple"

normalized = normalize_name("BHP Group Ltd")
# Returns: "bhp group"
```

### Match Company Names

```python
from entityidentity import match_company

# Find best match
match = match_company("Microsoft Corporation", country="US")
if match:
    print(f"Matched to: {match['name']}")
    print(f"Confidence: {match['score']}")
```

### Resolve with Details

```python
from entityidentity import resolve_company

# Get full resolution details
result = resolve_company("Tesla", country="US")

# Access matched company
company = result['final']
print(f"Name: {company['name']}")
print(f"Country: {company['country']}")

# See decision type
print(f"Decision: {result['decision']}")
# Examples: 'auto_high_conf', 'llm_tiebreak', 'low_confidence'

# Review all matches
for match in result['matches']:
    print(f"  {match['name']} - Score: {match['score']}")
```

## Data Sources

The package includes pre-built company data from:

- **GLEIF LEI**: Global Legal Entity Identifier database
- **Wikidata**: Rich company metadata and aliases
- **Stock Exchanges**: ASX, LSE, TSX listings

Sample data is included in the package for immediate use.

## API Reference

### `match_company(name, country=None)`

Simple interface to find the best matching company.

**Parameters**:
- `name` (str): Company name to match
- `country` (str, optional): ISO 2-letter country code

**Returns**: Dictionary with matched company data, or `None` if no good match found.

### `resolve_company(name, country=None, **kwargs)`

Full resolution with all details and match scores.

**Parameters**:
- `name` (str): Company name to resolve
- `country` (str, optional): ISO 2-letter country code
- Additional kwargs for advanced options

**Returns**: Dictionary with:
- `final`: Best matched company
- `decision`: Decision type ('auto_high_conf', 'llm_tiebreak', etc.)
- `matches`: List of all potential matches with scores

### `normalize_name(name)`

Normalize a company name for matching.

**Parameters**:
- `name` (str): Company name to normalize

**Returns**: Normalized string (lowercase, no punctuation, legal suffixes removed)

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

- **Documentation**: See [MAINTENANCE.md](MAINTENANCE.md) for development details
- **Issues**: Report bugs on GitHub
- **License**: MIT

## Author

Peter Cotton

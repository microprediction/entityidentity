# Company Resolution API Reference

This document describes the public API for company entity resolution in EntityIdentity.

## Quick Start

```python
from entityidentity import company_identifier, match_company

# Get canonical identifier for a company
company_id = company_identifier("Apple")
# Returns: 'Apple Inc:US'

# Get full company information
company = match_company("BHP", country="AU")
# Returns: {'name': 'BHP Group Limited', 'country': 'AU', 'lei': '...', ...}
```

## Architecture Overview

EntityIdentity uses a three-layer architecture for company resolution:

```
┌─────────────────────────────────────────────────────┐
│  PUBLIC API LAYER (companyapi.py)                   │
│  - Clean, user-friendly functions                   │
│  - Exported via top-level entityidentity module     │
│  - USE THIS FOR ALL NEW CODE                        │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  IMPLEMENTATION LAYER (companyresolver.py)          │
│  - Internal orchestration logic                     │
│  - Coordinates blocking, scoring, decisions         │
│  - DO NOT IMPORT DIRECTLY                           │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  HELPER MODULES                                      │
│  - companynormalize.py: Name normalization          │
│  - companyblocking.py: Candidate filtering          │
│  - companyscoring.py: Fuzzy matching                │
│  - Internal use only                                 │
└─────────────────────────────────────────────────────┘
```

### Legacy Module (Deprecated)

- **companyidentity.py**: Deprecated compatibility layer. Still works but will be removed in future versions. Migrate to `companyapi.py`.

## Public API Functions

All functions are available from the top-level module:

```python
from entityidentity import (
    company_identifier,       # Primary API - get canonical ID
    match_company,            # Get full company details
    resolve_company,          # Get resolution with all candidates
    normalize_company_name,   # Normalize names for matching
    canonicalize_company_name,# Canonicalize names for display
    extract_companies,        # Extract companies from text
    get_company_id,           # Format company as ID string
)
```

### Naming Convention

The package uses consistent naming for normalization functions:

- **`normalize_company_name()`**: Aggressive normalization for fuzzy matching (lowercase, no punctuation)
- **`canonicalize_company_name()`**: Gentle normalization for display/identifiers (preserves case)

**Deprecated**: The shorter `normalize_name()` alias is deprecated and will be removed in v1.0.0.

---

### `company_identifier(name, country=None)`

**Primary API for company resolution.** Get a stable, canonical identifier for a company.

**Arguments:**
- `name` (str): Company name in any format (e.g., "MSFT", "Microsoft Corp", "Microsoft")
- `country` (str, optional): Two-letter country code hint (e.g., "US", "GB") - improves accuracy

**Returns:**
- `str | None`: Canonical identifier in format `"CompanyName:CountryCode"`, or `None` if no confident match

**Examples:**
```python
>>> company_identifier("Apple")
'Apple Inc:US'

>>> company_identifier("BHP", country="AU")
'BHP Group Limited:AU'

>>> company_identifier("Anglo American")
'Anglo American plc:GB'

>>> company_identifier("asdfqwerzxcv")  # No match
None
```

**Use Cases:**
- Entity deduplication in datasets
- Creating stable join keys across data sources
- Canonical company references in databases

**Performance:** <100ms per query (in-memory database)

---

### `match_company(name, country=None)`

Find the best matching company with full details.

**Arguments:**
- `name` (str): Company name to match
- `country` (str, optional): Country code hint

**Returns:**
- `dict | None`: Company record with fields:
  - `name` (str): Canonical company name
  - `country` (str): Two-letter country code
  - `lei` (str | None): Legal Entity Identifier (if available)
  - `wikidata_qid` (str | None): Wikidata QID (if available)
  - `aliases` (list): Alternative names for this company
  - Or `None` if no confident match

**Examples:**
```python
>>> match_company("Microsoft")
{
    'name': 'Microsoft Corporation',
    'country': 'US',
    'lei': 'INR2EJN1ERAN0W5ZP974',
    'wikidata_qid': 'Q2283',
    'aliases': ['MSFT', 'Microsoft Corp', ...]
}

>>> match_company("Acme Fake Company Inc")
None
```

**Use Cases:**
- Looking up company metadata (LEI, Wikidata ID)
- Enriching datasets with canonical company information
- Validating company names

---

### `resolve_company(name, country=None)`

Resolve company with full diagnostic information including all candidates and scores.

**Arguments:**
- `name` (str): Company name to resolve
- `country` (str, optional): Country code hint

**Returns:**
- `dict`: Resolution result with fields:
  - `final` (dict | None): Best matching company (same as `match_company`)
  - `decision` (str): How the match was decided:
    - `"auto_high_conf"`: High confidence, auto-matched
    - `"no_match"`: No confident match found
    - `"needs_hint_or_llm"`: Ambiguous, needs country hint or manual review
  - `matches` (list[dict]): All candidate matches with scores
  - `query` (dict): Normalized query information

**Examples:**
```python
>>> resolve_company("Apple")
{
    'final': {'name': 'Apple Inc', 'country': 'US', ...},
    'decision': 'auto_high_conf',
    'matches': [
        {'name': 'Apple Inc', 'score': 95.3, 'country': 'US', ...},
        {'name': 'Apple Bank', 'score': 72.1, 'country': 'US', ...}
    ],
    'query': {'name': 'Apple', 'name_norm': 'apple', 'country': None}
}

>>> result = resolve_company("Rio Tinto")
>>> result['decision']
'needs_hint_or_llm'  # Ambiguous - Rio Tinto has entities in GB and AU

>>> result = resolve_company("Rio Tinto", country="GB")
>>> result['decision']
'auto_high_conf'  # Clear match with country hint
```

**Use Cases:**
- Debugging why a match succeeded/failed
- Reviewing match confidence scores
- Handling ambiguous matches programmatically
- Building interactive resolution UIs

---

### `extract_companies(text, country_hint=None, min_confidence=0.75)`

Extract company mentions from unstructured text and resolve to canonical entities.

**Arguments:**
- `text` (str): Text to extract companies from
- `country_hint` (str, optional): Country code to prioritize for ambiguous matches
- `min_confidence` (float): Minimum match score (0.0-1.0, default 0.75)

**Returns:**
- `list[dict]`: Extracted companies with fields:
  - `mention` (str): Original text mention
  - `name` (str): Canonical company name
  - `country` (str): Country code
  - `lei` (str | None): LEI if available
  - `score` (float): Match confidence (0.0-1.0)
  - `context` (str): Surrounding text

**Examples:**
```python
>>> text = "Apple and Microsoft lead tech. BHP operates in Australia."
>>> companies = extract_companies(text)
>>> for co in companies:
...     print(f"{co['mention']} -> {co['name']} ({co['country']})")
Apple -> Apple Inc (US)
Microsoft -> Microsoft Corporation (US)
BHP -> BHP Group Limited (AU)

>>> text = "Rio Tinto announced new mines in Western Australia."
>>> extract_companies(text, country_hint="AU")
[{'mention': 'Rio Tinto', 'name': 'Rio Tinto Limited', 'country': 'AU', ...}]
```

**Use Cases:**
- Named entity recognition (NER) for companies
- Building knowledge graphs from documents
- Monitoring news/social media for company mentions
- Compliance screening

---

### `normalize_company_name(name)`

Normalize company name for fuzzy matching (aggressive normalization).

**Arguments:**
- `name` (str): Company name to normalize

**Returns:**
- `str`: Normalized name (lowercase, no punctuation, legal suffixes removed)

**Examples:**
```python
>>> normalize_company_name("Apple Inc.")
'apple'

>>> normalize_company_name("AT&T Corporation")
'at&t'

>>> normalize_company_name("BHP Billiton Ltd")
'bhp billiton'
```

**Use Cases:**
- Pre-processing for fuzzy matching
- Building search indexes
- Deduplication workflows

---

### `canonicalize_company_name(name)`

Canonicalize company name for display and identifiers (preserves readability).

**Arguments:**
- `name` (str): Company name to canonicalize

**Returns:**
- `str`: Canonicalized name (case preserved, safe for identifiers)

**Examples:**
```python
>>> canonicalize_company_name("Apple, Inc.")
'Apple Inc'

>>> canonicalize_company_name("AT&T Corporation")
'AT&T Corporation'

>>> canonicalize_company_name("Société Générale")
'Societe Generale'
```

**Use Cases:**
- Creating human-readable identifiers
- Display names in UI
- Database keys that need to be readable

---

### `normalize_name(name)` *(DEPRECATED)*

**⚠️ DEPRECATED**: Use `normalize_company_name()` instead. This function will be removed in v1.0.0.

Normalize company name for matching (removes legal suffixes, punctuation, etc.).

**Migration:**
```python
# Old (deprecated)
from entityidentity import normalize_name
result = normalize_name("Apple Inc.")

# New (recommended)
from entityidentity import normalize_company_name
result = normalize_company_name("Apple Inc.")
```

---

### `get_company_id(company, safe=False)`

Format a company record as a canonical identifier string.

**Arguments:**
- `company` (dict): Company record with `name` and `country` fields
- `safe` (bool): If True, return filesystem/database-safe ID (replaces special chars with `_`)

**Returns:**
- `str`: Identifier in format `"CompanyName:CountryCode"` (or `CompanyName_CountryCode` if safe=True)

**Examples:**
```python
>>> company = {'name': 'Apple Inc', 'country': 'US'}
>>> get_company_id(company)
'Apple Inc:US'

>>> company = {'name': 'AT&T Corporation', 'country': 'US'}
>>> get_company_id(company)
'AT&T Corporation:US'

>>> get_company_id(company, safe=True)
'AT_T_Corporation_US'
```

**Use Cases:**
- Creating database table names or file names from companies
- URL-safe company identifiers
- SQL-safe column names

---

## Advanced Usage

### Working with Match Scores

The resolution system uses fuzzy matching scores (0-100):

- **88+**: High confidence - auto-matched
- **76-88**: Medium confidence - may need country hint
- **<76**: Low confidence - not matched

```python
result = resolve_company("Rio")
top_match = result['matches'][0]

if top_match['score'] >= 88:
    print("High confidence match")
elif top_match['score'] >= 76:
    print("Needs country hint or review")
else:
    print("No confident match")
```

### Handling Ambiguous Matches

Some company names are ambiguous without country context:

```python
# Ambiguous - could be GB or AU
result = resolve_company("Rio Tinto")
if result['decision'] == 'needs_hint_or_llm':
    # Provide country hint
    result_gb = resolve_company("Rio Tinto", country="GB")
    result_au = resolve_company("Rio Tinto", country="AU")
```

### Batch Resolution

For processing many companies, load the database once:

```python
from entityidentity import match_company

companies_to_resolve = ["Apple", "Microsoft", "BHP"]
results = [match_company(name) for name in companies_to_resolve]
```

The database is loaded once per process and cached in memory (~10-50MB).

### Custom Data Sources

Advanced users can load companies from custom data sources:

```python
from entityidentity.companies.companyresolver import resolve_company

# Use custom database
result = resolve_company(
    "Apple",
    data_path="/path/to/custom_companies.parquet"
)
```

## Migration Guide

### From `companyidentity.py` (deprecated)

**Old:**
```python
from entityidentity.companies.companyidentity import (
    resolve_company,
    match_company,
    normalize_name,
)
```

**New:**
```python
from entityidentity import (
    resolve_company,
    match_company,
    normalize_name,
)
```

### From `companyresolver.py` (internal)

**Old:**
```python
from entityidentity.companies.companyresolver import resolve_company
```

**New:**
```python
from entityidentity import resolve_company
```

## Error Handling

```python
from entityidentity import match_company

try:
    company = match_company("Apple")
    if company is None:
        print("No confident match found")
    else:
        print(f"Matched: {company['name']}")
except FileNotFoundError as e:
    print("Companies database not found. Run build script to generate it.")
except Exception as e:
    print(f"Error during resolution: {e}")
```

## Performance Characteristics

- **Query latency**: <100ms for most lookups
- **Database size**: ~10-50MB in memory (Parquet format)
- **Startup time**: 1-2 seconds to load database (cached for session)
- **Matching accuracy**: >95% for exact names, >85% for variations

## Database Schema

The companies database contains:

| Field | Type | Coverage | Description |
|-------|------|----------|-------------|
| `name` | str | 100% | Canonical company name |
| `country` | str | 100% | Two-letter country code |
| `lei` | str | ~23% | Legal Entity Identifier |
| `wikidata_qid` | str | ~40% | Wikidata QID |
| `source` | str | 100% | Data source (GLEIF, Wikidata, Exchanges) |
| `aliases` | list | ~60% | Alternative names |

## Related Documentation

- [Filtering Guide](FILTERING.md) - Filter companies by sector (mining/energy)
- [CLAUDE.md](../../CLAUDE.md) - Development setup and architecture
- [README.md](../../README.md) - Package overview

## Support

For issues or questions:
- GitHub Issues: https://github.com/microprediction/entityidentity/issues
- See examples in `examples/` directory
- Run tests: `pytest tests/companies/`

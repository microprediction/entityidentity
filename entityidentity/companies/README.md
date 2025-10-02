# Company Resolution Module

Internal implementation for company entity resolution and filtering. For usage documentation, see the main [repository README](../../README.md) and [project CLAUDE.md](../../CLAUDE.md).

## Quick Start

```python
from entityidentity import company_identifier, match_company, extract_companies

# Get canonical identifier
company_id = company_identifier("Apple")  # Returns: 'Apple Inc:US'

# Get full company details
company = match_company("BHP", country="AU")
# Returns: {'name': 'BHP Group Limited', 'country': 'AU', 'lei': '...', ...}

# Extract companies from text
text = "Apple and Microsoft lead tech. BHP operates in Australia."
companies = extract_companies(text)
```

## Module Structure

### Public API (`companyapi.py`)
**Use this for all external code.** Clean, user-facing functions exported via top-level `entityidentity` module.

Core functions:
- `company_identifier(name, country=None)` - Get canonical ID for a company
- `match_company(name, country=None)` - Find best matching company with details
- `resolve_company(name, country=None)` - Full resolution with all candidates and scores
- `extract_companies(text, ...)` - Extract company mentions from text
- `normalize_company_name(name)` - Normalize names for matching
- `canonicalize_company_name(name)` - Canonicalize names for display

### Implementation Layer (Internal)
**Do not import directly from these modules:**
- `companyresolver.py` - Resolution orchestration
- `companynormalize.py` - Name normalization
- `companyblocking.py` - Candidate filtering
- `companyscoring.py` - Fuzzy matching
- `companyextractor.py` - Text extraction

### Data Loading
- `companygleif.py` - GLEIF LEI data loader
- `companywikidata.py` - Wikidata loader
- `companyexchanges.py` - Stock exchange loaders

### Filtering (`companyfilter.py`)
Filter companies to specific sectors (e.g., mining/energy):

```python
from entityidentity.companies.companyfilter import filter_companies
import pandas as pd

df = pd.read_parquet('companies.parquet')

# Hybrid mode (recommended) - fast + accurate
filtered = filter_companies(df, strategy='hybrid', provider='openai')

# Keyword-only - fastest, no API costs
filtered = filter_companies(df, strategy='keyword')

# LLM-only - most accurate
filtered = filter_companies(df, strategy='llm', provider='openai')
```

**Strategies:**
- `keyword` - Pattern matching (~10K companies/sec, free)
- `llm` - AI classification (~3 companies/sec, API costs)
- `hybrid` - Keyword pre-filter + LLM refinement (recommended)

### Deprecated Modules

⚠️ **`companyidentity.py`** - Legacy compatibility layer, will be removed in v1.0.0. Use `companyapi.py` instead.

## Architecture

```
┌─────────────────────────────────────┐
│  Public API (companyapi.py)         │  ← Import from entityidentity
│  User-facing functions               │     from entityidentity import ...
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  Resolver (companyresolver.py)      │  ← Internal use only
│  Orchestration logic                 │     Do not import directly
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  Helper Modules                      │  ← Internal use only
│  - companynormalize.py               │
│  - companyblocking.py                │
│  - companyscoring.py                 │
└─────────────────────────────────────┘
```

## Database Building

Build the companies database:

```bash
# Use samples for testing (fast)
python scripts/companies/build_database_cli.py --use-samples

# Build full database from live sources
python scripts/companies/build_database_cli.py

# Filter to mining/energy companies
python -m entityidentity.companies.companyfilter \
  --input tables/companies/companies.parquet \
  --output tables/companies/companies_metals.parquet \
  --strategy hybrid \
  --provider openai
```

## Configuration

### LLM Filtering
Configure LLM prompts and sector definitions in `company_classifier_config.yaml`.

### Environment Variables
- `OPENAI_API_KEY` - For OpenAI LLM filtering
- `ANTHROPIC_API_KEY` - For Anthropic LLM filtering

## Performance

- **Query latency**: <100ms per lookup
- **Database size**: ~10-50MB in memory
- **Startup time**: 1-2 seconds to load database
- **Matching accuracy**: >95% for exact names, >85% for variations

## Data Sources

Companies are loaded from:
1. **GLEIF** (Legal Entity Identifier) - Official regulatory data
2. **Wikidata** - Crowdsourced metadata and aliases
3. **Stock Exchanges** - ASX, LSE, TSX listings

Source priority: GLEIF > Wikidata > Exchanges (for stable identifiers)

## Development

```bash
# Run tests
pytest tests/companies/ -v

# Build database with samples
python scripts/companies/build_database_cli.py --use-samples

# Test resolution
python -c "from entityidentity import company_identifier; print(company_identifier('Apple'))"
```

## Migration Notes

### From companyidentity.py (deprecated)
```python
# OLD (deprecated)
from entityidentity.companies.companyidentity import resolve_company

# NEW (recommended)
from entityidentity import resolve_company
```

### Normalization Functions
- Use `normalize_company_name()` instead of `normalize_name()`
- Use `canonicalize_company_name()` instead of `canonicalize_name()`

The shorter aliases are deprecated and will be removed in v1.0.0.

## See Also

- [Main README](../../README.md) - Package overview and installation
- [CLAUDE.md](../../CLAUDE.md) - Development guide and architecture
- [examples/](../../examples/) - Usage examples

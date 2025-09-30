# EntityIdentity

Entity resolution and identity matching for companies.

On-the-fly company name resolution using deterministic blocking, fuzzy scoring, and optional LLM tie-breaking. No server required.

## Features

- **In-memory resolution**: Fast lookups from consolidated Parquet files
- **Multiple data sources**: GLEIF LEI, Wikidata, stock exchanges (ASX, LSE, TSX, etc.)
- **Smart matching**: Deterministic blocking + RapidFuzz scoring
- **Optional LLM tie-breaking**: For ambiguous matches
- **Aggressive caching**: `functools.lru_cache` for performance

## Installation

```bash
pip install -e .
```

## Quick Start

### 1. Build the company database

```bash
# Quick test with sample data
python scripts/companies/update_companies_db.py --use-samples

# Full database from live sources (slow, ~2-3GB download)
python scripts/companies/update_companies_db.py
```

This creates:
- `tables/companies/companies.parquet` - Main database (compressed)
- `tables/companies/companies.csv` - First 500 rows for easy inspection
- `tables/companies/companies_info.txt` - Database statistics and metadata

### 2. Resolve company names

```python
from entityidentity import resolve_company, match_company

# Full resolution with details
result = resolve_company("BHP Group", country="AU")
print(result['final'])  # Best match
print(result['decision'])  # Decision type: auto_high_conf, llm_tiebreak, etc.
print(result['matches'])  # All top matches with scores

# Simple: just get best match or None
match = match_company("Apple Inc", country="US")
if match:
    print(f"Matched: {match['name']} (LEI: {match['lei']})")
```

## Architecture

```
entityidentity/
├── companies/              # Company resolution
│   ├── companyidentity.py  # Main resolver
│   ├── companygleif.py     # GLEIF LEI loader
│   ├── companywikidata.py  # Wikidata loader
│   └── companyexchanges.py # Exchange loaders
├── build_companies_db.py   # Consolidation script
└── COMPANIES.md            # Data source documentation

tables/
└── companies/
    └── companies.parquet   # Consolidated lookup database

scripts/
└── companies/
    └── update_companies_db.py  # CLI for building database

tests/
└── companies/              # Test suite
    ├── test_companyidentity.py
    └── test_loaders.py
```

## Data Sources

See [COMPANIES.md](entityidentity/COMPANIES.md) for details on all data sources.

**Tier 1 (High Quality)**
- GLEIF LEI Golden Copy (~2.5M entities, updated 3×/day)
- Wikidata (rich aliases and metadata)

**Tier 2 (Exchange Listings)**
- ASX (Australian Securities Exchange)
- LSE (London Stock Exchange)  
- TSX/TSXV (Toronto Stock Exchange)

**Tier 3 (Registries - planned)**
- UK Companies House
- SEC EDGAR
- SEDAR+ (Canada)

## Matching Strategy

1. **Normalize**: Lowercase, strip legal suffixes, remove punctuation
2. **Block candidates**: Country filter, first-token prefix matching
3. **Score**: RapidFuzz with boosts for country match, LEI presence
4. **Decide**:
   - Score ≥ 88 + gap ≥ 6 → auto-accept (high confidence)
   - Score 76-87 → optional LLM tie-break
   - Otherwise → return shortlist

## API

### `resolve_company(name, country=None, **kwargs)`

Full resolution with all details.

**Returns:**
```python
{
    "query": {"name": "...", "name_norm": "...", "country": "..."},
    "matches": [
        {
            "name": "Apple Inc.",
            "score": 95.0,
            "lei": "529900HNOAA1KXQJUQ27",
            "country": "US",
            "wikidata_qid": "Q312",
            "aliases": ["Apple Computer", "AAPL"],
            "explain": {"name_norm": "apple", "country_match": True, ...}
        },
        # ... more matches
    ],
    "final": {...},  # Best match if confident, else None
    "decision": "auto_high_conf"  # or "llm_tiebreak", "needs_hint_or_llm"
}
```

### `match_company(name, country=None)`

Simple interface: returns best match dict or None.

### `normalize_name(name)`

Normalize company name for matching.

```python
from entityidentity import normalize_name
normalize_name("Apple Inc.")  # "apple"
normalize_name("BHP Group Ltd")  # "bhp group"
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=entityidentity

# Run only integration tests
pytest tests/companies/test_loaders.py

# Test with live APIs (slow)
ENTITYIDENTITY_TEST_LIVE=1 pytest -v -m integration
```

## Performance

- **In-memory**: <100ms for most queries
- **With SQLite + FTS5**: Scales to millions of companies
- **Database size**: ~10-50MB compressed (Parquet)

## License

MIT License - see [LICENSE](LICENSE)

## Author

Peter Cotton

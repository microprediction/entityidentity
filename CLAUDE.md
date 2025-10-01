# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

EntityIdentity is a Python package for company and country entity resolution. It provides fast, in-memory resolution of messy company names (tickers, abbreviations, variations) to stable canonical identifiers using fuzzy matching and smart normalization.

## High-Level Architecture

### Core Resolution Pipeline

The package implements a multi-stage resolution pipeline for company matching:

1. **Data Loading & Consolidation**: Multiple data sources (GLEIF, Wikidata, stock exchanges) are loaded and deduplicated using a deterministic priority system (GLEIF > Wikidata > Exchanges) to ensure stable identifiers
2. **Normalization Layer**: Company names undergo multi-step normalization (legal suffix removal, unicode conversion, canonicalization) with caching via `@lru_cache`
3. **Blocking Strategy**: Candidates are filtered by country code and first-token prefix, reducing search space by 99%+
4. **Fuzzy Matching**: RapidFuzz library performs optimized string matching with configurable thresholds
5. **Decision Engine**: Scoring system determines confidence levels (auto_high_conf, needs_hint_or_llm, etc.)

### Country Resolution Pipeline

Three-stage fallback system with fuzzy matching:
1. **country_converter** library for primary resolution
2. **pycountry** library as fallback
3. **Custom fuzzy matching** for typos and colloquialisms

### LLM Classification System

Optional LLM-based filtering for metals/mining industry companies:
- Configurable via YAML for sector definitions and prompts
- Persistent caching in `.cache/companies/classifications.json`
- Supports both OpenAI and Anthropic APIs
- Classification categories: supply (mining/recycling), demand (manufacturing/electronics), both, or irrelevant

## Common Development Commands

### Installation & Setup
```bash
# Install package in development mode
pip install -e .

# Install with development dependencies
pip install -r requirements-dev.txt

# Build sample database (required for first use)
python scripts/companies/update_companies_db.py --use-samples
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=entityidentity

# Run specific test file
pytest tests/companies/test_companyidentity.py -v

# Run with live API calls (GLEIF, Wikidata)
ENTITYIDENTITY_TEST_LIVE=1 pytest -v
```

### Database Building
```bash
# Build sample database (~50KB, uses included CSV samples)
python scripts/companies/update_companies_db.py --use-samples

# Build full database (~2-3GB download, 30-60 min)
python scripts/companies/update_companies_db.py

# Build filtered dataset with LLM classification
bash scripts/companies/build_filtered_dataset.sh
```

### LLM Classification
```bash
# Set API key
export OPENAI_API_KEY=your_key_here

# Run LLM filter on database
bash scripts/companies/filter_mining_energy_llm.sh \
  --input tables/companies/companies_full.parquet \
  --output tables/companies/companies_metals.parquet \
  --provider openai \
  --model gpt-4o-mini
```

## Key Implementation Details

### Data Priority System (entityidentity/companies/companyidentity.py)

The package uses deterministic source priority to ensure stable identifiers:
- GLEIF (priority 1): Official legal names from regulatory filings
- Wikidata (priority 2): Crowdsourced but well-curated
- Stock Exchanges (priority 3): Often inconsistent formatting

This prevents identifier drift when the same company appears in multiple sources.

### Normalization Pipeline (entityidentity/companies/companynormalize.py)

Two-level normalization for matching:
1. `canonicalize_name()`: Preserves readability (e.g., "Apple Inc" not "APPLE INC")
2. `normalize_name()`: Aggressive normalization for matching (lowercase, remove suffixes)

### Blocking Strategy (entityidentity/companies/companyblocking.py)

Efficient candidate filtering using:
- Country code matching (if provided)
- First token prefix matching
- Reduces millions of companies to ~100 candidates for scoring

### Caching Architecture

Multiple caching layers:
- `@lru_cache` on normalization functions
- LLM classifications cached to `.cache/companies/classifications.json`
- Database loaded once per session into memory

## File Organization

### Core Package Structure
```
entityidentity/
├── __init__.py                      # Main API exports
├── companies/
│   ├── companyidentity.py          # Main resolver and deduplication logic
│   ├── companynormalize.py         # Name normalization functions
│   ├── companyblocking.py          # Candidate filtering
│   ├── companyscoring.py           # Fuzzy matching and scoring
│   ├── companyresolver.py          # Decision engine
│   ├── companygleif.py             # GLEIF data loader
│   ├── companywikidata.py          # Wikidata loader
│   ├── companyexchanges.py         # Stock exchange loaders
│   ├── companyfilter.py            # LLM classification
│   └── company_classifier_config.yaml  # LLM configuration
└── countries/
    ├── fuzzycountry.py              # Country resolution with fuzzy matching
    └── countryapi.py                # Country API wrapper
```

### Data Files
```
tables/companies/
├── companies.parquet                # Main database (git ignored, generated)
├── companies.csv                    # Sample preview (git tracked)
├── companies_info.txt               # Database statistics (git tracked)
└── samples/                         # Sample data for testing
```

### Scripts
```
scripts/companies/
├── update_companies_db.py           # Main database builder
├── build_filtered_dataset.sh        # Complete pipeline with LLM filtering
├── filter_mining_energy_llm.sh      # LLM classification script
└── expand_with_exchanges.py         # Add exchange data to existing DB
```

## Environment Variables

Required for LLM classification:
- `OPENAI_API_KEY`: For OpenAI API access
- `ANTHROPIC_API_KEY`: For Anthropic API access (optional)

Optional:
- `ENTITYIDENTITY_TEST_LIVE=1`: Enable live API tests

## Performance Characteristics

- **Query latency**: <100ms for most lookups
- **Database size**: ~10-50MB compressed (Parquet), ~50-200MB in memory
- **Startup time**: 1-2 seconds to load database
- **LLM classification**: ~3 companies/second with GPT-4o-mini
- **Matching accuracy**: >95% for exact names, >85% for variations

## Troubleshooting

### No companies data found
```bash
python scripts/companies/update_companies_db.py --use-samples
```

### LLM classification fails
```bash
# Check API key
echo $OPENAI_API_KEY

# Clear cache if corrupted
rm -rf .cache/companies/
```

### Tests fail with API errors
```bash
# Run without live API tests
pytest -m "not integration"
```
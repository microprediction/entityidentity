# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

EntityIdentity is a Python package for company and country entity resolution. See README.md for user documentation.

## Development Quick Reference

### Setup
```bash
pip install -e .                                      # Install in dev mode
python scripts/companies/build_database_cli.py --use-samples  # Build sample DB
```

### Testing
```bash
pytest                                                # Run all tests
pytest --cov=entityidentity                          # With coverage
ENTITYIDENTITY_TEST_LIVE=1 pytest -v                 # Include live API tests
```

## Architecture Notes for Development

### Key Implementation Concepts

1. **Deterministic Source Priority**: When merging data sources, GLEIF > Wikidata > Exchanges priority ensures stable identifiers regardless of load order

2. **Two-Level Normalization**:
   - `canonicalize_name()`: For display/identifiers (preserves case)
   - `normalize_name()`: For matching (aggressive lowercase)

3. **Blocking Strategy**: First-token prefix + country code filtering reduces candidate set by 99%+ before fuzzy matching

4. **Caching Layers**:
   - `@lru_cache` decorators on normalization functions
   - LLM classifications persist to `.cache/companies/classifications.json`
   - Company database loaded once per session

### Code Organization

```
entityidentity/
├── companies/           # Company resolution modules
│   ├── companyapi.py   # Public API (imports from companyresolver)
│   ├── companyresolver.py  # Core resolution logic
│   ├── companynormalize.py # Name normalization
│   ├── companyblocking.py  # Candidate filtering
│   ├── companyscoring.py   # Fuzzy matching
│   └── companyidentity.py  # Database building & deduplication
├── countries/          # Country resolution
└── metals/            # Metal resolution
```

### Common Development Tasks

#### Adding a New Data Source
1. Create loader in `entityidentity/companies/company{source}.py`
2. Add to `build_database_cli.py` with appropriate priority
3. Update deduplication logic in `companyidentity.py`

#### Modifying Resolution Logic
- Scoring thresholds: `companyresolver.py` (high_conf_threshold, high_conf_gap)
- Normalization rules: `companynormalize.py`
- Blocking strategy: `companyblocking.py`

#### Working with LLM Classification
```bash
export OPENAI_API_KEY=your_key
bash scripts/companies/filter_mining_energy_llm.sh \
  --input tables/companies/companies_full.parquet \
  --output tables/companies/companies_metals.parquet
```

### Performance Considerations

- Database stays in memory after first `load_companies()` call
- Blocking is critical - without it, matching would be O(n) for each query
- RapidFuzz C++ extensions provide 10-100x speedup over pure Python

### Testing Strategy

- Unit tests: Test individual functions (normalization, scoring)
- Integration tests: Test full resolution pipeline
- Live tests (ENTITYIDENTITY_TEST_LIVE=1): Test external API integrations

### Troubleshooting

#### No companies data found
```bash
python scripts/companies/build_database_cli.py --use-samples
```

#### Cache corruption
```bash
rm -rf .cache/companies/
```

#### Memory issues with large datasets
Consider using filtered datasets or increasing system memory. Full GLEIF database can use 2-3GB RAM.

## Environment Variables

- `OPENAI_API_KEY`: Required for LLM classification
- `ANTHROPIC_API_KEY`: Alternative LLM provider
- `ENTITYIDENTITY_TEST_LIVE`: Enable live API tests

## Files to Edit for Common Changes

- **Add new API function**: `entityidentity/companies/companyapi.py` and export in `__all__`
- **Change matching algorithm**: `entityidentity/companies/companyscoring.py`
- **Modify data sources**: `scripts/companies/build_database_cli.py`
- **Adjust confidence thresholds**: `entityidentity/companies/companyresolver.py`
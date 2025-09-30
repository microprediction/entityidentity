# Company Data Tables

This directory contains the consolidated company lookup database.

## Files

- `companies.parquet` - Main company lookup database (consolidated from all sources)
- `companies.csv` - CSV preview of first 500 rows (auto-generated for easy inspection)
- `companies_info.txt` - Database statistics and metadata (auto-generated)

## Building/Updating the Database

To create or update the companies database:

```bash
# Quick test with sample data (recommended first time)
python scripts/companies/update_companies_db.py --use-samples

# Full database from live sources (slow, requires internet)
python scripts/companies/update_companies_db.py

# Incremental update (add new records, keep existing)
python scripts/companies/update_companies_db.py --incremental

# With caching to avoid re-downloading
python scripts/companies/update_companies_db.py --cache-dir .cache/companies
```

## Data Structure

The parquet file contains the following columns:

- `name` - Official company name
- `name_norm` - Normalized name for matching
- `country` - ISO 3166-1 alpha-2 country code
- `lei` - Legal Entity Identifier (if available)
- `wikidata_qid` - Wikidata Q-ID (if available)
- `aliases` - List of alternate names
- `address` - Full address (if available)
- `city` - City (if available)
- `postal_code` - Postal/ZIP code (if available)
- `source` - Data source (GLEIF, Wikidata, ASX, LSE, TSX, etc.)

## Data Sources

1. **GLEIF LEI** - Global Legal Entity Identifiers
2. **Wikidata** - Rich metadata and aliases
3. **ASX** - Australian Securities Exchange
4. **LSE** - London Stock Exchange
5. **TSX/TSXV** - Toronto Stock Exchange

See `entityidentity/COMPANIES.md` for more details on data sources.


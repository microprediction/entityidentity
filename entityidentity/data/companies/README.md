# Sample Companies Dataset

This directory contains a **sample dataset** of ~500 companies for demonstration and testing purposes.

## Purpose

This sample data is:
- ✅ **Distributed with the Python package** (included in PyPI releases)
- ✅ **Checked into git** (small enough for version control)
- ✅ **Always available** after `pip install entityidentity`
- ✅ **Fast to load** (<100ms)

**What it's good for:**
- Quick demos and prototyping
- Running tests without building full database
- Learning the API
- CI/CD testing

**What it's NOT good for:**
- Production use (limited coverage)
- Comprehensive company resolution (only ~500 companies)
- Real-world applications requiring high recall

## Full Database

For comprehensive company resolution, build the full database:

```bash
# Build full database (100K+ companies, takes 30-60 minutes)
python scripts/companies/update_companies_db.py

# This creates: tables/companies/companies.parquet (~10-50MB)
```

The full database includes:
- 100,000+ companies from GLEIF, Wikidata, and stock exchanges
- Comprehensive name variations and aliases
- Global coverage across 200+ countries
- Industry classifications and metadata

## Data Location

**This is the PACKAGE data directory:**
```
entityidentity/data/companies/    ← You are here (sample data)
tables/companies/                 ← Full database (if built)
```

For detailed explanation of data organization, see:
- [DATA_LOCATIONS.md](../../../DATA_LOCATIONS.md) - Data directory conventions
- [CLAUDE.md](../../../CLAUDE.md) - Development setup

## Files in This Directory

- `companies.parquet` - Sample dataset (~500 companies, Parquet format)
- `companies.csv` - CSV preview for human inspection
- `companies_info.txt` - Database statistics and metadata
- `README.md` - This file

## Data Sources

Sample includes companies from:
- **GLEIF** - Global Legal Entity Identifier Foundation
- **Wikidata** - Crowdsourced company data
- **Stock Exchanges** - ASX (Australia), LSE (UK), TSX (Canada)

Priority: GLEIF > Wikidata > Exchanges (for identifier stability)

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `name` | str | Canonical company name |
| `country` | str | ISO 2-letter country code |
| `lei` | str | Legal Entity Identifier (if available) |
| `wikidata_qid` | str | Wikidata QID (if available) |
| `source` | str | Data source (gleif/wikidata/exchange) |
| `aliases` | list | Alternative names |

## Regenerating Sample Data

To update the sample dataset:

```bash
# Rebuild sample from full database
python scripts/companies/update_companies_db.py --use-samples

# This script:
# 1. Loads full database from tables/companies/
# 2. Selects diverse sample (~500 companies)
# 3. Saves to entityidentity/data/companies/
```

Sample selection criteria:
- Geographic diversity (all major countries)
- Company size diversity (large and small)
- Source diversity (GLEIF, Wikidata, exchanges)
- Industry diversity

## Size Limits

**Keep this directory small (<200KB total)** to avoid bloating the pip package.

Current size:
```
companies.parquet   ~80 KB
companies.csv       ~99 KB
companies_info.txt  ~1 KB
Total:             ~180 KB
```

If sample grows beyond 200KB, consider:
- Reducing sample size
- Removing CSV preview (keep only Parquet)
- Compressing more aggressively

## Git Status

✅ **This directory IS tracked in git**

All files are checked into version control because:
- Small size (<200KB)
- Needed for tests and demos
- Distributed with package
- Users expect data after `pip install`

The full database (`tables/companies/`) is NOT tracked (too large).

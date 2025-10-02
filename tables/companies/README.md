# Full Companies Database

This directory contains the **full companies database** built from multiple sources.

## Purpose

This is the **development and production database**:
- ❌ **NOT distributed with pip** (too large)
- ❌ **NOT checked into git** (regenerated locally)
- ✅ **Comprehensive** (100,000+ companies)
- ✅ **Production-ready** (high coverage and accuracy)

**Use this for:**
- Development and testing with real-world data
- Production deployments
- Research and analysis
- Applications requiring high recall

**Don't use this for:**
- Quick demos (use sample data instead)
- CI/CD (build time too long)
- Git commits (files too large)

## Quick Start

Build the full database:

```bash
# Full build (30-60 minutes, downloads GLEIF + Wikidata)
python scripts/companies/build_database_cli.py

# This creates:
#   tables/companies/companies_full.parquet  (unfiltered, 100K+ companies)
#   tables/companies/companies.parquet       (filtered, ready to use)
```

## Data Location

**This is the DEVELOPMENT data directory:**
```
entityidentity/data/companies/    ← Sample data (distributed with package)
tables/companies/                 ← You are here (full database)
```

For detailed explanation, see [DATA_LOCATIONS.md](../../DATA_LOCATIONS.md)

## Files in This Directory

### Generated Files (Git Ignored)

- `companies_full.parquet` - Complete unfiltered dataset (~10-50MB)
- `companies.parquet` - Filtered dataset ready for use (~1-10MB)
- `companies_metals.parquet` - Mining/energy sector only (~1-5MB)
- `companies.csv` - CSV preview (first 500 rows, ~700KB)
- `companies_info.txt` - Database statistics and build metadata

### Version Controlled Files

- `README.md` - This file
- `__init__.py` - Python package marker

## Database Variants

### 1. Full Database (`companies_full.parquet`)

**What:** Complete unfiltered dataset from all sources

**Size:** 10-50MB (100,000+ companies)

**Build:**
```bash
python scripts/companies/build_database_cli.py
```

**Use for:**
- Custom filtering workflows
- Research requiring complete data
- Building specialized subsets

### 2. Standard Database (`companies.parquet`)

**What:** Filtered to mining/energy sectors (default)

**Size:** 1-10MB (10,000-50,000 companies)

**Build:**
```bash
# Keyword-based filtering (fast)
python -m entityidentity.companies.companyfilter \
    --input tables/companies/companies_full.parquet \
    --output tables/companies/companies.parquet \
    --strategy keyword
```

**Use for:**
- Most applications (if you're working with metals/mining/energy)
- Production deployments
- API endpoint backing

### 3. LLM-Filtered Database (`companies_metals.parquet`)

**What:** High-accuracy filtering using LLM classification

**Size:** 1-5MB (5,000-20,000 companies)

**Build:**
```bash
# LLM-based filtering (slow but accurate)
bash scripts/companies/build_filtered_dataset.sh
```

**Use for:**
- Research requiring high precision
- Applications where false positives are costly
- When budget allows for longer build times

See [FILTERING.md](../../entityidentity/companies/FILTERING.md) for filtering strategies.

## Build Process

### Standard Build (Recommended)

```bash
# 1. Build full database
python scripts/companies/build_database_cli.py
# Downloads: GLEIF (~2GB), Wikidata (streaming), Stock exchanges
# Time: 30-60 minutes
# Output: tables/companies/companies_full.parquet

# 2. Filter to relevant sectors (keyword-based)
python -m entityidentity.companies.companyfilter \
    --input tables/companies/companies_full.parquet \
    --output tables/companies/companies.parquet \
    --strategy keyword
# Time: 5-10 seconds
# Output: tables/companies/companies.parquet
```

### LLM-Enhanced Build (High Accuracy)

```bash
# Complete pipeline with LLM classification
bash scripts/companies/build_filtered_dataset.sh

# This runs:
# 1. Build full database
# 2. Keyword pre-filtering
# 3. LLM refinement (GPT-4o-mini)
# Time: 60-90 minutes
# Output: tables/companies/companies_metals.parquet
```

### Sample-Only Build (Fast)

```bash
# Just rebuild sample data (for package distribution)
python scripts/companies/build_database_cli.py --use-samples

# Time: 5-10 seconds
# Output: entityidentity/data/companies/companies.parquet
```

## Data Sources

Companies are sourced from:

1. **GLEIF** (Global Legal Entity Identifier Foundation)
   - Official legal entity data
   - ~2.4 million companies globally
   - Highest priority for identifier stability
   - Requires download (~2GB)

2. **Wikidata**
   - Crowdsourced company information
   - ~5 million companies
   - Good for well-known companies
   - Includes aliases and alternative names

3. **Stock Exchanges**
   - ASX (Australia), LSE (UK), TSX (Canada)
   - Publicly traded companies
   - Ticker symbols included
   - Lowest priority (formatting inconsistencies)

## Deduplication

When the same company appears in multiple sources, we use deterministic priority:

**Priority:** GLEIF > Wikidata > Exchanges

This ensures:
- Stable canonical identifiers
- Consistent names across updates
- LEI codes when available

See `entityidentity/companies/companyidentity.py` for deduplication logic.

## Schema

| Column | Type | Coverage | Description |
|--------|------|----------|-------------|
| `name` | str | 100% | Canonical company name |
| `country` | str | 100% | ISO 2-letter country code |
| `lei` | str | ~23% | Legal Entity Identifier |
| `wikidata_qid` | str | ~40% | Wikidata QID |
| `source` | str | 100% | gleif/wikidata/asx/lse/tsx |
| `source_priority` | int | 100% | Deduplication priority (1=GLEIF, 2=Wikidata, 3=Exchange) |
| `aliases` | list | ~60% | Alternative names |
| `name_norm` | str | 100% | Normalized name (for matching) |

## Statistics

See `companies_info.txt` for:
- Total companies
- Breakdown by source
- Coverage by country
- Data completeness metrics

Example:
```
Total Companies: 125,432

Breakdown by Source:
  - gleif:     45,234 (36.0%)
  - wikidata:  52,198 (41.6%)
  - asx:        8,234 (6.6%)
  - lse:       12,345 (9.8%)
  - tsx:        7,421 (5.9%)

Top Countries:
  - US: 42,156 (33.6%)
  - CN: 18,234 (14.5%)
  - GB: 12,345 (9.8%)
  ...
```

## Maintenance

### Rebuilding

Rebuild periodically to get latest data:

```bash
# Full rebuild (recommended monthly)
python scripts/companies/build_database_cli.py

# Quick update (if sources haven't changed much)
python scripts/companies/build_database_cli.py --skip-download
```

### Cleaning Up

```bash
# Remove all generated databases
rm tables/companies/companies*.parquet

# Remove cache
rm -rf .cache/companies/

# Start completely fresh
rm -rf tables/ .cache/
python scripts/companies/build_database_cli.py
```

### Updating Sample Data

When schema changes, update the package sample:

```bash
# Rebuild sample from full database
python scripts/companies/build_database_cli.py --use-samples

# Commit updated sample
git add entityidentity/data/companies/
git commit -m "Update sample companies data"
```

## Size Management

**Current sizes (typical):**
```
companies_full.parquet     15 MB   (unfiltered)
companies.parquet           3 MB   (keyword filtered)
companies_metals.parquet    2 MB   (LLM filtered)
companies.csv             700 KB   (preview only)
Total:                    ~21 MB
```

**If sizes grow too large:**
- Use more aggressive filtering
- Remove unnecessary columns
- Split by region/country
- Use better compression

## Git Status

❌ **This directory is git-ignored** (except README and __init__.py)

Database files are NOT tracked because:
- Too large for git (>1MB per file)
- Can be regenerated from sources
- Different developers may use different filters
- Build is reproducible

To use this data:
1. Clone repository
2. Run build script
3. Files appear here automatically

## Performance

**Build Times:**
- GLEIF download: 5-10 min
- Wikidata fetch: 10-20 min
- Exchange data: 1-2 min
- Deduplication: 5-10 min
- Total: 30-60 min

**Loading Times:**
- Parquet load: 0.5-2 seconds
- In-memory size: 50-200 MB
- Query latency: <100ms

**Caching:**
- Database loaded once per Python session
- Cached with `@lru_cache` decorator
- Subsequent loads are instant

## Troubleshooting

### "No companies data found"

```bash
# Run build script
python scripts/companies/build_database_cli.py
```

### "Download failed"

```bash
# Check internet connection
# Try with verbose output
python scripts/companies/build_database_cli.py -v

# Skip problematic source
python scripts/companies/build_database_cli.py --skip-gleif
```

### "Database too old"

```bash
# Full rebuild
rm tables/companies/companies*.parquet
python scripts/companies/build_database_cli.py
```

## Related Documentation

- [DATA_LOCATIONS.md](../../DATA_LOCATIONS.md) - Data directory conventions
- [FILTERING.md](../../entityidentity/companies/FILTERING.md) - Filtering strategies
- [CLAUDE.md](../../CLAUDE.md) - Development setup
- [scripts/companies/README.md](../../scripts/companies/README.md) - Build scripts

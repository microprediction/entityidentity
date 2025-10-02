# Data Location Conventions

EntityIdentity uses multiple data directories for different purposes. This document clarifies where data lives and why.

## Overview

```
entityidentity/
├── entityidentity/data/companies/    # 📦 PACKAGE DATA (distributed)
│   ├── companies.parquet             # Sample dataset (~500 companies)
│   ├── companies.csv                 # CSV preview
│   └── README.md                     # Data description
│
├── tables/companies/                 # 🔨 DEVELOPMENT DATA (not distributed)
│   ├── companies.parquet             # Full dataset (git ignored)
│   ├── companies_full.parquet        # Complete unfiltered data
│   └── companies_info.txt            # Database statistics
│
└── .cache/companies/                 # 💾 RUNTIME CACHE (git ignored)
    └── classifications.json          # LLM classification cache
```

## Directory Purposes

### 1. `entityidentity/data/companies/` - Package Distribution Data

**Purpose:** Small sample dataset shipped with the Python package

**Contents:**
- `companies.parquet` - ~500 sample companies (~80KB)
- `companies.csv` - CSV preview for inspection
- `companies_info.txt` - Database statistics
- Sample data from GLEIF, Wikidata, and stock exchanges

**Git Status:** ✅ Tracked (checked into repository)

**When Used:**
- When package is installed via pip
- For tests on CI/CD (no build required)
- For quick demos and examples
- When no full database is available

**Size Limit:** <100KB (keep package lightweight)

**How to Update:**
```bash
# Build sample data from full dataset
python scripts/companies/build_database_cli.py --use-samples

# This generates data in entityidentity/data/companies/
```

**Users See This Data When:**
- Installing from PyPI: `pip install entityidentity`
- Running tests without building full database
- Using the package for the first time

---

### 2. `tables/companies/` - Development Database

**Purpose:** Full company database for development and production use

**Contents:**
- `companies.parquet` - Full filtered dataset (10K-100K companies)
- `companies_full.parquet` - Complete unfiltered dataset (100K+ companies)
- `companies_metals.parquet` - Sector-filtered dataset (mining/energy only)
- `companies.csv` - CSV preview (first 500 rows)
- `companies_info.txt` - Statistics and metadata

**Git Status:** ❌ Ignored (too large for git, regenerated locally)

**When Used:**
- During development
- For production deployments
- For comprehensive testing
- For research and analysis

**Size:** 1MB - 50MB (depends on filtering)

**How to Build:**
```bash
# Build full database
python scripts/companies/build_database_cli.py

# Build filtered database (mining/energy only)
python -m entityidentity.companies.companyfilter \
    --input tables/companies/companies_full.parquet \
    --output tables/companies/companies.parquet \
    --strategy keyword

# Or use LLM-based filtering
bash scripts/companies/build_filtered_dataset.sh
```

**Build Time:**
- Sample data: 5-10 seconds
- Full database: 30-60 minutes (downloads GLEIF, Wikidata, exchanges)

---

### 3. `.cache/companies/` - Runtime Cache

**Purpose:** Persistent cache for expensive operations (LLM classifications, etc.)

**Contents:**
- `classifications.json` - LLM classification results
- Temporary processing files

**Git Status:** ❌ Ignored (local cache, user-specific)

**When Used:**
- During LLM-based company filtering
- For caching expensive API calls
- For incremental processing

**Managed By:** Automatic (created as needed)

---

## Data Loading Priority

The `load_companies()` function follows this search order:

```python
from entityidentity.companies.companyresolver import load_companies

# Priority 1: Explicit path (if provided)
df = load_companies(data_path="/custom/path/companies.parquet")

# Priority 2: Package data (entityidentity/data/companies/)
# - Fast, always available
# - Small sample dataset

# Priority 3: Development data (tables/companies/)
# - Full dataset
# - Only available if built locally

# Priority 4: FileNotFoundError
# - Clear error message with build instructions
```

**Code:**
```python
@lru_cache(maxsize=1)
def load_companies(data_path: Optional[str] = None) -> pd.DataFrame:
    if data_path is None:
        # Try package data first (distributed with pip)
        pkg_dir = Path(__file__).parent.parent
        data_dir = pkg_dir / "data" / "companies"

        # Try development data second (built locally)
        if not found:
            tables_dir = pkg_dir.parent / "tables" / "companies"

        if not found:
            raise FileNotFoundError(
                "No companies data found. Run build script..."
            )
```

## Use Cases

### For End Users (Installing from PyPI)

```bash
pip install entityidentity
```

**Data Available:** Sample dataset in `entityidentity/data/companies/`

**What You Can Do:**
- Try out the API with ~500 companies
- Run tests
- Prototype applications

**What You Can't Do:**
- Resolve all company names (limited dataset)
- Production use (sample data only)

**To Get Full Data:**
```bash
# Clone repository and build
git clone https://github.com/microprediction/entityidentity
cd entityidentity
python scripts/companies/build_database_cli.py
```

---

### For Developers (Working on the Package)

**Setup:**
```bash
git clone https://github.com/microprediction/entityidentity
cd entityidentity
pip install -e .  # Install in development mode

# Build full database
python scripts/companies/build_database_cli.py
```

**Data Available:**
- Sample data: `entityidentity/data/companies/`
- Full data: `tables/companies/`

**Workflow:**
1. Develop using sample data (fast iteration)
2. Test with full data before committing
3. Update sample data if needed
4. Never commit full database to git

---

### For Production Deployments

**Recommended Setup:**

```dockerfile
# Dockerfile
FROM python:3.9

# Install package
RUN pip install entityidentity

# Download and build full database
WORKDIR /data
RUN git clone https://github.com/microprediction/entityidentity
RUN cd entityidentity && python scripts/companies/build_database_cli.py

# Copy built database to app
COPY entityidentity/tables/companies/companies.parquet /app/data/
```

**Or use pre-built database:**

```python
from entityidentity.companies.companyresolver import load_companies

# Load from custom location
df = load_companies(data_path="/app/data/companies.parquet")
```

---

## Common Questions

### Q: Why are there two data directories?

**A:** Separation of concerns:
- **Package data** = Small, distributed with pip, always available
- **Development data** = Large, built locally, for comprehensive use

This follows Python packaging best practices (similar to spaCy's small vs large models).

### Q: Which data should I use?

**A:** Depends on your needs:

| Use Case | Data Location | Size | Build Time |
|----------|---------------|------|------------|
| Quick demo | `entityidentity/data/` | ~80KB | Pre-built |
| Testing | `entityidentity/data/` | ~80KB | Pre-built |
| Development | `tables/` | 1-50MB | 30-60 min |
| Production | `tables/` or custom | 1-50MB | 30-60 min |

### Q: Why does load_companies() check both locations?

**A:** Graceful fallback for better user experience:
1. Try package data first (always available)
2. Fall back to development data (if built)
3. Fail with helpful error message

This means the package "just works" after pip install, while still supporting full datasets for serious use.

### Q: How do I know which data I'm using?

**A:** Check the file path:

```python
from entityidentity.companies.companyresolver import load_companies

df = load_companies()
# Check where it loaded from by looking at the returned dataframe size
print(f"Loaded {len(df):,} companies")

# Sample data: ~500 companies
# Full data: 10,000+ companies
```

### Q: Can I ship my own database with my app?

**A:** Yes! Two approaches:

**Option 1:** Bundle database in your package
```python
import pkg_resources
db_path = pkg_resources.resource_filename('myapp', 'data/companies.parquet')
df = load_companies(data_path=db_path)
```

**Option 2:** Download at runtime
```python
# Download from S3, Google Cloud, etc.
import requests
db_url = "https://myapp.com/data/companies.parquet"
local_path = "/tmp/companies.parquet"
# ... download logic ...
df = load_companies(data_path=local_path)
```

---

## Maintenance

### Updating Sample Data

When the full database schema changes, update the sample:

```bash
# Rebuild full database
python scripts/companies/build_database_cli.py

# Regenerate sample (creates entityidentity/data/companies/)
python scripts/companies/build_database_cli.py --use-samples

# Commit the updated sample
git add entityidentity/data/companies/
git commit -m "Update sample companies data"
```

### Cleaning Up

```bash
# Remove development databases (keeps sample)
rm -rf tables/companies/companies*.parquet

# Remove cache
rm -rf .cache/

# Remove everything (start fresh)
rm -rf tables/ .cache/
```

---

## File Sizes

**entityidentity/data/companies/ (Tracked in Git)**
```
companies.parquet    ~80 KB   (500 companies)
companies.csv        ~99 KB   (CSV preview)
companies_info.txt   ~1 KB    (metadata)
Total:              ~180 KB
```

**tables/companies/ (Git Ignored)**
```
companies_full.parquet    10-50 MB   (100K+ companies)
companies.parquet          1-10 MB   (filtered dataset)
companies_metals.parquet   1-5 MB    (sector filtered)
companies.csv             ~700 KB    (CSV preview)
Total:                    15-70 MB
```

**Why This Matters:**
- Git repository stays small (<1MB for data)
- PyPI package stays small (<500KB)
- Full datasets are opt-in, not mandatory

---

## Data Loading Patterns

EntityIdentity uses two different data loading patterns depending on whether the data is:
1. **Static** (bundled with package) - like metals data
2. **Dynamic** (built/downloaded by user) - like companies data

### Pattern 1: Static Package Data (Metals)

**Location:** `entityidentity/metals/data/metals.parquet`

**Characteristics:**
- Data is **module-local** (stored within the package)
- Always available after pip install
- Never searches `tables/` directory
- Small, curated dataset (<1MB)
- Updates require new package release

**Loading Code:**
```python
from entityidentity.metals.metalapi import load_metals

# Searches only: entityidentity/metals/data/metals.parquet
df = load_metals()
```

**Use Case:** Metal entities are:
- Stable (periodic table doesn't change often)
- Small (~50 metals)
- Manually curated
- Part of the package's core value

---

### Pattern 2: Dynamic Build Data (Companies)

**Location:** `tables/companies/companies.parquet` OR `entityidentity/data/companies/companies.parquet`

**Characteristics:**
- Data can be **built or downloaded** by user
- Falls back to sample data in package
- Searches both `tables/` (dev) and `data/` (package)
- Large, generated dataset (1-50MB)
- User updates via build scripts

**Loading Code:**
```python
from entityidentity.companies.companyresolver import load_companies

# Priority:
# 1. Explicit path (if provided)
# 2. Package data: entityidentity/data/companies/
# 3. Development data: tables/companies/
df = load_companies()
```

**Use Case:** Company data is:
- Dynamic (companies constantly change)
- Large (10K-100K+ companies)
- Downloaded from external sources (GLEIF, Wikidata)
- Too large to bundle fully with package

---

### When to Use Each Pattern

| Criteria | Static (Metals) | Dynamic (Companies) |
|----------|----------------|---------------------|
| **Data size** | <1MB | >1MB |
| **Update frequency** | Rare (years) | Frequent (weekly/monthly) |
| **Source** | Manually curated | External APIs/downloads |
| **Distribution** | Bundle with package | User builds locally |
| **Search locations** | Module-local only | Multiple fallback paths |

---

### Shared Utilities

Both patterns use the shared `find_data_file()` utility from `entityidentity.utils.datautils`:

```python
# Metals - module-local only
found_path = find_data_file(
    module_file=__file__,
    subdirectory="metals",
    filenames=["metals.parquet"],
    search_dev_tables=False,      # Don't search tables/
    module_local_data=True,       # Check metals/data/
)

# Companies - multiple search paths
found_path = find_data_file(
    module_file=__file__,
    subdirectory="companies",
    filenames=["companies.parquet", "companies.csv"],
    search_dev_tables=True,       # Also search tables/
    module_local_data=False,      # Use standard data/ dir
)
```

This unified approach provides:
- Consistent error messages
- Flexible search strategies
- Easy configuration per data type

---

## Related Documentation

- [CLAUDE.md](CLAUDE.md) - Development setup and commands
- [entityidentity/data/companies/README.md](entityidentity/data/companies/README.md) - Sample data description
- [tables/companies/README.md](tables/companies/README.md) - Full database documentation
- [scripts/companies/README.md](scripts/companies/README.md) - Build scripts

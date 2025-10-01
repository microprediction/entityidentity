# Dataset Expansion Strategy

## The Name Drift Problem

**Problem**: If we add exchange companies now and expand GLEIF later, identifiers will drift.

### Example Scenario

**Wrong Order** (causes drift):
```
1. Current: 644 GLEIF companies
2. Add exchanges: "BHP GROUP LIMITED:AU" (from ASX)
3. Later expand GLEIF: "BHP Group Limited:AU" (from GLEIF, higher priority)
4. ❌ DRIFT: Same company, different identifier!
```

**Correct Order** (stable):
```
1. Load 100K GLEIF companies
2. "BHP Group Limited:AU" established from GLEIF
3. Add exchanges: BHP already in dataset, uses GLEIF name
4. ✅ STABLE: Identifier locked in, no future drift
```

## Source Priority System

The system uses source priority to resolve conflicts:

```
GLEIF (Priority 1) > Wikidata (Priority 2) > Exchanges (Priority 3)
```

**Why this matters:**
- GLEIF has official legal names from regulatory filings
- Exchanges often have inconsistent formatting (ALL CAPS, etc.)
- Priority ensures deterministic resolution

**The catch:**
- Priority only works when sources are loaded together
- Adding new high-priority sources later causes drift
- **Solution**: Load high-priority sources (GLEIF) comprehensively first

## Recommended Strategy: GLEIF-First, Then Exchanges

### Phase 1: Comprehensive GLEIF (100K companies)

**Command:**
```bash
caffeinate bash scripts/companies/build_filtered_dataset.sh 100000 openai
```

**What it does:**
1. Fetches 100K companies from GLEIF API (~30 min download)
2. Caches locally in `.cache/companies/`
3. Runs LLM classification (reuses 9,944 cached entries)
4. Filters to mining/metals companies
5. Saves to `entityidentity/data/companies/`

**Estimates:**
- **Cost**: ~$20 (90K new classifications at $0.002 each)
- **Time**: ~3-4 hours
- **Output**: ~700-1000 mining/metals companies
- **Coverage**: Comprehensive GLEIF subset

**Benefits:**
- Establishes authoritative names from GLEIF
- No future drift (GLEIF is highest priority)
- Reuses 9,944 cached classifications
- Geographic diversity from GLEIF's global coverage

### Phase 2: Exchange Addition (ASX, LSE, TSX)

**Command:**
```bash
python scripts/companies/expand_with_exchanges.py --provider openai
```

**What it does:**
1. Loads companies from major stock exchanges:
   - ASX: ~2000 Australian companies
   - LSE: ~350 UK companies (FTSE 100+250)
   - TSX: ~220 Canadian companies
2. Deduplicates against existing GLEIF dataset
3. Classifies only NEW companies with LLM
4. Merges with existing dataset

**Estimates:**
- **Cost**: ~$2-5 (most companies already in GLEIF)
- **Time**: ~1 hour
- **Output**: +50-200 additional companies
- **Coverage**: Exchange-listed mining companies not in GLEIF

**Benefits:**
- Catches smaller mining companies
- Better coverage of junior miners
- Minimal cost (most are duplicates)
- Names stable (use GLEIF names where available)

### Phase 3 (Optional): Wikidata

**Command:**
```bash
python scripts/companies/expand_with_wikidata.py --provider openai
```

**Estimates:**
- **Cost**: ~$5
- **Time**: ~1 hour
- **Output**: +50-100 companies

## Complete Build Script

For convenience, use the all-in-one script:

```bash
bash scripts/companies/run_gleif_first_expansion.sh
```

This runs:
1. Phase 1: Comprehensive GLEIF (with confirmation)
2. Phase 2: Exchange expansion (with confirmation)

**Total estimates:**
- **Cost**: ~$22-25
- **Time**: ~4-6 hours
- **Output**: ~800-1200 mining/metals companies
- **Result**: Stable identifiers, no future drift

## Cost Comparison

### Wrong Approach (Exchange-First)
```
1. Add exchanges now:        $5,  1.4 hours →  655 + 178 = 833 companies
2. Later expand GLEIF:       $40,  8 hours   → +200 companies
3. Fix name drift:           ???, ??? hours  → Rebuild required
Total:                       $45+, 10+ hours, UNSTABLE
```

### Correct Approach (GLEIF-First)
```
1. Comprehensive GLEIF:       $20,  3-4 hours →  700-1000 companies
2. Add exchanges:             $5,   1 hour     → +50-200 companies
Total:                        $25,  4-5 hours,  STABLE FOREVER
```

**Winner**: GLEIF-First
- ✅ Cheaper ($25 vs $45+)
- ✅ Faster (4-5 hours vs 10+ hours)
- ✅ Better quality (GLEIF is authoritative)
- ✅ No drift (names stable forever)

## Technical Details

### GLEIF API

```python
from entityidentity.companies.companygleif import load_gleif_lei

# Fetch 100K companies (with caching)
df = load_gleif_lei(
    cache_dir=".cache/companies",
    max_records=100000
)
```

**API Details:**
- Endpoint: `https://api.gleif.org/api/v1/lei-records`
- Pagination: 10,000 records per request
- Rate limit: Reasonable (handles pagination)
- Download time: ~30 minutes for 100K

### Caching Strategy

```
.cache/companies/
├── gleif_100000.parquet          # GLEIF raw data
├── classification_cache.json     # LLM classifications
└── exchanges/
    ├── asx.parquet                # ASX cached data
    ├── lse.parquet                # LSE cached data
    └── tsx.parquet                # TSX cached data
```

**Cache behavior:**
- GLEIF data cached locally (fast subsequent builds)
- LLM classifications cached by `(name, country)` key
- Exchange data fetched fresh (changes frequently)

### Deduplication Logic

When adding exchanges to GLEIF dataset:

```python
def deduplicate_against_gleif(exchange_df, gleif_df):
    """
    1. Normalize names (canonicalize_name)
    2. Check LEI overlap (exact match)
    3. Check name+country overlap (normalized match)
    4. Return only new companies
    """
```

**Result:**
- Exchange company with LEI in GLEIF → Skip (use GLEIF)
- Exchange company with name+country in GLEIF → Skip (use GLEIF)
- Exchange company not in GLEIF → Add with exchange name
- **Outcome**: GLEIF names take precedence, no drift

## Preview Before Running

To see what would be added without running LLM classification:

```bash
# Preview GLEIF expansion
python -c "
from entityidentity.companies.companygleif import load_gleif_lei
df = load_gleif_lei(cache_dir='.cache/companies', max_records=100000)
print(f'Would fetch: {len(df)} GLEIF companies')
print(f'Top countries: {df[\"country\"].value_counts().head(10)}')
"

# Preview exchange expansion
python scripts/companies/preview_exchange_expansion.py
```

## Monitoring Progress

During LLM classification:

```
Classification Progress: 1234/100000 [1%]
⚠️  Slow request detected: 5.2s (rate limit?)

📊 Batch stats (last 100):
   Avg API time: 2.1s
   Slow requests: 2 (>5s)
   Cached: 9,944 classifications

Expected completion: 2.5 hours
```

## Troubleshooting

### Issue: "Rate limited by OpenAI"
**Solution**: 
- Script includes backoff logic
- Slow requests detected and logged
- Continues automatically

### Issue: "Out of memory"
**Solution**:
- Script processes in batches
- Clears memory between batches
- Should work on 8GB+ RAM

### Issue: "Classification cache corrupted"
**Solution**:
```bash
rm .cache/companies/classification_cache.json
# Re-run (will reclassify everything)
```

### Issue: "GLEIF API unavailable"
**Solution**:
- Check https://www.gleif.org/en/lei-data/gleif-api
- Use cached data if available
- Try again later

## Next Steps

1. **Review current status**:
   ```bash
   python scripts/companies/preview_exchange_expansion.py
   ```

2. **Run comprehensive build**:
   ```bash
   caffeinate bash scripts/companies/run_gleif_first_expansion.sh
   ```

3. **Test the dataset**:
   ```bash
   python -c 'from entityidentity import list_companies; print(len(list_companies()))'
   ```

4. **Review statistics**:
   ```bash
   cat entityidentity/data/companies/companies_info.txt
   ```

5. **Commit to git**:
   ```bash
   git add entityidentity/data/companies/
   git commit -m "Expand dataset with GLEIF-first strategy"
   ```

## Summary

**DO**:
- ✅ Load GLEIF comprehensively first (100K companies)
- ✅ Then add exchanges
- ✅ Use caching for cost efficiency
- ✅ Monitor progress during classification

**DON'T**:
- ❌ Add exchanges before comprehensive GLEIF
- ❌ Skip caching (wastes money)
- ❌ Load sources in arbitrary order (causes drift)
- ❌ Ignore source priority (breaks determinism)

**Result**: Stable, high-quality dataset with no future name drift! 🎉


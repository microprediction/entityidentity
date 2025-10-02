# Company Filtering Strategies

This document explains the three filtering strategies available in EntityIdentity for filtering companies to mining/energy sectors.

## Overview

The [`companyfilter.py`](companyfilter.py) module provides a unified API with three distinct strategies:

1. **Keyword Filtering** (Fast but Simple)
2. **LLM Classification** (Accurate but Expensive)
3. **Hybrid Mode** (Balanced - Recommended)

## Quick Start

```python
from entityidentity.companies.companyfilter import filter_companies
import pandas as pd

# Load your company data
df = pd.read_parquet('companies.parquet')

# Option 1: Hybrid mode (recommended for most use cases)
filtered = filter_companies(
    df,
    strategy='hybrid',
    provider='openai',
    cache_file='.cache/companies/classifications.json'
)

# Option 2: Keyword-only (fastest, no API costs)
filtered = filter_companies(df, strategy='keyword')

# Option 3: LLM-only (most accurate)
filtered = filter_companies(
    df,
    strategy='llm',
    provider='openai',
    confidence_threshold=0.8
)
```

## Strategy Comparison

| Strategy | Speed | Accuracy | Cost | Best For |
|----------|-------|----------|------|----------|
| **Keyword** | ~10,000 companies/sec | ~70-80% | Free | CI/CD, quick filtering, tight budgets |
| **LLM** | ~3 companies/sec | ~95%+ | API costs | Production databases, research, high accuracy needs |
| **Hybrid** | ~100 companies/sec | ~90%+ | Moderate | **Most use cases** - balances speed, accuracy, cost |

## When to Use Each Strategy

### 1. Keyword Filtering (`strategy='keyword'`)

**Use When:**
- Running in CI/CD pipelines
- Working with very large datasets (millions of companies)
- No API budget available
- Quick exploratory analysis needed
- Acceptable to have some false positives/negatives

**How It Works:**
- Matches company names, industries, and sector codes against predefined keywords
- Checks GICS, NAICS, and NACE industry classification codes
- Uses whitelist of known major mining/energy companies
- Processes ~10,000 companies per second

**Limitations:**
- Misses companies with unclear names (e.g., "Glencore" without "mining" keyword)
- Can't understand context or business model nuances
- No distinction between supply-side (mining) and demand-side (manufacturing)

**Example:**
```python
from entityidentity.companies.companyfilter import filter_companies_keyword

# Direct keyword filtering (no API needed)
filtered = filter_companies_keyword(df)
```

### 2. LLM Classification (`strategy='llm'`)

**Use When:**
- Building production research databases
- Need to distinguish supply-side (mining) vs demand-side (manufacturing)
- Working with diversified conglomerates
- Accuracy is critical
- Have API budget available

**How It Works:**
- Uses OpenAI or Anthropic LLMs to intelligently classify companies
- Understands business context, supply chains, and industry nuances
- Provides confidence scores and reasoning
- Distinguishes between supply/demand sides of value chain
- Processes ~3 companies per second (GPT-4o-mini)

**Configuration:**
```python
filtered = filter_companies(
    df,
    strategy='llm',
    provider='openai',              # or 'anthropic'
    model='gpt-4o-mini',            # optional, uses default
    cache_file='.cache/classifications.json',  # enables persistent caching
    confidence_threshold=0.7,        # minimum confidence (0.0-1.0)
    batch_size=100,                  # cache save frequency
)
```

**Cost Estimation:**
- GPT-4o-mini: ~$0.0003 per company (~$300 per million companies)
- GPT-4o: ~$0.0075 per company (~$7,500 per million companies)
- Claude Haiku: ~$0.0004 per company (~$400 per million companies)

**Advantages:**
- Handles edge cases (e.g., "BHP" is mining despite no keywords)
- Understands diversified companies (e.g., Samsung Electronics vs Samsung C&T)
- Classifies value chain position (supplier vs consumer)
- Provides confidence scores and reasoning

### 3. Hybrid Mode (`strategy='hybrid'`)  **← RECOMMENDED**

**Use When:**
- Building filtered datasets for most use cases
- Want good accuracy without excessive costs
- Processing 10K-1M companies
- Need reasonable speed (<1 hour for 100K companies)

**How It Works:**
1. **Stage 1**: Apply keyword filtering to reduce dataset by ~90%
2. **Stage 2**: Use LLM to refine results and eliminate false positives

**Performance:**
- Processes ~100 companies/second
- Typically ~90% accurate
- Reduces API costs by 10x compared to LLM-only
- Completes 100K companies in ~30 minutes (vs 9 hours for LLM-only)

**Example Output:**
```
======================================================================
  HYBRID FILTERING STRATEGY
======================================================================

📍 Stage 1: Keyword Pre-filtering
----------------------------------------------------------------------
Filtering using keyword-based rules...
Total companies: 100,000
✅ Matched companies: 12,500 (12.5%)
   Reduced dataset by 87.5% (100,000 → 12,500 companies)

📍 Stage 2: LLM Refinement
----------------------------------------------------------------------
Using openai with model gpt-4o-mini
Total companies: 12,500
Cached classifications: 0
Classifying companies (confidence threshold: 0.7)...
[Progress bar: 12,500/12,500]

✅ Matched companies: 9,200 (73.6% of keyword matches)

======================================================================
  HYBRID FILTERING RESULTS
======================================================================
   Original dataset:         100,000 companies
   After keyword filter:      12,500 companies ( 12.5%)
   After LLM refinement:       9,200 companies (  9.2%)
   False positive rate:        26.4%
======================================================================
```

## Advanced Configuration

### Caching

LLM classifications are expensive. Always use caching for production workflows:

```python
from pathlib import Path

filtered = filter_companies(
    df,
    strategy='hybrid',
    cache_file=Path('.cache/companies/classifications.json')
)
```

Cache keys: `{company_name}|{country}` - if you re-filter the same companies, results are instant.

### Custom Confidence Thresholds

```python
# Strict filtering (fewer false positives)
filtered = filter_companies(
    df,
    strategy='llm',
    confidence_threshold=0.9  # Only companies the LLM is very confident about
)

# Relaxed filtering (catch more edge cases)
filtered = filter_companies(
    df,
    strategy='llm',
    confidence_threshold=0.5  # Include companies LLM is somewhat confident about
)
```

### Custom Sector Definitions

Edit [`company_classifier_config.yaml`](company_classifier_config.yaml) to customize sector definitions, prompts, and classification criteria.

## Command-Line Usage

```bash
# Hybrid filtering (recommended)
python -m entityidentity.companies.companyfilter \
    --input companies_full.parquet \
    --output companies_metals.parquet \
    --strategy hybrid \
    --provider openai \
    --cache-file .cache/classifications.json

# LLM-only filtering
python -m entityidentity.companies.companyfilter \
    --input companies_full.parquet \
    --output companies_metals.parquet \
    --provider anthropic \
    --model claude-3-haiku-20240307 \
    --cache-file .cache/classifications.json \
    --confidence-threshold 0.8

# Keyword-only filtering
python scripts/companies/filter_mining_energy.py \
    --input companies_full.parquet \
    --output companies_metals.parquet
```

## Migration from Old Scripts

If you were using the standalone scripts:

**Old:** `scripts/companies/filter_mining_energy.py` (keyword-based)
```python
# Deprecated approach
from scripts.companies.filter_mining_energy import filter_database
filtered = filter_database(input_path, output_path)
```

**New:** Use unified API
```python
from entityidentity.companies.companyfilter import filter_companies
df = pd.read_parquet(input_path)
filtered = filter_companies(df, strategy='keyword')
filtered.to_parquet(output_path)
```

**Old:** `scripts/companies/filter_mining_energy_llm.sh` (LLM script)
```bash
# Deprecated
bash scripts/companies/filter_mining_energy_llm.sh
```

**New:** Use Python API or CLI
```bash
python -m entityidentity.companies.companyfilter \
    --input companies.parquet \
    --output filtered.parquet \
    --strategy hybrid
```

## Performance Tips

1. **Use caching**: Always enable `cache_file` for LLM strategies
2. **Start with hybrid**: Test on small dataset, then scale up
3. **Batch processing**: For very large datasets (>1M), split into batches and merge
4. **Rate limits**: OpenAI/Anthropic rate limit at ~10,000 requests/min - hybrid mode helps avoid this
5. **Confidence tuning**: Start with default (0.7), adjust based on false positive/negative analysis

## Troubleshooting

### Rate Limiting
```
🔴 RATE LIMIT detected - API is throttling requests!
```

**Solution:** Use hybrid mode to reduce API calls, or add delays between batches.

### Low Accuracy
If you're getting too many false positives/negatives:

- **Too many false positives?** → Increase `confidence_threshold` to 0.8 or 0.9
- **Too many false negatives?** → Decrease `confidence_threshold` to 0.5 or 0.6
- **Keyword mode missing companies?** → Switch to hybrid or LLM mode

### High Costs
If API costs are too high:

- Use hybrid mode instead of LLM-only (reduces costs by 10x)
- Use keyword mode for CI/CD and exploratory work
- Cache aggressively - re-running with cache is free
- Use GPT-4o-mini instead of GPT-4o (25x cheaper)

## API Reference

See [`companyfilter.py`](companyfilter.py) for complete API documentation.

### Main Functions

- `filter_companies(df, strategy, ...)` - Unified entry point
- `filter_companies_keyword(df)` - Keyword-only filtering
- `filter_companies_llm(df, provider, model, ...)` - LLM-only classification
- `filter_companies_hybrid(df, provider, ...)` - Hybrid approach

### Configuration

- [`company_classifier_config.yaml`](company_classifier_config.yaml) - LLM prompts and sector definitions
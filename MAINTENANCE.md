# Maintenance Guide

Internal documentation for developers and maintainers of the EntityIdentity package.

## Building the Company Database

### Quick Test Build (Sample Data)

```bash
python scripts/companies/build_database_cli.py --use-samples
```

This creates:
- `tables/companies/companies.parquet` - Main database (compressed)
- `tables/companies/companies.csv` - First 500 rows for inspection
- `tables/companies/companies_info.txt` - Database statistics

### Full Build (Live Data Sources)

```bash
python scripts/companies/build_database_cli.py
```

**Warning**: Downloads ~2-3GB of data and takes 30-60 minutes.

Data sources:
- GLEIF LEI Golden Copy (~2.5M entities)
- Wikidata companies
- Stock exchange listings (ASX, LSE, TSX)

## LLM-Based Filtering

### Overview

The package includes LLM-based classification to filter companies in the metals value chain:

**Supply Side (Producers)**:
- Mining & Extraction: Primary metals, precious metals, rare earths, critical minerals
- Recycling & Circular Economy: Scrap metal, e-waste, battery recycling, urban mining

**Demand Side (Consumers)**:
- Automotive & Transportation: Auto OEMs, EV manufacturers, aerospace
- Manufacturing & Industrial: Heavy equipment, steel mills, fabrication
- Construction & Infrastructure: Building materials, structural steel
- Electronics & Technology: Semiconductors, batteries, solar panels
- Appliances & Consumer Goods: Home appliances, power tools

### Running LLM Filter

```bash
# Set API key
echo "OPENAI_API_KEY=your_key_here" >> .env

# Filter database
bash scripts/companies/filter_mining_energy_llm.sh \
  --input tables/companies/companies_full.parquet \
  --output tables/companies/companies_metals.parquet \
  --provider openai
```

Options:
- `--provider`: `openai` or `anthropic`
- `--model`: Override default model
- `--confidence`: Threshold (default: 0.7)
- `--cache-file`: Path to cache file

### Test Results

**Test Dataset**: 13 sample companies
**Model**: GPT-4o-mini
**Success Rate**: 92.3% (12/13)
**Processing Time**: 37 seconds (~2.87s per company)

**Classification Results**:
- Supply (9): BHP, Rio Tinto, Anglo American, Fortescue, Newcrest, Antofagasta, Barrick Gold, Franco-Nevada, Wheaton
- Demand (2): Apple (electronics), Tesla (EVs)
- Both (1): Glencore (mining + trading/processing)
- Rejected (1): Microsoft (not metal-intensive)

### Cost Estimates

**GPT-4o-mini** (Recommended):
| Dataset Size | Cost | Time |
|-------------|------|------|
| 1,000 companies | $0.23 | 10-15 min |
| 10,000 companies | $2.33 | 2-3 hours |
| 100,000 companies | $23.25 | 20-30 hours |
| 250,000 companies | $58 | ~3 days |
| 2.5M companies (full GLEIF) | $581 | ~20-25 days |

**GPT-4o** (Premium):
| Dataset Size | Cost | Time |
|-------------|------|------|
| 1,000 companies | $3.88 | 10-15 min |
| 10,000 companies | $38.75 | 2-3 hours |
| 100,000 companies | $387.50 | 20-30 hours |
| 250,000 companies | $970 | ~3 days |
| 2.5M companies | $9,687.50 | ~20-25 days |

**Token usage per company**: ~950 input + ~150 output = 1,100 tokens

### Caching

Classifications are cached to `.cache/companies/classifications.json`:
- First run: Full API cost
- Subsequent runs: $0 (uses cache)
- Only new/changed companies are processed

Cache format:
```json
{
  "Company Name|Country": {
    "is_relevant": true,
    "category": "supply",
    "reasoning": "...",
    "confidence": 0.95,
    "metal_intensity": "high",
    "key_activities": ["mining", "extraction"],
    "timestamp": "2025-09-30T15:14:41.294515"
  }
}
```

### Cost Reduction Strategies

1. **Use GPT-4o-mini**: 95% cheaper, still excellent accuracy
2. **Enable caching**: Reruns are free
3. **Batch processing**: Process in chunks with cache saves
4. **Hybrid approach**: Pre-filter with keywords, then LLM classify ambiguous cases
   - Can reduce costs by 80-90%
   - Example: 2.5M → 500K candidates → ~$116 total

### Configuration

Edit `entityidentity/companies/company_classifier_config.yaml`:

```yaml
# Sector definitions
categories:
  supply:
    sectors:
      mining: [...]
      recycling: [...]
  demand:
    sectors:
      automotive: [...]
      manufacturing: [...]
      # etc.

# LLM prompts
prompts:
  system: |
    You are an expert in metals industry classification...
  user_template: |
    Classify this company...

# Model configuration
models:
  openai:
    default: "gpt-4o-mini"
    max_tokens: 400
  anthropic:
    default: "claude-3-haiku-20240307"
    max_tokens: 400
```

### Example Classifications

**BHP Group Limited** (Supply - Mining):
```json
{
  "is_relevant": true,
  "category": "supply",
  "reasoning": "Primary mining operations: copper, iron, nickel, coal",
  "confidence": 1.0,
  "metal_intensity": "high",
  "key_activities": ["copper mining", "iron ore extraction", "nickel production"]
}
```

**Apple Inc.** (Demand - Electronics):
```json
{
  "is_relevant": true,
  "category": "demand",
  "reasoning": "Major consumer of metals through electronics manufacturing",
  "confidence": 0.95,
  "metal_intensity": "medium",
  "key_activities": ["consumer electronics", "semiconductors", "aluminum casings"]
}
```

**Glencore plc** (Both):
```json
{
  "is_relevant": true,
  "category": "both",
  "reasoning": "Mines metals AND trades/processes them globally",
  "confidence": 1.0,
  "metal_intensity": "high",
  "key_activities": ["coal mining", "copper mining", "metal trading", "smelting"]
}
```

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=entityidentity
```

### Run Specific Test Suite

```bash
pytest tests/companies/test_companyidentity.py -v
pytest tests/companies/test_loaders.py -v
```

### Test with Live APIs

```bash
ENTITYIDENTITY_TEST_LIVE=1 pytest -v
```

**Warning**: This will make real API calls to GLEIF, Wikidata, etc.

### Test Structure

```
tests/
└── companies/
    ├── test_companyidentity.py  # Normalization and resolution
    └── test_loaders.py           # Data source loaders
```

## Package Structure

```
entityidentity/
├── __init__.py
└── companies/
    ├── __init__.py
    ├── companyidentity.py           # Main resolver
    ├── companygleif.py              # GLEIF LEI loader
    ├── companywikidata.py           # Wikidata loader
    ├── companyexchanges.py          # Exchange loaders
    ├── companyfilter.py             # LLM classification
    └── company_classifier_config.yaml  # LLM config

scripts/
└── companies/
    ├── build_database_cli.py       # Build database
    └── filter_mining_energy_llm.sh  # LLM filtering

tables/
└── companies/
    ├── companies.parquet            # Main database (git ignored)
    ├── companies.csv                # Preview (git tracked)
    ├── companies_info.txt           # Metadata (git tracked)
    └── README.md

tests/
└── companies/
    ├── test_companyidentity.py
    └── test_loaders.py
```

## Release Process

### 1. Update Version

Edit `setup.py` and `entityidentity/__init__.py`:
```python
__version__ = "0.0.2"
```

### 2. Build Sample Database

```bash
python scripts/companies/build_database_cli.py --use-samples
```

Commit the generated files:
- `tables/companies/companies.csv` (preview)
- `tables/companies/companies_info.txt` (metadata)

### 3. Run Tests

```bash
pytest
```

### 4. Build Package

```bash
python setup.py sdist bdist_wheel
```

### 5. Upload to PyPI

```bash
twine upload dist/*
```

## Data Files in Package Distribution

**Included in package** (via `MANIFEST.in` and `setup.py`):
- `tables/companies/*.csv` - Preview data (small)
- `tables/companies/*.txt` - Metadata files
- `tables/companies/README.md` - Documentation

**Git ignored but package included**:
- `tables/companies/companies.parquet` - Full database (generated during build)

**Git ignored and not in package**:
- `.cache/` - LLM classification cache (user-specific)
- `tables/companies/companies_full.parquet` - Unfiltered full database

Users can generate the full database after installation:
```bash
python scripts/companies/build_database_cli.py --use-samples
```

## Architecture Decisions

### Why In-Memory?

- **Speed**: <100ms for most queries
- **Simplicity**: No server setup required
- **Portability**: Works anywhere Python runs
- **Cost**: No infrastructure costs

### Why Parquet?

- **Compression**: ~10-20x smaller than CSV
- **Performance**: Fast loading with pandas
- **Schema**: Preserves data types
- **Standard**: Widely supported

### Why LLM Classification?

- **Accuracy**: Better than rule-based keywords
- **Flexibility**: Easy to adjust prompts
- **Scalability**: Handles millions of companies
- **Maintenance**: No manual whitelists

### Why Cache Everything?

- **Cost**: Avoid redundant LLM API calls
- **Speed**: Instant lookups for known cases
- **Reliability**: Work offline after first run

## Troubleshooting

### FileNotFoundError: No companies data found

```bash
# Generate sample data
python scripts/companies/build_database_cli.py --use-samples
```

### Import Error: pandas not installed

```bash
pip install -e .
```

### LLM Classification Errors

Check API key:
```bash
echo $OPENAI_API_KEY
```

Test connection:
```python
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

### Cache Issues

Clear cache:
```bash
rm -rf .cache/companies/
```

## Performance Optimization

### Matching Performance

- **Normalization**: Cached with `@lru_cache`
- **Blocking**: Country + first-token prefix reduces candidates by 99%+
- **Scoring**: RapidFuzz is highly optimized C++

Typical query: <100ms for 1M+ companies

### Database Size

- Sample database: ~10-50KB (parquet), ~50-200KB (csv)
- Full GLEIF: ~50-100MB (parquet), ~500MB (csv)
- Memory usage: ~200-500MB when loaded

### LLM Classification

- **Throughput**: ~3-5 companies/second
- **Parallelization**: Not recommended (rate limits, cost)
- **Batch size**: 100 companies per cache save (good balance)

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Document public functions
- Write tests for new features

### Adding Data Sources

1. Create loader in `entityidentity/companies/companyXXX.py`
2. Return DataFrame with required columns: `name`, `country`
3. Optional columns: `lei`, `ticker`, `industry`, `aliases`
4. Add to `build_database_cli.py` consolidation
5. Write tests in `tests/companies/test_loaders.py`

### Updating LLM Prompts

1. Edit `entityidentity/companies/company_classifier_config.yaml`
2. Test on sample data
3. Review classifications in cache file
4. Document changes in this file

## License

MIT License - see [LICENSE](LICENSE)


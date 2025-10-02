# Instruments Module

The instruments module provides loading and resolution of financial instrument ticker references with automatic crosswalk to metals and clusters.

## Features

- **Multi-source loading**: Automatic fallback from GCS → environment variable → local files
- **Computed identifiers**: Stable 16-character instrument IDs based on source + ticker
- **Metal crosswalk**: Automatic resolution of material hints to metal IDs and clusters
- **LRU caching**: Fast in-memory access after initial load
- **Flexible schemas**: Handles various column name formats

## Usage

### Basic Loading

```python
from entityidentity.instruments import load_instruments

# Load ticker references (auto-selects source)
df = load_instruments()

# Columns include:
# - instrument_id: Stable 16-char hex ID
# - ticker_norm: Normalized ticker for matching
# - name_norm: Normalized name for matching
# - material_id: Resolved metal ID (if available)
# - cluster_id: Metal cluster ID (if available)
```

### Loading Priority

The loader tries sources in this order:

1. **Explicit path** (if provided)
2. **Environment variable** `GSMC_TICKERS_PATH`
3. **Google Cloud Storage** `gs://gsmc-market-data/ticker_references.parquet`
4. **Local package data** `entityidentity/instruments/data/`
5. **Development tables** `../tables/instruments/`

### Environment Configuration

```bash
# Use a specific local file
export GSMC_TICKERS_PATH=/path/to/ticker_references.parquet

# Or configure GCS credentials
gcloud auth application-default login
```

### Cache Management

```python
from entityidentity.instruments import clear_cache

# Clear cached data (useful for testing or updates)
clear_cache()
```

## Data Schema

The ticker references include:

- `Source`: Data provider (Fastmarkets, LME, Bloomberg, etc.)
- `asset_id` / `ticker`: Provider-specific ticker symbol
- `Name` / `instrument_name`: Human-readable description
- `currency`: Quote currency (USD, EUR, etc.)
- `unit`: Measurement unit (USD/t, USD/lb, etc.)
- `Metal` / `material_hint`: Metal or material type

### Computed Columns

The loader adds these columns automatically:

- `instrument_id`: SHA1 hash of normalized `source|ticker` (16 chars)
- `ticker_norm`: Normalized ticker for fuzzy matching
- `name_norm`: Normalized name for fuzzy matching
- `material_id`: Resolved metal ID via `metal_identifier()`
- `cluster_id`: Supply chain cluster from resolved metal

## Integration with talquery

The module can leverage the `talquery` package for ticker data:

```python
# If talquery is available in parent directory
import sys
sys.path.append("../talquery")

from talquery.sources.ticker import TickerReference
ticker_ref = TickerReference()
df = ticker_ref.load()
```

## Testing

```bash
# Run unit tests
pytest tests/test_instruments.py

# Enable GCS tests (requires credentials)
ENTITYIDENTITY_TEST_GCS=1 pytest tests/test_instruments.py
```

## Example: Find Cobalt Instruments

```python
from entityidentity.instruments import load_instruments

df = load_instruments()

# Filter for cobalt instruments
cobalt = df[df["Metal"].str.contains("Cobalt", case=False, na=False)]
print(f"Found {len(cobalt)} cobalt instruments")

# Show tickers
for ticker in cobalt["asset_id"].values:
    print(f"  - {ticker}")
```

## Error Handling

The loader provides detailed error messages when data cannot be found:

```python
try:
    df = load_instruments()
except FileNotFoundError as e:
    print(e)
    # Shows all searched locations and how to fix
```

## Performance

- Initial load: ~100-500ms depending on source
- Subsequent calls: <1ms (cached)
- Memory usage: ~5-10MB for typical ticker reference data
- Metal resolution: Adds ~200-500ms on first load

## Future Enhancements

- [ ] Add `instrument_identifier()` API for text → instrument resolution
- [ ] Support for multiple ticker reference sources
- [ ] Batch metal resolution for better performance
- [ ] Support for historical ticker mappings
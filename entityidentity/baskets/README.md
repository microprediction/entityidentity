# Baskets Module

Entity resolution for commodity baskets - composite products made up of multiple metals or materials.

## Overview

The baskets module provides fast, in-memory resolution of basket names (e.g., "PGM 4E", "NdPr", "Battery Pack") to canonical basket entities with stable identifiers and component lists.

## Key Features

- **Fast In-Memory Resolution**: <100ms query latency via blocking strategy
- **Fuzzy Matching**: Handles variations, abbreviations, and typos (90% similarity threshold)
- **Stable Identifiers**: Deterministic `basket_id` generation via SHA-1 hashing
- **Component Tracking**: Each basket tracks constituent metals/materials

## Quick Start

```python
from entityidentity.baskets import basket_identifier, get_basket_components

# Resolve basket name
basket = basket_identifier("PGM 4E")
# Returns: {'basket_id': 'PGM_4E', 'name': 'PGM 4E', ...}

# Get component metals
components = get_basket_components("PGM 4E")
# Returns: ['Pt', 'Pd', 'Rh', 'Au']

# Fuzzy matching works
basket = basket_identifier("4e pgm")
# Returns: same PGM 4E basket

# Get top matches for disambiguation
from entityidentity.baskets import match_basket
matches = match_basket("pgm", k=3)
# Returns: [{'name': 'PGM 4E', 'score': 95, ...}, {'name': 'PGM 5E', 'score': 95, ...}]
```

## Available Baskets

Initial set of 5 baskets:

1. **PGM 4E**: Platinum, Palladium, Rhodium, Gold (traditional South African basket)
2. **PGM 5E**: PGM 4E + Iridium (higher-grade deposits)
3. **NdPr**: Neodymium-Praseodymium (rare earth magnet materials)
4. **REE Light**: Light rare earth elements (La, Ce, Pr, Nd)
5. **Battery Pack**: Li-ion battery metals (Li, Co, Ni, Mn, Graphite)

## API Reference

### `basket_identifier(name, *, threshold=90)`

Resolve basket name to canonical basket entity.

**Args:**
- `name` (str): Basket name or alias
- `threshold` (int): Minimum fuzzy match score (0-100)

**Returns:**
- `dict | None`: Basket entity with all fields, or None if no match

**Examples:**
```python
basket_identifier("PGM 4E")
basket_identifier("ndpr oxide")
basket_identifier("battery metals")
```

### `get_basket_components(name, *, threshold=90)`

Get list of component symbols for a basket.

**Args:**
- `name` (str): Basket name or alias
- `threshold` (int): Minimum fuzzy match score (0-100)

**Returns:**
- `list[str] | None`: Component symbols, or None if basket not found

**Examples:**
```python
get_basket_components("PGM 4E")
# Returns: ['Pt', 'Pd', 'Rh', 'Au']

get_basket_components("NdPr")
# Returns: ['Nd', 'Pr']
```

### `match_basket(name, *, k=5)`

Get top-K basket candidates with scores (for disambiguation UIs).

**Args:**
- `name` (str): Basket name or alias
- `k` (int): Number of top candidates to return

**Returns:**
- `list[dict]`: Basket entities with 'score' field (0-100), ordered by score

**Examples:**
```python
matches = match_basket("pgm", k=3)
for m in matches:
    print(f"{m['name']} - score: {m['score']}")
# Output:
# PGM 4E - score: 95.0
# PGM 5E - score: 95.0
```

### `list_baskets()`

List all available baskets.

**Returns:**
- `pd.DataFrame`: All basket entities

**Examples:**
```python
df = list_baskets()
print(df[['name', 'basket_id', 'description']])
```

## Data Schema

Each basket entity contains:

| Field | Type | Description |
|-------|------|-------------|
| `basket_id` | str | Unique identifier (e.g., "PGM_4E") |
| `basket_key` | str | URL-safe slug (e.g., "pgm-4e") |
| `name` | str | Canonical display name |
| `name_norm` | str | Normalized name for matching |
| `description` | str | Brief description of basket and uses |
| `alias1...alias10` | str | Alternative names |
| `component1...component10` | str | Constituent metals (format: "symbol" or "symbol:weight_pct") |

## Resolution Strategy

The module uses a 3-step blocking + scoring pipeline:

1. **Exact basket_id match**: If query looks like an ID (e.g., "PGM_4E")
2. **Prefix blocking**: First 3 chars of normalized name (reduces search space by ~99%)
3. **Fuzzy scoring**: RapidFuzz WRatio on name + aliases

This approach provides <100ms latency even as the basket database grows.

## Building the Database

```bash
# Generate baskets.parquet from baskets.yaml
cd entityidentity/baskets/data
python build_baskets.py
```

The build script:
- Loads `baskets.yaml` (source of truth)
- Generates deterministic `basket_id` for each basket
- Expands aliases into `alias1...alias10` columns
- Expands components into `component1...component10` columns
- Writes `baskets.parquet` for fast loading

## Adding New Baskets

Edit `entityidentity/baskets/data/baskets.yaml`:

```yaml
baskets:
  - basket_id: "MY_BASKET"
    name: "My Basket"
    aliases:
      - "Alternative Name 1"
      - "Alternative Name 2"
    components:
      - symbol: "Pt"
        weight_pct: 0.50  # 50% platinum
      - symbol: "Pd"
        weight_pct: 0.50  # 50% palladium
    description: "Brief description of the basket"
```

Then rebuild:
```bash
python entityidentity/baskets/data/build_baskets.py
```

## Testing

```bash
# Run basket tests
pytest tests/baskets/

# With coverage
pytest tests/baskets/ --cov=entityidentity.baskets

# Specific test file
pytest tests/baskets/test_basketapi.py -v
```

## Performance Characteristics

- **Database size**: ~5-50KB (5-50 baskets)
- **Load time**: <10ms (cached via `@lru_cache`)
- **Query latency**: <100ms (blocking reduces search space by ~99%)
- **Memory footprint**: <1MB

## Design Principles

1. **Simplicity**: Baskets are simpler than metals (no symbols, categories, clusters)
2. **Consistency**: Follows same patterns as metals module (blocking, scoring, API)
3. **Extensibility**: Easy to add new baskets via YAML
4. **Stability**: Deterministic IDs prevent drift across rebuilds

# Test Organization

This directory contains tests for EntityIdentity, organized by type and scope.

## Test Structure

```
tests/
├── test_smoke.py              # Quick smoke tests (imports, version)
├── test_api.py                # Integration tests for public API
├── test_metals.py             # Metal resolution tests
│
├── companies/
│   ├── test_normalization.py  # Unit tests for name normalization
│   ├── test_resolution.py     # Integration tests for company resolution
│   └── test_loaders.py        # Tests for data loaders (GLEIF, Wikidata, etc.)
│
└── countries/
    └── test_resolution.py     # Country resolution tests
```

## Test Categories

### 1. Smoke Tests (`test_smoke.py`)

Fast, lightweight tests that verify basic functionality:
- Package imports successfully
- Version is defined
- Primary API functions are callable

**When to run:** On every commit, in CI/CD

**Expected runtime:** <1 second

### 2. API Integration Tests (`test_api.py`)

Tests for the **public API** (`entityidentity/__init__.py`):
- `company_identifier()` - company resolution
- `country_identifier()` - country resolution
- `country_identifiers()` - batch country resolution
- Backwards compatibility (`get_identifier`)
- Multi-API integration

**When to run:** Before release, in CI/CD

**Expected runtime:** 1-5 seconds (depends on data availability)

**Note:** These tests gracefully skip if companies data is not available.

### 3. Unit Tests

#### Company Normalization (`companies/test_normalization.py`)

Tests for low-level normalization functions:
- `normalize_name()` - company name normalization
- `LEGAL_RE` - legal suffix regex patterns
- Edge cases (unicode, whitespace, punctuation)

**No data dependencies** - pure unit tests

**Expected runtime:** <1 second

#### Company Resolution (`companies/test_resolution.py`)

Integration tests for company resolution logic:
- Full resolution pipeline (`resolve_company`)
- Match confidence scoring
- Decision logic (auto_high_conf, needs_hint, etc.)
- Candidate ranking

**Requires:** Companies database

**Expected runtime:** 1-3 seconds

#### Data Loaders (`companies/test_loaders.py`)

Tests for data source loaders:
- GLEIF LEI loader
- Wikidata loader
- Stock exchange loaders (ASX, LSE, TSX)
- Sample data validation

**May require:** Live API access (controlled by `ENTITYIDENTITY_TEST_LIVE` env var)

**Expected runtime:** Variable (5-60 seconds if live APIs enabled)

### 4. Domain-Specific Tests

#### Metals (`test_metals.py`)

Tests for metal resolution and extraction:
- Metal name resolution
- Text extraction
- Metal pairs/combinations

#### Countries (`countries/test_resolution.py`)

Tests for country resolution:
- ISO code resolution
- Fuzzy matching
- Colloquial names

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
# Smoke tests only (fast)
pytest tests/test_smoke.py

# Public API tests
pytest tests/test_api.py

# Company-specific tests
pytest tests/companies/

# Unit tests only (no data dependencies)
pytest tests/companies/test_normalization.py
```

### Run with Coverage
```bash
pytest --cov=entityidentity --cov-report=html
```

### Run with Live API Tests
```bash
# Enable live API calls to GLEIF, Wikidata, etc.
ENTITYIDENTITY_TEST_LIVE=1 pytest tests/companies/test_loaders.py
```

## Test Markers

Tests can be marked with pytest markers:

```python
import pytest

@pytest.mark.unit
def test_normalization():
    """Pure unit test - no dependencies"""
    pass

@pytest.mark.integration
def test_resolution():
    """Integration test - requires database"""
    pass

@pytest.mark.slow
def test_live_api():
    """Slow test - live API calls"""
    pass
```

Run specific markers:
```bash
pytest -m unit        # Unit tests only
pytest -m integration # Integration tests
pytest -m "not slow"  # Skip slow tests
```

## Writing New Tests

### For Unit Tests (Pure Logic)
- Place in appropriate module (e.g., `test_normalization.py`)
- No database or API dependencies
- Fast (<100ms per test)
- Mark with `@pytest.mark.unit`

### For Integration Tests (With Data)
- Place in `test_api.py` for public API tests
- Place in `test_resolution.py` for internal resolution logic
- Use `pytest.skip()` if data unavailable:
  ```python
  try:
      result = resolve_company("Apple")
  except FileNotFoundError:
      pytest.skip("Companies data not available")
  ```
- Mark with `@pytest.mark.integration`

### For Live API Tests
- Place in `test_loaders.py`
- Gate behind `ENTITYIDENTITY_TEST_LIVE` environment variable
- Mark with `@pytest.mark.slow`
- Add reasonable timeouts

## Deprecated Test Files

- `test_basic.py` - **Merged into `test_smoke.py`** (removed duplicates)
- `companies/test_companyidentity.py` - **Split into `test_normalization.py` and `test_resolution.py`**

These files have been reorganized to avoid duplication and improve clarity.

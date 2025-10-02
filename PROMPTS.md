# Claude Code Prompts for EntityIdentity v0.2.0 Implementation

This file contains a series of prompts to guide Claude Code through implementing the IMPLEMENTATION_PLAN.md.

**Strategy**: Each prompt is self-contained and can be used in a fresh Claude Code session. They're ordered to build incrementally, with clear success criteria.

---

## STATUS UPDATE (2025-10-02)

**Phase 1 Progress**: 3 of 3 modules completed (100%) ✅

| Prompt | Module | Status | Notes |
|--------|--------|--------|-------|
| 1A-1B | Baskets | ✅ COMPLETED | 74 tests passing, README complete |
| 1C-1D | Period | ✅ COMPLETED | 52 tests passing (90% coverage), APIs exported |
| 1E | Places | ✅ COMPLETED | 52 of 55 tests passing, APIs exported, data built |

**Phase 1 Complete! ✅ Moving to Phase 2**

**Immediate Actions**:
1. ✅ ~~Baskets Module~~ - DONE (74 tests)
2. ✅ ~~Period Module~~ - DONE (52 tests, 90% coverage)
3. ✅ ~~Places Module~~ - DONE (52 of 55 tests passing)
4. ⏭️ **NEXT**: Execute Prompt 2A-2B (Units Module + Tests)
5. ⏭️ **THEN**: Execute Prompt 2C-2E (Instruments Module + Tests)

See [REPO_STATUS.md](REPO_STATUS.md) for detailed analysis.

---

## Phase 1: Foundation

### Prompt 1A: Baskets Module - Core Structure ✅ COMPLETED

**Status**: Implementation complete. See [entityidentity/baskets/](entityidentity/baskets/)

<details>
<summary>Original Prompt (click to expand)</summary>

```
I need you to implement the baskets module following IMPLEMENTATION_PLAN.md section B.2 (Baskets API).

Create the complete module structure:
- entityidentity/baskets/
  - __init__.py
  - basketapi.py
  - basketidentity.py
  - basketnormalize.py
  - data/baskets.yaml
  - data/build_baskets.py
  - README.md

Follow these exact patterns from the existing metals module:
1. API signatures match the spec in IMPLEMENTATION_PLAN.md
2. Use the same blocking → scoring → decision pipeline as metals/metalidentity.py
3. Reuse utilities from entityidentity/utils/ (find_data_file, load_parquet_or_csv)
4. Add @lru_cache to load_baskets() like load_metals()

Start with data/baskets.yaml containing these 5 baskets:
- PGM 4E (Pt, Pd, Rh, Au)
- PGM 5E (add Ir to 4E)
- NdPr (Nd, Pr with unknown ratio)
- REE Light (La, Ce, Pr, Nd)
- Battery Pack (Li, Co, Ni, Mn, Graphite)

Then implement the builder (build_baskets.py) that converts YAML → baskets.parquet.

Show me the complete implementation with inline comments explaining the blocking strategy.
```

**Success Criteria**:
- ✅ Module loads without errors
- ✅ `basket_identifier("PGM 4E")` returns expected structure
- ✅ Builder creates valid baskets.parquet
```

</details>

---

### Prompt 1B: Baskets Module - Tests ✅ COMPLETED

**Status**: 74 tests implemented and passing. See [tests/baskets/](tests/baskets/)

<details>
<summary>Original Prompt (click to expand)</summary>

```
Now implement comprehensive tests for the baskets module in tests/baskets/.

Create:
- tests/baskets/test_basketapi.py
- tests/baskets/test_normalization.py

Follow the test structure from tests/test_metals.py. Include these test cases:

test_basketapi.py:
- test_basket_identifier_pgm_4e() - exact match
- test_basket_identifier_variations() - "PGM-4E", "4E PGM", etc.
- test_basket_partial_splits() - verify shares can be None
- test_basket_unknown_share() - computed unknown fraction
- test_match_basket() - top-K candidates
- test_list_baskets() - filtering
- test_load_baskets() - caching behavior

test_normalization.py:
- test_normalize_basket_name() - aggressive normalization
- test_canonicalize_basket_name() - display format
- test_basket_id_generation() - slugification

Run pytest and show me the coverage report for the baskets module.
```

**Success Criteria**:
- ✅ All tests pass
- ✅ Coverage ≥85% for baskets module
- ✅ Tests follow existing patterns

</details>

---

### Prompt 1C: Period Module - Complete Implementation ✅ COMPLETED

**Status**: Implementation complete. See [entityidentity/period/](entityidentity/period/)

<details>
<summary>Original Prompt (click to expand)</summary>

```
Implement the period module following IMPLEMENTATION_PLAN.md section B.3 (Period API).

Create:
- entityidentity/period/
  - __init__.py
  - periodapi.py (period_identifier, extract_periods)
  - periodidentity.py (core resolver)
  - periodnormalize.py (text normalization)
  - README.md

Key requirements:
1. Support these period types: year, half, quarter, month, week, date_range
2. H1/H2 remain as single "half" periods (don't auto-expand to quarters)
3. ISO weeks start on Monday (use isoweek library)
4. Relative periods ("last quarter") use asof_ts parameter
5. Return structure matches spec exactly (period_type, period_id, start_ts, end_ts, etc.)

Use python-dateutil for parsing and isoweek for ISO week handling.

Include these examples in the docstrings:
- "H2 2026" → period_type="half", period_id="2026H2"
- "Q1–Q2 2026" → period_type="date_range" spanning both quarters
- "2025-W02" → period_type="week" with Monday start
- "last quarter" with asof_ts → computes relative

Show me the implementation with comprehensive inline comments.
```

**Success Criteria**:
- ✅ `period_identifier("H2 2026")` returns correct structure
- ✅ ISO weeks start Monday
- ✅ Ranges have correct start/end timestamps

</details>

---

### Prompt 1D: Period Module - Tests ✅ COMPLETED

**Status**: 52 tests implemented and passing (90% coverage)

<details>
<summary>Original Prompt (click to expand)</summary>

```
Implement comprehensive tests for the period module in tests/test_period.py.

Include at least 20 test cases covering:

Period Types:
- test_period_year() - "2025", "FY2026"
- test_period_half_h1() - "H1 2026"
- test_period_half_h2() - "H2 2026", "2025H2"
- test_period_quarter() - "Q1 2026", "2025Q3"
- test_period_month() - "Jan 2026", "2025-01"
- test_period_week() - "2025-W02", "week of 2025-01-06"
- test_period_date_range() - "Q1–Q2 2026", "Jan-Mar 2025"

Edge Cases:
- test_period_iso_week_monday_start() - verify week starts Monday
- test_period_relative_last_quarter() - uses asof_ts
- test_period_fiscal_year() - "FY2026" (calendar for now)
- test_extract_periods_multiple() - finds multiple periods in text

Validation:
- test_period_invalid() - returns None for unparseable text
- test_period_score() - scoring logic

Run pytest and show me results with coverage.
```

**Success Criteria**:
- ✅ All 20+ tests pass
- ✅ Coverage ≥90% for period module
- ✅ Edge cases handled correctly

</details>

---

### Prompt 1E: Places Module - Implementation ✅ COMPLETED

**Status**: Implementation complete with 52 of 55 tests passing. APIs exported.

```
Implement the places module following IMPLEMENTATION_PLAN.md section B.4 (Places API).

Create:
- entityidentity/places/
  - __init__.py
  - placeapi.py (place_identifier, extract_location, list_places, load_places)
  - placeidentity.py (admin1 matching with country blocking)
  - placenormalize.py (normalization helpers)
  - data/build_admin1.py (GeoNames → Parquet builder)
  - README.md

Follow the same blocking → scoring → decision pattern as companies/metals.

Blocking strategy:
1. Extract country via country_identifier() (reuse existing)
2. Filter admin1 by country if found (5000 → ~50 per country)
3. Prefix match on admin1_name + aliases
4. RapidFuzz WRatio scoring

Data source (per DATA_SOURCES.md):
- Download GeoNames admin1CodesASCII.txt from https://download.geonames.org/export/dump/
- Parse tab-separated format: country.admin1_code, name, ascii_name, geonameid
- Build parquet with columns: country, admin1, admin1_code, lat, lon, aliases

Example usage:
```python
from entityidentity.places import place_identifier

# Resolve with country hint
place = place_identifier("Limpopo", country_hint="ZA")
# Returns: {'country': 'ZA', 'admin1': 'Limpopo', 'admin1_code': 'ZA-LP', ...}

# Resolve without hint (tries all countries)
place = place_identifier("Western Australia")
# Returns: {'country': 'AU', 'admin1': 'Western Australia', 'admin1_code': 'AU-WA', ...}
```

Success Criteria:
- ✅ place_identifier("Limpopo", country_hint="ZA") works
- ✅ Country blocking reduces search space 99%+
- ✅ admin1.parquet built from GeoNames data
```

---

## Phase 2: Conversion & Ground Truth

### Prompt 2A: Units Module - Implementation ⏭️ TODO

```
Implement the units module following IMPLEMENTATION_PLAN.md section B.4 (Units API).

Create:
- entityidentity/units/
  - __init__.py
  - unitapi.py (normalize_unit)
  - unitnorm.py (conversion logic)
  - unitconfig.yaml (metal-specific rules)
  - README.md

Key requirements:
1. Normalize value/unit/basis to canonical forms
2. Convert when safe (have all required parameters)
3. Warn when conversion impossible (missing grade, ambiguous ton system)
4. Always preserve raw input in response
5. Support these canonical bases:
   - FeCr → USD/lb Cr contained (requires Cr_pct, ton_system)
   - APT → USD/mtu WO3 (requires WO3_pct)
   - Copper → USD/lb Cu contained (simple conversion)

Return structure: {"raw": {...}, "norm": {...}, "warning": Optional[str]}

Never guess missing parameters - always warn instead.

Show me the complete implementation with conversion formulas clearly documented.
```

**Success Criteria**:
- ✅ FeCr with grade converts correctly
- ✅ APT without grade warns and preserves raw
- ✅ Ambiguous ton system triggers warning

---

### Prompt 2B: Units Module - Tests

```
Implement comprehensive tests for the units module in tests/test_units.py.

Include at least 14 test cases covering:

Successful Conversions:
- test_unit_fecr_conversion() - $/t alloy → $/lb Cr with grade
- test_unit_apt_conversion() - $/t APT → $/mtu WO2 with WO3%
- test_unit_copper_simple() - $/t → $/lb for pure metal

Missing Parameters:
- test_unit_fecr_missing_grade() - warns without Cr_pct
- test_unit_fecr_missing_ton_system() - warns without ton system
- test_unit_apt_missing_grade() - warns without WO2_pct

Edge Cases:
- test_unit_ambiguous_ton() - "t" without system → no conversion
- test_unit_preserve_raw() - raw always returned unchanged
- test_unit_no_warning_when_complete() - warning=None for valid conversions
- test_unit_multiple_warnings() - accumulates warnings

Different Ton Systems:
- test_unit_metric_ton() - 999 kg
- test_unit_short_ton() - 1999 lb
- test_unit_long_ton() - 2239 lb

Run pytest and show coverage.
```

**Success Criteria**:
- ✅ All tests pass
- ✅ Coverage ≥85%
- ✅ All edge cases handled

---

### Prompt 2C: Instruments Module - Data Loading

```
Implement the instruments data loader following IMPLEMENTATION_PLAN.md section B.6 (Instruments API).

Create:
- entityidentity/instruments/
  - __init__.py
  - instrumentloaders.py (GCS + local loading)

Requirements:
1. Load from gs://gsmc-market-data/ticker_references.parquet by default
2. Support local override via env var GSMC_TICKERS_PATH
3. Add computed columns:
   - instrument_id = sha1(normalize(source + "|" + ticker))[:16]
   - ticker_norm, name_norm (reuse normalization patterns)
   - material_id via metal_identifier(material_hint)
   - cluster_id from material's cluster_id
4. Use @lru_cache for session persistence
5. Fallback to find_data_file() for dev tables

Dependencies:
- google-cloud-storage for GCS access
- Reuse metals/metalapi.py for material crosswalk

Show me the loader implementation with error handling for:
- GCS access failures (fallback to local)
- Missing material_hint (leave material_id as None)
- Invalid metal_identifier results

Test with a small sample file first before attempting GCS.
```

**Success Criteria**:
- ✅ Loads from GCS successfully
- ✅ Local override works
- ✅ Crosswalk to metals working
- ✅ Computed columns correct

---

### Prompt 2D: Instruments Module - Resolution & API

```
Implement the instruments resolution engine and public API.

Create:
- entityidentity/instruments/instrumentapi.py
- entityidentity/instruments/instrumentidentity.py

Follow the same blocking → scoring → decision pattern as companies/metals.

Blocking strategy:
1. Regex detection for common patterns:
   - Fastmarkets: MB-\w+-\d+
   - LME: LME_[A-Z]{2,3}_\w+
   - Argus: (varies, use flexible prefix match)
2. Optional source_hint to filter/boost provider
3. Prefix match on ticker_norm
4. Fuzzy match on name_norm

Scoring:
- RapidFuzz WRatio on ticker + name + aliases
- Boost +5 if source matches source_hint
- Boost +2 if material_id matches metal_hint (if provided)

API functions:
- instrument_identifier(text, source_hint, threshold) → dict or None
- match_instruments(text, k) → list[dict]
- list_instruments(source, search) → DataFrame
- load_instruments(path) → DataFrame

Return structure matches IMPLEMENTATION_PLAN.md section B.6.

Show me the complete implementation.
```

**Success Criteria**:
- ✅ Regex patterns detect tickers correctly
- ✅ Blocking reduces search space 99%+
- ✅ Crosswalk to materials working

---

### Prompt 2E: Instruments Module - Tests

```
Implement tests for instruments in tests/test_instruments.py.

Include at least 12 test cases:

Ticker Detection:
- test_instrument_fastmarkets_ticker() - "MB-CO-0005"
- test_instrument_lme_ticker() - "LME_AL_CASH"
- test_instrument_regex_patterns() - various formats

Resolution:
- test_instrument_identifier_exact() - exact ticker match
- test_instrument_identifier_name() - match by instrument name
- test_instrument_source_hint() - biases toward hinted provider
- test_match_instruments_top_k() - returns K candidates

Crosswalk:
- test_instrument_material_crosswalk() - material_hint → material_id
- test_instrument_cluster_mapping() - material_id → cluster_id
- test_instrument_missing_material_hint() - gracefully handles None

API:
- test_list_instruments_by_source() - filter by provider
- test_load_instruments_caching() - LRU cache behavior

If GCS access fails in tests, use @pytest.mark.skipif with clear reason.

Run pytest and show coverage.
```

**Success Criteria**:
- ✅ All tests pass (or skip if no GCS)
- ✅ Coverage ≥85%
- ✅ Crosswalk tests passing

---

## Phase 3: Facilities (Optional)

### Prompt 3A: Facilities Module - Stub Implementation

```
Implement a stub facilities module that works without a facilities master table.

Create:
- entityidentity/facilities/
  - __init__.py
  - facilityapi.py (link_facility)
  - facilitylink.py (linker logic)
  - README.md

Stub behavior:
1. Check if facilities master exists (via env ENTITYIDENTITY_FACILITIES_PATH)
2. If NOT exists:
   - Fall back to company_identifier only
   - Return {"facility_id": None, "company_id": "...", "link_score": 0, "features": {}, "warning": "No facilities master available"}
3. If exists:
   - Implement full probabilistic linking per IMPLEMENTATION_PLAN.md section B.6

The stub should:
- Accept all parameters (company_hint, place_hint, metal_hint, process_stage_hint)
- Always resolve company_hint via company_identifier
- Return structured response matching spec
- Be ready to swap in full implementation when data available

Show me the stub implementation with clear TODOs for full version.
```

**Success Criteria**:
- ✅ Stub loads without errors
- ✅ Returns company fallback correctly
- ✅ API matches spec

---

### Prompt 3B: Facilities Module - Tests (Skip Pattern)

```
Implement tests for facilities in tests/test_facilities.py.

Use pytest.mark.skipif pattern to skip when no facilities master:

import os
import pytest

FACILITIES_AVAILABLE = os.path.exists(
    os.getenv("ENTITYIDENTITY_FACILITIES_PATH", "/nonexistent")
)

@pytest.mark.skipif(not FACILITIES_AVAILABLE, reason="No facilities master")
def test_facility_link_full():
    # Full linking tests when data available
    pass

def test_facility_link_company_fallback():
    # This should always work (stub behavior)
    result = link_facility(company_hint="BHP")
    assert result['company_id'] is not None
    # If no facilities data:
    if not FACILITIES_AVAILABLE:
        assert result['facility_id'] is None
        assert result['link_score'] == 0

Include these test cases (skip appropriately):
- test_facility_link_full() - full blocking/scoring
- test_facility_link_company_fallback() - stub behavior
- test_facility_link_geo_distance() - haversine calculation
- test_facility_link_features() - feature scoring breakdown
- test_facility_link_threshold() - confidence filtering

Run pytest and show which tests run vs skip.
```

**Success Criteria**:
- ✅ Tests pass in stub mode
- ✅ Skip markers work correctly
- ✅ Ready for full implementation

---

## Phase 4: Integration

### Prompt 4A: Package Integration

```
Integrate all new modules into the main package.

Update entityidentity/__init__.py:
1. Add imports for all 5 new modules
2. Update __all__ exports
3. Maintain backwards compatibility (no changes to existing exports)
4. Organize imports by entity type with clear comments
5. Update version to "0.2.0"

Follow the exact structure shown in IMPLEMENTATION_PLAN.md section F.

Then verify:
- All imports work: python -c "from entityidentity import basket_identifier, period_identifier, instrument_identifier, normalize_unit, link_facility"
- No circular dependencies
- Backwards compat: python -c "from entityidentity import company_identifier, metal_identifier; print(company_identifier('Apple'))"

Show me the updated __init__.py with organized sections.
```

**Success Criteria**:
- ✅ All imports work
- ✅ No breaking changes
- ✅ Clean organization

---

### Prompt 4B: Update Main README

```
Update README.md to include the new entities while keeping the existing structure.

Changes needed:
1. Update opening description to mention all 6 entity types (companies, countries, metals, baskets, periods, instruments)
2. Add Quick Start examples for new entities (keep it brief, 1-2 lines each)
3. Expand Complete API Reference section to include:
   - Basket Resolution (subsection)
   - Period Normalization (subsection)
   - Unit Normalization (subsection)
   - Instrument Resolution (subsection)
   - Facility Linking (subsection)
4. Update Table of Contents
5. Add "Resolution Precedence" section (from IMPLEMENTATION_PLAN.md section G)
6. Keep all existing content intact

Follow the current README style (concise, lots of code examples, clear sections).

Show me the updated sections you'll add (not the whole file, just the new parts).
```

**Success Criteria**:
- ✅ All new entities documented
- ✅ Quick Start stays concise
- ✅ API reference comprehensive

---

### Prompt 4C: Update CLAUDE.md

```
Update CLAUDE.md to include architecture details for the new modules.

Add sections for:
1. Baskets module structure (data/, YAML → Parquet pipeline)
2. Period module (pure resolver, no data table)
3. Units module (config.yaml, conversion formulas)
4. Instruments module (GCS loading, crosswalk to metals)
5. Facilities module (stub vs full implementation)

Follow the existing CLAUDE.md style (developer-focused, internal details, architecture decisions).

Include:
- File structure for each module
- Key design decisions
- Testing strategy
- Known limitations

Show me the new sections to add.
```

**Success Criteria**:
- ✅ Developer documentation complete
- ✅ Architecture explained
- ✅ Matches existing style

---

### Prompt 4D: Integration Tests

```
Create comprehensive integration tests that exercise multiple modules together.

In tests/test_integration.py, implement:

test_workflow_news_extraction():
    """Test extracting all entities from news article."""
    text = '''
    Anglo American's Mogalakwena mine in Limpopo province reported
    PGM 4E production of 450,000 oz in H2 2026. Fastmarkets assessed
    MB-CO-0005 at USD 15.50/lb.
    '''

    # Extract companies
    companies = extract_companies(text)
    assert len(companies) > 0

    # Resolve basket
    basket = basket_identifier("PGM 4E")
    assert basket is not None

    # Extract periods
    periods = extract_periods(text)
    assert any(p['period_id'] == '2026H2' for p in periods)

    # Resolve instrument
    inst = instrument_identifier("MB-CO-0005")
    assert inst is not None
    assert inst['material_id'] == 'Co'

test_workflow_structured_data():
    """Test building structured record from messy input."""
    # Similar to example in IMPLEMENTATION_PLAN.md section M

test_resolution_precedence():
    """Test that instruments take precedence over metals."""
    # Query both, verify instrument preferred

test_end_to_end_pipeline():
    """Test complete entity resolution pipeline."""
    # Extract → Resolve → Normalize → Link

Run these tests and verify all modules work together correctly.
```

**Success Criteria**:
- ✅ All integration tests pass
- ✅ Modules interact correctly
- ✅ Precedence rules work

---

### Prompt 4E: Performance Benchmarks

```
Create performance benchmarks to verify <100ms target.

In tests/test_performance.py, implement:

import time
import pytest

def test_basket_resolution_speed():
    """Baskets should resolve in <100ms."""
    start = time.time()
    for _ in range(100):
        basket_identifier("PGM 4E")
    elapsed = (time.time() - start) / 100
    assert elapsed < 0.1, f"Average query time: {elapsed*1000:.1f}ms"

def test_period_resolution_speed():
    """Periods should resolve in <50ms (pure computation)."""
    # Similar benchmark

def test_instrument_resolution_speed():
    """Instruments should resolve in <100ms."""
    # Benchmark with warm cache

def test_unit_normalization_speed():
    """Units should normalize in <10ms (pure computation)."""
    # Benchmark conversions

def test_facility_linking_speed():
    """Facilities should link in <200ms (more complex)."""
    # Benchmark if data available

Run benchmarks and report:
- Average query time for each entity type
- Memory usage after loading all modules
- Cache effectiveness (first vs subsequent queries)

Show me the results.
```

**Success Criteria**:
- ✅ All queries <100ms (warm cache)
- ✅ Memory <500MB total
- ✅ Cache working effectively

---

### Prompt 4F: Final Documentation

```
Create final documentation artifacts:

1. MIGRATION.md - v0.1 → v0.2 upgrade guide
   - Backwards compatibility guarantees
   - New capabilities overview
   - Import changes (none, all additive)
   - Example migration scenarios

2. CHANGELOG.md - v0.2.0 release notes
   - New features (5 entity types)
   - API additions
   - Dependencies added
   - Performance improvements
   - Known limitations

3. Update each module's README.md with:
   - Quick start examples
   - API reference
   - Data sources
   - Testing instructions

Follow conventional changelog format and keep tone consistent with existing docs.

Show me the MIGRATION.md and CHANGELOG.md content.
```

**Success Criteria**:
- ✅ Migration guide clear
- ✅ Changelog comprehensive
- ✅ All modules documented

---

## Bonus: Interactive Verification Prompts

### Verification 1: Smoke Test

```
Run a comprehensive smoke test to verify everything works.

Create tests/test_v02_smoke.py:

def test_all_imports():
    """Verify all new imports work."""
    from entityidentity import (
        basket_identifier, match_basket, list_baskets,
        period_identifier, extract_periods,
        normalize_unit,
        instrument_identifier, match_instruments, list_instruments,
        link_facility
    )

def test_all_primary_apis():
    """Quick test of each primary API."""
    assert basket_identifier("PGM 4E") is not None
    assert period_identifier("H2 2026") is not None
    assert normalize_unit({"value": 100, "unit": "USD/lb"}) is not None
    # instrument_identifier may fail without data
    # link_facility returns company fallback

def test_backwards_compatibility():
    """Verify v0.1 APIs unchanged."""
    from entityidentity import company_identifier, metal_identifier, country_identifier
    assert company_identifier("Apple") == "Apple Inc:US"
    assert metal_identifier("lithium") is not None
    assert country_identifier("USA") == "US"

Run this and show me the results.
```

---

### Verification 2: Test Coverage Report

```
Generate a comprehensive test coverage report for all new modules.

Run:
pytest --cov=entityidentity.baskets \
       --cov=entityidentity.period \
       --cov=entityidentity.units \
       --cov=entityidentity.instruments \
       --cov=entityidentity.facilities \
       --cov-report=term-missing \
       --cov-report=html

Then show me:
1. Coverage % for each module
2. Any uncovered lines
3. Total line count added
4. Total test count

Target: ≥85% coverage for all modules.
```

---

## How to Use These Prompts

### Strategy 1: Sequential Execution
Work through prompts in order, one session per prompt. Each builds on the previous.

**Pros**: Clean separation, easy to debug
**Cons**: ~20 sessions total

---

### Strategy 2: Grouped Sessions
Combine related prompts in single sessions:

**Session 1**: Prompts 1A + 1B (Baskets module + tests)
**Session 2**: Prompts 1C + 1D (Period module + tests)
**Session 3**: Prompts 2A + 2B (Units module + tests)
**Session 4**: Prompts 2C + 2D + 2E (Instruments module + tests)
**Session 5**: Prompts 3A + 3B (Facilities stub + tests)
**Session 6**: Prompts 4A + 4B + 4C (Integration + docs)
**Session 7**: Prompts 4D + 4E + 4F (Final tests + docs)
**Session 8**: Verification prompts

**Pros**: Fewer sessions (~8 total)
**Cons**: Longer sessions, more context

---

### Strategy 3: Iterative with Checkpoints

After each major prompt, run verification:
```
Quick checkpoint: Run pytest on just the module we added. Show me any failures.
```

Fix issues before moving to next prompt.

**Pros**: Catch issues early
**Cons**: More back-and-forth

---

## Success Checklist

After completing all prompts, verify:

- [ ] All 5 modules implemented (baskets, period, units, instruments, facilities)
- [ ] 100+ new tests passing
- [ ] Coverage ≥85% for all new modules
- [ ] Integration tests passing
- [ ] Performance benchmarks <100ms
- [ ] Documentation complete (README, CLAUDE.md, MIGRATION.md)
- [ ] Backwards compatibility verified
- [ ] Package version bumped to 0.2.0
- [ ] All prompts executed successfully

---

## Troubleshooting Common Issues

### Issue: "Module import failed"
**Prompt**: "Debug the import error. Check circular dependencies and __init__.py exports."

### Issue: "Tests failing due to missing data"
**Prompt**: "Add pytest.mark.skipif decorators for tests requiring external data. Follow the pattern in tests/conftest.py."

### Issue: "Performance benchmark failing"
**Prompt**: "Profile the slow function. Add @lru_cache if missing. Show me the flamegraph."

### Issue: "Coverage below 85%"
**Prompt**: "Show me uncovered lines. Write targeted tests for the missing coverage."

---

## End of Prompts Guide

**Recommended Approach**: Start with Strategy 2 (grouped sessions), use checkpoints after each module.

**Estimated Time**: 2-3 days of focused work across 8 sessions.

**Questions?** Start with Prompt 1A and see how it goes!

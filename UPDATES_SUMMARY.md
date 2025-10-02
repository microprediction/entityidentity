# EntityIdentity v0.2.0 Plan Updates - Places Module Added

**Date**: 2025-10-02
**Changes**: Added `places/` module to resolve geographic locations (admin1 states/provinces)

---

## What Changed

### 1. Entity Count: 5 → 6 Modules

**Before**:
1. Baskets
2. Periods
3. Units
4. Instruments
5. Facilities

**After**:
1. Baskets
2. Periods
3. **Places** ← NEW
4. Units
5. Instruments
6. Facilities

---

## Why Add Places?

### Problem Identified
The facilities module requires `place_hint` parameter:
```python
link_facility(
    company_hint="Anglo American",
    place_hint={"country": "ZA", "admin1": "Limpopo"},  # ← How do we get this?
    metal_hint="PGM"
)
```

**Without places module**: No way to extract `admin1` (state/province) from text
- ✅ Have: `country_identifier()` for countries
- ❌ Missing: Admin1 resolver for states/provinces

### Solution: Places Module

Resolves geographic locations at **admin1** granularity (states, provinces, territories):

```python
# Resolve place name
place_identifier("Limpopo", country_hint="ZA")
# → {"country": "ZA", "admin1": "Limpopo", "admin1_code": "ZA-LP", "lat": -24.0, "lon": 29.5}

# Extract from text
extract_location("Anglo American's mine in Limpopo province, South Africa")
# → {"country": "ZA", "admin1": "Limpopo", "mentions": ["Limpopo province", "South Africa"], ...}
```

---

## What Was Added

### IMPLEMENTATION_PLAN.md

#### Updated Sections:
1. **Executive Summary** - 5 → 6 entities
2. **Repository Structure** - Added `places/` directory
3. **Public APIs (Section B.4)** - Complete Places API specification
4. **Testing Strategy** - Added places tests (Section D.3)
5. **Data Contracts** - Added admin1.parquet schema (Section E.2)
6. **Package Integration** - Added places exports (Section F)
7. **Roadmap** - Added PR #3 for places module (Phase 1, Week 1-2)
8. **Success Criteria** - 100+ → 120+ tests
9. **Example Workflows** - Integrated extract_location() calls

#### New Content:

**Places API** (IMPLEMENTATION_PLAN.md lines 265-423):
- `place_identifier(name, country_hint, threshold)` → Resolve admin1
- `extract_location(text)` → Extract country + admin1 from text
- `list_places(country, search)` → Browse admin1 database
- `load_places(path)` → Load admin1 data

**Data Schema** (admin1.parquet):
```
country: str              # ISO2
admin1_name: str          # "Limpopo", "California"
admin1_code: str          # ISO 3166-2 (ZA-LP, US-CA)
alias1-3: str             # "WA", "West Aus"
lat/lon: float            # Centroid
population/area_km2       # Optional metadata
```

**Coverage**: ~5000 admin1 regions worldwide
**Data Size**: ~500KB parquet

---

### PROMPTS.md

#### Added Prompts:

**Prompt 1E: Places Module - Implementation**
- Create complete `places/` module structure
- Implement blocking → scoring → decision pipeline
- Build admin1.parquet from Natural Earth data
- ~100 regions sample for testing

**Prompt 1F: Places Module - Tests**
- 15+ test cases
- Coverage targets ≥85%
- Tests for abbreviations, fuzzy matching, extraction

#### Updated Workflow:
- **Phase 1**: Now includes 3 PRs (Baskets, Period, **Places**)
- **Week 1-2**: Complete foundation modules
- **Estimated sessions**: 8 → 9 total (added 1 for places)

---

## Technical Details

### Blocking Strategy (99%+ reduction)

```
Input: "Limpopo"
5000 admin1 regions globally

Stage 1: Extract country via country_identifier
  If country_hint="ZA" provided, filter immediately
  5000 → 9 (SA provinces only)

Stage 2: Prefix match on normalized name
  "lim*" matches "limpopo"
  9 → 1 candidate

Stage 3: Fuzzy scoring
  RapidFuzz WRatio: "limpopo" vs "limpopo" = 100

Return: {"country": "ZA", "admin1": "Limpopo", ...}
```

### Integration with Existing Modules

**Countries Module** (no changes):
- `country_identifier()` still handles countries
- Places uses it for country extraction

**Facilities Module** (enhanced):
```python
# Before (manual dict construction)
place_hint = {"country": "ZA", "admin1": "Limpopo"}

# After (automated extraction)
place_hint = extract_location(text)
facility = link_facility(company_hint="Anglo", place_hint=place_hint, ...)
```

---

## Files Modified

### 1. IMPLEMENTATION_PLAN.md
- **Lines changed**: ~200 additions
- **Sections updated**: 9
- **New API section**: B.4 Places API (159 lines)

### 2. PROMPTS.md
- **Lines changed**: ~85 additions
- **New prompts**: 2 (1E, 1F)
- **Roadmap update**: Phase 1 now has 3 modules

### 3. Created Files
- `UPDATES_SUMMARY.md` (this file)

---

## Updated Roadmap

### Phase 1: Foundation (Week 1-2) - NOW 3 MODULES

**PR #1: Baskets** (unchanged)
**PR #2: Period** (unchanged)
**PR #3: Places** ← NEW
- Create `entityidentity/places/` structure
- Implement `placeapi.py`, `placeidentity.py`, `placenormalize.py`
- Build `data/admin1.parquet` from Natural Earth
- Add tests: `tests/test_places.py` (15+ cases)
- Update package exports
- Update README

### Phase 2-4: Unchanged
- PR #4: Units (was PR #3)
- PR #5: Instruments (was PR #4)
- PR #6: Facilities (was PR #5)
- PR #7: Integration (was PR #6)

---

## Success Metrics Updated

| Metric | Before | After |
|--------|--------|-------|
| New entity modules | 5 | **6** |
| Total new tests | 100+ | **120+** |
| Phase 1 PRs | 2 | **3** |
| Data files | 3 | **4** (added admin1.parquet) |
| Primary APIs | 5 | **6** (added place_identifier) |

---

## Next Steps

### To Implement Places Module:

1. **Use Prompt 1E** from PROMPTS.md
   - Creates full module structure
   - Implements blocking/scoring pipeline
   - Builds sample admin1 data

2. **Use Prompt 1F** from PROMPTS.md
   - Comprehensive tests
   - Validates all functionality

3. **Verify Integration**
   - Test with facilities module
   - Ensure `extract_location()` works in workflows

### Estimated Effort:
- **Implementation**: 1 session (~2-3 hours)
- **Testing**: 1 session (~1-2 hours)
- **Total**: ~4-5 hours for complete places module

---

## Benefits

### 1. Completeness
- ✅ No missing pieces for facilities linking
- ✅ Full geographic resolution (country + admin1)
- ✅ Handles all major mining regions worldwide

### 2. Consistency
- ✅ Follows exact same patterns as metals/companies
- ✅ Same blocking → scoring → decision pipeline
- ✅ Same API style (identifier, match, list, load)

### 3. Utility
- ✅ Powers facilities module
- ✅ Useful standalone (geocoding for free)
- ✅ Small data footprint (~500KB)

---

## Questions & Decisions

### Q: Why admin1 only? What about cities?
**A**: Admin1 (states/provinces) is sufficient for mining facility resolution. Cities would add:
- 10x more data (~50K cities vs 5K admin1)
- More ambiguity (many duplicate city names)
- Diminishing returns for mining use case

Can add city support in v0.3.0 if needed.

### Q: Which data source for admin1?
**A**: Natural Earth admin1 boundaries (free, well-maintained)
- Alternative: GeoNames admin1 (more detailed, similar coverage)
- Decision: Start with Natural Earth, can switch to GeoNames later

### Q: Should we add lat/lon geocoding?
**A**: Yes, for centroid only (simpler than full geocoding)
- Enables haversine distance in facilities module
- No external API dependency (stored in parquet)

---

## Appendix: Example Usage

### Standalone Use
```python
from entityidentity import place_identifier, extract_location

# Resolve place name
place = place_identifier("Limpopo", country_hint="ZA")
# → {"country": "ZA", "admin1": "Limpopo", "lat": -24.0, "lon": 29.5}

# Extract from text
text = "BHP's operations in Western Australia expanded in Q2"
location = extract_location(text)
# → {"country": "AU", "admin1": "Western Australia", "admin1_code": "AU-WA"}
```

### Integrated Workflow
```python
from entityidentity import extract_companies, extract_location, link_facility

text = "Anglo American's Mogalakwena mine in Limpopo province"

company = extract_companies(text)[0]  # → "Anglo American Platinum Limited:ZA"
location = extract_location(text)     # → {"country": "ZA", "admin1": "Limpopo"}

facility = link_facility(
    company_hint=company['name'],
    place_hint=location,  # ← Uses places module output directly
    metal_hint="PGM"
)
# → {"facility_id": "mogalakwena_001", "link_score": 92}
```

---

**End of Updates Summary**

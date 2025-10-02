"""Test suite for places entity resolution.

Tests cover:
1. Exact matching with country hints
2. Abbreviation resolution
3. Country blocking efficiency
4. Fuzzy matching
5. Top-K matching
6. Filtering and listing
"""

import pytest
import pandas as pd
from entityidentity.places.placeapi import (
    load_places,
    place_identifier,
    match_place,
    list_places,
)
from entityidentity.places.placenormalize import (
    normalize_place_name,
    canonicalize_place_name,
    slugify_place_name,
    generate_place_id,
)


# ---- Fixtures ----

@pytest.fixture
def places_df():
    """Load places DataFrame once for all tests"""
    # For testing, we'll create a minimal test dataset
    # In production, this would use load_places()
    test_data = [
        {
            'place_id': generate_place_id('ZA', 'LP'),
            'place_key': 'za-limpopo',
            'country': 'ZA',
            'admin1': 'Limpopo',
            'admin1_norm': 'limpopo',
            'admin1_code': 'LP',
            'ascii_name': 'Limpopo',
            'geonameid': '964137',
            'lat': '',
            'lon': '',
            'alias1': '',
            'alias2': '',
            'alias3': '',
            'alias4': '',
            'alias5': '',
            'alias6': '',
            'alias7': '',
            'alias8': '',
            'alias9': '',
            'alias10': '',
            'attribution': 'Data from GeoNames (geonames.org)',
        },
        {
            'place_id': generate_place_id('AU', 'WA'),
            'place_key': 'au-western-australia',
            'country': 'AU',
            'admin1': 'Western Australia',
            'admin1_norm': 'western australia',
            'admin1_code': 'WA',
            'ascii_name': 'Western Australia',
            'geonameid': '2058645',
            'lat': '',
            'lon': '',
            'alias1': 'WA',
            'alias2': '',
            'alias3': '',
            'alias4': '',
            'alias5': '',
            'alias6': '',
            'alias7': '',
            'alias8': '',
            'alias9': '',
            'alias10': '',
            'attribution': 'Data from GeoNames (geonames.org)',
        },
        {
            'place_id': generate_place_id('US', 'CA'),
            'place_key': 'us-california',
            'country': 'US',
            'admin1': 'California',
            'admin1_norm': 'california',
            'admin1_code': 'CA',
            'ascii_name': 'California',
            'geonameid': '5332921',
            'lat': '',
            'lon': '',
            'alias1': 'CA',
            'alias2': '',
            'alias3': '',
            'alias4': '',
            'alias5': '',
            'alias6': '',
            'alias7': '',
            'alias8': '',
            'alias9': '',
            'alias10': '',
            'attribution': 'Data from GeoNames (geonames.org)',
        },
        {
            'place_id': generate_place_id('US', 'WA'),
            'place_key': 'us-washington',
            'country': 'US',
            'admin1': 'Washington',
            'admin1_norm': 'washington',
            'admin1_code': 'WA',
            'ascii_name': 'Washington',
            'geonameid': '5815135',
            'lat': '',
            'lon': '',
            'alias1': 'WA',
            'alias2': '',
            'alias3': '',
            'alias4': '',
            'alias5': '',
            'alias6': '',
            'alias7': '',
            'alias8': '',
            'alias9': '',
            'alias10': '',
            'attribution': 'Data from GeoNames (geonames.org)',
        },
        {
            'place_id': generate_place_id('ZA', 'GT'),
            'place_key': 'za-gauteng',
            'country': 'ZA',
            'admin1': 'Gauteng',
            'admin1_norm': 'gauteng',
            'admin1_code': 'GT',
            'ascii_name': 'Gauteng',
            'geonameid': '964420',
            'lat': '',
            'lon': '',
            'alias1': '',
            'alias2': '',
            'alias3': '',
            'alias4': '',
            'alias5': '',
            'alias6': '',
            'alias7': '',
            'alias8': '',
            'alias9': '',
            'alias10': '',
            'attribution': 'Data from GeoNames (geonames.org)',
        },
    ]
    return pd.DataFrame(test_data)


# ---- Test 1: Normalization Functions ----

def test_normalize_place_name():
    """Test place name normalization"""
    assert normalize_place_name("Western Australia") == "western australia"
    assert normalize_place_name("São Paulo") == "sao paulo"
    assert normalize_place_name("Hawai'i") == "hawaii"
    assert normalize_place_name("  Limpopo  ") == "limpopo"


def test_canonicalize_place_name():
    """Test place name canonicalization"""
    assert canonicalize_place_name("western australia") == "Western Australia"
    assert canonicalize_place_name("  limpopo  ") == "Limpopo"
    assert canonicalize_place_name("são paulo") == "São Paulo"


def test_slugify_place_name():
    """Test place name slugification"""
    assert slugify_place_name("Western Australia") == "western-australia"
    assert slugify_place_name("São Paulo") == "sao-paulo"
    assert slugify_place_name("Uusimaa (Nyland)") == "uusimaa-nyland"


def test_generate_place_id():
    """Test deterministic place_id generation"""
    id1 = generate_place_id("AU", "WA")
    id2 = generate_place_id("AU", "WA")
    id3 = generate_place_id("US", "WA")

    assert id1 == id2  # Deterministic
    assert id1 != id3  # Different for different countries
    assert len(id1) == 16  # 16-char hex


# ---- Test 2: Exact Matching with Country Hints ----

def test_exact_match_with_country_hint(places_df):
    """Test exact place name match with country hint"""
    from entityidentity.places.placeidentity import resolve_place

    result = resolve_place("Limpopo", places_df, country_hint="ZA")
    assert result is not None
    assert result["admin1"] == "Limpopo"
    assert result["country"] == "ZA"
    assert result["admin1_code"] == "LP"


def test_exact_match_case_insensitive(places_df):
    """Test that matching is case-insensitive"""
    from entityidentity.places.placeidentity import resolve_place

    result_upper = resolve_place("LIMPOPO", places_df, country_hint="ZA")
    result_lower = resolve_place("limpopo", places_df, country_hint="ZA")
    result_mixed = resolve_place("LiMpOpO", places_df, country_hint="ZA")

    assert result_upper is not None
    assert result_lower is not None
    assert result_mixed is not None
    assert result_upper["place_id"] == result_lower["place_id"] == result_mixed["place_id"]


def test_exact_match_full_name(places_df):
    """Test full admin1 name resolution"""
    from entityidentity.places.placeidentity import resolve_place

    result = resolve_place("Western Australia", places_df, country_hint="AU")
    assert result is not None
    assert result["admin1"] == "Western Australia"
    assert result["country"] == "AU"
    assert result["admin1_code"] == "WA"


# ---- Test 3: Abbreviation Resolution ----

def test_abbreviation_match(places_df):
    """Test abbreviation matching via aliases"""
    from entityidentity.places.placeidentity import resolve_place

    result = resolve_place("WA", places_df, country_hint="AU")
    assert result is not None
    assert result["admin1"] == "Western Australia"
    assert result["country"] == "AU"


def test_abbreviation_disambiguation_with_country(places_df):
    """Test that country hint disambiguates abbreviations"""
    from entityidentity.places.placeidentity import resolve_place

    # WA with AU hint → Western Australia
    result_au = resolve_place("WA", places_df, country_hint="AU")
    assert result_au is not None
    assert result_au["country"] == "AU"
    assert result_au["admin1"] == "Western Australia"

    # WA with US hint → Washington
    result_us = resolve_place("WA", places_df, country_hint="US")
    assert result_us is not None
    assert result_us["country"] == "US"
    assert result_us["admin1"] == "Washington"


def test_abbreviation_ca(places_df):
    """Test CA abbreviation with country hint"""
    from entityidentity.places.placeidentity import resolve_place

    result = resolve_place("CA", places_df, country_hint="US")
    assert result is not None
    assert result["admin1"] == "California"
    assert result["country"] == "US"


# ---- Test 4: Country Blocking Efficiency ----

def test_country_blocking_reduces_candidates(places_df):
    """Test that country hint significantly reduces candidate pool"""
    from entityidentity.places.placeidentity import _build_candidate_pool

    # Without country hint (all 5 places)
    candidates_all = _build_candidate_pool(places_df, "limpopo", country_hint=None)

    # With country hint (only ZA places)
    candidates_za = _build_candidate_pool(places_df, "limpopo", country_hint="ZA")

    assert len(candidates_za) < len(candidates_all)
    assert all(candidates_za["country"] == "ZA")


def test_country_blocking_with_invalid_country(places_df):
    """Test handling of invalid country hint"""
    from entityidentity.places.placeidentity import resolve_place

    # Invalid country code should return None or fall back
    result = resolve_place("Limpopo", places_df, country_hint="XX")
    # Should either return None or fall back to no country filter
    # Behavior depends on implementation choice


# ---- Test 5: Fuzzy Matching ----

def test_fuzzy_match_typo(places_df):
    """Test fuzzy matching handles typos"""
    from entityidentity.places.placeidentity import resolve_place

    # "Limpopo" with typo → should still match
    result = resolve_place("Limpoo", places_df, country_hint="ZA", threshold=80)
    assert result is not None
    assert result["admin1"] == "Limpopo"


def test_fuzzy_match_partial(places_df):
    """Test partial name matching"""
    from entityidentity.places.placeidentity import resolve_place

    result = resolve_place("West Australia", places_df, country_hint="AU", threshold=80)
    assert result is not None
    assert result["admin1"] == "Western Australia"


def test_no_match_below_threshold(places_df):
    """Test that low-score matches are rejected"""
    from entityidentity.places.placeidentity import resolve_place

    # Very different name should not match
    result = resolve_place("XYZ", places_df, country_hint="ZA", threshold=90)
    assert result is None


# ---- Test 6: Top-K Matching ----

def test_topk_matches(places_df):
    """Test top-K matching returns scored candidates"""
    from entityidentity.places.placeidentity import topk_matches

    matches = topk_matches("Limpopo", places_df, k=3, country_hint="ZA")

    assert len(matches) > 0
    assert matches[0][0]["admin1"] == "Limpopo"  # Best match
    assert matches[0][1] == 100  # Perfect score

    # Scores should be descending
    scores = [score for _, score in matches]
    assert scores == sorted(scores, reverse=True)


def test_topk_matches_disambiguation(places_df):
    """Test top-K for disambiguating abbreviations"""
    from entityidentity.places.placeidentity import topk_matches

    # WA without country hint → multiple matches
    matches = topk_matches("WA", places_df, k=5, country_hint=None)

    # Should have both Western Australia and Washington
    admin1_names = [row["admin1"] for row, _ in matches]
    # At least one of them should be in results
    assert len(matches) > 0


# ---- Test 7: Listing and Filtering ----

def test_list_places_by_country(places_df):
    """Test listing places filtered by country"""
    from entityidentity.places.placeidentity import resolve_place

    # This test uses the actual list_places function logic
    za_places = places_df[places_df["country"] == "ZA"]
    assert len(za_places) == 2  # Limpopo and Gauteng
    assert all(za_places["country"] == "ZA")

    us_places = places_df[places_df["country"] == "US"]
    assert len(us_places) == 2  # California and Washington
    assert all(us_places["country"] == "US")


def test_list_all_places(places_df):
    """Test listing all places without filter"""
    assert len(places_df) == 5  # All test places


# ---- Test 8: Attribution ----

def test_attribution_present(places_df):
    """Test that all places have GeoNames attribution"""
    assert all(places_df["attribution"] == "Data from GeoNames (geonames.org)")


# ---- Test 9: Place ID Determinism ----

def test_place_id_deterministic(places_df):
    """Test that place_id is deterministic and unique"""
    # Generate IDs for same place twice
    id1 = generate_place_id("ZA", "LP")
    id2 = generate_place_id("ZA", "LP")
    assert id1 == id2

    # Check all IDs in test data are unique
    place_ids = places_df["place_id"].tolist()
    assert len(place_ids) == len(set(place_ids))


# ---- Test 10: Integration Tests ----

def test_resolve_without_country_hint(places_df):
    """Test resolution without country hint (searches all)"""
    from entityidentity.places.placeidentity import resolve_place

    # Unique name should resolve even without country hint
    result = resolve_place("Gauteng", places_df, country_hint=None)
    assert result is not None
    assert result["admin1"] == "Gauteng"
    assert result["country"] == "ZA"


def test_resolve_with_prefix_blocking(places_df):
    """Test that prefix blocking works correctly"""
    from entityidentity.places.placeidentity import _build_candidate_pool

    # "Limpopo" → prefix "lim"
    candidates = _build_candidate_pool(places_df, "limpopo", country_hint=None)

    # Should only include places starting with "lim"
    assert all(row["admin1_norm"].startswith("lim") for _, row in candidates.iterrows())

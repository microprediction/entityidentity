"""Tests for facilities module."""

import os
import pytest
from unittest.mock import Mock, patch
import math

from entityidentity.facilities.facilitylink import (
    link_facility,
    FacilityLinker,
    haversine_distance,
    _score_name_match,
    _score_geo_distance,
    _score_company_match,
)

# Check if facilities master data is available
FACILITIES_AVAILABLE = os.path.exists(
    os.getenv("ENTITYIDENTITY_FACILITIES_PATH", "/nonexistent")
)


class TestFacilityLink:
    """Tests for facility linking functionality."""

    @pytest.mark.skipif(not FACILITIES_AVAILABLE, reason="No facilities master available")
    def test_facility_link_full(self):
        """Test full facility linking with blocking and scoring."""
        # This would test full functionality when facilities data is available
        result = link_facility(
            facility_name="Olympic Dam",
            company_hint="BHP",
            latitude=-30.44,
            longitude=136.88,
            threshold=0.7
        )

        assert result is not None
        assert 'facility_id' in result
        assert 'company_id' in result
        assert 'link_score' in result
        assert result['link_score'] > 0.7
        assert result['facility_name'] is not None
        assert result['company_name'] is not None

    def test_facility_link_company_fallback(self):
        """Test company fallback behavior (should always work)."""
        result = link_facility(company_hint="BHP")

        assert result is not None
        assert 'company_id' in result
        assert result['company_id'] is not None  # Should resolve company

        # If no facilities data available, should have stub behavior
        if not FACILITIES_AVAILABLE:
            assert result['facility_id'] is None
            assert result['link_score'] == 0
            assert result.get('facility_name') is None
            assert result.get('company_name') is not None  # Company should still resolve

    @pytest.mark.skipif(not FACILITIES_AVAILABLE, reason="No facilities master available")
    def test_facility_link_geo_distance(self):
        """Test geographic distance calculations in facility linking."""
        # Test with two known facilities
        result1 = link_facility(
            facility_name="Site A",
            latitude=-30.0,
            longitude=136.0
        )

        result2 = link_facility(
            facility_name="Site B",
            latitude=-31.0,
            longitude=137.0
        )

        if result1 and result2:
            # Check that closer matches have better scores
            close_result = link_facility(
                facility_name="Test Site",
                latitude=-30.01,  # Very close to Site A
                longitude=136.01
            )

            far_result = link_facility(
                facility_name="Test Site",
                latitude=-35.0,  # Far from both
                longitude=140.0
            )

            if close_result and far_result:
                assert close_result['link_score'] > far_result['link_score']

    @pytest.mark.skipif(not FACILITIES_AVAILABLE, reason="No facilities master available")
    def test_facility_link_features(self):
        """Test feature scoring breakdown in facility linking."""
        result = link_facility(
            facility_name="Olympic Dam Mine",
            company_hint="BHP Billiton",
            latitude=-30.44,
            longitude=136.88,
            return_features=True  # Request detailed features
        )

        assert result is not None
        if 'features' in result:
            features = result['features']
            assert 'name_score' in features
            assert 'geo_score' in features
            assert 'company_score' in features

            # Scores should be between 0 and 1
            for score_name in ['name_score', 'geo_score', 'company_score']:
                if features.get(score_name) is not None:
                    assert 0 <= features[score_name] <= 1

    @pytest.mark.skipif(not FACILITIES_AVAILABLE, reason="No facilities master available")
    def test_facility_link_threshold(self):
        """Test confidence threshold filtering."""
        # Test with high threshold
        strict_result = link_facility(
            facility_name="Generic Mine",
            threshold=0.95
        )

        # Test with low threshold
        lenient_result = link_facility(
            facility_name="Generic Mine",
            threshold=0.1
        )

        # With high threshold, might not find match
        # With low threshold, more likely to find match
        if strict_result and lenient_result:
            assert lenient_result['link_score'] >= 0.1
            if strict_result:
                assert strict_result['link_score'] >= 0.95
        elif lenient_result and not strict_result:
            # This is expected - lenient found match, strict didn't
            assert lenient_result['link_score'] >= 0.1
            assert lenient_result['link_score'] < 0.95


class TestFacilityLinker:
    """Tests for FacilityLinker class."""

    def test_facility_linker_init_stub(self):
        """Test FacilityLinker initialization in stub mode."""
        if not FACILITIES_AVAILABLE:
            linker = FacilityLinker()
            assert linker.facilities_df is None
            assert linker.company_resolver is not None  # Should still have company resolver

    @pytest.mark.skipif(not FACILITIES_AVAILABLE, reason="No facilities master available")
    def test_facility_linker_init_full(self):
        """Test FacilityLinker initialization with data."""
        linker = FacilityLinker()
        assert linker.facilities_df is not None
        assert not linker.facilities_df.empty
        assert 'facility_name' in linker.facilities_df.columns
        assert 'company_id' in linker.facilities_df.columns

    def test_facility_linker_link_stub(self):
        """Test linking behavior in stub mode."""
        if not FACILITIES_AVAILABLE:
            linker = FacilityLinker()
            result = linker.link(facility_name="Test Facility")

            assert result is not None
            assert result['facility_id'] is None
            assert result['link_score'] == 0


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_haversine_distance(self):
        """Test haversine distance calculation."""
        # Test distance between two known points
        # Sydney to Melbourne (approximately 713 km)
        dist = haversine_distance(-33.87, 151.21, -37.81, 144.96)
        assert 700 < dist < 720  # Should be approximately 713 km

        # Test same point
        dist = haversine_distance(0, 0, 0, 0)
        assert dist == 0

        # Test antipodes (opposite sides of Earth)
        # Should be approximately half Earth's circumference (~20,000 km)
        dist = haversine_distance(0, 0, 0, 180)
        assert 19900 < dist < 20100

    def test_score_name_match(self):
        """Test name matching scorer."""
        # Exact match
        score = _score_name_match("Olympic Dam", "Olympic Dam")
        assert score == 1.0

        # Case insensitive
        score = _score_name_match("Olympic Dam", "OLYMPIC DAM")
        assert score > 0.9

        # Partial match
        score = _score_name_match("Olympic Dam Mine", "Olympic Dam")
        assert 0.5 < score < 0.95

        # No match
        score = _score_name_match("Mount Isa", "Olympic Dam")
        assert score < 0.5

        # Empty strings
        score = _score_name_match("", "")
        assert score == 0

        score = _score_name_match("Olympic Dam", "")
        assert score == 0

    def test_score_geo_distance(self):
        """Test geographic distance scorer."""
        # Same location
        score = _score_geo_distance(0, 0, 0, 0)
        assert score == 1.0

        # 10 km away (should be high score)
        score = _score_geo_distance(0, 0, 0.09, 0)  # ~10 km
        assert score > 0.9

        # 50 km away (medium score)
        score = _score_geo_distance(0, 0, 0.45, 0)  # ~50 km
        assert 0.3 < score < 0.7

        # 500 km away (low score)
        score = _score_geo_distance(0, 0, 4.5, 0)  # ~500 km
        assert score < 0.2

        # Opposite side of Earth (minimum score)
        score = _score_geo_distance(0, 0, 0, 180)
        assert score < 0.01

    def test_score_company_match(self):
        """Test company matching scorer."""
        # Same company ID
        score = _score_company_match("Q658255", "Q658255")
        assert score == 1.0

        # Different companies
        score = _score_company_match("Q658255", "Q734827")
        assert score == 0

        # None values
        score = _score_company_match(None, None)
        assert score == 0

        score = _score_company_match("Q658255", None)
        assert score == 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_link_facility_empty_inputs(self):
        """Test with empty or None inputs."""
        # All None
        result = link_facility()
        assert result is not None
        assert result['facility_id'] is None
        assert result['link_score'] == 0

        # Empty strings
        result = link_facility(facility_name="", company_hint="")
        assert result is not None

    def test_link_facility_invalid_coordinates(self):
        """Test with invalid geographic coordinates."""
        # Out of range latitude
        result = link_facility(facility_name="Test", latitude=91, longitude=0)
        assert result is not None  # Should handle gracefully

        # Out of range longitude
        result = link_facility(facility_name="Test", latitude=0, longitude=181)
        assert result is not None  # Should handle gracefully

        # Non-numeric coordinates (would raise TypeError in real usage)
        with pytest.raises((TypeError, ValueError)):
            link_facility(facility_name="Test", latitude="not_a_number", longitude=0)

    def test_link_facility_only_company(self):
        """Test with only company hint provided."""
        result = link_facility(company_hint="Rio Tinto")

        assert result is not None
        assert 'company_id' in result
        # Company should resolve even without facilities data
        assert result['company_id'] is not None

        if not FACILITIES_AVAILABLE:
            assert result['facility_id'] is None
            assert result['link_score'] == 0


@pytest.mark.skipif(not FACILITIES_AVAILABLE, reason="No facilities master available")
class TestIntegration:
    """Integration tests requiring facilities data."""

    def test_known_facility_linking(self):
        """Test linking known facilities."""
        # Test some well-known mining facilities
        known_facilities = [
            {
                'name': 'Olympic Dam',
                'company': 'BHP',
                'lat': -30.44,
                'lon': 136.88
            },
            {
                'name': 'Mount Isa',
                'company': 'Glencore',
                'lat': -20.73,
                'lon': 139.49
            }
        ]

        for facility in known_facilities:
            result = link_facility(
                facility_name=facility['name'],
                company_hint=facility['company'],
                latitude=facility['lat'],
                longitude=facility['lon']
            )

            assert result is not None
            assert result['link_score'] > 0.5
            assert facility['name'].lower() in result.get('facility_name', '').lower()

    def test_ambiguous_facility_resolution(self):
        """Test resolution of ambiguous facility names."""
        # Many mines have generic names like "Gold Mine"
        result_with_hint = link_facility(
            facility_name="Gold Mine",
            company_hint="Newmont"
        )

        result_without_hint = link_facility(
            facility_name="Gold Mine"
        )

        # With company hint should have higher confidence
        if result_with_hint and result_without_hint:
            if result_with_hint.get('company_id') and result_without_hint.get('facility_id'):
                assert result_with_hint['link_score'] >= result_without_hint['link_score']


if __name__ == "__main__":
    # Run tests and show which ones are skipped
    pytest.main([__file__, "-v", "-rs"])
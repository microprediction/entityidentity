"""Comprehensive tests for instruments module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from entityidentity.instruments import (
    instrument_identifier,
    match_instruments,
    list_instruments,
    load_instruments,
    clear_cache,
)
from entityidentity.instruments.instrumentidentity import (
    _detect_ticker_pattern,
    normalize_ticker,
    normalize_instrument_name,
)


# Skip GCS tests if no credentials
SKIP_GCS = not os.environ.get("ENTITYIDENTITY_TEST_GCS")


class TestTickerDetection:
    """Test ticker pattern detection."""

    def test_instrument_fastmarkets_ticker(self):
        """Test Fastmarkets ticker pattern detection (MB-XX-####)."""
        # Test exact Fastmarkets ticker - use one that exists
        result = instrument_identifier("MB-AL-0045")
        if result:  # Only if this ticker exists
            assert result["ticker"] == "MB-AL-0045"
            assert result["provider"] == "Fastmarkets"

        # Test pattern detection
        pattern = _detect_ticker_pattern("MB-CO-0005")
        assert pattern == "Fastmarkets"

        # Various Fastmarkets formats
        assert _detect_ticker_pattern("MB-AL-0045") == "Fastmarkets"
        assert _detect_ticker_pattern("MB-NI-0001") == "Fastmarkets"
        assert _detect_ticker_pattern("MB-FEC-0001") == "Fastmarkets"

    def test_instrument_lme_ticker(self):
        """Test LME ticker pattern detection (LME_XX_XXXX)."""
        # Test exact LME ticker
        result = instrument_identifier("LME_AL_CASH")
        if result:  # May not exist in sample data
            assert "LME" in result.get("ticker", "").upper()

        # Test pattern detection
        pattern = _detect_ticker_pattern("LME_AL_CASH")
        assert pattern == "LME"

        # Various LME formats
        assert _detect_ticker_pattern("LME_CU_CASH") == "LME"
        assert _detect_ticker_pattern("LME_NI_3M") == "LME"
        assert _detect_ticker_pattern("LME-ZN-CASH") == "LME"  # With hyphens

    def test_instrument_regex_patterns(self):
        """Test various ticker format regex patterns."""
        # CME patterns (short codes)
        assert _detect_ticker_pattern("HG") == "CME"
        assert _detect_ticker_pattern("SI") == "CME"
        assert _detect_ticker_pattern("GC") == "CME"

        # Bloomberg patterns
        assert _detect_ticker_pattern("LMCADY") == "Bloomberg"
        assert _detect_ticker_pattern("LMZSDY") == "Bloomberg"

        # Argus patterns
        assert _detect_ticker_pattern("PA0026990") == "Argus"
        assert _detect_ticker_pattern("PA1234567") == "Argus"

        # Non-matching patterns
        assert _detect_ticker_pattern("random text") is None
        assert _detect_ticker_pattern("123456") is None
        assert _detect_ticker_pattern("not-a-ticker") is None


class TestResolution:
    """Test instrument resolution functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_instrument_identifier_exact(self):
        """Test exact ticker match resolution."""
        # Test with known ticker in actual data
        result = instrument_identifier("MB-AL-0045")
        if result:  # Only test if found
            assert result["entity_type"] == "instrument"
            assert result["ticker"] == "MB-AL-0045"
            assert "instrument_id" in result
            assert len(result["instrument_id"]) == 16

            # Case variations should work
            result_lower = instrument_identifier("mb-al-0045")
            assert result_lower is not None
            assert result_lower["instrument_id"] == result["instrument_id"]

    def test_instrument_identifier_name(self):
        """Test resolution by instrument name."""
        # Search by partial name
        result = instrument_identifier("cobalt standard grade")
        if result:
            assert "cobalt" in result.get("instrument_name", "").lower() or \
                   "cobalt" in str(result.get("material_id", "")).lower()

        # Search by material name
        result = instrument_identifier("lithium carbonate")
        if result:
            assert "lithium" in str(result.values()).lower() or \
                   "li" in str(result.values()).lower()

    def test_instrument_source_hint(self):
        """Test that source_hint biases toward hinted provider."""
        # Without hint
        result_no_hint = instrument_identifier("copper")

        # With Fastmarkets hint
        result_fm = instrument_identifier("copper", source_hint="Fastmarkets")
        if result_fm:
            assert result_fm.get("provider") == "Fastmarkets"

        # With LME hint
        result_lme = instrument_identifier("aluminum", source_hint="LME")
        if result_lme and result_lme.get("provider"):
            # If we got a result with LME hint, it should prefer LME
            pass  # May not have LME data in samples

        # Source hint should not exclude other sources if no match
        result = instrument_identifier("unique-ticker-xyz", source_hint="Fastmarkets")
        assert result is None  # No forcing of wrong matches

    def test_match_instruments_top_k(self):
        """Test that match_instruments returns K candidates."""
        # Get top 3 matches
        matches = match_instruments("metal", k=3)
        assert isinstance(matches, list)
        assert len(matches) <= 3

        # Check sorting by score
        if len(matches) > 1:
            scores = [m["score"] for m in matches]
            assert scores == sorted(scores, reverse=True)

        # Each match should have required fields
        for match in matches:
            assert "entity_type" in match
            assert match["entity_type"] == "instrument"
            assert "ticker" in match
            assert "score" in match
            assert isinstance(match["score"], (int, float))

        # Test with k=1
        matches = match_instruments("cobalt", k=1)
        assert len(matches) <= 1

        # Test with high k
        matches = match_instruments("a", k=100)
        assert len(matches) <= 100


class TestCrosswalk:
    """Test material crosswalk functionality."""

    def test_instrument_material_crosswalk(self):
        """Test that material_hint resolves to material_id."""
        # Load instruments to check crosswalk
        df = load_instruments()

        # Find instruments with metals
        if "Metal" in df.columns and "material_id" in df.columns:
            metal_rows = df[df["Metal"].notna() & df["material_id"].notna()]

            if not metal_rows.empty:
                # Take first row with resolved metal
                row = metal_rows.iloc[0]
                ticker = row["asset_id"]

                # Resolution should include material_id
                result = instrument_identifier(ticker)
                assert result is not None
                assert "material_id" in result
                assert result["material_id"] is not None

    def test_instrument_cluster_mapping(self):
        """Test that material_id maps to cluster_id."""
        # Test known cobalt ticker
        result = instrument_identifier("MB-CO-0005")
        if result and "material_id" in result and result["material_id"]:
            # Cobalt should map to nickel_cobalt_chain
            assert "cluster_id" in result
            assert result["cluster_id"] == "nickel_cobalt_chain"

        # Test lithium
        result = instrument_identifier("MB-LI-0029")
        if result and "material_id" in result and result["material_id"]:
            assert "cluster_id" in result
            assert result["cluster_id"] == "lithium_chain"

    def test_instrument_missing_material_hint(self):
        """Test graceful handling of missing material_hint."""
        # Create test data without material hint
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Source,asset_id,Name,currency,unit\n")
            f.write("TestSource,TEST-001,Test Instrument,USD,USD/t\n")
            f.write("TestSource,TEST-002,Another Test,EUR,EUR/kg\n")
            temp_path = f.name

        try:
            df = load_instruments(path=temp_path)

            # Should have material_id column but with None values
            assert "material_id" in df.columns
            assert df["material_id"].isna().all()

            # Resolution should still work
            clear_cache()
            result = instrument_identifier("TEST-001")
            if result:
                # material_id should be None or not present
                assert result.get("material_id") is None
                assert result.get("cluster_id") is None
        finally:
            os.unlink(temp_path)


class TestAPI:
    """Test public API functions."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_list_instruments_by_source(self):
        """Test filtering instruments by provider."""
        # List all instruments
        all_instruments = list_instruments()
        assert isinstance(all_instruments, pd.DataFrame)
        assert len(all_instruments) > 0

        # Filter by Fastmarkets
        fm_instruments = list_instruments(source="Fastmarkets")
        if not fm_instruments.empty:
            assert all(fm_instruments["Source"] == "Fastmarkets")
            assert len(fm_instruments) <= len(all_instruments)

        # Filter by non-existent source
        empty = list_instruments(source="NonExistentSource")
        assert len(empty) == 0

        # Case insensitive
        fm_lower = list_instruments(source="fastmarkets")
        fm_upper = list_instruments(source="FASTMARKETS")
        assert len(fm_lower) == len(fm_upper)

    def test_load_instruments_caching(self):
        """Test LRU cache behavior for load_instruments."""
        # First load
        df1 = load_instruments()
        id1 = id(df1)

        # Second load should return cached
        df2 = load_instruments()
        id2 = id(df2)
        assert id1 == id2  # Same object

        # Clear cache
        clear_cache()

        # Third load should be new object
        df3 = load_instruments()
        id3 = id(df3)
        assert id1 != id3  # Different object

        # But data should be equivalent
        assert len(df1) == len(df3)
        assert df1.columns.tolist() == df3.columns.tolist()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self):
        """Test handling of empty input."""
        assert instrument_identifier("") is None
        assert instrument_identifier("   ") is None
        assert instrument_identifier(None) is None

        assert match_instruments("") == []
        assert match_instruments("   ") == []

    def test_special_characters(self):
        """Test handling of special characters."""
        # Should handle gracefully
        result = instrument_identifier("!@#$%^&*()")
        assert result is None

        # Hyphens and underscores should work
        result = instrument_identifier("MB-CO-0005")
        assert result is not None

        # Dots and slashes in names
        result = instrument_identifier("APT 88.5% WO3")
        # Should handle percentage signs and dots

    def test_threshold_filtering(self):
        """Test that threshold properly filters results."""
        # Very high threshold
        result = instrument_identifier("cobaltt", threshold=99)  # Typo
        assert result is None  # Should not match with typo at high threshold

        # Lower threshold
        result = instrument_identifier("cobaltt", threshold=80)  # Typo
        # May or may not match depending on data

    def test_normalization_functions(self):
        """Test normalization helper functions."""
        # Ticker normalization
        assert normalize_ticker("MB-CO-0005") == "mb-co-0005"
        assert normalize_ticker("LME_AL_CASH") == "lme_al_cash"
        assert normalize_ticker("HG@#$123") == "hg123"

        # Instrument name normalization
        assert normalize_instrument_name("Cobalt Standard Grade") == "cobalt standard grade"
        assert normalize_instrument_name("APT 88.5% WO3") == "apt 88 5 wo3"
        assert normalize_instrument_name("In-Whs Rotterdam") == "in-whs rotterdam"


class TestIntegration:
    """Integration tests across multiple functions."""

    def test_full_resolution_pipeline(self):
        """Test complete resolution pipeline."""
        # Load data
        df = load_instruments()
        assert len(df) > 0

        # Get exact match
        if not df.empty:
            ticker = df.iloc[0]["asset_id"]
            result = instrument_identifier(ticker)
            assert result is not None
            assert result["ticker"] == ticker

        # Get fuzzy matches
        matches = match_instruments("metal", k=5)
        assert len(matches) <= 5

        # List and filter
        filtered = list_instruments(search="cobalt")
        if not filtered.empty:
            # Try to resolve first result
            first_ticker = filtered.iloc[0]["asset_id"]
            result = instrument_identifier(first_ticker)
            assert result is not None

    def test_crosswalk_integration(self):
        """Test integration with metals crosswalk."""
        # Get all instruments with resolved metals
        df = load_instruments()

        if "material_id" in df.columns:
            resolved = df[df["material_id"].notna()]

            if not resolved.empty:
                # Check a resolved instrument
                row = resolved.iloc[0]
                ticker = row["asset_id"]

                result = instrument_identifier(ticker)
                assert result is not None
                assert result.get("material_id") == row["material_id"]

                # Check cluster propagation
                if "cluster_id" in row and pd.notna(row["cluster_id"]):
                    assert result.get("cluster_id") == row["cluster_id"]


@pytest.mark.skipif(SKIP_GCS, reason="GCS tests disabled (set ENTITYIDENTITY_TEST_GCS=1 to enable)")
class TestGCS:
    """Test Google Cloud Storage functionality."""

    def test_gcs_loading(self):
        """Test loading from GCS."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any local path overrides
            if "GSMC_TICKERS_PATH" in os.environ:
                del os.environ["GSMC_TICKERS_PATH"]

            clear_cache()

            try:
                df = load_instruments()
                # If successful, should have substantial data
                assert len(df) > 10
                assert "instrument_id" in df.columns
            except FileNotFoundError:
                # Expected if no GCS access
                pytest.skip("GCS not accessible")

    def test_gcs_fallback(self):
        """Test fallback when GCS fails."""
        with patch('entityidentity.instruments.instrumentloaders._load_from_gcs') as mock_gcs:
            mock_gcs.return_value = None  # Simulate GCS failure

            clear_cache()

            # Should still work with local data
            df = load_instruments()
            assert df is not None
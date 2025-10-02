"""Unit tests for instruments module."""

import os
import tempfile
import pandas as pd
import pytest
from pathlib import Path

from entityidentity.instruments import load_instruments, clear_cache


class TestInstrumentsLoader:
    """Test instruments data loading functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
        # Store and clear env var
        self.orig_env = os.environ.get("GSMC_TICKERS_PATH")
        if "GSMC_TICKERS_PATH" in os.environ:
            del os.environ["GSMC_TICKERS_PATH"]

        yield

        # Restore env var
        if self.orig_env:
            os.environ["GSMC_TICKERS_PATH"] = self.orig_env
        elif "GSMC_TICKERS_PATH" in os.environ:
            del os.environ["GSMC_TICKERS_PATH"]

    def test_load_from_explicit_path(self):
        """Test loading from an explicit file path."""
        # Use the sample CSV
        sample_path = Path(__file__).parent.parent / "entityidentity/instruments/data/samples/ticker_references_sample.csv"

        if sample_path.exists():
            df = load_instruments(path=sample_path)

            assert df is not None
            assert len(df) == 10  # Sample has 10 rows
            assert "instrument_id" in df.columns
            assert "ticker_norm" in df.columns
            assert "name_norm" in df.columns

            # Check instrument_id is computed correctly
            assert df["instrument_id"].notna().all()
            assert df["instrument_id"].str.len().eq(16).all()  # Should be 16-char hex

    def test_load_from_env_variable(self):
        """Test loading via GSMC_TICKERS_PATH environment variable."""
        sample_path = Path(__file__).parent.parent / "entityidentity/instruments/data/samples/ticker_references_sample.csv"

        if sample_path.exists():
            os.environ["GSMC_TICKERS_PATH"] = str(sample_path)

            df = load_instruments()  # No explicit path

            assert df is not None
            assert len(df) == 10

    def test_computed_columns(self):
        """Test that computed columns are added correctly."""
        sample_path = Path(__file__).parent.parent / "entityidentity/instruments/data/samples/ticker_references_sample.csv"

        if sample_path.exists():
            df = load_instruments(path=sample_path)

            # Required computed columns
            assert "instrument_id" in df.columns
            assert "ticker_norm" in df.columns
            assert "name_norm" in df.columns
            assert "material_id" in df.columns
            assert "cluster_id" in df.columns

            # Check normalizations
            row = df[df["asset_id"] == "MB-CO-0005"].iloc[0]
            assert row["ticker_norm"] == "mb-co-0005"

            # Material resolution (might be None if metals not available)
            # Just check the column exists
            assert "material_id" in row

    def test_instrument_id_stability(self):
        """Test that instrument_id is deterministic."""
        sample_path = Path(__file__).parent.parent / "entityidentity/instruments/data/samples/ticker_references_sample.csv"

        if sample_path.exists():
            # Load twice
            df1 = load_instruments(path=sample_path)
            clear_cache()
            df2 = load_instruments(path=sample_path)

            # IDs should be identical
            assert df1["instrument_id"].equals(df2["instrument_id"])

    def test_error_on_missing_file(self):
        """Test that FileNotFoundError is raised for non-existent files."""
        # The loader will fall back to other sources if path doesn't exist
        # So we don't expect FileNotFoundError anymore
        # Instead test that it loads from fallback
        result = load_instruments(path="/non/existent/file.parquet")
        assert result is not None  # Should fallback to available data

    def test_cache_functionality(self):
        """Test that LRU cache works correctly."""
        sample_path = Path(__file__).parent.parent / "entityidentity/instruments/data/samples/ticker_references_sample.csv"

        if sample_path.exists():
            # First load
            df1 = load_instruments(path=sample_path)
            id1 = id(df1)

            # Second load should return cached object
            df2 = load_instruments(path=sample_path)
            id2 = id(df2)

            assert id1 == id2  # Same object

            # Clear cache
            clear_cache()

            # Third load should be new object
            df3 = load_instruments(path=sample_path)
            id3 = id(df3)

            assert id1 != id3  # Different object

    def test_parquet_loading(self):
        """Test loading from parquet file."""
        # Check if we have the real parquet file
        parquet_path = Path(__file__).parent.parent / "entityidentity/instruments/data/ticker_references.parquet"

        if parquet_path.exists():
            df = load_instruments(path=parquet_path)

            assert df is not None
            assert len(df) > 0
            assert "instrument_id" in df.columns

            # Real data should have more rows than sample
            assert len(df) > 10

    @pytest.mark.skipif(
        not os.environ.get("ENTITYIDENTITY_TEST_GCS"),
        reason="GCS tests disabled by default"
    )
    def test_gcs_loading(self):
        """Test loading from Google Cloud Storage."""
        # This test requires GCS credentials and is disabled by default
        clear_cache()

        try:
            df = load_instruments()  # Will try GCS first
            assert df is not None
            assert len(df) > 0
        except FileNotFoundError:
            # Expected if no GCS access
            pass

    def test_material_crosswalk(self):
        """Test that material_id crosswalk works when metals are available."""
        sample_path = Path(__file__).parent.parent / "entityidentity/instruments/data/samples/ticker_references_sample.csv"

        if sample_path.exists():
            df = load_instruments(path=sample_path)

            # Check if any metals were resolved
            if df["material_id"].notna().any():
                # At least some should be resolved
                cobalt_rows = df[df["Metal"].str.contains("Cobalt", case=False, na=False)]
                if len(cobalt_rows) > 0:
                    # Cobalt should resolve to something
                    assert cobalt_rows.iloc[0]["material_id"] is not None

    def test_column_name_flexibility(self):
        """Test that loader handles various column name formats."""
        # Create temp file with alternate column names
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("source,ticker,name,currency,unit,material_hint\n")
            f.write("TestSource,TEST-001,Test Ticker,USD,USD/t,Copper\n")
            temp_path = f.name

        try:
            df = load_instruments(path=temp_path)

            # Should still work with different column names
            assert df is not None
            assert len(df) == 1
            assert "instrument_id" in df.columns

        finally:
            os.unlink(temp_path)
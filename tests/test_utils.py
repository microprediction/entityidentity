"""Tests for shared utilities."""

import pytest
from pathlib import Path
import pandas as pd
import tempfile

from entityidentity.utils.dataloader import (
    find_data_file,
    load_parquet_or_csv,
    format_not_found_error,
)


class TestFindDataFile:
    """Test data file finding utility"""

    def test_find_module_local_data(self):
        """Test finding data in module-local directory"""
        # Metals data is in metals/data/
        from entityidentity.metals import metalapi
        path = find_data_file(
            module_file=metalapi.__file__,
            subdirectory="metals",
            filenames=["metals.parquet"],
            module_local_data=True,
        )
        assert path is not None
        assert path.exists()
        assert path.name == "metals.parquet"

    def test_find_package_data(self):
        """Test finding data in package data directory"""
        # Companies data is in entityidentity/data/companies/
        from entityidentity.companies import companyresolver
        path = find_data_file(
            module_file=companyresolver.__file__,
            subdirectory="companies",
            filenames=["companies.parquet", "companies.csv"],
        )
        assert path is not None
        assert path.exists()
        assert path.name in ["companies.parquet", "companies.csv"]

    def test_find_nonexistent_file(self):
        """Test that None is returned when file not found"""
        from entityidentity.companies import companyresolver
        path = find_data_file(
            module_file=companyresolver.__file__,
            subdirectory="nonexistent",
            filenames=["missing.parquet"],
        )
        assert path is None


class TestLoadParquetOrCsv:
    """Test data loading utility"""

    def test_load_parquet(self):
        """Test loading parquet file"""
        # Create temporary parquet file
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
            df.to_parquet(f.name)
            temp_path = Path(f.name)

        try:
            loaded_df = load_parquet_or_csv(temp_path)
            assert isinstance(loaded_df, pd.DataFrame)
            assert len(loaded_df) == 3
            assert list(loaded_df.columns) == ["a", "b"]
        finally:
            temp_path.unlink()

    def test_load_csv(self):
        """Test loading CSV file"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False) as f:
            f.write("a,b\n1,4\n2,5\n3,6\n")
            temp_path = Path(f.name)

        try:
            loaded_df = load_parquet_or_csv(temp_path)
            assert isinstance(loaded_df, pd.DataFrame)
            assert len(loaded_df) == 3
            assert list(loaded_df.columns) == ["a", "b"]
        finally:
            temp_path.unlink()

    def test_unsupported_format(self):
        """Test that unsupported formats raise ValueError"""
        temp_path = Path("/tmp/test.txt")
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_parquet_or_csv(temp_path)


class TestFormatNotFoundError:
    """Test error message formatting utility"""

    def test_format_basic_error(self):
        """Test basic error message formatting"""
        msg = format_not_found_error(
            subdirectory="test",
            searched_locations=[
                ("Location 1", Path("/path/1")),
                ("Location 2", Path("/path/2")),
            ],
            fix_instructions=[
                "Run command A",
                "Run command B",
            ],
        )

        assert "No test data found" in msg
        assert "Searched:" in msg
        assert "Location 1" in msg
        assert "/path/1" in msg
        assert "Location 2" in msg
        assert "/path/2" in msg
        assert "To fix:" in msg
        assert "Run command A" in msg
        assert "Run command B" in msg

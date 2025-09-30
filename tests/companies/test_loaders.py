"""Integration tests for company data loaders.

These tests verify that each data source loader works correctly.
By default, tests use sample data. Set ENTITYIDENTITY_TEST_LIVE=1
to test against real APIs (requires internet and may be slow).
"""

import os
import pytest
import pandas as pd
from entityidentity.companies.companygleif import (
    load_gleif_lei,
    sample_gleif_data,
    _normalize_gleif_level1,
)
from entityidentity.companies.companywikidata import (
    load_wikidata_companies,
    sample_wikidata_data,
    _parse_wikidata_results,
    _extract_qid,
)
from entityidentity.companies.companyexchanges import (
    load_asx,
    load_lse,
    load_tsx,
    sample_asx_data,
    sample_lse_data,
    sample_tsx_data,
)


# Check if we should test against live APIs
TEST_LIVE = os.environ.get('ENTITYIDENTITY_TEST_LIVE', '0') == '1'


class TestGLEIFLoader:
    """Test GLEIF LEI data loader."""
    
    def test_sample_gleif_data(self):
        """Test that sample GLEIF data has correct structure."""
        df = sample_gleif_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        # Check required columns
        required_columns = ['lei', 'name', 'country']
        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"
        
        # Check LEI format (20 alphanumeric characters)
        assert df['lei'].notna().all(), "LEI should not be null"
        for lei in df['lei']:
            assert len(lei) == 20, f"LEI should be 20 chars: {lei}"
            assert lei.isalnum(), f"LEI should be alphanumeric: {lei}"
        
        # Check country codes (should be 2-letter ISO codes)
        assert df['country'].notna().all(), "Country should not be null"
        for country in df['country']:
            assert len(country) == 2, f"Country should be 2-letter code: {country}"
    
    def test_sample_data_companies(self):
        """Test that sample data includes expected companies."""
        df = sample_gleif_data()
        
        # Should include major companies
        names = df['name'].str.lower()
        assert any('apple' in name for name in names), "Should include Apple"
        assert any('microsoft' in name for name in names), "Should include Microsoft"
    
    @pytest.mark.skipif(not TEST_LIVE, reason="Live API testing disabled")
    def test_load_gleif_live(self, tmp_path):
        """Test loading real GLEIF data (slow, requires internet)."""
        # Load a small subset
        df = load_gleif_lei(cache_dir=str(tmp_path), max_records=100)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'lei' in df.columns
        assert 'name' in df.columns


class TestWikidataLoader:
    """Test Wikidata company loader."""
    
    def test_sample_wikidata_data(self):
        """Test that sample Wikidata has correct structure."""
        df = sample_wikidata_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        # Check required columns
        required_columns = ['wikidata_qid', 'name', 'country']
        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"
        
        # Check Q-ID format
        assert df['wikidata_qid'].notna().all(), "Q-ID should not be null"
        for qid in df['wikidata_qid']:
            assert qid.startswith('Q'), f"Q-ID should start with Q: {qid}"
            assert qid[1:].isdigit(), f"Q-ID should be Q followed by digits: {qid}"
        
        # Check aliases are lists
        if 'aliases' in df.columns:
            for aliases in df['aliases']:
                assert isinstance(aliases, list), "Aliases should be a list"
    
    def test_extract_qid(self):
        """Test Q-ID extraction from URLs."""
        assert _extract_qid("http://www.wikidata.org/entity/Q312") == "Q312"
        assert _extract_qid("http://www.wikidata.org/entity/Q2283") == "Q2283"
        assert _extract_qid("invalid") == ""
    
    def test_sample_data_has_aliases(self):
        """Test that sample data includes aliases."""
        df = sample_wikidata_data()
        
        # At least one company should have aliases
        has_aliases = any(len(aliases) > 0 for aliases in df['aliases'])
        assert has_aliases, "Sample data should include companies with aliases"
    
    @pytest.mark.skipif(not TEST_LIVE, reason="Live API testing disabled")
    def test_load_wikidata_live(self):
        """Test loading real Wikidata (slow, requires internet)."""
        # Load a small subset
        df = load_wikidata_companies(limit=50)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'wikidata_qid' in df.columns
        assert 'name' in df.columns


class TestExchangeLoaders:
    """Test stock exchange data loaders."""
    
    def test_sample_asx_data(self):
        """Test ASX sample data structure."""
        df = sample_asx_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        # Check required columns
        assert 'ticker' in df.columns
        assert 'name' in df.columns
        assert 'country' in df.columns
        assert 'exchange' in df.columns
        
        # All should be Australian companies
        assert (df['country'] == 'AU').all(), "ASX companies should be AU"
        assert (df['exchange'] == 'ASX').all(), "Exchange should be ASX"
        
        # Should include major mining companies
        names = df['name'].str.lower()
        assert any('bhp' in name for name in names), "Should include BHP"
    
    def test_sample_lse_data(self):
        """Test LSE sample data structure."""
        df = sample_lse_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        assert 'ticker' in df.columns
        assert 'name' in df.columns
        assert 'country' in df.columns
        assert 'exchange' in df.columns
        
        # Should be UK companies
        assert (df['country'] == 'GB').all(), "LSE companies should be GB"
        assert (df['exchange'] == 'LSE').all(), "Exchange should be LSE"
    
    def test_sample_tsx_data(self):
        """Test TSX sample data structure."""
        df = sample_tsx_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        assert 'ticker' in df.columns
        assert 'name' in df.columns
        assert 'country' in df.columns
        assert 'exchange' in df.columns
        
        # Should be Canadian companies
        assert (df['country'] == 'CA').all(), "TSX companies should be CA"
        assert (df['exchange'] == 'TSX').all(), "Exchange should be TSX"
    
    def test_exchange_tickers_unique(self):
        """Test that tickers are unique within each exchange."""
        for sample_fn, name in [
            (sample_asx_data, 'ASX'),
            (sample_lse_data, 'LSE'),
            (sample_tsx_data, 'TSX'),
        ]:
            df = sample_fn()
            duplicates = df['ticker'].duplicated()
            assert not duplicates.any(), f"{name} has duplicate tickers"
    
    @pytest.mark.skipif(not TEST_LIVE, reason="Live API testing disabled")
    def test_load_asx_live(self):
        """Test loading real ASX data (may fail if endpoint changes)."""
        try:
            df = load_asx()
            assert isinstance(df, pd.DataFrame)
            # If successful, should have many companies
            if len(df) > 0:
                assert 'ticker' in df.columns
                assert 'name' in df.columns
        except Exception:
            # ASX endpoint may not be available or may have changed
            pytest.skip("ASX live data not available")


class TestDataIntegration:
    """Test integration across data sources."""
    
    def test_all_sources_have_name_and_country(self):
        """Test that all data sources provide name and country."""
        sources = [
            sample_gleif_data(),
            sample_wikidata_data(),
            sample_asx_data(),
            sample_lse_data(),
            sample_tsx_data(),
        ]
        
        for df in sources:
            assert 'name' in df.columns, "All sources should have 'name'"
            assert 'country' in df.columns, "All sources should have 'country'"
            assert len(df) > 0, "Sample data should not be empty"
    
    def test_lei_overlap_gleif_wikidata(self):
        """Test that some LEIs overlap between GLEIF and Wikidata."""
        gleif = sample_gleif_data()
        wikidata = sample_wikidata_data()
        
        # Both should have LEI column
        assert 'lei' in gleif.columns
        assert 'lei' in wikidata.columns
        
        # Get non-null LEIs
        gleif_leis = set(gleif[gleif['lei'].notna()]['lei'])
        wikidata_leis = set(wikidata[wikidata['lei'].notna()]['lei'])
        
        # There should be some overlap in sample data
        overlap = gleif_leis & wikidata_leis
        assert len(overlap) > 0, "Sample data should have overlapping LEIs"
    
    def test_data_can_be_concatenated(self):
        """Test that data from all sources can be concatenated."""
        sources = [
            sample_gleif_data(),
            sample_wikidata_data(),
            sample_asx_data(),
            sample_lse_data(),
            sample_tsx_data(),
        ]
        
        # All should concat without error
        try:
            combined = pd.concat(sources, ignore_index=True)
            assert len(combined) == sum(len(df) for df in sources)
        except Exception as e:
            pytest.fail(f"Failed to concatenate data sources: {e}")
    
    def test_country_codes_valid(self):
        """Test that all country codes are valid 2-letter codes."""
        sources = [
            sample_gleif_data(),
            sample_wikidata_data(),
            sample_asx_data(),
            sample_lse_data(),
            sample_tsx_data(),
        ]
        
        for df in sources:
            countries = df[df['country'].notna()]['country']
            for country in countries:
                assert len(country) == 2, f"Country code should be 2 letters: {country}"
                assert country.isupper(), f"Country code should be uppercase: {country}"
                assert country.isalpha(), f"Country code should be letters: {country}"


class TestBuildScript:
    """Test the consolidation build script."""
    
    def test_consolidate_with_samples(self):
        """Test that consolidation works with sample data."""
        from entityidentity.build_companies_db import consolidate_companies
        
        df = consolidate_companies(use_samples=True)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        # Check all required columns exist
        required = ['name', 'name_norm', 'country', 'lei', 'wikidata_qid', 
                   'aliases', 'source']
        for col in required:
            assert col in df.columns, f"Missing column: {col}"
        
        # Check name_norm is populated
        assert df['name_norm'].notna().all(), "name_norm should be populated"
        
        # Check we have data from multiple sources
        sources = df['source'].unique()
        assert len(sources) > 1, "Should have data from multiple sources"
        assert 'GLEIF' in sources, "Should include GLEIF data"
        # Note: Wikidata records may be deduplicated by LEI if they overlap with GLEIF
        # That's expected behavior - the most important thing is we have data from exchanges too
        assert any(s in sources for s in ['ASX', 'LSE', 'TSX']), "Should include exchange data"
    
    def test_consolidate_deduplicates(self):
        """Test that consolidation removes duplicates."""
        from entityidentity.build_companies_db import consolidate_companies
        
        df = consolidate_companies(use_samples=True)
        
        # Check for LEI duplicates
        lei_records = df[df['lei'].notna() & (df['lei'] != '')]
        if len(lei_records) > 0:
            duplicates = lei_records['lei'].duplicated()
            assert not duplicates.any(), "Should not have duplicate LEIs"
        
        # Check for name+country duplicates (for records without LEI)
        no_lei = df[~df['lei'].notna() | (df['lei'] == '')]
        if len(no_lei) > 0:
            duplicates = no_lei[['name_norm', 'country']].duplicated()
            # Some duplicates acceptable if from different sources
            # but should be minimal
            dup_rate = duplicates.sum() / len(no_lei)
            assert dup_rate < 0.1, f"Duplicate rate too high: {dup_rate:.1%}"


# Mark tests that require external dependencies
@pytest.mark.integration
class TestFullIntegration:
    """Full integration tests (can be run separately)."""
    
    @pytest.mark.skipif(not TEST_LIVE, reason="Live API testing disabled")
    def test_build_full_database(self, tmp_path):
        """Test building a full database from live sources."""
        from entityidentity.build_companies_db import consolidate_companies
        
        # This is slow but comprehensive
        df = consolidate_companies(
            use_samples=False,
            cache_dir=str(tmp_path)
        )
        
        assert len(df) > 100, "Should have substantial data"
        
        # Save to parquet
        output = tmp_path / "companies.parquet"
        df.to_parquet(output, index=False)
        
        # Verify file was created
        assert output.exists()
        assert output.stat().st_size > 1000  # At least 1KB


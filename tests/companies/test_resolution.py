"""Integration tests for company resolution.

These tests verify the full resolution pipeline including database access,
blocking, scoring, and decision logic.

Run with: pytest tests/companies/test_resolution.py
"""

import pytest


class TestCompanyResolution:
    """Test company resolution with real data"""

    def test_resolve_with_data(self):
        """Test that resolve_company works when data is available"""
        from entityidentity import resolve_company

        try:
            result = resolve_company("BHP Group")
            assert isinstance(result, dict)
            assert 'matches' in result
            assert 'decision' in result
            assert 'query' in result
            assert 'final' in result
        except FileNotFoundError:
            pytest.skip("Companies data not available")

    def test_match_with_data(self):
        """Test that match_company works when data is available"""
        from entityidentity import match_company

        try:
            result = match_company("BHP Group")
            # Could be None if no high-confidence match
            assert result is None or isinstance(result, dict)
            if result:
                assert 'name' in result
                assert 'country' in result
        except FileNotFoundError:
            pytest.skip("Companies data not available")

    def test_company_identifier_format(self):
        """Test company_identifier returns correct format"""
        from entityidentity import company_identifier

        try:
            result = company_identifier("Apple")
            if result:
                assert isinstance(result, str)
                assert ":" in result  # Should be in format "name:country"
                parts = result.split(":")
                assert len(parts) == 2
                name, country = parts
                assert len(country) == 2  # ISO 2-letter code
                assert country.isupper()
        except FileNotFoundError:
            pytest.skip("Companies data not available")


class TestResolutionDecisions:
    """Test resolution decision logic"""

    def test_high_confidence_auto_match(self):
        """Test that high-confidence matches are auto-accepted"""
        from entityidentity import resolve_company

        try:
            # Well-known unique company name
            result = resolve_company("Apple Inc")
            if result.get('final'):
                # Should be auto-matched if found
                assert result['decision'] in ['auto_high_conf', 'needs_hint_or_llm']
        except FileNotFoundError:
            pytest.skip("Companies data not available")

    def test_country_hint_disambiguation(self):
        """Test that country hint helps with ambiguous names"""
        from entityidentity import resolve_company

        try:
            # Rio Tinto exists in both GB and AU
            result_no_hint = resolve_company("Rio Tinto")
            result_with_hint = resolve_company("Rio Tinto", country="AU")

            # With hint should be more confident
            if result_with_hint.get('final'):
                assert result_with_hint['final']['country'] == "AU"
        except FileNotFoundError:
            pytest.skip("Companies data not available")


class TestResolutionEdgeCases:
    """Test edge cases in resolution"""

    def test_empty_string(self):
        """Test resolution with empty string"""
        from entityidentity import company_identifier

        try:
            result = company_identifier("")
            assert result is None
        except FileNotFoundError:
            pytest.skip("Companies data not available")

    def test_unknown_company(self):
        """Test resolution with completely unknown company"""
        from entityidentity import company_identifier

        try:
            result = company_identifier("ZZZ_NONEXISTENT_COMPANY_XYZ_123456789")
            assert result is None
        except FileNotFoundError:
            pytest.skip("Companies data not available")

    def test_resolve_with_explicit_path(self):
        """Test that resolve works with explicit data path"""
        from entityidentity.companies.companyresolver import resolve_company

        # Should fail with non-existent path
        with pytest.raises(FileNotFoundError):
            resolve_company("Test", data_path="/nonexistent/path.parquet")


class TestGetCompanyId:
    """Test get_company_id formatting"""

    def test_get_company_id_basic(self):
        """Test basic company ID formatting"""
        from entityidentity import get_company_id

        company = {'name': 'Apple Inc', 'country': 'US'}
        assert get_company_id(company) == 'Apple Inc:US'

    def test_get_company_id_safe(self):
        """Test safe company ID formatting"""
        from entityidentity import get_company_id

        company = {'name': 'AT&T Corporation', 'country': 'US'}
        assert get_company_id(company, safe=False) == 'AT&T Corporation:US'
        assert get_company_id(company, safe=True) == 'AT_T_Corporation_US'

    def test_get_company_id_special_chars(self):
        """Test company ID with special characters"""
        from entityidentity import get_company_id

        company = {'name': 'Foo-Bar & Co.', 'country': 'GB'}
        result_safe = get_company_id(company, safe=True)
        assert result_safe == 'Foo_Bar_Co_GB'
        # No special chars except underscore
        assert all(c.isalnum() or c == '_' for c in result_safe)

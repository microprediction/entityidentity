"""Integration tests for the public API.

These tests verify that the main public API (entityidentity/__init__.py)
works correctly across companies, countries, and metals.

Tests focus on:
- Primary API functions (company_identifier, country_identifier, etc.)
- Backwards compatibility with legacy aliases
- Cross-API integration (e.g., company + country resolution together)

For unit tests of specific modules, see:
- companies/test_normalization.py - Company name normalization
- companies/test_resolution.py - Company resolution logic
- test_metals.py - Metal resolution

Run with: pytest tests/test_api.py
"""

import pytest
from entityidentity import (
    company_identifier,
    country_identifier,
    country_identifiers,
    get_identifier,  # Backwards compatibility
)


class TestCompanyIdentifier:
    """Test company_identifier function"""
    
    def test_company_identifier_with_data(self):
        """Test company resolution with actual data"""
        try:
            # Test with a well-known company that should be in dataset
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
    
    def test_company_identifier_with_country_hint(self):
        """Test company resolution with country hint"""
        try:
            result = company_identifier("BHP", "AU")
            if result:
                assert isinstance(result, str)
                assert ":AU" in result or ":GB" in result  # BHP could be Australia or UK
        except FileNotFoundError:
            pytest.skip("Companies data not available")
    
    def test_company_identifier_unknown(self):
        """Test that unknown companies return None"""
        try:
            result = company_identifier("ZZZ_NONEXISTENT_COMPANY_XYZ_123")
            assert result is None
        except FileNotFoundError:
            pytest.skip("Companies data not available")
    
    def test_company_identifier_empty_string(self):
        """Test that empty string returns None"""
        try:
            result = company_identifier("")
            assert result is None
        except FileNotFoundError:
            pytest.skip("Companies data not available")


class TestCountryIdentifier:
    """Test country_identifier function"""
    
    def test_country_identifier_iso2_code(self):
        """Test resolution of ISO2 codes"""
        assert country_identifier("US") == "US"
        assert country_identifier("GB") == "GB"
        assert country_identifier("AU") == "AU"
        assert country_identifier("DE") == "DE"
    
    def test_country_identifier_iso3_code(self):
        """Test resolution of ISO3 codes"""
        assert country_identifier("USA") == "US"
        assert country_identifier("GBR") == "GB"
        assert country_identifier("AUS") == "AU"
        assert country_identifier("DEU") == "DE"
    
    def test_country_identifier_official_names(self):
        """Test resolution of official country names"""
        assert country_identifier("United States") == "US"
        assert country_identifier("United Kingdom") == "GB"
        assert country_identifier("Australia") == "AU"
        assert country_identifier("Germany") == "DE"
    
    def test_country_identifier_colloquial_names(self):
        """Test resolution of colloquial/cultural names"""
        # These are handled by the manual catalog in fuzzycountry
        assert country_identifier("Holland") == "NL"
        assert country_identifier("England") == "GB"
        assert country_identifier("Scotland") == "GB"
        assert country_identifier("Wales") == "GB"
    
    def test_country_identifier_fuzzy_matching(self):
        """Test fuzzy matching for typos"""
        # "Untied States" should fuzzy match to "United States" → US
        result = country_identifier("Untied States")
        assert result == "US"
    
    def test_country_identifier_case_insensitive(self):
        """Test that matching is case-insensitive"""
        assert country_identifier("usa") == "US"
        assert country_identifier("USA") == "US"
        assert country_identifier("UsA") == "US"
    
    def test_country_identifier_unknown(self):
        """Test that unknown countries return None"""
        assert country_identifier("ZZZ_INVALID_XYZ") is None
        assert country_identifier("NotACountry123") is None
    
    def test_country_identifier_empty_string(self):
        """Test that empty string returns None"""
        assert country_identifier("") is None
        assert country_identifier("   ") is None


class TestCountryIdentifiers:
    """Test country_identifiers batch function"""
    
    def test_country_identifiers_batch(self):
        """Test batch resolution of multiple countries"""
        names = ["USA", "Holland", "England", "Germany"]
        results = country_identifiers(names)
        
        assert isinstance(results, list)
        assert len(results) == len(names)
        assert results[0] == "US"
        assert results[1] == "NL"
        assert results[2] == "GB"
        assert results[3] == "DE"
    
    def test_country_identifiers_with_none(self):
        """Test batch resolution with invalid entries"""
        names = ["USA", "INVALID_XYZ", "Germany"]
        results = country_identifiers(names)
        
        assert len(results) == 3
        assert results[0] == "US"
        assert results[1] is None
        assert results[2] == "DE"
    
    def test_country_identifiers_empty_list(self):
        """Test batch resolution with empty list"""
        results = country_identifiers([])
        assert results == []


class TestBackwardsCompatibility:
    """Test backwards compatibility with old API"""
    
    def test_get_identifier_alias(self):
        """Test that get_identifier is still available as alias"""
        # get_identifier should be the same as company_identifier
        assert get_identifier is not None
        
        # It should work the same way
        try:
            result1 = get_identifier("Apple")
            result2 = company_identifier("Apple")
            assert result1 == result2
        except FileNotFoundError:
            pytest.skip("Companies data not available")
    
    def test_get_identifier_with_country(self):
        """Test get_identifier with country parameter"""
        try:
            result = get_identifier("BHP", "AU")
            # Should return same format as company_identifier
            if result:
                assert isinstance(result, str)
                assert ":" in result
        except FileNotFoundError:
            pytest.skip("Companies data not available")


class TestAPIIntegration:
    """Integration tests for the complete API"""
    
    def test_api_functions_importable(self):
        """Test that all main API functions can be imported"""
        from entityidentity import (
            company_identifier,
            country_identifier,
            country_identifiers,
            get_identifier,
            list_companies,
            normalize_company_name,
        )

        assert callable(company_identifier)
        assert callable(country_identifier)
        assert callable(country_identifiers)
        assert callable(get_identifier)
        assert callable(list_companies)
        assert callable(normalize_company_name)
    
    def test_company_and_country_work_together(self):
        """Test that both APIs work together"""
        # Resolve a country
        country_code = country_identifier("United States")
        assert country_code == "US"
        
        # Try to resolve a company (may not have data)
        try:
            company = company_identifier("Apple", country_code)
            if company:
                # Should include the country code
                assert country_code in company
        except FileNotFoundError:
            pytest.skip("Companies data not available")


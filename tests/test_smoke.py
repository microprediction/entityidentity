"""Smoke tests - fast, lightweight tests for basic functionality.

These tests verify that the package imports successfully and core functions
are available. They run quickly (<1 second) and are suitable for CI/CD.

Run with: pytest tests/test_smoke.py
"""

import pytest


class TestPackageBasics:
    """Test basic package functionality"""

    def test_version_exists(self):
        """Test that package version is defined"""
        from entityidentity import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_package_imports(self):
        """Test that package imports successfully"""
        import entityidentity
        assert entityidentity is not None


class TestAPIImports:
    """Test that all primary API functions can be imported"""

    def test_company_api_imports(self):
        """Test company API imports"""
        from entityidentity import (
            company_identifier,
            match_company,
            resolve_company,
            normalize_name,
            extract_companies,
            get_company_id,
        )

        assert callable(company_identifier)
        assert callable(match_company)
        assert callable(resolve_company)
        assert callable(normalize_name)
        assert callable(extract_companies)
        assert callable(get_company_id)

    def test_country_api_imports(self):
        """Test country API imports"""
        from entityidentity import (
            country_identifier,
            country_identifiers,
        )

        assert callable(country_identifier)
        assert callable(country_identifiers)

    def test_metal_api_imports(self):
        """Test metal API imports"""
        from entityidentity import (
            metal_identifier,
            match_metal,
            list_metals,
            extract_metals_from_text,
        )

        assert callable(metal_identifier)
        assert callable(match_metal)
        assert callable(list_metals)
        assert callable(extract_metals_from_text)

    def test_backwards_compatibility_aliases(self):
        """Test that legacy aliases are still available"""
        from entityidentity import company_identifier, get_identifier

        # get_identifier should be available (alias for company_identifier)
        assert callable(get_identifier)
        assert get_identifier is company_identifier or callable(get_identifier)

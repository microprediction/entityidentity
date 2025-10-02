"""Unit tests for company name normalization.

These tests verify the normalization logic without requiring database access.
They run quickly and are suitable for TDD and CI/CD.

Run with: pytest tests/companies/test_normalization.py
"""

import pytest


class TestNormalization:
    """Test company name normalization"""

    def test_normalize_basic(self):
        """Test basic normalization"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("Apple Inc.") == "apple"
        assert normalize_company_name("Microsoft Corporation") == "microsoft"

    def test_normalize_legal_suffixes(self):
        """Test removal of legal suffixes"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("Acme Ltd") == "acme"
        assert normalize_company_name("Acme Limited") == "acme"
        assert normalize_company_name("Foo Bar GmbH") == "foo bar"
        assert normalize_company_name("Example LLC") == "example"
        assert normalize_company_name("BHP Corporation") == "bhp"

    def test_normalize_punctuation(self):
        """Test punctuation handling"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("AT&T") == "at&t"
        assert normalize_company_name("Foo-Bar") == "foo-bar"
        assert normalize_company_name("Test, Inc.") == "test"
        assert normalize_company_name("A.B.C. Corp") == "a b c"

    def test_normalize_unicode(self):
        """Test unicode normalization"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("Café Inc") == "cafe"
        assert normalize_company_name("Zürich AG") == "zurich"

    def test_normalize_whitespace(self):
        """Test whitespace handling"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("  Apple   Inc  ") == "apple"
        assert normalize_company_name("Foo\t\nBar") == "foo bar"

    def test_normalize_empty(self):
        """Test empty string handling"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("") == ""
        assert normalize_company_name("   ") == ""


class TestLegalSuffixes:
    """Test legal suffix patterns"""

    def test_common_suffixes(self):
        """Test common legal suffixes are matched"""
        from entityidentity.companies.companynormalize import LEGAL_RE

        test_cases = [
            "Inc", "Corp", "Ltd", "LLC", "GmbH", "AG", "SA",
            "PLC", "Limited", "Company", "Corporation"
        ]
        for suffix in test_cases:
            text = f"Test {suffix}"
            assert LEGAL_RE.search(text) is not None, f"Should match {suffix}"

    def test_suffix_with_period(self):
        """Test suffixes with trailing period"""
        from entityidentity.companies.companynormalize import LEGAL_RE

        assert LEGAL_RE.search("Test Inc.") is not None
        assert LEGAL_RE.search("Test Ltd.") is not None


class TestEdgeCases:
    """Test edge cases and corner scenarios"""

    def test_all_punctuation(self):
        """Test strings with only punctuation"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("...") == ""
        assert normalize_company_name("!!!") == ""

    def test_very_long_name(self):
        """Test very long company names"""
        from entityidentity import normalize_company_name

        long_name = "A" * 500 + " Corporation"
        result = normalize_company_name(long_name)
        assert len(result) > 0
        assert "corporation" not in result

    def test_mixed_case(self):
        """Test mixed case handling"""
        from entityidentity import normalize_company_name

        assert normalize_company_name("ApPlE InC") == "apple"
        assert normalize_company_name("MICROSOFT") == "microsoft"

    def test_multiple_legal_suffixes(self):
        """Test names with multiple legal suffixes"""
        from entityidentity import normalize_company_name

        # Should remove all legal suffixes
        assert normalize_company_name("Test Inc. Ltd.") == "test"
        assert normalize_company_name("Foo Corp LLC") == "foo"

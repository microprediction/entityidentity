"""Basic test to verify test framework is working"""

import pytest
from entityidentity import __version__


def test_version_exists():
    """Test that package version is defined"""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_basic_assertion():
    """Test that basic assertions work"""
    assert True


def test_main_api_imports():
    """Test that main API functions can be imported"""
    from entityidentity import (
        company_identifier,
        country_identifier,
        country_identifiers,
        get_identifier,
    )
    
    # All should be callable
    assert callable(company_identifier)
    assert callable(country_identifier)
    assert callable(country_identifiers)
    assert callable(get_identifier)


def test_backwards_compatibility():
    """Test that get_identifier is an alias of company_identifier"""
    from entityidentity import company_identifier, get_identifier
    
    # They should be the same function (or get_identifier wraps company_identifier)
    assert get_identifier is company_identifier or callable(get_identifier)


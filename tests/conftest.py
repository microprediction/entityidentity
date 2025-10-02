"""Shared test fixtures and utilities for entityidentity tests."""

import pytest
from functools import wraps
from typing import Callable, TypeVar, Any


F = TypeVar('F', bound=Callable[..., Any])


def skip_if_no_data(func: F) -> F:
    """Decorator to skip tests when companies data is not available.

    This decorator wraps test functions that require companies data to be loaded.
    If the data is not available (FileNotFoundError), the test is skipped with
    an appropriate message.

    Example:
        @skip_if_no_data
        def test_company_resolution():
            result = resolve_company("Apple")
            assert result is not None
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            pytest.skip("Companies data not available")
    return wrapper


@pytest.fixture
def companies_data_required():
    """Fixture that checks if companies data is available.

    This fixture can be used as a test dependency to ensure companies data
    is loaded before the test runs. It will skip the test if data is not available.

    Example:
        def test_with_companies(companies_data_required):
            result = resolve_company("Apple")
            assert result is not None
    """
    try:
        from entityidentity.companies.companyresolver import load_companies
        load_companies()
    except FileNotFoundError:
        pytest.skip("Companies data not available")


@pytest.fixture
def sample_companies():
    """Fixture providing sample company names for testing.

    Returns a list of commonly used test company names.
    """
    return [
        "Apple",
        "Microsoft",
        "BHP",
        "Anglo American",
        "Tesla",
        "Glencore"
    ]


@pytest.fixture
def sample_countries():
    """Fixture providing sample country codes for testing.

    Returns a dict of country names/codes and their ISO2 codes.
    """
    return {
        "USA": "US",
        "United States": "US",
        "United Kingdom": "GB",
        "England": "GB",
        "Australia": "AU",
        "Canada": "CA",
        "Germany": "DE",
        "France": "FR"
    }
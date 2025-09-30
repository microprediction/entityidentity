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


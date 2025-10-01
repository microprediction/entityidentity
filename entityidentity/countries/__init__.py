"""Country entity resolution and identification."""

# Clean API that wraps the robust fuzzycountry implementation
from entityidentity.countries.countryapi import (
    country_identifier,
    country_identifiers,
)

__all__ = [
    "country_identifier",
    "country_identifiers",
]


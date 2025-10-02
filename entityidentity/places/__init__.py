"""Places entity resolution and identification."""

# Clean API that wraps the robust placeidentity implementation
from entityidentity.places.placeapi import (
    load_places,
    place_identifier,
    extract_location,
    match_place,
    list_places,
)

__all__ = [
    "load_places",
    "place_identifier",
    "extract_location",
    "match_place",
    "list_places",
]

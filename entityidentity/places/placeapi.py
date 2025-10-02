"""Places entity resolution API.

Public API for place identification and resolution.
This provides a clean, simple API for resolving admin1 regions (states, provinces, regions)
to canonical place entities with deterministic identifiers.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional, Union
import pandas as pd

# Import robust implementation from placeidentity
from entityidentity.places.placeidentity import (
    resolve_place as _resolve_place,
    topk_matches as _topk_matches,
)
from entityidentity.utils.dataloader import (
    find_data_file,
    load_parquet_or_csv,
    format_not_found_error,
)


@lru_cache(maxsize=1)
def load_places(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load compiled places.parquet into memory.

    Uses LRU cache to load the places DataFrame once and reuse it.
    This provides fast, memory-resident lookups for all place resolution operations.

    Args:
        path: Optional path to places.parquet file. If None, uses default location
              in entityidentity/places/data/places.parquet

    Returns:
        DataFrame with place entities and all metadata columns:
          - place_id: 16-hex deterministic hash
          - place_key: Human-readable slug
          - country: ISO 3166-1 alpha-2 country code (e.g., "US", "AU", "ZA")
          - admin1: Display name (e.g., "Western Australia", "Limpopo")
          - admin1_norm: Normalized admin1 name for matching
          - admin1_code: GeoNames admin1 code (e.g., "WA", "LP")
          - ascii_name: ASCII-safe version of name
          - geonameid: GeoNames ID
          - lat, lon: Coordinates (if available)
          - alias1...alias10: Common aliases and abbreviations
          - attribution: Data source attribution

    Examples:
        >>> df = load_places()
        >>> df[['country', 'admin1', 'admin1_code']].head()
    """
    if path is None:
        # Use shared utility to find data file (places data is in places/data/)
        found_path = find_data_file(
            module_file=__file__,
            subdirectory="places",
            filenames=["places.parquet"],
            search_dev_tables=False,  # Places data only in package, not tables/
            module_local_data=True,  # Check places/data/ directory
        )

        if found_path is None:
            # Generate helpful error message
            places_dir = Path(__file__).parent / "data"
            error_msg = format_not_found_error(
                subdirectory="places",
                searched_locations=[
                    ("Module-local data", places_dir),
                ],
                fix_instructions=[
                    "Run entityidentity/places/data/build_admin1.py to generate it.",
                    "Or download GeoNames admin1CodesASCII.txt and rebuild.",
                ],
            )
            raise FileNotFoundError(error_msg)

        path = found_path

    # Load data using shared utility
    return load_parquet_or_csv(Path(path))


def place_identifier(
    name: str,
    *,
    country_hint: Optional[str] = None,
    threshold: int = 90,
) -> Optional[dict]:
    """Return canonical place row as dict or None.

    Resolves admin1 region names (states, provinces, regions) to canonical place entities
    using country-based blocking and fuzzy matching pipeline.

    Resolution strategy:
      1. Country blocking (if country_hint provided) - reduces 5000 → ~50
      2. Exact match on normalized admin1 name
      3. Exact match on aliases (abbreviations, alternate names)
      4. Prefix blocking (first 3 chars normalized)
      5. Final scoring via RapidFuzz WRatio on names + aliases

    Args:
        name: Admin1 region name
              Examples: "Western Australia", "WA", "Limpopo", "California", "CA"
        country_hint: Optional ISO 3166-1 alpha-2 country code (e.g., "US", "AU", "ZA")
                     If not provided, searches all countries (slower, more ambiguous)
        threshold: Minimum fuzzy match score (0-100). Default 90.

    Returns:
        Dict with canonical place fields, or None if no match above threshold.
        Dict contains: place_id, place_key, country, admin1, admin1_code, lat, lon,
                      geonameid, and all other metadata fields.

    Examples:
        >>> place_identifier("Limpopo", country_hint="ZA")
        {'place_id': '...', 'country': 'ZA', 'admin1': 'Limpopo', 'admin1_code': 'LP', ...}

        >>> place_identifier("Western Australia")
        {'place_id': '...', 'country': 'AU', 'admin1': 'Western Australia', 'admin1_code': 'WA', ...}

        >>> place_identifier("WA", country_hint="AU")
        {'place_id': '...', 'country': 'AU', 'admin1': 'Western Australia', 'admin1_code': 'WA', ...}

        >>> place_identifier("California", country_hint="US")
        {'place_id': '...', 'country': 'US', 'admin1': 'California', 'admin1_code': 'CA', ...}
    """
    df = load_places()
    result = _resolve_place(
        name=name,
        df=df,
        country_hint=country_hint,
        threshold=threshold,
    )

    if result is None:
        return None

    # Convert Series to dict
    return result.to_dict()


def extract_location(text: str, *, country_hint: Optional[str] = None) -> Optional[dict]:
    """Extract first place mention from text.

    Convenience function for extracting place names from unstructured text.
    Currently a simple wrapper around place_identifier. Future versions may
    use NER or more sophisticated extraction.

    Args:
        text: Text containing potential place names
        country_hint: Optional country code to narrow search

    Returns:
        Dict with canonical place fields, or None if no place found

    Examples:
        >>> extract_location("Mining operations in Limpopo province", country_hint="ZA")
        {'place_id': '...', 'country': 'ZA', 'admin1': 'Limpopo', ...}

        >>> extract_location("Western Australia mining", country_hint="AU")
        {'place_id': '...', 'country': 'AU', 'admin1': 'Western Australia', ...}
    """
    # For now, use the text directly as name
    # TODO: Implement proper NER-based extraction in future
    return place_identifier(text, country_hint=country_hint)


def match_place(name: str, *, k: int = 5, country_hint: Optional[str] = None) -> list[dict]:
    """Top-K candidates + scores (for review UIs).

    Returns the top K place candidates with their fuzzy match scores,
    useful for interactive review interfaces, disambiguation, and
    understanding resolution decisions.

    Args:
        name: Admin1 region name to match
        k: Number of top candidates to return. Default 5.
        country_hint: Optional ISO 3166-1 alpha-2 country code

    Returns:
        List of dicts, each containing:
          - All place fields (place_id, country, admin1, etc.)
          - score: Fuzzy match score (0-100)
        Ordered by descending score.

    Examples:
        >>> matches = match_place("Limpopo", k=3, country_hint="ZA")
        >>> for m in matches:
        ...     print(f"{m['admin1']} ({m['country']}) - score: {m['score']}")
        Limpopo (ZA) - score: 100
        ...
    """
    df = load_places()
    results = _topk_matches(name=name, df=df, k=k, country_hint=country_hint)

    # Convert list of (Series, score) tuples to list of dicts with scores
    return [
        {**row.to_dict(), "score": score}
        for row, score in results
    ]


def list_places(country: Optional[str] = None) -> pd.DataFrame:
    """List places filtered by country.

    Returns the places DataFrame filtered by country code.
    Useful for exploring available admin1 regions in specific countries.

    Args:
        country: Optional ISO 3166-1 alpha-2 country code (e.g., "US", "AU", "ZA")
                If None, returns all places.

    Returns:
        Filtered DataFrame with place entities

    Examples:
        >>> za_places = list_places(country="ZA")
        >>> za_places[['admin1', 'admin1_code']].values
        array([['Eastern Cape', 'EC'], ['Free State', 'FS'], ['Gauteng', 'GT'], ...])

        >>> au_places = list_places(country="AU")
        >>> au_places[['admin1', 'admin1_code']].values
        array([['Australian Capital Territory', 'ACT'], ['New South Wales', 'NSW'], ...])
    """
    df = load_places()

    # Apply country filter
    if country is not None:
        country_upper = country.upper()
        df = df[df["country"] == country_upper]

    return df


__all__ = [
    "load_places",
    "place_identifier",
    "extract_location",
    "match_place",
    "list_places",
]

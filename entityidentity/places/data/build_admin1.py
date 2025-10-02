#!/usr/bin/env python3
"""
Build places.parquet from GeoNames admin1CodesASCII.txt following DATA_SOURCES.md specifications.

This script:
1. Downloads GeoNames admin1CodesASCII.txt (or uses local copy)
2. Parses tab-separated format: country.admin1_code, name, ascii_name, geonameid
3. Generates place_id using sha1(country.admin1_code + '|place')[:16]
4. Expands aliases into alias1...alias10 columns
5. Writes places.parquet with all columns as strings
6. Generates validation report for duplicates and missing data

GeoNames admin1CodesASCII.txt format (tab-separated):
- Column 0: country.admin1_code (e.g., "US.CA", "AU.WA", "ZA.LP")
- Column 1: name (UTF-8, e.g., "California", "Western Australia", "Limpopo")
- Column 2: ascii_name (ASCII-safe version)
- Column 3: geonameid (numeric ID)

Attribution required: "Data from GeoNames (geonames.org)" per CC-BY 4.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import pandas as pd

from entityidentity.places.placenormalize import (
    normalize_place_name,
    canonicalize_place_name,
    slugify_place_name,
    generate_place_id,
)
from entityidentity.utils.build_utils import expand_aliases
from entityidentity.utils.build_framework import (
    BuildConfig,
    build_entity_database,
    validate_duplicate_ids,
    validate_duplicate_keys,
    validate_required_fields,
)


GEONAMES_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
ATTRIBUTION = "Data from GeoNames (geonames.org)"


def download_geonames_admin1(output_path: Path) -> Path:
    """Download GeoNames admin1CodesASCII.txt if not present."""
    if output_path.exists():
        print(f"Using existing file: {output_path}")
        return output_path

    print(f"Downloading {GEONAMES_URL}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        urllib.request.urlretrieve(GEONAMES_URL, output_path)
        print(f"Downloaded to: {output_path}")
        return output_path
    except Exception as e:
        raise RuntimeError(f"Failed to download GeoNames data: {e}")


def parse_geonames_admin1(file_path: Path) -> List[dict]:
    """Parse GeoNames admin1CodesASCII.txt into list of dicts."""
    places = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Skip comments
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue

            code_parts = parts[0].split('.')
            if len(code_parts) != 2:
                continue

            country, admin1_code = code_parts
            name = parts[1]
            ascii_name = parts[2]
            geonameid = parts[3]

            # Build aliases list
            aliases = []
            if ascii_name and ascii_name != name:
                aliases.append(ascii_name)

            # Add common variations
            # e.g., "Western Australia" -> ["WA", "West Australia"]
            if " " in name:
                # Add potential abbreviation from words
                abbrev = ''.join(word[0] for word in name.split() if word[0].isupper())
                if abbrev and len(abbrev) >= 2:
                    aliases.append(abbrev)

            places.append({
                'country': country,
                'admin1_code': admin1_code,
                'name': name,
                'ascii_name': ascii_name,
                'geonameid': geonameid,
                'aliases': aliases,
            })

    return places


def process_place(place: dict) -> dict:
    """Convert a place entry to a DataFrame row."""
    country = place['country']
    admin1_code = place['admin1_code']
    name = place['name']

    # Generate IDs
    place_id = generate_place_id(country, admin1_code)
    place_key = slugify_place_name(f"{country}-{name}")

    # Create row with all fields as strings
    row = {
        'place_id': place_id,
        'place_key': place_key,
        'country': country,
        'admin1': canonicalize_place_name(name),
        'admin1_norm': normalize_place_name(name),
        'admin1_code': admin1_code,
        'ascii_name': place.get('ascii_name', ''),
        'geonameid': str(place.get('geonameid', '')),
        'lat': '',  # GeoNames admin1 doesn't include coords; use allCountries.txt if needed
        'lon': '',
        'attribution': ATTRIBUTION,
    }

    # Expand aliases
    row.update(expand_aliases(place.get('aliases', [])))

    return row


def validate_places(df: pd.DataFrame, _: Optional[dict]) -> List[str]:
    """Validate place data and return list of issues."""
    issues = []

    # Check for duplicates
    issues.extend(validate_duplicate_ids(df, 'place_id', 'places'))
    issues.extend(validate_duplicate_keys(df, 'place_key', 'places'))

    # Check for missing country codes
    invalid_countries = df[df['country'].str.len() != 2]
    if not invalid_countries.empty:
        invalid_names = invalid_countries[['admin1', 'country']].to_dict('records')
        issues.append(f"Invalid country codes (not 2-char ISO): {invalid_names}")

    # Check for missing admin1_code
    missing_codes = df[df['admin1_code'] == '']
    if not missing_codes.empty:
        missing_names = missing_codes[['admin1', 'country']].to_dict('records')
        issues.append(f"Missing admin1_code: {missing_names}")

    # Check for required fields
    issues.extend(validate_required_fields(df, ['place_id', 'place_key', 'country', 'admin1', 'admin1_code']))

    return issues


def generate_place_summary(df: pd.DataFrame, _: Optional[dict]) -> None:
    """Print place-specific summary statistics."""
    # Country distribution
    print("\nCountry distribution (top 10):")
    for country, count in df['country'].value_counts().head(10).items():
        print(f"  {country}: {count}")

    # Places with aliases
    with_aliases = df[df['alias1'] != '']
    print(f"\nPlaces with aliases: {len(with_aliases)}")

    # Places with GeoNames ID
    with_geonameid = df[df['geonameid'] != '']
    print(f"Places with GeoNames ID: {len(with_geonameid)}")


def load_geonames_data(data_dir: Path) -> List[dict]:
    """Download and parse GeoNames admin1 data."""
    download_path = data_dir / "admin1CodesASCII.txt"

    # Download if needed
    download_geonames_admin1(download_path)

    # Parse
    return parse_geonames_admin1(download_path)


def main():
    """Main build process."""
    data_dir = Path(__file__).parent

    # Load GeoNames data
    print("Loading GeoNames admin1 data...")
    places = load_geonames_data(data_dir)

    config = BuildConfig(
        input_data=places,  # Use direct data instead of YAML
        output_parquet=data_dir / "places.parquet",
        process_entity=process_place,
        validate_data=validate_places,
        generate_summary=generate_place_summary,
        entity_name="place",
        entity_plural="places",
    )

    return build_entity_database(config)


if __name__ == "__main__":
    sys.exit(main())

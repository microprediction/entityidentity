#!/usr/bin/env python3
"""
Standalone build script for places.parquet from GeoNames admin1CodesASCII.txt.

This version avoids imports from entityidentity package to work around
any import issues in other modules.

Usage:
    python build_admin1_standalone.py
"""

import sys
import hashlib
import unicodedata
import re
from pathlib import Path
from typing import Dict, List
import urllib.request
import pandas as pd


GEONAMES_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
ATTRIBUTION = "Data from GeoNames (geonames.org)"


# ---- Inline normalization functions ----

def normalize_place_name(s: str) -> str:
    """Normalize place name for matching."""
    if not s:
        return ""
    s = s.lower().strip()
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r"[^a-z0-9\s\-()']", '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def canonicalize_place_name(s: str) -> str:
    """Canonicalize place name for display."""
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)
    return s.title()


def slugify_place_name(s: str) -> str:
    """Create URL-safe slug."""
    if not s:
        return ""
    s = s.lower().strip()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^a-z0-9\s\-_]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def generate_place_id(country: str, admin1_code: str) -> str:
    """Generate deterministic place_id."""
    key = f"{country}.{admin1_code}"
    namespaced = f"{key}|place"
    hash_bytes = hashlib.sha1(namespaced.encode("utf-8")).digest()
    return hash_bytes.hex()[:16]


def expand_aliases(aliases: List[str], max_aliases: int = 10) -> Dict[str, str]:
    """Expand aliases into alias1...alias10 columns."""
    result = {}
    for i in range(1, max_aliases + 1):
        if i <= len(aliases):
            result[f'alias{i}'] = aliases[i - 1]
        else:
            result[f'alias{i}'] = ''
    return result


# ---- Download and parse functions ----

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
        'lat': '',
        'lon': '',
        'attribution': ATTRIBUTION,
    }

    # Expand aliases
    row.update(expand_aliases(place.get('aliases', [])))

    return row


def validate_places(df: pd.DataFrame) -> List[str]:
    """Validate place data and return list of issues."""
    issues = []

    # Check for duplicate place_ids
    duplicates = df[df.duplicated(subset=['place_id'], keep=False)]
    if not duplicates.empty:
        dup_names = duplicates[['admin1', 'place_id']].to_dict('records')
        issues.append(f"Duplicate place_ids found: {dup_names}")

    # Check for duplicate place_keys
    dup_keys = df[df.duplicated(subset=['place_key'], keep=False)]
    if not dup_keys.empty:
        dup_key_names = dup_keys[['admin1', 'place_key']].to_dict('records')
        issues.append(f"Duplicate place_keys found: {dup_key_names}")

    # Check for invalid country codes
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
    for field in ['place_id', 'place_key', 'country', 'admin1', 'admin1_code']:
        missing = df[df[field].isna() | (df[field] == "")]
        if not missing.empty:
            missing_names = missing['admin1'].tolist()
            issues.append(f"Missing {field} for entities: {missing_names}")

    return issues


def main():
    """Main build process."""
    data_dir = Path(__file__).parent

    # Download and parse GeoNames data
    print("Building places database from GeoNames admin1CodesASCII.txt")
    print("=" * 60)

    download_path = data_dir / "admin1CodesASCII.txt"
    download_geonames_admin1(download_path)

    print("\nParsing GeoNames data...")
    places = parse_geonames_admin1(download_path)
    print(f"Parsed {len(places)} admin1 regions")

    # Process each place
    print("\nProcessing places...")
    rows = [process_place(place) for place in places]

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Ensure all columns are strings
    for col in df.columns:
        df[col] = df[col].astype(str)
        df[col] = df[col].replace('None', '')

    # Validate data
    print("\nValidating data...")
    issues = validate_places(df)

    if issues:
        print("\n⚠️  Validation issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print()
    else:
        print("✅ All validations passed")

    # Sort by admin1 name
    df = df.sort_values('admin1').reset_index(drop=True)

    # Write to Parquet
    output_path = data_dir / "places.parquet"
    print(f"\nWriting {len(df)} places to {output_path}")
    df.to_parquet(output_path, index=False, engine='pyarrow')

    # Generate summary
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"Total places: {len(df)}")
    print(f"Output file: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")

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

    if issues:
        print(f"\n⚠️  Build completed with {len(issues)} validation issues")
        return 1
    else:
        print("\n✅ Build completed successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())

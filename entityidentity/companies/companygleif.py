"""GLEIF LEI (Legal Entity Identifier) data loader.

The Global Legal Entity Identifier Foundation (GLEIF) provides the LEI Golden Copy,
which contains canonical company names, addresses, and corporate relationships.

Data source: https://www.gleif.org/en/lei-data/gleif-concatenated-file
Updated: 3 times daily
Format: XML or CSV concatenated files
"""

from __future__ import annotations
import requests
import zipfile
import io
from typing import Optional, Dict, Any, List
from pathlib import Path
import pandas as pd


# GLEIF concatenated file endpoints
GLEIF_LEVEL1_URL = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest/download"
GLEIF_LEVEL2_URL = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/rr/latest/download"


def load_gleif_lei(
    cache_dir: Optional[str] = None,
    level: int = 1,
    max_records: Optional[int] = None,
) -> pd.DataFrame:
    """Load GLEIF LEI data.
    
    Level 1: Basic entity data (name, address, status, registration)
    Level 2: Relationship data (parent-child, branches)
    
    Args:
        cache_dir: Directory to cache downloaded files
        level: 1 for entity data, 2 for relationships
        max_records: Limit number of records (for testing)
        
    Returns:
        DataFrame with columns:
        - lei: Legal Entity Identifier (20-char alphanumeric)
        - name: Legal name
        - country: ISO 3166-1 alpha-2 country code
        - address: Full address
        - city: City
        - postal_code: Postal/ZIP code
        - status: LEI status (ISSUED, LAPSED, etc.)
        - registration_authority: Local registration authority
        - registration_id: Local registration number
        
    Raises:
        requests.HTTPError: If download fails
        
    Note:
        The full dataset is ~3GB compressed, ~30GB uncompressed.
        Contains ~2.5M active entities globally.
        This function downloads the CSV format for easier parsing.
    """
    if cache_dir:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        cached_file = cache_path / f"gleif_level{level}.csv"
        if cached_file.exists():
            df = pd.read_csv(cached_file, nrows=max_records)
            return df
    
    # Download GLEIF data
    url = GLEIF_LEVEL1_URL if level == 1 else GLEIF_LEVEL2_URL
    
    print(f"Downloading GLEIF Level {level} data from {url}...")
    print("This may take several minutes (file is ~3GB)...")
    
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    
    # The file is a ZIP containing CSV or XML
    # For simplicity, we'll expect CSV format
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        # Find the CSV file in the archive
        csv_files = [f for f in zf.namelist() if f.endswith('.csv')]
        if not csv_files:
            raise ValueError("No CSV file found in GLEIF archive")
        
        with zf.open(csv_files[0]) as csv_file:
            df = pd.read_csv(csv_file, nrows=max_records)
    
    # Normalize column names (GLEIF uses specific column names)
    # This is a simplified mapping - actual GLEIF format may vary
    if level == 1:
        df = _normalize_gleif_level1(df)
    
    # Cache if requested
    if cache_dir and cached_file:
        df.to_csv(cached_file, index=False)
        print(f"Cached to {cached_file}")
    
    return df


def _normalize_gleif_level1(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize GLEIF Level 1 columns to our schema.
    
    GLEIF Level 1 columns include:
    - LEI
    - Entity.LegalName
    - Entity.LegalAddress.Country
    - Entity.LegalAddress.City
    - Entity.LegalAddress.PostalCode
    - Entity.LegalAddress.AddressLines
    - Entity.RegistrationAuthority.RegistrationAuthorityID
    - Entity.RegistrationAuthority.RegistrationAuthorityEntityID
    - Registration.RegistrationStatus
    """
    # Map GLEIF columns to our schema
    # Note: Actual column names may differ - adjust based on real data
    column_mapping = {
        'LEI': 'lei',
        'Entity.LegalName': 'name',
        'Entity.LegalAddress.Country': 'country',
        'Entity.LegalAddress.City': 'city',
        'Entity.LegalAddress.PostalCode': 'postal_code',
        'Registration.RegistrationStatus': 'status',
        'Entity.RegistrationAuthority.RegistrationAuthorityID': 'registration_authority',
        'Entity.RegistrationAuthority.RegistrationAuthorityEntityID': 'registration_id',
    }
    
    # Rename columns that exist
    rename_map = {old: new for old, new in column_mapping.items() if old in df.columns}
    df = df.rename(columns=rename_map)
    
    # Build full address from components if needed
    if 'address' not in df.columns:
        address_cols = [c for c in df.columns if 'AddressLine' in c or 'Address.Line' in c]
        if address_cols:
            df['address'] = df[address_cols].fillna('').agg(' '.join, axis=1).str.strip()
    
    # Ensure required columns exist
    required = ['lei', 'name', 'country']
    for col in required:
        if col not in df.columns:
            df[col] = None
    
    return df


def sample_gleif_data() -> pd.DataFrame:
    """Return a small sample of GLEIF-like data for testing.
    
    Returns:
        DataFrame with sample company data
    """
    data = [
        {
            'lei': '529900HNOAA1KXQJUQ27',
            'name': 'Apple Inc.',
            'country': 'US',
            'city': 'Cupertino',
            'address': 'One Apple Park Way',
            'postal_code': '95014',
            'status': 'ISSUED',
            'registration_authority': 'RA000665',
            'registration_id': 'C0806592',
        },
        {
            'lei': '549300FX7K9QRXDE7E94',
            'name': 'Microsoft Corporation',
            'country': 'US',
            'city': 'Redmond',
            'address': 'One Microsoft Way',
            'postal_code': '98052',
            'status': 'ISSUED',
            'registration_authority': 'RA000676',
            'registration_id': '600413485',
        },
        {
            'lei': 'RR3QWICWWIPCS8A4S074',
            'name': 'Tesla, Inc.',
            'country': 'US',
            'city': 'Austin',
            'address': '13101 Tesla Road',
            'postal_code': '78725',
            'status': 'ISSUED',
            'registration_authority': 'RA000665',
            'registration_id': 'C3232779',
        },
    ]
    return pd.DataFrame(data)


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


# GLEIF API endpoints
GLEIF_API_BASE = "https://api.gleif.org/api/v1"
GLEIF_LEI_RECORDS_URL = f"{GLEIF_API_BASE}/lei-records"
GLEIF_RATE_LIMIT = 60  # requests per minute


def load_gleif_lei(
    cache_dir: Optional[str] = None,
    level: int = 1,
    max_records: Optional[int] = None,
) -> pd.DataFrame:
    """Load GLEIF LEI data via REST API.
    
    Args:
        cache_dir: Directory to cache downloaded files
        level: 1 for entity data (only level 1 currently supported)
        max_records: Limit number of records (for testing). Default 10,000.
        
    Returns:
        DataFrame with columns:
        - lei: Legal Entity Identifier (20-char alphanumeric)
        - name: Legal name
        - country: ISO 3166-1 alpha-2 country code
        - address: Full address
        - city: City
        - postal_code: Postal/ZIP code
        - status: LEI status (ISSUED, LAPSED, etc.)
        
    Raises:
        requests.HTTPError: If API request fails
        
    Note:
        The full dataset contains ~3M active entities globally.
        This function uses the GLEIF REST API with pagination.
        Rate limit: 60 requests per minute.
    """
    import time
    from tqdm import tqdm
    
    if level != 1:
        raise NotImplementedError("Only level 1 (basic entity data) is currently supported")
    
    if cache_dir:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        cached_file = cache_path / f"gleif_lei_{max_records or 'all'}.parquet"
        if cached_file.exists():
            print(f"Loading from cache: {cached_file}")
            df = pd.read_parquet(cached_file)
            if max_records:
                df = df.head(max_records)
            return df
    
    # Set default max_records
    if max_records is None:
        max_records = 10000
    
    print(f"Fetching {max_records:,} LEI records from GLEIF API...")
    print(f"API: {GLEIF_LEI_RECORDS_URL}")
    
    # Fetch paginated data
    page_size = 200  # Max records per request
    num_pages = (max_records + page_size - 1) // page_size
    
    all_records = []
    for page_num in tqdm(range(1, num_pages + 1), desc="Fetching pages"):
        params = {
            'page[number]': page_num,
            'page[size]': min(page_size, max_records - len(all_records)),
        }
        
        try:
            response = requests.get(GLEIF_LEI_RECORDS_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Extract records from JSON API format
            if 'data' in data:
                all_records.extend(data['data'])
            
            if len(all_records) >= max_records:
                break
                
            # Respect rate limiting (60 req/min = 1 req per second)
            time.sleep(1.1)
            
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to fetch page {page_num}: {e}")
            if len(all_records) == 0:
                raise
            break
    
    print(f"Fetched {len(all_records):,} records")
    
    # Parse JSON records into DataFrame
    df = _parse_gleif_json(all_records)
    
    # Cache if requested
    if cache_dir and cached_file:
        df.to_parquet(cached_file, index=False)
        print(f"Cached to {cached_file}")
    
    return df


def _parse_gleif_json(records: List[Dict]) -> pd.DataFrame:
    """Parse GLEIF JSON API records into DataFrame.
    
    Args:
        records: List of JSON records from GLEIF API
        
    Returns:
        DataFrame with normalized columns
    """
    rows = []
    for record in records:
        attrs = record.get('attributes', {})
        entity = attrs.get('entity', {})
        registration = attrs.get('registration', {})
        legal_addr = entity.get('legalAddress', {})
        
        # Extract data
        row = {
            'lei': attrs.get('lei'),
            'name': entity.get('legalName', {}).get('name'),
            'country': legal_addr.get('country'),
            'city': legal_addr.get('city'),
            'postal_code': legal_addr.get('postalCode'),
            'address': ' '.join(legal_addr.get('addressLines', [])).strip() or None,
            'status': entity.get('status'),
        }
        rows.append(row)
    
    return pd.DataFrame(rows)


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


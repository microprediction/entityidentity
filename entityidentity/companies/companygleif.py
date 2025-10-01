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
    
    # Determine how many records to fetch
    if max_records is None:
        print(f"Fetching ALL LEI records from GLEIF API (~2.5M records)...")
        print(f"This will take approximately 30-45 minutes...")
        print(f"API: {GLEIF_LEI_RECORDS_URL}")
        # We'll fetch pages until we get no more data
        fetch_all = True
        num_pages = None  # Unknown
    else:
        print(f"Fetching {max_records:,} LEI records from GLEIF API...")
        print(f"API: {GLEIF_LEI_RECORDS_URL}")
        fetch_all = False
        page_size = 200  # Max records per request
        num_pages = (max_records + page_size - 1) // page_size
    
    all_records = []
    page_size = 200  # Max records per request
    
    # For incremental saving during long downloads
    temp_cache_file = None
    resume_from_page = 0
    if cache_dir and fetch_all:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        temp_cache_file = cache_path / "gleif_full_temp.parquet"
        
        # Clean up any incomplete write
        temp_write_file = cache_path / f"{temp_cache_file.name}.writing"
        if temp_write_file.exists():
            print(f"Removing incomplete write: {temp_write_file}")
            temp_write_file.unlink()
        
        # Check if we have a partial download to resume
        if temp_cache_file.exists():
            print(f"\n✅ Found partial download: {temp_cache_file}")
            print(f"   File size: {temp_cache_file.stat().st_size / 1024 / 1024:.1f} MB")
            try:
                temp_df = pd.read_parquet(temp_cache_file)
                # Convert back to raw JSON format for API
                # This is a workaround - we'll skip already-fetched pages
                resume_from_page = len(temp_df) // page_size
                print(f"   Records: {len(temp_df):,}")
                print(f"   Resuming from page: {resume_from_page:,}")
                print(f"\n⚠️  Note: Will re-download from page {resume_from_page}")
                print(f"   (Cannot resume mid-page with current API)")
                print()
            except Exception as e:
                print(f"⚠️  Could not load temp file: {e}")
                print(f"   Starting fresh download...")
                try:
                    temp_cache_file.unlink()
                except:
                    pass
    
    if fetch_all:
        # Fetch all pages until no more data
        page_num = resume_from_page + 1 if resume_from_page > 0 else 1
        save_interval = 100  # Save every 100 pages (~20K records)
        last_save = resume_from_page
        
        # Estimate: ~2.5M records / 200 per page = ~12,500 pages
        estimated_total_pages = 12500
        
        with tqdm(
            desc="Fetching GLEIF", 
            unit="page", 
            initial=resume_from_page,
            total=estimated_total_pages,
            bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}'
        ) as pbar:
            while True:
                params = {
                    'page[number]': page_num,
                    'page[size]': page_size,
                }
                
                try:
                    response = requests.get(GLEIF_LEI_RECORDS_URL, params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extract records from JSON API format
                    if 'data' in data and len(data['data']) > 0:
                        all_records.extend(data['data'])
                        pbar.update(1)
                        
                        # Show records in millions for readability
                        records_str = f"{len(all_records)/1000:.1f}K" if len(all_records) < 1000000 else f"{len(all_records)/1000000:.2f}M"
                        pbar.set_postfix_str(f"{records_str} records")
                        page_num += 1
                        
                        # Incremental save to temp file
                        if temp_cache_file and (page_num - last_save) >= save_interval:
                            try:
                                # Atomic write: write to temp, then rename
                                temp_write_file = temp_cache_file.parent / f"{temp_cache_file.name}.writing"
                                temp_df = _parse_gleif_json(all_records)
                                temp_df.to_parquet(temp_write_file, index=False)
                                # Atomic rename (overwrites old temp file)
                                temp_write_file.replace(temp_cache_file)
                                last_save = page_num
                                pbar.set_postfix_str(f"{records_str} records [saved ✓]")
                            except Exception as e:
                                pbar.set_postfix_str(f"{records_str} records [save failed: {e}]")
                                # Continue downloading even if save fails
                    else:
                        # No more data
                        break
                        
                except requests.exceptions.RequestException as e:
                    print(f"\n⚠️  Error fetching page {page_num}: {e}")
                    if len(all_records) > 0:
                        print(f"Saving {len(all_records):,} records before exit...")
                        # Save what we have
                        if temp_cache_file:
                            try:
                                # Atomic write
                                temp_write_file = temp_cache_file.parent / f"{temp_cache_file.name}.writing"
                                temp_df = _parse_gleif_json(all_records)
                                temp_df.to_parquet(temp_write_file, index=False)
                                temp_write_file.replace(temp_cache_file)
                                print(f"✅ Saved to: {temp_cache_file}")
                                print(f"   To resume: run the same command again")
                            except Exception as save_error:
                                print(f"❌ Failed to save: {save_error}")
                                print(f"   {len(all_records):,} records will be lost!")
                        break
                    else:
                        raise
                except KeyboardInterrupt:
                    print(f"\n\n⚠️  Download interrupted by user")
                    if len(all_records) > 0:
                        print(f"Saving {len(all_records):,} records before exit...")
                        if temp_cache_file:
                            try:
                                temp_write_file = temp_cache_file.parent / f"{temp_cache_file.name}.writing"
                                temp_df = _parse_gleif_json(all_records)
                                temp_df.to_parquet(temp_write_file, index=False)
                                temp_write_file.replace(temp_cache_file)
                                print(f"✅ Saved to: {temp_cache_file}")
                                print(f"   To resume: run the same command again")
                            except Exception as save_error:
                                print(f"❌ Failed to save: {save_error}")
                        raise
                    else:
                        raise
                
                # Rate limiting
                time.sleep(1 / GLEIF_RATE_LIMIT * 60)  # Respect rate limit
    else:
        # Fetch limited number of pages
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
                    
            except requests.exceptions.RequestException as e:
                print(f"\n⚠️  Error fetching page {page_num}: {e}")
                if len(all_records) == 0:
                    raise
                break
            
            # Respect rate limiting (60 req/min = 1 req per second)
            time.sleep(1.1)
    
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


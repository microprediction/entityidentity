#!/usr/bin/env python3
"""Build consolidated companies.parquet from multiple data sources.

This module fetches company data from:
- GLEIF LEI (global legal entities)
- Wikidata (rich metadata and aliases)
- Stock exchanges (ASX, LSE, TSX, etc.)

And consolidates them into a single normalized companies.parquet file
for use with the company identity resolution system.

Primary API:
    consolidate_companies() - Main function to build the consolidated dataset

CLI Usage (for basic testing):
    python -m entityidentity.build_companies_db [--output companies.parquet] [--use-samples]

For production use with full CLI features, use:
    python scripts/companies/build_database_cli.py
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import List, Optional
import pandas as pd
from entityidentity.companies.companynormalize import normalize_company_name, canonicalize_company_name

# Import loaders
from entityidentity.companies.companygleif import load_gleif_lei, sample_gleif_data
from entityidentity.companies.companywikidata import load_wikidata_companies, sample_wikidata_data
from entityidentity.companies.companyexchanges import (
    load_asx, sample_asx_data,
    load_lse, sample_lse_data,
    sample_tsx_data,
)


def consolidate_companies(
    use_samples: bool = False,
    cache_dir: Optional[str] = None,
    max_companies: Optional[int] = None,
) -> pd.DataFrame:
    """Consolidate company data from all sources.
    
    Args:
        use_samples: Use sample data instead of downloading (for testing)
        cache_dir: Directory to cache downloaded files
        max_companies: Maximum number of companies to fetch from GLEIF (default: 10,000)
        
    Returns:
        Consolidated DataFrame with standardized schema
    """
    companies_dfs = []
    
    # 1. GLEIF LEI data (Tier 1 - highest quality)
    print("\n=== Loading GLEIF LEI data ===")
    if use_samples:
        gleif_df = sample_gleif_data()
        print(f"Using sample GLEIF data: {len(gleif_df)} companies")
    else:
        try:
            max_records = max_companies if max_companies else 10000
            gleif_df = load_gleif_lei(cache_dir=cache_dir, max_records=max_records)
            print(f"Loaded {len(gleif_df)} companies from GLEIF")
        except Exception as e:
            print(f"Failed to load GLEIF data: {e}")
            print("Using sample data instead")
            gleif_df = sample_gleif_data()
    
    gleif_df['source'] = 'GLEIF'
    companies_dfs.append(_normalize_gleif(gleif_df))
    
    # 2. Wikidata (Tier 1 - rich metadata)
    print("\n=== Loading Wikidata ===")
    if use_samples:
        wikidata_df = sample_wikidata_data()
        print(f"Using sample Wikidata: {len(wikidata_df)} companies")
    else:
        try:
            wikidata_df = load_wikidata_companies(limit=10000)
            print(f"Loaded {len(wikidata_df)} companies from Wikidata")
        except Exception as e:
            print(f"Failed to load Wikidata: {e}")
            print("Using sample data instead")
            wikidata_df = sample_wikidata_data()
    
    wikidata_df['source'] = 'Wikidata'
    companies_dfs.append(_normalize_wikidata(wikidata_df))
    
    # 3. Stock Exchanges (Tier 2)
    print("\n=== Loading stock exchanges ===")
    
    # ASX
    if use_samples:
        asx_df = sample_asx_data()
    else:
        try:
            asx_df = load_asx(cache_dir=cache_dir)
        except:
            asx_df = sample_asx_data()
    asx_df['source'] = 'ASX'
    companies_dfs.append(_normalize_exchange(asx_df))
    print(f"ASX: {len(asx_df)} companies")
    
    # LSE
    if use_samples:
        lse_df = sample_lse_data()
    else:
        try:
            lse_df = load_lse(cache_dir=cache_dir)
        except:
            lse_df = sample_lse_data()
    lse_df['source'] = 'LSE'
    companies_dfs.append(_normalize_exchange(lse_df))
    print(f"LSE: {len(lse_df)} companies")
    
    # TSX (sample only for now)
    tsx_df = sample_tsx_data()
    tsx_df['source'] = 'TSX'
    companies_dfs.append(_normalize_exchange(tsx_df))
    print(f"TSX: {len(tsx_df)} companies")
    
    # Combine all sources
    print("\n=== Consolidating data ===")
    combined = pd.concat(companies_dfs, ignore_index=True)
    
    # Filter out companies with empty names
    original_count = len(combined)
    combined = combined[combined['name'].notna() & (combined['name'] != '')].copy()
    if len(combined) < original_count:
        print(f"Removed {original_count - len(combined)} companies with empty names")
    
    # Define source priority (highest to lowest)
    # GLEIF: Official legal names from regulatory filings
    # Wikidata: Crowdsourced but generally well-curated
    # Exchanges: Often inconsistent formatting (ALL CAPS, etc.)
    SOURCE_PRIORITY = {
        'GLEIF': 1,
        'Wikidata': 2,
        'ASX': 3,
        'LSE': 3,
        'TSX': 3,
    }
    
    # Add priority column for sorting
    combined['_priority'] = combined['source'].map(SOURCE_PRIORITY).fillna(99)
    
    # Sort by priority (lower number = higher priority)
    combined = combined.sort_values('_priority')
    
    # Deduplicate based on LEI (if available), then by normalized name + country
    print(f"Total records before deduplication: {len(combined)}")
    
    # First pass: dedupe by LEI, keeping highest priority source
    lei_records = combined[combined['lei'].notna() & (combined['lei'] != '')]
    no_lei_records = combined[~combined.index.isin(lei_records.index)]
    
    # Keep first (highest priority due to sorting)
    lei_deduped = lei_records.drop_duplicates(subset=['lei'], keep='first')
    print(f"Deduplicated {len(lei_records) - len(lei_deduped)} records by LEI (kept highest priority source)")
    
    # Second pass: dedupe non-LEI records by name_norm + country, keeping highest priority
    no_lei_deduped = no_lei_records.drop_duplicates(
        subset=['name_norm', 'country'], 
        keep='first'
    )
    print(f"Deduplicated {len(no_lei_records) - len(no_lei_deduped)} records by name+country (kept highest priority source)")
    
    final = pd.concat([lei_deduped, no_lei_deduped], ignore_index=True)
    
    # Remove temporary priority column
    final = final.drop(columns=['_priority'])
    
    print(f"\nFinal dataset: {len(final)} unique companies")
    print(f"  - With LEI: {final['lei'].notna().sum()}")
    print(f"  - With Wikidata QID: {final['wikidata_qid'].notna().sum()}")
    print(f"  - By source: {final['source'].value_counts().to_dict()}")
    print(f"  - By country: {final['country'].value_counts().head()}")
    
    return final


# Standard output schema for all data sources
_STANDARD_COLUMNS = [
    'name', 'name_norm', 'country', 'lei', 'wikidata_qid',
    'alias1', 'alias2', 'alias3', 'alias4', 'alias5',
    'address', 'city', 'postal_code', 'source'
]


def _normalize_to_schema(
    df: pd.DataFrame,
    *,
    has_lei: bool = False,
    has_wikidata_qid: bool = False,
    has_aliases: bool = False,
    has_address_fields: bool = False,
    ticker_to_alias: bool = False,
) -> pd.DataFrame:
    """Normalize any data source to standard schema.

    This is the base normalization function used by all data loaders.
    Handles name canonicalization, column creation, and schema standardization.

    Args:
        df: Input DataFrame from any source
        has_lei: Source provides LEI column
        has_wikidata_qid: Source provides wikidata_qid column
        has_aliases: Source provides alias columns or aliases list
        has_address_fields: Source provides address/city/postal_code
        ticker_to_alias: Copy ticker column to alias1 (for exchanges)

    Returns:
        DataFrame with standardized schema
    """
    df = df.copy()

    # Step 1: Canonicalize and normalize company names
    df['name'] = df['name'].apply(canonicalize_company_name)
    df['name_norm'] = df['name'].apply(normalize_company_name)

    # Step 2: Handle LEI column
    if not has_lei:
        df['lei'] = None

    # Step 3: Handle Wikidata QID column
    if not has_wikidata_qid:
        df['wikidata_qid'] = None

    # Step 4: Handle alias columns
    if has_aliases:
        # Check if already has flat alias columns
        if 'alias1' not in df.columns:
            # Convert from 'aliases' list column to flat columns
            def extract_aliases(row):
                aliases = row.get('aliases', []) if 'aliases' in df.columns else []
                if not isinstance(aliases, list):
                    aliases = []
                return {f'alias{i}': aliases[i-1] if i-1 < len(aliases) else None
                        for i in range(1, 6)}

            alias_cols = df.apply(extract_aliases, axis=1, result_type='expand')
            df = pd.concat([df, alias_cols], axis=1)
    else:
        # Create empty alias columns
        if ticker_to_alias and 'ticker' in df.columns:
            df['alias1'] = df['ticker']
            for i in range(2, 6):
                df[f'alias{i}'] = None
        else:
            for i in range(1, 6):
                df[f'alias{i}'] = None

    # Ensure all alias columns exist
    for i in range(1, 6):
        if f'alias{i}' not in df.columns:
            df[f'alias{i}'] = None

    # Step 5: Handle address fields
    if not has_address_fields:
        df['address'] = None
        df['city'] = None
        df['postal_code'] = None

    # Step 6: Return only standard columns in standard order
    return df[_STANDARD_COLUMNS]


def _normalize_gleif(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize GLEIF data to standard schema.

    GLEIF provides: name, country, lei, address fields
    GLEIF does NOT provide: aliases, wikidata_qid
    """
    return _normalize_to_schema(
        df,
        has_lei=True,
        has_wikidata_qid=False,
        has_aliases=False,
        has_address_fields=True,
    )


def _normalize_wikidata(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Wikidata to standard schema.

    Wikidata provides: name, country, lei (sometimes), wikidata_qid, aliases
    Wikidata does NOT provide: address fields
    """
    return _normalize_to_schema(
        df,
        has_lei=True,  # Sometimes present
        has_wikidata_qid=True,
        has_aliases=True,
        has_address_fields=False,
    )


def _normalize_exchange(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize stock exchange data to standard schema.

    Exchanges provide: name, country, ticker
    Exchanges do NOT provide: lei, wikidata_qid, address fields

    Ticker is mapped to alias1 for matching purposes.
    """
    return _normalize_to_schema(
        df,
        has_lei=False,
        has_wikidata_qid=False,
        has_aliases=False,
        has_address_fields=False,
        ticker_to_alias=True,
    )


def main():
    """Simple CLI entry point for basic testing.

    For production use with full features (backup, incremental updates, etc.),
    use scripts/companies/build_database_cli.py instead.
    """
    parser = argparse.ArgumentParser(
        description="Build consolidated companies database from multiple sources (basic CLI)",
        epilog="For production use with full features, use: python scripts/companies/build_database_cli.py"
    )
    parser.add_argument(
        '--output', '-o',
        default='companies.parquet',
        help='Output file path (default: companies.parquet)'
    )
    parser.add_argument(
        '--use-samples', '-s',
        action='store_true',
        help='Use sample data instead of downloading (for testing)'
    )
    parser.add_argument(
        '--cache-dir', '-c',
        default=None,
        help='Directory to cache downloaded files'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['parquet', 'csv'],
        default='parquet',
        help='Output format (default: parquet)'
    )

    args = parser.parse_args()

    # Build consolidated dataset
    print("=== Building Companies Database (Basic Mode) ===")
    print(f"Output: {args.output}")
    print(f"Format: {args.format}")
    print(f"Using samples: {args.use_samples}")
    print("\nNote: For full features (backup, incremental updates, info files),")
    print("use: python scripts/companies/build_database_cli.py")
    print()

    companies = consolidate_companies(
        use_samples=args.use_samples,
        cache_dir=args.cache_dir,
    )

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == 'parquet':
        companies.to_parquet(output_path, index=False, compression='snappy')
    else:
        companies.to_csv(output_path, index=False)

    print(f"\n✅ Saved {len(companies)} companies to {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == '__main__':
    main()


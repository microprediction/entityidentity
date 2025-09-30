#!/usr/bin/env python3
"""Build consolidated companies.parquet from multiple data sources.

This script fetches company data from:
- GLEIF LEI (global legal entities)
- Wikidata (rich metadata and aliases)
- Stock exchanges (ASX, LSE, TSX, etc.)

And consolidates them into a single normalized companies.parquet file
for use with the company identity resolution system.

Usage:
    python -m entityidentity.build_companies_db [--output companies.parquet] [--use-samples]
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import List, Optional
import pandas as pd
from entityidentity.companies.companyidentity import normalize_name

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
) -> pd.DataFrame:
    """Consolidate company data from all sources.
    
    Args:
        use_samples: Use sample data instead of downloading (for testing)
        cache_dir: Directory to cache downloaded files
        
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
            gleif_df = load_gleif_lei(cache_dir=cache_dir, max_records=10000)
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
    
    # Deduplicate based on LEI (if available), then by normalized name + country
    print(f"Total records before deduplication: {len(combined)}")
    
    # First pass: dedupe by LEI
    lei_records = combined[combined['lei'].notna() & (combined['lei'] != '')]
    no_lei_records = combined[~combined.index.isin(lei_records.index)]
    
    lei_deduped = lei_records.drop_duplicates(subset=['lei'], keep='first')
    print(f"Deduplicated {len(lei_records) - len(lei_deduped)} records by LEI")
    
    # Second pass: dedupe non-LEI records by name_norm + country
    no_lei_deduped = no_lei_records.drop_duplicates(
        subset=['name_norm', 'country'], 
        keep='first'
    )
    print(f"Deduplicated {len(no_lei_records) - len(no_lei_deduped)} records by name+country")
    
    final = pd.concat([lei_deduped, no_lei_deduped], ignore_index=True)
    
    print(f"\nFinal dataset: {len(final)} unique companies")
    print(f"  - With LEI: {final['lei'].notna().sum()}")
    print(f"  - With Wikidata QID: {final['wikidata_qid'].notna().sum()}")
    print(f"  - By country: {final['country'].value_counts().head()}")
    
    return final


def _normalize_gleif(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize GLEIF data to standard schema."""
    df = df.copy()
    df['name_norm'] = df['name'].apply(normalize_name)
    df['aliases'] = [[]] * len(df)  # GLEIF doesn't provide aliases
    df['wikidata_qid'] = None
    df['stock_ticker'] = None
    return df[['name', 'name_norm', 'country', 'lei', 'wikidata_qid', 
               'aliases', 'address', 'city', 'postal_code', 'source']]


def _normalize_wikidata(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Wikidata to standard schema."""
    df = df.copy()
    df['name_norm'] = df['name'].apply(normalize_name)
    df['address'] = None
    df['city'] = None
    df['postal_code'] = None
    return df[['name', 'name_norm', 'country', 'lei', 'wikidata_qid',
               'aliases', 'address', 'city', 'postal_code', 'source']]


def _normalize_exchange(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize stock exchange data to standard schema."""
    df = df.copy()
    df['name_norm'] = df['name'].apply(normalize_name)
    df['lei'] = None
    df['wikidata_qid'] = None
    df['aliases'] = [[]] * len(df)
    df['address'] = None
    df['city'] = None
    df['postal_code'] = None
    
    # Use ticker as alias if available
    if 'ticker' in df.columns:
        df['aliases'] = df['ticker'].apply(lambda x: [x] if pd.notna(x) else [])
    
    return df[['name', 'name_norm', 'country', 'lei', 'wikidata_qid',
               'aliases', 'address', 'city', 'postal_code', 'source']]


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build consolidated companies database from multiple sources"
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
    print("=== Building Companies Database ===")
    print(f"Output: {args.output}")
    print(f"Format: {args.format}")
    print(f"Using samples: {args.use_samples}")
    
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


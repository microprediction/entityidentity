#!/usr/bin/env python3
"""
Fuzzy match exchange companies to GLEIF database.

Strategy:
1. Load exchange data (ASX, LSE, TSX)
2. Load cached GLEIF data (2.5M records)
3. Fuzzy match exchange names → GLEIF names
4. Output: GLEIF records that match exchanges

This filters 2.5M GLEIF → ~2.5K exchange-listed companies
BEFORE running expensive LLM classification.

Output: .cache/companies/gleif_exchange_matched.parquet (~2K records)
Time: ~2 minutes
Cost: FREE (local processing)
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from entityidentity.companies.companyexchanges import load_asx, load_lse, load_tsx
from entityidentity.companies.companynormalize import canonicalize_company_name
from rapidfuzz import fuzz, process


def load_exchanges():
    """Load data from major mining exchanges."""
    print("=" * 70)
    print("Loading Exchange Data")
    print("=" * 70)
    
    exchanges = []
    
    # ASX
    print("\n📊 ASX (Australian Securities Exchange)...")
    try:
        asx = load_asx()
        print(f"   Loaded: {len(asx):,} companies")
        exchanges.append(asx)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    # LSE
    print("\n📊 LSE (London Stock Exchange)...")
    try:
        lse = load_lse()
        print(f"   Loaded: {len(lse):,} companies")
        exchanges.append(lse)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    # TSX
    print("\n📊 TSX (Toronto Stock Exchange)...")
    try:
        tsx = load_tsx()
        print(f"   Loaded: {len(tsx):,} companies")
        exchanges.append(tsx)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    if exchanges:
        combined = pd.concat(exchanges, ignore_index=True)
        print(f"\n✅ Total: {len(combined):,} exchange companies")
        return combined
    else:
        print("\n❌ No exchange data loaded!")
        return pd.DataFrame()


def fuzzy_match_to_gleif(exchange_df, gleif_df, threshold=85):
    """
    Fuzzy match exchange companies to GLEIF database.
    
    Args:
        exchange_df: DataFrame with exchange companies
        gleif_df: DataFrame with GLEIF data
        threshold: Minimum similarity score (0-100)
    
    Returns:
        DataFrame with matched GLEIF records
    """
    print("\n" + "=" * 70)
    print("Fuzzy Matching Exchange → GLEIF")
    print("=" * 70)
    
    print(f"\n📊 Input:")
    print(f"   Exchange companies: {len(exchange_df):,}")
    print(f"   GLEIF companies: {len(gleif_df):,}")
    print(f"   Match threshold: {threshold}%")
    
    # Build GLEIF lookup by country
    print(f"\n🔍 Building GLEIF lookup index...")
    gleif_by_country = {}
    for country in gleif_df['country'].unique():
        if pd.isna(country):
            continue
        country_df = gleif_df[gleif_df['country'] == country].copy()
        # Create lookup dict: canonical_name → row_index
        lookup = {}
        for idx, row in country_df.iterrows():
            if isinstance(row.get('name'), str):
                canon = canonicalize_company_name(row['name']).lower()
                lookup[canon] = idx
        gleif_by_country[country] = {
            'df': country_df,
            'lookup': lookup,
            'names': list(lookup.keys())
        }
    
    print(f"   Indexed {len(gleif_by_country)} countries")
    
    # Match each exchange company
    print(f"\n🔗 Matching companies...")
    matched_indices = set()
    match_details = []
    
    for idx, ex_row in exchange_df.iterrows():
        if (idx + 1) % 500 == 0:
            print(f"   Processed {idx + 1:,}/{len(exchange_df):,}...")
        
        ex_name = ex_row.get('name')
        ex_country = ex_row.get('country')
        
        if not isinstance(ex_name, str) or not isinstance(ex_country, str):
            continue
        
        # Get GLEIF data for this country
        country_data = gleif_by_country.get(ex_country)
        if not country_data:
            continue
        
        # Canonicalize exchange name
        ex_canon = canonicalize_company_name(ex_name).lower()
        
        # Try exact match first
        gleif_idx = country_data['lookup'].get(ex_canon)
        if gleif_idx is not None:
            matched_indices.add(gleif_idx)
            match_details.append({
                'exchange_name': ex_name,
                'gleif_name': gleif_df.loc[gleif_idx, 'name'],
                'country': ex_country,
                'score': 100,
                'match_type': 'exact'
            })
            continue
        
        # Fuzzy match
        if country_data['names']:
            result = process.extractOne(
                ex_canon,
                country_data['names'],
                scorer=fuzz.WRatio
            )
            if result:
                matched_name, score, _ = result
                if score >= threshold:
                    gleif_idx = country_data['lookup'][matched_name]
                    matched_indices.add(gleif_idx)
                    match_details.append({
                        'exchange_name': ex_name,
                        'gleif_name': gleif_df.loc[gleif_idx, 'name'],
                        'country': ex_country,
                        'score': score,
                        'match_type': 'fuzzy'
                    })
    
    # Extract matched GLEIF records
    matched_df = gleif_df.loc[list(matched_indices)].copy()
    
    print(f"\n✅ Results:")
    print(f"   Matches found: {len(matched_df):,}")
    print(f"   Match rate: {len(matched_df) / len(exchange_df) * 100:.1f}%")
    
    # Show sample matches
    print(f"\n📋 Sample matches:")
    match_details_df = pd.DataFrame(match_details)
    for i, row in match_details_df.head(10).iterrows():
        print(f"   {row['exchange_name']:40s} → {row['gleif_name']:40s} ({row['score']:.0f}%)")
    
    # Show match quality
    if len(match_details_df) > 0:
        print(f"\n📊 Match Quality:")
        print(f"   Exact matches: {len(match_details_df[match_details_df['match_type']=='exact']):,}")
        print(f"   Fuzzy matches: {len(match_details_df[match_details_df['match_type']=='fuzzy']):,}")
        print(f"   Avg score: {match_details_df['score'].mean():.1f}%")
        print(f"   Min score: {match_details_df['score'].min():.1f}%")
    
    return matched_df


def main():
    print("=" * 70)
    print("SMART FILTERING: Exchange → GLEIF Matching")
    print("=" * 70)
    
    # Check if GLEIF cache exists
    gleif_cache = Path(".cache/companies/gleif_full.parquet")
    if not gleif_cache.exists():
        print(f"\n❌ GLEIF cache not found: {gleif_cache}")
        print(f"\nPlease run first:")
        print(f"   python scripts/companies/download_gleif_full.py")
        return
    
    # Load GLEIF
    print(f"\n📂 Loading GLEIF cache: {gleif_cache}")
    gleif_df = pd.read_parquet(gleif_cache)
    print(f"   Records: {len(gleif_df):,}")
    
    # Load exchanges
    exchange_df = load_exchanges()
    if len(exchange_df) == 0:
        print("\n❌ No exchange data loaded!")
        return
    
    # Match
    matched_df = fuzzy_match_to_gleif(exchange_df, gleif_df, threshold=85)
    
    if len(matched_df) == 0:
        print("\n❌ No matches found!")
        return
    
    # Save
    output_file = Path(".cache/companies/gleif_exchange_matched.parquet")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    matched_df.to_parquet(output_file, index=False)
    
    print("\n" + "=" * 70)
    print("Matching Complete!")
    print("=" * 70)
    
    print(f"\n✅ Saved: {output_file}")
    print(f"   Records: {len(matched_df):,}")
    print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
    
    print(f"\n🌍 Geographic distribution:")
    for country, count in matched_df['country'].value_counts().head(10).items():
        print(f"   {country:3s}: {count:,}")
    
    print(f"\n📋 Next step:")
    print(f"   python -m entityidentity.companies.companyfilter \\")
    print(f"       --input {output_file} \\")
    print(f"       --output entityidentity/data/companies/companies.parquet \\")
    print(f"       --provider openai")
    
    print(f"\n💰 Estimated LLM cost: ${len(matched_df) * 0.002:.2f}")
    print(f"⏱️  Estimated time: ~{len(matched_df) * 2 / 3600:.1f} hours")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()


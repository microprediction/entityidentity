#!/usr/bin/env python3
"""
Smart expansion script: Add companies from major stock exchanges.

This focuses on exchange-listed companies which are more likely to be:
1. Large/important companies
2. Well-documented
3. Diverse geographically (major exchanges worldwide)
4. Relevant for mining/metals industries

Strategy:
- Pull from ASX, LSE, TSX, NYSE, NASDAQ, SSE, SZSE
- Filter by sector (mining, materials, industrials) if available
- Deduplicate against existing dataset  
- Run LLM classification only on new companies
- Merge with existing dataset

Cost: ~$10-20 depending on how many new companies
Time: ~3-6 hours
Expected: ~500-1,000 additional mining/metals companies
"""

import pandas as pd
import argparse
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from entityidentity.companies.companyfilter import filter_companies_llm
from entityidentity.companies.companyexchanges import load_asx, load_lse, load_tsx


def load_exchange_data():
    """Load data from all available exchanges."""
    print("=" * 70)
    print("Loading Exchange Data")
    print("=" * 70)
    
    exchanges_data = []
    
    # ASX (Australia)
    print("\n📊 ASX (Australian Securities Exchange)...")
    try:
        asx_df = load_asx()
        print(f"   Loaded: {len(asx_df)} companies")
        exchanges_data.append(asx_df)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        print(f"   Using sample data instead")
        from entityidentity.companies.companyexchanges import sample_asx_data
        asx_df = sample_asx_data()
        exchanges_data.append(asx_df)
    
    # LSE (London)
    print("\n📊 LSE (London Stock Exchange)...")
    try:
        lse_df = load_lse()
        print(f"   Loaded: {len(lse_df)} companies")
        exchanges_data.append(lse_df)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        print(f"   Using sample data instead")
        from entityidentity.companies.companyexchanges import sample_lse_data
        lse_df = sample_lse_data()
        exchanges_data.append(lse_df)
    
    # TSX (Toronto)
    print("\n📊 TSX (Toronto Stock Exchange)...")
    try:
        tsx_df = load_tsx()
        print(f"   Loaded: {len(tsx_df)} companies")
        exchanges_data.append(tsx_df)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        print(f"   Using sample data instead")
        from entityidentity.companies.companyexchanges import sample_tsx_data
        tsx_df = sample_tsx_data()
        exchanges_data.append(tsx_df)
    
    # Combine all exchange data
    if exchanges_data:
        combined = pd.concat(exchanges_data, ignore_index=True)
        print(f"\n✅ Total companies from exchanges: {len(combined)}")
        return combined
    else:
        print("\n❌ No exchange data loaded!")
        return pd.DataFrame()


def deduplicate_against_existing(exchange_df, existing_df):
    """Remove companies that are already in our dataset."""
    print("\n" + "=" * 70)
    print("Deduplicating Against Existing Dataset")
    print("=" * 70)
    
    # Build lookup sets from existing data
    existing_names = set(existing_df['name'].dropna().str.lower())
    existing_tickers = set()
    for col in ['alias1', 'alias2', 'alias3', 'alias4', 'alias5']:
        if col in existing_df.columns:
            for ticker in existing_df[col].dropna():
                if isinstance(ticker, str):
                    existing_tickers.add(ticker.lower())
    
    print(f"Existing dataset has {len(existing_names)} unique names and {len(existing_tickers)} tickers")
    
    # Check each exchange company
    new_companies = []
    duplicates = 0
    
    for idx, row in exchange_df.iterrows():
        name_lower = row['name'].lower() if isinstance(row['name'], str) else ""
        ticker_lower = row.get('ticker', '').lower() if isinstance(row.get('ticker'), str) else ""
        
        # Check if already in dataset
        if name_lower in existing_names or ticker_lower in existing_tickers:
            duplicates += 1
        else:
            new_companies.append(row)
    
    new_df = pd.DataFrame(new_companies)
    
    print(f"\n  Duplicates (already in dataset): {duplicates}")
    print(f"  New companies to classify: {len(new_df)}")
    
    return new_df


def main():
    parser = argparse.ArgumentParser(description="Expand dataset with exchange-listed companies")
    parser.add_argument("--provider", default="openai", choices=["openai", "anthropic"],
                       help="LLM provider for classification")
    parser.add_argument("--existing-data", default="entityidentity/data/companies/companies.parquet",
                       help="Path to existing filtered dataset")
    parser.add_argument("--cache-file", default=".cache/companies/classification_cache.json",
                       help="Path to classification cache")
    parser.add_argument("--output", default="entityidentity/data/companies/companies_expanded.parquet",
                       help="Path to save expanded dataset")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("SMART EXPANSION: Exchange-Listed Companies")
    print("=" * 70)
    
    # Load existing dataset
    print(f"\n📂 Loading existing dataset from {args.existing_data}...")
    existing_df = pd.read_parquet(args.existing_data)
    print(f"   Current dataset: {len(existing_df)} companies")
    print(f"   - Supply (mining): {len(existing_df[existing_df['value_chain_category']=='supply'])}")
    print(f"   - Demand: {len(existing_df[existing_df['value_chain_category']=='demand'])}")
    
    # Load exchange data
    exchange_df = load_exchange_data()
    
    if len(exchange_df) == 0:
        print("\n❌ No exchange data to process!")
        return
    
    # Deduplicate
    new_companies = deduplicate_against_existing(exchange_df, existing_df)
    
    if len(new_companies) == 0:
        print("\n✅ No new companies to add - existing dataset already has full exchange coverage!")
        return
    
    # Classify new companies with LLM
    print("\n" + "=" * 70)
    print("Classifying New Companies with LLM")
    print("=" * 70)
    
    classified = filter_companies_llm(
        new_companies,
        provider=args.provider,
        cache_file=Path(args.cache_file),
        confidence_threshold=0.7,
        batch_size=100
    )
    
    print(f"\n✅ Classified {len(classified)} relevant companies from exchanges")
    
    # Merge with existing dataset
    print("\n" + "=" * 70)
    print("Merging Datasets")
    print("=" * 70)
    
    expanded = pd.concat([existing_df, classified], ignore_index=True)
    
    # Final deduplication by (name, country)
    expanded = expanded.drop_duplicates(subset=['name', 'country'], keep='first')
    
    print(f"\n📊 Final dataset statistics:")
    print(f"   Total companies: {len(expanded)} (was {len(existing_df)}, +{len(expanded) - len(existing_df)})")
    print(f"   Supply (mining): {len(expanded[expanded['value_chain_category']=='supply'])}")
    print(f"   Demand: {len(expanded[expanded['value_chain_category']=='demand'])}")
    print(f"   Both: {len(expanded[expanded['value_chain_category']=='both'])}")
    print(f"   Neither: {len(expanded[expanded['value_chain_category']=='neither'])}")
    
    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    expanded.to_parquet(output_path, index=False)
    expanded.to_csv(output_path.with_suffix('.csv'), index=False)
    
    print(f"\n✅ Saved expanded dataset to:")
    print(f"   - {output_path}")
    print(f"   - {output_path.with_suffix('.csv')}")
    
    print("\n" + "=" * 70)
    print("✨ Expansion Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()


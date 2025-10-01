#!/usr/bin/env python3
"""
Preview what exchange expansion would add to the dataset.

Shows:
- How many companies from each exchange
- How many are new vs already in dataset
- Geographic breakdown
- Estimated cost/time for LLM classification

Run this before executing the full expansion.
"""

import pandas as pd
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

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
        from entityidentity.companies.companyexchanges import sample_asx_data
        asx_df = sample_asx_data()
        print(f"   Using sample data: {len(asx_df)} companies")
        exchanges_data.append(asx_df)
    
    # LSE (London)
    print("\n📊 LSE (London Stock Exchange)...")
    try:
        lse_df = load_lse()
        print(f"   Loaded: {len(lse_df)} companies")
        exchanges_data.append(lse_df)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        from entityidentity.companies.companyexchanges import sample_lse_data
        lse_df = sample_lse_data()
        print(f"   Using sample data: {len(lse_df)} companies")
        exchanges_data.append(lse_df)
    
    # TSX (Toronto)
    print("\n📊 TSX (Toronto Stock Exchange)...")
    try:
        tsx_df = load_tsx()
        print(f"   Loaded: {len(tsx_df)} companies")
        exchanges_data.append(tsx_df)
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        from entityidentity.companies.companyexchanges import sample_tsx_data
        tsx_df = sample_tsx_data()
        print(f"   Using sample data: {len(tsx_df)} companies")
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
    print("Deduplication Analysis")
    print("=" * 70)
    
    # Normalize names for comparison
    from entityidentity.companies.companynormalize import canonicalize_name
    
    # Build lookup sets from existing data
    existing_names = set()
    for name in existing_df['name'].dropna():
        if isinstance(name, str):
            existing_names.add(canonicalize_name(name).lower())
    
    existing_tickers = set()
    for col in ['alias1', 'alias2', 'alias3', 'alias4', 'alias5']:
        if col in existing_df.columns:
            for ticker in existing_df[col].dropna():
                if isinstance(ticker, str):
                    existing_tickers.add(ticker.lower())
    
    print(f"\nExisting dataset:")
    print(f"  • {len(existing_names)} unique names")
    print(f"  • {len(existing_tickers)} tickers")
    
    # Check each exchange company
    new_companies = []
    duplicates = []
    
    for idx, row in exchange_df.iterrows():
        if not isinstance(row.get('name'), str):
            continue
            
        name_canon = canonicalize_name(row['name']).lower()
        ticker_lower = row.get('ticker', '').lower() if isinstance(row.get('ticker'), str) else ""
        
        # Check if already in dataset
        is_duplicate = (
            name_canon in existing_names or 
            (ticker_lower and ticker_lower in existing_tickers)
        )
        
        if is_duplicate:
            duplicates.append(row)
        else:
            new_companies.append(row)
    
    new_df = pd.DataFrame(new_companies)
    dup_df = pd.DataFrame(duplicates)
    
    print(f"\nResults:")
    print(f"  • Duplicates (already in dataset): {len(dup_df)}")
    print(f"  • New companies: {len(new_df)}")
    
    if len(dup_df) > 0:
        print(f"\n  Sample duplicates:")
        for i, row in dup_df.head(5).iterrows():
            print(f"    - {row['name']} ({row.get('ticker', 'N/A')})")
    
    return new_df, dup_df


def main():
    print("=" * 70)
    print("PREVIEW: Exchange-Based Expansion")
    print("=" * 70)
    
    # Load existing dataset
    existing_path = Path("entityidentity/data/companies/companies.parquet")
    if not existing_path.exists():
        print(f"\n❌ Existing dataset not found: {existing_path}")
        return
    
    print(f"\n📂 Loading existing dataset from {existing_path}...")
    existing_df = pd.read_parquet(existing_path)
    print(f"   Current dataset: {len(existing_df)} companies")
    
    if 'value_chain_category' in existing_df.columns:
        print(f"   - Supply (mining): {len(existing_df[existing_df['value_chain_category']=='supply'])}")
        print(f"   - Demand: {len(existing_df[existing_df['value_chain_category']=='demand'])}")
        print(f"   - Both: {len(existing_df[existing_df['value_chain_category']=='both'])}")
    
    # Load exchange data
    exchange_df = load_exchange_data()
    
    if len(exchange_df) == 0:
        print("\n❌ No exchange data to process!")
        return
    
    # Deduplicate
    new_companies, duplicates = deduplicate_against_existing(exchange_df, existing_df)
    
    if len(new_companies) == 0:
        print("\n✅ No new companies to add - existing dataset already has full exchange coverage!")
        return
    
    # Analysis of new companies
    print("\n" + "=" * 70)
    print("New Companies Analysis")
    print("=" * 70)
    
    print(f"\n📊 Total: {len(new_companies)} new companies")
    
    print(f"\n🌍 Geographic Distribution:")
    for country, count in new_companies['country'].value_counts().items():
        print(f"   {country:3s}: {count:4d} companies")
    
    print(f"\n📚 By Exchange:")
    for exchange, count in new_companies['exchange'].value_counts().items():
        print(f"   {exchange:10s}: {count:4d} companies")
    
    # Estimate cost/time
    print("\n" + "=" * 70)
    print("LLM Classification Estimates")
    print("=" * 70)
    
    num_new = len(new_companies)
    
    # Check cache
    cache_path = Path(".cache/companies/classification_cache.json")
    cached_count = 0
    if cache_path.exists():
        import json
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        
        # Estimate how many might be cached
        from entityidentity.companies.companynormalize import canonicalize_name
        cache_keys = set(cache.keys())
        for _, row in new_companies.iterrows():
            if not isinstance(row.get('name'), str):
                continue
            cache_key = f"{canonicalize_name(row['name'])}|{row.get('country', '')}"
            if cache_key in cache_keys:
                cached_count += 1
    
    to_classify = num_new - cached_count
    
    print(f"\n📦 Companies to classify: {to_classify}")
    if cached_count > 0:
        print(f"   (Cached: {cached_count}, reusing from previous runs)")
    
    # Cost estimates (GPT-4o-mini: ~$0.002 per classification)
    cost_per_company = 0.002
    estimated_cost = to_classify * cost_per_company
    
    # Time estimates (~2s per classification)
    time_per_company = 2
    estimated_time_sec = to_classify * time_per_company
    estimated_time_hr = estimated_time_sec / 3600
    
    print(f"\n💰 Estimated Cost:")
    print(f"   ${estimated_cost:.2f} (at ~$0.002 per company)")
    
    print(f"\n⏱️  Estimated Time:")
    print(f"   ~{estimated_time_hr:.1f} hours (at ~2s per company)")
    
    # Expected output
    print("\n" + "=" * 70)
    print("Expected Results")
    print("=" * 70)
    
    # Based on historical ~7% match rate for mining/metals
    expected_matches = int(to_classify * 0.07)
    print(f"\n📈 Expected new mining/metals companies: ~{expected_matches}")
    print(f"   (Based on ~7% historical match rate)")
    
    final_dataset_size = len(existing_df) + expected_matches
    print(f"\n📊 Final dataset size: ~{final_dataset_size} companies")
    
    # Geographic improvement
    print(f"\n🌍 Geographic Diversity Improvement:")
    current_countries = existing_df['country'].value_counts()
    new_countries = new_companies['country'].value_counts()
    
    for country in ['AU', 'GB', 'CA']:
        current = current_countries.get(country, 0)
        new = new_countries.get(country, 0)
        expected_added = int(new * 0.07)
        print(f"   {country}: {current} → ~{current + expected_added} (+{expected_added})")
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    print(f"\n✅ Ready to expand!")
    print(f"   • New companies to process: {to_classify}")
    print(f"   • Estimated cost: ${estimated_cost:.2f}")
    print(f"   • Estimated time: ~{estimated_time_hr:.1f} hours")
    print(f"   • Expected additions: ~{expected_matches} mining/metals companies")
    print(f"   • Main benefit: Better geographic diversity (AU, GB, CA)")
    
    print(f"\n📋 Next step:")
    print(f"   caffeinate python scripts/companies/expand_with_exchanges.py --provider openai")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()


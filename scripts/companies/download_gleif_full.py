#!/usr/bin/env python3
"""
Download the complete GLEIF LEI database (~2.5M records).

This downloads ALL GLEIF data once and caches it locally.
Future operations can then filter/match against this cache.

Output: .cache/companies/gleif_full.parquet (~1 GB)
Time: ~30-45 minutes
Cost: FREE (GLEIF API is free)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from entityidentity.companies.companygleif import load_gleif_lei


def main():
    print("=" * 70)
    print("Download Complete GLEIF Database")
    print("=" * 70)
    
    cache_dir = Path(".cache/companies")
    cache_file = cache_dir / "gleif_full.parquet"
    
    print(f"\n📂 Cache directory: {cache_dir}")
    print(f"📄 Output file: {cache_file}")
    
    if cache_file.exists():
        print(f"\n✅ GLEIF cache already exists!")
        print(f"   File size: {cache_file.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"\n   To re-download, delete: {cache_file}")
        
        import pandas as pd
        df = pd.read_parquet(cache_file)
        print(f"   Records: {len(df):,}")
        print(f"   Countries: {df['country'].nunique()}")
        
        return
    
    print("\n⚠️  This will download ~2.5 million LEI records (~2-3 GB)")
    print("    Estimated time: 30-45 minutes")
    print("    GLEIF API is free - no cost")
    print()
    
    response = input("Continue? [y/N] ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    print("\n" + "=" * 70)
    print("Downloading GLEIF Data")
    print("=" * 70)
    print("\nThis may take 30-45 minutes...")
    print("The download will be cached for future use.")
    print()
    
    # Download all GLEIF data
    df = load_gleif_lei(
        cache_dir=str(cache_dir),
        max_records=None  # No limit - download all
    )
    
    print("\n" + "=" * 70)
    print("Download Complete!")
    print("=" * 70)
    
    print(f"\n📊 Statistics:")
    print(f"   Total records: {len(df):,}")
    print(f"   Countries: {df['country'].nunique()}")
    print(f"   File size: {cache_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    print(f"\n🌍 Top 10 Countries:")
    for country, count in df['country'].value_counts().head(10).items():
        print(f"   {country:3s}: {count:,}")
    
    print(f"\n✅ Cached: {cache_file}")
    print(f"\n📋 Next step:")
    print(f"   python scripts/companies/match_exchanges_to_gleif.py")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()


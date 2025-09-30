#!/usr/bin/env python3
"""Update or create the companies.parquet lookup database.

This script fetches fresh company data from all configured sources
(GLEIF, Wikidata, stock exchanges) and builds a consolidated
companies.parquet file for use with company identity resolution.

Usage:
    # Basic usage (download all sources)
    python scripts/companies/update_companies_db.py
    
    # Quick test with sample data
    python scripts/companies/update_companies_db.py --use-samples
    
    # Specify output location
    python scripts/companies/update_companies_db.py --output data/companies.parquet
    
    # Use cache directory to avoid re-downloading
    python scripts/companies/update_companies_db.py --cache-dir .cache
    
    # Incremental update (if exists, only fetch new data)
    python scripts/companies/update_companies_db.py --incremental

Environment Variables:
    COMPANIES_DB_PATH: Default output path (default: tables/companies/companies.parquet)
    COMPANIES_CACHE_DIR: Cache directory for downloads (default: .cache/companies)
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from entityidentity.build_companies_db import consolidate_companies


def _write_info_file(info_path: Path, data: pd.DataFrame, args):
    """Write database statistics to info file."""
    with open(info_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Company Database Information\n")
        f.write("=" * 70 + "\n")
        f.write(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Mode: {'Sample Data (Testing)' if args.use_samples else 'Live Sources'}\n")
        f.write(f"\n")
        
        f.write(f"Total Companies: {len(data):,}\n")
        f.write(f"\n")
        
        f.write("Breakdown by Source:\n")
        source_counts = data['source'].value_counts()
        for source, count in source_counts.items():
            pct = count / len(data) * 100
            f.write(f"  - {source:15s}: {count:6,} companies ({pct:5.1f}%)\n")
        f.write(f"\n")
        
        f.write("Data Coverage:\n")
        lei_count = data['lei'].notna().sum()
        lei_pct = lei_count / len(data) * 100
        f.write(f"  - With LEI:         {lei_count:6,} ({lei_pct:5.1f}%)\n")
        
        qid_count = data['wikidata_qid'].notna().sum()
        qid_pct = qid_count / len(data) * 100
        f.write(f"  - With Wikidata QID: {qid_count:6,} ({qid_pct:5.1f}%)\n")
        
        alias_count = data['aliases'].apply(lambda x: len(x) > 0).sum()
        alias_pct = alias_count / len(data) * 100
        f.write(f"  - With Aliases:      {alias_count:6,} ({alias_pct:5.1f}%)\n")
        
        address_count = data['address'].notna().sum()
        address_pct = address_count / len(data) * 100
        f.write(f"  - With Address:      {address_count:6,} ({address_pct:5.1f}%)\n")
        f.write(f"\n")
        
        f.write("Top 10 Countries:\n")
        top_countries = data['country'].value_counts().head(10)
        for country, count in top_countries.items():
            pct = count / len(data) * 100
            f.write(f"  - {country}: {count:6,} ({pct:5.1f}%)\n")
        f.write(f"\n")
        
        f.write("Database Files:\n")
        parquet_path = args.output
        if parquet_path.exists():
            size_mb = parquet_path.stat().st_size / 1024 / 1024
            f.write(f"  - Parquet: {parquet_path.name} ({size_mb:.2f} MB)\n")
        
        csv_path = args.output.with_suffix('.csv')
        if csv_path.exists():
            size_kb = csv_path.stat().st_size / 1024
            csv_rows = min(500, len(data))
            f.write(f"  - CSV Preview: {csv_path.name} ({size_kb:.1f} KB, {csv_rows} rows)\n")
        
        f.write(f"\n")
        f.write("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Update companies lookup database from live sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('tables/companies/companies.parquet'),
        help='Output parquet file path (default: tables/companies/companies.parquet)'
    )
    
    parser.add_argument(
        '--cache-dir', '-c',
        type=Path,
        default=Path('.cache/companies'),
        help='Cache directory for downloads (default: .cache/companies)'
    )
    
    parser.add_argument(
        '--use-samples', '-s',
        action='store_true',
        help='Use sample data instead of live sources (fast, for testing)'
    )
    
    parser.add_argument(
        '--incremental', '-i',
        action='store_true',
        help='Incremental update: preserve existing data and add new records'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['parquet', 'csv'],
        default='parquet',
        help='Output format (default: parquet, recommended for performance)'
    )
    
    parser.add_argument(
        '--backup', '-b',
        action='store_true',
        help='Create timestamped backup before updating'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("=" * 70)
    print("  Company Database Updater")
    print("=" * 70)
    print(f"Mode: {'Sample Data (Testing)' if args.use_samples else 'Live Sources'}")
    print(f"Output: {args.output}")
    print(f"Format: {args.format}")
    print(f"Cache: {args.cache_dir}")
    print("=" * 70)
    print()
    
    # Create cache directory
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup existing database if requested
    existing_data = None
    if args.output.exists():
        print(f"📁 Found existing database: {args.output}")
        print(f"   Size: {args.output.stat().st_size / 1024 / 1024:.2f} MB")
        
        if args.backup:
            backup_path = args.output.with_suffix(
                f'.{datetime.now().strftime("%Y%m%d_%H%M%S")}.parquet.bak'
            )
            print(f"💾 Creating backup: {backup_path}")
            import shutil
            shutil.copy2(args.output, backup_path)
        
        if args.incremental:
            print("📥 Loading existing data for incremental update...")
            if args.format == 'parquet':
                existing_data = pd.read_parquet(args.output)
            else:
                existing_data = pd.read_csv(args.output)
            print(f"   Existing records: {len(existing_data):,}")
    
    # Build/update database
    print()
    print("🔄 Fetching data from sources...")
    print()
    
    try:
        new_data = consolidate_companies(
            use_samples=args.use_samples,
            cache_dir=str(args.cache_dir) if not args.use_samples else None,
        )
        
        # Merge with existing data if incremental
        if args.incremental and existing_data is not None:
            print()
            print("🔗 Merging with existing data...")
            
            # Combine old and new
            combined = pd.concat([existing_data, new_data], ignore_index=True)
            
            # Deduplicate (prioritize newer data)
            print("   Deduplicating...")
            
            # First by LEI
            lei_records = combined[combined['lei'].notna() & (combined['lei'] != '')]
            no_lei_records = combined[~combined.index.isin(lei_records.index)]
            
            lei_deduped = lei_records.drop_duplicates(subset=['lei'], keep='last')
            print(f"   - LEI dedupe: {len(lei_records)} → {len(lei_deduped)}")
            
            # Then by name_norm + country
            no_lei_deduped = no_lei_records.drop_duplicates(
                subset=['name_norm', 'country'],
                keep='last'
            )
            print(f"   - Name+country dedupe: {len(no_lei_records)} → {len(no_lei_deduped)}")
            
            final_data = pd.concat([lei_deduped, no_lei_deduped], ignore_index=True)
            
            print(f"   Total: {len(existing_data):,} + {len(new_data):,} → {len(final_data):,}")
        else:
            final_data = new_data
        
        # Save output
        print()
        print(f"💾 Saving to {args.output}...")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        
        if args.format == 'parquet':
            final_data.to_parquet(args.output, index=False, compression='snappy')
            
            # Also create a CSV preview with first 500 rows
            csv_preview_path = args.output.with_suffix('.csv')
            preview_rows = min(500, len(final_data))
            print(f"📄 Creating CSV preview: {csv_preview_path} ({preview_rows} rows)")
            final_data.head(preview_rows).to_csv(csv_preview_path, index=False)
            
            # Create info file with database statistics
            info_path = args.output.parent / 'companies_info.txt'
            print(f"📊 Creating info file: {info_path}")
            _write_info_file(info_path, final_data, args)
        else:
            final_data.to_csv(args.output, index=False)
        
        file_size = args.output.stat().st_size / 1024 / 1024
        
        # Print summary
        print()
        print("=" * 70)
        print("✅ Database updated successfully!")
        print("=" * 70)
        print(f"Output file: {args.output}")
        print(f"File size: {file_size:.2f} MB")
        if args.format == 'parquet':
            csv_size = args.output.with_suffix('.csv').stat().st_size / 1024
            print(f"CSV preview: {args.output.with_suffix('.csv')} ({csv_size:.1f} KB)")
            print(f"Info file: {args.output.parent / 'companies_info.txt'}")
        print(f"Total companies: {len(final_data):,}")
        print()
        print("Breakdown by source:")
        source_counts = final_data['source'].value_counts()
        for source, count in source_counts.items():
            print(f"  - {source:12s}: {count:6,} companies")
        print()
        print("Data coverage:")
        print(f"  - With LEI: {final_data['lei'].notna().sum():,} ({final_data['lei'].notna().sum()/len(final_data)*100:.1f}%)")
        print(f"  - With Wikidata QID: {final_data['wikidata_qid'].notna().sum():,} ({final_data['wikidata_qid'].notna().sum()/len(final_data)*100:.1f}%)")
        print()
        print("Top countries:")
        top_countries = final_data['country'].value_counts().head(5)
        for country, count in top_countries.items():
            print(f"  - {country}: {count:,}")
        print("=" * 70)
        
        if args.verbose:
            print()
            print("Sample records:")
            print(final_data.head(10).to_string())
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Error: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


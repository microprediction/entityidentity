#!/usr/bin/env python3
"""Production CLI for updating/creating the companies.parquet lookup database.

This script provides a feature-rich CLI wrapper around the consolidate_companies()
function with additional production features:
- Automatic backups with timestamps
- Incremental updates (merge with existing data)
- CSV preview generation for inspection
- Detailed info file with database statistics
- Progress reporting and error handling

Usage:
    # Basic usage (download all sources)
    python scripts/companies/build_database_cli.py

    # Quick test with sample data
    python scripts/companies/build_database_cli.py --use-samples

    # Specify output location
    python scripts/companies/build_database_cli.py --output data/companies.parquet

    # Use cache directory to avoid re-downloading
    python scripts/companies/build_database_cli.py --cache-dir .cache

    # Incremental update (merge with existing data)
    python scripts/companies/build_database_cli.py --incremental

    # Create backup before updating
    python scripts/companies/build_database_cli.py --backup

Environment Variables:
    COMPANIES_DB_PATH: Default output path (default: tables/companies/companies.parquet)
    COMPANIES_CACHE_DIR: Cache directory for downloads (default: .cache/companies)
"""

import argparse
import shutil
import sys
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from entityidentity.companies.data.build_companies import consolidate_companies


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
        
        # Count companies with at least one alias (alias1-alias5)
        alias_count = data['alias1'].notna().sum()
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
            csv_rows = min(5000, len(data))
            f.write(f"  - CSV Preview: {csv_path.name} ({size_kb:.1f} KB, up to {csv_rows} rows sampled)\n")
        
        f.write(f"\n")
        f.write("=" * 70 + "\n")


def _create_backup(output_path: Path) -> Path:
    """Create timestamped backup of existing database.

    Args:
        output_path: Path to the existing database

    Returns:
        Path to the backup file
    """
    backup_path = output_path.with_suffix(
        f'.{datetime.now().strftime("%Y%m%d_%H%M%S")}.parquet.bak'
    )
    print(f"💾 Creating backup: {backup_path}")
    shutil.copy2(output_path, backup_path)
    return backup_path


def _merge_incremental(existing_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
    """Merge new data with existing data, deduplicating intelligently.

    Args:
        existing_data: Current database
        new_data: Newly fetched data

    Returns:
        Merged and deduplicated DataFrame
    """
    print()
    print("🔗 Merging with existing data...")

    # Combine old and new
    combined = pd.concat([existing_data, new_data], ignore_index=True)

    # Deduplicate (prioritize newer data by using keep='last')
    print("   Deduplicating...")

    # First dedupe by LEI
    lei_records = combined[combined['lei'].notna() & (combined['lei'] != '')]
    no_lei_records = combined[~combined.index.isin(lei_records.index)]

    lei_deduped = lei_records.drop_duplicates(subset=['lei'], keep='last')
    print(f"   - LEI dedupe: {len(lei_records)} → {len(lei_deduped)}")

    # Then dedupe by name_norm + country
    no_lei_deduped = no_lei_records.drop_duplicates(
        subset=['name_norm', 'country'],
        keep='last'
    )
    print(f"   - Name+country dedupe: {len(no_lei_records)} → {len(no_lei_deduped)}")

    final_data = pd.concat([lei_deduped, no_lei_deduped], ignore_index=True)

    print(f"   Total: {len(existing_data):,} + {len(new_data):,} → {len(final_data):,}")
    return final_data


def _create_csv_preview(parquet_path: Path, data: pd.DataFrame, max_rows: int = 5000) -> Path:
    """Create a CSV preview file with a sample of the data.

    Args:
        parquet_path: Path to the parquet file
        data: Full DataFrame
        max_rows: Maximum rows for preview

    Returns:
        Path to the CSV preview file
    """
    csv_preview_path = parquet_path.with_suffix('.csv')
    preview_rows = min(max_rows, len(data))
    print(f"📄 Creating CSV preview: {csv_preview_path} ({preview_rows} rows, randomly sampled)")

    if len(data) > max_rows:
        preview_df = data.sample(n=max_rows, random_state=42)
    else:
        preview_df = data

    preview_df.to_csv(csv_preview_path, index=False)
    return csv_preview_path


def main():
    """Main entry point for production CLI."""
    parser = argparse.ArgumentParser(
        description="Production company database updater with full features",
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
    
    # Handle existing database
    existing_data = None
    if args.output.exists():
        print(f"📁 Found existing database: {args.output}")
        print(f"   Size: {args.output.stat().st_size / 1024 / 1024:.2f} MB")

        if args.backup:
            _create_backup(args.output)

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
            final_data = _merge_incremental(existing_data, new_data)
        else:
            final_data = new_data
        
        # Save output
        print()
        print(f"💾 Saving to {args.output}...")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        
        if args.format == 'parquet':
            final_data.to_parquet(args.output, index=False, compression='snappy')

            # Create CSV preview
            _create_csv_preview(args.output, final_data)

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
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


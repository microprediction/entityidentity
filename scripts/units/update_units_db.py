#!/usr/bin/env python3
"""Production CLI for updating/creating the units.parquet lookup database.

This script provides a feature-rich CLI wrapper around the unit database builder
with additional production features:
- Automatic backups with timestamps
- CSV preview generation for inspection
- Detailed info file with database statistics
- Progress reporting and error handling

Usage:
    # Basic usage (build from configuration)
    python scripts/units/update_units_db.py

    # Specify output location
    python scripts/units/update_units_db.py --output data/units.parquet

    # Create backup before updating
    python scripts/units/update_units_db.py --backup

    # Generate CSV preview
    python scripts/units/update_units_db.py --csv-preview

Environment Variables:
    UNITS_DB_PATH: Default output path (default: tables/units/units.parquet)
"""

import argparse
import os
import shutil
import sys
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from entityidentity.units.data.build_units import (
    load_unit_data,
    process_unit,
    validate_units,
    generate_unit_summary,
)
from entityidentity.utils.build_framework import BuildConfig, build_entity_database


def _write_info_file(info_path: Path, data: pd.DataFrame):
    """Write database statistics to info file."""
    with open(info_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Unit Database Information\n")
        f.write("=" * 70 + "\n")
        f.write(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n")

        f.write(f"Total Units: {len(data):,}\n")
        f.write(f"\n")

        f.write("Breakdown by Category:\n")
        category_counts = data['category'].value_counts()
        for category, count in category_counts.items():
            if category:  # Skip empty strings
                pct = count / len(data) * 100
                f.write(f"  - {category:20s}: {count:3,} units ({pct:5.1f}%)\n")
        f.write(f"\n")

        f.write("Data Coverage:\n")
        si_count = ((data['si_factor'].notna()) & (data['si_factor'] != '')).sum()
        si_pct = si_count / len(data) * 100
        f.write(f"  - With SI Factor:     {si_count:3,} ({si_pct:5.1f}%)\n")

        material_count = (data['material'] != '').sum()
        material_pct = material_count / len(data) * 100
        f.write(f"  - Material-specific:  {material_count:3,} ({material_pct:5.1f}%)\n")

        composite_count = (data['numerator'] != '').sum()
        composite_pct = composite_count / len(data) * 100
        f.write(f"  - Composite units:    {composite_count:3,} ({composite_pct:5.1f}%)\n")

        alias_count = (data['alias1'] != '').sum()
        alias_pct = alias_count / len(data) * 100
        f.write(f"  - With Aliases:       {alias_count:3,} ({alias_pct:5.1f}%)\n")
        f.write(f"\n")

        f.write("Database Files:\n")
        parquet_path = info_path.parent / "units.parquet"
        if parquet_path.exists():
            size_kb = parquet_path.stat().st_size / 1024
            f.write(f"  - Parquet: {parquet_path.name} ({size_kb:.2f} KB)\n")

        csv_path = info_path.parent / "units.csv"
        if csv_path.exists():
            size_kb = csv_path.stat().st_size / 1024
            f.write(f"  - CSV preview: {csv_path.name} ({size_kb:.2f} KB)\n")
        f.write(f"\n")

        f.write("Top Unit Symbols:\n")
        top_symbols = data[data['symbol'] != '']['symbol'].value_counts().head(10)
        for symbol, count in top_symbols.items():
            f.write(f"  - {symbol}: {count} units\n")


def main():
    parser = argparse.ArgumentParser(
        description='Build/update the units.parquet lookup database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Output options
    default_output = Path(os.environ.get('UNITS_DB_PATH', 'tables/units/units.parquet'))
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=default_output,
        help=f'Output path for units.parquet (default: {default_output})'
    )

    # Feature options
    parser.add_argument(
        '--backup', '-b',
        action='store_true',
        help='Create timestamped backup of existing database before updating'
    )
    parser.add_argument(
        '--csv-preview',
        action='store_true',
        help='Generate units.csv preview file alongside parquet'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        default=True,
        help='Generate units.info text file with statistics (default: True)'
    )

    # Development options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving output files (validation only)'
    )

    args = parser.parse_args()

    try:
        # Ensure output directory exists
        args.output.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing database if requested
        if args.backup and args.output.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = args.output.parent / f"{args.output.stem}_{timestamp}.parquet"
            print(f"Creating backup: {backup_path}")
            shutil.copy2(args.output, backup_path)

        print("Building units database...")
        print("=" * 70)

        # Load unit data
        print("Loading unit definitions...")
        unit_data = load_unit_data()
        print(f"  Found {len(unit_data['units'])} units")

        # Create build config
        config = BuildConfig(
            input_yaml=None,  # We're loading programmatically
            output_parquet=args.output if not args.dry_run else None,
            aux_yaml=None,
            process_entity=process_unit,
            validate_data=validate_units,
            generate_summary=generate_unit_summary,
            entity_name="unit",
            entity_plural="units",
            yaml_key="units",
            aux_yaml_key=None,
            input_data=unit_data,  # Pass data directly
        )

        # Build database
        result = build_entity_database(config)

        if result != 0:
            print(f"Build failed with return code: {result}")
            return result

        # If dry run, stop here
        if args.dry_run:
            print("\nDry run complete - no files written")
            return 0

        # Read the generated parquet file
        data = pd.read_parquet(args.output)
        print(f"\nGenerated {args.output} with {len(data):,} units")

        # Generate CSV preview if requested
        if args.csv_preview:
            csv_path = args.output.parent / f"{args.output.stem}.csv"
            data.head(1000).to_csv(csv_path, index=False)
            print(f"Generated CSV preview: {csv_path}")

        # Generate info file
        if args.info:
            info_path = args.output.parent / f"{args.output.stem}.info"
            _write_info_file(info_path, data)
            print(f"Generated info file: {info_path}")

        print("\n" + "=" * 70)
        print("Unit database build complete!")
        print(f"Output: {args.output}")
        print(f"Units: {len(data):,}")

        # Summary by category
        print("\nCategories:")
        for category, count in data['category'].value_counts().items():
            if category:
                print(f"  - {category}: {count}")

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
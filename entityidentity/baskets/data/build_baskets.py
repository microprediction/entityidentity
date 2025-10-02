#!/usr/bin/env python3
"""
Build baskets.parquet from baskets.yaml.

This script:
1. Loads baskets.yaml
2. Generates basket_id using sha1(normalize(name) + '|basket')[:16]
3. Expands aliases into alias1...alias10 columns
4. Expands components into component1...component10 columns
5. Writes baskets.parquet with all columns as strings
6. Generates validation report for duplicates and consistency
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

# Import basket normalization functions from the shared module
from entityidentity.baskets.basketnormalize import (
    normalize_basket_name,
    canonicalize_basket_name,
    slugify_basket_name,
    generate_basket_id,
)
from entityidentity.utils.build_utils import expand_aliases, expand_components, load_yaml_file


def validate_data(df: pd.DataFrame) -> List[str]:
    """
    Validate the data and return list of issues found.
    """
    issues = []

    # Check for duplicate basket_ids
    duplicates = df[df.duplicated(subset=['basket_id'], keep=False)]
    if not duplicates.empty:
        dup_names = duplicates[['name', 'basket_id']].to_dict('records')
        issues.append(f"Duplicate basket_ids found: {dup_names}")

    # Check for duplicate basket_keys
    dup_keys = df[df.duplicated(subset=['basket_key'], keep=False)]
    if not dup_keys.empty:
        dup_key_names = dup_keys[['name', 'basket_key']].to_dict('records')
        issues.append(f"Duplicate basket_keys found: {dup_key_names}")

    # Check for missing required fields
    required_fields = ['name', 'basket_id', 'basket_key']
    for field in required_fields:
        missing = df[df[field].isna() | (df[field] == "")]
        if not missing.empty:
            missing_names = missing['name'].tolist()
            issues.append(f"Missing {field} for baskets: {missing_names}")

    # Check that each basket has at least one component
    no_components = df[df['component1'] == '']
    if not no_components.empty:
        no_comp_names = no_components['name'].tolist()
        issues.append(f"Baskets with no components: {no_comp_names}")

    return issues


def main():
    """Main build process."""
    # Setup paths
    data_dir = Path(__file__).parent
    baskets_yaml = data_dir / "baskets.yaml"
    output_parquet = data_dir / "baskets.parquet"

    print(f"Building baskets database from {baskets_yaml}")

    # Load source data
    print("Loading YAML file...")
    baskets_data = load_yaml_file(baskets_yaml)

    # Process baskets
    print(f"Processing {len(baskets_data.get('baskets', []))} baskets...")
    rows = []

    for basket in baskets_data.get('baskets', []):
        # Core fields
        name = basket.get('name', '')

        # Generate IDs
        # Use explicit basket_id from YAML if provided, otherwise generate from name
        basket_id = basket.get('basket_id', generate_basket_id(name))
        basket_key = basket.get('basket_key') or slugify_basket_name(name)

        # Create row with all fields as strings
        row = {
            'basket_id': basket_id,
            'basket_key': basket_key,
            'name': canonicalize_basket_name(name),
            'name_norm': normalize_basket_name(name),
            'description': str(basket.get('description') or ''),
        }

        # Expand aliases
        alias_cols = expand_aliases(basket.get('aliases', []))
        row.update(alias_cols)

        # Expand components
        component_cols = expand_components(basket.get('components', []))
        row.update(component_cols)

        rows.append(row)

    # Create DataFrame with all string dtypes
    df = pd.DataFrame(rows)

    # Ensure all columns are strings
    for col in df.columns:
        df[col] = df[col].astype(str)
        # Replace 'None' strings with empty strings
        df[col] = df[col].replace('None', '')

    # Validate data
    print("\nValidating data...")
    issues = validate_data(df)

    if issues:
        print("\n⚠️  Validation issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print()
    else:
        print("✅ All validations passed")

    # Sort by name for consistent output
    df = df.sort_values('name').reset_index(drop=True)

    # Write to Parquet
    print(f"\nWriting {len(df)} baskets to {output_parquet}")
    df.to_parquet(output_parquet, index=False, engine='pyarrow')

    # Generate summary report
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"Total baskets: {len(df)}")
    print(f"Output file: {output_parquet}")
    print(f"File size: {output_parquet.stat().st_size / 1024:.1f} KB")

    # Component statistics
    print("\nBasket details:")
    for idx, row in df.iterrows():
        components = [c for c in [row.get(f'component{i}', '') for i in range(1, 11)] if c]
        print(f"  {row['name']}: {len(components)} components")

    # Baskets with aliases
    with_aliases = df[df['alias1'] != '']
    print(f"\nBaskets with aliases: {len(with_aliases)}")

    if issues:
        print(f"\n⚠️  Build completed with {len(issues)} validation issues")
        return 1
    else:
        print("\n✅ Build completed successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Build metals.parquet from metals.yaml following METALS_ONTOLOGY_PLAN.md specifications.

This script:
1. Loads metals.yaml and supply_chain_clusters.yaml
2. Generates metal_id using sha1(normalize(name) + '|metal')[:16]
3. Expands aliases into alias1...alias10 columns
4. Implements validate_basis() with APT/FeCr/precious examples
5. Writes metals.parquet with all columns as strings
6. Generates validation report for duplicates, missing clusters, unit/basis mismatches
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

# Import metal normalization functions from the shared module
from entityidentity.metals.metalnormalize import (
    normalize_metal_name,
    canonicalize_metal_name,
    slugify_metal_name,
    generate_metal_id,
)


def validate_basis(unit: Optional[str], basis: Optional[str]) -> bool:
    """
    Validate unit/basis consistency per section 9 of METALS_ONTOLOGY_PLAN.md.

    Examples from the plan:
    - APT: unit="mtu", basis="$/mtu WO3" (OK)
    - FeCr: unit="lb", basis="$/lb Cr contained" (OK)
    - Precious: unit="toz", basis="$/toz" (OK)
    """
    if not unit or not basis:
        # Both None is OK, one None is questionable
        return unit is None and basis is None

    # Normalize for comparison
    unit_lower = unit.lower()
    basis_lower = basis.lower()

    # Check if unit appears in basis
    if unit_lower not in basis_lower:
        return False

    # Specific validations
    validations = [
        # APT case
        (unit_lower == "mtu", "mtu" in basis_lower and ("wo3" in basis_lower or "tungsten" in basis_lower)),
        # Ferroalloy cases
        (unit_lower == "lb", "lb" in basis_lower and any(x in basis_lower for x in ["cr", "mo", "v", "w", "mn", "contained"])),
        # Precious metals
        (unit_lower in ["oz", "toz", "troy oz"], any(x in basis_lower for x in ["oz", "toz", "troy"])),
        # Standard metric
        (unit_lower in ["mt", "t", "tonne"], any(x in basis_lower for x in ["mt", "tonne", "t/", "per t"])),
        (unit_lower == "kg", "kg" in basis_lower),
        # Currency per unit pattern
        ("$/" in basis or "usd/" in basis_lower or "eur/" in basis_lower, True),
    ]

    # If any specific validation matches, return True
    for condition, check in validations:
        if condition and check:
            return True

    # Default: if unit appears in basis, consider it valid
    return True


def expand_aliases(aliases: Optional[List[str]], max_columns: int = 10) -> Dict[str, str]:
    """
    Expand aliases list into alias1...alias10 columns.
    """
    result = {}
    if not aliases:
        aliases = []

    for i in range(1, max_columns + 1):
        col_name = f"alias{i}"
        if i <= len(aliases):
            result[col_name] = str(aliases[i - 1])
        else:
            result[col_name] = ""

    return result


def load_yaml_file(path: Path) -> dict:
    """Load and parse YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, 'r') as f:
        return yaml.safe_load(f)


def validate_data(df: pd.DataFrame, clusters: dict) -> List[str]:
    """
    Validate the data and return list of issues found.
    """
    issues = []

    # Check for duplicate metal_ids
    duplicates = df[df.duplicated(subset=['metal_id'], keep=False)]
    if not duplicates.empty:
        dup_names = duplicates[['name', 'metal_id']].to_dict('records')
        issues.append(f"Duplicate metal_ids found: {dup_names}")

    # Check for duplicate metal_keys
    dup_keys = df[df.duplicated(subset=['metal_key'], keep=False)]
    if not dup_keys.empty:
        dup_key_names = dup_keys[['name', 'metal_key']].to_dict('records')
        issues.append(f"Duplicate metal_keys found: {dup_key_names}")

    # Check for missing clusters
    if clusters:
        invalid_clusters = df[
            df['cluster_id'].notna() &
            ~df['cluster_id'].isin(clusters.keys())
        ]
        if not invalid_clusters.empty:
            invalid_names = invalid_clusters[['name', 'cluster_id']].to_dict('records')
            issues.append(f"Invalid cluster_ids found: {invalid_names}")

    # Check unit/basis consistency
    for idx, row in df.iterrows():
        if pd.notna(row.get('default_unit')) or pd.notna(row.get('default_basis')):
            if not validate_basis(row.get('default_unit'), row.get('default_basis')):
                issues.append(
                    f"Unit/basis mismatch for {row['name']}: "
                    f"unit='{row.get('default_unit')}', basis='{row.get('default_basis')}'"
                )

    # Check for missing required fields
    required_fields = ['name', 'metal_id', 'metal_key', 'category_bucket']
    for field in required_fields:
        missing = df[df[field].isna() | (df[field] == "")]
        if not missing.empty:
            missing_names = missing['name'].tolist()
            issues.append(f"Missing {field} for metals: {missing_names}")

    return issues


def main():
    """Main build process."""
    # Setup paths
    data_dir = Path(__file__).parent
    metals_yaml = data_dir / "metals.yaml"
    clusters_yaml = data_dir / "supply_chain_clusters.yaml"
    output_parquet = data_dir / "metals.parquet"

    print(f"Building metals database from {metals_yaml}")

    # Load source data
    print("Loading YAML files...")
    metals_data = load_yaml_file(metals_yaml)

    # Load clusters if available
    clusters = {}
    if clusters_yaml.exists():
        clusters_data = load_yaml_file(clusters_yaml)
        clusters = clusters_data.get('clusters', {})
        print(f"Loaded {len(clusters)} supply chain clusters")

    # Process metals
    print(f"Processing {len(metals_data.get('metals', []))} metals...")
    rows = []

    for metal in metals_data.get('metals', []):
        # Core fields
        name = metal.get('name', '')

        # Generate IDs
        metal_id = generate_metal_id(name)
        metal_key = metal.get('metal_key') or slugify_metal_name(name)

        # Create row with all fields as strings
        row = {
            'metal_id': metal_id,
            'metal_key': metal_key,
            'name': canonicalize_metal_name(name),
            'name_norm': normalize_metal_name(name),
            'symbol': str(metal.get('symbol') or ''),
            'formula': str(metal.get('formula') or ''),
            'code': str(metal.get('code') or ''),
            'category_bucket': str(metal.get('category_bucket') or ''),
            'cluster_id': str(metal.get('cluster_id') or ''),
            'group_name': str(metal.get('group_name') or ''),
            'default_unit': str(metal.get('default_unit') or ''),
            'default_basis': str(metal.get('default_basis') or ''),
            'hs6': str(metal.get('hs6') or ''),
            'pra_hint': str(metal.get('pra_hint') or ''),
            'notes': str(metal.get('notes') or ''),
            'source_priority': ','.join(metal.get('sources', [])),
        }

        # Expand aliases
        alias_cols = expand_aliases(metal.get('aliases', []))
        row.update(alias_cols)

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
    issues = validate_data(df, clusters)

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
    print(f"\nWriting {len(df)} metals to {output_parquet}")
    df.to_parquet(output_parquet, index=False, engine='pyarrow')

    # Generate summary report
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"Total metals: {len(df)}")
    print(f"Output file: {output_parquet}")
    print(f"File size: {output_parquet.stat().st_size / 1024:.1f} KB")

    # Category distribution
    print("\nCategory distribution:")
    for category, count in df['category_bucket'].value_counts().items():
        if category:  # Skip empty strings
            print(f"  {category}: {count}")

    # Cluster distribution
    if clusters:
        print("\nCluster distribution:")
        cluster_counts = df[df['cluster_id'] != '']['cluster_id'].value_counts()
        for cluster, count in cluster_counts.items():
            print(f"  {cluster}: {count}")

    # Metals with units/basis
    with_units = df[(df['default_unit'] != '') & (df['default_basis'] != '')]
    print(f"\nMetals with units/basis defined: {len(with_units)}")

    # Metals with aliases
    with_aliases = df[df['alias1'] != '']
    print(f"Metals with aliases: {len(with_aliases)}")

    if issues:
        print(f"\n⚠️  Build completed with {len(issues)} validation issues")
        return 1
    else:
        print("\n✅ Build completed successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())
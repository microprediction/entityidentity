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

from entityidentity.metals.metalnormalize import (
    normalize_metal_name,
    canonicalize_metal_name,
    slugify_metal_name,
    generate_metal_id,
)
from entityidentity.utils.build_utils import expand_aliases
from entityidentity.utils.build_framework import (
    BuildConfig,
    build_entity_database,
    validate_duplicate_ids,
    validate_duplicate_keys,
    validate_required_fields,
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


def process_metal(metal: dict) -> dict:
    """Convert a metal YAML entry to a DataFrame row."""
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
    row.update(expand_aliases(metal.get('aliases', [])))

    return row


def validate_metals(df: pd.DataFrame, clusters: Optional[dict]) -> List[str]:
    """Validate metal data and return list of issues."""
    issues = []

    # Check for duplicates
    issues.extend(validate_duplicate_ids(df, 'metal_id', 'metals'))
    issues.extend(validate_duplicate_keys(df, 'metal_key', 'metals'))

    # Check for missing clusters
    if clusters:
        invalid_clusters = df[
            df['cluster_id'].notna() &
            (df['cluster_id'] != '') &
            ~df['cluster_id'].isin(clusters.keys())
        ]
        if not invalid_clusters.empty:
            invalid_names = invalid_clusters[['name', 'cluster_id']].to_dict('records')
            issues.append(f"Invalid cluster_ids found: {invalid_names}")

    # Check unit/basis consistency
    for idx, row in df.iterrows():
        unit = row.get('default_unit')
        basis = row.get('default_basis')
        if (unit and unit != '') or (basis and basis != ''):
            if not validate_basis(unit if unit != '' else None, basis if basis != '' else None):
                issues.append(
                    f"Unit/basis mismatch for {row['name']}: "
                    f"unit='{unit}', basis='{basis}'"
                )

    # Check for missing required fields
    issues.extend(validate_required_fields(df, ['name', 'metal_id', 'metal_key', 'category_bucket']))

    return issues


def generate_metal_summary(df: pd.DataFrame, clusters: Optional[dict]) -> None:
    """Print metal-specific summary statistics."""
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


def main():
    """Main build process."""
    data_dir = Path(__file__).parent

    config = BuildConfig(
        input_yaml=data_dir / "metals.yaml",
        output_parquet=data_dir / "metals.parquet",
        aux_yaml=data_dir / "supply_chain_clusters.yaml",
        process_entity=process_metal,
        validate_data=validate_metals,
        generate_summary=generate_metal_summary,
        entity_name="metal",
        entity_plural="metals",
        yaml_key="metals",
        aux_yaml_key="clusters",
    )

    return build_entity_database(config)


if __name__ == "__main__":
    sys.exit(main())
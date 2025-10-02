"""
Shared framework for building entity databases from YAML files.

This module provides common functionality for build_baskets.py and build_metals.py,
eliminating ~80% code duplication while allowing entity-specific customization.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

import pandas as pd

from entityidentity.utils.build_utils import load_yaml_file


@dataclass
class BuildConfig:
    """Configuration for building an entity database."""

    # Input source (one of these required)
    input_yaml: Optional[Path] = None  # For YAML-based entities
    input_data: Optional[List[dict]] = None  # For direct data (e.g., downloaded files)

    # File paths (required)
    output_parquet: Path = None

    # Entity-specific callbacks (required)
    process_entity: Callable[[dict], dict] = None  # Convert YAML entry to DataFrame row
    validate_data: Callable[[pd.DataFrame, Optional[dict]], List[str]] = None  # Return validation issues
    generate_summary: Callable[[pd.DataFrame, Optional[dict]], None] = None  # Print summary stats

    # Entity metadata (required)
    entity_name: str = None  # "basket", "metal", etc.
    entity_plural: str = None  # "baskets", "metals", etc.
    yaml_key: Optional[str] = None  # Key in YAML file ("baskets", "metals") - required if input_yaml used

    # Optional fields
    aux_yaml: Optional[Path] = None  # For metals' supply_chain_clusters.yaml
    aux_yaml_key: Optional[str] = None  # Key in auxiliary YAML


def build_entity_database(config: BuildConfig) -> int:
    """
    Generic build process for entity databases.

    Returns:
        0 on success, 1 if validation issues found
    """
    # Determine input source
    if config.input_data is not None:
        source = "direct data"
        print(f"Building {config.entity_plural} database from {source}")
        # Extract entities from the input_data dictionary using yaml_key
        entities = config.input_data.get(config.yaml_key, [])
    elif config.input_yaml is not None:
        source = str(config.input_yaml)
        print(f"Building {config.entity_plural} database from {source}")

        # Load source data
        print("Loading YAML files...")
        yaml_data = load_yaml_file(config.input_yaml)
        entities = yaml_data.get(config.yaml_key, [])
    else:
        raise ValueError("Either input_yaml or input_data must be provided")

    # Load auxiliary data if needed (e.g., clusters for metals)
    aux_data = None
    if config.aux_yaml and config.aux_yaml.exists():
        aux_yaml_data = load_yaml_file(config.aux_yaml)
        aux_data = aux_yaml_data.get(config.aux_yaml_key, {})
        print(f"Loaded {len(aux_data)} {config.aux_yaml_key}")

    # Process entities
    print(f"Processing {len(entities)} {config.entity_plural}...")

    rows = [config.process_entity(entity) for entity in entities]

    # Create DataFrame with all string dtypes
    df = pd.DataFrame(rows)

    # Ensure all columns are strings
    for col in df.columns:
        df[col] = df[col].astype(str)
        # Replace 'None' strings with empty strings
        df[col] = df[col].replace('None', '')

    # Validate data
    print("\nValidating data...")
    issues = config.validate_data(df, aux_data)

    if issues:
        print("\n⚠️  Validation issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print()
    else:
        print("✅ All validations passed")

    # Sort by name for consistent output (if name column exists)
    if 'name' in df.columns:
        df = df.sort_values('name').reset_index(drop=True)
    elif 'admin1' in df.columns:
        # For places, sort by admin1
        df = df.sort_values('admin1').reset_index(drop=True)
    else:
        # Sort by first column
        df = df.sort_values(df.columns[0]).reset_index(drop=True)

    # Write to Parquet
    print(f"\nWriting {len(df)} {config.entity_plural} to {config.output_parquet}")
    df.to_parquet(config.output_parquet, index=False, engine='pyarrow')

    # Generate summary report
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"Total {config.entity_plural}: {len(df)}")
    print(f"Output file: {config.output_parquet}")
    print(f"File size: {config.output_parquet.stat().st_size / 1024:.1f} KB")

    # Entity-specific summary
    config.generate_summary(df, aux_data)

    if issues:
        print(f"\n⚠️  Build completed with {len(issues)} validation issues")
        return 1
    else:
        print("\n✅ Build completed successfully")
        return 0


def validate_duplicate_ids(df: pd.DataFrame, id_field: str, entity_plural: str) -> List[str]:
    """Check for duplicate IDs."""
    issues = []
    duplicates = df[df.duplicated(subset=[id_field], keep=False)]
    if not duplicates.empty:
        dup_names = duplicates[['name', id_field]].to_dict('records')
        issues.append(f"Duplicate {id_field}s found: {dup_names}")
    return issues


def validate_duplicate_keys(df: pd.DataFrame, key_field: str, entity_plural: str) -> List[str]:
    """Check for duplicate keys."""
    issues = []
    dup_keys = df[df.duplicated(subset=[key_field], keep=False)]
    if not dup_keys.empty:
        dup_key_names = dup_keys[['name', key_field]].to_dict('records')
        issues.append(f"Duplicate {key_field}s found: {dup_key_names}")
    return issues


def validate_required_fields(df: pd.DataFrame, required_fields: List[str]) -> List[str]:
    """Check for missing required fields."""
    issues = []
    for field in required_fields:
        missing = df[df[field].isna() | (df[field] == "")]
        if not missing.empty:
            missing_names = missing['name'].tolist()
            issues.append(f"Missing {field} for entities: {missing_names}")
    return issues
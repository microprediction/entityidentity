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

from entityidentity.baskets.basketnormalize import (
    normalize_basket_name,
    canonicalize_basket_name,
    slugify_basket_name,
    generate_basket_id,
)
from entityidentity.utils.build_utils import expand_aliases, expand_components
from entityidentity.utils.build_framework import (
    BuildConfig,
    build_entity_database,
    validate_duplicate_ids,
    validate_duplicate_keys,
    validate_required_fields,
)


def process_basket(basket: dict) -> dict:
    """Convert a basket YAML entry to a DataFrame row."""
    name = basket.get('name', '')

    # Generate IDs
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

    # Expand aliases and components
    row.update(expand_aliases(basket.get('aliases', [])))
    row.update(expand_components(basket.get('components', [])))

    return row


def validate_baskets(df: pd.DataFrame, aux_data: Optional[dict]) -> List[str]:
    """Validate basket data and return list of issues."""
    issues = []

    # Check for duplicates
    issues.extend(validate_duplicate_ids(df, 'basket_id', 'baskets'))
    issues.extend(validate_duplicate_keys(df, 'basket_key', 'baskets'))

    # Check for missing required fields
    issues.extend(validate_required_fields(df, ['name', 'basket_id', 'basket_key']))

    # Check that each basket has at least one component
    no_components = df[df['component1'] == '']
    if not no_components.empty:
        no_comp_names = no_components['name'].tolist()
        issues.append(f"Baskets with no components: {no_comp_names}")

    return issues


def generate_basket_summary(df: pd.DataFrame, aux_data: Optional[dict]) -> None:
    """Print basket-specific summary statistics."""
    # Component statistics
    print("\nBasket details:")
    for idx, row in df.iterrows():
        components = [c for c in [row.get(f'component{i}', '') for i in range(1, 11)] if c]
        print(f"  {row['name']}: {len(components)} components")

    # Baskets with aliases
    with_aliases = df[df['alias1'] != '']
    print(f"\nBaskets with aliases: {len(with_aliases)}")


def main():
    """Main build process."""
    data_dir = Path(__file__).parent

    config = BuildConfig(
        input_yaml=data_dir / "baskets.yaml",
        output_parquet=data_dir / "baskets.parquet",
        process_entity=process_basket,
        validate_data=validate_baskets,
        generate_summary=generate_basket_summary,
        entity_name="basket",
        entity_plural="baskets",
        yaml_key="baskets",
    )

    return build_entity_database(config)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Build units.parquet database from unit configuration and conversion rules.

This script:
1. Loads unit definitions and conversion rules
2. Generates unit_id using sha1(normalize(name) + '|unit')[:16]
3. Expands unit aliases and conversions
4. Validates unit/basis consistency
5. Writes units.parquet with all columns as strings
"""

import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Optional
import yaml

import pandas as pd

from entityidentity.utils.build_utils import expand_aliases
from entityidentity.utils.build_framework import (
    BuildConfig,
    build_entity_database,
    validate_duplicate_ids,
    validate_duplicate_keys,
    validate_required_fields,
)


def normalize_unit_name(name: str) -> str:
    """Normalize unit name for matching."""
    if not name:
        return ""

    # Convert to lowercase and strip
    normalized = name.lower().strip()

    # Remove common punctuation
    normalized = normalized.replace("-", "").replace("_", "").replace(" ", "")

    # Standardize common patterns
    replacements = {
        "usd": "$",
        "dollar": "$",
        "pound": "lb",
        "pounds": "lb",
        "kilogram": "kg",
        "kilograms": "kg",
        "tonne": "t",
        "tonnes": "t",
        "metricton": "mt",
        "metrictons": "mt",
        "troyounce": "toz",
        "troyoz": "toz",
        "ounce": "oz",
    }

    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized


def generate_unit_id(name: str) -> str:
    """Generate stable unit ID from name."""
    if not name:
        return ""

    # Normalize and hash
    normalized = normalize_unit_name(name)
    content = f"{normalized}|unit"
    hash_obj = hashlib.sha1(content.encode())

    # Return first 16 chars of hex digest
    return hash_obj.hexdigest()[:16]


def load_unit_data() -> Dict[str, List[dict]]:
    """Load unit definitions from various sources."""
    data_dir = Path(__file__).parent
    units_dir = data_dir.parent

    units = []

    # Load from unitconfig.yaml
    config_file = units_dir / "unitconfig.yaml"
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

            # Process material-specific units
            for material, spec in config.items():
                if material == "conversion_constants":
                    continue

                if isinstance(spec, dict) and 'canonical_unit' in spec:
                    units.append({
                        'name': f"{material} {spec['canonical_unit']}",
                        'unit_key': material.lower(),
                        'material': material,
                        'canonical_unit': spec['canonical_unit'],
                        'canonical_basis': spec.get('canonical_basis', ''),
                        'requires': ','.join(spec.get('requires', [])),
                        'conversion_note': spec.get('conversion_note', ''),
                        'source': spec.get('source', 'unitconfig.yaml'),
                        'category': 'material_specific',
                    })

    # Add standard mass units
    mass_units = [
        {
            'name': 'Metric Ton',
            'unit_key': 'mt',
            'symbol': 't',
            'aliases': ['metric ton', 'tonne', 'MT', 'metric tonne'],
            'category': 'mass',
            'si_factor': 1000.0,  # kg
            'source': 'standard',
        },
        {
            'name': 'Kilogram',
            'unit_key': 'kg',
            'symbol': 'kg',
            'aliases': ['kilogram', 'kilo', 'KG'],
            'category': 'mass',
            'si_factor': 1.0,
            'source': 'standard',
        },
        {
            'name': 'Pound',
            'unit_key': 'lb',
            'symbol': 'lb',
            'aliases': ['pound', 'lbs', 'LB', 'pounds'],
            'category': 'mass',
            'si_factor': 0.453592,  # kg
            'source': 'standard',
        },
        {
            'name': 'Short Ton',
            'unit_key': 'short_ton',
            'symbol': 'st',
            'aliases': ['short ton', 'ton', 'US ton'],
            'category': 'mass',
            'si_factor': 907.185,  # kg
            'source': 'standard',
        },
        {
            'name': 'Long Ton',
            'unit_key': 'long_ton',
            'symbol': 'lt',
            'aliases': ['long ton', 'imperial ton', 'UK ton'],
            'category': 'mass',
            'si_factor': 1016.05,  # kg
            'source': 'standard',
        },
        {
            'name': 'Troy Ounce',
            'unit_key': 'toz',
            'symbol': 'oz t',
            'aliases': ['troy ounce', 'troy oz', 'toz', 'ozt'],
            'category': 'mass_precious',
            'si_factor': 0.0311035,  # kg
            'source': 'standard',
        },
        {
            'name': 'Metric Ton Unit',
            'unit_key': 'mtu',
            'symbol': 'mtu',
            'aliases': ['MTU', 'metric ton unit'],
            'category': 'mass_concentrate',
            'si_factor': 10.0,  # kg (1% of metric ton)
            'source': 'standard',
        },
    ]

    # Add currency units
    currency_units = [
        {
            'name': 'US Dollar',
            'unit_key': 'usd',
            'symbol': '$',
            'aliases': ['USD', 'dollar', 'dollars', 'US$'],
            'category': 'currency',
            'source': 'standard',
        },
        {
            'name': 'Euro',
            'unit_key': 'eur',
            'symbol': '€',
            'aliases': ['EUR', 'euro', 'euros'],
            'category': 'currency',
            'source': 'standard',
        },
        {
            'name': 'British Pound',
            'unit_key': 'gbp',
            'symbol': '£',
            'aliases': ['GBP', 'pound sterling', 'sterling'],
            'category': 'currency',
            'source': 'standard',
        },
        {
            'name': 'Chinese Yuan',
            'unit_key': 'cny',
            'symbol': '¥',
            'aliases': ['CNY', 'yuan', 'renminbi', 'RMB'],
            'category': 'currency',
            'source': 'standard',
        },
    ]

    # Add composite price units
    price_units = [
        {
            'name': 'USD per pound',
            'unit_key': 'usd_lb',
            'symbol': '$/lb',
            'aliases': ['USD/lb', '$/pound', 'dollars per pound'],
            'category': 'price_per_mass',
            'numerator': 'usd',
            'denominator': 'lb',
            'source': 'standard',
        },
        {
            'name': 'USD per metric ton',
            'unit_key': 'usd_mt',
            'symbol': '$/t',
            'aliases': ['USD/t', '$/MT', 'USD/MT', 'dollars per tonne'],
            'category': 'price_per_mass',
            'numerator': 'usd',
            'denominator': 'mt',
            'source': 'standard',
        },
        {
            'name': 'USD per troy ounce',
            'unit_key': 'usd_toz',
            'symbol': '$/oz',
            'aliases': ['USD/oz', '$/toz', 'USD/toz', 'dollars per ounce'],
            'category': 'price_per_mass',
            'numerator': 'usd',
            'denominator': 'toz',
            'source': 'standard',
        },
        {
            'name': 'USD per MTU',
            'unit_key': 'usd_mtu',
            'symbol': '$/mtu',
            'aliases': ['USD/mtu', '$/MTU', 'dollars per MTU'],
            'category': 'price_per_mass',
            'numerator': 'usd',
            'denominator': 'mtu',
            'source': 'standard',
        },
    ]

    units.extend(mass_units)
    units.extend(currency_units)
    units.extend(price_units)

    return {'units': units}


def process_unit(unit: dict) -> dict:
    """Convert a unit entry to a DataFrame row."""
    name = unit.get('name', '')

    # Generate IDs
    unit_id = generate_unit_id(name)
    unit_key = unit.get('unit_key', '').lower()

    # Create row with all fields as strings
    row = {
        'unit_id': unit_id,
        'unit_key': unit_key,
        'name': name,
        'name_norm': normalize_unit_name(name),
        'symbol': str(unit.get('symbol', '')),
        'category': str(unit.get('category', '')),
        'material': str(unit.get('material', '')),
        'canonical_unit': str(unit.get('canonical_unit', '')),
        'canonical_basis': str(unit.get('canonical_basis', '')),
        'requires': str(unit.get('requires', '')),
        'conversion_note': str(unit.get('conversion_note', '')),
        'si_factor': str(unit.get('si_factor', '')),
        'numerator': str(unit.get('numerator', '')),
        'denominator': str(unit.get('denominator', '')),
        'source': str(unit.get('source', '')),
    }

    # Expand aliases
    row.update(expand_aliases(unit.get('aliases', [])))

    return row


def validate_units(df: pd.DataFrame, aux_data: Optional[dict]) -> List[str]:
    """Validate unit data and return list of issues."""
    issues = []

    # Check for duplicates
    issues.extend(validate_duplicate_ids(df, 'unit_id', 'units'))
    issues.extend(validate_duplicate_keys(df, 'unit_key', 'units'))

    # Check for composite units with missing components
    composite_units = df[df['category'] == 'price_per_mass']
    for idx, row in composite_units.iterrows():
        numerator = row.get('numerator', '')
        denominator = row.get('denominator', '')

        if numerator and numerator not in df['unit_key'].values:
            issues.append(f"Unknown numerator unit '{numerator}' in {row['name']}")

        if denominator and denominator not in df['unit_key'].values:
            issues.append(f"Unknown denominator unit '{denominator}' in {row['name']}")

    # Check for required fields
    issues.extend(validate_required_fields(df, ['name', 'unit_id', 'unit_key', 'category']))

    return issues


def generate_unit_summary(df: pd.DataFrame, aux_data: Optional[dict]) -> None:
    """Print unit-specific summary statistics."""
    # Category distribution
    print("\nCategory distribution:")
    for category, count in df['category'].value_counts().items():
        if category:  # Skip empty strings
            print(f"  {category}: {count}")

    # Units with SI factors
    with_si = df[df['si_factor'] != '']
    print(f"\nUnits with SI conversion factors: {len(with_si)}")

    # Material-specific units
    material_units = df[df['material'] != '']
    print(f"Material-specific units: {len(material_units)}")

    # Composite units
    composite = df[df['numerator'] != '']
    print(f"Composite price units: {len(composite)}")

    # Units with aliases
    with_aliases = df[df['alias1'] != '']
    print(f"Units with aliases: {len(with_aliases)}")


def main():
    """Main build process."""
    data_dir = Path(__file__).parent

    # Load unit data
    unit_data = load_unit_data()

    # Create config using the loaded data
    config = BuildConfig(
        input_yaml=None,  # We're loading programmatically
        output_parquet=data_dir / "units.parquet",
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

    return build_entity_database(config)


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
CLI tool for testing metal resolution.

Usage:
    python test_metal_resolution.py <metal_name> [--category CATEGORY] [--cluster CLUSTER] [--threshold THRESHOLD]
    python test_metal_resolution.py --list [--category CATEGORY] [--cluster CLUSTER]
    python test_metal_resolution.py --extract "text with metals"
    python test_metal_resolution.py --match <metal_name> [--k K]

Examples:
    python test_metal_resolution.py "Pt"
    python test_metal_resolution.py "chrome" --category ferroalloy
    python test_metal_resolution.py "APT 88.5%"
    python test_metal_resolution.py --list --category pgm
    python test_metal_resolution.py --extract "The Pt/Pd ratio is important"
    python test_metal_resolution.py --match tungsten --k 5
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from entityidentity import (
    metal_identifier,
    match_metal,
    list_metals,
    load_metals,
    extract_metals_from_text
)


def resolve_metal(args):
    """Resolve a single metal name."""
    result = metal_identifier(
        args.metal_name,
        category=args.category,
        cluster=args.cluster,
        threshold=args.threshold
    )

    if result:
        print(f"✅ Resolved: '{args.metal_name}'")
        print("-" * 50)
        print(f"Name: {result['name']}")
        print(f"Metal Key: {result.get('metal_key', 'N/A')}")

        if result.get('symbol'):
            print(f"Symbol: {result['symbol']}")
        if result.get('formula'):
            print(f"Formula: {result['formula']}")
        if result.get('code'):
            print(f"Code: {result['code']}")

        print(f"Category: {result.get('category_bucket', 'N/A')}")
        print(f"Cluster: {result.get('cluster_id', 'N/A')}")

        if result.get('default_unit'):
            print(f"Default Unit: {result['default_unit']}")
        if result.get('default_basis'):
            print(f"Default Basis: {result['default_basis']}")
        if result.get('pra_hint'):
            print(f"PRA Hint: {result['pra_hint']}")

        if result.get('aliases'):
            aliases = [a for a in [result.get(f'alias{i}') for i in range(1, 11)] if a]
            if aliases:
                print(f"Aliases: {', '.join(aliases)}")

        if result.get('notes'):
            print(f"Notes: {result['notes']}")
        if result.get('sources'):
            print(f"Sources: {result['sources']}")
    else:
        print(f"❌ No match found for '{args.metal_name}' with threshold {args.threshold}")
        print("\nTry lowering the threshold or use --match to see candidates")


def list_metals_cmd(args):
    """List metals filtered by category or cluster."""
    metals = list_metals(category=args.category, cluster=args.cluster)

    if metals.empty:
        print("No metals found with the specified filters")
        return

    filter_desc = []
    if args.category:
        filter_desc.append(f"category='{args.category}'")
    if args.cluster:
        filter_desc.append(f"cluster='{args.cluster}'")

    print(f"Metals {' with ' + ' and '.join(filter_desc) if filter_desc else ''}:")
    print("-" * 80)

    for _, metal in metals.iterrows():
        line = f"• {metal['name']}"

        details = []
        if metal.get('symbol'):
            details.append(f"[{metal['symbol']}]")
        if metal.get('code'):
            details.append(f"code={metal['code']}")
        if metal.get('formula'):
            details.append(f"formula={metal['formula']}")

        if details:
            line += f" {' '.join(details)}"

        print(line)

    print(f"\nTotal: {len(metals)} metals")


def match_metal_cmd(args):
    """Find top-K matches for a metal name."""
    candidates = match_metal(args.metal_name, k=args.k)

    if not candidates:
        print(f"No matches found for '{args.metal_name}'")
        return

    print(f"Top {args.k} matches for '{args.metal_name}':")
    print("-" * 50)

    for i, cand in enumerate(candidates, 1):
        print(f"\n{i}. {cand['name']} (score: {cand.get('score', 'N/A')})")

        if cand.get('symbol'):
            print(f"   Symbol: {cand['symbol']}")
        if cand.get('code'):
            print(f"   Code: {cand['code']}")
        if cand.get('formula'):
            print(f"   Formula: {cand['formula']}")
        print(f"   Category: {cand.get('category_bucket', 'N/A')}")
        print(f"   Key: {cand.get('metal_key', 'N/A')}")


def extract_metals_cmd(args):
    """Extract metals from text."""
    metals = extract_metals_from_text(args.text)

    if not metals:
        print(f"No metals found in text")
        return

    print(f"Metals found in text:")
    print("-" * 50)
    print(f"Text: '{args.text}'")
    print()

    for metal in metals:
        snippet = args.text[metal['span'][0]:metal['span'][1]]
        print(f"• '{snippet}' -> {metal['query']}")
        print(f"  Type: {metal['hint']}")
        if 'category' in metal:
            print(f"  Category: {metal['category']}")
        if 'cluster' in metal:
            print(f"  Cluster: {metal['cluster']}")
        print(f"  Position: {metal['span']}")

        # Try to resolve it
        resolved = metal_identifier(metal['query'], category=metal.get('category'))
        if resolved:
            print(f"  ✓ Resolves to: {resolved['name']} ({resolved.get('metal_key', 'N/A')})")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Test metal resolution from entityidentity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Create subparsers for different modes
    parser.add_argument('metal_name', nargs='?', help='Metal name to resolve')
    parser.add_argument('--category', help='Category hint (e.g., pgm, battery, ferroalloy)')
    parser.add_argument('--cluster', help='Cluster hint (e.g., pgm_complex, lithium_chain)')
    parser.add_argument('--threshold', type=int, default=90, help='Matching threshold (default: 90)')

    # List mode
    parser.add_argument('--list', action='store_true', help='List metals')

    # Match mode
    parser.add_argument('--match', action='store_true', help='Find top-K matches')
    parser.add_argument('--k', type=int, default=5, help='Number of matches to return (default: 5)')

    # Extract mode
    parser.add_argument('--extract', metavar='TEXT', help='Extract metals from text')

    # Info mode
    parser.add_argument('--info', action='store_true', help='Show database info')

    args = parser.parse_args()

    # Load database once
    try:
        metals_df = load_metals()
    except Exception as e:
        print(f"Error loading metals database: {e}")
        print("Make sure to run build_metals.py first")
        sys.exit(1)

    # Handle different modes
    if args.info:
        print(f"Metals Database Information:")
        print("-" * 50)
        print(f"Total metals: {len(metals_df)}")
        print(f"\\nCategories:")
        for cat, count in metals_df['category_bucket'].value_counts().items():
            print(f"  {cat:12} : {count:3} metals")
        print(f"\\nClusters:")
        for cluster, count in metals_df['cluster_id'].value_counts().items():
            if cluster:  # Skip empty clusters
                print(f"  {cluster:25} : {count:3} metals")
    elif args.list:
        list_metals_cmd(args)
    elif args.extract:
        args.text = args.extract
        extract_metals_cmd(args)
    elif args.match and args.metal_name:
        match_metal_cmd(args)
    elif args.metal_name:
        resolve_metal(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
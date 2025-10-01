#!/usr/bin/env python3
"""
Test script for metalextractor module.
"""

from entityidentity.metals.metalextractor import extract_metals_from_text, extract_metal_pairs

def test_extraction():
    """Test various extraction patterns."""

    test_cases = [
        # Element symbols
        "The Pt/Pd ratio in the catalyst is important",
        "Ni-Co sulfides are found in laterite deposits",
        "We need 100kg of Cu for the project",

        # Trade specifications
        "APT 88.5% is trading at $320/mtu",
        "P1020 aluminum ingots are in high demand",
        "SHG zinc prices have increased",

        # Chemical forms
        "Lithium carbonate demand is growing for batteries",
        "We produce ferro-chrome for stainless steel",
        "Battery grade lithium hydroxide (LiOH) is critical",
        "NdPr oxide is used in permanent magnets",

        # Mixed content
        "The mine produces copper concentrate with Au and Ag credits",
        "Cobalt sulfate (CoSO4) and nickel sulfate are battery precursors",
        "Natural graphite competes with synthetic graphite in anodes",

        # Percentages
        "We need 99.5% copper cathodes",
        "The ferro-vanadium contains 80% V",

        # Complex text
        "The PGM complex includes Pt, Pd, Rh, Ru, Ir, and Os from the Bushveld",
        "Battery metals like Li, Co, Ni, and graphite are essential for EVs"
    ]

    print("Metal Extraction Test Results")
    print("=" * 60)

    for i, text in enumerate(test_cases, 1):
        print(f"\nTest {i}: {text[:60]}{'...' if len(text) > 60 else ''}")
        print("-" * 40)

        results = extract_metals_from_text(text)

        if results:
            for result in results:
                matched_text = text[result['span'][0]:result['span'][1]]
                print(f"  Found: '{matched_text}' -> {result['query']}")
                print(f"    Type: {result['hint']}", end="")
                if 'category' in result:
                    print(f", Category: {result['category']}", end="")
                print(f"\n    Position: {result['span']}")
        else:
            print("  No metals found")

    # Test pair extraction
    print("\n" + "=" * 60)
    print("Metal Pair Extraction Tests")
    print("=" * 60)

    pair_tests = [
        "Pt/Pd ratio is important",
        "Ni-Co laterites",
        "Cu/Au/Ag polymetallic deposits",
        "The Sn-Ta-Nb-W belt"
    ]

    for text in pair_tests:
        pairs = extract_metal_pairs(text)
        print(f"\nText: {text}")
        if pairs:
            print(f"  Pairs found: {pairs}")
        else:
            print("  No pairs found")

if __name__ == "__main__":
    test_extraction()
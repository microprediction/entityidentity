#!/usr/bin/env python3
"""Filter company database to mining and energy sectors only.

**DEPRECATED**: This standalone script is deprecated in favor of the unified
filtering API in entityidentity.companies.companyfilter. Use that module instead:

    from entityidentity.companies.companyfilter import filter_companies

    # Keyword-only (same as this script)
    filtered = filter_companies(df, strategy='keyword')

    # Hybrid (keyword + LLM refinement, recommended)
    filtered = filter_companies(df, strategy='hybrid')

    # LLM-only (most accurate)
    filtered = filter_companies(df, strategy='llm')

This script remains for backwards compatibility but may be removed in future versions.

---

This script takes the full companies database and filters it to include only
companies in the mining and energy sectors using keyword-based rules.

Sector Classification:
- Mining: Metals, minerals, coal, precious metals
- Energy: Oil, gas, renewables, utilities, power generation

Uses industry classifications from:
- GICS (Global Industry Classification Standard)
- NACE (EU classification)
- NAICS (North American Industry Classification)
- SIC (Standard Industrial Classification)

Usage:
    python scripts/companies/filter_mining_energy.py
    python scripts/companies/filter_mining_energy.py --input data/all_companies.parquet
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Known major mining/energy companies (whitelist for edge cases)
KNOWN_MINING_ENERGY_COMPANIES = [
    'anglo american', 'bhp', 'rio tinto', 'vale', 'glencore',
    'freeport', 'newmont', 'barrick', 'southern copper',
    'exxon', 'chevron', 'shell', 'bp', 'totalenergies',
    'conocophillips', 'equinor', 'eni', 'petrobras',
]

# Mining and Energy sector keywords and codes
MINING_KEYWORDS = [
    'mining', 'mine', 'mineral', 'metals', 'gold', 'silver', 'copper',
    'iron', 'steel', 'aluminum', 'zinc', 'lead', 'nickel', 'lithium',
    'rare earth', 'coal', 'diamond', 'platinum', 'palladium', 'uranium',
    'exploration', 'ore', 'quarry', 'extraction', 'smelter', 'refinery',
    'resources', 'commodities', 'cobre', 'minera', 'miner'
]

ENERGY_KEYWORDS = [
    'energy', 'oil', 'gas', 'petroleum', 'lng', 'lpg', 'pipeline',
    'drilling', 'offshore', 'onshore', 'refining', 'exploration',
    'power', 'electric', 'electricity', 'utility', 'utilities',
    'solar', 'wind', 'renewable', 'hydro', 'nuclear', 'geothermal',
    'coal', 'battery', 'storage', 'grid', 'transmission'
]

# GICS Industry Codes (Level 2 - Industry Group)
# 1010 - Energy
# 1510 - Materials (includes mining)
GICS_CODES = ['10', '15', '1010', '1510']

# NAICS Codes
# 21 - Mining, Quarrying, and Oil and Gas Extraction
# 211 - Oil and Gas Extraction
# 212 - Mining (except Oil and Gas)
# 213 - Support Activities for Mining
# 221 - Utilities
NAICS_CODES = ['21', '211', '212', '213', '221', '2211', '2212']

# NACE Codes (EU)
# B - Mining and quarrying
# D - Electricity, gas, steam and air conditioning supply
NACE_CODES = ['B', 'D', '05', '06', '07', '08', '09', '35']


def matches_mining_energy(row: pd.Series) -> bool:
    """Check if a company matches mining or energy criteria.
    
    Args:
        row: DataFrame row with company data
        
    Returns:
        True if company is in mining/energy sector
    """
    # Check name against known companies whitelist first
    name = str(row.get('name', '')).lower()
    name_normalized = str(row.get('name_norm', '')).lower()
    
    for known_company in KNOWN_MINING_ENERGY_COMPANIES:
        if known_company in name or known_company in name_normalized:
            return True
    
    # Check name for keywords
    if any(keyword in name for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
        return True
    
    # Check industry field if available
    if 'industry' in row.index and pd.notna(row['industry']):
        industry = str(row['industry']).lower()
        if any(keyword in industry for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
            return True
    
    # Check sector field if available
    if 'sector' in row.index and pd.notna(row['sector']):
        sector = str(row['sector']).lower()
        if any(keyword in sector for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
            return True
    
    # Check GICS code if available
    if 'gics' in row.index and pd.notna(row['gics']):
        gics = str(row['gics'])
        if any(gics.startswith(code) for code in GICS_CODES):
            return True
    
    # Check NAICS code if available
    if 'naics' in row.index and pd.notna(row['naics']):
        naics = str(row['naics'])
        if any(naics.startswith(code) for code in NAICS_CODES):
            return True
    
    # Check NACE code if available
    if 'nace' in row.index and pd.notna(row['nace']):
        nace = str(row['nace']).upper()
        if any(nace.startswith(code) for code in NACE_CODES):
            return True
    
    # Check aliases for keywords
    if 'aliases' in row.index and isinstance(row['aliases'], list):
        for alias in row['aliases']:
            alias_lower = str(alias).lower()
            if any(keyword in alias_lower for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
                return True
    
    return False


def filter_database(
    input_path: Path,
    output_path: Path,
    verbose: bool = False
) -> pd.DataFrame:
    """Filter company database to mining and energy sectors.
    
    Args:
        input_path: Path to input parquet/csv file
        output_path: Path to output filtered parquet file
        verbose: Print detailed progress
        
    Returns:
        Filtered DataFrame
    """
    print(f"Loading database from {input_path}...")
    
    # Load data
    if input_path.suffix == '.parquet':
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path)
    
    print(f"Total companies: {len(df):,}")
    
    # Apply filter
    print("Filtering for mining and energy sectors...")
    mask = df.apply(matches_mining_energy, axis=1)
    filtered = df[mask].copy()
    
    print(f"Matched companies: {len(filtered):,} ({len(filtered)/len(df)*100:.1f}%)")
    
    # Show breakdown by source
    if 'source' in filtered.columns:
        print("\nBreakdown by source:")
        for source, count in filtered['source'].value_counts().items():
            print(f"  - {source:15s}: {count:6,}")
    
    # Show top countries
    if 'country' in filtered.columns:
        print("\nTop 10 countries:")
        for country, count in filtered['country'].value_counts().head(10).items():
            print(f"  - {country}: {count:,}")
    
    # Save filtered data
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_parquet(output_path, index=False, compression='snappy')
    
    # Also save CSV preview and info
    csv_path = output_path.with_suffix('.csv')
    preview_rows = min(500, len(filtered))
    print(f"Creating CSV preview: {csv_path} ({preview_rows} rows)")
    filtered.head(preview_rows).to_csv(csv_path, index=False)
    
    # Create info file
    info_path = output_path.parent / 'companies_info.txt'
    print(f"Creating info file: {info_path}")
    _write_info_file(info_path, filtered, input_path, output_path)
    
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\n✅ Filtered database saved: {size_mb:.2f} MB")
    
    return filtered


def _write_info_file(info_path: Path, data: pd.DataFrame, input_path: Path, output_path: Path):
    """Write database statistics to info file."""
    with open(info_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Mining & Energy Companies Database\n")
        f.write("=" * 70 + "\n")
        f.write(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Filtered from: {input_path.name}\n")
        f.write(f"Filter: Mining and Energy sectors only\n")
        f.write(f"\n")
        
        f.write(f"Total Companies: {len(data):,}\n")
        f.write(f"\n")
        
        if 'source' in data.columns:
            f.write("Breakdown by Source:\n")
            source_counts = data['source'].value_counts()
            for source, count in source_counts.items():
                pct = count / len(data) * 100
                f.write(f"  - {source:15s}: {count:6,} companies ({pct:5.1f}%)\n")
            f.write(f"\n")
        
        f.write("Data Coverage:\n")
        lei_count = data['lei'].notna().sum()
        lei_pct = lei_count / len(data) * 100
        f.write(f"  - With LEI:          {lei_count:6,} ({lei_pct:5.1f}%)\n")
        
        qid_count = data['wikidata_qid'].notna().sum() if 'wikidata_qid' in data.columns else 0
        qid_pct = qid_count / len(data) * 100
        f.write(f"  - With Wikidata QID: {qid_count:6,} ({qid_pct:5.1f}%)\n")
        
        if 'aliases' in data.columns:
            alias_count = data['aliases'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False).sum()
            alias_pct = alias_count / len(data) * 100
            f.write(f"  - With Aliases:      {alias_count:6,} ({alias_pct:5.1f}%)\n")
        f.write(f"\n")
        
        f.write("Top 15 Countries:\n")
        top_countries = data['country'].value_counts().head(15)
        for country, count in top_countries.items():
            pct = count / len(data) * 100
            f.write(f"  - {country}: {count:6,} ({pct:5.1f}%)\n")
        f.write(f"\n")
        
        f.write("Database Files:\n")
        if output_path.exists():
            size_mb = output_path.stat().st_size / 1024 / 1024
            f.write(f"  - Parquet: {output_path.name} ({size_mb:.2f} MB)\n")
        
        csv_path = output_path.with_suffix('.csv')
        if csv_path.exists():
            size_kb = csv_path.stat().st_size / 1024
            csv_rows = min(500, len(data))
            f.write(f"  - CSV Preview: {csv_path.name} ({size_kb:.1f} KB, {csv_rows} rows)\n")
        
        f.write(f"\n")
        f.write("Sector Focus:\n")
        f.write(f"  - Mining (metals, minerals, precious metals)\n")
        f.write(f"  - Energy (oil, gas, renewables, utilities)\n")
        f.write(f"\n")
        f.write("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Filter companies database to mining and energy sectors only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        '--input', '-i',
        type=Path,
        default=Path('tables/companies/companies_full.parquet'),
        help='Input parquet/csv file (default: tables/companies/companies_full.parquet)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('tables/companies/companies.parquet'),
        help='Output parquet file (default: tables/companies/companies.parquet)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        print(f"\nFirst build the full database with:")
        print(f"  python scripts/companies/update_companies_db.py --output {args.input}")
        return 1
    
    try:
        filter_database(args.input, args.output, args.verbose)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


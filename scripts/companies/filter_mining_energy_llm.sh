#!/bin/bash
# Wrapper script to run LLM-based company filtering
# All Python code lives in entityidentity.companies.companyfilter

python3 -c "
import sys
import argparse
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path('$0').parent.parent.parent))

from entityidentity.companies.companyfilter import filter_companies_llm, load_config

def write_info_file(info_path, data, input_path, provider, model):
    \"\"\"Write database statistics to info file.\"\"\"
    from datetime import datetime
    
    with open(info_path, 'w') as f:
        f.write('=' * 70 + '\n')
        f.write('Mining & Energy Companies Database\n')
        f.write('=' * 70 + '\n')
        f.write(f'\nGenerated: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\n')
        f.write(f'Filtered from: {input_path.name}\n')
        f.write(f'Filter: LLM classification ({provider} {model})\n\n')
        
        f.write(f'Total Companies: {len(data):,}\n\n')
        
        if 'source' in data.columns:
            f.write('Breakdown by Source:\n')
            for source, count in data['source'].value_counts().items():
                pct = count / len(data) * 100
                f.write(f'  - {source:15s}: {count:6,} ({pct:5.1f}%)\n')
            f.write('\n')
        
        f.write('Top 15 Countries:\n')
        for country, count in data['country'].value_counts().head(15).items():
            pct = count / len(data) * 100
            f.write(f'  - {country}: {count:6,} ({pct:5.1f}%)\n')
        f.write('\n' + '=' * 70 + '\n')

parser = argparse.ArgumentParser(description='Filter companies to mining/energy using LLM')
parser.add_argument('--input', '-i', type=Path, default=Path('tables/companies/companies_full.parquet'))
parser.add_argument('--output', '-o', type=Path, default=Path('tables/companies/companies.parquet'))
parser.add_argument('--provider', '-p', choices=['openai', 'anthropic'], default='openai')
parser.add_argument('--model', '-m', default=None)
parser.add_argument('--cache-file', '-c', type=Path, default=Path('.cache/companies/classifications.json'))
parser.add_argument('--confidence', '-t', type=float, default=0.7)
parser.add_argument('--batch-size', '-b', type=int, default=100)
parser.add_argument('--config', type=Path, default=None)

args = parser.parse_args()

if not args.input.exists():
    print(f'Error: Input file not found: {args.input}')
    sys.exit(1)

try:
    # Load data
    print(f'Loading database from {args.input}...')
    if args.input.suffix == '.parquet':
        df = pd.read_parquet(args.input)
    else:
        df = pd.read_csv(args.input)
    
    # Filter using LLM
    filtered = filter_companies_llm(
        df,
        provider=args.provider,
        model=args.model,
        cache_file=args.cache_file,
        confidence_threshold=args.confidence,
        batch_size=args.batch_size,
        config_path=args.config,
    )
    
    # Save output
    print(f'\nSaving to {args.output}...')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_parquet(args.output, index=False, compression='snappy')
    
    # Save CSV preview
    csv_path = args.output.with_suffix('.csv')
    preview_rows = min(500, len(filtered))
    print(f'Creating CSV preview: {csv_path} ({preview_rows} rows)')
    filtered.head(preview_rows).to_csv(csv_path, index=False)
    
    # Create info file
    info_path = args.output.parent / 'companies_info.txt'
    print(f'Creating info file: {info_path}')
    write_info_file(info_path, filtered, args.input, args.provider, args.model or 'default')
    
    size_mb = args.output.stat().st_size / 1024 / 1024
    print(f'\n✅ Filtered database saved: {size_mb:.2f} MB')
    
except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"


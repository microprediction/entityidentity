#!/bin/bash
# Wrapper script for LLM-based company filtering
#
# This script wraps entityidentity.companies.companyfilter with additional
# convenience features like CSV preview and info file generation.
#
# NOTE: For direct API access, use the Python module:
#   python -m entityidentity.companies.companyfilter --strategy llm --input ... --output ...
#
# This script adds:
#   - Automatic cache file configuration
#   - CSV preview generation (first 500 rows)
#   - Info file generation with statistics
#   - Colorized output
#
# Usage:
#   ./filter_mining_energy_llm.sh --input companies.parquet --output filtered.parquet
#   ./filter_mining_energy_llm.sh --provider anthropic --model claude-3-haiku
#
# All arguments are passed through to the Python module.

set -e  # Exit on error

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Parse key arguments for post-processing
INPUT=""
OUTPUT=""
PROVIDER="openai"
MODEL=""

# Simple argument parsing to extract key values
while [[ $# -gt 0 ]]; do
    case $1 in
        --input|-i)
            INPUT="$2"
            shift 2
            ;;
        --output|-o)
            OUTPUT="$2"
            shift 2
            ;;
        --provider|-p)
            PROVIDER="$2"
            shift 2
            ;;
        --model|-m)
            MODEL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Set defaults if not provided
INPUT=${INPUT:-"tables/companies/companies_full.parquet"}
OUTPUT=${OUTPUT:-"tables/companies/companies.parquet"}

# Reconstruct arguments for Python
ARGS=()
ARGS+=("--input" "$INPUT")
ARGS+=("--output" "$OUTPUT")
ARGS+=("--strategy" "llm")  # Explicitly use LLM strategy
ARGS+=("--provider" "$PROVIDER")
[[ -n "$MODEL" ]] && ARGS+=("--model" "$MODEL")

# Add default cache file if not specified
if [[ ! " ${ARGS[@]} " =~ " --cache-file " ]]; then
    ARGS+=("--cache-file" ".cache/companies/classifications.json")
fi

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Running LLM-based company filtering...${NC}"
echo ""

# Run the Python module directly
cd "$PROJECT_ROOT"
python -m entityidentity.companies.companyfilter "${ARGS[@]}" "$@"

# Check if successful
if [ $? -eq 0 ]; then
    # Post-processing: Create CSV preview and info file
    echo ""
    echo -e "${BLUE}Creating additional output files...${NC}"

    python3 - <<EOF
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

output_path = Path("$OUTPUT")
input_path = Path("$INPUT")
provider = "$PROVIDER"
model = "$MODEL" or "default"

if not output_path.exists():
    print("Warning: Output file not found, skipping post-processing")
    sys.exit(0)

# Load filtered data
filtered = pd.read_parquet(output_path)

# Create CSV preview (up to 500 rows)
csv_path = output_path.with_suffix('.csv')
preview_rows = min(500, len(filtered))
print(f"Creating CSV preview: {csv_path} ({preview_rows} rows)")
filtered.head(preview_rows).to_csv(csv_path, index=False)

# Create info file
info_path = output_path.parent / 'companies_info.txt'
print(f"Creating info file: {info_path}")

with open(info_path, 'w') as f:
    f.write("=" * 70 + "\n")
    f.write("Mining & Energy Companies Database\n")
    f.write("=" * 70 + "\n")
    f.write(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Filtered from: {input_path.name}\n")
    f.write(f"Filter: LLM classification ({provider} {model})\n\n")

    f.write(f"Total Companies: {len(filtered):,}\n\n")

    if 'source' in filtered.columns:
        f.write("Breakdown by Source:\n")
        for source, count in filtered['source'].value_counts().items():
            pct = count / len(filtered) * 100
            f.write(f"  - {source:15s}: {count:6,} ({pct:5.1f}%)\n")
        f.write("\n")

    f.write("Top 15 Countries:\n")
    for country, count in filtered['country'].value_counts().head(15).items():
        pct = count / len(filtered) * 100
        f.write(f"  - {country}: {count:6,} ({pct:5.1f}%)\n")
    f.write("\n" + "=" * 70 + "\n")

print("\n✅ Post-processing complete!")
EOF

    echo ""
    echo -e "${GREEN}✅ Filtering and post-processing complete!${NC}"
    echo "Output files:"
    echo "  - Parquet: $OUTPUT"
    echo "  - CSV preview: ${OUTPUT%.parquet}.csv"
    echo "  - Info file: $(dirname "$OUTPUT")/companies_info.txt"
else
    echo "❌ Filtering failed"
    exit 1
fi

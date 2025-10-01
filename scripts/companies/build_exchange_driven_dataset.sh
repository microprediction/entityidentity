#!/bin/bash
# Build dataset using Exchange-Driven GLEIF Filtering
#
# This is the SMART approach suggested by the user:
#   1. Download exchanges (FREE, 2 min)
#   2. Download GLEIF (FREE, 30-45 min)  
#   3. Fuzzy match exchanges → GLEIF (FREE, 2 min)
#   4. LLM classify matched subset (~$4, 1 hour)
#
# Result: High-quality mining companies with GLEIF names
# Cost: ~$4 (vs $180-400 for other approaches)
# No name drift: GLEIF names are authoritative

set -e  # Exit on error

cd "$(dirname "$0")/../.."

echo "=" | head -c 70 | tr -d '\n'; echo
echo "EXCHANGE-DRIVEN DATASET BUILD"
echo "Smart Filtering: Exchanges → GLEIF → LLM"
echo "=" | head -c 70 | tr -d '\n'; echo

# Check environment
if [ ! -f .env ]; then
    echo ""
    echo "❌ Error: .env file not found"
    echo "Please create .env with:"
    echo "  OPENAI_API_KEY=your_key_here"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

if [ -z "$OPENAI_API_KEY" ]; then
    echo ""
    echo "❌ Error: OPENAI_API_KEY not set in .env"
    exit 1
fi

echo ""
echo "✅ Environment configured"
echo ""

# Configuration
PROVIDER="openai"
CACHE_DIR=".cache/companies"
GLEIF_CACHE="$CACHE_DIR/gleif_full.parquet"
MATCHED_FILE="$CACHE_DIR/gleif_exchange_matched.parquet"
OUTPUT_DIR="entityidentity/data/companies"
CLASSIFICATION_CACHE="$CACHE_DIR/classification_cache.json"

# Show strategy
echo "=" | head -c 70 | tr -d '\n'; echo
echo "Strategy Overview"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""
echo "This approach filters 2.5M GLEIF companies down to ~2.5K"
echo "exchange-listed companies BEFORE running LLM classification."
echo ""
echo "Benefits:"
echo "  ✅ Cost: ~\$4 (vs \$180-400 for other approaches)"
echo "  ✅ Quality: ASX/LSE/TSX are major mining exchanges"
echo "  ✅ Names: GLEIF authoritative (no future drift)"
echo "  ✅ Scalable: Can add more exchanges easily"
echo ""
echo "Steps:"
echo "  1. Load exchanges (ASX, LSE, TSX) - FREE, ~2 min"
echo "  2. Download GLEIF (2.5M records) - FREE, ~30-45 min"
echo "  3. Fuzzy match exchanges → GLEIF - FREE, ~2 min"
echo "  4. LLM classify matched subset - ~\$4, ~1 hour"
echo ""

read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Step 1: Download GLEIF (if not cached)
echo ""
echo "=" | head -c 70 | tr -d '\n'; echo
echo "Step 1: Download GLEIF Database"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""

if [ -f "$GLEIF_CACHE" ]; then
    echo "✅ GLEIF cache found: $GLEIF_CACHE"
    echo "   Skipping download (delete cache to re-download)"
else
    echo "⬇️  Downloading GLEIF (2.5M records, ~30-45 min)..."
    echo ""
    python scripts/companies/download_gleif_full.py
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ GLEIF download failed!"
        exit 1
    fi
fi

# Step 2: Match exchanges to GLEIF
echo ""
echo "=" | head -c 70 | tr -d '\n'; echo
echo "Step 2: Match Exchanges → GLEIF"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""

if [ -f "$MATCHED_FILE" ]; then
    echo "✅ Matched file found: $MATCHED_FILE"
    echo ""
    read -p "Re-run matching? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping matching (using cached result)"
    else
        python scripts/companies/match_exchanges_to_gleif.py
    fi
else
    python scripts/companies/match_exchanges_to_gleif.py
fi

if [ ! -f "$MATCHED_FILE" ]; then
    echo ""
    echo "❌ Matching failed - no matched file created!"
    exit 1
fi

# Check matched count
MATCHED_COUNT=$(python -c "import pandas as pd; print(len(pd.read_parquet('$MATCHED_FILE')))")
echo ""
echo "📊 Matched companies: $MATCHED_COUNT"

# Step 3: LLM Classification
echo ""
echo "=" | head -c 70 | tr -d '\n'; echo
echo "Step 3: LLM Classification"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""

# Check cache
if [ -f "$CLASSIFICATION_CACHE" ]; then
    CACHE_SIZE=$(python -c "import json; print(len(json.load(open('$CLASSIFICATION_CACHE'))))")
    echo "💾 Classification cache: $CACHE_SIZE entries"
else
    CACHE_SIZE=0
    echo "💾 No classification cache (will be created)"
fi

# Estimate cost
ESTIMATED_NEW=$(python -c "print(max(0, $MATCHED_COUNT - $CACHE_SIZE))")
ESTIMATED_COST=$(python -c "print(f'${$ESTIMATED_NEW * 0.002:.2f}')")
ESTIMATED_TIME=$(python -c "print(f'{$ESTIMATED_NEW * 2 / 3600:.1f}')")

echo ""
echo "Estimates:"
echo "  Companies to classify: $ESTIMATED_NEW"
echo "  Estimated cost: $ESTIMATED_COST"
echo "  Estimated time: ~${ESTIMATED_TIME} hours"
echo ""

read -p "Run LLM classification? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Skipping classification."
    echo "Matched file ready at: $MATCHED_FILE"
    exit 0
fi

echo ""
echo "🤖 Running LLM classification..."
echo "   This may take ~${ESTIMATED_TIME} hours"
echo "   Progress will be shown below"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run classification with caffeinate to prevent sleep
caffeinate python -m entityidentity.companies.companyfilter \
    --input "$MATCHED_FILE" \
    --output "$OUTPUT_DIR/companies.parquet" \
    --provider "$PROVIDER" \
    --cache-file "$CLASSIFICATION_CACHE" \
    --confidence 0.7 \
    --batch-size 100

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ LLM classification failed!"
    exit 1
fi

# Generate info file
echo ""
echo "📊 Generating statistics..."
python << 'PYTHON_EOF'
import pandas as pd
from pathlib import Path

output_dir = Path("entityidentity/data/companies")
df = pd.read_parquet(output_dir / "companies.parquet")

# Generate info file
with open(output_dir / "companies_info.txt", "w") as f:
    f.write("=" * 70 + "\n")
    f.write("EntityIdentity Company Database\n")
    f.write("Built with: Exchange-Driven GLEIF Filtering\n")
    f.write("=" * 70 + "\n\n")
    
    f.write(f"Total Companies: {len(df):,}\n\n")
    
    if 'value_chain_category' in df.columns:
        f.write("By Value Chain Category:\n")
        for cat, count in df['value_chain_category'].value_counts().items():
            f.write(f"  {cat:15s}: {count:,}\n")
        f.write("\n")
    
    f.write("Top 20 Countries:\n")
    for country, count in df['country'].value_counts().head(20).items():
        f.write(f"  {country:3s}: {count:,}\n")
    f.write("\n")
    
    if 'source' in df.columns:
        f.write("By Source:\n")
        for source, count in df['source'].value_counts().items():
            f.write(f"  {source:10s}: {count:,}\n")

print("✅ Statistics generated")

# Generate CSV preview
csv_file = output_dir / "companies.csv"
df.head(5000).to_csv(csv_file, index=False)
print(f"✅ CSV preview: {csv_file} ({len(df.head(5000))} rows)")
PYTHON_EOF

# Final summary
echo ""
echo "=" | head -c 70 | tr -d '\n'; echo
echo "✨ BUILD COMPLETE!"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""
echo "📊 Dataset created:"
echo "   Location: $OUTPUT_DIR"
echo "   Files:"
echo "     • companies.parquet (main dataset)"
echo "     • companies.csv (preview)"
echo "     • companies_info.txt (statistics)"
echo ""
echo "📋 Review statistics:"
echo "   cat $OUTPUT_DIR/companies_info.txt"
echo ""
echo "🧪 Test the dataset:"
echo "   python -c 'from entityidentity import list_companies; print(len(list_companies()))'"
echo ""
echo "✅ Names are stable (GLEIF authoritative, no future drift!)"
echo ""
echo "=" | head -c 70 | tr -d '\n'; echo


#!/bin/bash
# Comprehensive dataset build: GLEIF-First, Then Exchanges
#
# This script implements the correct expansion strategy to prevent name drift:
#   1. Load comprehensive GLEIF (100K companies)
#   2. Filter with LLM (reuses cached classifications)
#   3. Add exchanges (only new companies)
#
# Estimated cost: ~$20-25
# Estimated time: ~4-6 hours
# Expected output: ~800-1200 mining/metals companies

cd "$(dirname "$0")/../.."

echo "=" | head -c 70 | tr -d '\n'; echo
echo "COMPREHENSIVE DATASET BUILD"
echo "Strategy: GLEIF-First, Then Exchanges"
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
MAX_GLEIF=100000
PROVIDER="openai"
CACHE_FILE=".cache/companies/classification_cache.json"
GLEIF_CACHE=".cache/companies/gleif_${MAX_GLEIF}.parquet"

# Check cache status
if [ -f "$CACHE_FILE" ]; then
    CACHE_SIZE=$(grep -o '"' "$CACHE_FILE" | wc -l)
    CACHE_SIZE=$((CACHE_SIZE / 2))
    echo "💾 Found classification cache: ~$CACHE_SIZE entries"
else
    echo "💾 No classification cache (will be created)"
fi

echo ""
read -p "Continue with GLEIF expansion ($MAX_GLEIF companies)? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "=" | head -c 70 | tr -d '\n'; echo
echo "Phase 1: Comprehensive GLEIF (100K companies)"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""
echo "This will:"
echo "  • Fetch 100K companies from GLEIF API (~30 min)"
echo "  • Cache locally for future use"
echo "  • Filter with LLM (reuses cached classifications)"
echo "  • Estimated cost: ~$20"
echo "  • Estimated time: ~3-4 hours"
echo ""

# Run GLEIF-first build
caffeinate bash ./scripts/companies/build_filtered_dataset.sh $MAX_GLEIF $PROVIDER

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ GLEIF build failed!"
    exit 1
fi

echo ""
echo "=" | head -c 70 | tr -d '\n'; echo
echo "Phase 2: Exchange Addition (ASX, LSE, TSX)"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""
echo "This will:"
echo "  • Load companies from major mining exchanges"
echo "  • Deduplicate against GLEIF dataset"
echo "  • Classify only NEW companies with LLM"
echo "  • Estimated cost: ~$2-5"
echo "  • Estimated time: ~1 hour"
echo ""
read -p "Continue with exchange expansion? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Skipping exchange expansion."
    echo "Dataset ready at: entityidentity/data/companies/"
    exit 0
fi

# Run exchange expansion
caffeinate python ./scripts/companies/expand_with_exchanges.py \
    --provider $PROVIDER \
    --cache-file $CACHE_FILE \
    --existing-data entityidentity/data/companies/companies.parquet \
    --output entityidentity/data/companies/companies.parquet

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Exchange expansion failed!"
    exit 1
fi

echo ""
echo "=" | head -c 70 | tr -d '\n'; echo
echo "✨ BUILD COMPLETE!"
echo "=" | head -c 70 | tr -d '\n'; echo
echo ""
echo "📊 Final dataset:"
echo "   Location: entityidentity/data/companies/"
echo "   Files:"
echo "     • companies.parquet (main dataset)"
echo "     • companies.csv (preview)"
echo "     • companies_info.txt (statistics)"
echo ""
echo "📋 Next steps:"
echo "   1. Review: cat entityidentity/data/companies/companies_info.txt"
echo "   2. Test: python -c 'from entityidentity import list_companies; print(len(list_companies()))'"
echo "   3. Commit: git add entityidentity/data/companies/"
echo ""
echo "✅ Dataset is stable - names won't drift on future expansions!"
echo ""


#!/bin/bash
# Smart expansion: Add companies from major stock exchanges
#
# This script focuses on exchange-listed companies (ASX, LSE, TSX)
# which are more likely to be large, important companies.
#
# Current status:
# - ASX: ✅ Working (1,992 companies, ~768 in Materials/Mining)
# - LSE: ⚠️  Falls back to sample data (3 companies)
# - TSX: ⚠️  Falls back to sample data (3 companies)
#
# Estimated for ASX alone:
# - New companies to classify: ~1,980 (after dedup with existing 655)
# - Expected mining/metals matches: ~300-500 companies
# - Cost: ~$4-8
# - Time: ~2-4 hours

set -e  # Exit on error

cd "$(dirname "$0")/../.."

echo "======================================================================"
echo "  Smart Expansion: Exchange-Listed Companies"
echo "======================================================================"
echo ""
echo "This will:"
echo "  1. Load companies from ASX (~2,000 companies)"
echo "  2. Load companies from LSE (sample data for now)"
echo "  3. Load companies from TSX (sample data for now)"
echo "  4. Deduplicate against existing 655 companies"
echo "  5. Run LLM classification on new companies"
echo "  6. Merge and save expanded dataset"
echo ""
echo "Expected results:"
echo "  - New companies: ~1,980"
echo "  - Mining/metals matches: ~300-500"
echo "  - Cost: ~$4-8"
echo "  - Time: ~2-4 hours"
echo ""
echo "Running in foreground with caffeinate - keep terminal open!"
echo "Press Ctrl+C to stop"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Activate conda environment and run
echo ""
echo "Starting expansion..."
caffeinate -is conda run -n entityidentity python scripts/companies/expand_with_exchanges.py \
    --provider openai \
    --existing-data entityidentity/data/companies/companies.parquet \
    --cache-file .cache/companies/classification_cache.json \
    --output entityidentity/data/companies/companies_expanded.parquet

echo ""
echo "======================================================================"
echo "  ✨ Expansion Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Review the expanded dataset:"
echo "     python -c 'import pandas as pd; df = pd.read_parquet(\"entityidentity/data/companies/companies_expanded.parquet\"); print(df.describe())'"
echo ""
echo "  2. If satisfied, replace the main dataset:"
echo "     cp entityidentity/data/companies/companies_expanded.parquet entityidentity/data/companies/companies.parquet"
echo "     cp entityidentity/data/companies/companies_expanded.csv entityidentity/data/companies/companies.csv"
echo ""
echo "  3. Regenerate info file:"
echo "     python scripts/companies/build_database_cli.py --info-only"
echo ""


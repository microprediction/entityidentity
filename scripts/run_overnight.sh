#!/bin/bash
# Run incremental build of filtered mining/energy company dataset
#
# This script fetches 15K companies and filters them with LLM
# Previous run: 10K companies (cached)
# New in this run: 5K additional companies
# Estimated time: ~3 hours (only new companies)
# Estimated cost: ~$10 (only new classifications)
# Expected output: ~1,000 mining/energy companies

cd "$(dirname "$0")/.."

echo "Starting incremental build (10K → 15K)..."
echo "This will:"
echo "  - Fetch 15K companies from GLEIF (~2 min)"
echo "  - Reuse cached classifications for first 10K"
echo "  - Filter 5K new companies with LLM (~3 hours, ~$10)"
echo "  - Create filtered dataset in entityidentity/data/companies/"
echo ""
echo "Running in foreground - keep terminal open!"
echo "Press Ctrl+C to stop"
echo ""

caffeinate ./scripts/companies/build_filtered_dataset.sh 15000 openai


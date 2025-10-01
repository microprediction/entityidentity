#!/bin/bash
# Run overnight build of filtered mining/energy company dataset
#
# This script fetches 100K companies and filters them with LLM
# Estimated time: ~28 hours
# Estimated cost: ~$20
# Expected output: ~2,000 mining/energy companies

cd "$(dirname "$0")/.."

echo "Starting overnight build..."
echo "This will:"
echo "  - Fetch 100K companies from GLEIF (~10 min)"
echo "  - Filter with LLM (~28 hours, ~$20)"
echo "  - Create filtered dataset in entityidentity/data/companies/"
echo ""
echo "Running in foreground - keep terminal open!"
echo "Press Ctrl+C to stop"
echo ""

caffeinate ./scripts/companies/build_filtered_dataset.sh 10000 openai


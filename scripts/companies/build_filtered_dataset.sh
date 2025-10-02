#!/bin/bash
# Build and filter company dataset for mining/energy companies
#
# This script orchestrates a complete pipeline:
# 1. Fetches companies from multiple sources (GLEIF, Wikidata, exchanges)
# 2. Filters for mining/energy companies using LLM classification
# 3. Creates distribution-ready files (parquet, CSV preview, info file)
#
# Usage:
#   ./build_filtered_dataset.sh [num_companies] [provider]
#
# Examples:
#   ./build_filtered_dataset.sh 100000 openai
#   ./build_filtered_dataset.sh 500000 anthropic
#
# Environment Variables:
#   OPENAI_API_KEY or ANTHROPIC_API_KEY must be set

set -e  # Exit on error

# Configuration
NUM_COMPANIES=${1:-100000}  # Default: 100K companies
LLM_PROVIDER=${2:-openai}   # Default: OpenAI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TABLES_DIR="$PROJECT_ROOT/tables/companies"
PACKAGE_DATA_DIR="$PROJECT_ROOT/entityidentity/data/companies"
CACHE_DIR="$PROJECT_ROOT/.cache/companies"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo ""
    echo "======================================================================"
    echo "  $1"
    echo "======================================================================"
    echo ""
}

# Check environment
print_header "Environment Check"

# Load .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    log_info "Loading environment from .env"
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
    log_success "Environment loaded"
else
    log_warning "No .env file found"
fi

# Check for API keys
if [ "$LLM_PROVIDER" = "openai" ]; then
    if [ -z "$OPENAI_API_KEY" ]; then
        log_error "OPENAI_API_KEY not set"
        echo "Please set it in .env or export it:"
        echo "  export OPENAI_API_KEY='your-key-here'"
        exit 1
    fi
    log_success "OpenAI API key found"
elif [ "$LLM_PROVIDER" = "anthropic" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        log_error "ANTHROPIC_API_KEY not set"
        echo "Please set it in .env or export it:"
        echo "  export ANTHROPIC_API_KEY='your-key-here'"
        exit 1
    fi
    log_success "Anthropic API key found"
else
    log_error "Unknown provider: $LLM_PROVIDER"
    echo "Use 'openai' or 'anthropic'"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    log_error "Python not found"
    exit 1
fi
log_success "Python found: $(python3 --version)"

# Create directories
mkdir -p "$TABLES_DIR"
mkdir -p "$CACHE_DIR"
mkdir -p "$PACKAGE_DATA_DIR"

# Display plan
print_header "Build Plan"
log_info "Companies to fetch: $(printf "%'d" $NUM_COMPANIES)"
log_info "LLM provider: $LLM_PROVIDER"
log_info "Output directory: $TABLES_DIR"
log_info "Package data directory: $PACKAGE_DATA_DIR"
echo ""

# Estimate costs and time
cost_per_company=0.0002
estimated_cost=$(python3 -c "print(f'\${${NUM_COMPANIES} * ${cost_per_company}:.2f}')")
estimated_time=$(python3 -c "print(f'{${NUM_COMPANIES} / 1000:.0f} minutes')")
expected_filtered=$(python3 -c "print(f'{int(${NUM_COMPANIES} * 0.02):,}')")

log_info "Estimated LLM cost: $estimated_cost"
log_info "Estimated time: $estimated_time"
log_info "Expected filtered companies: $expected_filtered (2% of total)"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Cancelled by user"
    exit 0
fi

# Step 1: Build companies database
print_header "Step 1/3: Building Companies Database"

log_info "Fetching companies from all sources..."
log_info "This will take approximately $(python3 -c "print(f'{${NUM_COMPANIES} / 200 * 1.1 / 60:.0f}')") minutes"
echo ""

# Use the build_database_cli.py script directly
cd "$PROJECT_ROOT"
python3 scripts/companies/build_database_cli.py \
    --output "$TABLES_DIR/companies_full.parquet" \
    --cache-dir "$CACHE_DIR"

if [ $? -eq 0 ]; then
    log_success "Successfully built companies database"

    # Show stats
    python3 -c "
import pandas as pd
df = pd.read_parquet('$TABLES_DIR/companies_full.parquet')
print('')
print(f'Total companies: {len(df):,}')
print(f'Countries: {df[\"country\"].nunique()}')
print(f'With LEI: {df[\"lei\"].notna().sum():,} ({df[\"lei\"].notna().sum()/len(df)*100:.1f}%)')
print('')
print('Top 10 countries:')
for country, count in df['country'].value_counts().head(10).items():
    print(f'  {country}: {count:,}')
"
else
    log_error "Failed to build companies database"
    exit 1
fi

# Step 2: Filter with LLM
print_header "Step 2/3: LLM Filtering for Mining/Energy Companies"

log_info "Running LLM classification..."
log_info "Provider: $LLM_PROVIDER"
log_info "This will take approximately $(python3 -c "print(f'{${NUM_COMPANIES} / 1000:.0f}')") minutes"
echo ""

# Use the companyfilter module directly
python3 -m entityidentity.companies.companyfilter \
    --input "$TABLES_DIR/companies_full.parquet" \
    --output "$TABLES_DIR/companies_filtered.parquet" \
    --provider "$LLM_PROVIDER" \
    --cache-file "$CACHE_DIR/classification_cache.json" \
    --batch-size 100

if [ $? -eq 0 ]; then
    log_success "LLM filtering completed"

    # Show filtered stats
    python3 -c "
import pandas as pd
original = pd.read_parquet('$TABLES_DIR/companies_full.parquet')
filtered = pd.read_parquet('$TABLES_DIR/companies_filtered.parquet')
print('')
print(f'Original: {len(original):,} companies')
print(f'Filtered: {len(filtered):,} companies ({len(filtered)/len(original)*100:.1f}%)')
print(f'File size: {(filtered.memory_usage(deep=True).sum() / 1_000_000):.1f} MB')
print('')
print('Top 10 countries in filtered dataset:')
for country, count in filtered['country'].value_counts().head(10).items():
    print(f'  {country}: {count:,}')
"
else
    log_error "LLM filtering failed"
    exit 1
fi

# Step 3: Copy to package data
print_header "Step 3/3: Preparing Distribution Files"

log_info "Copying filtered data to package..."

# Copy filtered data
cp "$TABLES_DIR/companies_filtered.parquet" "$PACKAGE_DATA_DIR/companies.parquet"
log_success "Copied companies.parquet"

# Create CSV preview (5000 random samples)
python3 -c "
import pandas as pd
df = pd.read_parquet('$PACKAGE_DATA_DIR/companies.parquet')
n_samples = min(5000, len(df))
preview = df.sample(n=n_samples, random_state=42) if len(df) > 5000 else df
preview.to_csv('$PACKAGE_DATA_DIR/companies.csv', index=False)
print(f'Created CSV preview with {len(preview):,} rows')
"
log_success "Created companies.csv"

# Create info file
python3 -c "
import pandas as pd
from datetime import datetime

df = pd.read_parquet('$PACKAGE_DATA_DIR/companies.parquet')

with open('$PACKAGE_DATA_DIR/companies_info.txt', 'w') as f:
    f.write('=' * 70 + '\n')
    f.write('Company Database Information\n')
    f.write('=' * 70 + '\n\n')
    f.write(f'Generated: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\n')
    f.write(f'Filter: Mining and Energy Companies (LLM-filtered)\n\n')
    f.write(f'Total Companies: {len(df):,}\n\n')

    f.write('Breakdown by Country (Top 10):\n')
    for country, count in df['country'].value_counts().head(10).items():
        pct = count / len(df) * 100
        f.write(f'  - {country:5s}: {count:6,} companies ({pct:5.1f}%)\n')
    f.write('\n')

    f.write('Data Coverage:\n')
    lei_count = df['lei'].notna().sum()
    f.write(f'  - With LEI: {lei_count:,} ({lei_count/len(df)*100:.1f}%)\n')
    if 'alias1' in df.columns:
        alias_count = df['alias1'].notna().sum()
        f.write(f'  - With Aliases: {alias_count:,} ({alias_count/len(df)*100:.1f}%)\n')
    f.write('\n')

    f.write('=' * 70 + '\n')
"
log_success "Created companies_info.txt"

# Check file sizes
print_header "File Size Check"

parquet_size=$(du -h "$PACKAGE_DATA_DIR/companies.parquet" | cut -f1)
csv_size=$(du -h "$PACKAGE_DATA_DIR/companies.csv" | cut -f1)
total_size=$(du -sh "$PACKAGE_DATA_DIR" | cut -f1)

log_info "companies.parquet: $parquet_size"
log_info "companies.csv: $csv_size"
log_info "Total package data: $total_size"
echo ""

# Check if under limits
parquet_mb=$(du -m "$PACKAGE_DATA_DIR/companies.parquet" | cut -f1)
if [ "$parquet_mb" -gt 20 ]; then
    log_error "Parquet file is ${parquet_mb}MB (> 20MB GitHub warning threshold)"
    echo "Consider filtering more aggressively or using Git LFS"
    exit 1
elif [ "$parquet_mb" -gt 10 ]; then
    log_warning "Parquet file is ${parquet_mb}MB (close to 20MB limit)"
else
    log_success "Parquet file size OK (${parquet_mb}MB < 20MB)"
fi

# Final summary
print_header "Build Complete!"

log_success "Filtered dataset ready for distribution"
log_info "Location: $PACKAGE_DATA_DIR"
log_info "Next steps:"
echo "  1. Test the package: python3 -c 'from entityidentity import list_companies; print(len(list_companies()))'"
echo "  2. Review the data: cat $PACKAGE_DATA_DIR/companies_info.txt"
echo "  3. Commit to git: git add $PACKAGE_DATA_DIR/*.parquet"
echo "  4. Build package: python3 -m build"
echo "  5. Publish to PyPI: python3 -m twine upload dist/*"
echo ""

log_success "Done! 🎉"
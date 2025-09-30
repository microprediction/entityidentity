#!/bin/bash
# Check if data files exceed GitHub/PyPI limits

MAX_FILE_SIZE_MB=20
MAX_TOTAL_SIZE_MB=50

echo "=== Checking Data File Sizes ==="
echo ""

# Check individual files
for file in entityidentity/data/companies/*.parquet; do
    if [ -f "$file" ]; then
        size_mb=$(du -m "$file" | cut -f1)
        echo "File: $(basename $file) - ${size_mb}MB"
        
        if [ "$size_mb" -gt "$MAX_FILE_SIZE_MB" ]; then
            echo "  ⚠️  WARNING: File exceeds ${MAX_FILE_SIZE_MB}MB (GitHub will warn)"
            echo "  → Consider splitting into multiple files or excluding from package"
        else
            echo "  ✅ OK (< ${MAX_FILE_SIZE_MB}MB)"
        fi
    fi
done

# Check total size
if [ -d "entityidentity/data/companies" ]; then
    total_mb=$(du -sm entityidentity/data/companies | cut -f1)
    echo ""
    echo "Total package data: ${total_mb}MB"
    
    if [ "$total_mb" -gt "$MAX_TOTAL_SIZE_MB" ]; then
        echo "  ⚠️  WARNING: Total data exceeds ${MAX_TOTAL_SIZE_MB}MB"
        echo "  → PyPI may have issues with large packages"
    else
        echo "  ✅ OK (< ${MAX_TOTAL_SIZE_MB}MB)"
    fi
fi

echo ""
echo "Recommendations:"
echo "- Individual files should be < ${MAX_FILE_SIZE_MB}MB"
echo "- Total package data should be < ${MAX_TOTAL_SIZE_MB}MB"
echo "- Use LLM filtering to keep dataset focused on mining/energy companies"

# Company Data

**This package includes pre-filtered mining and energy companies** - ready to use immediately after `pip install entityidentity`.

## What's Included

~50,000 companies filtered by LLM:
- **Supply**: Mining, metals extraction, recycling, refining  
- **Demand**: Major metal users (automotive, manufacturing, construction)

**Size**: ~6MB (fits comfortably in PyPI/GitHub limits)

## Usage

```python
from entityidentity import list_companies, resolve_company

# Works immediately - no setup needed!
companies = list_companies(country='US')
result = resolve_company('BHP', country='AU')
```

## For Developers

To rebuild/update the filtered dataset, see the scripts in `/scripts/companies/`:
1. `update_companies_db.py` - Fetch from GLEIF/exchanges
2. Filter with LLM for mining/energy companies  
3. Copy result to this directory

The filtered data is checked into git and distributed with the package.

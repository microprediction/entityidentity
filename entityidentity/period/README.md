## Period Module

Temporal entity resolution for converting any date-ish text to canonical Period objects with start/end timestamps.

## Overview

The period module resolves textual period references into structured Period objects with precise timestamp boundaries. It supports years, halves, quarters, months, ISO weeks, date ranges, and relative periods.

## Key Features

- **Multiple Period Types**: years, halves, quarters, months, ISO weeks, date ranges
- **ISO 8601 Compliance**: Weeks start on Monday following ISO standard
- **Relative Periods**: "last quarter" resolves using asof_ts parameter
- **Date Ranges**: "Q1-Q2 2026" preserved as single date_range
- **H1/H2 as Singles**: Halves remain as single periods (downstream can expand)

## Quick Start

```python
from entityidentity.period import period_identifier, extract_periods

# Resolve single period
period = period_identifier("H2 2026")
# Returns: {'period_type': 'half', 'period_id': '2026H2',
#           'start_ts': datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC),
#           'end_ts': datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC), ...}

# Resolve date range
period = period_identifier("Q1-Q2 2026")
# Returns: {'period_type': 'date_range', 'period_id': '2026Q1-2026Q2', ...}

# Resolve ISO week (Monday start)
period = period_identifier("2025-W02")
# Returns: {'period_type': 'week', 'period_id': '2025-W02',
#           'start_ts': datetime(2025, 1, 6, 0, 0, 0, tzinfo=UTC), ...}

# Relative period
from datetime import datetime, timezone
asof = datetime(2025, 10, 2, tzinfo=timezone.utc)
period = period_identifier("last quarter", asof_ts=asof)
# Returns: {'period_type': 'quarter', 'period_id': '2025Q3', ...}

# Extract multiple periods from text
text = "Revenue grew in Q1 2026 and H2 2025."
periods = extract_periods(text)
# Returns: [{'period_type': 'quarter', 'period_id': '2026Q1', ...},
#           {'period_type': 'half', 'period_id': '2025H2', ...}]
```

## Supported Period Types

### 1. Year
- **Formats**: "2025", "FY2026"
- **Example**:
  ```python
  period_identifier("2025")
  # {'period_type': 'year', 'period_id': '2025',
  #  'start_ts': '2025-01-01T00:00:00Z', 'end_ts': '2025-12-31T23:59:59Z'}
  ```

### 2. Half Year (H1/H2)
- **Formats**: "H1 2026", "2025H2", "H2-2025"
- **Remains as single period** (not auto-expanded to quarters)
- **Example**:
  ```python
  period_identifier("H2 2026")
  # {'period_type': 'half', 'period_id': '2026H2',
  #  'start_ts': '2026-07-01T00:00:00Z', 'end_ts': '2026-12-31T23:59:59Z'}
  ```

### 3. Quarter
- **Formats**: "Q1 2026", "2025Q3", "Q4-2025"
- **Example**:
  ```python
  period_identifier("Q1 2026")
  # {'period_type': 'quarter', 'period_id': '2026Q1',
  #  'start_ts': '2026-01-01T00:00:00Z', 'end_ts': '2026-03-31T23:59:59Z',
  #  'quarter': 1}
  ```

### 4. Month
- **Formats**: "Jan 2026", "January 2026", "2025-01"
- **Example**:
  ```python
  period_identifier("Jan 2026")
  # {'period_type': 'month', 'period_id': '2026-01',
  #  'start_ts': '2026-01-01T00:00:00Z', 'end_ts': '2026-01-31T23:59:59Z',
  #  'month': 1, 'quarter': 1}
  ```

### 5. ISO Week
- **Formats**: "2025-W02", "2025W02", "W02 2025"
- **Starts Monday** (ISO 8601 standard, uses isoweek library)
- **Example**:
  ```python
  period_identifier("2025-W02")
  # {'period_type': 'week', 'period_id': '2025-W02',
  #  'start_ts': '2025-01-06T00:00:00Z',  # Monday
  #  'end_ts': '2025-01-12T23:59:59Z'}     # Sunday
  ```

### 6. Date Range
- **Formats**: "Q1-Q2 2026", "Jan-Mar 2025", "H1 to H2 2026"
- **Preserves endpoints** as single date_range
- **Example**:
  ```python
  period_identifier("Q1-Q2 2026")
  # {'period_type': 'date_range', 'period_id': '2026Q1-2026Q2',
  #  'start_ts': '2026-01-01T00:00:00Z', 'end_ts': '2026-06-30T23:59:59Z'}
  ```

### 7. Relative Periods
- **Formats**: "last quarter", "this year", "next month"
- **Requires asof_ts** parameter for calculation
- **Example**:
  ```python
  asof = datetime(2025, 10, 2, tzinfo=timezone.utc)
  period_identifier("last quarter", asof_ts=asof)
  # {'period_type': 'quarter', 'period_id': '2025Q3',
  #  'start_ts': '2025-07-01T00:00:00Z', 'end_ts': '2025-09-30T23:59:59Z'}
  ```

## API Reference

### `period_identifier(text, *, asof_ts=None)`

Resolve period text to canonical Period dict.

**Args:**
- `text` (str): Period text to resolve
- `asof_ts` (datetime, optional): Reference timestamp for relative periods (default: now UTC)

**Returns:**
- `dict | None`: Period dict or None if not resolvable

**Period Dict Structure:**
```python
{
    "period_type": str,      # "week|month|quarter|half|year|date_range"
    "period_id": str,        # "2026Q1", "2025-W02", "2026H2", etc.
    "start_ts": datetime,    # Start of period (00:00:00 UTC)
    "end_ts": datetime,      # End of period (23:59:59 UTC)
    "year": int,             # Year
    "quarter": int | None,   # Quarter (1-4) if applicable
    "month": int | None,     # Month (1-12) if applicable
    "asof_ts": datetime,     # When query was resolved
    "timezone": str,         # "UTC"
    "score": int             # Match confidence (0-100)
}
```

### `extract_periods(text, *, asof_ts=None)`

Extract multiple periods from text.

**Args:**
- `text` (str): Text to scan for periods
- `asof_ts` (datetime, optional): Reference timestamp for relative periods

**Returns:**
- `list[dict]`: List of Period dicts (empty if no periods found)

**Example:**
```python
text = "Results for Q1 2026 and H2 2025 were strong."
periods = extract_periods(text)
# [{'period_type': 'quarter', 'period_id': '2026Q1', ...},
#  {'period_type': 'half', 'period_id': '2025H2', ...}]
```

### `format_period_display(period)`

Format period for human-readable display.

**Args:**
- `period` (dict): Period dict from `period_identifier()`

**Returns:**
- `str`: Display string

**Examples:**
```python
period = period_identifier("Q1 2026")
format_period_display(period)
# 'Q1 2026 (Jan 1 - Mar 31, 2026)'

period = period_identifier("2025-W02")
format_period_display(period)
# 'W02 2025 (Jan 6 - Jan 12, 2025)'
```

## Design Principles

### 1. H1/H2 as Single Periods
Halves remain as single "half" periods and are **not** automatically expanded to quarters. Downstream systems can expand if needed:

```python
period = period_identifier("H2 2026")
# Returns: {'period_type': 'half', ...}
# NOT: [Q3, Q4] expansion

# Downstream can expand:
if period['period_type'] == 'half':
    if period['period_id'].endswith('H1'):
        quarters = ['Q1', 'Q2']
    else:
        quarters = ['Q3', 'Q4']
```

### 2. ISO 8601 Week Standard
ISO weeks always start on Monday following ISO 8601 standard. Uses the `isoweek` library for accurate week calculation:

```python
period_identifier("2025-W02")
# start_ts: Monday, Jan 6, 2025 (00:00:00 UTC)
# end_ts: Sunday, Jan 12, 2025 (23:59:59 UTC)
```

### 3. Relative Period Resolution
Relative periods like "last quarter" require `asof_ts` parameter:

```python
# Current date: Oct 2, 2025
asof = datetime(2025, 10, 2, tzinfo=timezone.utc)

period_identifier("last quarter", asof_ts=asof)
# Resolves to Q3 2025 (Jul-Sep)

period_identifier("this year", asof_ts=asof)
# Resolves to 2025

period_identifier("next month", asof_ts=asof)
# Resolves to Nov 2025
```

### 4. Date Range Preservation
Ranges like "Q1-Q2 2026" are preserved as single `date_range` type with proper start/end:

```python
period_identifier("Q1-Q2 2026")
# {'period_type': 'date_range',
#  'period_id': '2026Q1-2026Q2',
#  'start_ts': '2026-01-01T00:00:00Z',  # Start of Q1
#  'end_ts': '2026-06-30T23:59:59Z'}    # End of Q2
```

## Implementation Details

### Pure Computation (No Data Table)
The period module is implemented as pure computation using:
- Regular expressions for pattern matching
- `python-dateutil` for date parsing
- `isoweek` for ISO week calculations

No data table or database is required.

### Resolution Algorithm

1. **Normalize text**: lowercase, normalize dashes, collapse whitespace
2. **Check relative**: if "last/this/next" → use asof_ts for calculation
3. **Check range**: if contains "-" or "to" → resolve as date_range
4. **Check ISO week**: if "2025-W02" format → resolve week
5. **Check quarter/half/month**: extract period type + year → resolve
6. **Check year only**: if just "2025" → resolve year
7. **Return None**: if no pattern matches

### Timestamp Boundaries
All timestamps are in UTC with precise boundaries:
- **Start**: 00:00:00.000000 UTC
- **End**: 23:59:59.999999 UTC

## Dependencies

```bash
pip install python-dateutil isoweek
```

## Testing

Run period tests:
```bash
pytest tests/period/ -v

# Specific test file
pytest tests/period/test_periodapi.py -v
```

## Common Use Cases

### Financial Reporting
```python
# Extract reporting periods
text = "Q1 2026 revenue increased 15% vs Q4 2025"
periods = extract_periods(text)
# [Q1 2026, Q4 2025]
```

### Time Series Analysis
```python
# Resolve period boundaries for data queries
period = period_identifier("H2 2025")
query_data_between(period['start_ts'], period['end_ts'])
```

### Relative Period Calculations
```python
# Calculate "last quarter" dynamically
asof = datetime.now(timezone.utc)
last_q = period_identifier("last quarter", asof_ts=asof)
# Automatically resolves to previous quarter
```

## Limitations

1. **Fiscal Year Variants**: Currently assumes calendar year. Custom fiscal years (e.g., "FY ends June 30") not yet supported.
2. **Timezone Variants**: All periods are in UTC. Local timezone conversion not included.
3. **Language**: English only. Month names in other languages not supported.
4. **Ambiguous Ranges**: "Jan-2025" could be "Jan only" or "entire 2025" - resolved as month.

## Future Enhancements

- Custom fiscal year definitions per market
- Multi-language support for month names
- Timezone-aware period resolution
- Period arithmetic (add/subtract periods)

"""Period Entity Resolution
--------------------------

Core resolver for converting date-ish text to canonical Period objects.

Supports:
  - Years: "2025", "FY2026"
  - Halves: "H1 2026", "2025H2"
  - Quarters: "Q1 2026", "2025Q3"
  - Months: "Jan 2026", "2025-01"
  - Weeks: "2025-W02" (ISO week, Monday start)
  - Date ranges: "Q1-Q2 2026", "Jan-Mar 2025"
  - Relative: "last quarter" (requires asof_ts)

Key Design Principles:
  1. H1/H2 remain as single "half" periods (don't auto-expand to quarters)
  2. ISO weeks start on Monday (isoweek library)
  3. Relative periods use asof_ts parameter
  4. Ranges preserve endpoints as date_range type
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import re

try:
    from dateutil import parser as dateutil_parser
    from dateutil.relativedelta import relativedelta
except ImportError as e:
    raise ImportError("python-dateutil not installed. pip install python-dateutil") from e

try:
    from isoweek import Week
except ImportError as e:
    raise ImportError("isoweek not installed. pip install isoweek") from e

from entityidentity.period.periodnormalize import (
    normalize_period_text,
    extract_year,
    extract_quarter_half_month,
    extract_month_name,
    extract_iso_week,
    detect_range_separator,
    is_relative_period,
)


# ---- Helper: Create timestamp at start/end of day ----

def _start_of_day(dt: datetime) -> datetime:
    """Return datetime at start of day (00:00:00) in UTC."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def _end_of_day(dt: datetime) -> datetime:
    """Return datetime at end of day (23:59:59) in UTC."""
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)


# ---- Year Resolution ----

def _resolve_year(year: int) -> dict:
    """
    Resolve year to period dict.

    Args:
        year: 4-digit year

    Returns:
        Period dict with year boundaries

    Example:
        >>> _resolve_year(2025)
        {'period_type': 'year', 'period_id': '2025',
         'start_ts': datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
         'year': 2025, 'quarter': None, 'month': None}
    """
    start_ts = _start_of_day(datetime(year, 1, 1))
    end_ts = _end_of_day(datetime(year, 12, 31))

    return {
        "period_type": "year",
        "period_id": str(year),
        "start_ts": start_ts,
        "end_ts": end_ts,
        "year": year,
        "quarter": None,
        "month": None,
    }


# ---- Half Resolution ----

def _resolve_half(year: int, half: int) -> dict:
    """
    Resolve half-year (H1 or H2) to period dict.

    H1 = Jan-Jun (Q1+Q2)
    H2 = Jul-Dec (Q3+Q4)

    NOTE: Returns single "half" period, not expanded to quarters.
    Downstream systems can expand if needed.

    Args:
        year: 4-digit year
        half: 1 or 2

    Returns:
        Period dict with half boundaries

    Example:
        >>> _resolve_half(2026, 2)
        {'period_type': 'half', 'period_id': '2026H2',
         'start_ts': datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC),
         'year': 2026, 'quarter': None, 'month': None}
    """
    if half == 1:
        start_month, end_month, end_day = 1, 6, 30
    else:  # half == 2
        start_month, end_month, end_day = 7, 12, 31

    start_ts = _start_of_day(datetime(year, start_month, 1))
    end_ts = _end_of_day(datetime(year, end_month, end_day))

    return {
        "period_type": "half",
        "period_id": f"{year}H{half}",
        "start_ts": start_ts,
        "end_ts": end_ts,
        "year": year,
        "quarter": None,  # Half doesn't map to single quarter
        "month": None,
    }


# ---- Quarter Resolution ----

def _resolve_quarter(year: int, quarter: int) -> dict:
    """
    Resolve quarter to period dict.

    Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec

    Args:
        year: 4-digit year
        quarter: 1, 2, 3, or 4

    Returns:
        Period dict with quarter boundaries

    Example:
        >>> _resolve_quarter(2026, 1)
        {'period_type': 'quarter', 'period_id': '2026Q1',
         'start_ts': datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2026, 3, 31, 23, 59, 59, tzinfo=UTC),
         'year': 2026, 'quarter': 1, 'month': None}
    """
    # Quarter start months and end days
    quarter_map = {
        1: (1, 3, 31),   # Jan-Mar
        2: (4, 6, 30),   # Apr-Jun
        3: (7, 9, 30),   # Jul-Sep
        4: (10, 12, 31), # Oct-Dec
    }

    start_month, end_month, end_day = quarter_map[quarter]
    start_ts = _start_of_day(datetime(year, start_month, 1))
    end_ts = _end_of_day(datetime(year, end_month, end_day))

    return {
        "period_type": "quarter",
        "period_id": f"{year}Q{quarter}",
        "start_ts": start_ts,
        "end_ts": end_ts,
        "year": year,
        "quarter": quarter,
        "month": None,
    }


# ---- Month Resolution ----

def _resolve_month(year: int, month: int) -> dict:
    """
    Resolve month to period dict.

    Args:
        year: 4-digit year
        month: 1-12

    Returns:
        Period dict with month boundaries

    Example:
        >>> _resolve_month(2026, 1)
        {'period_type': 'month', 'period_id': '2026-01',
         'start_ts': datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC),
         'year': 2026, 'quarter': 1, 'month': 1}
    """
    # Calculate last day of month using next month - 1 day
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    last_day = (next_month - relativedelta(days=1)).day

    start_ts = _start_of_day(datetime(year, month, 1))
    end_ts = _end_of_day(datetime(year, month, last_day))

    # Determine quarter (1-12 → 1-4)
    quarter = ((month - 1) // 3) + 1

    return {
        "period_type": "month",
        "period_id": f"{year}-{month:02d}",
        "start_ts": start_ts,
        "end_ts": end_ts,
        "year": year,
        "quarter": quarter,
        "month": month,
    }


# ---- ISO Week Resolution ----

def _resolve_week(year: int, week: int) -> dict:
    """
    Resolve ISO week to period dict.

    ISO weeks start on Monday and are numbered 1-53.
    Uses isoweek library for accurate ISO 8601 week calculation.

    Args:
        year: 4-digit year
        week: 1-53 (ISO week number)

    Returns:
        Period dict with week boundaries (Monday-Sunday)

    Example:
        >>> _resolve_week(2025, 2)
        {'period_type': 'week', 'period_id': '2025-W02',
         'start_ts': datetime(2025, 1, 6, 0, 0, 0, tzinfo=UTC),  # Monday
         'end_ts': datetime(2025, 1, 12, 23, 59, 59, tzinfo=UTC),  # Sunday
         'year': 2025, 'quarter': 1, 'month': 1}
    """
    # Get ISO week using isoweek library
    iso_week = Week(year, week)

    # Monday = start, Sunday = end
    monday = iso_week.monday()
    sunday = iso_week.sunday()

    start_ts = _start_of_day(datetime(monday.year, monday.month, monday.day))
    end_ts = _end_of_day(datetime(sunday.year, sunday.month, sunday.day))

    # Determine quarter and month from start date
    quarter = ((monday.month - 1) // 3) + 1

    return {
        "period_type": "week",
        "period_id": f"{year}-W{week:02d}",
        "start_ts": start_ts,
        "end_ts": end_ts,
        "year": year,
        "quarter": quarter,
        "month": monday.month,
    }


# ---- Relative Period Resolution ----

def _resolve_relative(text_norm: str, asof_ts: datetime) -> dict | None:
    """
    Resolve relative period expressions.

    Supported:
      - "last quarter", "previous quarter"
      - "this quarter", "current quarter"
      - "next quarter"
      - "last year", "this year", "next year"
      - "last month", "this month", "next month"

    Args:
        text_norm: Normalized text (e.g., "last quarter")
        asof_ts: Reference timestamp for relative calculation

    Returns:
        Period dict or None if not resolvable

    Example:
        >>> asof = datetime(2025, 10, 2, tzinfo=timezone.utc)
        >>> _resolve_relative("last quarter", asof)
        {'period_type': 'quarter', 'period_id': '2025Q3', ...}
    """
    # Extract period type (quarter, year, month)
    if "quarter" in text_norm:
        period_type = "quarter"
    elif "year" in text_norm:
        period_type = "year"
    elif "month" in text_norm:
        period_type = "month"
    else:
        return None

    # Extract relative offset (last=-1, this=0, next=1)
    if any(kw in text_norm for kw in ["last", "previous", "prior"]):
        offset = -1
    elif any(kw in text_norm for kw in ["this", "current"]):
        offset = 0
    elif "next" in text_norm:
        offset = 1
    else:
        return None

    # Calculate target period
    if period_type == "quarter":
        # Determine current quarter
        current_q = ((asof_ts.month - 1) // 3) + 1
        target_q = current_q + offset

        # Handle year wrapping
        target_year = asof_ts.year
        if target_q < 1:
            target_q += 4
            target_year -= 1
        elif target_q > 4:
            target_q -= 4
            target_year += 1

        return _resolve_quarter(target_year, target_q)

    elif period_type == "year":
        target_year = asof_ts.year + offset
        return _resolve_year(target_year)

    elif period_type == "month":
        target_month = asof_ts.month + offset
        target_year = asof_ts.year

        # Handle month wrapping
        if target_month < 1:
            target_month += 12
            target_year -= 1
        elif target_month > 12:
            target_month -= 12
            target_year += 1

        return _resolve_month(target_year, target_month)

    return None


# ---- Date Range Resolution ----

def _resolve_range(text_norm: str) -> dict | None:
    """
    Resolve date range expressions.

    Supported:
      - "Q1-Q2 2026" (quarter to quarter)
      - "Jan-Mar 2025" (month to month)
      - "H1 to H2 2026" (half to half)

    Returns period_type="date_range" with start/end from endpoints.

    Args:
        text_norm: Normalized text (e.g., "q1-q2 2026")

    Returns:
        Period dict with date_range type or None

    Example:
        >>> _resolve_range("q1-q2 2026")
        {'period_type': 'date_range', 'period_id': '2026Q1-2026Q2',
         'start_ts': datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC), ...}
    """
    # Extract year
    year = extract_year(text_norm)
    if not year:
        return None

    # Try quarter-quarter range: Q1-Q2
    q_range = re.search(r"q([1-4])(?:-|to)q([1-4])", text_norm)
    if q_range:
        q1, q2 = int(q_range.group(1)), int(q_range.group(2))
        start_period = _resolve_quarter(year, q1)
        end_period = _resolve_quarter(year, q2)

        return {
            "period_type": "date_range",
            "period_id": f"{start_period['period_id']}-{end_period['period_id']}",
            "start_ts": start_period["start_ts"],
            "end_ts": end_period["end_ts"],
            "year": year,
            "quarter": None,  # Range spans multiple quarters
            "month": None,
        }

    # Try half-half range: H1 to H2
    h_range = re.search(r"h([12])(?:-|to)h([12])", text_norm)
    if h_range:
        h1, h2 = int(h_range.group(1)), int(h_range.group(2))
        start_period = _resolve_half(year, h1)
        end_period = _resolve_half(year, h2)

        return {
            "period_type": "date_range",
            "period_id": f"{start_period['period_id']}-{end_period['period_id']}",
            "start_ts": start_period["start_ts"],
            "end_ts": end_period["end_ts"],
            "year": year,
            "quarter": None,
            "month": None,
        }

    # Try month-month range by name: Jan-Mar
    # Extract month names from text
    month_names = []
    for match in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", text_norm):
        month_names.append(extract_month_name(match.group(1)))

    if len(month_names) >= 2:
        m1, m2 = month_names[0], month_names[-1]  # First and last month
        if m1 and m2:
            start_period = _resolve_month(year, m1)
            end_period = _resolve_month(year, m2)

            return {
                "period_type": "date_range",
                "period_id": f"{start_period['period_id']}-{end_period['period_id']}",
                "start_ts": start_period["start_ts"],
                "end_ts": end_period["end_ts"],
                "year": year,
                "quarter": None,
                "month": None,
            }

    return None


# ---- Main Resolution Function ----

def resolve_period(
    text: str,
    *,
    asof_ts: Optional[datetime] = None,
    score: int = 95,
) -> Optional[dict]:
    """
    Resolve period text to canonical Period dict.

    Resolution Strategy:
      1. Normalize text (lowercase, normalize dashes, etc.)
      2. Check for relative period (requires asof_ts)
      3. Check for date range (Q1-Q2, Jan-Mar, etc.)
      4. Check for ISO week (2025-W02)
      5. Check for quarter/half/month + year
      6. Check for year only
      7. Return None if no pattern matches

    Args:
        text: Period text to resolve
        asof_ts: Reference timestamp for relative periods (default: now)
        score: Match confidence score (default: 95)

    Returns:
        Period dict with structure:
        {
            "period_type": "week|month|quarter|half|year|date_range",
            "period_id": str,  # "2026Q1", "2025-W02", "2026H2", etc.
            "start_ts": datetime,
            "end_ts": datetime,
            "year": int,
            "quarter": int | None,
            "month": int | None,
            "asof_ts": datetime,
            "timezone": "UTC",
            "score": int
        }

    Examples:
        >>> resolve_period("H2 2026")
        {'period_type': 'half', 'period_id': '2026H2', ...}

        >>> resolve_period("Q1-Q2 2026")
        {'period_type': 'date_range', 'period_id': '2026Q1-2026Q2', ...}

        >>> resolve_period("2025-W02")
        {'period_type': 'week', 'period_id': '2025-W02', ...}
    """
    if not text or not text.strip():
        return None

    # Normalize text
    text_norm = normalize_period_text(text)

    # Set asof_ts to now if not provided
    if asof_ts is None:
        asof_ts = datetime.now(timezone.utc)
    elif asof_ts.tzinfo is None:
        # Assume UTC if no timezone
        asof_ts = asof_ts.replace(tzinfo=timezone.utc)

    # 1. Try relative period (requires asof_ts)
    if is_relative_period(text_norm):
        result = _resolve_relative(text_norm, asof_ts)
        if result:
            result.update({
                "asof_ts": asof_ts,
                "timezone": "UTC",
                "score": score,
            })
            return result

    # 2. Try date range
    if detect_range_separator(text_norm):
        result = _resolve_range(text_norm)
        if result:
            result.update({
                "asof_ts": asof_ts,
                "timezone": "UTC",
                "score": score,
            })
            return result

    # 3. Try ISO week
    iso_year, iso_week = extract_iso_week(text_norm)
    if iso_year and iso_week:
        result = _resolve_week(iso_year, iso_week)
        result.update({
            "asof_ts": asof_ts,
            "timezone": "UTC",
            "score": score,
        })
        return result

    # 4. Try quarter/half/month with year
    year = extract_year(text_norm)
    if year:
        # Check for half
        period_type, period_num = extract_quarter_half_month(text_norm)

        if period_type == "half" and period_num:
            result = _resolve_half(year, period_num)
            result.update({
                "asof_ts": asof_ts,
                "timezone": "UTC",
                "score": score,
            })
            return result

        # Check for quarter
        if period_type == "quarter" and period_num:
            result = _resolve_quarter(year, period_num)
            result.update({
                "asof_ts": asof_ts,
                "timezone": "UTC",
                "score": score,
            })
            return result

        # Check for month by number
        if period_type == "month" and period_num:
            result = _resolve_month(year, period_num)
            result.update({
                "asof_ts": asof_ts,
                "timezone": "UTC",
                "score": score,
            })
            return result

        # Check for month by name
        month_num = extract_month_name(text_norm)
        if month_num:
            result = _resolve_month(year, month_num)
            result.update({
                "asof_ts": asof_ts,
                "timezone": "UTC",
                "score": score,
            })
            return result

        # Year only
        result = _resolve_year(year)
        result.update({
            "asof_ts": asof_ts,
            "timezone": "UTC",
            "score": score,
        })
        return result

    # No pattern matched
    return None


__all__ = [
    "resolve_period",
]

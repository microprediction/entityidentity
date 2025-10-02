"""Period entity resolution API.

Public API for period identification and temporal normalization.
Resolves any date-ish text to canonical Period with start/end timestamps.
"""

from datetime import datetime, timezone
from typing import Optional
import re

from entityidentity.period.periodidentity import resolve_period
from entityidentity.period.periodnormalize import normalize_period_text


def period_identifier(
    text: str,
    *,
    asof_ts: Optional[datetime] = None,
) -> Optional[dict]:
    """
    Resolve period text to canonical Period dict.

    Supports:
      - Years: "2025", "FY2026"
      - Halves: "H1 2026", "2025H2" (remains as single half period)
      - Quarters: "Q1 2026", "2025Q3"
      - Months: "Jan 2026", "2025-01"
      - ISO weeks: "2025-W02" (Monday start per ISO 8601)
      - Date ranges: "Q1-Q2 2026", "Jan-Mar 2025"
      - Relative: "last quarter" (uses asof_ts)

    Key Behaviors:
      1. H1/H2 remain as single "half" periods (downstream can expand to quarters)
      2. ISO weeks start on Monday following ISO 8601 standard
      3. Relative periods like "last quarter" use asof_ts parameter
      4. Date ranges preserve endpoints with period_type="date_range"

    Args:
        text: Period text to resolve
        asof_ts: Reference timestamp for relative periods (default: now UTC)

    Returns:
        Period dict with structure:
        {
            "period_type": "week|month|quarter|half|year|date_range",
            "period_id": str,  # "2026Q1", "2025-W02", "2026H2", etc.
            "start_ts": datetime,  # Start of period (00:00:00 UTC)
            "end_ts": datetime,    # End of period (23:59:59 UTC)
            "year": int,
            "quarter": int | None,  # Only if applicable
            "month": int | None,    # Only if applicable
            "asof_ts": datetime,    # When query was resolved
            "timezone": "UTC",
            "score": int           # Match confidence (0-100)
        }

        Returns None if text cannot be parsed as a period.

    Examples:
        >>> period_identifier("H2 2026")
        {'period_type': 'half', 'period_id': '2026H2',
         'start_ts': datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC),
         'year': 2026, 'quarter': None, 'month': None,
         'asof_ts': datetime(...), 'timezone': 'UTC', 'score': 95}

        >>> period_identifier("Q1-Q2 2026")
        {'period_type': 'date_range', 'period_id': '2026Q1-2026Q2',
         'start_ts': datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC),
         'year': 2026, 'quarter': None, 'month': None, ...}

        >>> period_identifier("2025-W02")
        {'period_type': 'week', 'period_id': '2025-W02',
         'start_ts': datetime(2025, 1, 6, 0, 0, 0, tzinfo=UTC),  # Monday
         'end_ts': datetime(2025, 1, 12, 23, 59, 59, tzinfo=UTC),  # Sunday
         'year': 2025, 'quarter': 1, 'month': 1, ...}

        >>> # Relative period with asof_ts
        >>> asof = datetime(2025, 10, 2, tzinfo=timezone.utc)
        >>> period_identifier("last quarter", asof_ts=asof)
        {'period_type': 'quarter', 'period_id': '2025Q3',
         'start_ts': datetime(2025, 7, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2025, 9, 30, 23, 59, 59, tzinfo=UTC),
         'year': 2025, 'quarter': 3, 'month': None, ...}

        >>> period_identifier("Jan 2026")
        {'period_type': 'month', 'period_id': '2026-01',
         'start_ts': datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
         'end_ts': datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC),
         'year': 2026, 'quarter': 1, 'month': 1, ...}
    """
    if not text or not text.strip():
        return None

    # Use core resolver
    return resolve_period(text, asof_ts=asof_ts)


def extract_periods(
    text: str,
    *,
    asof_ts: Optional[datetime] = None,
) -> list[dict]:
    """
    Extract multiple periods from text.

    Scans text for period patterns and resolves each one.
    Useful for extracting periods from longer documents or reports.

    Args:
        text: Text to scan for periods
        asof_ts: Reference timestamp for relative periods (default: now UTC)

    Returns:
        List of Period dicts (empty list if no periods found)

    Examples:
        >>> text = "Results for Q1 2026 and H2 2025 were strong."
        >>> extract_periods(text)
        [{'period_type': 'quarter', 'period_id': '2026Q1', ...},
         {'period_type': 'half', 'period_id': '2025H2', ...}]

        >>> text = "Revenue grew from Jan 2025 to Mar 2025."
        >>> extract_periods(text)
        [{'period_type': 'month', 'period_id': '2025-01', ...},
         {'period_type': 'month', 'period_id': '2025-03', ...}]
    """
    if not text or not text.strip():
        return []

    periods = []
    text_norm = normalize_period_text(text)

    # Period patterns to search for (in priority order)
    patterns = [
        # ISO week: 2025-W02
        (r"\b\d{4}-?w\d{1,2}\b", "iso_week"),
        # Quarter with year: Q1 2026, 2026Q1
        (r"\b(q[1-4]\s+\d{4}|\d{4}\s*q[1-4])\b", "quarter"),
        # Half with year: H1 2026, 2026H2
        (r"\b(h[12]\s+\d{4}|\d{4}\s*h[12])\b", "half"),
        # Month name with year: Jan 2026, January 2025
        (r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\b", "month_name"),
        # Month number with year: 2025-01
        (r"\b\d{4}-(0?[1-9]|1[0-2])\b", "month_num"),
        # Year only: 2025, FY2026
        (r"\b(fy)?\s*\d{4}\b", "year"),
        # Ranges: Q1-Q2 2026, Jan-Mar 2025
        (r"\b(q[1-4]|h[12]|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*[-–—]\s*(q[1-4]|h[12]|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\b", "range"),
    ]

    # Track matched positions to avoid duplicates
    matched_spans = set()

    for pattern, period_type in patterns:
        for match in re.finditer(pattern, text_norm):
            span = (match.start(), match.end())

            # Skip if this span overlaps with a previous match
            if any(
                (span[0] < prev_end and span[1] > prev_start)
                for prev_start, prev_end in matched_spans
            ):
                continue

            # Try to resolve the matched text
            period_text = match.group(0)
            period = period_identifier(period_text, asof_ts=asof_ts)

            if period:
                periods.append(period)
                matched_spans.add(span)

    # Sort by start timestamp
    periods.sort(key=lambda p: p["start_ts"])

    return periods


def format_period_display(period: dict) -> str:
    """
    Format period dict for human-readable display.

    Args:
        period: Period dict from period_identifier()

    Returns:
        Display string

    Examples:
        >>> period = period_identifier("Q1 2026")
        >>> format_period_display(period)
        'Q1 2026 (Jan 1 - Mar 31, 2026)'

        >>> period = period_identifier("H2 2025")
        >>> format_period_display(period)
        'H2 2025 (Jul 1 - Dec 31, 2025)'

        >>> period = period_identifier("2025-W02")
        >>> format_period_display(period)
        'W02 2025 (Jan 6 - Jan 12, 2025)'
    """
    if not period:
        return ""

    period_type = period["period_type"]
    start = period["start_ts"]
    end = period["end_ts"]

    # Format based on period type
    if period_type == "year":
        return f"{period['period_id']}"

    elif period_type == "half":
        half_num = period["period_id"][-1]  # Extract "2" from "2026H2"
        return f"H{half_num} {period['year']} ({start.strftime('%b %-d')} - {end.strftime('%b %-d, %Y')})"

    elif period_type == "quarter":
        q_num = period["period_id"][-1]  # Extract "1" from "2026Q1"
        return f"Q{q_num} {period['year']} ({start.strftime('%b %-d')} - {end.strftime('%b %-d, %Y')})"

    elif period_type == "month":
        return f"{start.strftime('%B %Y')}"

    elif period_type == "week":
        week_num = period["period_id"].split("-W")[1]  # Extract "02" from "2025-W02"
        return f"W{week_num} {period['year']} ({start.strftime('%b %-d')} - {end.strftime('%b %-d, %Y')})"

    elif period_type == "date_range":
        return f"{period['period_id']} ({start.strftime('%b %-d')} - {end.strftime('%b %-d, %Y')})"

    return period.get("period_id", "")


__all__ = [
    "period_identifier",
    "extract_periods",
    "format_period_display",
]

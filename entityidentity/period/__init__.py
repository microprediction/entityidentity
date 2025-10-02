"""Period module for temporal entity resolution.

This module provides resolution for any date-ish text to canonical Period
objects with start/end timestamps.

Public API:
    period_identifier(text, asof_ts=None) -> dict | None
        Resolve period text to canonical Period

    extract_periods(text, asof_ts=None) -> list[dict]
        Extract multiple periods from text

    format_period_display(period) -> str
        Format period for human-readable display

Examples:
    >>> from entityidentity.period import period_identifier, extract_periods
    >>>
    >>> # Resolve single period
    >>> period_identifier("H2 2026")
    {'period_type': 'half', 'period_id': '2026H2',
     'start_ts': datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC),
     'end_ts': datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC), ...}
    >>>
    >>> # Resolve date range
    >>> period_identifier("Q1-Q2 2026")
    {'period_type': 'date_range', 'period_id': '2026Q1-2026Q2', ...}
    >>>
    >>> # Resolve ISO week (Monday start)
    >>> period_identifier("2025-W02")
    {'period_type': 'week', 'period_id': '2025-W02',
     'start_ts': datetime(2025, 1, 6, 0, 0, 0, tzinfo=UTC), ...}
    >>>
    >>> # Relative period
    >>> from datetime import datetime, timezone
    >>> asof = datetime(2025, 10, 2, tzinfo=timezone.utc)
    >>> period_identifier("last quarter", asof_ts=asof)
    {'period_type': 'quarter', 'period_id': '2025Q3', ...}
    >>>
    >>> # Extract multiple periods from text
    >>> text = "Revenue grew in Q1 2026 and H2 2025."
    >>> extract_periods(text)
    [{'period_type': 'quarter', 'period_id': '2026Q1', ...},
     {'period_type': 'half', 'period_id': '2025H2', ...}]
"""

from entityidentity.period.periodapi import (
    period_identifier,
    extract_periods,
    format_period_display,
)

__all__ = [
    "period_identifier",
    "extract_periods",
    "format_period_display",
]

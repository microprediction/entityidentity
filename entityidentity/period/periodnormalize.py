"""Period Text Normalization
---------------------------

Utility functions for normalizing period-related text before parsing.

Examples:
  >>> normalize_period_text("Q1 2026")
  'q1 2026'

  >>> normalize_period_text("H2-2025")
  'h2 2025'

  >>> normalize_period_text("Jan–Mar 2025")
  'jan-mar 2025'
"""

import re
import unicodedata


def normalize_period_text(text: str) -> str:
    """
    Normalize period text for consistent parsing.

    Transformations:
      - Strip whitespace
      - Lowercase
      - Normalize Unicode (NFC)
      - Normalize dashes (—, –, − → -)
      - Normalize spaces around hyphens
      - Remove excessive whitespace

    Args:
        text: Raw period text (e.g., "Q1 2026", "H2–2025")

    Returns:
        Normalized text for parsing

    Examples:
        >>> normalize_period_text("Q1 2026")
        'q1 2026'

        >>> normalize_period_text("H2–2025")
        'h2 2025'

        >>> normalize_period_text("Jan - Mar 2025")
        'jan-mar 2025'

        >>> normalize_period_text("2025  Q1")
        '2025 q1'
    """
    if not text:
        return ""

    # Strip and lowercase
    text = text.strip().lower()

    # Unicode normalization (NFC)
    text = unicodedata.normalize("NFC", text)

    # Normalize various dash types to single hyphen
    # em dash (—), en dash (–), minus sign (−), figure dash (‒)
    text = text.replace("—", "-")
    text = text.replace("–", "-")
    text = text.replace("−", "-")
    text = text.replace("‒", "-")

    # Normalize spaces around hyphens: "Q1 - Q2" → "Q1-Q2"
    text = re.sub(r"\s*-\s*", "-", text)

    # Collapse multiple spaces to single space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_year(text: str) -> int | None:
    """
    Extract 4-digit year from text.

    Args:
        text: Normalized period text

    Returns:
        4-digit year or None if not found

    Examples:
        >>> extract_year("q1 2026")
        2026

        >>> extract_year("2025-w02")
        2025

        >>> extract_year("h2")
        None
    """
    # Match 4-digit year (1900-2199)
    match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", text)
    if match:
        return int(match.group(1))
    return None


def extract_quarter_half_month(text: str) -> tuple[str | None, int | None]:
    """
    Extract quarter/half/month indicators.

    Args:
        text: Normalized period text

    Returns:
        (period_type, period_number) tuple
        Examples: ("quarter", 1), ("half", 2), ("month", 3)

    Examples:
        >>> extract_quarter_half_month("q1 2026")
        ('quarter', 1)

        >>> extract_quarter_half_month("h2 2025")
        ('half', 2)

        >>> extract_quarter_half_month("fy2026")
        (None, None)
    """
    # Quarter: Q1, Q2, Q3, Q4
    quarter_match = re.search(r"\bq([1-4])\b", text)
    if quarter_match:
        return ("quarter", int(quarter_match.group(1)))

    # Half: H1, H2
    half_match = re.search(r"\bh([12])\b", text)
    if half_match:
        return ("half", int(half_match.group(1)))

    # Month number: 01-12 or 1-12
    month_match = re.search(r"\b(0?[1-9]|1[0-2])\b", text)
    if month_match:
        return ("month", int(month_match.group(1)))

    return (None, None)


def extract_month_name(text: str) -> int | None:
    """
    Extract month number from month name.

    Args:
        text: Normalized period text

    Returns:
        Month number (1-12) or None

    Examples:
        >>> extract_month_name("jan 2026")
        1

        >>> extract_month_name("december 2025")
        12

        >>> extract_month_name("q1 2026")
        None
    """
    # Month name patterns (support abbreviations and full names)
    month_patterns = {
        1: r"\b(jan|january)\b",
        2: r"\b(feb|february)\b",
        3: r"\b(mar|march)\b",
        4: r"\b(apr|april)\b",
        5: r"\b(may)\b",
        6: r"\b(jun|june)\b",
        7: r"\b(jul|july)\b",
        8: r"\b(aug|august)\b",
        9: r"\b(sep|sept|september)\b",
        10: r"\b(oct|october)\b",
        11: r"\b(nov|november)\b",
        12: r"\b(dec|december)\b",
    }

    for month_num, pattern in month_patterns.items():
        if re.search(pattern, text):
            return month_num

    return None


def extract_iso_week(text: str) -> tuple[int | None, int | None]:
    """
    Extract ISO week number from text.

    Supports formats:
      - 2025-W02
      - 2025W02
      - W02 2025

    Args:
        text: Normalized period text

    Returns:
        (year, week_number) tuple or (None, None)

    Examples:
        >>> extract_iso_week("2025-w02")
        (2025, 2)

        >>> extract_iso_week("w02 2025")
        (2025, 2)

        >>> extract_iso_week("q1 2025")
        (None, None)
    """
    # ISO week format: 2025-W02 or 2025W02
    match = re.search(r"\b(\d{4})-?w(0?[1-9]|[1-4]\d|5[0-3])\b", text)
    if match:
        year = int(match.group(1))
        week = int(match.group(2))
        return (year, week)

    # W02 2025 format
    match = re.search(r"\bw(0?[1-9]|[1-4]\d|5[0-3])\s+(\d{4})\b", text)
    if match:
        week = int(match.group(1))
        year = int(match.group(2))
        return (year, week)

    return (None, None)


def detect_range_separator(text: str) -> bool:
    """
    Detect if text contains a range separator.

    Looks for patterns like:
      - Q1-Q2
      - Jan-Mar
      - H1 to H2
      - 2025-01 to 2025-03

    Args:
        text: Normalized period text

    Returns:
        True if range separator detected, False otherwise

    Examples:
        >>> detect_range_separator("q1-q2 2026")
        True

        >>> detect_range_separator("jan-mar 2025")
        True

        >>> detect_range_separator("q1 2026")
        False

        >>> detect_range_separator("h1 to h2 2026")
        True
    """
    # Range patterns: hyphen, "to", "through", "thru"
    range_patterns = [
        r"\b(q[1-4]|h[12]|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-",
        r"\bto\b",
        r"\bthrough\b",
        r"\bthru\b",
    ]

    for pattern in range_patterns:
        if re.search(pattern, text):
            return True

    return False


def is_relative_period(text: str) -> bool:
    """
    Detect if text describes a relative period.

    Examples: "last quarter", "this year", "next month"

    Args:
        text: Normalized period text

    Returns:
        True if relative period detected, False otherwise

    Examples:
        >>> is_relative_period("last quarter")
        True

        >>> is_relative_period("this year")
        True

        >>> is_relative_period("q1 2026")
        False
    """
    relative_keywords = [
        r"\blast\b",
        r"\bthis\b",
        r"\bnext\b",
        r"\bcurrent\b",
        r"\bprevious\b",
        r"\bprior\b",
    ]

    for keyword in relative_keywords:
        if re.search(keyword, text):
            return True

    return False


__all__ = [
    "normalize_period_text",
    "extract_year",
    "extract_quarter_half_month",
    "extract_month_name",
    "extract_iso_week",
    "detect_range_separator",
    "is_relative_period",
]

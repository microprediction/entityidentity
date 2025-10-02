"""Instruments entity resolution API.

Public API for instrument/ticker identification and resolution.
Provides a clean, simple API for resolving ticker references to canonical
instruments with deterministic identifiers and metal crosswalk.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional, Union, List, Dict
import pandas as pd

# Import implementation from instrumentidentity
from entityidentity.instruments.instrumentidentity import (
    resolve_instrument as _resolve_instrument,
    topk_matches as _topk_matches,
)

# Import loader
from entityidentity.instruments.instrumentloaders import (
    load_instruments as _load_instruments
)


# Re-export load_instruments for convenience
load_instruments = _load_instruments


def instrument_identifier(
    text: str,
    *,
    source_hint: Optional[str] = None,
    threshold: int = 92,
) -> Optional[Dict]:
    """Resolve text to price instrument from ticker_references.

    Resolves ticker symbols, instrument names, and descriptions to
    canonical instrument entities using multi-stage blocking and fuzzy matching.

    Resolution strategy:
      1. Regex detection for known ticker patterns (MB-, LME_, etc.)
      2. Source filtering if hint provided or pattern detected
      3. Prefix blocking on ticker_norm
      4. Fuzzy scoring via RapidFuzz WRatio
      5. Boosts for matching source/material hints

    Args:
        text: Input text - can be ticker (MB-CO-0005), name (Cobalt standard grade),
              or partial description
        source_hint: Optional data provider hint ("Fastmarkets", "LME", "CME", etc.)
                    to filter/boost matching instruments
        threshold: Minimum score required for match (default 92, range 0-100)

    Returns:
        Dictionary with instrument details if match found, None otherwise:
        {
            "entity_type": "instrument",
            "instrument_id": "a3f2c8...",  # 16-char stable hash
            "provider": "Fastmarkets",
            "ticker": "MB-CO-0005",
            "instrument_name": "Cobalt standard grade in-whs Rotterdam",
            "currency": "USD",
            "unit": "USD/lb",
            "basis": None,  # or "Cr contained", "WO3 basis", etc.
            "material_id": "Co",  # Resolved metal ID if available
            "cluster_id": "nickel_cobalt_chain",  # From metal's cluster
            "score": 99
        }

    Examples:
        >>> instrument_identifier("MB-CO-0005")
        {"entity_type": "instrument",
         "instrument_id": "be9924e6a8b84a2a",
         "provider": "Fastmarkets",
         "ticker": "MB-CO-0005",
         "instrument_name": "Cobalt standard grade in-whs Rotterdam",
         "currency": "USD",
         "unit": "USD/lb",
         "material_id": "217037e460d592ee",
         "cluster_id": "nickel_cobalt_chain",
         "score": 100}

        >>> instrument_identifier("LME aluminum", source_hint="LME")
        {"entity_type": "instrument",
         "ticker": "LME_AL_CASH",
         "instrument_name": "LME Aluminium Cash",
         ...}

        >>> instrument_identifier("APT 88.5% Europe", source_hint="Fastmarkets")
        # Returns instrument if found, else None

    Notes:
        - Ticker patterns are automatically detected (MB-, LME_, PA, etc.)
        - Source_hint biases matching but doesn't exclude other sources
        - Returns None if no match above threshold
        - Callers should try instrument_identifier first, then fall back to
          metal_identifier if no instrument match
    """
    # Load instruments data
    df = load_instruments()

    # Resolve using implementation
    match = _resolve_instrument(
        text,
        df,
        source_hint=source_hint,
        threshold=threshold,
    )

    if match is None:
        return None

    # Build return dictionary matching spec
    result = {
        "entity_type": "instrument",
        "instrument_id": match.get("instrument_id"),
        "provider": match.get("Source"),
        "ticker": match.get("asset_id"),
        "instrument_name": None,  # Will populate below
        "currency": match.get("currency"),
        "unit": match.get("unit"),
        "basis": match.get("basis"),  # May not exist
        "material_id": match.get("material_id"),
        "cluster_id": match.get("cluster_id"),
        "score": 100,  # Will update with actual score
    }

    # Find instrument name from various possible columns
    name_cols = ["Name", "name", "instrument_name", "asset_name", "Description"]
    for col in name_cols:
        if col in match and pd.notna(match[col]):
            result["instrument_name"] = match[col]
            break

    # Clean up None values for missing columns
    result = {k: v for k, v in result.items() if v is not None}

    return result


def match_instruments(
    text: str,
    *,
    k: int = 5,
    source_hint: Optional[str] = None,
) -> List[Dict]:
    """Get top-K instrument candidates with scores.

    Useful for disambiguation or showing alternatives when exact match uncertain.

    Args:
        text: Input text to match
        k: Maximum number of candidates to return (default 5)
        source_hint: Optional source to filter/boost

    Returns:
        List of instrument dictionaries with scores, sorted by score descending.
        Same structure as instrument_identifier but may include lower-scoring matches.

    Examples:
        >>> match_instruments("cobalt", k=3)
        [
            {"ticker": "MB-CO-0005", "instrument_name": "Cobalt standard grade...", "score": 95},
            {"ticker": "MB-CO-0001", "instrument_name": "Cobalt alloy grade...", "score": 92},
            {"ticker": "MB-BMS-0002", "instrument_name": "Black mass payable...", "score": 88}
        ]

        >>> match_instruments("aluminum", k=2, source_hint="LME")
        [
            {"ticker": "LME_AL_CASH", "provider": "LME", "score": 100},
            {"ticker": "LME_AL_3M", "provider": "LME", "score": 95}
        ]
    """
    # Load instruments data
    df = load_instruments()

    # Get top-k matches
    matches = _topk_matches(
        text,
        df,
        k=k,
        source_hint=source_hint,
    )

    # Convert to list of dicts
    results = []
    for row, score in matches:
        result = {
            "entity_type": "instrument",
            "instrument_id": row.get("instrument_id"),
            "provider": row.get("Source"),
            "ticker": row.get("asset_id"),
            "instrument_name": None,
            "currency": row.get("currency"),
            "unit": row.get("unit"),
            "basis": row.get("basis"),
            "material_id": row.get("material_id"),
            "cluster_id": row.get("cluster_id"),
            "score": round(score),
        }

        # Find instrument name
        name_cols = ["Name", "name", "instrument_name", "asset_name", "Description"]
        for col in name_cols:
            if col in row and pd.notna(row[col]):
                result["instrument_name"] = row[col]
                break

        # Clean up None values
        result = {k: v for k, v in result.items() if v is not None}
        results.append(result)

    return results


def list_instruments(
    *,
    source: Optional[str] = None,
    search: Optional[str] = None,
) -> pd.DataFrame:
    """List instruments, optionally filtered by provider or search term.

    Useful for browsing available instruments or finding all instruments
    from a specific data provider.

    Args:
        source: Filter to specific data provider ("Fastmarkets", "LME", etc.)
        search: Search term to filter instruments (searches ticker and name)

    Returns:
        DataFrame with filtered instruments, sorted by ticker.
        Includes all original columns plus computed columns (instrument_id, etc.)

    Examples:
        >>> list_instruments(source="LME")
        # DataFrame with all LME instruments

        >>> list_instruments(search="cobalt")
        # DataFrame with all instruments containing "cobalt"

        >>> list_instruments(source="Fastmarkets", search="lithium")
        # DataFrame with Fastmarkets lithium instruments
    """
    # Load all instruments
    df = load_instruments()

    # Apply source filter
    if source and "Source" in df.columns:
        df = df[df["Source"].str.lower() == source.lower()]

    # Apply search filter
    if search:
        search_lower = search.lower()

        # Search in multiple columns
        mask = pd.Series([False] * len(df), index=df.index)

        # Search in ticker
        if "asset_id" in df.columns:
            mask |= df["asset_id"].str.lower().str.contains(search_lower, na=False)

        # Search in name columns
        name_cols = ["Name", "name", "instrument_name", "asset_name"]
        for col in name_cols:
            if col in df.columns:
                mask |= df[col].str.lower().str.contains(search_lower, na=False)

        # Search in Metal column
        if "Metal" in df.columns:
            mask |= df["Metal"].str.lower().str.contains(search_lower, na=False)

        df = df[mask]

    # Sort by ticker
    if "asset_id" in df.columns:
        df = df.sort_values("asset_id")

    return df.reset_index(drop=True)
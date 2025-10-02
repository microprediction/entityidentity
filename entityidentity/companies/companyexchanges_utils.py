"""Shared utilities for loading exchange data across scripts.

This module provides a centralized function for loading data from multiple
stock exchanges (ASX, LSE, TSX) with consistent error handling and fallback
to sample data when live data is unavailable.

Used by:
- scripts/companies/expand_with_exchanges.py
- scripts/companies/preview_exchange_expansion.py
- scripts/companies/match_exchanges_to_gleif.py
"""

from typing import List, Tuple
import pandas as pd
from entityidentity.companies.companyexchanges import (
    load_asx,
    load_lse,
    load_tsx,
    sample_asx_data,
    sample_lse_data,
    sample_tsx_data,
)


def load_all_exchanges(use_samples_on_error: bool = True, verbose: bool = True) -> Tuple[pd.DataFrame, dict]:
    """Load data from all available stock exchanges.

    Attempts to load live data from ASX, LSE, and TSX exchanges.
    On error, can optionally fall back to sample data.

    Args:
        use_samples_on_error: If True, use sample data when live data fails to load
        verbose: If True, print progress messages

    Returns:
        Tuple of:
        - Combined DataFrame with all exchange data
        - Dict with loading statistics: {
            'asx': {'status': 'live'|'sample'|'error', 'count': int},
            'lse': {...},
            'tsx': {...},
            'total': int
          }

    Examples:
        >>> df, stats = load_all_exchanges()
        >>> print(f"Loaded {stats['total']} companies from {len(stats)-1} exchanges")

        >>> # Silent mode
        >>> df, stats = load_all_exchanges(verbose=False)

        >>> # Don't use samples on error
        >>> df, stats = load_all_exchanges(use_samples_on_error=False)
    """
    if verbose:
        print("=" * 70)
        print("Loading Exchange Data")
        print("=" * 70)

    exchanges_data = []
    stats = {}

    # ASX (Australia)
    if verbose:
        print("\n📊 ASX (Australian Securities Exchange)...")
    try:
        asx_df = load_asx()
        if verbose:
            print(f"   Loaded: {len(asx_df):,} companies")
        exchanges_data.append(asx_df)
        stats['asx'] = {'status': 'live', 'count': len(asx_df)}
    except Exception as e:
        if use_samples_on_error:
            if verbose:
                print(f"   ⚠️  Error: {e}")
                print(f"   Using sample data instead")
            asx_df = sample_asx_data()
            exchanges_data.append(asx_df)
            stats['asx'] = {'status': 'sample', 'count': len(asx_df)}
        else:
            if verbose:
                print(f"   ⚠️  Error: {e}")
            stats['asx'] = {'status': 'error', 'count': 0}

    # LSE (London)
    if verbose:
        print("\n📊 LSE (London Stock Exchange)...")
    try:
        lse_df = load_lse()
        if verbose:
            print(f"   Loaded: {len(lse_df):,} companies")
        exchanges_data.append(lse_df)
        stats['lse'] = {'status': 'live', 'count': len(lse_df)}
    except Exception as e:
        if use_samples_on_error:
            if verbose:
                print(f"   ⚠️  Error: {e}")
                print(f"   Using sample data instead")
            lse_df = sample_lse_data()
            exchanges_data.append(lse_df)
            stats['lse'] = {'status': 'sample', 'count': len(lse_df)}
        else:
            if verbose:
                print(f"   ⚠️  Error: {e}")
            stats['lse'] = {'status': 'error', 'count': 0}

    # TSX (Toronto)
    if verbose:
        print("\n📊 TSX (Toronto Stock Exchange)...")
    try:
        tsx_df = load_tsx()
        if verbose:
            print(f"   Loaded: {len(tsx_df):,} companies")
        exchanges_data.append(tsx_df)
        stats['tsx'] = {'status': 'live', 'count': len(tsx_df)}
    except Exception as e:
        if use_samples_on_error:
            if verbose:
                print(f"   ⚠️  Error: {e}")
                print(f"   Using sample data instead")
            tsx_df = sample_tsx_data()
            exchanges_data.append(tsx_df)
            stats['tsx'] = {'status': 'sample', 'count': len(tsx_df)}
        else:
            if verbose:
                print(f"   ⚠️  Error: {e}")
            stats['tsx'] = {'status': 'error', 'count': 0}

    # Combine all exchange data
    if exchanges_data:
        combined = pd.concat(exchanges_data, ignore_index=True)
        stats['total'] = len(combined)

        if verbose:
            print("\n" + "=" * 70)
            print(f"Total companies loaded: {len(combined):,}")
            print("=" * 70)

        return combined, stats
    else:
        if verbose:
            print("\n⚠️  No exchange data loaded")
        stats['total'] = 0
        return pd.DataFrame(), stats


__all__ = ['load_all_exchanges']

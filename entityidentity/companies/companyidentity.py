"""DEPRECATED: Legacy compatibility layer for company resolution.

⚠️  DEPRECATION NOTICE ⚠️

This module is deprecated and maintained only for backwards compatibility.
It will be removed in a future version.

**For new code, use the public API instead:**

    from entityidentity import (
        company_identifier,  # Get canonical ID for a company
        match_company,       # Find best matching company
        resolve_company,     # Full resolution with scores
        normalize_name,      # Normalize company names
        extract_companies,   # Extract companies from text
    )

Or import from the companies.companyapi module directly:

    from entityidentity.companies.companyapi import (
        company_identifier,
        match_company,
        resolve_company,
    )

**Architecture:**
- companyapi.py: Public user-facing API (use this!)
- companyresolver.py: Internal implementation (do not import directly)
- companyidentity.py: THIS FILE - deprecated compatibility layer

**What this module does:**
Re-exports public interfaces from modular implementations for backwards compatibility:
- companynormalize: LEGAL_RE, normalize_company_name
- companyblocking: block_candidates (internal)
- companyscoring: score_candidates (internal)
- companyresolver: load_companies, resolve_company, match_company (internal)
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

import pandas as pd

from entityidentity.companies.companynormalize import (
    LEGAL_RE,
    normalize_company_name,
)
from entityidentity.companies.companyblocking import block_candidates
from entityidentity.companies.companyscoring import score_candidates
from entityidentity.companies.companyresolver import (
    load_companies,
    resolve_company,
    match_company,
    list_companies,
)

__all__ = [
    'LEGAL_RE',
    'normalize_company_name',
    'block_candidates',
    'score_candidates',
    'load_companies',
    'resolve_company',
    'match_company',
    'list_companies',
]

# Backwards compatibility alias
normalize_name = normalize_company_name

 

"""Compatibility delegator for company resolution.

Re-exports public interfaces from modular implementations:
- companynormalize: LEGAL_RE, normalize_name
- companyblocking: block_candidates
- companyscoring: score_candidates
- companyresolver: load_companies, resolve_company, match_company, list_companies
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

import pandas as pd

from entityidentity.companies.companynormalize import (
    LEGAL_RE,
    normalize_name,
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
    'normalize_name',
    'block_candidates',
    'score_candidates',
    'load_companies',
    'resolve_company',
    'match_company',
    'list_companies',
]

 

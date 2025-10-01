"""Company identity resolution and matching.

Architecture:
- companyapi.py: Public user-facing API (clean interfaces)
- companyidentity.py: Implementation details (not exposed directly)
- companyextractor.py: Text extraction utilities (used by API)
- companynormalize.py: Name normalization for display/identifiers
- Data loaders: Direct access for advanced users
"""

# User-facing API (clean wrappers around implementation)
from entityidentity.companies.companyapi import (
    normalize_name,
    match_company,
    resolve_company,
    list_companies,
    extract_companies,
    get_company_id,
)

# Data loaders (for advanced users and scripts)
from entityidentity.companies.companygleif import (
    load_gleif_lei,
    sample_gleif_data,
)

from entityidentity.companies.companywikidata import (
    load_wikidata_companies,
    sample_wikidata_data,
)

from entityidentity.companies.companyexchanges import (
    load_asx,
    load_lse,
    load_tsx,
    sample_asx_data,
    sample_lse_data,
    sample_tsx_data,
)

# LLM filtering (for advanced users)
from entityidentity.companies.companyfilter import (
    filter_companies_llm,
    load_config,
)

__all__ = [
    # Main API
    "normalize_name",
    "match_company",
    "resolve_company",
    "list_companies",
    "extract_companies",
    "get_company_id",
    # Data loaders
    "load_gleif_lei",
    "sample_gleif_data",
    "load_wikidata_companies",
    "sample_wikidata_data",
    "load_asx",
    "load_lse",
    "load_tsx",
    "sample_asx_data",
    "sample_lse_data",
    "sample_tsx_data",
    # LLM filtering
    "filter_companies_llm",
    "load_config",
]


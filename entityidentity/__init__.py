"""Entity Identity - Ontology / Entity Resolution

Public API for entity resolution across companies, countries, and metals.

Usage:
    from entityidentity import company_identifier, match_company

    # Get canonical company identifier
    company_id = company_identifier("Apple")  # Returns: 'Apple Inc:US'

    # Get full company details
    company = match_company("BHP", country="AU")

See entityidentity/companies/API.md for full documentation.
"""

__version__ = "0.0.1"

# ============================================================================
# Company Resolution API
# ============================================================================
# Primary interface: entityidentity.companies.companyapi
# Implementation: entityidentity.companies.companyresolver (internal)
# Deprecated: entityidentity.companies.companyidentity (use companyapi instead)

from .companies.companyapi import (
    company_identifier,      # Primary API - get canonical identifier
    get_identifier,          # Alias for backwards compatibility
    normalize_company_name,  # Normalize company names for matching
    canonicalize_company_name, # Canonicalize names for display/identifiers
    normalize_name,          # DEPRECATED - use normalize_company_name
    match_company,           # Get best matching company with details
    resolve_company,         # Get resolution with all candidates and scores
    list_companies,          # List/filter companies in database
    extract_companies,       # Extract companies from text
    get_company_id,          # Format company as identifier string
)

# ============================================================================
# Country Resolution API
# ============================================================================

from .countries.countryapi import (
    country_identifier,   # Primary API - resolve country name to ISO code
    country_identifiers,  # Batch resolution of multiple countries
)

# ============================================================================
# Metal Resolution API
# ============================================================================

from .metals.metalapi import (
    metal_identifier,    # Primary API - resolve metal name to canonical form
    match_metal,         # Get top-K candidate matches
    list_metals,         # List/filter available metals
    load_metals,         # Load metals database
)

# Metal extraction utilities
from .metals.metalextractor import (
    extract_metals_from_text,  # Extract metal mentions from text
    extract_metal_pairs,       # Extract metal pairs/combinations
)

__all__ = [
    # Version
    "__version__",

    # ========================================================================
    # PRIMARY APIS - Start here!
    # ========================================================================
    "company_identifier",   # Resolve company name -> canonical ID
    "country_identifier",   # Resolve country name -> ISO code
    "metal_identifier",     # Resolve metal name -> canonical form

    # ========================================================================
    # Company Resolution
    # ========================================================================
    "match_company",             # Get full company details
    "resolve_company",           # Get resolution with scores
    "normalize_company_name",    # Normalize names for matching
    "canonicalize_company_name", # Canonicalize names for display
    "normalize_name",            # DEPRECATED - use normalize_company_name
    "extract_companies",         # Extract companies from text
    "list_companies",            # List companies in database
    "get_company_id",            # Format company as ID string
    "get_identifier",            # Alias for company_identifier (backwards compat)

    # ========================================================================
    # Country Resolution
    # ========================================================================
    "country_identifiers",  # Batch country resolution

    # ========================================================================
    # Metal Resolution & Extraction
    # ========================================================================
    "match_metal",              # Get top-K metal matches
    "list_metals",              # List available metals
    "load_metals",              # Load metals database
    "extract_metals_from_text", # Extract metals from text
    "extract_metal_pairs",      # Extract metal pairs
]


"""Entity Identity - Ontology / Entity Resolution

Public API for entity resolution across companies, countries, metals, baskets, places, and periods.

Usage:
    from entityidentity import company_identifier, match_company
    from entityidentity import metal_identifier, basket_identifier, period_identifier
    from entityidentity import place_identifier

    # Get canonical company identifier
    company_id = company_identifier("Apple")  # Returns: 'Apple Inc:US'

    # Get full company details
    company = match_company("BHP", country="AU")

    # Resolve metal names
    metal = metal_identifier("Pt")  # Returns: {'name': 'Platinum', 'symbol': 'Pt', ...}

    # Resolve basket names
    basket = basket_identifier("PGM 4E")  # Returns: {'basket_id': 'PGM_4E', ...}

    # Resolve place names
    place = place_identifier("Limpopo", country_hint="ZA")  # Returns: {'country': 'ZA', 'admin1': 'Limpopo', ...}

    # Resolve period names
    period = period_identifier("H2 2026")  # Returns: {'period_type': 'half', 'period_id': '2026H2', ...}

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

# ============================================================================
# Basket Resolution API
# ============================================================================

from .baskets.basketapi import (
    basket_identifier,       # Primary API - resolve basket name to canonical form
    match_basket,            # Get top-K candidate matches
    list_baskets,            # List all available baskets
    get_basket_components,   # Get component metals for a basket
    load_baskets,            # Load baskets database
)

# ============================================================================
# Places Resolution API
# ============================================================================

from .places.placeapi import (
    place_identifier,        # Primary API - resolve admin1 region to canonical form
    extract_location,        # Extract location from text
    match_place,             # Get top-K candidate matches
    list_places,             # List/filter available places
    load_places,             # Load places database
)

# ============================================================================
# Period Resolution API
# ============================================================================

from .period.periodapi import (
    period_identifier,       # Primary API - resolve period text to canonical form
    extract_periods,         # Extract multiple periods from text
    format_period_display,   # Format period for display
)

# ============================================================================
# Units Normalization API
# ============================================================================

from .units.unitapi import (
    normalize_unit,          # Primary API - normalize value/unit/basis to canonical form
    get_canonical_unit,      # Get canonical unit and basis for a material
    validate_conversion_inputs,  # Validate required parameters are present
)

# ============================================================================
# Build Utilities (for database generation)
# ============================================================================

from .companies.data.build_companies import (
    consolidate_companies,   # Build companies database from multiple sources
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
    "basket_identifier",    # Resolve basket name -> canonical form
    "place_identifier",     # Resolve place name -> canonical form
    "period_identifier",    # Resolve period text -> canonical form
    "normalize_unit",       # Normalize value/unit/basis to canonical form

    # ========================================================================
    # Company Resolution
    # ========================================================================
    "match_company",             # Get full company details
    "resolve_company",           # Get resolution with scores
    "normalize_company_name",    # Normalize names for matching
    "canonicalize_company_name", # Canonicalize names for display
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

    # ========================================================================
    # Basket Resolution
    # ========================================================================
    "match_basket",            # Get top-K basket matches
    "list_baskets",            # List all available baskets
    "get_basket_components",   # Get component metals for a basket
    "load_baskets",            # Load baskets database

    # ========================================================================
    # Places Resolution
    # ========================================================================
    "place_identifier",        # Resolve place name to canonical form
    "extract_location",        # Extract location from text
    "match_place",             # Get top-K place matches
    "list_places",             # List available places
    "load_places",             # Load places database

    # ========================================================================
    # Period Resolution
    # ========================================================================
    "period_identifier",       # Resolve period text to canonical form
    "extract_periods",         # Extract multiple periods from text
    "format_period_display",   # Format period for display

    # ========================================================================
    # Units Normalization
    # ========================================================================
    "normalize_unit",              # Normalize value/unit/basis to canonical form
    "get_canonical_unit",          # Get canonical unit and basis for a material
    "validate_conversion_inputs",  # Validate required parameters are present

    # ========================================================================
    # Build Utilities
    # ========================================================================
    "consolidate_companies",   # Build companies database from multiple sources
]


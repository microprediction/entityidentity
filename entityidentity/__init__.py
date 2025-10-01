"""Entity Identity - Ontology / Entity Resolution"""

__version__ = "0.0.1"

# Company resolution API
from .companies.companyapi import (
    company_identifier,  # Primary company API
    get_identifier,      # Alias for backwards compatibility
    normalize_name,
    match_company,
    resolve_company,
    list_companies,
    extract_companies,
    get_company_id,
)

# Country resolution API
from .countries.countryapi import (
    country_identifier,  # Primary country API
    country_identifiers, # Batch resolution
)

# Metal resolution API
from .metals.metalapi import (
    metal_identifier,    # Primary metal API
    match_metal,        # Top-K candidates
    list_metals,        # List/filter metals
    load_metals,        # Load metals database
)

# Metal extraction utilities
from .metals.metalextractor import (
    extract_metals_from_text,  # Extract metals from text
    extract_metal_pairs,       # Extract metal pairs/combinations
)

__all__ = [
    "__version__",
    # Primary APIs
    "company_identifier",
    "country_identifier",
    "country_identifiers",  # Batch country resolution
    "metal_identifier",     # Metal resolution
    # Company functions
    "get_identifier",    # Backwards compatibility
    "normalize_name",
    "match_company",
    "resolve_company",
    "list_companies",
    "extract_companies",
    "get_company_id",
    # Metal functions
    "match_metal",
    "list_metals",
    "load_metals",
    "extract_metals_from_text",
    "extract_metal_pairs",
]


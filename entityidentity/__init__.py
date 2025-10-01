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

__all__ = [
    "__version__",
    # Primary APIs
    "company_identifier",
    "country_identifier",
    "country_identifiers",  # Batch country resolution
    # Company functions
    "get_identifier",    # Backwards compatibility
    "normalize_name",
    "match_company",
    "resolve_company",
    "list_companies",
    "extract_companies",
    "get_company_id",
]


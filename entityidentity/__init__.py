"""Entity Identity - Ontology / Entity Resolution"""

__version__ = "0.0.1"

# Expose clean API
from .companies.companyapi import (
    normalize_name,
    match_company,
    resolve_company,
    list_companies,
    extract_companies,
    get_company_id,
)

__all__ = [
    "__version__",
    "normalize_name",
    "match_company",
    "resolve_company",
    "list_companies",
    "extract_companies",
    "get_company_id",
]


"""Entity Identity - Ontology / Entity Resolution"""

__version__ = "0.0.1"

# Expose main functions
from .companies.companyidentity import (
    normalize_name,
    resolve_company,
    match_company,
    load_companies,
)

from .companies.companygleif import load_gleif_lei
from .companies.companywikidata import load_wikidata_companies
from .companies.companyexchanges import load_asx, load_lse, load_tsx

__all__ = [
    "__version__",
    "normalize_name",
    "resolve_company",
    "match_company",
    "load_companies",
    "load_gleif_lei",
    "load_wikidata_companies",
    "load_asx",
    "load_lse",
    "load_tsx",
]


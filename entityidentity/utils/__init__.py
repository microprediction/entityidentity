"""Shared utilities for EntityIdentity package."""

from entityidentity.utils.dataloader import (
    find_data_file,
    load_parquet_or_csv,
    format_not_found_error,
)
from entityidentity.utils.normalize import (
    normalize_name,
    canonicalize_name,
    slugify_name,
    normalize_quotes,
)
from entityidentity.utils.resolver import (
    get_aliases,
    score_candidate,
    score_all_candidates,
    find_best_match,
    topk_matches,
)

__all__ = [
    # Data loading
    "find_data_file",
    "load_parquet_or_csv",
    "format_not_found_error",
    # Normalization
    "normalize_name",
    "canonicalize_name",
    "slugify_name",
    "normalize_quotes",
    # Resolution
    "get_aliases",
    "score_candidate",
    "score_all_candidates",
    "find_best_match",
    "topk_matches",
]
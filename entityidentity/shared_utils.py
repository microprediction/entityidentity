"""
Shared Utility Functions (DEPRECATED)
--------------------------------------

DEPRECATED: This module is deprecated. Use the following instead:
  - entityidentity.utils.normalize: For normalization functions
  - entityidentity.utils.resolver: For resolution functions
  - entityidentity.utils.build_utils: For build utilities

This module is kept for backward compatibility only and will be removed in a future version.
All functions below now import from the new locations.
"""

import warnings

warnings.warn(
    "entityidentity.shared_utils is deprecated. "
    "Use entityidentity.utils.normalize, entityidentity.utils.resolver, "
    "or entityidentity.utils.build_utils instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from new locations for backward compatibility
from entityidentity.utils.normalize import slugify_name
from entityidentity.utils.build_utils import expand_aliases, load_yaml_file

# Note: generate_entity_id, get_aliases, and score_candidate have been moved
# to entityidentity.utils.resolver but are not re-exported here as they were
# not part of the original public API of this module


__all__ = [
    "slugify_name",
    "expand_aliases",
    "load_yaml_file",
]
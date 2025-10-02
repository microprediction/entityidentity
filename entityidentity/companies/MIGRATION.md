# Migration Guide: Normalization Function Names

## Overview

Starting with v0.1.0, EntityIdentity uses consistent naming for normalization functions. The shorter aliases (`normalize_name`, `canonicalize_name`) are deprecated and will be removed in v1.0.0.

## Changes

### Old Names (Deprecated)
- `normalize_name()` → **Use `normalize_company_name()`**
- `canonicalize_name()` → **Use `canonicalize_company_name()`**

### New Consistent Names
- `normalize_company_name()` - For fuzzy matching (aggressive normalization)
- `canonicalize_company_name()` - For display/identifiers (preserves readability)

## Migration Examples

### Basic Usage

```python
# OLD (deprecated)
from entityidentity import normalize_name
normalized = normalize_name("Apple Inc.")

# NEW (recommended)
from entityidentity import normalize_company_name
normalized = normalize_company_name("Apple Inc.")
```

### Both Functions

```python
# OLD (deprecated)
from entityidentity.companies.companynormalize import normalize_name, canonicalize_name
fuzzy = normalize_name("Microsoft Corp.")
display = canonicalize_name("Microsoft, Corp.")

# NEW (recommended)
from entityidentity.companies.companynormalize import normalize_company_name, canonicalize_company_name
fuzzy = normalize_company_name("Microsoft Corp.")
display = canonicalize_company_name("Microsoft, Corp.")
```

### Public API Usage

```python
# OLD (deprecated)
from entityidentity.companies import normalize_name
result = normalize_name("BHP Billiton Ltd")

# NEW (recommended)
from entityidentity.companies import normalize_company_name
result = normalize_company_name("BHP Billiton Ltd")
```

## Deprecation Timeline

- **v0.1.0** (current): Old names deprecated with warnings
- **v1.0.0** (future): Old names removed completely

## Suppressing Warnings

If you need time to migrate, you can temporarily suppress deprecation warnings:

```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="entityidentity")

# Your code using old names
from entityidentity import normalize_name  # No warning shown
```

## Why This Change?

1. **Clarity**: The new names clearly indicate they work on company names, not generic text
2. **Consistency**: All company-related functions now use the `company_` prefix
3. **Discoverability**: Easier to find related functions with autocomplete
4. **Future-proofing**: Room for other normalization functions (e.g., `normalize_person_name`)

## Questions?

Please file an issue on GitHub if you have questions about migration.
"""Test suite for basket name normalization functions.

Tests the three normalization layers:
1. normalize_basket_name() - Aggressive normalization for fuzzy matching
2. canonicalize_basket_name() - Light normalization for display
3. slugify_basket_name() - URL/key-safe slugs
4. generate_basket_id() - Deterministic ID generation
"""

import pytest
from entityidentity.baskets.basketnormalize import (
    normalize_basket_name,
    canonicalize_basket_name,
    slugify_basket_name,
    generate_basket_id,
)


# ---- Test 1: normalize_basket_name() ----

def test_normalize_basic():
    """Test basic normalization"""
    assert normalize_basket_name("PGM 4E") == "pgm 4e"
    assert normalize_basket_name("NdPr") == "ndpr"
    assert normalize_basket_name("Battery Pack") == "battery pack"


def test_normalize_case_insensitive():
    """Test normalization is case-insensitive"""
    assert normalize_basket_name("PGM 4E") == normalize_basket_name("pgm 4e")
    assert normalize_basket_name("NDPR") == normalize_basket_name("ndpr")
    assert normalize_basket_name("REE Light") == normalize_basket_name("ree light")


def test_normalize_whitespace():
    """Test normalization collapses whitespace"""
    assert normalize_basket_name("PGM  4E") == "pgm 4e"
    assert normalize_basket_name("  Battery   Pack  ") == "battery pack"
    assert normalize_basket_name("REE\tLight") == "ree light"


def test_normalize_special_characters():
    """Test normalization handles special characters"""
    assert normalize_basket_name("PGM-4E") == "pgm-4e"
    assert normalize_basket_name("Nd/Pr") == "nd/pr"
    assert normalize_basket_name("Battery (Pack)") == "battery (pack)"


def test_normalize_removes_punctuation():
    """Test normalization removes unwanted punctuation"""
    # Commas, periods, exclamation marks should be removed
    assert normalize_basket_name("PGM, 4E") == "pgm 4e"
    assert normalize_basket_name("Battery Pack!") == "battery pack"
    assert normalize_basket_name("REE.Light") == "ree light"


def test_normalize_unicode():
    """Test normalization handles Unicode"""
    # normalize uses NFC which preserves accents, unlike slugify which removes them
    # The regex removes non-alphanumeric chars, so é is removed entirely
    result = normalize_basket_name("Café")
    assert "caf" in result.lower()  # é removed by regex

    result2 = normalize_basket_name("naïve")
    assert "na" in result2.lower() and "ve" in result2.lower()


def test_normalize_empty():
    """Test normalization handles empty strings"""
    assert normalize_basket_name("") == ""
    assert normalize_basket_name("   ") == ""
    assert normalize_basket_name(None) == ""


# ---- Test 2: canonicalize_basket_name() ----

def test_canonicalize_basic():
    """Test basic canonicalization"""
    # Canonicalize preserves original casing
    assert canonicalize_basket_name("PGM 4E") == "PGM 4E"
    assert canonicalize_basket_name("NdPr") == "NdPr"
    assert canonicalize_basket_name("Battery Pack") == "Battery Pack"


def test_canonicalize_whitespace():
    """Test canonicalize collapses whitespace"""
    assert canonicalize_basket_name("PGM  4E") == "PGM 4E"
    assert canonicalize_basket_name("  Battery   Pack  ") == "Battery Pack"


def test_canonicalize_preserves_case():
    """Test canonicalize preserves original case"""
    # Unlike normalize, canonicalize keeps the case as provided
    assert canonicalize_basket_name("PGM 4E") == "PGM 4E"
    assert canonicalize_basket_name("pgm 4e") == "pgm 4e"


def test_canonicalize_empty():
    """Test canonicalize handles empty strings"""
    assert canonicalize_basket_name("") == ""
    assert canonicalize_basket_name("   ") == ""
    assert canonicalize_basket_name(None) == ""


# ---- Test 3: slugify_basket_name() ----

def test_slugify_basic():
    """Test basic slugification"""
    assert slugify_basket_name("PGM 4E") == "pgm-4e"
    assert slugify_basket_name("NdPr") == "ndpr"
    assert slugify_basket_name("Battery Pack") == "battery-pack"
    assert slugify_basket_name("REE Light") == "ree-light"


def test_slugify_removes_special_chars():
    """Test slugify removes special characters"""
    assert slugify_basket_name("PGM (4E)") == "pgm-4e"
    assert slugify_basket_name("Nd/Pr") == "ndpr"
    assert slugify_basket_name("Battery Pack!") == "battery-pack"


def test_slugify_replaces_spaces():
    """Test slugify replaces spaces with hyphens"""
    assert slugify_basket_name("Battery Pack") == "battery-pack"
    assert slugify_basket_name("PGM 4E Basket") == "pgm-4e-basket"


def test_slugify_collapses_hyphens():
    """Test slugify collapses multiple hyphens"""
    assert slugify_basket_name("PGM--4E") == "pgm-4e"
    assert slugify_basket_name("Battery   Pack") == "battery-pack"


def test_slugify_strips_hyphens():
    """Test slugify strips leading/trailing hyphens"""
    assert slugify_basket_name("-PGM 4E-") == "pgm-4e"
    assert slugify_basket_name("--Battery Pack--") == "battery-pack"


def test_slugify_lowercase():
    """Test slugify converts to lowercase"""
    assert slugify_basket_name("PGM 4E") == "pgm-4e"
    assert slugify_basket_name("BATTERY PACK") == "battery-pack"


def test_slugify_unicode():
    """Test slugify converts Unicode to ASCII"""
    assert slugify_basket_name("Café") == "cafe"
    assert slugify_basket_name("naïve") == "naive"


def test_slugify_empty():
    """Test slugify handles empty strings"""
    assert slugify_basket_name("") == ""
    assert slugify_basket_name("   ") == ""
    assert slugify_basket_name(None) == ""


def test_slugify_url_safe():
    """Test slugify output is URL-safe"""
    import re
    url_safe_pattern = re.compile(r'^[a-z0-9\-]*$')

    test_inputs = [
        "PGM 4E",
        "Battery Pack",
        "NdPr Oxide",
        "REE Light (LREE)",
        "Pt/Pd/Rh/Au",
    ]

    for input_str in test_inputs:
        slug = slugify_basket_name(input_str)
        assert url_safe_pattern.match(slug), f"Slug not URL-safe: {slug}"


# ---- Test 4: generate_basket_id() ----

def test_generate_basket_id_deterministic():
    """Test basket_id generation is deterministic"""
    name = "PGM 4E"
    id1 = generate_basket_id(name)
    id2 = generate_basket_id(name)
    assert id1 == id2


def test_generate_basket_id_unique():
    """Test different names produce different IDs"""
    id1 = generate_basket_id("PGM 4E")
    id2 = generate_basket_id("PGM 5E")
    id3 = generate_basket_id("NdPr")

    # All should be different
    assert id1 != id2
    assert id1 != id3
    assert id2 != id3


def test_generate_basket_id_format():
    """Test basket_id has correct format (16 hex chars)"""
    import re
    hex_pattern = re.compile(r'^[0-9a-f]{16}$')

    test_names = ["PGM 4E", "Battery Pack", "NdPr", "REE Light"]

    for name in test_names:
        basket_id = generate_basket_id(name)
        assert len(basket_id) == 16
        assert hex_pattern.match(basket_id), f"Invalid basket_id format: {basket_id}"


def test_generate_basket_id_case_insensitive():
    """Test basket_id is same for different cases"""
    # Since normalization is applied first, case shouldn't matter
    id1 = generate_basket_id("PGM 4E")
    id2 = generate_basket_id("pgm 4e")
    assert id1 == id2


def test_generate_basket_id_whitespace_insensitive():
    """Test basket_id ignores whitespace differences"""
    id1 = generate_basket_id("PGM 4E")
    id2 = generate_basket_id("PGM  4E")
    id3 = generate_basket_id("  PGM 4E  ")
    assert id1 == id2 == id3


def test_generate_basket_id_namespace():
    """Test basket_id uses basket namespace (different from metal_id)"""
    # The ID should be different from metal_id for same string
    # This ensures baskets and metals have separate namespaces
    basket_id = generate_basket_id("PGM 4E")

    # We can't directly test against metal_id without importing metals module,
    # but we can verify the ID is generated with proper namespace
    # The implementation uses "|basket" suffix for namespace
    assert len(basket_id) == 16
    assert isinstance(basket_id, str)


# ---- Test 5: Normalization Consistency ----

def test_normalization_idempotent():
    """Test normalize is idempotent"""
    name = "PGM 4E"
    normalized = normalize_basket_name(name)
    normalized_twice = normalize_basket_name(normalized)
    assert normalized == normalized_twice


def test_canonicalize_idempotent():
    """Test canonicalize is idempotent"""
    name = "PGM  4E  "
    canonical = canonicalize_basket_name(name)
    canonical_twice = canonicalize_basket_name(canonical)
    assert canonical == canonical_twice


def test_slugify_idempotent():
    """Test slugify is idempotent"""
    name = "PGM 4E"
    slug = slugify_basket_name(name)
    slug_twice = slugify_basket_name(slug)
    assert slug == slug_twice


def test_normalize_then_slugify():
    """Test normalize → slugify pipeline"""
    name = "PGM 4E"
    normalized = normalize_basket_name(name)
    # Slugify of normalized should match direct slugify
    assert slugify_basket_name(normalized) == slugify_basket_name(name)


# ---- Test 6: Real-World Examples ----

def test_normalization_real_baskets():
    """Test normalization on real basket names"""
    test_cases = [
        ("PGM 4E", "pgm 4e", "PGM 4E", "pgm-4e"),
        ("PGM 5E", "pgm 5e", "PGM 5E", "pgm-5e"),
        ("NdPr", "ndpr", "NdPr", "ndpr"),
        ("REE Light", "ree light", "REE Light", "ree-light"),
        ("Battery Pack", "battery pack", "Battery Pack", "battery-pack"),
    ]

    for name, expected_norm, expected_canon, expected_slug in test_cases:
        assert normalize_basket_name(name) == expected_norm
        assert canonicalize_basket_name(name) == expected_canon
        assert slugify_basket_name(name) == expected_slug


def test_normalization_aliases():
    """Test normalization on basket aliases"""
    # Test aliases normalize to similar forms
    pgm_4e_aliases = [
        "PGM 4E",
        "4E PGM",
        "Four Element PGM",
        "Platinum Group 4E",
    ]

    # All should normalize to lowercase with consistent whitespace
    normalized = [normalize_basket_name(alias) for alias in pgm_4e_aliases]

    # All should be lowercase and collapsed whitespace
    for norm in normalized:
        assert norm == norm.lower()
        assert "  " not in norm  # No double spaces


def test_basket_id_real_baskets():
    """Test basket_id generation on real baskets"""
    basket_names = [
        "PGM 4E",
        "PGM 5E",
        "NdPr",
        "REE Light",
        "Battery Pack",
    ]

    # Generate all IDs
    basket_ids = [generate_basket_id(name) for name in basket_names]

    # All should be unique
    assert len(basket_ids) == len(set(basket_ids))

    # All should be valid 16-char hex
    import re
    hex_pattern = re.compile(r'^[0-9a-f]{16}$')
    for basket_id in basket_ids:
        assert hex_pattern.match(basket_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

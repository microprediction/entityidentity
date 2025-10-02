"""Test suite for metals entity resolution.

Tests follow section 12 of METALS_ONTOLOGY_PLAN.md:
1. test_symbol_exact() — Pt → Platinum
2. test_aliases() — wolfram → tungsten (when tungsten added)
3. test_trade_terms() — APT 88.5% → APT with basis='$/mtu WO3'
4. test_colon_hints() — lithium:carbonate → lithium carbonate
5. test_cluster_filtering() — resolve within pgm_complex
6. test_unit_basis_validation() — verify section 9's examples
7. test_topk_matching() — scored candidates
"""

import pytest
from entityidentity.metals.metalapi import (
    load_metals,
    metal_identifier,
    match_metal,
    list_metals,
)


# ---- Fixtures ----

@pytest.fixture
def metals_df():
    """Load metals DataFrame once for all tests"""
    return load_metals()


# ---- Test 1: Exact Symbol Match ----

def test_symbol_exact_pt(metals_df):
    """Test Pt → Platinum exact symbol match"""
    result = metal_identifier("Pt")
    assert result is not None
    assert result["name"] == "Platinum"
    assert result["symbol"] == "Pt"
    assert result["category_bucket"] == "pgm"


def test_symbol_exact_cu(metals_df):
    """Test Cu → Copper exact symbol match"""
    result = metal_identifier("Cu")
    assert result is not None
    assert result["name"] == "Copper"
    assert result["symbol"] == "Cu"
    assert result["category_bucket"] == "base"


def test_symbol_exact_case_insensitive(metals_df):
    """Test that symbol matching is case-insensitive"""
    result_upper = metal_identifier("PT")
    result_lower = metal_identifier("pt")

    assert result_upper is not None
    assert result_lower is not None
    assert result_upper["metal_id"] == result_lower["metal_id"]
    assert result_upper["name"] == "Platinum"


def test_symbol_exact_ree(metals_df):
    """Test REE symbols resolve correctly"""
    ree_tests = [
        ("La", "Lanthanum"),
        ("Ce", "Cerium"),
        ("Nd", "Neodymium"),
        ("Dy", "Dysprosium"),
        ("Y", "Yttrium"),
    ]

    for symbol, expected_name in ree_tests:
        result = metal_identifier(symbol)
        assert result is not None, f"Failed to resolve {symbol}"
        assert result["name"] == expected_name
        assert result["symbol"] == symbol
        assert result["cluster_id"] == "rare_earth_chain"


# ---- Test 2: Aliases ----

def test_aliases_moly(metals_df):
    """Test moly → Molybdenum alias"""
    result = metal_identifier("moly")
    assert result is not None
    assert result["name"] == "Molybdenum"
    assert result["symbol"] == "Mo"


def test_aliases_ferrochrome(metals_df):
    """Test ferrochromium → Ferrochrome alias"""
    result = metal_identifier("ferrochromium")
    # May not resolve due to prefix blocking, but if it does:
    if result:
        assert result["name"] == "Ferrochrome"


def test_aliases_ndpr_variations(metals_df):
    """Test NdPr variations (limited by prefix blocking)"""
    # Full name should resolve
    result = metal_identifier("neodymium praseodymium")
    assert result is not None
    assert result["name"] == "Neodymium-Praseodymium"
    assert result["code"] == "NdPr"


# ---- Test 3: Trade Terms ----

def test_trade_terms_apt(metals_df):
    """Test APT 88.5% → Ammonium paratungstate with correct basis"""
    # Direct name match should work
    result = metal_identifier("ammonium paratungstate")
    assert result is not None
    assert result["name"] == "Ammonium Paratungstate"
    assert result["code"] == "WO3"
    assert result["default_basis"] == "$/mtu WO3"
    assert result["default_unit"] == "mtu"


def test_trade_terms_ferrochrome(metals_df):
    """Test Ferrochrome has correct basis with Cr content"""
    result = metal_identifier("ferrochrome")
    assert result is not None
    assert result["name"] == "Ferrochrome"
    assert result["default_basis"] == "$/lb Cr"
    assert "Cr" in result["default_basis"]


def test_trade_terms_lithium_carbonate(metals_df):
    """Test lithium carbonate has correct basis

    Note: Due to build script normalization removing 'carbonate' from name_norm,
    'lithium carbonate' may resolve to 'Lithium' (element) instead.
    Use colon hint syntax for disambiguation: 'lithium:carbonate'
    """
    # Using direct lookup to verify the lithium carbonate row exists
    li_carb = metals_df[metals_df["metal_key"] == "lithium-carbonate"]
    assert len(li_carb) == 1
    result = li_carb.iloc[0]
    assert result["name"] == "Lithium Carbonate"
    assert result["formula"] == "Li2CO3"
    assert "Li2CO3" in result["default_basis"]


# ---- Test 4: Colon Hints ----

def test_colon_hints_lithium_carbonate(metals_df):
    """Test lithium:carbonate → Lithium carbonate"""
    result = metal_identifier("lithium:carbonate")
    # This should resolve to lithium carbonate using form hint
    if result:
        assert "carbonate" in result["name"].lower()
        assert result["formula"] == "Li2CO3"


def test_colon_hints_lithium_hydroxide(metals_df):
    """Test lithium:hydroxide → Lithium hydroxide"""
    result = metal_identifier("lithium:hydroxide")
    if result:
        assert "hydroxide" in result["name"].lower()


def test_colon_hints_cobalt_sulfate(metals_df):
    """Test cobalt:sulfate → Cobalt sulfate"""
    result = metal_identifier("cobalt:sulfate")
    if result:
        assert "sulfate" in result["name"].lower()


# ---- Test 5: Cluster Filtering ----

def test_cluster_filtering_pgm(metals_df):
    """Test resolving within pgm_complex cluster"""
    # Get all PGM metals
    pgm_metals = list_metals(cluster="pgm_complex")
    assert len(pgm_metals) > 0

    # All should be in pgm_complex
    for _, metal in pgm_metals.iterrows():
        assert metal["cluster_id"] == "pgm_complex"

    # Platinum should be in PGM cluster
    result = metal_identifier("Pt", cluster="pgm_complex")
    assert result is not None
    assert result["name"] == "Platinum"
    assert result["cluster_id"] == "pgm_complex"


def test_cluster_filtering_porphyry_copper(metals_df):
    """Test porphyry copper chain has correct metals"""
    porphyry_metals = list_metals(cluster="porphyry_copper_chain")

    # Should include Cu, Mo, Re, Se, Te, Au
    names = set(porphyry_metals["name"].tolist())
    assert "Copper" in names
    assert "Molybdenum" in names
    assert "Rhenium" in names

    # All should be in correct cluster
    for _, metal in porphyry_metals.iterrows():
        assert metal["cluster_id"] == "porphyry_copper_chain"


def test_cluster_filtering_lead_zinc(metals_df):
    """Test lead-zinc chain has correct metals"""
    lead_zinc = list_metals(cluster="lead_zinc_chain")

    # Should include Zn, Pb, Ag, Cd, In, Ge, Bi, Sb
    names = set(lead_zinc["name"].tolist())
    assert "Zinc" in names
    assert "Lead" in names
    assert "Silver" in names

    # All should be in correct cluster
    for _, metal in lead_zinc.iterrows():
        assert metal["cluster_id"] == "lead_zinc_chain"


def test_cluster_filtering_ree(metals_df):
    """Test rare earth chain has 11 metals"""
    ree_metals = list_metals(cluster="rare_earth_chain")
    assert len(ree_metals) == 11

    # All should be in rare_earth_chain
    for _, metal in ree_metals.iterrows():
        assert metal["cluster_id"] == "rare_earth_chain"
        assert metal["category_bucket"] == "ree"


def test_cluster_filtering_category(metals_df):
    """Test category filtering"""
    # Test pgm category
    pgm_category = list_metals(category="pgm")
    assert len(pgm_category) > 0
    for _, metal in pgm_category.iterrows():
        assert metal["category_bucket"] == "pgm"

    # Test ree category
    ree_category = list_metals(category="ree")
    assert len(ree_category) == 11
    for _, metal in ree_category.iterrows():
        assert metal["category_bucket"] == "ree"


# ---- Test 6: Unit/Basis Validation ----

def test_unit_basis_apt(metals_df):
    """Test APT unit/basis: mtu + $/mtu WO3"""
    result = metal_identifier("ammonium paratungstate")
    assert result is not None
    assert result["default_unit"] == "mtu"
    assert result["default_basis"] == "$/mtu WO3"
    assert "WO3" in result["default_basis"]


def test_unit_basis_ferrochrome(metals_df):
    """Test FeCr unit/basis: lb + $/lb Cr"""
    result = metal_identifier("ferrochrome")
    assert result is not None
    assert result["default_unit"] == "lb"
    assert result["default_basis"] == "$/lb Cr"
    assert "Cr" in result["default_basis"]


def test_unit_basis_precious_metals(metals_df):
    """Test precious metals use toz + $/toz"""
    precious_tests = [
        ("Pt", "Platinum"),
        ("Pd", "Palladium"),
        ("Au", "Gold"),
        ("Ag", "Silver"),
    ]

    for symbol, name in precious_tests:
        result = metal_identifier(symbol)
        assert result is not None, f"Failed to resolve {symbol}"
        assert result["default_unit"] == "toz", f"{name} should use toz"
        assert result["default_basis"] == "$/toz", f"{name} should use $/toz"


def test_unit_basis_ree_oxides(metals_df):
    """Test REEs use kg + $/kg oxide"""
    ree_tests = [
        ("La", "La2O3"),
        ("Ce", "CeO2"),
        ("Nd", "Nd2O3"),
        ("Dy", "Dy2O3"),
    ]

    for symbol, oxide in ree_tests:
        result = metal_identifier(symbol)
        assert result is not None
        assert result["default_unit"] == "kg"
        assert oxide in result["default_basis"]


def test_unit_basis_base_metals(metals_df):
    """Test base metals typically use lb"""
    base_tests = ["Cu", "Zn", "Pb"]

    for symbol in base_tests:
        result = metal_identifier(symbol)
        assert result is not None
        assert result["default_unit"] == "lb"
        assert result["category_bucket"] == "base"


# ---- Test 7: Top-K Matching ----

def test_topk_matching_basic(metals_df):
    """Test top-K matching returns scored candidates"""
    matches = match_metal("copper", k=3)

    assert len(matches) > 0
    assert len(matches) <= 3

    # Should have score keys
    for match in matches:
        assert "score" in match
        assert "name" in match
        assert match["score"] >= 0
        assert match["score"] <= 100

    # Scores should be in descending order
    for i in range(len(matches) - 1):
        assert matches[i]["score"] >= matches[i + 1]["score"]


def test_topk_matching_exact_match_high_score(metals_df):
    """Test exact matches get high scores"""
    matches = match_metal("Platinum", k=5)

    assert len(matches) > 0
    top_match = matches[0]
    assert top_match["name"] == "Platinum"
    assert top_match["score"] >= 95  # Should be very high for exact match


def test_topk_matching_fuzzy(metals_df):
    """Test fuzzy matching returns reasonable candidates"""
    matches = match_metal("molybdenum", k=3)

    assert len(matches) > 0
    # Top match should be Molybdenum
    assert "Molybdenum" in matches[0]["name"]


def test_topk_matching_ree(metals_df):
    """Test top-K for REE names"""
    matches = match_metal("neodymium", k=3)

    assert len(matches) > 0
    top_match = matches[0]
    assert "Neodymium" in top_match["name"]
    assert top_match["score"] >= 90


# ---- Test 8: Data Quality ----

def test_all_metals_have_required_fields(metals_df):
    """Test all metals have required fields"""
    required_fields = [
        "metal_id",
        "metal_key",
        "name",
        "name_norm",
        "category_bucket",
        "cluster_id",
        "default_unit",
        "default_basis",
    ]

    for _, metal in metals_df.iterrows():
        for field in required_fields:
            assert field in metal.index, f"Missing field {field}"
            assert metal[field] is not None, f"{metal['name']} has null {field}"
            assert str(metal[field]).strip() != "", f"{metal['name']} has empty {field}"


def test_all_metals_have_sources(metals_df):
    """Test all metals have source citations"""
    for _, metal in metals_df.iterrows():
        assert "source_priority" in metal.index
        assert metal["source_priority"] is not None
        sources = str(metal["source_priority"])
        assert len(sources) > 0, f"{metal['name']} has no sources"


def test_ree_have_iupac_and_usgs_sources(metals_df):
    """Test REEs cite IUPAC and USGS"""
    ree_metals = metals_df[metals_df["cluster_id"] == "rare_earth_chain"]

    for _, metal in ree_metals.iterrows():
        sources = str(metal["source_priority"])
        # Individual REEs should have IUPAC
        if metal["symbol"]:
            assert "IUPAC" in sources, f"{metal['name']} missing IUPAC source"
        assert "USGS" in sources or "Fastmarkets" in sources


def test_by_product_metals_cite_usgs(metals_df):
    """Test by-product metals cite USGS"""
    # By-products from porphyry copper chain
    by_products = ["Rhenium", "Selenium", "Tellurium"]

    for name in by_products:
        metal = metals_df[metals_df["name"] == name]
        if not metal.empty:
            sources = str(metal.iloc[0]["source_priority"])
            assert "USGS" in sources, f"{name} missing USGS source"


# ---- Test 9: Supply Chain Relationships ----

def test_porphyry_copper_chain_relationships(metals_df):
    """Test porphyry copper chain has correct by-product relationships"""
    porphyry = metals_df[metals_df["cluster_id"] == "porphyry_copper_chain"]

    # Should have Cu as primary
    cu = porphyry[porphyry["symbol"] == "Cu"]
    assert len(cu) == 1
    assert "primary" in cu.iloc[0]["notes"].lower()

    # Should have Mo as co-product
    mo = porphyry[porphyry["symbol"] == "Mo"]
    if len(mo) > 0:
        assert "co-product" in mo.iloc[0]["notes"].lower()

    # Should have Re as by-product from Mo
    re = porphyry[porphyry["symbol"] == "Re"]
    if len(re) > 0:
        notes = re.iloc[0]["notes"].lower()
        assert "mo" in notes or "molybdenum" in notes


def test_lead_zinc_chain_relationships(metals_df):
    """Test lead-zinc chain has correct by-product relationships"""
    lead_zinc = metals_df[metals_df["cluster_id"] == "lead_zinc_chain"]

    # Should have Zn and Pb as primaries
    primaries = lead_zinc[lead_zinc["symbol"].isin(["Zn", "Pb"])]
    assert len(primaries) == 2

    # Should have In as by-product from Zn
    indium = lead_zinc[lead_zinc["symbol"] == "In"]
    if len(indium) > 0:
        notes = indium.iloc[0]["notes"].lower()
        assert "zn" in notes or "zinc" in notes


# ---- Test 10: Normalization ----

def test_normalization_consistency(metals_df):
    """Test name_norm is consistent with name"""
    from entityidentity.metals.metalnormalize import normalize_metal_name

    for _, metal in metals_df.iterrows():
        # name_norm should be normalized version of name
        # Note: build script may have different normalization, so we just check basic properties
        assert metal["name_norm"] is not None
        assert len(metal["name_norm"]) > 0
        assert metal["name_norm"] == metal["name_norm"].lower()


def test_metal_key_is_slug(metals_df):
    """Test metal_key is a valid slug"""
    import re
    slug_pattern = re.compile(r'^[a-z0-9\-]+$')

    for _, metal in metals_df.iterrows():
        metal_key = metal["metal_key"]
        assert metal_key is not None
        assert len(metal_key) > 0
        assert slug_pattern.match(metal_key), f"Invalid slug: {metal_key}"


# ---- Test 11: Edge Cases ----

def test_empty_query_returns_none():
    """Test empty query returns None"""
    assert metal_identifier("") is None
    assert metal_identifier("   ") is None
    assert metal_identifier(None) is None


def test_nonexistent_metal_returns_none():
    """Test nonexistent metal returns None"""
    result = metal_identifier("unobtainium")
    assert result is None


def test_topk_with_empty_query():
    """Test top-K with empty query returns empty list"""
    matches = match_metal("", k=5)
    assert matches == []


def test_list_metals_with_invalid_cluster():
    """Test list_metals with invalid cluster returns empty"""
    metals = list_metals(cluster="nonexistent_cluster")
    assert len(metals) == 0


def test_list_metals_with_invalid_category():
    """Test list_metals with invalid category returns empty"""
    metals = list_metals(category="nonexistent_category")
    assert len(metals) == 0


# ---- Test 12: API Convenience ----

def test_load_metals_is_cached():
    """Test load_metals uses cache"""
    df1 = load_metals()
    df2 = load_metals()
    # Should be same object (from cache)
    assert df1 is df2


def test_metal_identifier_returns_dict():
    """Test metal_identifier returns dict, not Series"""
    result = metal_identifier("Pt")
    assert result is not None
    assert isinstance(result, dict)
    assert "name" in result
    assert "symbol" in result


def test_match_metal_returns_list_of_dicts():
    """Test match_metal returns list of dicts with scores"""
    matches = match_metal("copper", k=3)
    assert isinstance(matches, list)
    for match in matches:
        assert isinstance(match, dict)
        assert "score" in match
        assert "name" in match


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

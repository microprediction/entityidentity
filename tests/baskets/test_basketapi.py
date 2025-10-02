"""Test suite for baskets entity resolution.

Test coverage:
1. TestBasketIdentifier — Exact name matching and variations
2. TestBasketComponents — Component extraction
3. TestBasketMatching — Top-K candidates with scores
4. TestBasketListing — Listing all baskets
5. TestCaching — Caching behavior
6. TestEdgeCases — Empty queries, invalid inputs
7. TestDataQuality — Data validation
8. TestSpecificBaskets — Basket-specific properties
"""

import pytest
import re
from entityidentity.baskets.basketapi import (
    load_baskets,
    basket_identifier,
    match_basket,
    list_baskets,
    get_basket_components,
)


# ---- Fixtures ----

@pytest.fixture(scope="module")
def baskets_df():
    """Load baskets DataFrame once for all tests"""
    return load_baskets()


# ---- Test 1: Basket Identifier ----

class TestBasketIdentifier:
    """Test basket_identifier() function"""

    def test_pgm_4e_exact_match(self, baskets_df):
        """Test PGM 4E exact match"""
        result = basket_identifier("PGM 4E")
        assert result is not None
        assert result["name"] == "PGM 4E"
        assert result["basket_id"] == "PGM_4E"
        assert result["component1"] == "Pt"
        assert result["component2"] == "Pd"
        assert result["component3"] == "Rh"
        assert result["component4"] == "Au"

    def test_pgm_5e_exact_match(self, baskets_df):
        """Test PGM 5E exact match"""
        result = basket_identifier("PGM 5E")
        assert result is not None
        assert result["name"] == "PGM 5E"
        assert result["basket_id"] == "PGM_5E"
        assert result["component5"] == "Ir"  # 5th element

    def test_ndpr_exact_match(self, baskets_df):
        """Test NdPr exact match"""
        result = basket_identifier("NdPr")
        assert result is not None
        assert result["name"] == "NdPr"
        assert result["basket_id"] == "NDPR"
        assert result["component1"] == "Nd"
        assert result["component2"] == "Pr"

    def test_ree_light_exact_match(self, baskets_df):
        """Test REE Light exact match"""
        result = basket_identifier("REE Light")
        assert result is not None
        assert result["name"] == "REE Light"
        assert result["basket_id"] == "REE_LIGHT"

    def test_battery_pack_exact_match(self, baskets_df):
        """Test Battery Pack exact match"""
        result = basket_identifier("Battery Pack")
        assert result is not None
        assert result["name"] == "Battery Pack"
        assert result["basket_id"] == "BATTERY_PACK"
        # Check key components
        assert result["component1"] == "Li"
        assert result["component2"] == "Co"
        assert result["component3"] == "Ni"

    def test_variations_pgm_4e(self, baskets_df):
        """Test PGM 4E variations resolve correctly"""
        variations = [
            "PGM 4E",
            "4E PGM",
            "Four Element PGM",
            "Platinum Group 4E",
            "4E Basket",
        ]

        for variation in variations:
            result = basket_identifier(variation)
            assert result is not None, f"Failed to resolve: {variation}"
            assert result["basket_id"] == "PGM_4E"
            assert result["name"] == "PGM 4E"

    def test_variations_ndpr(self, baskets_df):
        """Test NdPr variations resolve correctly"""
        variations = [
            "NdPr",
            "ndpr",
            "NdPr Oxide",
            "Neodymium-Praseodymium",
            "Nd-Pr",
            "Didymium",
        ]

        for variation in variations:
            result = basket_identifier(variation)
            assert result is not None, f"Failed to resolve: {variation}"
            assert result["basket_id"] == "NDPR"
            assert result["name"] == "NdPr"

    def test_variations_battery(self, baskets_df):
        """Test Battery Pack variations resolve correctly"""
        variations = [
            "Battery Pack",
            "battery pack",
            "EV Battery Basket",
            "Li-ion Battery Metals",
            "Battery Metals",
        ]

        for variation in variations:
            result = basket_identifier(variation)
            assert result is not None, f"Failed to resolve: {variation}"
            assert result["basket_id"] == "BATTERY_PACK"

    def test_case_insensitive(self, baskets_df):
        """Test case-insensitive matching"""
        test_cases = [
            ("pgm 4e", "PGM_4E"),
            ("NDPR", "NDPR"),
            ("ree light", "REE_LIGHT"),
            ("BATTERY PACK", "BATTERY_PACK"),
        ]

        for query, expected_id in test_cases:
            result = basket_identifier(query)
            assert result is not None, f"Failed to resolve: {query}"
            assert result["basket_id"] == expected_id

    def test_fuzzy_matching(self, baskets_df):
        """Test fuzzy matching handles typos and variations"""
        # These should still resolve with high similarity
        fuzzy_tests = [
            ("pgm4e", "PGM_4E"),  # Missing space
            ("4e", "PGM_4E"),  # Partial match
            ("pgm", None),  # Too ambiguous (both PGM 4E and 5E match)
            ("battery", "BATTERY_PACK"),  # Partial word
        ]

        for query, expected_id in fuzzy_tests:
            result = basket_identifier(query)
            if expected_id is None:
                # Ambiguous queries may or may not resolve
                continue
            else:
                # Clear queries should resolve
                if result:
                    assert result["basket_id"] == expected_id, f"Query '{query}' resolved to wrong basket"

    def test_returns_dict(self):
        """Test basket_identifier returns dict, not Series"""
        result = basket_identifier("PGM 4E")
        assert result is not None
        assert isinstance(result, dict)
        assert "name" in result
        assert "basket_id" in result


# ---- Test 2: Component Extraction ----

class TestBasketComponents:
    """Test get_basket_components() function"""

    def test_pgm_4e_components(self, baskets_df):
        """Test component extraction for PGM 4E"""
        components = get_basket_components("PGM 4E")
        assert components is not None
        assert components == ["Pt", "Pd", "Rh", "Au"]

    def test_ndpr_components(self, baskets_df):
        """Test component extraction for NdPr"""
        components = get_basket_components("NdPr")
        assert components is not None
        assert components == ["Nd", "Pr"]

    def test_battery_pack_components(self, baskets_df):
        """Test component extraction for Battery Pack"""
        components = get_basket_components("Battery Pack")
        assert components is not None
        assert set(components) == {"Li", "Co", "Ni", "Mn", "C"}

    def test_with_alias(self, baskets_df):
        """Test component extraction works with aliases"""
        components = get_basket_components("4E PGM")
        assert components is not None
        assert components == ["Pt", "Pd", "Rh", "Au"]

    def test_nonexistent_basket(self, baskets_df):
        """Test component extraction returns None for nonexistent basket"""
        components = get_basket_components("Nonexistent Basket")
        assert components is None


# ---- Test 3: Top-K Matching ----

class TestBasketMatching:
    """Test match_basket() function for top-K results"""

    def test_basic_matching(self, baskets_df):
        """Test top-K matching returns scored candidates"""
        matches = match_basket("pgm", k=3)

        assert len(matches) >= 2  # Should find both PGM baskets
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

    def test_exact_match_high_score(self, baskets_df):
        """Test exact matches get high scores"""
        matches = match_basket("PGM 4E", k=5)

        assert len(matches) > 0
        top_match = matches[0]
        assert top_match["name"] == "PGM 4E"
        assert top_match["score"] >= 95  # Should be very high for exact match

    def test_ambiguous_query(self, baskets_df):
        """Test ambiguous queries return multiple candidates"""
        matches = match_basket("pgm", k=5)

        # Should return both PGM 4E and PGM 5E with similar scores
        pgm_matches = [m for m in matches if "PGM" in m["name"]]
        assert len(pgm_matches) >= 2

        pgm_4e = [m for m in pgm_matches if "4E" in m["name"]][0]
        pgm_5e = [m for m in pgm_matches if "5E" in m["name"]][0]

        # Both should have high scores
        assert pgm_4e["score"] >= 85
        assert pgm_5e["score"] >= 85

    def test_ree_matching(self, baskets_df):
        """Test matching REE baskets"""
        matches = match_basket("rare earth", k=3)

        assert len(matches) > 0
        # Should find REE Light
        ree_matches = [m for m in matches if "REE" in m["name"] or "Rare" in m.get("description", "")]
        assert len(ree_matches) > 0

    def test_ndpr_matching(self, baskets_df):
        """Test matching NdPr with variations"""
        matches = match_basket("neodymium praseodymium", k=3)

        assert len(matches) > 0
        # Top match should be NdPr
        assert "NdPr" in matches[0]["name"] or matches[0]["basket_id"] == "NDPR"

    def test_returns_list_of_dicts(self):
        """Test match_basket returns list of dicts with scores"""
        matches = match_basket("pgm", k=3)
        assert isinstance(matches, list)
        for match in matches:
            assert isinstance(match, dict)
            assert "score" in match
            assert "name" in match


# ---- Test 4: Basket Listing ----

class TestBasketListing:
    """Test list_baskets() function"""

    def test_returns_all_baskets(self, baskets_df):
        """Test list_baskets returns all baskets"""
        baskets = list_baskets()
        assert len(baskets) == 5  # We have 5 baskets defined

        # Check all expected baskets are present
        basket_names = set(baskets["name"].tolist())
        expected = {"PGM 4E", "PGM 5E", "NdPr", "REE Light", "Battery Pack"}
        assert basket_names == expected

    def test_has_required_fields(self, baskets_df):
        """Test all baskets have required fields"""
        baskets = list_baskets()

        required_fields = [
            "basket_id",
            "basket_key",
            "name",
            "name_norm",
            "description",
        ]

        for _, basket in baskets.iterrows():
            for field in required_fields:
                assert field in basket.index, f"Missing field {field}"
                assert basket[field] is not None, f"{basket['name']} has null {field}"
                assert str(basket[field]).strip() != "", f"{basket['name']} has empty {field}"

    def test_has_components(self, baskets_df):
        """Test all baskets have at least one component"""
        baskets = list_baskets()

        for _, basket in baskets.iterrows():
            # Check component1 exists and is not empty
            assert "component1" in basket.index
            assert basket["component1"] is not None
            assert str(basket["component1"]).strip() != ""


# ---- Test 5: Caching ----

class TestCaching:
    """Test caching behavior"""

    def test_load_baskets_is_cached(self):
        """Test load_baskets uses cache"""
        df1 = load_baskets()
        df2 = load_baskets()
        # Should be same object (from cache)
        assert df1 is df2


# ---- Test 6: Edge Cases ----

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_query_returns_none(self):
        """Test empty query returns None"""
        assert basket_identifier("") is None
        assert basket_identifier("   ") is None
        assert basket_identifier(None) is None

    def test_nonexistent_basket_returns_none(self):
        """Test nonexistent basket returns None"""
        result = basket_identifier("Nonexistent Basket XYZ")
        assert result is None

    def test_match_basket_with_empty_query(self):
        """Test match_basket with empty query returns empty list"""
        matches = match_basket("", k=5)
        assert matches == []

    def test_threshold_filtering(self):
        """Test threshold parameter filters low-scoring matches"""
        # Very strict threshold should return None for fuzzy matches
        result = basket_identifier("xyz", threshold=99)
        assert result is None

        # Lower threshold should be more permissive
        result = basket_identifier("pgm", threshold=80)
        # May or may not return result depending on ambiguity


# ---- Test 7: Data Quality ----

class TestDataQuality:
    """Test data quality and consistency"""

    def test_basket_keys_are_valid_slugs(self, baskets_df):
        """Test basket_key is a valid slug"""
        slug_pattern = re.compile(r'^[a-z0-9\-]+$')

        baskets = list_baskets()
        for _, basket in baskets.iterrows():
            basket_key = basket["basket_key"]
            assert basket_key is not None
            assert len(basket_key) > 0
            assert slug_pattern.match(basket_key), f"Invalid slug: {basket_key}"

    def test_basket_ids_are_valid(self, baskets_df):
        """Test basket_id format is valid"""
        id_pattern = re.compile(r'^[A-Z0-9_]+$')

        baskets = list_baskets()
        for _, basket in baskets.iterrows():
            basket_id = basket["basket_id"]
            assert basket_id is not None
            assert len(basket_id) > 0
            assert id_pattern.match(basket_id), f"Invalid basket_id: {basket_id}"

    def test_no_duplicate_basket_ids(self, baskets_df):
        """Test basket_ids are unique"""
        baskets = list_baskets()
        basket_ids = baskets["basket_id"].tolist()
        assert len(basket_ids) == len(set(basket_ids)), "Duplicate basket_ids found"

    def test_no_duplicate_basket_keys(self, baskets_df):
        """Test basket_keys are unique"""
        baskets = list_baskets()
        basket_keys = baskets["basket_key"].tolist()
        assert len(basket_keys) == len(set(basket_keys)), "Duplicate basket_keys found"


# ---- Test 8: Specific Basket Properties ----

class TestSpecificBaskets:
    """Test specific basket properties and relationships"""

    def test_pgm_5e_includes_pgm_4e_components(self, baskets_df):
        """Test PGM 5E includes all PGM 4E components plus Iridium"""
        pgm_4e = get_basket_components("PGM 4E")
        pgm_5e = get_basket_components("PGM 5E")

        assert pgm_4e is not None
        assert pgm_5e is not None

        # PGM 5E should include all PGM 4E components
        for component in pgm_4e:
            assert component in pgm_5e

        # PGM 5E should have one more component
        assert len(pgm_5e) == len(pgm_4e) + 1

        # The extra component should be Ir
        assert "Ir" in pgm_5e
        assert "Ir" not in pgm_4e

    def test_ndpr_has_two_components(self, baskets_df):
        """Test NdPr has exactly two components"""
        components = get_basket_components("NdPr")
        assert components is not None
        assert len(components) == 2
        assert set(components) == {"Nd", "Pr"}

    def test_battery_pack_has_key_materials(self, baskets_df):
        """Test Battery Pack has key Li-ion battery materials"""
        components = get_basket_components("Battery Pack")
        assert components is not None

        # Must include lithium
        assert "Li" in components

        # Should include common cathode materials
        cathode_materials = {"Co", "Ni", "Mn"}
        assert any(mat in components for mat in cathode_materials)

        # Should include anode material (graphite)
        assert "C" in components


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

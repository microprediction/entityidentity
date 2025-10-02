"""Tests for units API."""

import pytest
from entityidentity.units import normalize_unit, get_canonical_unit, validate_conversion_inputs


class TestFeCrConversion:
    """Test FeCr (Ferrochrome) conversion."""

    def test_fecr_complete_parameters_metric_ton(self):
        """FeCr with complete parameters (metric ton) converts correctly."""
        result = normalize_unit({
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 65.0},
            "ton_system": "metric",
            "material": "FeCr"
        })

        assert result["norm"]["value"] == pytest.approx(1.5, rel=0.01)
        assert result["norm"]["unit"] == "USD/lb"
        assert result["norm"]["basis"] == "Cr contained"
        assert result["warning"] is None

    def test_fecr_complete_parameters_short_ton(self):
        """FeCr with short ton system."""
        result = normalize_unit({
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 65.0},
            "ton_system": "short",
            "material": "FeCr"
        })

        # $2150 / 0.65 = $3307.69/t Cr
        # $3307.69 / 2000 = $1.654/lb Cr
        assert result["norm"]["value"] == pytest.approx(1.654, rel=0.01)
        assert result["norm"]["unit"] == "USD/lb"
        assert result["warning"] is None

    def test_fecr_missing_grade(self):
        """FeCr without grade warns and preserves raw."""
        result = normalize_unit({
            "value": 2150,
            "unit": "USD/t alloy",
            "ton_system": "metric",
            "material": "FeCr"
        })

        assert result["norm"]["value"] == 2150  # Raw preserved
        assert result["warning"] is not None
        assert "Cr_pct" in result["warning"]

    def test_fecr_missing_ton_system(self):
        """FeCr without ton_system warns."""
        result = normalize_unit({
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 65.0},
            "material": "FeCr"
        })

        assert result["norm"]["value"] == 2150  # Raw preserved
        assert result["warning"] is not None
        assert "ton_system" in result["warning"]

    def test_fecr_already_canonical(self):
        """FeCr already in canonical form ($/lb Cr)."""
        result = normalize_unit({
            "value": 1.5,
            "unit": "USD/lb Cr",
            "grade": {"Cr_pct": 65.0},
            "ton_system": "metric",
            "material": "FeCr"
        })

        assert result["norm"]["value"] == 1.5
        assert result["warning"] is None


class TestAPTConversion:
    """Test APT (Ammonium Paratungstate) conversion."""

    def test_apt_complete_parameters(self):
        """APT with complete parameters converts correctly."""
        result = normalize_unit({
            "value": 450,
            "unit": "USD/t APT",
            "grade": {"WO3_pct": 88.5},
            "material": "APT"
        })

        # $450 * 0.885 = $398.25/t WO3
        # $398.25 / 10 = $39.825/mtu WO3
        assert result["norm"]["value"] == pytest.approx(39.825, rel=0.01)
        assert result["norm"]["unit"] == "USD/mtu WO3"
        assert result["norm"]["basis"] == "WO3 basis"
        assert result["warning"] is None

    def test_apt_missing_grade(self):
        """APT without grade warns and preserves raw."""
        result = normalize_unit({
            "value": 450,
            "unit": "USD/t APT",
            "material": "APT"
        })

        assert result["norm"]["value"] == 450  # Raw preserved
        assert result["warning"] is not None
        assert "WO3_pct" in result["warning"]

    def test_apt_already_canonical(self):
        """APT already in canonical form ($/mtu WO3)."""
        result = normalize_unit({
            "value": 39.825,
            "unit": "USD/mtu WO3",
            "grade": {"WO3_pct": 88.5},
            "material": "APT"
        })

        assert result["norm"]["value"] == 39.825
        assert result["warning"] is None


class TestSimpleMetals:
    """Test simple metals (Cu, Ni, Au, etc.)."""

    def test_copper_ton_to_lb(self):
        """Copper: $/t -> $/lb conversion."""
        result = normalize_unit({
            "value": 9000,
            "unit": "USD/t",
            "material": "Copper"
        })

        # $9000 / 2204.62 = $4.08/lb
        assert result["norm"]["value"] == pytest.approx(4.08, rel=0.01)
        assert result["norm"]["unit"] == "USD/lb"
        assert result["warning"] is not None  # Warns about assumed metric ton

    def test_copper_kg_to_lb(self):
        """Copper: $/kg -> $/lb conversion."""
        result = normalize_unit({
            "value": 10,
            "unit": "USD/kg",
            "material": "Copper"
        })

        # $10 / 2.20462 = $4.54/lb
        assert result["norm"]["value"] == pytest.approx(4.54, rel=0.01)
        assert result["norm"]["unit"] == "USD/lb"

    def test_gold_troy_oz(self):
        """Gold: troy ounce (no conversion needed)."""
        result = normalize_unit({
            "value": 2000,
            "unit": "USD/oz",
            "material": "Gold"
        })

        assert result["norm"]["value"] == 2000
        assert result["norm"]["unit"] == "USD/oz"
        assert result["norm"]["basis"] == "Gold contained"


class TestRawPreservation:
    """Test that raw input is always preserved."""

    def test_raw_always_included(self):
        """Raw input always included in response."""
        raw_input = {
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 65.0},
            "ton_system": "metric",
            "material": "FeCr"
        }

        result = normalize_unit(raw_input)

        assert "raw" in result
        assert result["raw"]["value"] == 2150
        assert result["raw"]["unit"] == "USD/t alloy"
        assert result["raw"]["grade"]["Cr_pct"] == 65.0

    def test_raw_preserved_on_error(self):
        """Raw preserved even when conversion fails."""
        raw_input = {
            "value": 450,
            "unit": "USD/t APT",
            "material": "APT"
        }

        result = normalize_unit(raw_input)

        # Raw values are preserved (though may have None fields added)
        assert result["raw"]["value"] == 450
        assert result["raw"]["unit"] == "USD/t APT"
        assert result["norm"]["value"] == 450  # Unchanged


class TestGetCanonicalUnit:
    """Test get_canonical_unit function."""

    def test_fecr_canonical(self):
        """Get FeCr canonical unit info."""
        info = get_canonical_unit("FeCr")

        assert info["canonical_unit"] == "USD/lb"
        assert info["canonical_basis"] == "Cr contained"
        assert "Cr_pct" in info["requires"]
        assert "ton_system" in info["requires"]

    def test_apt_canonical(self):
        """Get APT canonical unit info."""
        info = get_canonical_unit("APT")

        assert info["canonical_unit"] == "USD/mtu WO3"
        assert info["canonical_basis"] == "WO3 basis"
        assert "WO3_pct" in info["requires"]

    def test_copper_canonical(self):
        """Get Copper canonical unit info."""
        info = get_canonical_unit("Copper")

        assert info["canonical_unit"] == "USD/lb"
        assert info["canonical_basis"] == "Cu contained"
        assert len(info["requires"]) == 0  # No special requirements


class TestValidateConversionInputs:
    """Test validate_conversion_inputs function."""

    def test_fecr_valid_inputs(self):
        """FeCr with all required parameters."""
        validation = validate_conversion_inputs("FeCr", {
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 65.0},
            "ton_system": "metric"
        })

        assert validation["valid"] is True
        assert len(validation["missing"]) == 0

    def test_fecr_missing_grade(self):
        """FeCr missing Cr_pct."""
        validation = validate_conversion_inputs("FeCr", {
            "value": 2150,
            "unit": "USD/t alloy",
            "ton_system": "metric"
        })

        assert validation["valid"] is False
        assert "Cr_pct" in validation["missing"]

    def test_fecr_missing_ton_system(self):
        """FeCr missing ton_system."""
        validation = validate_conversion_inputs("FeCr", {
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 65.0}
        })

        assert validation["valid"] is False
        assert "ton_system" in validation["missing"]

    def test_copper_no_requirements(self):
        """Copper has no special requirements."""
        validation = validate_conversion_inputs("Copper", {
            "value": 9000,
            "unit": "USD/t"
        })

        assert validation["valid"] is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_cr_pct(self):
        """Invalid Cr percentage."""
        result = normalize_unit({
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 150},  # Invalid: > 100%
            "ton_system": "metric",
            "material": "FeCr"
        })

        assert result["warning"] is not None
        assert "Invalid Cr_pct" in result["warning"]

    def test_zero_cr_pct(self):
        """Zero Cr percentage."""
        result = normalize_unit({
            "value": 2150,
            "unit": "USD/t alloy",
            "grade": {"Cr_pct": 0},
            "ton_system": "metric",
            "material": "FeCr"
        })

        assert result["warning"] is not None

    def test_unknown_material(self):
        """Unknown material."""
        result = normalize_unit({
            "value": 1000,
            "unit": "USD/t",
            "material": "Unobtanium"
        })

        assert result["warning"] is not None
        assert "No conversion rule" in result["warning"]

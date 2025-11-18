"""Comprehensive tests for catalog cross-matching.

Tests cover:
- Unit tests for individual functions
- Smoke tests for basic functionality
- Integration tests for complete workflows
- Edge cases and boundary conditions
- Error handling and robustness
"""

import numpy as np
import pytest
from astropy.table import Table

from dsa110_contimg.database.catalog_crossmatch_astropy import (
    CATALOG_INFO,
    DEFAULT_SPECTRAL_INDEX,
    DSA110_FREQUENCY_MHZ,
    MatchedSource,
    RadioCatalogMatcher,
    create_mock_catalog,
)


class TestCatalogInfo:
    """Test catalog metadata and constants."""

    def test_all_catalogs_have_required_fields(self):
        """Verify all catalogs have required metadata."""
        required = ["frequency_mhz", "position_error_arcsec", "flux_type", "reference"]
        for cat_name, info in CATALOG_INFO.items():
            for field in required:
                assert field in info, f"Missing {field} in {cat_name}"
                assert info[field] is not None

    def test_catalog_frequencies_positive(self):
        """Verify all frequencies are positive."""
        for cat_name, info in CATALOG_INFO.items():
            assert info["frequency_mhz"] > 0

    def test_position_errors_positive(self):
        """Verify all position errors are positive."""
        for cat_name, info in CATALOG_INFO.items():
            assert info["position_error_arcsec"] > 0

    def test_dsa110_frequency_constant(self):
        """Verify DSA-110 frequency is correct."""
        assert DSA110_FREQUENCY_MHZ == 1405.0

    def test_default_spectral_index(self):
        """Verify default spectral index is reasonable."""
        assert -2.0 < DEFAULT_SPECTRAL_INDEX < 0.0


class TestFluxExtrapolation:
    """Test flux extrapolation edge cases."""

    def test_same_frequency_no_change(self):
        """Flux should not change if frequencies are the same."""
        matcher = RadioCatalogMatcher()
        flux = matcher.extrapolate_flux(10.0, 1400, 1400, -0.7)
        assert flux == 10.0

    def test_extrapolation_symmetry(self):
        """Forward and backward extrapolation should be symmetric."""
        matcher = RadioCatalogMatcher()
        flux_orig = 5.0
        flux_target = matcher.extrapolate_flux(flux_orig, 1400, 887.5, -0.7)
        flux_back = matcher.extrapolate_flux(flux_target, 887.5, 1400, -0.7)
        assert abs(flux_back - flux_orig) < 1e-10

    def test_negative_spectral_index_increases_flux(self):
        """Negative spectral index should increase flux at lower frequency."""
        matcher = RadioCatalogMatcher()
        flux_high = matcher.extrapolate_flux(1.0, 1400, 1500, -0.7)
        assert flux_high < 1.0  # Higher freq -> lower flux

        flux_low = matcher.extrapolate_flux(1.0, 1400, 1300, -0.7)
        assert flux_low > 1.0  # Lower freq -> higher flux

    def test_zero_flux_remains_zero(self):
        """Zero flux should remain zero."""
        matcher = RadioCatalogMatcher()
        flux = matcher.extrapolate_flux(0.0, 1400, 1500, -0.7)
        assert flux == 0.0

    def test_very_small_flux(self):
        """Test with very small flux values."""
        matcher = RadioCatalogMatcher()
        flux = matcher.extrapolate_flux(1e-10, 1400, 1500, -0.7)
        assert flux > 0
        assert np.isfinite(flux)

    def test_very_large_flux(self):
        """Test with very large flux values."""
        matcher = RadioCatalogMatcher()
        flux = matcher.extrapolate_flux(1e10, 1400, 1500, -0.7)
        assert flux > 0
        assert np.isfinite(flux)

    def test_extreme_spectral_index(self):
        """Test with extreme spectral indices."""
        matcher = RadioCatalogMatcher()

        # Very steep
        flux_steep = matcher.extrapolate_flux(1.0, 1400, 1500, -2.0)
        assert flux_steep > 0
        assert np.isfinite(flux_steep)

        # Very flat
        flux_flat = matcher.extrapolate_flux(1.0, 1400, 1500, -0.1)
        assert flux_flat > 0
        assert np.isfinite(flux_flat)


class TestSpectralIndexEstimation:
    """Test spectral index calculation edge cases."""

    def test_identical_fluxes(self):
        """Test with identical fluxes (flat spectrum)."""
        matcher = RadioCatalogMatcher()
        alpha, alpha_err = matcher.estimate_spectral_index(1.0, 1400, 1.0, 887.5)
        assert abs(alpha - 0.0) < 0.01  # Should be ~0
        assert alpha_err == 0.15

    def test_zero_flux_handling(self):
        """Test with zero flux."""
        matcher = RadioCatalogMatcher()
        alpha, alpha_err = matcher.estimate_spectral_index(0.0, 1400, 1.0, 887.5)
        assert alpha == DEFAULT_SPECTRAL_INDEX
        assert alpha_err == 0.3

    def test_negative_flux_handling(self):
        """Test with negative flux (error condition)."""
        matcher = RadioCatalogMatcher()
        alpha, alpha_err = matcher.estimate_spectral_index(-1.0, 1400, 1.0, 887.5)
        assert alpha == DEFAULT_SPECTRAL_INDEX
        assert alpha_err == 0.3

    def test_nan_flux_handling(self):
        """Test with NaN flux."""
        matcher = RadioCatalogMatcher()
        alpha, alpha_err = matcher.estimate_spectral_index(np.nan, 1400, 1.0, 887.5)
        assert alpha == DEFAULT_SPECTRAL_INDEX
        assert alpha_err == 0.3

    def test_inf_flux_handling(self):
        """Test with infinite flux."""
        matcher = RadioCatalogMatcher()
        alpha, alpha_err = matcher.estimate_spectral_index(np.inf, 1400, 1.0, 887.5)
        assert alpha == DEFAULT_SPECTRAL_INDEX
        assert alpha_err == 0.3


class TestPositionalMatching:
    """Test positional cross-matching edge cases."""

    def test_empty_catalog_a(self):
        """Test with empty first catalog."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": [], "ra": [], "dec": [], "flux": []})
        cat_a.meta["catalog"] = "VLA"

        cat_b = Table({"name": ["SRC1"], "ra": [100.0], "dec": [30.0], "flux": [1.0]})
        cat_b.meta["catalog"] = "NVSS"

        matches, idx, seps = matcher.match_two_catalogs(cat_a, cat_b, "VLA", "NVSS")
        assert len(matches) == 0

    def test_empty_catalog_b(self):
        """Test with empty second catalog."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": ["SRC1"], "ra": [100.0], "dec": [30.0], "flux": [1.0]})
        cat_a.meta["catalog"] = "VLA"

        cat_b = Table({"name": [], "ra": [], "dec": [], "flux": []})
        cat_b.meta["catalog"] = "NVSS"

        matches, idx, seps = matcher.match_two_catalogs(cat_a, cat_b, "VLA", "NVSS")
        assert len(matches) == 1
        assert not matches[0]  # No match
        assert np.isinf(seps[0])  # Infinite separation

    def test_both_catalogs_empty(self):
        """Test with both catalogs empty."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": [], "ra": [], "dec": [], "flux": []})
        cat_a.meta["catalog"] = "VLA"

        cat_b = Table({"name": [], "ra": [], "dec": [], "flux": []})
        cat_b.meta["catalog"] = "NVSS"

        matches, idx, seps = matcher.match_two_catalogs(cat_a, cat_b, "VLA", "NVSS")
        assert len(matches) == 0
        assert len(idx) == 0
        assert len(seps) == 0

    def test_exact_position_match(self):
        """Test with exactly matching positions."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": ["SRC1"], "ra": [100.0], "dec": [30.0], "flux": [1.0]})
        cat_a.meta["catalog"] = "VLA"

        cat_b = Table({"name": ["SRC1"], "ra": [100.0], "dec": [30.0], "flux": [1.0]})
        cat_b.meta["catalog"] = "FIRST"

        matches, idx, seps = matcher.match_two_catalogs(cat_a, cat_b, "VLA", "FIRST")
        assert matches[0]
        assert seps[0] < 1e-10  # Effectively zero

    def test_boundary_ra_0_360(self):
        """Test with RA near 0/360 boundary."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": ["SRC1"], "ra": [0.0001], "dec": [30.0], "flux": [1.0]})
        cat_a.meta["catalog"] = "VLA"

        cat_b = Table({"name": ["SRC1"], "ra": [359.9999], "dec": [30.0], "flux": [1.0]})
        cat_b.meta["catalog"] = "FIRST"

        matches, idx, seps = matcher.match_two_catalogs(cat_a, cat_b, "VLA", "FIRST")
        # Should match (very close across RA=0, ~0.36" separation)
        assert matches[0]
        assert seps[0] < 1.0  # Less than 1 arcsec

    def test_pole_matching(self):
        """Test matching near poles."""
        matcher = RadioCatalogMatcher()
        # Sources very close to pole with small RA difference
        cat_a = Table({"name": ["NP"], "ra": [100.0], "dec": [89.99], "flux": [1.0]})
        cat_a.meta["catalog"] = "VLA"

        cat_b = Table({"name": ["NP"], "ra": [101.0], "dec": [89.99], "flux": [1.0]})
        cat_b.meta["catalog"] = "FIRST"

        matches, idx, seps = matcher.match_two_catalogs(cat_a, cat_b, "VLA", "FIRST")
        # At 89.99° dec, 1° RA diff = ~0.6" separation
        # Threshold is 3×sqrt(1²+1²) = 4.2"
        # So this should match
        assert matches[0]
        assert seps[0] < 4.2  # Within threshold


class TestConeSearch:
    """Test cone search edge cases."""

    def test_empty_catalog(self):
        """Test cone search on empty catalog."""
        matcher = RadioCatalogMatcher()
        cat = Table({"name": [], "ra": [], "dec": [], "flux": []})
        result = matcher.cone_search(cat, 100.0, 30.0, 1.0)
        assert len(result) == 0

    def test_zero_radius(self):
        """Test with zero search radius."""
        matcher = RadioCatalogMatcher()
        cat = Table(
            {
                "name": ["SRC1", "SRC2"],
                "ra": [100.0, 100.1],
                "dec": [30.0, 30.1],
                "flux": [1.0, 1.0],
            }
        )
        result = matcher.cone_search(cat, 100.0, 30.0, 0.0)
        # Should only find exact matches
        assert len(result) <= 1

    def test_very_large_radius(self):
        """Test with very large search radius."""
        matcher = RadioCatalogMatcher()
        cat = Table(
            {
                "name": ["SRC1", "SRC2"],
                "ra": [100.0, 200.0],
                "dec": [30.0, 60.0],
                "flux": [1.0, 1.0],
            }
        )
        result = matcher.cone_search(cat, 100.0, 30.0, 180.0)
        # Should find all sources
        assert len(result) == 2

    def test_pole_cone_search(self):
        """Test cone search at pole."""
        matcher = RadioCatalogMatcher()
        cat = Table(
            {
                "name": ["NP1", "NP2"],
                "ra": [0.0, 180.0],
                "dec": [89.0, 89.0],
                "flux": [1.0, 1.0],
            }
        )
        result = matcher.cone_search(cat, 90.0, 90.0, 2.0)
        # Should find both (close to pole)
        assert len(result) == 2


class TestCatalogMerging:
    """Test catalog merging edge cases."""

    def test_merge_empty_catalogs(self):
        """Test merging two empty catalogs."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": [], "ra": [], "dec": [], "flux": []})
        cat_a.meta["catalog"] = "NVSS"

        cat_b = Table({"name": [], "ra": [], "dec": [], "flux": []})
        cat_b.meta["catalog"] = "RACS"

        merged = matcher.merge_two_catalogs(cat_a, cat_b, "NVSS", "RACS")
        assert len(merged) == 0
        assert isinstance(merged, list)

    def test_merge_one_source_each(self):
        """Test merging catalogs with one source each."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": ["A"], "ra": [100.0], "dec": [30.0], "flux": [1.5]})
        cat_a.meta["catalog"] = "NVSS"

        cat_b = Table({"name": ["B"], "ra": [100.0], "dec": [30.0], "flux": [2.1]})
        cat_b.meta["catalog"] = "RACS"

        merged = matcher.merge_two_catalogs(cat_a, cat_b, "NVSS", "RACS")
        assert len(merged) == 1
        assert merged[0].n_catalogs == 2
        assert merged[0].spectral_index is not None

    def test_merge_no_matches(self):
        """Test merging catalogs with no matches."""
        matcher = RadioCatalogMatcher()
        cat_a = Table({"name": ["A"], "ra": [100.0], "dec": [30.0], "flux": [1.0]})
        cat_a.meta["catalog"] = "NVSS"

        cat_b = Table({"name": ["B"], "ra": [200.0], "dec": [60.0], "flux": [1.0]})
        cat_b.meta["catalog"] = "RACS"

        merged = matcher.merge_two_catalogs(cat_a, cat_b, "NVSS", "RACS")
        assert len(merged) == 2
        assert all(s.n_catalogs == 1 for s in merged)

    def test_merge_multiple_matches(self):
        """Test merging with multiple matching sources."""
        matcher = RadioCatalogMatcher()
        cat_a = Table(
            {
                "name": ["A1", "A2", "A3"],
                "ra": [100.0, 150.0, 200.0],
                "dec": [30.0, 40.0, 50.0],
                "flux": [1.0, 2.0, 3.0],
            }
        )
        cat_a.meta["catalog"] = "NVSS"

        cat_b = Table(
            {
                "name": ["B1", "B2"],
                "ra": [100.0, 150.0],
                "dec": [30.0, 40.0],
                "flux": [1.0, 2.0],
            }
        )
        cat_b.meta["catalog"] = "RACS"

        merged = matcher.merge_two_catalogs(cat_a, cat_b, "NVSS", "RACS")
        assert len(merged) == 3  # 2 matched + 1 unmatched
        matched = [s for s in merged if s.n_catalogs == 2]
        assert len(matched) == 2


class TestMatchedSource:
    """Test MatchedSource dataclass."""

    def test_matched_source_creation(self):
        """Test creating a MatchedSource."""
        src = MatchedSource(
            name="TEST",
            ra_deg=100.0,
            dec_deg=30.0,
            flux_dsa110_jy=1.5,
            flux_uncertainty_jy=0.15,
            spectral_index=-0.7,
            spectral_index_error=0.15,
            n_catalogs=2,
            catalogs=["NVSS", "RACS"],
            separations_arcsec={"NVSS": 0.0, "RACS": 2.5},
            fluxes_observed={"NVSS": 1.5, "RACS": 2.1},
        )
        assert src.name == "TEST"
        assert src.n_catalogs == 2
        assert len(src.catalogs) == 2


class TestMockCatalog:
    """Test mock catalog generation."""

    def test_mock_catalog_size(self):
        """Test mock catalog has correct size."""
        cat = create_mock_catalog("TEST", n_sources=50)
        assert len(cat) == 50

    def test_mock_catalog_columns(self):
        """Test mock catalog has required columns."""
        cat = create_mock_catalog("TEST", n_sources=10)
        assert "name" in cat.colnames
        assert "ra" in cat.colnames
        assert "dec" in cat.colnames
        assert "flux" in cat.colnames

    def test_mock_catalog_ranges(self):
        """Test mock catalog has valid ranges."""
        cat = create_mock_catalog("TEST", n_sources=100)
        assert np.all(cat["ra"] >= 0)
        assert np.all(cat["ra"] <= 360)
        assert np.all(cat["dec"] >= -90)
        assert np.all(cat["dec"] <= 90)
        assert np.all(cat["flux"] > 0)

    def test_mock_catalog_reproducible(self):
        """Test mock catalog is reproducible."""
        cat1 = create_mock_catalog("TEST", n_sources=10)
        cat2 = create_mock_catalog("TEST", n_sources=10)
        assert np.allclose(cat1["ra"], cat2["ra"])
        assert np.allclose(cat1["dec"], cat2["dec"])
        assert np.allclose(cat1["flux"], cat2["flux"])


class TestRobustness:
    """Test robustness to various inputs."""

    def test_very_large_catalogs(self):
        """Test with large catalogs."""
        matcher = RadioCatalogMatcher()
        cat_a = create_mock_catalog("NVSS", n_sources=1000)
        cat_b = create_mock_catalog("RACS", n_sources=1000)

        # Should complete without error
        matches, idx, seps = matcher.match_two_catalogs(cat_a, cat_b, "NVSS", "RACS")
        assert len(matches) == 1000

    def test_unicode_source_names(self):
        """Test with unicode in source names."""
        matcher = RadioCatalogMatcher()
        cat_a = Table(
            {
                "name": ["Søren", "José", "北斗"],
                "ra": [100.0, 150.0, 200.0],
                "dec": [30.0, 40.0, 50.0],
                "flux": [1.0, 2.0, 3.0],
            }
        )
        cat_a.meta["catalog"] = "VLA"

        cat_b = Table(
            {
                "name": ["Match1", "Match2", "Match3"],
                "ra": [100.0, 150.0, 200.0],
                "dec": [30.0, 40.0, 50.0],
                "flux": [1.0, 2.0, 3.0],
            }
        )
        cat_b.meta["catalog"] = "FIRST"

        merged = matcher.merge_two_catalogs(cat_a, cat_b, "VLA", "FIRST")
        assert len(merged) == 3


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_racs_nvss_workflow(self):
        """Test complete RACS×NVSS workflow."""
        matcher = RadioCatalogMatcher(target_frequency_mhz=1405.0)

        # Create realistic test data
        nvss = Table(
            {
                "name": ["NVSS_J100000+300000", "NVSS_J150000+400000"],
                "ra": [150.0, 225.0],
                "dec": [30.0, 40.0],
                "flux": [1.5, 2.0],  # 1400 MHz
            }
        )
        nvss.meta["catalog"] = "NVSS"

        racs = Table(
            {
                "name": ["RACS_J100000+300000", "RACS_J200000+500000"],
                "ra": [150.0, 300.0],
                "dec": [30.0, 50.0],
                "flux": [2.1, 1.0],  # 887.5 MHz
            }
        )
        racs.meta["catalog"] = "RACS"

        # Full merge
        merged = matcher.merge_two_catalogs(nvss, racs, "NVSS", "RACS")

        # Verify results
        assert len(merged) == 3  # 1 matched + 2 unmatched
        matched = [s for s in merged if s.n_catalogs == 2][0]

        # Check spectral index is reasonable
        assert -1.0 < matched.spectral_index < -0.5

        # Check flux at DSA-110 frequency
        assert matched.flux_dsa110_jy > 0
        assert matched.flux_uncertainty_jy > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

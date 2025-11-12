"""Unit tests for cross-matching utilities."""

import pytest
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord, Angle
from astropy import units as u

from dsa110_contimg.catalog.crossmatch import (
    cross_match_sources,
    cross_match_dataframes,
    calculate_positional_offsets,
    calculate_flux_scale,
    search_around_sky,
    multi_catalog_match,
    identify_duplicate_catalog_sources,
)


class TestCrossMatchSources:
    """Test cross_match_sources function."""

    def test_basic_matching(self):
        """Test basic cross-matching with simple sources."""
        # Create detected sources
        detected_ra = np.array([10.0, 20.0, 30.0])
        detected_dec = np.array([0.0, 5.0, 10.0])

        # Create catalog sources (within 10 arcsec = ~0.0028 degrees)
        # 10 arcsec ≈ 0.0028 degrees at equator
        catalog_ra = np.array([10.0 + 0.001, 20.0 + 0.001, 50.0])
        catalog_dec = np.array([0.0 + 0.001, 5.0 + 0.001, 50.0])

        matches = cross_match_sources(
            detected_ra=detected_ra,
            detected_dec=detected_dec,
            catalog_ra=catalog_ra,
            catalog_dec=catalog_dec,
            radius_arcsec=10.0,
        )

        assert len(matches) == 2  # Two matches within 10 arcsec
        assert matches["separation_arcsec"].iloc[0] < 10.0
        assert matches["separation_arcsec"].iloc[1] < 10.0

    def test_no_matches(self):
        """Test when no sources match."""
        detected_ra = np.array([10.0, 20.0])
        detected_dec = np.array([0.0, 5.0])
        catalog_ra = np.array([100.0, 200.0])
        catalog_dec = np.array([50.0, 60.0])

        matches = cross_match_sources(
            detected_ra=detected_ra,
            detected_dec=detected_dec,
            catalog_ra=catalog_ra,
            catalog_dec=catalog_dec,
            radius_arcsec=10.0,
        )

        assert len(matches) == 0

    def test_with_flux(self):
        """Test cross-matching with flux information."""
        detected_ra = np.array([10.0, 20.0])
        detected_dec = np.array([0.0, 5.0])
        detected_flux = np.array([1.0, 2.0])
        # Use small offsets (within 10 arcsec ≈ 0.0028 degrees)
        catalog_ra = np.array([10.0 + 0.001, 20.0 + 0.001])
        catalog_dec = np.array([0.0 + 0.001, 5.0 + 0.001])
        catalog_flux = np.array([1.1, 2.1])

        matches = cross_match_sources(
            detected_ra=detected_ra,
            detected_dec=detected_dec,
            catalog_ra=catalog_ra,
            catalog_dec=catalog_dec,
            radius_arcsec=10.0,
            detected_flux=detected_flux,
            catalog_flux=catalog_flux,
        )

        assert len(matches) == 2
        assert "detected_flux" in matches.columns
        assert "catalog_flux" in matches.columns
        assert "flux_ratio" in matches.columns
        assert np.allclose(matches["flux_ratio"], [1.0 / 1.1, 2.0 / 2.1], rtol=0.1)

    def test_with_ids(self):
        """Test cross-matching with source IDs."""
        detected_ra = np.array([10.0])
        detected_dec = np.array([0.0])
        detected_ids = np.array(["src1"])
        # Use small offset (within 10 arcsec)
        catalog_ra = np.array([10.0 + 0.001])
        catalog_dec = np.array([0.0 + 0.001])
        catalog_ids = np.array(["cat1"])

        matches = cross_match_sources(
            detected_ra=detected_ra,
            detected_dec=detected_dec,
            catalog_ra=catalog_ra,
            catalog_dec=catalog_dec,
            radius_arcsec=10.0,
            detected_ids=detected_ids,
            catalog_ids=catalog_ids,
        )

        assert len(matches) == 1
        assert "detected_id" in matches.columns
        assert "catalog_id" in matches.columns
        assert matches["detected_id"].iloc[0] == "src1"
        assert matches["catalog_id"].iloc[0] == "cat1"


class TestCrossMatchDataframes:
    """Test cross_match_dataframes function."""

    def test_dataframe_matching(self):
        """Test cross-matching with DataFrames."""
        detected_df = pd.DataFrame(
            {
                "ra_deg": [10.0, 20.0],
                "dec_deg": [0.0, 5.0],
                "flux_jy": [1.0, 2.0],
            }
        )

        # Use small offsets (within 10 arcsec)
        catalog_df = pd.DataFrame(
            {
                "ra_deg": [10.0 + 0.001, 20.0 + 0.001],
                "dec_deg": [0.0 + 0.001, 5.0 + 0.001],
                "flux_mjy": [1100.0, 2100.0],
            }
        )

        matches = cross_match_dataframes(
            detected_df=detected_df,
            catalog_df=catalog_df,
            radius_arcsec=10.0,
            detected_ra_col="ra_deg",
            detected_dec_col="dec_deg",
            catalog_ra_col="ra_deg",
            catalog_dec_col="dec_deg",
            detected_flux_col="flux_jy",
            catalog_flux_col="flux_mjy",
        )

        assert len(matches) == 2
        assert "detected_flux" in matches.columns
        assert "catalog_flux" in matches.columns

    def test_empty_dataframes(self):
        """Test with empty DataFrames."""
        detected_df = pd.DataFrame({"ra_deg": [], "dec_deg": []})
        catalog_df = pd.DataFrame({"ra_deg": [], "dec_deg": []})

        # Empty DataFrames should return empty matches or raise ValueError
        try:
            matches = cross_match_dataframes(
                detected_df=detected_df,
                catalog_df=catalog_df,
                radius_arcsec=10.0,
            )
            # Should return empty DataFrame with expected columns
            assert len(matches) == 0 or (
                isinstance(matches, pd.DataFrame) and matches.empty
            )
        except ValueError:
            # Expected behavior when catalog is empty
            pass


class TestCalculatePositionalOffsets:
    """Test calculate_positional_offsets function."""

    def test_offset_calculation(self):
        """Test offset calculation."""
        matches = pd.DataFrame(
            {
                "dra_arcsec": [1.0, -1.0, 2.0, -2.0],
                "ddec_arcsec": [0.5, -0.5, 1.0, -1.0],
            }
        )

        dra_median, ddec_median, dra_madfm, ddec_madfm = calculate_positional_offsets(
            matches
        )

        assert isinstance(dra_median, u.Quantity)
        assert isinstance(ddec_median, u.Quantity)
        assert abs(dra_median.to(u.arcsec).value) < 1.0  # Should be near zero
        assert abs(ddec_median.to(u.arcsec).value) < 1.0

    def test_empty_matches(self):
        """Test with empty matches."""
        import warnings

        matches = pd.DataFrame({"dra_arcsec": [], "ddec_arcsec": []})

        # Empty matches should raise ValueError or return NaN
        # Suppress expected RuntimeWarnings from numpy when operating on empty arrays
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", category=RuntimeWarning, message="Mean of empty slice"
            )
            warnings.filterwarnings(
                "ignore", category=RuntimeWarning, message="invalid value encountered"
            )
            try:
                dra_median, ddec_median, dra_madfm, ddec_madfm = (
                    calculate_positional_offsets(matches)
                )
                # If it doesn't raise, check that results are NaN or invalid
                assert np.isnan(dra_median.to(u.arcsec).value) or np.isnan(
                    ddec_median.to(u.arcsec).value
                )
            except (ValueError, IndexError, RuntimeError):
                # Expected behavior - empty matches should raise an error
                pass


class TestCalculateFluxScale:
    """Test calculate_flux_scale function."""

    def test_flux_scale_calculation(self):
        """Test flux scale calculation."""
        matches = pd.DataFrame(
            {
                "flux_ratio": [1.0, 1.1, 0.9, 1.05],
            }
        )

        flux_corr, flux_ratio = calculate_flux_scale(matches)

        assert flux_corr.nominal_value > 0
        assert flux_ratio.nominal_value > 0
        assert abs(flux_corr.nominal_value - 1.0) < 0.2  # Should be near 1.0

    def test_empty_matches(self):
        """Test with empty matches."""
        matches = pd.DataFrame({"flux_ratio": []})

        with pytest.raises(ValueError):
            calculate_flux_scale(matches)

    def test_invalid_flux_ratios(self):
        """Test with invalid flux ratios."""
        matches = pd.DataFrame(
            {
                "flux_ratio": [np.nan, -1.0, 0.0],
            }
        )

        with pytest.raises(ValueError):
            calculate_flux_scale(matches)


class TestSearchAroundSky:
    """Test search_around_sky function."""

    def test_search_around_sky(self):
        """Test search_around_sky function."""
        coords1 = SkyCoord([10.0, 20.0] * u.deg, [0.0, 5.0] * u.deg)
        # Use small offsets (within 10 arcsec)
        coords2 = SkyCoord(
            [10.0 + 0.001, 20.0 + 0.001, 30.0] * u.deg,
            [0.0 + 0.001, 5.0 + 0.001, 50.0] * u.deg,
        )
        radius = Angle(10.0 * u.arcsec)

        idx1, idx2, sep2d = search_around_sky(coords1, coords2, radius)

        assert len(idx1) == len(idx2) == len(sep2d)
        assert len(idx1) == 2  # Two matches within radius


class TestMultiCatalogMatch:
    """Test multi_catalog_match function."""

    def test_multi_catalog_matching(self):
        """Test matching against multiple catalogs."""
        detected_ra = np.array([10.0, 20.0])
        detected_dec = np.array([0.0, 5.0])

        # Use small offsets (within 10 arcsec)
        catalogs = {
            "nvss": {
                "ra": np.array([10.0 + 0.001, 50.0]),
                "dec": np.array([0.0 + 0.001, 50.0]),
                "flux": np.array([1.0, 2.0]),
            },
            "first": {
                "ra": np.array([20.0 + 0.001, 60.0]),
                "dec": np.array([5.0 + 0.001, 60.0]),
                "flux": np.array([1.5, 2.5]),
            },
        }

        results = multi_catalog_match(
            detected_ra=detected_ra,
            detected_dec=detected_dec,
            catalogs=catalogs,
            radius_arcsec=10.0,
        )

        assert len(results) == 2
        assert "best_catalog" in results.columns
        assert "best_separation_arcsec" in results.columns
        assert results["best_catalog"].iloc[0] == "nvss"
        assert results["best_catalog"].iloc[1] == "first"

    def test_no_matches(self):
        """Test when no catalogs have matches."""
        detected_ra = np.array([10.0])
        detected_dec = np.array([0.0])

        catalogs = {
            "nvss": {
                "ra": np.array([100.0]),
                "dec": np.array([50.0]),
            },
        }

        results = multi_catalog_match(
            detected_ra=detected_ra,
            detected_dec=detected_dec,
            catalogs=catalogs,
            radius_arcsec=10.0,
        )

        assert len(results) == 1
        # When no matches, separation should be very large (not necessarily inf)
        assert results["best_separation_arcsec"].iloc[0] > 1000.0 or np.isinf(
            results["best_separation_arcsec"].iloc[0]
        )


class TestIdentifyDuplicateCatalogSources:
    """Test identify_duplicate_catalog_sources function."""

    def test_no_duplicates(self):
        """Test when no duplicates exist."""
        catalog_matches = {
            "nvss": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0, 20.0],
                    "catalog_dec_deg": [0.0, 5.0],
                    "catalog_source_id": ["nvss_1", "nvss_2"],
                }
            ),
            "first": pd.DataFrame(
                {
                    "catalog_ra_deg": [30.0, 40.0],
                    "catalog_dec_deg": [10.0, 15.0],
                    "catalog_source_id": ["first_1", "first_2"],
                }
            ),
        }

        master_ids = identify_duplicate_catalog_sources(catalog_matches)

        # Each entry should have its own master ID
        assert len(master_ids) == 4
        assert master_ids["nvss:nvss_1"] == "nvss:nvss_1"
        assert master_ids["nvss:nvss_2"] == "nvss:nvss_2"
        assert master_ids["first:first_1"] == "first:first_1"
        assert master_ids["first:first_2"] == "first:first_2"

    def test_duplicates_same_position(self):
        """Test when multiple catalogs have sources at same position."""
        # Same position (within 2 arcsec = ~0.00056 degrees)
        catalog_matches = {
            "nvss": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0],
                    "catalog_dec_deg": [0.0],
                    "catalog_source_id": ["nvss_J123456+012345"],
                }
            ),
            "first": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0 + 0.0001],  # Very close
                    "catalog_dec_deg": [0.0 + 0.0001],
                    "catalog_source_id": ["first_J123456+012345"],
                }
            ),
        }

        master_ids = identify_duplicate_catalog_sources(
            catalog_matches, deduplication_radius_arcsec=2.0
        )

        # Both should share NVSS master ID (NVSS has priority)
        assert len(master_ids) == 2
        assert master_ids["nvss:nvss_J123456+012345"] == "nvss:nvss_J123456+012345"
        assert master_ids["first:first_J123456+012345"] == "nvss:nvss_J123456+012345"

    def test_catalog_priority(self):
        """Test that catalog priority is respected (NVSS > FIRST > RACS)."""
        catalog_matches = {
            "rax": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0],
                    "catalog_dec_deg": [0.0],
                    "catalog_source_id": ["rax_1"],
                }
            ),
            "first": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0 + 0.0001],
                    "catalog_dec_deg": [0.0 + 0.0001],
                    "catalog_source_id": ["first_1"],
                }
            ),
            "nvss": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0 + 0.0002],
                    "catalog_dec_deg": [0.0 + 0.0002],
                    "catalog_source_id": ["nvss_1"],
                }
            ),
        }

        master_ids = identify_duplicate_catalog_sources(
            catalog_matches, deduplication_radius_arcsec=5.0
        )

        # All should share NVSS master ID (highest priority)
        assert master_ids["nvss:nvss_1"] == "nvss:nvss_1"
        assert master_ids["first:first_1"] == "nvss:nvss_1"
        assert master_ids["rax:rax_1"] == "nvss:nvss_1"

    def test_transitive_duplicates(self):
        """Test transitive duplicate relationships (A matches B, B matches C)."""
        catalog_matches = {
            "nvss": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0],
                    "catalog_dec_deg": [0.0],
                    "catalog_source_id": ["nvss_A"],
                }
            ),
            "first": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0 + 0.0003],  # Matches NVSS
                    "catalog_dec_deg": [0.0 + 0.0003],
                    "catalog_source_id": ["first_B"],
                }
            ),
            "rax": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0 + 0.0006],  # Matches FIRST
                    "catalog_dec_deg": [0.0 + 0.0006],
                    "catalog_source_id": ["rax_C"],
                }
            ),
        }

        master_ids = identify_duplicate_catalog_sources(
            catalog_matches, deduplication_radius_arcsec=5.0
        )

        # All should be grouped together with NVSS as master
        assert master_ids["nvss:nvss_A"] == "nvss:nvss_A"
        assert master_ids["first:first_B"] == "nvss:nvss_A"
        assert master_ids["rax:rax_C"] == "nvss:nvss_A"

    def test_empty_catalog_matches(self):
        """Test with empty catalog matches."""
        catalog_matches = {}

        master_ids = identify_duplicate_catalog_sources(catalog_matches)

        assert len(master_ids) == 0

    def test_partial_catalog_matches(self):
        """Test with some catalogs having no matches."""
        catalog_matches = {
            "nvss": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0],
                    "catalog_dec_deg": [0.0],
                    "catalog_source_id": ["nvss_1"],
                }
            ),
            "first": pd.DataFrame(),  # Empty
            "rax": None,  # None
        }

        master_ids = identify_duplicate_catalog_sources(catalog_matches)

        # Should only process NVSS
        assert len(master_ids) == 1
        assert master_ids["nvss:nvss_1"] == "nvss:nvss_1"

    def test_deduplication_radius(self):
        """Test that deduplication radius affects grouping."""
        catalog_matches = {
            "nvss": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0],
                    "catalog_dec_deg": [0.0],
                    "catalog_source_id": ["nvss_1"],
                }
            ),
            "first": pd.DataFrame(
                {
                    # ~1.08 arcsec (within 2 arcsec)
                    "catalog_ra_deg": [10.0 + 0.0003],
                    "catalog_dec_deg": [0.0 + 0.0003],
                    "catalog_source_id": ["first_1"],
                }
            ),
        }

        # Small radius - should group (within 2 arcsec)
        master_ids_small = identify_duplicate_catalog_sources(
            catalog_matches, deduplication_radius_arcsec=2.0
        )
        assert master_ids_small["nvss:nvss_1"] == "nvss:nvss_1"
        assert master_ids_small["first:first_1"] == "nvss:nvss_1"

        # Test with sources too far apart
        catalog_matches_far = {
            "nvss": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0],
                    "catalog_dec_deg": [0.0],
                    "catalog_source_id": ["nvss_1"],
                }
            ),
            "first": pd.DataFrame(
                {
                    "catalog_ra_deg": [10.0 + 0.01],  # ~36 arcsec (too far)
                    "catalog_dec_deg": [0.0 + 0.01],
                    "catalog_source_id": ["first_1"],
                }
            ),
        }

        # Small radius - should not group
        master_ids_far = identify_duplicate_catalog_sources(
            catalog_matches_far, deduplication_radius_arcsec=2.0
        )
        assert master_ids_far["nvss:nvss_1"] == "nvss:nvss_1"
        assert master_ids_far["first:first_1"] == "first:first_1"

    def test_approximate_position_from_offset(self):
        """Test when catalog positions are approximated from offsets."""
        catalog_matches = {
            "nvss": pd.DataFrame(
                {
                    "ra_deg": [10.0],
                    "dec_deg": [0.0],
                    "dra_arcsec": [0.0],
                    "ddec_arcsec": [0.0],
                    "catalog_source_id": ["nvss_1"],
                }
            ),
            "first": pd.DataFrame(
                {
                    "ra_deg": [10.0],
                    "dec_deg": [0.0],
                    "dra_arcsec": [0.1],
                    "ddec_arcsec": [0.1],
                    "catalog_source_id": ["first_1"],
                }
            ),
        }

        master_ids = identify_duplicate_catalog_sources(
            catalog_matches, deduplication_radius_arcsec=5.0
        )

        # Should group if positions are close enough
        assert len(master_ids) == 2

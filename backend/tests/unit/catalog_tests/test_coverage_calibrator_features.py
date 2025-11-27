"""Unit tests for Coverage-Aware Catalog Selection + Smart Calibrator Pre-Selection.

Tests for:
- Proposal #8: Coverage-Aware Catalog Selection (coverage.py)
- Proposal #3: Smart Calibrator Pre-Selection (calibrator_registry.py, calibrator_integration.py)
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# Add source directory to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "src" / "dsa110_contimg" / "src")
)

from dsa110_contimg.catalog.calibrator_integration import (
    recommend_calibrator_for_observation,
    select_bandpass_calibrator_fast,
    select_multiple_calibrators,
    validate_calibrator_selection,
)
from dsa110_contimg.catalog.calibrator_registry import (
    _calculate_quality_score,
    add_calibrator_to_registry,
    blacklist_source,
    create_calibrator_registry,
    get_best_calibrator,
    get_registry_statistics,
    is_source_blacklisted,
    query_calibrators,
)
from dsa110_contimg.catalog.coverage import (
    CATALOG_COVERAGE,
    get_available_catalogs,
    get_catalog_coverage,
    get_catalog_overlap_region,
    is_position_in_catalog,
    recommend_catalogs,
    validate_catalog_choice,
)

# ============================================================================
# Coverage-Aware Catalog Selection Tests (Proposal #8)
# ============================================================================


class TestCatalogCoverage:
    """Tests for catalog coverage definitions and lookups."""

    def test_catalog_coverage_complete(self):
        """All expected catalogs are defined."""
        expected_catalogs = {"nvss", "first", "racs", "vlass", "sumss"}
        assert set(CATALOG_COVERAGE.keys()) == expected_catalogs

    def test_catalog_coverage_structure(self):
        """Each catalog has required fields."""
        required_fields = {
            "name",
            "frequency_ghz",
            "dec_min",
            "dec_max",
            "resolution_arcsec",
            "typical_rms_mjy",
            "flux_limit_mjy",
            "best_for",
            "notes",
        }

        for catalog_type, coverage in CATALOG_COVERAGE.items():
            assert set(coverage.keys()) == required_fields, f"{catalog_type} missing fields"
            assert coverage["dec_min"] < coverage["dec_max"]
            assert coverage["frequency_ghz"] > 0
            assert coverage["resolution_arcsec"] > 0

    def test_get_catalog_coverage(self):
        """get_catalog_coverage returns correct data."""
        nvss = get_catalog_coverage("nvss")
        assert nvss is not None
        assert nvss["name"] == "NVSS"
        assert nvss["frequency_ghz"] == 1.4
        assert nvss["dec_min"] == -40.0

        # Unknown catalog returns None
        assert get_catalog_coverage("unknown") is None

    def test_is_position_in_catalog_nvss(self):
        """NVSS coverage checking."""
        # Inside coverage
        assert is_position_in_catalog(0.0, 0.0, "nvss") is True
        assert is_position_in_catalog(0.0, 45.0, "nvss") is True
        assert is_position_in_catalog(0.0, -39.0, "nvss") is True

        # Outside coverage
        assert is_position_in_catalog(0.0, -50.0, "nvss") is False
        assert is_position_in_catalog(0.0, 95.0, "nvss") is False

    def test_is_position_in_catalog_sumss(self):
        """SUMSS coverage checking (southern sky)."""
        # Inside coverage
        assert is_position_in_catalog(0.0, -60.0, "sumss") is True
        assert is_position_in_catalog(0.0, -31.0, "sumss") is True

        # Outside coverage
        assert is_position_in_catalog(0.0, 0.0, "sumss") is False
        assert is_position_in_catalog(0.0, 50.0, "sumss") is False


class TestAvailableCatalogs:
    """Tests for finding available catalogs at positions."""

    def test_northern_source(self):
        """Northern source has NVSS, FIRST, VLASS."""
        catalogs = get_available_catalogs(180.0, 60.0)
        assert "nvss" in catalogs
        assert "first" in catalogs
        assert "vlass" in catalogs
        assert "sumss" not in catalogs

    def test_southern_source(self):
        """Southern source has RACS, SUMSS."""
        catalogs = get_available_catalogs(180.0, -60.0)
        assert "racs" in catalogs
        assert "sumss" in catalogs
        assert "nvss" not in catalogs

    def test_overlap_region(self):
        """Equatorial region has multiple catalogs."""
        catalogs = get_available_catalogs(180.0, 0.0)
        assert len(catalogs) >= 3  # NVSS, FIRST, RACS, VLASS


class TestCatalogRecommendations:
    """Tests for intelligent catalog recommendations."""

    def test_general_purpose_recommendation(self):
        """General purpose returns NVSS for northern sky."""
        recs = recommend_catalogs(180.0, 30.0, purpose="general")
        assert len(recs) > 0
        # NVSS should be top recommendation for general
        assert recs[0]["catalog_type"] == "nvss"
        assert recs[0]["priority"] == 1

    def test_calibration_purpose(self):
        """Calibration purpose prioritizes NVSS/FIRST."""
        recs = recommend_catalogs(180.0, 30.0, purpose="calibration")
        assert len(recs) > 0
        top_catalogs = [r["catalog_type"] for r in recs[:2]]
        assert "nvss" in top_catalogs or "first" in top_catalogs

    def test_astrometry_purpose(self):
        """Astrometry purpose prefers high-resolution catalogs."""
        recs = recommend_catalogs(180.0, 30.0, purpose="astrometry")
        assert len(recs) > 0
        # FIRST (5") should be prioritized over NVSS (45")
        first_priority = next((r["priority"] for r in recs if r["catalog_type"] == "first"), 999)
        nvss_priority = next((r["priority"] for r in recs if r["catalog_type"] == "nvss"), 999)
        assert first_priority <= nvss_priority

    def test_spectral_index_purpose(self):
        """Spectral index purpose returns multiple frequencies."""
        recs = recommend_catalogs(180.0, 20.0, purpose="spectral_index")
        assert len(recs) >= 2  # Need multiple catalogs
        frequencies = [CATALOG_COVERAGE[r["catalog_type"]]["frequency_ghz"] for r in recs]
        assert len(set(frequencies)) >= 2  # Different frequencies

    def test_resolution_filtering(self):
        """Resolution constraints filter catalogs."""
        # Only high-resolution catalogs
        recs = recommend_catalogs(180.0, 30.0, max_resolution_arcsec=10.0)
        for rec in recs:
            resolution = CATALOG_COVERAGE[rec["catalog_type"]]["resolution_arcsec"]
            assert resolution <= 10.0


class TestCatalogValidation:
    """Tests for catalog coverage validation."""

    def test_valid_catalog_choice(self):
        """Valid catalog/position combinations."""
        is_valid, msg = validate_catalog_choice("nvss", 180.0, 30.0)
        assert is_valid is True
        assert msg is None

        is_valid, msg = validate_catalog_choice("sumss", 180.0, -60.0)
        assert is_valid is True
        assert msg is None

    def test_invalid_catalog_choice(self):
        """Invalid catalog/position combinations."""
        # NVSS doesn't cover Dec < -40
        is_valid, msg = validate_catalog_choice("nvss", 180.0, -50.0)
        assert is_valid is False
        assert "does not cover" in msg

        # SUMSS doesn't cover Dec > -30
        is_valid, msg = validate_catalog_choice("sumss", 180.0, 50.0)
        assert is_valid is False
        assert "does not cover" in msg

    def test_unknown_catalog(self):
        """Unknown catalog returns error."""
        is_valid, msg = validate_catalog_choice("unknown", 180.0, 30.0)
        assert is_valid is False
        assert "Unknown catalog" in msg


class TestCatalogOverlap:
    """Tests for catalog overlap calculations."""

    def test_nvss_first_overlap(self):
        """NVSS and FIRST overlap."""
        dec_min, dec_max = get_catalog_overlap_region(["nvss", "first"])
        assert dec_min == -40.0
        assert dec_max == 90.0

    def test_racs_sumss_overlap(self):
        """RACS and SUMSS overlap in southern sky."""
        dec_min, dec_max = get_catalog_overlap_region(["racs", "sumss"])
        assert dec_min == -90.0
        assert dec_max == -30.0

    def test_no_overlap(self):
        """No overlap between NVSS and far southern catalogs."""
        # NVSS (Dec > -40) and SUMSS (Dec < -30) barely overlap
        dec_min, dec_max = get_catalog_overlap_region(["nvss", "sumss"])
        assert dec_min == -40.0
        assert dec_max == -30.0


# ============================================================================
# Smart Calibrator Pre-Selection Tests (Proposal #3)
# ============================================================================


@pytest.fixture
def temp_registry_db():
    """Create temporary calibrator registry database."""
    temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    db_path = temp_db.name
    temp_db.close()

    # Create registry
    create_calibrator_registry(db_path=db_path)

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestCalibratorRegistry:
    """Tests for calibrator registry database."""

    def test_create_registry(self, temp_registry_db):
        """Registry database created with correct schema."""
        conn = sqlite3.connect(temp_registry_db)
        cur = conn.cursor()

        # Check tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        expected_tables = {
            "calibrator_sources",
            "calibrator_blacklist",
            "pb_weights_cache",
            "registry_metadata",
        }
        assert expected_tables.issubset(tables)

        conn.close()

    def test_add_calibrator(self, temp_registry_db):
        """Add calibrator to registry."""
        record_id = add_calibrator_to_registry(
            source_name="TEST_CAL_1",
            ra_deg=180.0,
            dec_deg=30.0,
            flux_1400mhz_jy=5.0,
            dec_strip=30,
            db_path=temp_registry_db,
        )

        assert record_id is not None
        assert record_id > 0

    def test_add_duplicate_calibrator(self, temp_registry_db):
        """Adding duplicate calibrator replaces existing."""
        # Add first time
        record_id1 = add_calibrator_to_registry(
            source_name="TEST_CAL",
            ra_deg=180.0,
            dec_deg=30.0,
            flux_1400mhz_jy=5.0,
            dec_strip=30,
            db_path=temp_registry_db,
        )

        # Add again (should replace)
        record_id2 = add_calibrator_to_registry(
            source_name="TEST_CAL",
            ra_deg=180.0,
            dec_deg=30.0,
            flux_1400mhz_jy=6.0,  # Different flux
            dec_strip=30,
            db_path=temp_registry_db,
        )

        assert record_id2 is not None


class TestCalibratorQueries:
    """Tests for querying calibrators from registry."""

    def test_query_empty_registry(self, temp_registry_db):
        """Querying empty registry returns empty list."""
        calibrators = query_calibrators(
            dec_deg=30.0,
            dec_tolerance=5.0,
            db_path=temp_registry_db,
        )
        assert calibrators == []

    def test_query_calibrators_by_declination(self, temp_registry_db):
        """Query calibrators within declination range."""
        # Add test calibrators
        for i, dec in enumerate([28.0, 30.0, 32.0, 40.0]):
            add_calibrator_to_registry(
                source_name=f"CAL_{i}",
                ra_deg=180.0 + i,
                dec_deg=dec,
                flux_1400mhz_jy=5.0 - i * 0.5,
                dec_strip=int(dec / 10) * 10,
                db_path=temp_registry_db,
            )

        # Query around Dec=30 with tolerance=5
        calibrators = query_calibrators(
            dec_deg=30.0,
            dec_tolerance=5.0,
            min_flux_jy=1.0,
            db_path=temp_registry_db,
        )

        # Should get calibrators at Dec=28, 30, 32 (not 40)
        assert len(calibrators) == 3

    def test_query_calibrators_by_flux(self, temp_registry_db):
        """Query calibrators above flux threshold."""
        # Add calibrators with different fluxes
        for i in range(5):
            add_calibrator_to_registry(
                source_name=f"CAL_{i}",
                ra_deg=180.0,
                dec_deg=30.0,
                flux_1400mhz_jy=float(i),  # 0, 1, 2, 3, 4 Jy
                dec_strip=30,
                db_path=temp_registry_db,
            )

        # Query with min_flux=2 Jy
        calibrators = query_calibrators(
            dec_deg=30.0,
            dec_tolerance=5.0,
            min_flux_jy=2.0,
            db_path=temp_registry_db,
        )

        # Should get calibrators with flux >= 2 (i=2,3,4)
        assert len(calibrators) == 3
        for cal in calibrators:
            assert cal["flux_1400mhz_jy"] >= 2.0

    def test_get_best_calibrator(self, temp_registry_db):
        """Get single best calibrator."""
        # Add calibrators with different quality
        for i in range(3):
            add_calibrator_to_registry(
                source_name=f"CAL_{i}",
                ra_deg=180.0,
                dec_deg=30.0,
                flux_1400mhz_jy=float(i + 1),  # 1, 2, 3 Jy
                dec_strip=30,
                quality_score=float((i + 1) * 20),  # 20, 40, 60
                db_path=temp_registry_db,
            )

        best = get_best_calibrator(
            dec_deg=30.0,
            dec_tolerance=5.0,
            min_flux_jy=1.0,
            db_path=temp_registry_db,
        )

        assert best is not None
        # Should get calibrator with highest quality (CAL_2 with score 60)
        assert best["source_name"] == "CAL_2"
        assert best["quality_score"] == 60.0


class TestCalibratorBlacklist:
    """Tests for calibrator blacklisting."""

    def test_blacklist_source(self, temp_registry_db):
        """Blacklist a source."""
        success = blacklist_source(
            source_name="PULSAR_J0534+2200",
            ra_deg=83.633,
            dec_deg=22.014,
            reason="pulsar",
            source_type="pulsar",
            db_path=temp_registry_db,
        )
        assert success is True

    def test_is_source_blacklisted_by_name(self, temp_registry_db):
        """Check if source is blacklisted by name."""
        # Blacklist source
        blacklist_source(
            source_name="BAD_CAL",
            ra_deg=180.0,
            dec_deg=30.0,
            reason="variable",
            db_path=temp_registry_db,
        )

        # Check by name
        is_blacklisted, reason = is_source_blacklisted(
            source_name="BAD_CAL",
            db_path=temp_registry_db,
        )
        assert is_blacklisted is True
        assert reason == "variable"

        # Non-blacklisted source
        is_blacklisted, _ = is_source_blacklisted(
            source_name="GOOD_CAL",
            db_path=temp_registry_db,
        )
        assert is_blacklisted is False

    def test_blacklisted_sources_filtered(self, temp_registry_db):
        """Blacklisted sources are filtered from queries."""
        # Add two calibrators
        add_calibrator_to_registry(
            source_name="GOOD_CAL",
            ra_deg=180.0,
            dec_deg=30.0,
            flux_1400mhz_jy=5.0,
            dec_strip=30,
            db_path=temp_registry_db,
        )
        add_calibrator_to_registry(
            source_name="BAD_CAL",
            ra_deg=181.0,
            dec_deg=30.0,
            flux_1400mhz_jy=6.0,
            dec_strip=30,
            db_path=temp_registry_db,
        )

        # Blacklist one
        blacklist_source(
            source_name="BAD_CAL",
            ra_deg=181.0,
            dec_deg=30.0,
            reason="variable",
            db_path=temp_registry_db,
        )

        # Query should return only good calibrator
        calibrators = query_calibrators(
            dec_deg=30.0,
            dec_tolerance=5.0,
            db_path=temp_registry_db,
        )

        assert len(calibrators) == 1
        assert calibrators[0]["source_name"] == "GOOD_CAL"


class TestQualityScoring:
    """Tests for calibrator quality scoring."""

    def test_quality_score_bright_source(self):
        """Bright sources get high flux score."""
        # 10 Jy source should get maximum flux score
        score = _calculate_quality_score(
            flux_jy=10.0,
            spectral_index=None,
            compactness=None,
        )
        assert score >= 40.0  # High flux score

    def test_quality_score_flat_spectrum(self):
        """Flat spectrum sources get high spectral score."""
        score = _calculate_quality_score(
            flux_jy=5.0,
            spectral_index=0.0,  # Flat spectrum
            compactness=None,
        )
        # Should get high spectral index score
        assert score >= 60.0

    def test_quality_score_point_source(self):
        """Point sources get high compactness score."""
        score = _calculate_quality_score(
            flux_jy=5.0,
            spectral_index=None,
            compactness=1.0,  # Perfect point source
        )
        # Should get high compactness score
        assert score >= 60.0

    def test_quality_score_ideal_calibrator(self):
        """Ideal calibrator gets near-perfect score."""
        score = _calculate_quality_score(
            flux_jy=10.0,  # Bright
            spectral_index=0.0,  # Flat spectrum
            compactness=1.0,  # Point source
        )
        assert score >= 95.0  # Near perfect


class TestRegistryStatistics:
    """Tests for registry statistics."""

    def test_statistics_empty_registry(self, temp_registry_db):
        """Statistics for empty registry."""
        stats = get_registry_statistics(db_path=temp_registry_db)
        assert stats["total_calibrators"] == 0
        assert stats["blacklisted_sources"] == 0

    def test_statistics_with_data(self, temp_registry_db):
        """Statistics with calibrators and blacklist."""
        # Add calibrators
        for i in range(5):
            add_calibrator_to_registry(
                source_name=f"CAL_{i}",
                ra_deg=180.0,
                dec_deg=30.0,
                flux_1400mhz_jy=5.0,
                dec_strip=30,
                quality_score=float(i * 20),
                db_path=temp_registry_db,
            )

        # Add blacklist entry
        blacklist_source(
            source_name="BAD_CAL",
            ra_deg=180.0,
            dec_deg=30.0,
            reason="variable",
            db_path=temp_registry_db,
        )

        stats = get_registry_statistics(db_path=temp_registry_db)
        assert stats["total_calibrators"] == 5
        assert stats["blacklisted_sources"] == 1
        assert "quality_distribution" in stats


# ============================================================================
# Pipeline Integration Tests
# ============================================================================


class TestCalibratorIntegration:
    """Tests for calibrator integration with pipeline."""

    def test_fast_selection_with_registry(self, temp_registry_db):
        """Fast calibrator selection from registry."""
        # Add test calibrator
        add_calibrator_to_registry(
            source_name="TEST_CAL",
            ra_deg=180.0,
            dec_deg=30.0,
            flux_1400mhz_jy=5.0,
            dec_strip=30,
            db_path=temp_registry_db,
        )

        # Select calibrator
        calibrator = select_bandpass_calibrator_fast(
            dec_deg=30.0,
            dec_tolerance=5.0,
            min_flux_jy=1.0,
            use_registry=True,
            fallback_to_catalog=False,
            db_path=temp_registry_db,
        )

        assert calibrator is not None
        assert calibrator["source_name"] == "TEST_CAL"

    def test_fast_selection_empty_registry(self, temp_registry_db):
        """Fast selection with empty registry returns None."""
        calibrator = select_bandpass_calibrator_fast(
            dec_deg=30.0,
            dec_tolerance=5.0,
            use_registry=True,
            fallback_to_catalog=False,
            db_path=temp_registry_db,
        )

        assert calibrator is None

    def test_multiple_calibrator_selection(self, temp_registry_db):
        """Select multiple calibrators."""
        # Add calibrators at different positions
        for i in range(10):
            add_calibrator_to_registry(
                source_name=f"CAL_{i}",
                ra_deg=180.0 + i * 2.0,  # Separated by 2 degrees
                dec_deg=30.0,
                flux_1400mhz_jy=5.0,
                dec_strip=30,
                db_path=temp_registry_db,
            )

        # Select 5 calibrators with minimum separation
        calibrators = select_multiple_calibrators(
            dec_deg=30.0,
            n_calibrators=5,
            min_separation_deg=1.0,
            db_path=temp_registry_db,
        )

        assert len(calibrators) == 5

    def test_validate_calibrator_selection(self):
        """Validate calibrator selection."""
        good_calibrator = {
            "source_name": "GOOD_CAL",
            "ra_deg": 180.0,
            "dec_deg": 30.0,
            "flux_1400mhz_jy": 5.0,
            "quality_score": 80.0,
        }

        is_valid, msg = validate_calibrator_selection(
            calibrator=good_calibrator,
            target_dec=30.0,
            max_dec_offset=10.0,
            min_flux_jy=1.0,
        )

        assert is_valid is True
        assert msg is None

    def test_validate_calibrator_low_flux(self):
        """Reject calibrator with low flux."""
        low_flux_cal = {
            "source_name": "WEAK_CAL",
            "ra_deg": 180.0,
            "dec_deg": 30.0,
            "flux_1400mhz_jy": 0.3,
            "quality_score": 50.0,
        }

        is_valid, msg = validate_calibrator_selection(
            calibrator=low_flux_cal,
            target_dec=30.0,
            min_flux_jy=1.0,
        )

        assert is_valid is False
        assert "Flux too low" in msg

    def test_observation_recommendation_general(self, temp_registry_db):
        """Recommend calibrator for general observation."""
        # Add test calibrator
        add_calibrator_to_registry(
            source_name="TEST_CAL",
            ra_deg=180.0,
            dec_deg=30.0,
            flux_1400mhz_jy=5.0,
            dec_strip=30,
            quality_score=70.0,
            db_path=temp_registry_db,
        )

        calibrator = recommend_calibrator_for_observation(
            target_dec=30.0,
            observation_type="general",
            db_path=temp_registry_db,
        )

        assert calibrator is not None
        assert calibrator["quality_score"] >= 50.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_complete_calibrator_workflow(self, temp_registry_db):
        """Complete workflow: add, query, validate, select."""
        # 1. Add calibrators
        for i in range(5):
            add_calibrator_to_registry(
                source_name=f"CAL_{i}",
                ra_deg=180.0 + i,
                dec_deg=30.0,
                flux_1400mhz_jy=float(5 - i),
                dec_strip=30,
                db_path=temp_registry_db,
            )

        # 2. Blacklist one
        blacklist_source(
            source_name="CAL_2",
            ra_deg=182.0,
            dec_deg=30.0,
            reason="variable",
            db_path=temp_registry_db,
        )

        # 3. Query calibrators
        calibrators = query_calibrators(
            dec_deg=30.0,
            dec_tolerance=5.0,
            min_flux_jy=1.0,
            db_path=temp_registry_db,
        )

        # Should get 4 (5 - 1 blacklisted)
        assert len(calibrators) == 4
        assert all(c["source_name"] != "CAL_2" for c in calibrators)

        # 4. Get best calibrator
        best = get_best_calibrator(
            dec_deg=30.0,
            dec_tolerance=5.0,
            db_path=temp_registry_db,
        )

        assert best is not None
        assert best["source_name"] != "CAL_2"

        # 5. Validate selection
        is_valid, _ = validate_calibrator_selection(
            calibrator=best,
            target_dec=30.0,
        )

        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""Comprehensive unit tests for Transient Detection & Astrometric Calibration.

Tests cover:
- Transient detection database tables
- Detection algorithm (new/variable/fading sources)
- Alert generation and management
- Astrometric offset calculation
- WCS correction application
- Database storage and retrieval
- Edge cases and error handling
"""

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Add src directory to path
src_path = Path(__file__).parent.parent.parent.parent / "dsa110_contimg" / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from dsa110_contimg.catalog.astrometric_calibration import (
    calculate_astrometric_offsets,
    create_astrometry_tables,
    get_astrometric_accuracy_stats,
    get_recent_astrometric_solutions,
    mark_solution_applied,
    store_astrometric_solution,
)
from dsa110_contimg.catalog.transient_detection import (
    create_transient_detection_tables,
    detect_transients,
    generate_transient_alerts,
    get_transient_alerts,
    get_transient_candidates,
    store_transient_candidates,
)

# ============================================================================
# Transient Detection Tests
# ============================================================================


class TestTransientDetectionTables:
    """Test transient detection database table creation."""

    def test_create_tables_success(self):
        """Test successful table creation."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            result = create_transient_detection_tables(tmp.name)
            assert result is True

            # Verify tables exist
            conn = sqlite3.connect(tmp.name)
            cur = conn.cursor()

            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='transient_candidates'"
            )
            assert cur.fetchone() is not None

            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' " "AND name='transient_alerts'"
            )
            assert cur.fetchone() is not None

            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='transient_lightcurves'"
            )
            assert cur.fetchone() is not None

            conn.close()

    def test_create_tables_idempotent(self):
        """Test that creating tables multiple times is safe."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            result1 = create_transient_detection_tables(tmp.name)
            result2 = create_transient_detection_tables(tmp.name)
            assert result1 is True
            assert result2 is True

    def test_table_indices(self):
        """Test that indices are created correctly."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_transient_detection_tables(tmp.name)

            conn = sqlite3.connect(tmp.name)
            cur = conn.cursor()

            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND tbl_name='transient_candidates'"
            )
            indices = [row[0] for row in cur.fetchall()]
            assert "idx_transients_type" in indices
            assert "idx_transients_coords" in indices
            assert "idx_transients_detected" in indices

            conn.close()


class TestTransientDetection:
    """Test transient detection algorithm."""

    def test_detect_new_sources(self):
        """Test detection of new sources not in baseline."""
        observed = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.1],
                "dec_deg": [30.0, 30.1],
                "flux_mjy": [50.0, 60.0],
                "flux_err_mjy": [5.0, 6.0],
            }
        )

        baseline = pd.DataFrame({"ra_deg": [180.5], "dec_deg": [30.5], "flux_mjy": [40.0]})

        new, variable, fading = detect_transients(
            observed,
            baseline,
            detection_threshold_sigma=5.0,
            match_radius_arcsec=10.0,
        )

        assert len(new) == 2
        assert len(variable) == 0
        # Baseline source at (180.5, 30.5) not detected = 1 fading
        assert len(fading) == 1

    def test_detect_variable_sources(self):
        """Test detection of variable sources."""
        observed = pd.DataFrame(
            {
                "ra_deg": [180.0],
                "dec_deg": [30.0],
                "flux_mjy": [100.0],
                "flux_err_mjy": [10.0],
            }
        )

        baseline = pd.DataFrame({"ra_deg": [180.0], "dec_deg": [30.0], "flux_mjy": [30.0]})

        new, variable, fading = detect_transients(
            observed,
            baseline,
            variability_threshold=2.0,
            match_radius_arcsec=10.0,
        )

        assert len(new) == 0
        assert len(variable) == 1
        assert variable[0]["detection_type"] == "brightening"

    def test_detect_fading_sources(self):
        """Test detection of fading sources."""
        observed = pd.DataFrame({"ra_deg": [180.0], "dec_deg": [30.0], "flux_mjy": [50.0]})

        baseline = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.5],
                "dec_deg": [30.0, 30.5],
                "flux_mjy": [50.0, 100.0],
            }
        )

        new, variable, fading = detect_transients(
            observed,
            baseline,
            match_radius_arcsec=10.0,
            variability_threshold=2.0,
        )

        assert len(new) == 0
        assert len(variable) == 0
        assert len(fading) == 1

    def test_empty_observed_sources(self):
        """Test handling of empty observed sources."""
        observed = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])
        baseline = pd.DataFrame({"ra_deg": [180.0], "dec_deg": [30.0], "flux_mjy": [50.0]})

        new, variable, fading = detect_transients(observed, baseline)

        assert len(new) == 0
        assert len(variable) == 0
        assert len(fading) == 0

    def test_empty_baseline(self):
        """Test handling of empty baseline catalog."""
        observed = pd.DataFrame(
            {
                "ra_deg": [180.0],
                "dec_deg": [30.0],
                "flux_mjy": [50.0],
                "flux_err_mjy": [5.0],
            }
        )
        baseline = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

        new, variable, fading = detect_transients(
            observed,
            baseline,
            detection_threshold_sigma=5.0,
        )

        assert len(new) == 1
        assert len(variable) == 0
        assert len(fading) == 0

    def test_detection_thresholds(self):
        """Test that detection thresholds are respected."""
        observed = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.1],
                "dec_deg": [30.0, 30.1],
                "flux_mjy": [50.0, 20.0],
                "flux_err_mjy": [5.0, 10.0],
            }
        )
        baseline = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

        new, variable, fading = detect_transients(
            observed,
            baseline,
            detection_threshold_sigma=5.0,
        )

        # Only first source meets 5σ threshold (50/5=10σ)
        # Second source is 2σ (20/10=2σ)
        assert len(new) == 1
        assert new[0]["flux_obs_mjy"] == 50.0


class TestTransientStorage:
    """Test transient candidate storage."""

    def test_store_candidates_success(self):
        """Test successful storage of candidates."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_transient_detection_tables(tmp.name)

            candidates = [
                {
                    "ra_deg": 180.0,
                    "dec_deg": 30.0,
                    "flux_obs_mjy": 50.0,
                    "significance_sigma": 7.5,
                    "detection_type": "new",
                },
                {
                    "ra_deg": 180.1,
                    "dec_deg": 30.1,
                    "flux_obs_mjy": 100.0,
                    "flux_baseline_mjy": 30.0,
                    "flux_ratio": 3.33,
                    "significance_sigma": 8.2,
                    "detection_type": "brightening",
                },
            ]

            candidate_ids = store_transient_candidates(candidates, db_path=tmp.name)

            assert len(candidate_ids) == 2
            assert all(isinstance(id, int) for id in candidate_ids)

    def test_query_candidates_by_significance(self):
        """Test querying candidates by significance threshold."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_transient_detection_tables(tmp.name)

            candidates = [
                {
                    "ra_deg": 180.0,
                    "dec_deg": 30.0,
                    "flux_obs_mjy": 50.0,
                    "significance_sigma": 5.0,
                    "detection_type": "new",
                },
                {
                    "ra_deg": 180.1,
                    "dec_deg": 30.1,
                    "flux_obs_mjy": 100.0,
                    "significance_sigma": 10.0,
                    "detection_type": "new",
                },
            ]

            store_transient_candidates(candidates, db_path=tmp.name)

            # Query with high threshold
            df = get_transient_candidates(min_significance=8.0, db_path=tmp.name)
            assert len(df) == 1
            assert df.iloc[0]["significance_sigma"] == 10.0

    def test_query_candidates_by_type(self):
        """Test querying candidates by detection type."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_transient_detection_tables(tmp.name)

            candidates = [
                {
                    "ra_deg": 180.0,
                    "dec_deg": 30.0,
                    "flux_obs_mjy": 50.0,
                    "significance_sigma": 7.0,
                    "detection_type": "new",
                },
                {
                    "ra_deg": 180.1,
                    "dec_deg": 30.1,
                    "flux_obs_mjy": 100.0,
                    "flux_baseline_mjy": 30.0,
                    "significance_sigma": 8.0,
                    "detection_type": "brightening",
                },
            ]

            store_transient_candidates(candidates, db_path=tmp.name)

            # Query only new sources
            df = get_transient_candidates(detection_types=["new"], db_path=tmp.name)
            assert len(df) == 1
            assert df.iloc[0]["detection_type"] == "new"


class TestTransientAlerts:
    """Test transient alert generation."""

    def test_generate_alerts_critical(self):
        """Test generation of CRITICAL alerts."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_transient_detection_tables(tmp.name)

            candidates = [
                {
                    "ra_deg": 180.0,
                    "dec_deg": 30.0,
                    "flux_obs_mjy": 50.0,
                    "significance_sigma": 12.0,
                    "detection_type": "new",
                }
            ]

            candidate_ids = store_transient_candidates(candidates, db_path=tmp.name)
            alert_ids = generate_transient_alerts(
                candidate_ids, alert_threshold_sigma=7.0, db_path=tmp.name
            )

            assert len(alert_ids) == 1

            # Check alert level
            df = get_transient_alerts(db_path=tmp.name)
            assert len(df) == 1
            assert df.iloc[0]["alert_level"] == "CRITICAL"

    def test_generate_alerts_threshold(self):
        """Test that alerts respect threshold."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_transient_detection_tables(tmp.name)

            candidates = [
                {
                    "ra_deg": 180.0,
                    "dec_deg": 30.0,
                    "flux_obs_mjy": 50.0,
                    "significance_sigma": 5.0,
                    "detection_type": "new",
                }
            ]

            candidate_ids = store_transient_candidates(candidates, db_path=tmp.name)
            alert_ids = generate_transient_alerts(
                candidate_ids, alert_threshold_sigma=7.0, db_path=tmp.name
            )

            # Should not generate alert (5σ < 7σ threshold)
            assert len(alert_ids) == 0

    def test_query_alerts_by_level(self):
        """Test querying alerts by level."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_transient_detection_tables(tmp.name)

            candidates = [
                {
                    "ra_deg": 180.0,
                    "dec_deg": 30.0,
                    "flux_obs_mjy": 50.0,
                    "significance_sigma": 12.0,
                    "detection_type": "new",
                },
                {
                    "ra_deg": 180.1,
                    "dec_deg": 30.1,
                    "flux_obs_mjy": 60.0,
                    "significance_sigma": 8.0,
                    "detection_type": "new",
                },
            ]

            candidate_ids = store_transient_candidates(candidates, db_path=tmp.name)
            generate_transient_alerts(candidate_ids, alert_threshold_sigma=7.0, db_path=tmp.name)

            # Query CRITICAL alerts
            df = get_transient_alerts(alert_level="CRITICAL", db_path=tmp.name)
            assert len(df) == 1


# ============================================================================
# Astrometric Calibration Tests
# ============================================================================


class TestAstrometryTables:
    """Test astrometric calibration database tables."""

    def test_create_tables_success(self):
        """Test successful table creation."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            result = create_astrometry_tables(tmp.name)
            assert result is True

            # Verify tables exist
            conn = sqlite3.connect(tmp.name)
            cur = conn.cursor()

            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='astrometric_solutions'"
            )
            assert cur.fetchone() is not None

            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='astrometric_residuals'"
            )
            assert cur.fetchone() is not None

            conn.close()

    def test_create_tables_idempotent(self):
        """Test that creating tables multiple times is safe."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            result1 = create_astrometry_tables(tmp.name)
            result2 = create_astrometry_tables(tmp.name)
            assert result1 is True
            assert result2 is True


class TestAstrometricOffsets:
    """Test astrometric offset calculation."""

    def test_calculate_offsets_success(self):
        """Test successful offset calculation."""
        # Create synthetic data with known offset
        true_ra_offset_mas = 100.0
        true_dec_offset_mas = -50.0

        reference = pd.DataFrame(
            {
                "ra_deg": [180.0 + i * 0.01 for i in range(20)],
                "dec_deg": [30.0 + i * 0.01 for i in range(20)],
                "flux_mjy": [50.0] * 20,
            }
        )

        np.random.seed(42)
        dec_mean = reference["dec_deg"].mean()
        ra_offset_deg = true_ra_offset_mas / (3600.0 * 1000.0 * np.cos(np.radians(dec_mean)))
        dec_offset_deg = true_dec_offset_mas / (3600.0 * 1000.0)

        observed = pd.DataFrame(
            {
                "ra_deg": reference["ra_deg"] + ra_offset_deg + np.random.normal(0, 1e-6, 20),
                "dec_deg": reference["dec_deg"] + dec_offset_deg + np.random.normal(0, 1e-6, 20),
                "flux_mjy": [50.0] * 20,
            }
        )

        solution = calculate_astrometric_offsets(
            observed, reference, match_radius_arcsec=5.0, min_matches=10
        )

        assert solution is not None
        assert solution["n_matches"] == 20
        assert abs(solution["ra_offset_mas"] - true_ra_offset_mas) < 20.0
        assert abs(solution["dec_offset_mas"] - true_dec_offset_mas) < 20.0

    def test_insufficient_matches(self):
        """Test handling of insufficient matches."""
        observed = pd.DataFrame({"ra_deg": [180.0], "dec_deg": [30.0], "flux_mjy": [50.0]})

        reference = pd.DataFrame({"ra_deg": [180.0], "dec_deg": [30.0], "flux_mjy": [50.0]})

        solution = calculate_astrometric_offsets(observed, reference, min_matches=10)

        assert solution is None

    def test_empty_sources(self):
        """Test handling of empty source lists."""
        observed = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])
        reference = pd.DataFrame({"ra_deg": [180.0], "dec_deg": [30.0], "flux_mjy": [50.0]})

        solution = calculate_astrometric_offsets(observed, reference)
        assert solution is None

    def test_flux_weighting(self):
        """Test that flux weighting affects solution."""
        reference = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.01],
                "dec_deg": [30.0, 30.01],
                "flux_mjy": [50.0, 50.0],
            }
        )

        observed = pd.DataFrame(
            {
                "ra_deg": [180.0001, 180.0102],
                "dec_deg": [30.0001, 30.0102],
                "flux_mjy": [100.0, 10.0],
            }
        )

        solution_weighted = calculate_astrometric_offsets(
            observed, reference, flux_weight=True, min_matches=2
        )

        solution_unweighted = calculate_astrometric_offsets(
            observed, reference, flux_weight=False, min_matches=2
        )

        assert solution_weighted is not None
        assert solution_unweighted is not None
        # Weighted solution should be different
        assert solution_weighted["ra_offset_mas"] != solution_unweighted["ra_offset_mas"]


class TestAstrometricStorage:
    """Test astrometric solution storage."""

    def test_store_solution_success(self):
        """Test successful storage of solution."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_astrometry_tables(tmp.name)

            solution = {
                "n_matches": 15,
                "ra_offset_mas": 120.5,
                "dec_offset_mas": -45.2,
                "ra_offset_err_mas": 8.3,
                "dec_offset_err_mas": 7.1,
                "rms_residual_mas": 150.0,
                "matches": [
                    {
                        "ra_obs": 180.0,
                        "dec_obs": 30.0,
                        "ra_ref": 179.9999,
                        "dec_ref": 30.0001,
                        "ra_offset_mas": 120.0,
                        "dec_offset_mas": -50.0,
                        "separation_mas": 130.0,
                        "flux_obs": 50.0,
                        "flux_ref": 48.0,
                    }
                ],
            }

            solution_id = store_astrometric_solution(solution, mosaic_id=1, db_path=tmp.name)

            assert solution_id is not None
            assert isinstance(solution_id, int)

    def test_query_recent_solutions(self):
        """Test querying recent solutions."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_astrometry_tables(tmp.name)

            solution1 = {
                "n_matches": 15,
                "ra_offset_mas": 100.0,
                "dec_offset_mas": -50.0,
                "ra_offset_err_mas": 10.0,
                "dec_offset_err_mas": 10.0,
                "rms_residual_mas": 150.0,
                "matches": [],
            }

            solution2 = {
                "n_matches": 20,
                "ra_offset_mas": 200.0,
                "dec_offset_mas": -100.0,
                "ra_offset_err_mas": 10.0,
                "dec_offset_err_mas": 10.0,
                "rms_residual_mas": 200.0,
                "matches": [],
            }

            store_astrometric_solution(solution1, mosaic_id=1, db_path=tmp.name)
            store_astrometric_solution(solution2, mosaic_id=2, db_path=tmp.name)

            df = get_recent_astrometric_solutions(limit=10, db_path=tmp.name)
            assert len(df) == 2

    def test_mark_solution_applied(self):
        """Test marking solution as applied."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_astrometry_tables(tmp.name)

            solution = {
                "n_matches": 15,
                "ra_offset_mas": 100.0,
                "dec_offset_mas": -50.0,
                "ra_offset_err_mas": 10.0,
                "dec_offset_err_mas": 10.0,
                "rms_residual_mas": 150.0,
                "matches": [],
            }

            solution_id = store_astrometric_solution(solution, mosaic_id=1, db_path=tmp.name)

            result = mark_solution_applied(solution_id, db_path=tmp.name)
            assert result is True

            # Verify in database
            conn = sqlite3.connect(tmp.name)
            cur = conn.cursor()
            cur.execute(
                "SELECT applied FROM astrometric_solutions WHERE id = ?",
                (solution_id,),
            )
            applied = cur.fetchone()[0]
            assert applied == 1
            conn.close()


class TestAstrometricStatistics:
    """Test astrometric accuracy statistics."""

    def test_get_accuracy_stats(self):
        """Test getting accuracy statistics."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_astrometry_tables(tmp.name)

            solutions = [
                {
                    "n_matches": 15,
                    "ra_offset_mas": 100.0 + i * 10,
                    "dec_offset_mas": -50.0 + i * 5,
                    "ra_offset_err_mas": 10.0,
                    "dec_offset_err_mas": 10.0,
                    "rms_residual_mas": 150.0 + i * 20,
                    "matches": [],
                }
                for i in range(5)
            ]

            for i, solution in enumerate(solutions):
                store_astrometric_solution(solution, mosaic_id=i, db_path=tmp.name)

            stats = get_astrometric_accuracy_stats(db_path=tmp.name)
            assert stats["n_solutions"] == 5
            assert stats["mean_rms_mas"] is not None
            assert stats["median_rms_mas"] is not None

    def test_stats_empty_database(self):
        """Test statistics with empty database."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            create_astrometry_tables(tmp.name)

            stats = get_astrometric_accuracy_stats(db_path=tmp.name)
            assert stats["n_solutions"] == 0
            assert stats["mean_rms_mas"] is None


class TestWCSCorrection:
    """Test WCS correction application."""

    def test_apply_wcs_correction_nonexistent_file(self):
        """Test handling of nonexistent FITS file."""
        from dsa110_contimg.catalog.astrometric_calibration import (
            apply_wcs_correction,
        )

        # Should return False for nonexistent file
        result = apply_wcs_correction(
            ra_offset_mas=100.0,
            dec_offset_mas=-50.0,
            fits_path="/fake/nonexistent/path.fits",
        )

        assert result is False


# ============================================================================
# Integration Tests
# ============================================================================


class TestEndToEndWorkflow:
    """Test complete transient detection and astrometry workflow."""

    def test_full_transient_workflow(self):
        """Test complete transient detection workflow."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            # Setup
            create_transient_detection_tables(tmp.name)

            # Simulate observations
            observed = pd.DataFrame(
                {
                    "ra_deg": [180.0, 180.1, 180.2],
                    "dec_deg": [30.0, 30.1, 30.2],
                    "flux_mjy": [50.0, 100.0, 20.0],
                    "flux_err_mjy": [5.0, 10.0, 2.0],
                }
            )

            baseline = pd.DataFrame(
                {
                    "ra_deg": [180.1, 180.2, 180.3],
                    "dec_deg": [30.1, 30.2, 30.3],
                    "flux_mjy": [30.0, 20.0, 50.0],
                }
            )

            # Detect transients
            new, variable, fading = detect_transients(
                observed,
                baseline,
                detection_threshold_sigma=3.0,
                variability_threshold=2.0,
            )

            # Store candidates
            all_candidates = new + variable + fading
            candidate_ids = store_transient_candidates(all_candidates, db_path=tmp.name)

            # Generate alerts
            alert_ids = generate_transient_alerts(
                candidate_ids, alert_threshold_sigma=5.0, db_path=tmp.name
            )

            # Verify results
            assert len(candidate_ids) >= 2
            assert len(alert_ids) >= 0

            # Query results
            df_candidates = get_transient_candidates(db_path=tmp.name)
            assert len(df_candidates) >= 2

    def test_full_astrometry_workflow(self):
        """Test complete astrometric calibration workflow."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
            # Setup
            create_astrometry_tables(tmp.name)

            # Create synthetic data
            reference = pd.DataFrame(
                {
                    "ra_deg": [180.0 + i * 0.01 for i in range(20)],
                    "dec_deg": [30.0 + i * 0.01 for i in range(20)],
                    "flux_mjy": [50.0] * 20,
                }
            )

            np.random.seed(42)
            observed = pd.DataFrame(
                {
                    "ra_deg": reference["ra_deg"] + 0.00003 + np.random.normal(0, 1e-6, 20),
                    "dec_deg": reference["dec_deg"] - 0.00001 + np.random.normal(0, 1e-6, 20),
                    "flux_mjy": [50.0] * 20,
                }
            )

            # Calculate offsets
            solution = calculate_astrometric_offsets(observed, reference, min_matches=10)

            assert solution is not None

            # Store solution
            solution_id = store_astrometric_solution(solution, mosaic_id=1, db_path=tmp.name)

            assert solution_id is not None

            # Query statistics
            stats = get_astrometric_accuracy_stats(db_path=tmp.name)
            assert stats["n_solutions"] == 1

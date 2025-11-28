#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Science-First Calibration Integration Validation

These tests validate ACTUAL calibration tables and MS files for scientific correctness.
They read real calibration products and validate:
- Flux scale accuracy
- Phase solution quality
- Bandpass shape
- CASA compliance
- Scientific validity

These tests REQUIRE actual calibration tables and MS files to run.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def calibration_table_paths():
    """Fixture for calibration table paths (set via environment or pytest)."""
    # These can be set via environment variables or pytest markers
    bp_table = os.environ.get("TEST_BP_TABLE", "")
    prebp_table = os.environ.get("TEST_PREBP_TABLE", "")
    g_table = os.environ.get("TEST_G_TABLE", "")

    return {
        "bandpass": bp_table,
        "prebandpass": prebp_table,
        "gain": g_table,
    }


@pytest.fixture
def ms_path():
    """Fixture for MS path (set via environment or pytest)."""
    return os.environ.get("TEST_MS_PATH", "")


@pytest.fixture
def known_calibrator_info():
    """Known calibrator information for validation."""
    # 0834+555: Standard VLA calibrator
    return {
        "name": "0834+555",
        "ra_deg": 128.7287,
        "dec_deg": 55.5725,
        "flux_jy_1_4ghz": 2.5,  # Jy at 1.4 GHz
        "tolerance_jy": 0.1,  # 4% tolerance
    }


class TestActualCalibrationFluxScale:
    """Validate flux scale from actual calibration tables."""

    @pytest.mark.skipif(
        not os.environ.get("TEST_BP_TABLE"),
        reason="Requires TEST_BP_TABLE environment variable",
    )
    def test_bandpass_normalization_from_table(self, calibration_table_paths):
        """Validate bandpass normalization from actual table."""

        from dsa110_contimg.qa.calibration_quality import validate_caltable_quality

        bp_table = calibration_table_paths["bandpass"]
        if not bp_table or not os.path.exists(bp_table):
            pytest.skip(f"Bandpass table not found: {bp_table}")

        metrics = validate_caltable_quality(bp_table)

        # Bandpass should be normalized to unity (solnorm=True)
        expected_median = 1.0
        tolerance = 0.05  # 5% tolerance

        median_amp = metrics.median_amplitude

        assert abs(median_amp - expected_median) < tolerance, (
            f"Bandpass median amplitude {median_amp:.3f} deviates from "
            f"expected {expected_median:.3f} by more than {tolerance:.3f}. "
            f"This indicates bandpass normalization error (solnorm may not be working)."
        )

    @pytest.mark.skipif(
        not os.environ.get("TEST_MS_PATH"),
        reason="Requires TEST_MS_PATH environment variable",
    )
    def test_model_data_flux_from_ms(self, ms_path, known_calibrator_info):
        """Validate MODEL_DATA flux from actual MS."""
        from casacore.tables import table

        if not ms_path or not os.path.exists(ms_path):
            pytest.skip(f"MS not found: {ms_path}")

        with table(ms_path, readonly=True) as tb:
            if "MODEL_DATA" not in tb.colnames():
                pytest.skip("MODEL_DATA column not present in MS")

            # Sample MODEL_DATA
            n_sample = min(1000, tb.nrows())
            model_data = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
            flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)

            # Get unflagged model data
            unflagged_model = model_data[~flags]
            if len(unflagged_model) == 0:
                pytest.skip("All MODEL_DATA is flagged")

            model_amps = np.abs(unflagged_model)
            model_amps = model_amps[model_amps > 1e-10]  # Filter near-zero

            if len(model_amps) == 0:
                pytest.skip("No valid MODEL_DATA found")

            median_flux = np.median(model_amps)
            catalog_flux = known_calibrator_info["flux_jy_1_4ghz"]
            tolerance = known_calibrator_info["tolerance_jy"]

            assert abs(median_flux - catalog_flux) < tolerance, (
                f"MODEL_DATA median flux {median_flux:.3f} Jy does not match "
                f"catalog flux {catalog_flux:.3f} Jy (tolerance: {tolerance:.3f} Jy). "
                f"This indicates MODEL_DATA population error."
            )


class TestActualCalibrationPhaseQuality:
    """Validate phase solution quality from actual calibration tables."""

    @pytest.mark.skipif(
        not os.environ.get("TEST_PREBP_TABLE"),
        reason="Requires TEST_PREBP_TABLE environment variable",
    )
    def test_prebandpass_phase_scatter_from_table(self, calibration_table_paths):
        """Validate pre-bandpass phase scatter from actual table."""
        from dsa110_contimg.qa.calibration_quality import validate_caltable_quality

        prebp_table = calibration_table_paths["prebandpass"]
        if not prebp_table or not os.path.exists(prebp_table):
            pytest.skip(f"Pre-bandpass table not found: {prebp_table}")

        metrics = validate_caltable_quality(prebp_table)

        # Pre-bandpass phase scatter should be < 20 degrees
        max_acceptable_scatter_deg = 20.0
        phase_scatter = metrics.phase_scatter_deg

        assert phase_scatter < max_acceptable_scatter_deg, (
            f"Pre-bandpass phase scatter {phase_scatter:.1f} degrees exceeds "
            f"maximum {max_acceptable_scatter_deg:.1f} degrees. "
            f"This indicates phase decorrelation or calibration error."
        )

    @pytest.mark.skipif(
        not os.environ.get("TEST_BP_TABLE"),
        reason="Requires TEST_BP_TABLE environment variable",
    )
    def test_bandpass_flagged_fraction_from_table(self, calibration_table_paths):
        """Validate bandpass flagged fraction from actual table."""
        from dsa110_contimg.qa.calibration_quality import validate_caltable_quality

        bp_table = calibration_table_paths["bandpass"]
        if not bp_table or not os.path.exists(bp_table):
            pytest.skip(f"Bandpass table not found: {bp_table}")

        metrics = validate_caltable_quality(bp_table)

        # Bandpass flagged fraction should be < 50%
        max_acceptable_flagged = 0.50  # 50%
        fraction_flagged = metrics.fraction_flagged

        assert fraction_flagged < max_acceptable_flagged, (
            f"Bandpass flagged fraction {fraction_flagged:.1%} exceeds "
            f"maximum {max_acceptable_flagged:.1%}. "
            f"This indicates calibration failure or poor data quality."
        )

        # Better target: < 30%
        target_flagged = 0.30
        if fraction_flagged > target_flagged:
            pytest.warn(
                UserWarning,
                f"Bandpass flagged fraction {fraction_flagged:.1%} exceeds "
                f"target {target_flagged:.1%} (though below maximum). "
                f"Consider improving calibration parameters.",
            )


class TestActualMSStructure:
    """Validate MS structure from actual MS files."""

    @pytest.mark.skipif(
        not os.environ.get("TEST_MS_PATH"),
        reason="Requires TEST_MS_PATH environment variable",
    )
    def test_ms_phase_center_alignment(self, ms_path, known_calibrator_info):
        """Validate MS phase center alignment from actual MS."""
        from astropy import units as u
        from astropy.coordinates import SkyCoord
        from casacore.tables import table

        if not ms_path or not os.path.exists(ms_path):
            pytest.skip(f"MS not found: {ms_path}")

        # Read REFERENCE_DIR from FIELD table
        with table(f"{ms_path}::FIELD", readonly=True) as tf:
            if "REFERENCE_DIR" not in tf.colnames():
                pytest.skip("REFERENCE_DIR not present in FIELD table")

            ref_dir = tf.getcol("REFERENCE_DIR")[0][0]  # Shape: (2,)
            ref_ra_rad = ref_dir[0]
            ref_dec_rad = ref_dir[1]

        # Convert to degrees
        ref_ra_deg = ref_ra_rad * 180.0 / np.pi
        ref_dec_deg = ref_dec_rad * 180.0 / np.pi

        # Compare with calibrator position
        cal_ra = known_calibrator_info["ra_deg"]
        cal_dec = known_calibrator_info["dec_deg"]

        ms_coord = SkyCoord(ra=ref_ra_deg * u.deg, dec=ref_dec_deg * u.deg, frame="icrs")
        cal_coord = SkyCoord(ra=cal_ra * u.deg, dec=cal_dec * u.deg, frame="icrs")
        separation = ms_coord.separation(cal_coord)

        # Separation must be < 1 arcmin for proper calibration
        max_separation_arcmin = 1.0
        separation_arcmin = separation.to(u.arcmin).value

        assert separation_arcmin < max_separation_arcmin, (
            f"MS phase center offset {separation_arcmin:.2f} arcmin exceeds "
            f"maximum {max_separation_arcmin:.2f} arcmin. "
            f"MS REFERENCE_DIR: RA={ref_ra_deg:.6f}°, Dec={ref_dec_deg:.6f}° "
            f"Calibrator: RA={cal_ra:.6f}°, Dec={cal_dec:.6f}° "
            f"This indicates MS phasing error (REFERENCE_DIR not updated correctly)."
        )

    @pytest.mark.skipif(
        not os.environ.get("TEST_MS_PATH"),
        reason="Requires TEST_MS_PATH environment variable",
    )
    def test_model_data_phase_scatter(self, ms_path):
        """Validate MODEL_DATA phase scatter from actual MS."""
        from casacore.tables import table

        if not ms_path or not os.path.exists(ms_path):
            pytest.skip(f"MS not found: {ms_path}")

        with table(ms_path, readonly=True) as tb:
            if "MODEL_DATA" not in tb.colnames():
                pytest.skip("MODEL_DATA column not present in MS")

            # Sample MODEL_DATA
            n_sample = min(1000, tb.nrows())
            model_data = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
            flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)

            # Get unflagged model data
            unflagged_model = model_data[~flags]
            if len(unflagged_model) == 0:
                pytest.skip("All MODEL_DATA is flagged")

            # Compute phase scatter
            phases_rad = np.angle(unflagged_model.flatten())
            phases_deg = np.degrees(phases_rad)
            phase_scatter_deg = np.std(phases_deg)

            # Phase scatter should be < 10 degrees (indicates proper alignment)
            max_acceptable_scatter_deg = 10.0

            assert phase_scatter_deg < max_acceptable_scatter_deg, (
                f"MODEL_DATA phase scatter {phase_scatter_deg:.1f} degrees exceeds "
                f"maximum {max_acceptable_scatter_deg:.1f} degrees. "
                f"This indicates MODEL_DATA phase structure error (misalignment)."
            )


class TestActualCASACompliance:
    """Validate CASA compliance from actual calibration tables."""

    @pytest.mark.skipif(
        not os.environ.get("TEST_BP_TABLE"),
        reason="Requires TEST_BP_TABLE environment variable",
    )
    def test_bandpass_table_structure(self, calibration_table_paths):
        """Validate bandpass table structure from actual table."""
        from casacore.tables import table

        bp_table = calibration_table_paths["bandpass"]
        if not bp_table or not os.path.exists(bp_table):
            pytest.skip(f"Bandpass table not found: {bp_table}")

        with table(bp_table, readonly=True) as tb:
            colnames = set(tb.colnames())

            # Required CASA columns
            required_columns = {"TIME", "ANTENNA1", "SPW", "CHAN", "CPARAM", "FLAG"}

            missing_columns = required_columns - colnames

            assert len(missing_columns) == 0, (
                f"Bandpass table missing required CASA columns: {missing_columns}. "
                f"Table has columns: {colnames}. "
                f"This indicates non-CASA-compliant table structure."
            )

            # Validate CPARAM shape
            if "CPARAM" in colnames:
                cparam = tb.getcol("CPARAM", startrow=0, nrow=1)
                # CPARAM shape: (n_pols, n_solutions)
                assert len(cparam.shape) >= 2, (
                    f"CPARAM shape {cparam.shape} is incorrect. "
                    f"Expected (n_pols, n_solutions) or higher dimensions."
                )

    @pytest.mark.skipif(
        not os.environ.get("TEST_G_TABLE"),
        reason="Requires TEST_G_TABLE environment variable",
    )
    def test_gain_table_structure(self, calibration_table_paths):
        """Validate gain table structure from actual table."""
        from casacore.tables import table

        g_table = calibration_table_paths["gain"]
        if not g_table or not os.path.exists(g_table):
            pytest.skip(f"Gain table not found: {g_table}")

        with table(g_table, readonly=True) as tb:
            colnames = set(tb.colnames())

            # Required CASA columns (gain table has no CHAN)
            required_columns = {"TIME", "ANTENNA1", "SPW", "CPARAM", "FLAG"}

            missing_columns = required_columns - colnames

            assert len(missing_columns) == 0, (
                f"Gain table missing required CASA columns: {missing_columns}. "
                f"Table has columns: {colnames}. "
                f"This indicates non-CASA-compliant table structure."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

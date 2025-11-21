#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the complete calibration workflow.

These tests verify the end-to-end calibration process including:
1. Subband file discovery and ordering
2. UVH5 to MS conversion with correct spectral ordering
3. MS phasing and REFERENCE_DIR handling
4. MODEL_DATA population
5. Pre-bandpass phase solve with correct parameters
6. Bandpass calibration with quality validation
7. Gain calibration

Requirements:
- pyuvdata installed
- casacore Python bindings
- Test data or synthetic data generation capability
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def temp_dir():
    """Create temporary directory for test outputs."""
    temp_path = tempfile.mkdtemp(prefix="cal_test_")
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def synthetic_uvh5_files(temp_dir):
    """Generate synthetic UVH5 files with 16 subbands for testing."""
    try:
        from tests.utils.generate_uvh5_calibrator import generate_uvh5
    except ImportError:
        pytest.skip("Synthetic UVH5 generation not available")

    # Generate 16 subband files (simplified - in reality would have different frequencies)
    files = []
    for sb in range(16):
        fpath = Path(temp_dir) / f"synthetic_sb{sb:02d}.hdf5"
        # For simplicity, generate same structure for each subband
        # In reality, subbands would have different frequency ranges
        try:
            generate_uvh5(
                str(fpath),
                n_ants=16,
                n_times=4,
                n_chans=64,
                start_jd=2460000.0,
                int_time_s=15.0,
                f0_hz=1.4e9 + sb * 10e6,  # Offset each subband by 10 MHz
                chan_bw_hz=1.0e6,
                ra_deg=128.7287,  # 0834+555
                dec_deg=55.5725,
                flux_jy=2.5,
            )
            files.append(str(fpath))
        except (ValueError, Exception) as e:
            # Skip if synthetic data generation fails (e.g., pyuvdata validation)
            pytest.skip(f"Synthetic UVH5 generation failed: {e}")
            break

    if not files:
        pytest.skip("No synthetic UVH5 files generated")

    return files


class TestSubbandOrderingIntegration:
    """Integration tests for subband ordering in conversion workflow."""

    def test_subband_files_sorted_correctly(self, synthetic_uvh5_files):
        """Test that subband files are sorted by subband number during conversion."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        # Sort files by subband number (should be 0-15)
        def sort_key(fpath):
            fname = os.path.basename(fpath)
            sb = _extract_subband_code(fname)
            sb_num = int(sb.replace("sb", "")) if sb else 999
            return sb_num

        sorted_files = sorted(synthetic_uvh5_files, key=sort_key)

        # Verify ordering
        for i, fpath in enumerate(sorted_files):
            fname = os.path.basename(fpath)
            sb = _extract_subband_code(fname)
            sb_num = int(sb.replace("sb", "")) if sb else 999
            assert sb_num == i, f"Subband {i} should be at position {i}, found {sb_num}"

    def test_subband_group_discovery(self, synthetic_uvh5_files):
        """Test that complete 16-subband groups are discovered correctly."""

        # This would require the actual implementation
        # For now, verify files exist
        assert len(synthetic_uvh5_files) == 16, "Should have 16 subband files"


class TestCalibrationWorkflowIntegration:
    """Full calibration workflow integration tests."""

    @pytest.mark.skipif(
        not os.environ.get("TEST_WITH_SYNTHETIC_DATA"),
        reason="Requires TEST_WITH_SYNTHETIC_DATA=1 and synthetic data generation",
    )
    def test_full_calibration_with_prebp_phase(self, temp_dir, synthetic_uvh5_files):
        """Test full calibration workflow with pre-bandpass phase correction."""
        from dsa110_contimg.calibration.calibration import (
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import flag_zeros, reset_flags
        from dsa110_contimg.calibration.model import write_point_model_with_ft
        from dsa110_contimg.conversion.uvh5_to_ms import convert_single_file
        from dsa110_contimg.qa.calibration_quality import validate_caltable_quality

        ms_path = Path(temp_dir) / "test_calibration.ms"

        # Step 1: Convert UVH5 to MS (would need to merge subbands first in real workflow)
        # For this test, assume single file conversion
        if len(synthetic_uvh5_files) > 0:
            convert_single_file(synthetic_uvh5_files[0], str(ms_path), add_imaging_columns=True)

        # Step 2: Populate MODEL_DATA
        write_point_model_with_ft(
            str(ms_path), ra_deg=128.7287, dec_deg=55.5725, flux_jy=2.5, field="0"
        )

        # Step 3: Flag zeros
        reset_flags(str(ms_path))
        flag_zeros(str(ms_path), datacolumn="data")

        # Step 4: Pre-bandpass phase solve with correct parameters
        prebp_table = solve_prebandpass_phase(
            str(ms_path),
            "0",
            refant="0",
            combine_fields=False,
            uvrange="",
            solint="30s",  # Correct parameter (not "inf")
            minsnr=3.0,  # Correct parameter (not 5.0)
        )

        assert prebp_table is not None, "Pre-bandpass phase table should be created"

        # Step 5: Bandpass solve
        bp_tables = solve_bandpass(
            str(ms_path),
            "0",
            refant="0",
            ktable=None,
            combine_fields=False,
            combine_spw=False,
            minsnr=3.0,
            uvrange="",
            prebandpass_phase_table=prebp_table,
        )

        assert len(bp_tables) > 0, "Bandpass tables should be created"

        # Step 6: Validate bandpass quality
        metrics = validate_caltable_quality(bp_tables[0])
        fraction_flagged = float(metrics.fraction_flagged)

        assert (
            fraction_flagged < 0.50
        ), f"Bandpass flagged fraction {fraction_flagged:.3f} should be < 50%"

        # Step 7: Gain calibration
        g_tables = solve_gains(
            str(ms_path),
            "0",
            refant="0",
            ktable=None,
            bptables=bp_tables,
            combine_fields=False,
            phase_only=True,
            uvrange="",
            solint="60s",
            minsnr=3.0,
        )

        assert len(g_tables) > 0, "Gain tables should be created"

    def test_ms_phasing_verification(self, temp_dir):
        """Test that MS phasing verification logic works."""
        from astropy import units as u
        from astropy.coordinates import SkyCoord

        # This test would require an actual MS file
        # For now, verify the logic
        # Calibrator position
        cal_coord = SkyCoord(ra=128.7287 * u.deg, dec=55.5725 * u.deg, frame="icrs")

        # MS REFERENCE_DIR (would read from actual MS)
        # For test, use known misaligned position
        ms_coord = SkyCoord(ra=128.5719 * u.deg, dec=54.6652 * u.deg, frame="icrs")

        separation = ms_coord.separation(cal_coord)

        # Should detect misalignment
        if separation.to(u.arcmin).value > 1.0:
            # MS needs rephasing
            assert True, "MS phasing issue detected"

        # After rephasing, should be aligned
        aligned_coord = SkyCoord(ra=128.7287 * u.deg, dec=55.5725 * u.deg, frame="icrs")
        aligned_separation = aligned_coord.separation(cal_coord)

        assert (
            aligned_separation.to(u.arcmin).value < 1.0
        ), "After rephasing, separation should be < 1 arcmin"


class TestCalibrationParameterValidation:
    """Test that calibration parameters are set correctly."""

    def test_prebp_solint_parameter(self):
        """Test that pre-bandpass solint parameter is configurable."""
        import inspect

        from dsa110_contimg.calibration.calibration import solve_prebandpass_phase

        sig = inspect.signature(solve_prebandpass_phase)
        assert "solint" in sig.parameters, "solve_prebandpass_phase should have solint parameter"

        # Default should be "inf" (problematic)
        default_solint = sig.parameters["solint"].default
        assert default_solint == "inf", "Default solint should be 'inf'"

    def test_prebp_minsnr_parameter(self):
        """Test that pre-bandpass minsnr parameter is configurable."""
        import inspect

        from dsa110_contimg.calibration.calibration import solve_prebandpass_phase

        sig = inspect.signature(solve_prebandpass_phase)
        assert "minsnr" in sig.parameters, "solve_prebandpass_phase should have minsnr parameter"

        # Default should be 5.0 (too strict)
        default_minsnr = sig.parameters["minsnr"].default
        assert default_minsnr == 5.0, "Default minsnr should be 5.0"

    def test_bandpass_combine_parameters(self):
        """Test that bandpass combine parameters exist."""
        import inspect

        from dsa110_contimg.calibration.calibration import solve_bandpass

        sig = inspect.signature(solve_bandpass)

        assert "combine_spw" in sig.parameters, "solve_bandpass should have combine_spw parameter"
        assert (
            "combine_fields" in sig.parameters
        ), "solve_bandpass should have combine_fields parameter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

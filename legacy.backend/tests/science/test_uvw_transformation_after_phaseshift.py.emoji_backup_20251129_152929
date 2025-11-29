"""Test to verify UVW transformation after phaseshift.

This test verifies that phaseshift correctly transforms UVW coordinates
for large phase shifts, which is critical for ft() to work correctly.
"""

import os
import shutil

import numpy as np
import pytest
from astropy.coordinates import Angle
from casacore.tables import table
from casatasks import phaseshift


@pytest.fixture
def ms_path():
    """Fixture for MS path (set via environment or pytest)."""
    return os.environ.get("TEST_MS_PATH", "")


@pytest.mark.skipif(
    not os.environ.get("TEST_MS_PATH"),
    reason="Requires TEST_MS_PATH environment variable",
)
def test_uvw_transformation_after_phaseshift(ms_path):
    """Test that phaseshift correctly transforms UVW coordinates.

    Strategy:
    1. Read original UVW coordinates
    2. Apply phaseshift to new phase center
    3. Check if UVW coordinates are transformed correctly
    4. Verify UVW frame matches new phase center
    """
    if not ms_path or not os.path.exists(ms_path):
        pytest.skip(f"MS not found: {ms_path}")

    # Make a copy of the MS for testing
    test_ms = ms_path.rstrip("/").rstrip(".ms") + "_uvw_test.ms"
    if os.path.exists(test_ms):
        shutil.rmtree(test_ms, ignore_errors=True)
    shutil.copytree(ms_path, test_ms)

    try:
        # Read original phase center and UVW
        with table(f"{test_ms}::FIELD", readonly=True) as field_tb:
            ref_dir_orig = field_tb.getcol("REFERENCE_DIR")[0][0]
            ref_ra_orig = ref_dir_orig[0] * 180.0 / np.pi
            ref_dec_orig = ref_dir_orig[1] * 180.0 / np.pi

        with table(test_ms, readonly=True) as main_tb:
            n_sample = min(1000, main_tb.nrows())
            uvw_orig = main_tb.getcol("UVW", startrow=0, nrow=n_sample)
            flags = main_tb.getcol("FLAG", startrow=0, nrow=n_sample)
            unflagged_mask = ~flags.any(axis=(1, 2))
            uvw_orig_unflagged = uvw_orig[unflagged_mask]

        # New phase center (calibrator position)
        new_ra_deg = 128.7287
        new_dec_deg = 55.5725

        # Format for phaseshift
        ra_hms = (
            Angle(new_ra_deg, unit="deg")
            .to_string(unit="hourangle", sep="hms", precision=2, pad=True)
            .replace(" ", "")
        )
        dec_dms = (
            Angle(new_dec_deg, unit="deg")
            .to_string(unit="deg", sep="dms", precision=2, alwayssign=True, pad=True)
            .replace(" ", "")
        )
        phasecenter_str = f"J2000 {ra_hms} {dec_dms}"

        # Apply phaseshift
        shifted_ms = test_ms.rstrip("/").rstrip(".ms") + "_shifted.ms"
        if os.path.exists(shifted_ms):
            shutil.rmtree(shifted_ms, ignore_errors=True)

        phaseshift(vis=test_ms, outputvis=shifted_ms, phasecenter=phasecenter_str)

        # Read UVW after phaseshift
        with table(shifted_ms, readonly=True) as main_tb:
            n_sample = min(1000, main_tb.nrows())
            uvw_new = main_tb.getcol("UVW", startrow=0, nrow=n_sample)
            flags = main_tb.getcol("FLAG", startrow=0, nrow=n_sample)
            unflagged_mask = ~flags.any(axis=(1, 2))
            uvw_new_unflagged = uvw_new[unflagged_mask]

        # Check if UVW changed
        uvw_diff = np.abs(uvw_orig_unflagged - uvw_new_unflagged)
        max_diff = np.max(uvw_diff)

        print("\nUVW Transformation Check:")
        print(f"  Original phase center: RA={ref_ra_orig:.6f}°, Dec={ref_dec_orig:.6f}°")
        print(f"  New phase center: RA={new_ra_deg:.6f}°, Dec={new_dec_deg:.6f}°")
        print(f"  Max UVW difference: {max_diff:.3f} meters")

        # For a large phase shift (54 arcmin), UVW should change significantly
        # Typical baseline length: ~100-400 meters
        # For 54 arcmin shift, expected UVW change: ~baseline_length * sin(54 arcmin) ≈ 1-2 meters

        if max_diff < 0.1:
            print("\n✗ UVW coordinates NOT transformed by phaseshift!")
            print("  This suggests phaseshift didn't update UVW correctly")
            print("  ft() will use old phase center frame (WRONG)")
            pytest.fail("phaseshift did not transform UVW coordinates")
        else:
            print("\n✓ UVW coordinates transformed by phaseshift")
            print(f"  Max change: {max_diff:.3f} meters (expected for large phase shift)")

        # Verify new phase center in FIELD table
        with table(f"{shifted_ms}::FIELD", readonly=True) as field_tb:
            phase_dir = field_tb.getcol("PHASE_DIR")[0][0]
            phase_ra = phase_dir[0] * 180.0 / np.pi
            phase_dec = phase_dir[1] * 180.0 / np.pi

            offset_ra = abs(phase_ra - new_ra_deg) * 3600  # arcsec
            offset_dec = abs(phase_dec - new_dec_deg) * 3600  # arcsec

            print("\nPHASE_DIR after phaseshift:")
            print(f"  RA={phase_ra:.6f}° (offset: {offset_ra:.3f} arcsec)")
            print(f"  Dec={phase_dec:.6f}° (offset: {offset_dec:.3f} arcsec)")

            if offset_ra > 1.0 or offset_dec > 1.0:
                print("\n✗ PHASE_DIR not correctly updated by phaseshift")
                pytest.fail("phaseshift did not update PHASE_DIR correctly")
            else:
                print("\n✓ PHASE_DIR correctly updated by phaseshift")

    finally:
        # Cleanup
        if os.path.exists(test_ms):
            shutil.rmtree(test_ms, ignore_errors=True)
        if os.path.exists(shifted_ms):
            shutil.rmtree(shifted_ms, ignore_errors=True)

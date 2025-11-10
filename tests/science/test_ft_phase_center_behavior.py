"""Test to understand how CASA ft() determines phase center.

This test creates a controlled experiment to determine:
1. Which column does ft() use: REFERENCE_DIR or PHASE_DIR?
2. Does ft() cache the phase center?
3. What happens if REFERENCE_DIR and PHASE_DIR differ?
"""

import pytest
import numpy as np
from casacore.tables import table
from casatasks import ft
from casatools import componentlist as cltool
import tempfile
import shutil
import os


@pytest.fixture
def ms_path():
    """Fixture for MS path (set via environment or pytest)."""
    return os.environ.get("TEST_MS_PATH", "")


@pytest.mark.skipif(
    not os.environ.get("TEST_MS_PATH"),
    reason="Requires TEST_MS_PATH environment variable",
)
def test_ft_uses_reference_dir_or_phase_dir(ms_path):
    """Test which phase center column ft() actually uses.

    Strategy:
    1. Create a test MS with REFERENCE_DIR != PHASE_DIR
    2. Set REFERENCE_DIR to position A
    3. Set PHASE_DIR to position B
    4. Call ft() with component at position A
    5. Check MODEL_DATA phase structure
    6. If MODEL_DATA matches position A, ft() uses REFERENCE_DIR
    7. If MODEL_DATA matches position B, ft() uses PHASE_DIR
    """
    if not ms_path or not os.path.exists(ms_path):
        pytest.skip(f"MS not found: {ms_path}")

    # Make a copy of the MS for testing
    test_ms = ms_path.rstrip("/").rstrip(".ms") + "_ft_test.ms"
    if os.path.exists(test_ms):
        shutil.rmtree(test_ms, ignore_errors=True)
    shutil.copytree(ms_path, test_ms)

    try:
        # Read current phase centers
        with table(f"{test_ms}::FIELD", readonly=False) as field_tb:
            ref_dir = field_tb.getcol("REFERENCE_DIR")[0][0].copy()
            phase_dir = field_tb.getcol("PHASE_DIR")[0][0].copy()

            # Set REFERENCE_DIR to position A (calibrator position)
            cal_ra_rad = 128.7287 * np.pi / 180.0
            cal_dec_rad = 55.5725 * np.pi / 180.0
            position_a = np.array([cal_ra_rad, cal_dec_rad])

            # Set PHASE_DIR to position B (offset by 1 degree)
            position_b = np.array(
                [cal_ra_rad + 1.0 * np.pi / 180.0, cal_dec_rad]  # 1 degree offset
            )

            # Set REFERENCE_DIR to position A
            field_tb.putcol("REFERENCE_DIR", position_a.reshape(1, 1, 2))

            # Set PHASE_DIR to position B
            field_tb.putcol("PHASE_DIR", position_b.reshape(1, 1, 2))

            print(
                f"Set REFERENCE_DIR to position A: RA={position_a[0]*180/np.pi:.6f}°, Dec={position_a[1]*180/np.pi:.6f}°"
            )
            print(
                f"Set PHASE_DIR to position B: RA={position_b[0]*180/np.pi:.6f}°, Dec={position_b[1]*180/np.pi:.6f}°"
            )

        # Create component list at position A
        comp_path = os.path.join(os.path.dirname(test_ms), "test_component.cl")
        if os.path.exists(comp_path):
            shutil.rmtree(comp_path, ignore_errors=True)

        cl = cltool()
        cl.addcomponent(
            dir={
                "refer": "J2000",
                "type": "direction",
                "long": f"{position_a[0]*180/np.pi}deg",
                "lat": f"{position_a[1]*180/np.pi}deg",
            },
            flux=2.5,
            fluxunit="Jy",
            freq="1.4GHz",
            shape="point",
        )
        cl.rename(comp_path)
        cl.close()

        # Clear MODEL_DATA
        with table(test_ms, readonly=False) as main_tb:
            if "MODEL_DATA" in main_tb.colnames():
                zeros = np.zeros(main_tb.getcol("MODEL_DATA").shape, dtype=np.complex64)
                main_tb.putcol("MODEL_DATA", zeros)

        # Call ft() - this should use one of the phase centers
        ft(vis=test_ms, complist=comp_path, usescratch=True, field="0")

        # Check MODEL_DATA phase structure
        with table(test_ms, readonly=True) as main_tb:
            n_sample = min(1000, main_tb.nrows())
            model_data = main_tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
            flags = main_tb.getcol("FLAG", startrow=0, nrow=n_sample)
            uvw = main_tb.getcol("UVW", startrow=0, nrow=n_sample)

            unflagged_mask = ~flags.any(axis=(1, 2))
            if unflagged_mask.sum() > 0:
                model_unflagged = model_data[unflagged_mask]
                uvw_unflagged = uvw[unflagged_mask]
                phases = np.angle(model_unflagged[:, 0, 0])

                u_coord = uvw_unflagged[:, 0]
                v_coord = uvw_unflagged[:, 1]
                wavelength = 3e8 / 1.4e9

                # Calculate expected phase for position A (REFERENCE_DIR)
                offset_ra_a = (
                    0.0  # Component at position A, MS phase center at position A
                )
                offset_dec_a = 0.0
                expected_phase_a = (
                    2
                    * np.pi
                    * (u_coord * offset_ra_a + v_coord * offset_dec_a)
                    / wavelength
                )
                expected_phase_a = np.mod(expected_phase_a + np.pi, 2 * np.pi) - np.pi

                # Calculate expected phase for position B (PHASE_DIR)
                offset_ra_b = (position_a[0] - position_b[0]) * np.cos(position_b[1])
                offset_dec_b = position_a[1] - position_b[1]
                expected_phase_b = (
                    2
                    * np.pi
                    * (u_coord * offset_ra_b + v_coord * offset_dec_b)
                    / wavelength
                )
                expected_phase_b = np.mod(expected_phase_b + np.pi, 2 * np.pi) - np.pi

                # Compare
                diff_a = phases - expected_phase_a
                diff_a = np.mod(diff_a + np.pi, 2 * np.pi) - np.pi
                diff_a_deg = np.degrees(diff_a)

                diff_b = phases - expected_phase_b
                diff_b = np.mod(diff_b + np.pi, 2 * np.pi) - np.pi
                diff_b_deg = np.degrees(diff_b)

                scatter_a = np.std(diff_a_deg)
                scatter_b = np.std(diff_b_deg)

                print(f"\nPhase comparison:")
                print(
                    f"  MODEL_DATA vs REFERENCE_DIR (position A): {scatter_a:.1f}° scatter"
                )
                print(
                    f"  MODEL_DATA vs PHASE_DIR (position B): {scatter_b:.1f}° scatter"
                )

                # Determine which phase center ft() used
                if scatter_a < 10:
                    print(f"\n✓ ft() USES REFERENCE_DIR for phase calculations")
                    assert scatter_a < 10, "ft() should use REFERENCE_DIR"
                elif scatter_b < 10:
                    print(f"\n✓ ft() USES PHASE_DIR for phase calculations")
                    assert scatter_b < 10, "ft() should use PHASE_DIR"
                else:
                    print(f"\n✗ ft() does NOT match either REFERENCE_DIR or PHASE_DIR")
                    print(f"  This suggests ft() uses a different source or has a bug")
                    pytest.fail("ft() phase center behavior unclear")

    finally:
        # Cleanup
        if os.path.exists(test_ms):
            shutil.rmtree(test_ms, ignore_errors=True)
        if os.path.exists(comp_path):
            shutil.rmtree(comp_path, ignore_errors=True)

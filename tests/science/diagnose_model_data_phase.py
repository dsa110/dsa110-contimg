#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic script to investigate MODEL_DATA phase structure issues.

This script identifies why MODEL_DATA has high phase scatter when it should
be nearly constant for a point source at the phase center.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from casacore.tables import table


def diagnose_model_data_phase(ms_path: str, cal_ra_deg: float, cal_dec_deg: float):
    """Diagnose MODEL_DATA phase structure issues."""

    print("=" * 70)
    print("MODEL_DATA Phase Structure Diagnosis")
    print("=" * 70)

    # 1. Check MS phase center
    print("\n1. MS Phase Center:")
    with table(f"{ms_path}::FIELD", readonly=True) as tf:
        if "REFERENCE_DIR" in tf.colnames():
            ref_dir = tf.getcol("REFERENCE_DIR")[0][0]
            ref_ra = ref_dir[0] * 180.0 / np.pi
            ref_dec = ref_dir[1] * 180.0 / np.pi
            print(f"   REFERENCE_DIR: RA={ref_ra:.6f}°, Dec={ref_dec:.6f}°")

        if "PHASE_DIR" in tf.colnames():
            phase_dir = tf.getcol("PHASE_DIR")[0][0]
            phase_ra = phase_dir[0] * 180.0 / np.pi
            phase_dec = phase_dir[1] * 180.0 / np.pi
            print(f"   PHASE_DIR:      RA={phase_ra:.6f}°, Dec={phase_dec:.6f}°")

    print(f"   Calibrator:     RA={cal_ra_deg:.6f}°, Dec={cal_dec_deg:.6f}°")

    ms_coord = SkyCoord(ra=ref_ra * u.deg, dec=ref_dec * u.deg, frame="icrs")
    cal_coord = SkyCoord(ra=cal_ra_deg * u.deg, dec=cal_dec_deg * u.deg, frame="icrs")

    # Use u_coord and v_coord for UVW coordinates to avoid conflict with astropy units 'u'
    u_coord = None
    v_coord = None
    separation = ms_coord.separation(cal_coord)
    print(f"   Separation: {separation.to(u.arcmin):.4f}")

    if separation.to(u.arcmin).value > 1.0:
        print(f"   ✗ PROBLEM: Phase center offset > 1 arcmin!")
    else:
        print(f"   ✓ Phase center aligned")

    # 2. Check MODEL_DATA phase structure
    print("\n2. MODEL_DATA Phase Structure:")
    with table(ms_path, readonly=True) as tb:
        if "MODEL_DATA" not in tb.colnames():
            print("   ✗ MODEL_DATA column not present")
            return

        n_sample = min(5000, tb.nrows())
        model_data = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
        flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)
        uvw = tb.getcol("UVW", startrow=0, nrow=n_sample)

        unflagged_mask = ~flags.any(axis=(1, 2))
        if unflagged_mask.sum() == 0:
            print("   ✗ All MODEL_DATA is flagged")
            return

        model_unflagged = model_data[unflagged_mask]
        uvw_unflagged = uvw[unflagged_mask]

        # Amplitude
        amps = np.abs(model_unflagged)
        print(
            f"   Amplitude: median={np.median(amps):.3f} Jy, std={np.std(amps):.3f} Jy"
        )

        # Phase
        phases_rad = np.angle(model_unflagged[:, 0, 0])  # First channel, first pol
        phases_deg = np.degrees(phases_rad)
        print(
            f"   Phase:      mean={np.mean(phases_deg):.1f}°, std={np.std(phases_deg):.1f}°"
        )

        if np.std(phases_deg) > 50:
            print(f"   ✗ PROBLEM: Phase scatter too high ({np.std(phases_deg):.1f}°)")
            print(f"      Expected: < 10° for point source at phase center")
        else:
            print(f"   ✓ Phase scatter acceptable")

        # 3. Calculate expected phase for point source
        print("\n3. Expected Phase Calculation:")

        # For point source at phase center, phase should be constant
        # For point source offset from phase center:
        #   phase = 2π * (u*ΔRA + v*ΔDec) / λ
        # where ΔRA, ΔDec are offsets from phase center

        offset_ra_rad = (
            (cal_ra_deg - ref_ra) * np.pi / 180.0 * np.cos(ref_dec * np.pi / 180.0)
        )
        offset_dec_rad = (cal_dec_deg - ref_dec) * np.pi / 180.0

        wavelength = 3e8 / 1.4e9  # meters at 1.4 GHz

        u_coord = uvw_unflagged[:, 0]  # u coordinate in meters
        v_coord = uvw_unflagged[:, 1]  # v coordinate in meters

        # Expected phase for point source
        expected_phase = (
            2
            * np.pi
            * (u_coord * offset_ra_rad + v_coord * offset_dec_rad)
            / wavelength
        )
        expected_phase = (
            np.mod(expected_phase + np.pi, 2 * np.pi) - np.pi
        )  # Wrap to [-π, π]
        expected_phase_deg = np.degrees(expected_phase)

        print(
            f"   Source offset: ΔRA={offset_ra_rad*180/np.pi*3600:.2f} arcsec, "
            f"ΔDec={offset_dec_rad*180/np.pi*3600:.2f} arcsec"
        )
        print(f"   Expected phase scatter: {np.std(expected_phase_deg):.1f}°")

        # Compare actual vs expected
        phase_diff = phases_rad - expected_phase
        phase_diff = np.mod(phase_diff + np.pi, 2 * np.pi) - np.pi
        phase_diff_deg = np.degrees(phase_diff)

        print(f"   Actual - Expected phase scatter: {np.std(phase_diff_deg):.1f}°")

        if np.std(phase_diff_deg) > 50:
            print(
                f"   ✗ PROBLEM: MODEL_DATA phase doesn't match expected phase structure"
            )
            print(f"      This indicates ft() calculated MODEL_DATA incorrectly")
            print(f"      Possible causes:")
            print(f"        1. Component list position doesn't match MS phase center")
            print(f"        2. ft() is using wrong phase center reference")
            print(
                f"        3. MODEL_DATA was written before MS rephasing and not properly cleared"
            )
            print(f"        4. ft() has a bug with phase calculation")
        else:
            print(f"   ✓ MODEL_DATA phase matches expected structure")

    # 4. Check if component list exists and verify position
    print("\n4. Component List Check:")
    comp_path = Path(ms_path).parent / "cal_component.cl"
    if comp_path.exists():
        print(f"   Component list found: {comp_path}")
        # Note: Can't easily read component list position without CASA tools
        print(
            f"   (Component list position should match calibrator: "
            f"RA={cal_ra_deg:.6f}°, Dec={cal_dec_deg:.6f}°)"
        )
    else:
        print(f"   Component list not found (expected at: {comp_path})")
        print(f"   (This is normal - component list may have been cleaned up)")

    print("\n" + "=" * 70)
    print("Diagnosis Complete")
    print("=" * 70)


if __name__ == "__main__":
    ms_path = "/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.ms"
    cal_ra = 128.7287
    cal_dec = 55.5725

    diagnose_model_data_phase(ms_path, cal_ra, cal_dec)

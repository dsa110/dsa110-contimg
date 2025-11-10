#!/usr/bin/env python3
"""Investigate MODEL_DATA phase center vs field phase centers."""
from casacore.tables import table
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
import sys

sys.path.insert(0, "src")
from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec

ms_path = "/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms"

print("=" * 70)
print("INVESTIGATING MODEL_DATA PHASE CENTER vs FIELD PHASE CENTERS")
print("=" * 70)

# Get expected coordinates
catalog = load_vla_catalog()
expected_ra_deg, expected_dec_deg = get_calibrator_radec(catalog, "0834+555")
expected_coord = SkyCoord(
    expected_ra_deg * u.deg, expected_dec_deg * u.deg, frame="icrs"
)

print(f"\nExpected 0834+555: RA={expected_ra_deg:.10f}°, Dec={expected_dec_deg:.10f}°")

# Get field phase centers
with table(ms_path + "/FIELD", readonly=True) as field:
    phase_dirs = field.getcol("PHASE_DIR")
    field_ra_deg = np.rad2deg(phase_dirs[0][0][0])
    field_dec_deg = np.rad2deg(phase_dirs[0][0][1])
    field_coord = SkyCoord(field_ra_deg * u.deg, field_dec_deg * u.deg, frame="icrs")

    print(f"Field PHASE_DIR: RA={field_ra_deg:.10f}°, Dec={field_dec_deg:.10f}°")

    # Check REFERENCE_DIR
    if "REFERENCE_DIR" in field.colnames():
        ref_dirs = field.getcol("REFERENCE_DIR")
        ref_ra_deg = np.rad2deg(ref_dirs[0][0][0])
        ref_dec_deg = np.rad2deg(ref_dirs[0][0][1])
        ref_coord = SkyCoord(ref_ra_deg * u.deg, ref_dec_deg * u.deg, frame="icrs")

        print(f"Field REFERENCE_DIR: RA={ref_ra_deg:.10f}°, Dec={ref_dec_deg:.10f}°")

        ref_phase_sep = ref_coord.separation(field_coord).arcsec
        print(f"REFERENCE_DIR vs PHASE_DIR offset: {ref_phase_sep:.6f} arcsec")

# Check component list phase center
cl_path = "/stage/dsa110-contimg/ms/0834_20251029/0834+555.cl"

print(f'\n{"="*70}')
print("Checking component list phase center:")
print(f'{"="*70}')

try:
    from casatools import componentlist as cltool

    cl = cltool()
    cl.open(cl_path)

    comp = cl.getcomponent(0)
    cl_dir = comp["direction"]
    cl_ra_rad = cl_dir["m0"]["value"]
    cl_dec_rad = cl_dir["m1"]["value"]
    cl_ra_deg = np.rad2deg(cl_ra_rad)
    cl_dec_deg = np.rad2deg(cl_dec_rad)
    cl_coord = SkyCoord(cl_ra_deg * u.deg, cl_dec_deg * u.deg, frame="icrs")

    print(f"Component list direction: RA={cl_ra_deg:.10f}°, Dec={cl_dec_deg:.10f}°")

    # Compare to expected
    cl_expected_sep = cl_coord.separation(expected_coord).arcsec
    print(f"Component list vs expected offset: {cl_expected_sep:.6f} arcsec")

    # Compare to field
    cl_field_sep = cl_coord.separation(field_coord).arcsec
    print(f"Component list vs FIELD PHASE_DIR offset: {cl_field_sep:.6f} arcsec")

    cl.close()
    cl.done()
except Exception as e:
    print(f"Error reading component list: {e}")
    import traceback

    traceback.print_exc()

# Check MODEL_DATA phase structure by field
print(f'\n{"="*70}')
print("Checking MODEL_DATA phase structure by field:")
print(f'{"="*70}')

with table(ms_path, readonly=True) as tb:
    # Get FIELD_ID for each row
    field_ids = tb.getcol("FIELD_ID")
    unique_fields = np.unique(field_ids)

    print(f"\nUnique fields in data: {len(unique_fields)}")

    # Sample MODEL_DATA from different fields
    for field_id in unique_fields[:5]:  # Check first 5 fields
        field_mask = field_ids == field_id
        field_rows = np.where(field_mask)[0]

        if len(field_rows) > 0:
            sample_size = min(100, len(field_rows))
            model_data = tb.getcol(
                "MODEL_DATA", startrow=field_rows[0], nrow=sample_size
            )

            # Check if MODEL_DATA is purely real (phase = 0) for this field
            flat_data = model_data.flatten()
            non_zero = flat_data[flat_data != 0]

            if len(non_zero) > 0:
                phases = np.angle(non_zero)
                phase_std_deg = np.std(phases) * 180 / np.pi
                max_imag = np.max(np.abs(np.imag(non_zero)))

                print(f"\nField {field_id}:")
                print(f"  Rows sampled: {sample_size}")
                print(f"  Phase std: {phase_std_deg:.6f}°")
                print(f"  Max |imag|: {max_imag:.6e}")

                if phase_std_deg < 0.01 and max_imag < 1e-6:
                    print(
                        f"  ✓ MODEL_DATA is purely real (phase ≈ 0) - consistent with source at phase center"
                    )
                else:
                    print(
                        f"  ✗ MODEL_DATA has phase variation - may indicate source not at phase center"
                    )

print("\n" + "=" * 70)

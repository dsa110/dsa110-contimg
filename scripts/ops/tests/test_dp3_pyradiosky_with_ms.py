#!/opt/miniforge/envs/casa6/bin/python
"""
Full integration test of pyradiosky + DP3 with actual MS file.

This script:
1. Creates a sky model using pyradiosky
2. Converts it to DP3 format
3. Uses DP3 predict to populate MODEL_DATA
4. Validates the results
"""

import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import os
import tempfile
import time

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from casacore.tables import table
from pyradiosky import SkyModel

from dsa110_contimg.calibration.dp3_wrapper import (_find_dp3_executable,
                                                    convert_skymodel_to_dp3,
                                                    predict_from_skymodel_dp3)


def get_ms_info(ms_path: str):
    """Get basic info about the MS."""
    try:
        t = table(ms_path, readonly=True)
        nrows = t.nrows()
        colnames = t.colnames()
        has_model = "MODEL_DATA" in colnames
        
        # Get field info
        field_table = table(ms_path + "/FIELD", readonly=True)
        nfields = field_table.nrows()
        if nfields > 0:
            phase_dir_col = field_table.getcol("PHASE_DIR")
            # PHASE_DIR shape is typically (nfields, 1, 2) where last dim is [RA, Dec] in radians
            # For first field: phase_dir_col[0] has shape (1, 2)
            phase_dir = phase_dir_col[0]  # First field, shape (1, 2)
            phase_ra = phase_dir[0, 0] * 180 / np.pi  # RA in degrees
            phase_dec = phase_dir[0, 1] * 180 / np.pi  # Dec in degrees
        else:
            phase_ra = phase_dec = None
        field_table.close()
        
        t.close()
        return {
            "nrows": nrows,
            "has_model": has_model,
            "nfields": nfields,
            "phase_ra": phase_ra,
            "phase_dec": phase_dec,
        }
    except Exception as e:
        print(f"Error reading MS: {e}")
        return None


def create_test_skymodel(center_ra_deg: float, center_dec_deg: float, n_sources: int = 5):
    """Create a test sky model around the MS phase center."""
    # Create sources around the phase center
    ra_offsets = np.linspace(-0.1, 0.1, n_sources)  # degrees
    dec_offsets = np.linspace(-0.1, 0.1, n_sources)
    
    ra_values = center_ra_deg + ra_offsets
    dec_values = center_dec_deg + dec_offsets
    flux_values = np.linspace(2.0, 0.5, n_sources)  # Jy, decreasing
    
    ra = ra_values * u.deg
    dec = dec_values * u.deg
    stokes = np.zeros((4, 1, n_sources))
    stokes[0, 0, :] = flux_values  # I flux in Jy
    
    skycoord = SkyCoord(ra=ra, dec=dec, frame='icrs')
    
    sky = SkyModel(
        name=[f"test_source_{i}" for i in range(n_sources)],
        skycoord=skycoord,
        stokes=stokes * u.Jy,
        spectral_type='flat',
        component_type='point',
    )
    
    return sky


def check_model_data(ms_path: str):
    """Check if MODEL_DATA was populated."""
    try:
        t = table(ms_path, readonly=True)
        if "MODEL_DATA" not in t.colnames():
            t.close()
            return False, "MODEL_DATA column does not exist"
        
        # Check a few rows
        sample_rows = min(10, t.nrows())
        model_sum = 0.0
        for i in range(sample_rows):
            model_data = t.getcell("MODEL_DATA", i)
            if model_data is not None:
                model_sum += np.abs(model_data).sum()
        
        t.close()
        
        if model_sum > 0:
            return True, f"MODEL_DATA populated (sample sum: {model_sum:.2e})"
        else:
            return False, "MODEL_DATA exists but appears to be zero"
    except Exception as e:
        return False, f"Error checking MODEL_DATA: {e}"


def main():
    """Run full integration test."""
    ms_path = "/tmp/dp3_pyradiosky_test/test_ms.ms"
    
    print("=" * 60)
    print("Full Integration Test: pyradiosky + DP3 with MS")
    print("=" * 60)
    print()
    
    # Check MS exists
    if not os.path.exists(ms_path):
        print(f":cross: MS not found: {ms_path}")
        return 1
    
    print(f":check: MS found: {ms_path}")
    
    # Get MS info
    print("\n" + "-" * 60)
    print("MS Information")
    print("-" * 60)
    ms_info = get_ms_info(ms_path)
    if ms_info is None:
        print(":cross: Failed to read MS")
        return 1
    
    print(f"  Rows: {ms_info['nrows']:,}")
    print(f"  Fields: {ms_info['nfields']}")
    print(f"  Phase center: RA={ms_info['phase_ra']:.6f}°, Dec={ms_info['phase_dec']:.6f}°")
    print(f"  MODEL_DATA exists: {ms_info['has_model']}")
    
    # Check DP3 availability
    print("\n" + "-" * 60)
    print("DP3 Availability")
    print("-" * 60)
    dp3_cmd = _find_dp3_executable()
    if not dp3_cmd:
        print(":cross: DP3 not found")
        return 1
    print(f":check: DP3 available: {dp3_cmd}")
    
    # Create sky model
    print("\n" + "-" * 60)
    print("Creating Sky Model with pyradiosky")
    print("-" * 60)
    try:
        sky = create_test_skymodel(
            center_ra_deg=ms_info['phase_ra'],
            center_dec_deg=ms_info['phase_dec'],
            n_sources=5,
        )
        print(f":check: Created SkyModel with {sky.Ncomponents} sources")
        print(f"  Component type: {sky.component_type}")
        print(f"  Spectral type: {sky.spectral_type}")
    except Exception as e:
        print(f":cross: Failed to create SkyModel: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Convert to DP3 format
    print("\n" + "-" * 60)
    print("Converting to DP3 Format")
    print("-" * 60)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.skymodel', delete=False) as f:
        dp3_path = f.name
    
    try:
        result_path = convert_skymodel_to_dp3(sky, out_path=dp3_path)
        print(f":check: Converted to DP3 format: {result_path}")
        
        # Check file
        file_size = os.path.getsize(result_path)
        with open(result_path, 'r') as f:
            lines = f.readlines()
        print(f"  File size: {file_size} bytes")
        print(f"  Sources: {len(lines) - 1}")  # -1 for header
    except Exception as e:
        print(f":cross: Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(dp3_path):
            os.unlink(dp3_path)
        return 1
    
    # Check MODEL_DATA before
    print("\n" + "-" * 60)
    print("MODEL_DATA Before DP3 Predict")
    print("-" * 60)
    before_ok, before_msg = check_model_data(ms_path)
    print(f"  Status: {before_msg}")
    
    # Run DP3 predict
    print("\n" + "-" * 60)
    print("Running DP3 Predict")
    print("-" * 60)
    start_time = time.time()
    try:
        predict_from_skymodel_dp3(
            ms_path=ms_path,
            sky_model_path=dp3_path,
            field="",  # All fields
            use_beam=False,
            operation="replace",
        )
        elapsed = time.time() - start_time
        print(f":check: DP3 predict completed in {elapsed:.2f} seconds")
    except Exception as e:
        print(f":cross: DP3 predict failed: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(dp3_path):
            os.unlink(dp3_path)
        return 1
    
    # Check MODEL_DATA after
    print("\n" + "-" * 60)
    print("MODEL_DATA After DP3 Predict")
    print("-" * 60)
    after_ok, after_msg = check_model_data(ms_path)
    print(f"  Status: {after_msg}")
    
    # Cleanup
    if os.path.exists(dp3_path):
        os.unlink(dp3_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"MS: {ms_path}")
    print(f"Sky Model: {sky.Ncomponents} sources")
    print(f"DP3 Predict: {':check:' if after_ok else ':cross:'}")
    print(f"MODEL_DATA: {':check: Populated' if after_ok else ':cross: Not populated'}")
    
    if after_ok:
        print("\n:check: Full integration test PASSED")
        print("  pyradiosky + DP3 workflow is working correctly")
        return 0
    else:
        print("\n:cross: Integration test FAILED")
        print("  Check output above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())


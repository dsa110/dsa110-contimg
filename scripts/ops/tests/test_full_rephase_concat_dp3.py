#!/opt/miniforge/envs/casa6/bin/python
"""
Full test of rephasing + concatenation + DP3 workflow.

This script:
1. Rephases all fields to common phase center
2. Concatenates fields into single field
3. Uses DP3 predict on the concatenated MS
4. Validates MODEL_DATA
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

from dsa110_contimg.calibration.dp3_wrapper import (convert_skymodel_to_dp3,
                                                    predict_from_skymodel_dp3,
                                                    prepare_ms_for_dp3)


def check_model_data(ms_path: str):
    """Check if MODEL_DATA was populated."""
    try:
        t = table(ms_path, readonly=True)
        if "MODEL_DATA" not in t.colnames():
            t.close()
            return False, "MODEL_DATA column does not exist"
        
        # Check a few rows
        sample_rows = min(100, t.nrows())
        model_sum = 0.0
        non_zero_count = 0
        for i in range(sample_rows):
            model_data = t.getcell("MODEL_DATA", i)
            if model_data is not None:
                abs_sum = np.abs(model_data).sum()
                model_sum += abs_sum
                if abs_sum > 0:
                    non_zero_count += 1
        
        t.close()
        
        if model_sum > 0:
            return True, f"MODEL_DATA populated (sample: {non_zero_count}/{sample_rows} non-zero, sum: {model_sum:.2e})"
        else:
            return False, "MODEL_DATA exists but appears to be zero"
    except Exception as e:
        return False, f"Error checking MODEL_DATA: {e}"


def main():
    """Run full integration test."""
    ms_path = "/tmp/dp3_pyradiosky_test/test_ms.ms"
    
    print("=" * 60)
    print("Full Test: Rephase + Concatenate + DP3")
    print("=" * 60)
    print()
    
    # Get phase center for rephasing
    field_table = table(ms_path + "/FIELD", readonly=True)
    phase_dirs = field_table.getcol("PHASE_DIR")
    target_ra = np.degrees(phase_dirs[0][0, 0])
    target_dec = np.degrees(phase_dirs[0][0, 1])
    nfields = field_table.nrows()
    field_table.close()
    
    print(f"Input MS: {ms_path}")
    print(f"  Fields: {nfields}")
    print(f"  Target phase center: RA={target_ra:.6f}°, Dec={target_dec:.6f}°")
    
    # Step 1: Prepare MS (rephase + concatenate)
    print("\n" + "-" * 60)
    print("Step 1: Preparing MS (rephase + concatenate)")
    print("-" * 60)
    start_time = time.time()
    
    try:
        prepared_ms = prepare_ms_for_dp3(
            ms_path=ms_path,
            target_ra_deg=target_ra,
            target_dec_deg=target_dec,
            output_ms_path="/tmp/dp3_pyradiosky_test/test_ms_prepared.ms",
            keep_copy=True,
        )
        prep_time = time.time() - start_time
        print(f":check: MS prepared in {prep_time:.2f} seconds")
        print(f"  Prepared MS: {prepared_ms}")
        
        # Verify it's single field
        field_table = table(prepared_ms + "/FIELD", readonly=True)
        nfields_prep = field_table.nrows()
        field_table.close()
        print(f"  Fields after preparation: {nfields_prep}")
        if nfields_prep != 1:
            print(f"  :warning: Expected 1 field, got {nfields_prep}")
    except Exception as e:
        print(f":cross: MS preparation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 2: Create sky model
    print("\n" + "-" * 60)
    print("Step 2: Creating sky model with pyradiosky")
    print("-" * 60)
    
    # Create stokes array with correct shape: (4, Nfreqs, Ncomponents)
    # For flat spectrum: Nfreqs=1, Ncomponents=1
    stokes = np.zeros((4, 1, 1)) * u.Jy
    stokes[0, 0, 0] = 2.3 * u.Jy  # I flux
    
    sky = SkyModel(
        name=["test_source"],
        skycoord=SkyCoord(ra=target_ra*u.deg, dec=target_dec*u.deg, frame='icrs'),
        stokes=stokes,
        spectral_type='flat',
        component_type='point',
    )
    print(f":check: Created SkyModel")
    
    # Step 3: Convert to DP3 format
    print("\n" + "-" * 60)
    print("Step 3: Converting to DP3 format")
    print("-" * 60)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.skymodel', delete=False) as f:
        dp3_path = f.name
    
    try:
        convert_skymodel_to_dp3(sky, out_path=dp3_path)
        print(f":check: Converted to DP3 format: {dp3_path}")
    except Exception as e:
        print(f":cross: Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 4: Check MODEL_DATA before
    print("\n" + "-" * 60)
    print("Step 4: MODEL_DATA Before DP3 Predict")
    print("-" * 60)
    before_ok, before_msg = check_model_data(prepared_ms)
    print(f"  {before_msg}")
    
    # Step 5: Run DP3 predict
    print("\n" + "-" * 60)
    print("Step 5: Running DP3 Predict")
    print("-" * 60)
    start_time = time.time()
    
    try:
        predict_from_skymodel_dp3(
            ms_path=prepared_ms,
            sky_model_path=dp3_path,
            field="",  # Single field now, so empty is fine
        )
        dp3_time = time.time() - start_time
        print(f":check: DP3 predict completed in {dp3_time:.2f} seconds")
    except Exception as e:
        print(f":cross: DP3 predict failed: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(dp3_path):
            os.unlink(dp3_path)
        return 1
    
    # Step 6: Check MODEL_DATA after
    print("\n" + "-" * 60)
    print("Step 6: MODEL_DATA After DP3 Predict")
    print("-" * 60)
    after_ok, after_msg = check_model_data(prepared_ms)
    print(f"  {after_msg}")
    
    # Cleanup
    if os.path.exists(dp3_path):
        os.unlink(dp3_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Input MS: {nfields} fields")
    print(f"Prepared MS: Single field")
    print(f"Preparation time: {prep_time:.2f} seconds")
    print(f"DP3 predict time: {dp3_time:.2f} seconds")
    print(f"Total time: {prep_time + dp3_time:.2f} seconds")
    print(f"MODEL_DATA: {':check: Populated' if after_ok else ':cross: Not populated'}")
    
    if after_ok:
        print("\n:check: Full workflow PASSED")
        print("  Rephasing + Concatenation + DP3 is working!")
        return 0
    else:
        print("\n:cross: Workflow FAILED")
        print("  Check output above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())


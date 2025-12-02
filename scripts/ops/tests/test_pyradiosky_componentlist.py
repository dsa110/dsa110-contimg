#!/opt/miniforge/envs/casa6/bin/python
"""
Test pyradiosky :arrow_right: componentlist :arrow_right: CASA ft() workflow.

This is the recommended workflow since DP3 cannot handle 2-pol MS files.
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

from dsa110_contimg.calibration.skymodels import (
  convert_skymodel_to_componentlist, ft_from_cl)


def check_model_data(ms_path: str):
    """Check if MODEL_DATA was populated."""
    try:
        t = table(ms_path, readonly=True)
        if "MODEL_DATA" not in t.colnames():
            t.close()
            return False, "MODEL_DATA column does not exist"
        
        # Check a sample of rows
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
    """Test pyradiosky :arrow_right: componentlist :arrow_right: ft() workflow."""
    ms_path = "/tmp/dp3_pyradiosky_test/test_ms.ms"
    
    print("=" * 60)
    print("Test: pyradiosky :arrow_right: componentlist :arrow_right: CASA ft()")
    print("=" * 60)
    print()
    print("This is the recommended workflow for 2-pol MS files.")
    print("(DP3 requires 4-pol, so CASA ft() is used instead)")
    print()
    
    # Get MS phase center
    field_table = table(ms_path + "/FIELD", readonly=True)
    phase_dirs = field_table.getcol("PHASE_DIR")
    target_ra = np.degrees(phase_dirs[0][0, 0])
    target_dec = np.degrees(phase_dirs[0][0, 1])
    field_table.close()
    
    print(f"MS: {ms_path}")
    print(f"Phase center: RA={target_ra:.6f}°, Dec={target_dec:.6f}°")
    
    # Step 1: Create sky model with pyradiosky
    print("\n" + "-" * 60)
    print("Step 1: Creating sky model with pyradiosky")
    print("-" * 60)
    
    stokes = np.zeros((4, 1, 1)) * u.Jy
    stokes[0, 0, 0] = 2.3 * u.Jy  # I flux
    
    sky = SkyModel(
        name=["test_source"],
        skycoord=SkyCoord(ra=target_ra*u.deg, dec=target_dec*u.deg, frame='icrs'),
        stokes=stokes,
        spectral_type='flat',
        component_type='point',
    )
    print(f":check: Created SkyModel with {sky.Ncomponents} source(s)")
    
    # Step 2: Convert to componentlist
    print("\n" + "-" * 60)
    print("Step 2: Converting to CASA componentlist")
    print("-" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cl_path = os.path.join(tmpdir, "model.cl")
        
        try:
            result_path = convert_skymodel_to_componentlist(sky, out_path=cl_path)
            print(f":check: Converted to componentlist: {result_path}")
            
            # Verify it exists
            if os.path.exists(result_path):
                print(f"  Componentlist exists: :check:")
            else:
                print(f"  Componentlist exists: :cross:")
                return 1
        except Exception as e:
            print(f":cross: Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Step 3: Check MODEL_DATA before
        print("\n" + "-" * 60)
        print("Step 3: MODEL_DATA Before CASA ft()")
        print("-" * 60)
        before_ok, before_msg = check_model_data(ms_path)
        print(f"  {before_msg}")
        
        # Step 4: Use CASA ft()
        print("\n" + "-" * 60)
        print("Step 4: Running CASA ft()")
        print("-" * 60)
        start_time = time.time()
        
        try:
            ft_from_cl(ms_path, cl_path, field="0")
            ft_time = time.time() - start_time
            print(f":check: CASA ft() completed in {ft_time:.2f} seconds")
        except Exception as e:
            print(f":cross: CASA ft() failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Step 5: Check MODEL_DATA after
        print("\n" + "-" * 60)
        print("Step 5: MODEL_DATA After CASA ft()")
        print("-" * 60)
        after_ok, after_msg = check_model_data(ms_path)
        print(f"  {after_msg}")
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"pyradiosky SkyModel: :check: Created")
        print(f"Componentlist conversion: :check:")
        print(f"CASA ft() time: {ft_time:.2f} seconds")
        print(f"MODEL_DATA: {':check: Populated' if after_ok else ':cross: Not populated'}")
        
        if after_ok:
            print("\n:check: Full workflow PASSED")
            print("  pyradiosky :arrow_right: componentlist :arrow_right: CASA ft() is working!")
            return 0
        else:
            print("\n:cross: Workflow FAILED")
            return 1


if __name__ == "__main__":
    sys.exit(main())


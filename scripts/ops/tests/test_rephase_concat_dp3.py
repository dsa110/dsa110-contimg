#!/opt/miniforge/envs/casa6/bin/python
"""
Test rephasing + concatenation approach for DP3.

This script:
1. Rephases all fields to a common phase center
2. Concatenates fields into single field
3. Tests DP3 predict on the concatenated MS
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os
import shutil
import tempfile

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from casacore.tables import table
from pyradiosky import SkyModel

from dsa110_contimg.calibration.dp3_wrapper import (convert_skymodel_to_dp3,
                                                    predict_from_skymodel_dp3)


def get_ms_phase_center(ms_path: str, field_id: int = 0):
    """Get phase center of a field."""
    field_table = table(ms_path + "/FIELD", readonly=True)
    phase_dirs = field_table.getcol("PHASE_DIR")
    phase_dir = phase_dirs[field_id]
    ra_rad = phase_dir[0, 0]
    dec_rad = phase_dir[0, 1]
    field_table.close()
    return np.degrees(ra_rad), np.degrees(dec_rad)


def test_rephase_concat_approach():
    """Test the rephasing + concatenation approach."""
    ms_path = "/tmp/dp3_pyradiosky_test/test_ms.ms"
    test_ms_copy = "/tmp/dp3_pyradiosky_test/test_ms_rephased.ms"
    
    print("=" * 60)
    print("Testing Rephasing + Concatenation for DP3")
    print("=" * 60)
    
    # Step 1: Check current state
    print("\n1. Current MS State:")
    field_table = table(ms_path + "/FIELD", readonly=True)
    nfields = field_table.nrows()
    print(f"   Fields: {nfields}")
    
    # Get first field phase center as target
    ra_deg, dec_deg = get_ms_phase_center(ms_path, 0)
    print(f"   Target phase center: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")
    field_table.close()
    
    # Step 2: Copy MS for testing
    print("\n2. Copying MS for testing...")
    if os.path.exists(test_ms_copy):
        shutil.rmtree(test_ms_copy)
    shutil.copytree(ms_path, test_ms_copy)
    print(f"   :check: Copied to {test_ms_copy}")
    
    # Step 3: Rephase (using existing function)
    print("\n3. Rephasing all fields to common phase center...")
    try:
        import logging

        from dsa110_contimg.calibration.cli_utils import \
          rephase_ms_to_calibrator
        logger = logging.getLogger(__name__)
        
        success = rephase_ms_to_calibrator(
            test_ms_copy,
            ra_deg,
            dec_deg,
            "DP3_test",
            logger,
        )
        if success:
            print("   :check: Rephasing completed")
        else:
            print("   :warning: Rephasing may have failed or was skipped")
    except Exception as e:
        print(f"   :cross: Rephasing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Check field structure after rephasing
    print("\n4. Checking field structure after rephasing...")
    field_table = table(test_ms_copy + "/FIELD", readonly=True)
    phase_dirs = field_table.getcol("PHASE_DIR")
    print(f"   Fields: {len(phase_dirs)}")
    # Check if all phase centers are now the same
    first_phase = phase_dirs[0]
    all_same = all(np.allclose(pd, first_phase) for pd in phase_dirs[1:])
    print(f"   All fields have same phase center: {all_same}")
    field_table.close()
    
    # Step 5: Create sky model
    print("\n5. Creating sky model with pyradiosky...")
    sky = SkyModel(
        name=["test_source"],
        skycoord=SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg, frame='icrs'),
        stokes=np.array([[[[2.3]]]]) * u.Jy,  # Shape: (4, 1, 1) for I,Q,U,V, freq, component
        spectral_type='flat',
        component_type='point',
    )
    print(f"   :check: Created SkyModel")
    
    # Step 6: Convert to DP3 format
    print("\n6. Converting to DP3 format...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.skymodel', delete=False) as f:
        dp3_path = f.name
    convert_skymodel_to_dp3(sky, out_path=dp3_path)
    print(f"   :check: Converted to DP3 format")
    
    # Step 7: Test DP3 on rephased MS (still multi-field, but same phase centers)
    print("\n7. Testing DP3 on rephased MS...")
    print("   (Note: Still has multiple fields, but same phase centers)")
    try:
        predict_from_skymodel_dp3(
            test_ms_copy,
            dp3_path,
            field="0",  # Try first field
        )
        print("   :check: DP3 predict succeeded!")
        return True
    except Exception as e:
        print(f"   :cross: DP3 predict failed: {e}")
        print("\n   Next step would be to concatenate fields into single field")
        print("   Then test DP3 on the concatenated MS")
        return False
    finally:
        if os.path.exists(dp3_path):
            os.unlink(dp3_path)


if __name__ == "__main__":
    success = test_rephase_concat_approach()
    sys.exit(0 if success else 1)


#!/opt/miniforge/envs/casa6/bin/python
"""Corrected test scenario: Component at PHASE_DIR position.

This tests if ft() uses PHASE_DIR correctly by:
1. Setting component at position B (PHASE_DIR position)
2. Setting PHASE_DIR to position B
3. If ft() uses PHASE_DIR correctly, scatter should be ~0°
4. If ft() uses wrong phase center, scatter should be large (~100°)

Usage:
    python test_ft_phase_dir_corrected.py <ms_path>
"""

import os
import shutil
import sys

import numpy as np
from casacore.tables import table
from casatasks import ft
from casatools import componentlist as cltool


def test_ft_phase_dir_corrected(ms_path):
    """Test if ft() uses PHASE_DIR correctly with component at PHASE_DIR position."""
    
    print("=" * 80)
    print("CORRECTED TEST: Component at PHASE_DIR position")
    print("=" * 80)
    print(f"\nMS path: {ms_path}")
    
    if not os.path.exists(ms_path):
        raise FileNotFoundError(f"MS not found: {ms_path}")
    
    # Make a copy of the MS for testing
    test_ms = ms_path.rstrip('/').rstrip('.ms') + '_ft_test_corrected.ms'
    if os.path.exists(test_ms):
        shutil.rmtree(test_ms, ignore_errors=True)
    print(f"\nCopying MS to: {test_ms}")
    shutil.copytree(ms_path, test_ms)
    
    comp_path = os.path.join(os.path.dirname(test_ms), "test_component_corrected.cl")
    
    try:
        # Read current phase centers
        with table(f"{test_ms}::FIELD", readonly=False) as field_tb:
            # Get original phase center
            original_ref_dir = field_tb.getcol("REFERENCE_DIR")[0][0].copy()
            original_phase_dir = field_tb.getcol("PHASE_DIR")[0][0].copy()
            
            print(f"\nOriginal phase centers:")
            print(f"  REFERENCE_DIR: RA={np.degrees(original_ref_dir[0]):.6f}°, Dec={np.degrees(original_ref_dir[1]):.6f}°")
            print(f"  PHASE_DIR: RA={np.degrees(original_phase_dir[0]):.6f}°, Dec={np.degrees(original_phase_dir[1]):.6f}°")
            
            # Set both REFERENCE_DIR and PHASE_DIR to position B (calibrator position)
            cal_ra_rad = 128.7287 * np.pi / 180.0
            cal_dec_rad = 55.5725 * np.pi / 180.0
            position_b = np.array([cal_ra_rad, cal_dec_rad])
            
            # Set position A (1 degree offset in RA)
            position_a = np.array([
                cal_ra_rad + 1.0 * np.pi / 180.0,  # 1 degree offset
                cal_dec_rad
            ])
            
            # Get number of fields
            nfields = field_tb.nrows()
            
            # Set REFERENCE_DIR to position A (different from PHASE_DIR) for all fields
            ref_dir_array = np.tile(position_a.reshape(1, 1, 2), (nfields, 1, 1))
            field_tb.putcol("REFERENCE_DIR", ref_dir_array)
            
            # Set PHASE_DIR to position B (calibrator position) for all fields
            phase_dir_array = np.tile(position_b.reshape(1, 1, 2), (nfields, 1, 1))
            field_tb.putcol("PHASE_DIR", phase_dir_array)
            
            print(f"\nTest configuration:")
            print(f"  REFERENCE_DIR (position A): RA={np.degrees(position_a[0]):.6f}°, Dec={np.degrees(position_a[1]):.6f}°")
            print(f"  PHASE_DIR (position B): RA={np.degrees(position_b[0]):.6f}°, Dec={np.degrees(position_b[1]):.6f}°")
            print(f"  Component position: RA={np.degrees(position_b[0]):.6f}°, Dec={np.degrees(position_b[1]):.6f}° (same as PHASE_DIR)")
            print(f"\n  Key: Component is at PHASE_DIR position (position B)")
            print(f"       If ft() uses PHASE_DIR correctly, scatter should be ~0°")
            print(f"       If ft() uses REFERENCE_DIR (position A), scatter should be ~100°")
        
        # Create component list at position B (PHASE_DIR position)
        if os.path.exists(comp_path):
            shutil.rmtree(comp_path, ignore_errors=True)
        
        print(f"\nCreating component list at position B (PHASE_DIR)...")
        cl = cltool()
        cl.addcomponent(
            dir={"refer": "J2000", "type": "direction", 
                 "long": f"{position_b[0]*180/np.pi}deg", 
                 "lat": f"{position_b[1]*180/np.pi}deg"},
            flux=2.5,
            fluxunit="Jy",
            freq="1.4GHz",
            shape="point"
        )
        cl.rename(comp_path)
        cl.close()
        
        # Clear MODEL_DATA
        print("\nClearing MODEL_DATA...")
        with table(test_ms, readonly=False) as main_tb:
            if "MODEL_DATA" in main_tb.colnames():
                zeros = np.zeros(main_tb.getcol("MODEL_DATA").shape, dtype=np.complex64)
                main_tb.putcol("MODEL_DATA", zeros)
        
        # Call ft() - this should use one of the phase centers
        print(f"\nCalling ft() with component at position B (PHASE_DIR position)...")
        ft(vis=test_ms, complist=comp_path, usescratch=True, field="0")
        
        # Check MODEL_DATA phase structure
        print("\nAnalyzing MODEL_DATA phase structure...")
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
                
                # Calculate expected phase for position B (PHASE_DIR) - component is AT position B
                # Offset = 0 (component at phase center)
                offset_ra_b = 0.0  # Component at position B, PHASE_DIR at position B
                offset_dec_b = 0.0
                expected_phase_b = 2 * np.pi * (u_coord * offset_ra_b + v_coord * offset_dec_b) / wavelength
                expected_phase_b = np.mod(expected_phase_b + np.pi, 2*np.pi) - np.pi
                
                # Calculate expected phase for position A (REFERENCE_DIR) - component is 1° from position A
                offset_ra_a = (position_b[0] - position_a[0]) * np.cos(position_a[1])
                offset_dec_a = position_b[1] - position_a[1]
                expected_phase_a = 2 * np.pi * (u_coord * offset_ra_a + v_coord * offset_dec_a) / wavelength
                expected_phase_a = np.mod(expected_phase_a + np.pi, 2*np.pi) - np.pi
                
                # Compare
                diff_b = phases - expected_phase_b
                diff_b = np.mod(diff_b + np.pi, 2*np.pi) - np.pi
                diff_b_deg = np.degrees(diff_b)
                
                diff_a = phases - expected_phase_a
                diff_a = np.mod(diff_a + np.pi, 2*np.pi) - np.pi
                diff_a_deg = np.degrees(diff_a)
                
                scatter_b = np.std(diff_b_deg)
                scatter_a = np.std(diff_a_deg)
                
                print(f"\n" + "=" * 80)
                print("RESULTS:")
                print("=" * 80)
                print(f"\nMODEL_DATA vs PHASE_DIR (position B): {scatter_b:.1f}° scatter")
                print(f"  Expected: ~0° if ft() uses PHASE_DIR correctly")
                print(f"\nMODEL_DATA vs REFERENCE_DIR (position A): {scatter_a:.1f}° scatter")
                print(f"  Expected: ~100° if ft() uses REFERENCE_DIR (component 1° from REFERENCE_DIR)")
                
                # Determine which phase center ft() used
                print(f"\n" + "=" * 80)
                print("CONCLUSION:")
                print("=" * 80)
                if scatter_b < 10:
                    print(f"\n✓ ft() USES PHASE_DIR for phase calculations")
                    print(f"  Scatter ({scatter_b:.1f}°) is small, indicating component is at phase center")
                    return True
                elif scatter_a < 10:
                    print(f"\n✓ ft() USES REFERENCE_DIR for phase calculations")
                    print(f"  Scatter ({scatter_a:.1f}°) is small, but component is 1° from REFERENCE_DIR")
                    print(f"  This suggests ft() correctly uses REFERENCE_DIR")
                    return True
                else:
                    print(f"\n✗ ft() does NOT match either REFERENCE_DIR or PHASE_DIR")
                    print(f"  PHASE_DIR scatter: {scatter_b:.1f}° (expected ~0°)")
                    print(f"  REFERENCE_DIR scatter: {scatter_a:.1f}° (expected ~100°)")
                    print(f"  This suggests ft() uses a different source or has a bug")
                    return False
            else:
                print("\n✗ No unflagged data found")
                return False
    
    finally:
        # Cleanup
        if os.path.exists(test_ms):
            print(f"\nCleaning up test MS: {test_ms}")
            shutil.rmtree(test_ms, ignore_errors=True)
        if os.path.exists(comp_path):
            print(f"Cleaning up component list: {comp_path}")
            shutil.rmtree(comp_path, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ft_phase_dir_corrected.py <ms_path>")
        sys.exit(1)
    
    ms_path = sys.argv[1]
    success = test_ft_phase_dir_corrected(ms_path)
    sys.exit(0 if success else 1)


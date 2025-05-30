#!/usr/bin/env python3
"""
UVW Coordinate Diagnostic Script
Diagnoses and potentially fixes UVW coordinate discrepancies
"""

import sys
import os
import numpy as np
from pathlib import Path
from pyuvdata import UVData
import warnings

# Add your pipeline path
pipeline_parent_dir = '/data/jfaber/dsa110-contimg/'
if pipeline_parent_dir not in sys.path:
    sys.path.insert(0, pipeline_parent_dir)

from pipeline import dsa110_utils
from astropy.coordinates import EarthLocation
import astropy.units as u

def diagnose_uvw_issue(hdf5_file_path, dsa110_location=None):
    """
    Comprehensive diagnosis of UVW coordinate issues
    """
    print("=== UVW COORDINATE DIAGNOSTIC ===")
    print(f"Analyzing: {hdf5_file_path}")
    
    if dsa110_location is None:
        dsa110_location = dsa110_utils.loc_dsa110
    
    # Load the HDF5 file
    uvd = UVData()
    print("Loading HDF5 file...")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
        warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
        warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*")
        uvd.read(hdf5_file_path, file_type='uvh5', run_check=False)
    
    print(f"\n--- BASIC INFO ---")
    print(f"Telescope name: {uvd.telescope.name}")
    print(f"N antennas: {uvd.Nants_telescope}")
    print(f"N baselines: {uvd.Nbls}")
    
    # Check telescope location
    print(f"\n--- TELESCOPE LOCATION ---")
    if hasattr(uvd, 'telescope_location') and uvd.telescope_location is not None:
        tel_xyz = uvd.telescope_location
        print(f"Telescope XYZ: {tel_xyz}")
        
        # Convert to EarthLocation for comparison
        tel_earthloc = EarthLocation.from_geocentric(
            tel_xyz[0] * u.m, tel_xyz[1] * u.m, tel_xyz[2] * u.m
        )
        print(f"Lat/Lon/Alt: {tel_earthloc.lat.deg:.6f}°, {tel_earthloc.lon.deg:.6f}°, {tel_earthloc.height.value:.1f}m")
        
        # Compare with expected DSA-110 location
        try:
            expected_itrs = dsa110_location.get_itrs()
            expected_xyz = [expected_itrs.x.value, expected_itrs.y.value, expected_itrs.z.value]
        except:
            expected_xyz = [dsa110_location.itrs.x.value, dsa110_location.itrs.y.value, dsa110_location.itrs.z.value]
        
        location_diff = np.sqrt(np.sum((tel_xyz - expected_xyz)**2))
        print(f"Difference from expected DSA-110: {location_diff:.3f} m")
        
        if location_diff > 100:
            print(f"⚠️  LARGE telescope location discrepancy!")
    else:
        print("❌ No telescope location found!")
    
    # Check antenna positions
    print(f"\n--- ANTENNA POSITIONS ---")
    if hasattr(uvd, 'antenna_positions') and uvd.antenna_positions is not None:
        ant_pos = uvd.antenna_positions
        print(f"Antenna positions shape: {ant_pos.shape}")
        print(f"Position ranges:")
        print(f"  X: {ant_pos[:, 0].min():.1f} to {ant_pos[:, 0].max():.1f} m")
        print(f"  Y: {ant_pos[:, 1].min():.1f} to {ant_pos[:, 1].max():.1f} m") 
        print(f"  Z: {ant_pos[:, 2].min():.1f} to {ant_pos[:, 2].max():.1f} m")
        
        max_baseline = np.sqrt(np.sum(ant_pos**2, axis=1)).max()
        print(f"Max antenna distance from center: {max_baseline:.1f} m")
        
        # Check for coordinate system issues
        print(f"\n--- COORDINATE SYSTEM DIAGNOSIS ---")
        if max_baseline > 1e6:  # > 1000 km suggests absolute coordinates
            print(f"❌ Antenna positions appear to be in absolute ECEF coordinates!")
            print(f"   (should be relative to telescope center)")
            print(f"   This is likely the source of your UVW discrepancy.")
            return "absolute_coordinates"
        elif max_baseline < 10:  # < 10 m suggests wrong units or single antenna
            print(f"❌ Antenna positions seem too small - possibly wrong units")
            return "wrong_units"
        else:
            print(f"✅ Antenna position scale looks reasonable for relative coordinates")
    else:
        print("❌ No antenna positions found!")
    
    # Check UVW ranges
    print(f"\n--- UVW COORDINATES ---")
    if hasattr(uvd, 'uvw_array') and uvd.uvw_array is not None:
        uvw_max = np.max(np.abs(uvd.uvw_array))
        uvw_rms = np.sqrt(np.mean(uvd.uvw_array**2))
        print(f"Max UVW coordinate: {uvw_max:.1f} m")
        print(f"RMS UVW coordinate: {uvw_rms:.1f} m")
        
        # Check for consistency with antenna positions
        if hasattr(uvd, 'antenna_positions') and uvd.antenna_positions is not None:
            max_baseline = np.sqrt(np.sum(uvd.antenna_positions**2, axis=1)).max()
            ratio = uvw_max / max_baseline if max_baseline > 0 else float('inf')
            print(f"UVW/antenna baseline ratio: {ratio:.2f}")
            
            if ratio > 20:
                print(f"⚠️  UVW coordinates seem too large compared to antenna positions!")
                print(f"    This suggests a coordinate system mismatch.")
                return "uvw_antenna_mismatch"
            elif ratio < 0.1:
                print(f"⚠️  UVW coordinates seem too small compared to antenna positions!")
                return "uvw_too_small"
            else:
                print(f"✅ UVW/antenna ratio looks reasonable")
    else:
        print("❌ No UVW coordinates found!")
    
    # Try running PyUVData's check to see the exact error
    print(f"\n--- PYUVDATA CHECK ---")
    try:
        uvd.check(check_extra=True, run_check_acceptability=True)
        print("✅ PyUVData check passed!")
        return "ok"
    except Exception as e:
        print(f"❌ PyUVData check failed: {e}")
        return "check_failed"

def suggest_fixes(diagnosis):
    """Suggest fixes based on the diagnosis"""
    print(f"\n--- SUGGESTED FIXES ---")
    
    if diagnosis == "absolute_coordinates":
        print("🔧 SOLUTION: Convert antenna positions to relative coordinates")
        print("   In your _load_uvh5_file function, add this after reading:")
        print("""
   # Fix absolute coordinates
   if np.max(np.abs(uvdata_obj.antenna_positions)) > 1e6:
       tel_xyz = uvdata_obj.telescope_location
       uvdata_obj.antenna_positions = uvdata_obj.antenna_positions - tel_xyz
       logger.info("Converted antenna positions from absolute to relative coordinates")
        """)
    
    elif diagnosis == "uvw_antenna_mismatch":
        print("🔧 SOLUTION: The UVW calculation may need fixing")
        print("   Options:")
        print("   1. Use the 'simple' phasing method that keeps original UVWs")
        print("   2. Check telescope location accuracy")
        print("   3. Verify antenna position coordinate system")
    
    elif diagnosis == "check_failed":
        print("🔧 SOLUTION: Try running with relaxed checks")
        print("   In your code, use:")
        print("   uvdata_obj.check(check_extra=False, run_check_acceptability=False)")
        print("   Or add: strict_uvw_antpos_check=False to relevant function calls")
    
    else:
        print("💡 General recommendations:")
        print("   1. Verify telescope location is exactly correct")
        print("   2. Ensure antenna positions are relative to telescope center")
        print("   3. Check that LST calculation uses correct longitude")
        print("   4. Try the 'simple' phasing method in your pipeline")

def main():
    """Main diagnostic function"""
    import glob
    
    # Find an HDF5 file to test
    hdf5_pattern = "/data/incoming/20*_sb00.hdf5"
    hdf5_files = glob.glob(hdf5_pattern)
    
    if not hdf5_files:
        print(f"❌ No HDF5 files found matching pattern: {hdf5_pattern}")
        print("Please specify the correct path to your HDF5 files")
        return
    
    # Use the first file found
    test_file = hdf5_files[0]
    
    # Run diagnosis
    diagnosis = diagnose_uvw_issue(test_file)
    
    # Suggest fixes
    suggest_fixes(diagnosis)
    
    print(f"\n=== SUMMARY ===")
    if diagnosis in ["absolute_coordinates", "uvw_antenna_mismatch"]:
        print("🚨 SERIOUS ISSUE: UVW discrepancy will affect data quality")
        print("   Recommended: Fix the coordinate system issues before proceeding")
    elif diagnosis == "check_failed":
        print("⚠️  MODERATE ISSUE: PyUVData validation failed")
        print("   May be acceptable if other checks pass")
    else:
        print("✅ No major issues detected")

if __name__ == "__main__":
    main()
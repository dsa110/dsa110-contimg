#!/usr/bin/env python3
"""
Rephase MS back to meridian phase center.

This script rephases an MS that has been rephased to a calibrator position
back to the original meridian phase center (RA=LST at midpoint, Dec=pointing).

Usage:
    python rephase_to_meridian.py <ms_path> [uvh5_path]

If uvh5_path is provided, it will use the pointing declination from the UVH5 file.
Otherwise, it will attempt to infer from MS metadata or use the first field's declination.

Example:
    python rephase_to_meridian.py /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
        /scratch/dsa110-contimg/uvh5/2025-10-29T13:54:17.uvh5
"""

import sys
import os
import numpy as np
from casacore.tables import table
from casatasks import phaseshift
from astropy.coordinates import SkyCoord, Angle, EarthLocation
from astropy.time import Time
from astropy import units as u
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.conversion.helpers import get_meridian_coords


def get_ms_midpoint_time(ms_path: str) -> float:
    """Get midpoint time (MJD) from MS."""
    with table(ms_path, readonly=True) as tb:
        if 'TIME' not in tb.colnames():
            raise ValueError("MS has no TIME column")
        
        times = tb.getcol('TIME')  # Seconds (MJD seconds)
        if len(times) == 0:
            raise ValueError("MS has no time samples")
        
        t0 = float(times.min())
        t1 = float(times.max())
        mid_time_sec = 0.5 * (t0 + t1)
        
        # Convert to MJD days
        # TIME is in seconds since MJD epoch (MJD seconds)
        mid_mjd = mid_time_sec / 86400.0
        
        return mid_mjd


def get_pointing_declination(ms_path: str, uvh5_path: str = None) -> u.Quantity:
    """Get pointing declination from UVH5 or MS."""
    
    # Option 1: Read from UVH5 file if provided
    if uvh5_path and os.path.exists(uvh5_path):
        try:
            import h5py
            with h5py.File(uvh5_path, 'r') as f:
                if 'Header' in f and 'extra_keywords' in f['Header']:
                    ek = f['Header']['extra_keywords']
                    if 'phase_center_dec' in ek:
                        dec_rad = float(np.asarray(ek['phase_center_dec']))
                        print(f"✓ Found pointing declination in UVH5: {np.degrees(dec_rad):.6f}°")
                        return dec_rad * u.rad
        except Exception as e:
            print(f"WARNING: Could not read UVH5: {e}")
    
    # Option 2: Use first field's declination from MS
    # (This assumes first field is at meridian, which may not be true after rephasing)
    try:
        with table(f"{ms_path}::FIELD", readonly=True) as field_tb:
            if field_tb.nrows() == 0:
                raise ValueError("MS has no fields")
            
            # Try to get declination from first field
            # Note: After rephasing, this may be calibrator dec, not pointing dec!
            if "REFERENCE_DIR" in field_tb.colnames():
                ref_dir = field_tb.getcol("REFERENCE_DIR")[0][0]
                dec_rad = ref_dir[1]
            elif "PHASE_DIR" in field_tb.colnames():
                phase_dir = field_tb.getcol("PHASE_DIR")[0][0]
                dec_rad = phase_dir[1]
            else:
                raise ValueError("MS has no REFERENCE_DIR or PHASE_DIR")
            
            dec_deg = np.degrees(dec_rad)
            print(f"⚠ Using first field declination from MS: {dec_deg:.6f}°")
            print(f"  WARNING: This may be calibrator declination, not pointing declination!")
            print(f"  If incorrect, provide UVH5 file path to get correct pointing declination.")
            
            return dec_rad * u.rad
    except Exception as e:
        raise ValueError(f"Could not get pointing declination: {e}")


def rephase_to_meridian(ms_path: str, uvh5_path: str = None, output_path: str = None):
    """Rephase MS back to meridian phase center."""
    
    print("=" * 100)
    print("REPHASING MS TO MERIDIAN")
    print("=" * 100)
    print(f"MS: {ms_path}")
    if uvh5_path:
        print(f"UVH5: {uvh5_path}")
    
    # Get midpoint time
    print("\n1. Getting midpoint time from MS...")
    mid_mjd = get_ms_midpoint_time(ms_path)
    print(f"   Midpoint time: MJD {mid_mjd:.6f}")
    
    # Get pointing declination
    print("\n2. Getting pointing declination...")
    pt_dec = get_pointing_declination(ms_path, uvh5_path)
    print(f"   Pointing declination: {pt_dec.to(u.deg).value:.6f}°")
    
    # Calculate meridian coordinates
    print("\n3. Calculating meridian coordinates...")
    meridian_ra_rad, meridian_dec_rad = get_meridian_coords(pt_dec, mid_mjd)
    meridian_ra_deg = meridian_ra_rad.to(u.deg).value
    meridian_dec_deg = meridian_dec_rad.to(u.deg).value
    
    print(f"   Meridian RA:  {meridian_ra_deg:.6f}°")
    print(f"   Meridian Dec: {meridian_dec_deg:.6f}°")
    
    # Format phase center string for CASA
    ra_hms = Angle(meridian_ra_deg, unit='deg').to_string(
        unit='hourangle', sep='hms', precision=2, pad=True
    ).replace(' ', '')
    dec_dms = Angle(meridian_dec_deg, unit='deg').to_string(
        unit='deg', sep='dms', precision=2, alwayssign=True, pad=True
    ).replace(' ', '')
    phasecenter_str = f"J2000 {ra_hms} {dec_dms}"
    print(f"   Phase center string: {phasecenter_str}")
    
    # Determine output path
    if output_path is None:
        ms_abs = os.path.abspath(ms_path.rstrip('/'))
        ms_dir = os.path.dirname(ms_abs)
        ms_base = os.path.basename(ms_abs).rstrip('.ms')
        output_path = os.path.join(ms_dir, f"{ms_base}.meridian.ms")
    
    # Check if output already exists
    if os.path.exists(output_path):
        response = input(f"\nOutput MS already exists: {output_path}\n"
                        f"Delete and recreate? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return
        print(f"Removing existing MS: {output_path}")
        import shutil
        shutil.rmtree(output_path, ignore_errors=True)
    
    # Run phaseshift
    print(f"\n4. Rephasing MS to meridian...")
    print(f"   Output: {output_path}")
    print(f"   This may take a while...")
    
    phaseshift(
        vis=ms_path,
        outputvis=output_path,
        phasecenter=phasecenter_str
        # No field parameter = rephase ALL fields
    )
    
    print(f"\n✓ phaseshift completed successfully")
    
    # Verify phase center
    print("\n5. Verifying phase center...")
    try:
        with table(f"{output_path}::FIELD", readonly=True) as tf:
            if "REFERENCE_DIR" in tf.colnames():
                ref_dir = tf.getcol("REFERENCE_DIR")[0][0]
                ref_ra_deg = np.degrees(ref_dir[0])
                ref_dec_deg = np.degrees(ref_dir[1])
                
                meridian_coord = SkyCoord(ra=meridian_ra_deg*u.deg, dec=meridian_dec_deg*u.deg)
                ms_coord = SkyCoord(ra=ref_ra_deg*u.deg, dec=ref_dec_deg*u.deg)
                separation = meridian_coord.separation(ms_coord)
                
                print(f"   Final phase center: RA={ref_ra_deg:.6f}°, Dec={ref_dec_deg:.6f}°")
                print(f"   Separation from meridian: {separation.to(u.arcmin):.4f}")
                
                if separation.to(u.arcmin).value > 1.0:
                    print(f"   ⚠ WARNING: Phase center still offset by {separation.to(u.arcmin):.4f}")
                else:
                    print(f"   ✓ Phase center aligned (within 1 arcmin)")
    except Exception as e:
        print(f"   ⚠ Could not verify phase center: {e}")
    
    # Update REFERENCE_DIR to match PHASE_DIR
    print("\n6. Updating REFERENCE_DIR to match PHASE_DIR...")
    try:
        with table(f"{output_path}::FIELD", readonly=False) as tf:
            if "REFERENCE_DIR" in tf.colnames() and "PHASE_DIR" in tf.colnames():
                ref_dir_all = tf.getcol("REFERENCE_DIR")
                phase_dir_all = tf.getcol("PHASE_DIR")
                nfields = len(ref_dir_all)
                
                needs_update = False
                for field_idx in range(nfields):
                    ref_dir = ref_dir_all[field_idx][0]
                    phase_dir = phase_dir_all[field_idx][0]
                    if not np.allclose(ref_dir, phase_dir, atol=2.9e-5):
                        needs_update = True
                        break
                
                if needs_update:
                    print(f"   Updating REFERENCE_DIR for all {nfields} fields...")
                    tf.putcol("REFERENCE_DIR", phase_dir_all)
                    print(f"   ✓ REFERENCE_DIR updated")
                else:
                    print(f"   ✓ REFERENCE_DIR already matches PHASE_DIR")
    except Exception as e:
        print(f"   ⚠ Could not update REFERENCE_DIR: {e}")
    
    print("\n" + "=" * 100)
    print("REPHASING COMPLETE")
    print("=" * 100)
    print(f"Meridian-phased MS: {output_path}")
    print(f"\nYou can now use --skip-rephase with this MS.")
    print("=" * 100)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    ms_path = sys.argv[1]
    uvh5_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(ms_path):
        print(f"ERROR: MS not found: {ms_path}")
        sys.exit(1)
    
    if uvh5_path and not os.path.exists(uvh5_path):
        print(f"WARNING: UVH5 not found: {uvh5_path}")
        print(f"         Will attempt to infer pointing declination from MS")
        uvh5_path = None
    
    rephase_to_meridian(ms_path, uvh5_path)


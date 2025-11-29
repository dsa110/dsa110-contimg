#!/opt/miniforge/envs/casa6/bin/python
"""
Test ft() with explicit phasecenter parameter to see if it fixes phase center issues.

Usage:
    python test_ft_with_phasecenter.py <ms_path> <cal_ra_deg> <cal_dec_deg> <flux_jy>
"""

import sys

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from casacore.tables import table
from casatasks import ft
from casatools import componentlist as cltool


def test_ft_with_phasecenter(ms_path, cal_ra_deg, cal_dec_deg, flux_jy):
    """Test ft() with explicit phasecenter parameter."""
    
    print("=" * 100)
    print(f"Testing ft() with explicit phasecenter: {ms_path}")
    print("=" * 100)
    
    # Format phase center string
    from astropy.coordinates import Angle
    ra_hms = Angle(cal_ra_deg, unit='deg').to_string(unit='hour', precision=2)
    dec_dms = Angle(cal_dec_deg, unit='deg').to_string(unit='deg', precision=2)
    phasecenter_str = f"J2000 {ra_hms} {dec_dms}"
    
    print(f"\nPhase center string: {phasecenter_str}")
    print(f"Calibrator: RA={cal_ra_deg:.6f}°, Dec={cal_dec_deg:.6f}°, Flux={flux_jy:.2f} Jy")
    
    # Create component list
    comp_path = f"{ms_path}.test_ft.cl"
    import os
    import shutil
    if os.path.exists(comp_path):
        shutil.rmtree(comp_path, ignore_errors=True)
    
    cl = cltool()
    sc = SkyCoord(ra=cal_ra_deg * u.deg, dec=cal_dec_deg * u.deg, frame="icrs")
    dir_dict = {
        "refer": "J2000",
        "type": "direction",
        "long": f"{sc.ra.deg}deg",
        "lat": f"{sc.dec.deg}deg",
    }
    cl.addcomponent(
        dir=dir_dict,
        flux=float(flux_jy),
        fluxunit="Jy",
        freq="1.4GHz",
        shape="point")
    cl.rename(comp_path)
    cl.close()
    
    # Clear MODEL_DATA
    print("\nClearing MODEL_DATA...")
    try:
        t = table(ms_path, readonly=False)
        if "MODEL_DATA" in t.colnames() and t.nrows() > 0:
            if "DATA" in t.colnames():
                data_sample = t.getcell("DATA", 0)
                data_shape = getattr(data_sample, "shape", None)
                data_dtype = getattr(data_sample, "dtype", None)
                if data_shape and data_dtype:
                    zeros = np.zeros((t.nrows(),) + data_shape, dtype=data_dtype)
                    t.putcol("MODEL_DATA", zeros)
        t.close()
        print("  :check: MODEL_DATA cleared")
    except Exception as e:
        print(f"  ERROR: Failed to clear MODEL_DATA: {e}")
        return False
    
    # Test 1: ft() WITHOUT phasecenter parameter (current usage)
    print("\n" + "=" * 100)
    print("Test 1: ft() WITHOUT phasecenter parameter (current usage)")
    print("=" * 100)
    try:
        ft(vis=ms_path, complist=comp_path, usescratch=True)
        print("  :check: ft() completed")
        
        # Check phase scatter
        with table(ms_path, readonly=True) as tb:
            n_sample = min(5000, tb.nrows())
            model_data = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
            flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)
            
            unflagged_mask = ~flags.any(axis=(1, 2))
            if unflagged_mask.sum() > 0:
                model_unflagged = model_data[unflagged_mask]
                model_phases = np.angle(model_unflagged[:, 0, 0])
                model_phases_deg = np.degrees(model_phases)
                model_phase_scatter = np.std(model_phases_deg)
                print(f"  Phase scatter: {model_phase_scatter:.2f}°")
                
                # Store for comparison
                scatter_without = model_phase_scatter
            else:
                print("  ERROR: All data flagged")
                scatter_without = None
    except Exception as e:
        print(f"  ERROR: ft() failed: {e}")
        import traceback
        traceback.print_exc()
        scatter_without = None
    
    # Clear MODEL_DATA again
    print("\nClearing MODEL_DATA for next test...")
    try:
        t = table(ms_path, readonly=False)
        if "MODEL_DATA" in t.colnames() and t.nrows() > 0:
            if "DATA" in t.colnames():
                data_sample = t.getcell("DATA", 0)
                data_shape = getattr(data_sample, "shape", None)
                data_dtype = getattr(data_sample, "dtype", None)
                if data_shape and data_dtype:
                    zeros = np.zeros((t.nrows(),) + data_shape, dtype=data_dtype)
                    t.putcol("MODEL_DATA", zeros)
        t.close()
    except Exception as e:
        print(f"  ERROR: Failed to clear MODEL_DATA: {e}")
    
    # Test 2: ft() WITH phasecenter parameter (if supported)
    print("\n" + "=" * 100)
    print("Test 2: ft() WITH phasecenter parameter")
    print("=" * 100)
    try:
        # Try ft() with phasecenter parameter
        # Note: This may not be supported in CASA 6, but worth trying
        ft(vis=ms_path, complist=comp_path, usescratch=True, phasecenter=phasecenter_str)
        print("  :check: ft() with phasecenter completed")
        
        # Check phase scatter
        with table(ms_path, readonly=True) as tb:
            n_sample = min(5000, tb.nrows())
            model_data = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
            flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)
            
            unflagged_mask = ~flags.any(axis=(1, 2))
            if unflagged_mask.sum() > 0:
                model_unflagged = model_data[unflagged_mask]
                model_phases = np.angle(model_unflagged[:, 0, 0])
                model_phases_deg = np.degrees(model_phases)
                model_phase_scatter = np.std(model_phases_deg)
                print(f"  Phase scatter: {model_phase_scatter:.2f}°")
                
                scatter_with = model_phase_scatter
            else:
                print("  ERROR: All data flagged")
                scatter_with = None
    except TypeError as e:
        print(f"  INFO: phasecenter parameter not supported: {e}")
        scatter_with = None
    except Exception as e:
        print(f"  ERROR: ft() with phasecenter failed: {e}")
        import traceback
        traceback.print_exc()
        scatter_with = None
    
    # Summary
    print("\n" + "=" * 100)
    print("Summary")
    print("=" * 100)
    if scatter_without is not None:
        print(f"  Without phasecenter: {scatter_without:.2f}°")
    if scatter_with is not None:
        print(f"  With phasecenter: {scatter_with:.2f}°")
        if scatter_without is not None and scatter_with < scatter_without:
            print(f"  :check: phasecenter parameter improves phase scatter!")
        elif scatter_without is not None and scatter_with >= scatter_without:
            print(f"  :cross: phasecenter parameter does not improve phase scatter")
    else:
        print(f"  phasecenter parameter not supported or test failed")
    
    # Cleanup
    if os.path.exists(comp_path):
        shutil.rmtree(comp_path, ignore_errors=True)
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    
    ms_path = sys.argv[1]
    cal_ra_deg = float(sys.argv[2])
    cal_dec_deg = float(sys.argv[3])
    flux_jy = float(sys.argv[4])
    
    test_ft_with_phasecenter(ms_path, cal_ra_deg, cal_dec_deg, flux_jy)


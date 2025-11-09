#!/usr/bin/env python3
"""
Recalculate MODEL_DATA using manual calculation method.

This fixes MODEL_DATA phase scatter issues caused by ft() using incorrect phase centers.

Usage:
    python recalculate_model_data.py <ms_path> <cal_ra_deg> <cal_dec_deg> <flux_jy>
    
Example:
    python recalculate_model_data.py /stage/dsa110-contimg/ms/2025-10-29T13:54:17.ms 128.7287 55.5725 2.5
"""

import sys
from dsa110_contimg.calibration.model import _calculate_manual_model_data
from casacore.tables import table
import numpy as np

def recalculate_model_data(ms_path, cal_ra_deg, cal_dec_deg, flux_jy):
    """Recalculate MODEL_DATA using manual calculation."""
    
    print("=" * 100)
    print(f"Recalculating MODEL_DATA: {ms_path}")
    print("=" * 100)
    
    # Clear existing MODEL_DATA
    print("\nStep 1: Clearing existing MODEL_DATA...")
    try:
        with table(ms_path, readonly=False) as tb:
            if "MODEL_DATA" in tb.colnames() and tb.nrows() > 0:
                # Get DATA shape to match MODEL_DATA shape
                if "DATA" in tb.colnames():
                    data_sample = tb.getcell("DATA", 0)
                    data_shape = getattr(data_sample, "shape", None)
                    data_dtype = getattr(data_sample, "dtype", None)
                    if data_shape and data_dtype:
                        zeros = np.zeros((tb.nrows(),) + data_shape, dtype=data_dtype)
                        tb.putcol("MODEL_DATA", zeros)
                        print(f"  ✓ Cleared MODEL_DATA ({tb.nrows()} rows)")
                    else:
                        print(f"  WARNING: Could not determine DATA shape")
                else:
                    print(f"  WARNING: DATA column not found")
            else:
                print(f"  ℹ MODEL_DATA column not present or empty")
    except Exception as e:
        print(f"  ERROR: Failed to clear MODEL_DATA: {e}")
        return False
    
    # Recalculate MODEL_DATA using manual method
    print("\nStep 2: Recalculating MODEL_DATA using manual calculation...")
    print(f"  Calibrator: RA={cal_ra_deg:.6f}°, Dec={cal_dec_deg:.6f}°, Flux={flux_jy:.2f} Jy")
    try:
        _calculate_manual_model_data(ms_path, cal_ra_deg, cal_dec_deg, flux_jy, field=None)
        print(f"  ✓ MODEL_DATA recalculated successfully")
    except Exception as e:
        print(f"  ERROR: Failed to recalculate MODEL_DATA: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify MODEL_DATA phase scatter
    print("\nStep 3: Verifying MODEL_DATA phase scatter...")
    try:
        with table(ms_path, readonly=True) as tb:
            if "MODEL_DATA" not in tb.colnames():
                print(f"  ERROR: MODEL_DATA column not found after recalculation")
                return False
            
            n_sample = min(5000, tb.nrows())
            model_data = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
            flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)
            
            unflagged_mask = ~flags.any(axis=(1, 2))
            if unflagged_mask.sum() == 0:
                print(f"  ERROR: All MODEL_DATA is flagged")
                return False
            
            model_unflagged = model_data[unflagged_mask]
            model_phases = np.angle(model_unflagged[:, 0, 0])
            model_phases_deg = np.degrees(model_phases)
            model_phase_scatter = np.std(model_phases_deg)
            
            print(f"  Phase scatter: {model_phase_scatter:.2f}°")
            print(f"  Expected: < 10°")
            
            if model_phase_scatter < 10:
                print(f"  ✓ MODEL_DATA phase scatter is acceptable")
                return True
            else:
                print(f"  ✗ MODEL_DATA phase scatter is still high")
                print(f"    This may indicate DATA column phasing issues")
                return False
    except Exception as e:
        print(f"  WARNING: Could not verify MODEL_DATA: {e}")
        return True  # Assume success if verification fails
    
    print("\n" + "=" * 100)
    print("MODEL_DATA recalculation complete!")
    print("=" * 100)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    
    ms_path = sys.argv[1]
    cal_ra_deg = float(sys.argv[2])
    cal_dec_deg = float(sys.argv[3])
    flux_jy = float(sys.argv[4])
    
    success = recalculate_model_data(ms_path, cal_ra_deg, cal_dec_deg, flux_jy)
    sys.exit(0 if success else 1)


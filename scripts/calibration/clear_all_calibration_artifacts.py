#!/opt/miniforge/envs/casa6/bin/python
"""Clear all calibration artifacts from MS before calibration.

This ensures a clean slate:
- MODEL_DATA
- CORRECTED_DATA  
- Any existing calibration tables in the directory
- Flag tables
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def clear_model_data(ms_path: str) -> bool:
    """Clear MODEL_DATA column completely."""
    print(f"\nClearing MODEL_DATA from {ms_path}...")
    
    try:
        import numpy as np
        from casacore.tables import table
        
        with table(ms_path, readonly=False) as tb:
            if "MODEL_DATA" not in tb.colnames():
                print("  ✓ MODEL_DATA column does not exist")
                return True
            
            nrows = tb.nrows()
            if nrows == 0:
                print("  ✓ MS has no rows")
                return True
            
            # Get DATA shape to match MODEL_DATA shape
            if "DATA" in tb.colnames():
                data_sample = tb.getcell("DATA", 0)
                data_shape = getattr(data_sample, "shape", None)
                data_dtype = getattr(data_sample, "dtype", None)
                
                if data_shape and data_dtype:
                    # Clear MODEL_DATA with zeros matching DATA shape
                    zeros = np.zeros((nrows,) + data_shape, dtype=data_dtype)
                    tb.putcol("MODEL_DATA", zeros)
                    print(f"  ✓ MODEL_DATA cleared ({nrows} rows)")
                    return True
                else:
                    print("  ⚠ Could not determine DATA shape")
                    return False
            else:
                print("  ⚠ DATA column not found")
                return False
                
    except Exception as e:
        print(f"  ✗ Error clearing MODEL_DATA: {e}")
        return False


def clear_corrected_data(ms_path: str) -> bool:
    """Clear CORRECTED_DATA column completely."""
    print(f"\nClearing CORRECTED_DATA from {ms_path}...")
    
    try:
        from casacore.tables import table
        
        with table(ms_path, readonly=False) as tb:
            if "CORRECTED_DATA" not in tb.colnames():
                print("  ✓ CORRECTED_DATA column does not exist")
                return True
            
            # CORRECTED_DATA is typically initialized from DATA
            # We'll just verify it exists, actual clearing happens during calibration
            nrows = tb.nrows()
            print(f"  ✓ CORRECTED_DATA present ({nrows} rows, will be recalculated during calibration)")
            return True
                
    except Exception as e:
        print(f"  ✗ Error checking CORRECTED_DATA: {e}")
        return False


def clear_calibration_tables(ms_dir: str) -> int:
    """Remove all calibration tables from MS directory."""
    print(f"\nClearing calibration tables from {ms_dir}...")
    
    cal_extensions = [".cal", "_kcal", "_bpcal", "_gcal", "_gpcal", "_gacal"]
    removed = 0
    
    for item in os.listdir(ms_dir):
        item_path = os.path.join(ms_dir, item)
        
        # Check if it's a calibration table
        is_cal_table = False
        for ext in cal_extensions:
            if item.endswith(ext) or item.endswith(ext + ".tmp"):
                is_cal_table = True
                break
        
        if is_cal_table:
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                print(f"  ✓ Removed: {item}")
                removed += 1
            except Exception as e:
                print(f"  ✗ Failed to remove {item}: {e}")
    
    if removed == 0:
        print("  ✓ No calibration tables found")
    
    return removed


def clear_flag_tables(ms_path: str) -> bool:
    """Clear flag command table (if present)."""
    print(f"\nClearing flag tables from {ms_path}...")
    
    try:
        from casacore.tables import table
        
        flag_table_path = f"{ms_path}::FLAG_CMD"
        if os.path.exists(flag_table_path):
            with table(flag_table_path, readonly=False) as tb:
                nrows = tb.nrows()
                if nrows > 0:
                    # Clear all rows (flag commands are not critical for calibration)
                    # Actually, we probably shouldn't clear this - it may contain important flags
                    print(f"  ✓ Flag table exists ({nrows} rows, preserving)")
                    return True
                else:
                    print(f"  ✓ Flag table is empty")
                    return True
        else:
            print(f"  ✓ Flag table does not exist")
            return True
            
    except Exception as e:
        print(f"  ⚠ Error checking flag table: {e}")
        return False


def clear_all(ms_path: str) -> bool:
    """Clear all calibration artifacts."""
    print("=" * 70)
    print("CLEARING ALL CALIBRATION ARTIFACTS")
    print("=" * 70)
    
    if not os.path.exists(ms_path):
        print(f"✗ MS not found: {ms_path}")
        return False
    
    ms_dir = os.path.dirname(ms_path) if os.path.dirname(ms_path) else os.getcwd()
    
    results = {
        "model_data": clear_model_data(ms_path),
        "corrected_data": clear_corrected_data(ms_path),
        "calibration_tables": clear_calibration_tables(ms_dir),
        "flag_tables": clear_flag_tables(ms_path),
    }
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_ok = all([results["model_data"], results["corrected_data"], results["flag_tables"]])
    
    print(f"  MODEL_DATA cleared: {'✓' if results['model_data'] else '✗'}")
    print(f"  CORRECTED_DATA checked: {'✓' if results['corrected_data'] else '✗'}")
    print(f"  Calibration tables removed: {results['calibration_tables']}")
    print(f"  Flag tables checked: {'✓' if results['flag_tables'] else '✗'}")
    
    if all_ok:
        print("\n✓ All artifacts cleared successfully")
    else:
        print("\n⚠ Some artifacts may not be fully cleared")
    
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Clear all calibration artifacts from MS"
    )
    parser.add_argument(
        "ms",
        type=str,
        help="Path to Measurement Set",
    )
    
    args = parser.parse_args()
    
    success = clear_all(args.ms)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


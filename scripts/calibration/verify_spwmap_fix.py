#!/opt/miniforge/envs/casa6/bin/python
"""
Verify that the spwmap fix is working correctly.

This script checks:
1. If bandpass table has only 1 SPW (from combine_spw)
2. If gain tables have solutions for all SPWs (should have 16 SPWs)
3. Whether the fix would correctly detect and apply spwmap

Usage:
    python scripts/verify_spwmap_fix.py <bandpass_table> <gain_table> <ms_path>
"""

import sys
from pathlib import Path


def get_caltable_spw_count(caltable_path: str):
    """Get the number of unique spectral windows in a calibration table."""
    import numpy as np
    from casacore.tables import table
    
    try:
        with table(caltable_path, readonly=True, ack=False) as tb:
            if "SPECTRAL_WINDOW_ID" not in tb.colnames():
                return None
            spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
            return len(np.unique(spw_ids))
    except Exception as e:
        print(f"Error reading {caltable_path}: {e}")
        return None

def get_ms_spw_count(ms_path: str):
    """Get the number of spectral windows in an MS."""
    from casacore.tables import table
    
    try:
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True, ack=False) as spw:
            return spw.nrows()
    except Exception:
        return None

def check_gain_solutions(gain_table: str):
    """Check if gain table has solutions for all SPWs."""
    import numpy as np
    from casacore.tables import table
    
    try:
        with table(gain_table, readonly=True, ack=False) as tb:
            if "SPECTRAL_WINDOW_ID" not in tb.colnames():
                return None, None
            
            spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
            flags = tb.getcol("FLAG")
            
            # Get unique SPWs and their solution status
            unique_spws = sorted(set(spw_ids))
            spw_status = {}
            
            for spw_id in unique_spws:
                spw_mask = spw_ids == spw_id
                spw_flags = flags[spw_mask]
                # Check if any solutions exist (not all flagged)
                has_solutions = not np.all(spw_flags)
                spw_status[spw_id] = has_solutions
            
            return unique_spws, spw_status
    except Exception as e:
        print(f"Error reading {gain_table}: {e}")
        return None, None

def main():
    if len(sys.argv) < 4:
        print("Usage: python verify_spwmap_fix.py <bandpass_table> <gain_table> <ms_path>")
        sys.exit(1)
    
    bp_table = sys.argv[1]
    gain_table = sys.argv[2]
    ms_path = sys.argv[3]
    
    print("=" * 70)
    print("Verifying spwmap Fix for combine_spw Bandpass Tables")
    print("=" * 70)
    
    # Check MS SPW count
    n_ms_spw = get_ms_spw_count(ms_path)
    print(f"\n1. MS Spectral Windows: {n_ms_spw}")
    
    # Check bandpass table SPW count
    n_bp_spw = get_caltable_spw_count(bp_table)
    print(f"2. Bandpass Table SPWs: {n_bp_spw}")
    
    if n_bp_spw == 1:
        print("   ✓ Bandpass table has 1 SPW (from combine_spw)")
        print(f"   → Fix should detect this and set spwmap=[0]*{n_ms_spw}")
    else:
        print(f"   ℹ Bandpass table has {n_bp_spw} SPWs (not from combine_spw)")
    
    # Check gain table solutions
    print(f"\n3. Gain Table Solutions:")
    gain_spws, spw_status = check_gain_solutions(gain_table)
    
    if gain_spws is None:
        print("   ✗ Could not read gain table")
        sys.exit(1)
    
    print(f"   Gain table has solutions for {len(gain_spws)} SPWs: {gain_spws}")
    
    # Check if all MS SPWs have solutions
    if n_ms_spw is not None:
        expected_spws = set(range(n_ms_spw))
        gain_spw_set = set(gain_spws)
        
        missing_spws = expected_spws - gain_spw_set
        
        print(f"\n4. Solution Coverage:")
        print(f"   Expected SPWs: {sorted(expected_spws)}")
        print(f"   Gain table SPWs: {sorted(gain_spw_set)}")
        
        if missing_spws:
            print(f"   ✗ MISSING SPWs: {sorted(missing_spws)}")
            print(f"\n   ⚠ ISSUE: Gain calibration failed for {len(missing_spws)} SPWs")
            print(f"   This suggests the spwmap fix was NOT applied or did not work.")
            return False
        else:
            print(f"   ✓ All {n_ms_spw} SPWs have solutions")
            
            # Check if solutions are actually valid (not all flagged)
            all_valid = True
            for spw_id in sorted(gain_spws):
                if spw_id in spw_status:
                    if not spw_status[spw_id]:
                        print(f"   ⚠ SPW {spw_id}: All solutions flagged")
                        all_valid = False
                else:
                    print(f"   ⚠ SPW {spw_id}: Status unknown")
                    all_valid = False
            
            if all_valid:
                print(f"\n   ✓ SUCCESS: All SPWs have valid solutions")
                if n_bp_spw == 1:
                    print(f"   ✓ The spwmap fix is working correctly!")
                return True
            else:
                print(f"\n   ⚠ Some SPWs have all solutions flagged (may be data quality issue)")
                return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


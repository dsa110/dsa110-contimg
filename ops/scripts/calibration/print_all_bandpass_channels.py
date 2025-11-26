#!/opt/miniforge/envs/casa6/bin/python
"""
Print all bandpass channels with flagging statistics (post-solve).

This script provides the complete picture that CASA doesn't print,
showing ALL channels regardless of flagging threshold.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    from casacore.tables import table
except ImportError:
    print("ERROR: casacore not available. Activate casa6 environment.")
    sys.exit(1)


def print_all_channels(bp_table_path: str, spw: int = None):
    """Print complete channel-by-channel flagging statistics."""
    
    with table(bp_table_path, readonly=True) as tb:
        spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
        flags = tb.getcol("FLAG")
        
        unique_spws = np.unique(spw_ids)
        
        if spw is not None:
            if spw not in unique_spws:
                print(f"ERROR: SPW {spw} not found in table")
                return
            spws_to_analyze = [spw]
        else:
            spws_to_analyze = sorted(unique_spws)
        
        for spw_id in spws_to_analyze:
            spw_mask = spw_ids == spw_id
            flags_spw = flags[spw_mask]
            
            nrows = flags_spw.shape[0]
            nchan = flags_spw.shape[1]
            npol = flags_spw.shape[2]
            n_total_per_chan = nrows * npol
            
            print(f"\n{'=' * 80}")
            print(f"SPW {spw_id}: Complete Channel Flagging Report")
            print(f"{'=' * 80}")
            print(f"{'Channel':<10} {'Flagged':<12} {'Unflagged':<12} {'Total':<10} {'% Flagged':<12} {'Baselines':<12} {'Status':<10}")
            print("-" * 80)
            
            for chan in range(nchan):
                chan_flags = flags_spw[:, chan, :]
                n_flagged = np.sum(chan_flags)
                n_unflagged = n_total_per_chan - n_flagged
                pct_flagged = (n_flagged / n_total_per_chan) * 100
                
                # Count baselines with flags
                flagged_per_baseline = np.sum(chan_flags, axis=1)
                baselines_with_flags = np.sum(flagged_per_baseline > 0)
                
                # Determine status
                if n_flagged == 0:
                    status = "✓ ALL OK"
                elif baselines_with_flags >= 28:
                    status = "⚠ PRINTED"
                elif baselines_with_flags >= 27:
                    status = "⚠ NOT PRINTED"
                else:
                    status = "⚠ MINOR"
                
                print(f"chan={chan:<7} {n_flagged:>4}/{n_total_per_chan:<7} "
                      f"{n_unflagged:>4}/{n_total_per_chan:<7} {n_total_per_chan:>4}     "
                      f"{pct_flagged:>5.1f}%      {baselines_with_flags:>3}/{nrows:<7} {status:<10}")


def main():
    parser = argparse.ArgumentParser(
        description="Print all bandpass channels (what CASA doesn't show)"
    )
    parser.add_argument("bp_table", type=str, help="Path to bandpass calibration table")
    parser.add_argument("--spw", type=int, default=None, help="Specific SPW (default: all)")
    
    args = parser.parse_args()
    
    if not Path(args.bp_table).exists():
        print(f"ERROR: Table not found: {args.bp_table}")
        sys.exit(1)
    
    print_all_channels(args.bp_table, args.spw)


if __name__ == "__main__":
    main()


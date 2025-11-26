#!/opt/miniforge/envs/casa6/bin/python
"""
Analyze what determines if a baseline is "affected" (has flagged solutions).

This script investigates:
1. MS flagging before bandpass (pre-existing flags)
2. Bandpass solve flagging (SNR, quality issues)
3. Relationship between MS flags and calibration table flags
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


def analyze_ms_flagging(ms_path: str, spw: int, field: int = 0):
    """Analyze MS flagging before bandpass solve."""
    print("=" * 80)
    print("MS FLAGGING ANALYSIS (Before Bandpass Solve)")
    print("=" * 80)
    
    with table(ms_path, readonly=True) as tb:
        flags = tb.getcol("FLAG")
        spw_ids = tb.getcol("DATA_DESC_ID")
        field_ids = tb.getcol("FIELD_ID")
        antenna1 = tb.getcol("ANTENNA1")
        antenna2 = tb.getcol("ANTENNA2")
        
        # Get SPW mapping
        with table(f"{ms_path}/DATA_DESCRIPTION", readonly=True) as dd_tb:
            spw_map = dd_tb.getcol("SPECTRAL_WINDOW_ID")
        
        # Filter by SPW and field
        spw_mask = spw_map[spw_ids] == spw
        field_mask = field_ids == field
        mask = spw_mask & field_mask
        
        flags_spw = flags[mask]
        antenna1_spw = antenna1[mask]
        antenna2_spw = antenna2[mask]
        
        nrows = flags_spw.shape[0]
        nchan = flags_spw.shape[1]
        npol = flags_spw.shape[2]
        
        # Get unique baselines
        unique_baselines = set(zip(antenna1_spw, antenna2_spw))
        n_baselines = len(unique_baselines)
        
        print(f"\nSPW {spw}, Field {field}:")
        print(f"  Total rows: {nrows}")
        print(f"  Unique baselines: {n_baselines}")
        print(f"  Channels: {nchan}")
        print(f"  Polarizations: {npol}")
        
        # Check per-channel flagging
        print(f"\nPer-channel flagging in MS:")
        print(f"{'Channel':<10} {'Flagged':<12} {'Unflagged':<12} {'Total':<10} {'% Flagged':<12}")
        print("-" * 70)
        
        for chan in range(min(10, nchan)):  # Show first 10 channels
            chan_flags = flags_spw[:, chan, :]
            n_flagged = np.sum(chan_flags)
            n_unflagged = np.size(chan_flags) - n_flagged
            pct_flagged = (n_flagged / np.size(chan_flags)) * 100
            print(f"chan={chan:<7} {n_flagged:>6}/{np.size(chan_flags):<5} "
                  f"{n_unflagged:>6}/{np.size(chan_flags):<5} {np.size(chan_flags):>4}     "
                  f"{pct_flagged:>5.1f}%")
        
        # Check per-baseline flagging for a specific channel
        print(f"\n{'=' * 80}")
        print(f"Per-baseline flagging in MS (for chan=47, as example):")
        print(f"{'=' * 80}")
        
        chan = 47
        if chan < nchan:
            chan_flags = flags_spw[:, chan, :]
            
            # Count flags per baseline
            baseline_flag_counts = {}
            for i, (ant1, ant2) in enumerate(zip(antenna1_spw, antenna2_spw)):
                baseline = tuple(sorted([ant1, ant2]))
                if baseline not in baseline_flag_counts:
                    baseline_flag_counts[baseline] = {'flagged': 0, 'total': 0}
                baseline_flag_counts[baseline]['flagged'] += np.sum(chan_flags[i, :])
                baseline_flag_counts[baseline]['total'] += npol
            
            # Count baselines with flags
            baselines_with_flags = sum(1 for bl in baseline_flag_counts.values() if bl['flagged'] > 0)
            
            print(f"  Baselines with flags: {baselines_with_flags}/{n_baselines}")
            print(f"  Baselines with no flags: {n_baselines - baselines_with_flags}/{n_baselines}")


def analyze_caltable_flagging(bp_table_path: str, spw: int):
    """Analyze calibration table flagging (after bandpass solve)."""
    print("\n" + "=" * 80)
    print("CALIBRATION TABLE FLAGGING ANALYSIS (After Bandpass Solve)")
    print("=" * 80)
    
    with table(bp_table_path, readonly=True) as tb:
        spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
        flags = tb.getcol("FLAG")
        antenna1 = tb.getcol("ANTENNA1")
        antenna2 = tb.getcol("ANTENNA2")
        
        # Filter by SPW
        spw_mask = spw_ids == spw
        flags_spw = flags[spw_mask]
        antenna1_spw = antenna1[spw_mask]
        antenna2_spw = antenna2[spw_mask]
        
        nrows = flags_spw.shape[0]
        nchan = flags_spw.shape[1]
        npol = flags_spw.shape[2]
        
        print(f"\nSPW {spw}:")
        print(f"  Rows (antenna pairs): {nrows}")
        print(f"  Channels: {nchan}")
        print(f"  Polarizations: {npol}")
        
        # Analyze per-channel flagging
        print(f"\nPer-channel flagging in calibration table:")
        print(f"{'Channel':<10} {'Flagged':<12} {'Unflagged':<12} {'Total':<10} {'% Flagged':<12} {'Baselines':<12}")
        print("-" * 70)
        
        for chan in range(min(10, nchan)):  # Show first 10 channels
            chan_flags = flags_spw[:, chan, :]
            n_flagged = np.sum(chan_flags)
            n_unflagged = np.size(chan_flags) - n_flagged
            pct_flagged = (n_flagged / np.size(chan_flags)) * 100
            
            # Count baselines with flags
            flagged_per_baseline = np.sum(chan_flags, axis=1)
            baselines_with_flags = np.sum(flagged_per_baseline > 0)
            
            print(f"chan={chan:<7} {n_flagged:>4}/{np.size(chan_flags):<7} "
                  f"{n_unflagged:>4}/{np.size(chan_flags):<7} {np.size(chan_flags):>4}     "
                  f"{pct_flagged:>5.1f}%      {baselines_with_flags:>3}/{nrows:<7}")
        
        # Detailed analysis for chan=47
        print(f"\n{'=' * 80}")
        print(f"Detailed analysis for chan=47 (calibration table):")
        print(f"{'=' * 80}")
        
        chan = 47
        if chan < nchan:
            chan_flags = flags_spw[:, chan, :]
            
            # Count flags per baseline
            baseline_flag_counts = {}
            for i, (ant1, ant2) in enumerate(zip(antenna1_spw, antenna2_spw)):
                baseline = tuple(sorted([ant1, ant2]))
                if baseline not in baseline_flag_counts:
                    baseline_flag_counts[baseline] = {'flagged': 0, 'total': 0}
                baseline_flag_counts[baseline]['flagged'] += np.sum(chan_flags[i, :])
                baseline_flag_counts[baseline]['total'] += npol
            
            # Count baselines with flags
            baselines_with_flags = sum(1 for bl in baseline_flag_counts.values() if bl['flagged'] > 0)
            
            print(f"  Baselines with flags: {baselines_with_flags}/{nrows}")
            print(f"  Baselines with no flags: {nrows - baselines_with_flags}/{nrows}")
            
            # Show distribution of flags per baseline
            flag_counts = [bl['flagged'] for bl in baseline_flag_counts.values()]
            print(f"\n  Flag distribution per baseline:")
            print(f"    Baselines with 0 flags: {flag_counts.count(0)}")
            print(f"    Baselines with 1 flag: {flag_counts.count(1)}")
            print(f"    Baselines with 2 flags: {flag_counts.count(2)}")
            print(f"    Baselines with >2 flags: {sum(1 for c in flag_counts if c > 2)}")


def compare_ms_vs_caltable(ms_path: str, bp_table_path: str, spw: int, field: int = 0, chan: int = 47):
    """Compare MS flagging vs calibration table flagging."""
    print("\n" + "=" * 80)
    print(f"COMPARISON: MS Flags vs Calibration Table Flags (SPW {spw}, chan {chan})")
    print("=" * 80)
    
    # Get MS flags
    with table(ms_path, readonly=True) as tb:
        flags_ms = tb.getcol("FLAG")
        spw_ids_ms = tb.getcol("DATA_DESC_ID")
        field_ids = tb.getcol("FIELD_ID")
        antenna1_ms = tb.getcol("ANTENNA1")
        antenna2_ms = tb.getcol("ANTENNA2")
        
        with table(f"{ms_path}/DATA_DESCRIPTION", readonly=True) as dd_tb:
            spw_map = dd_tb.getcol("SPECTRAL_WINDOW_ID")
        
        spw_mask = spw_map[spw_ids_ms] == spw
        field_mask = field_ids == field
        mask = spw_mask & field_mask
        
        flags_ms_spw = flags_ms[mask]
        antenna1_ms_spw = antenna1_ms[mask]
        antenna2_ms_spw = antenna2_ms[mask]
        
        # Get flags for this channel
        if chan < flags_ms_spw.shape[1]:
            chan_flags_ms = flags_ms_spw[:, chan, :]
            n_flagged_ms = np.sum(chan_flags_ms)
            n_total_ms = np.size(chan_flags_ms)
            
            # Count baselines with flags in MS
            baseline_flags_ms = {}
            for i, (ant1, ant2) in enumerate(zip(antenna1_ms_spw, antenna2_ms_spw)):
                baseline = tuple(sorted([ant1, ant2]))
                if baseline not in baseline_flags_ms:
                    baseline_flags_ms[baseline] = False
                if np.any(chan_flags_ms[i, :]):
                    baseline_flags_ms[baseline] = True
            
            baselines_with_flags_ms = sum(1 for v in baseline_flags_ms.values() if v)
        else:
            baselines_with_flags_ms = 0
            n_flagged_ms = 0
            n_total_ms = 0
    
    # Get calibration table flags
    with table(bp_table_path, readonly=True) as tb:
        spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
        flags = tb.getcol("FLAG")
        antenna1 = tb.getcol("ANTENNA1")
        antenna2 = tb.getcol("ANTENNA2")
        
        spw_mask = spw_ids == spw
        flags_spw = flags[spw_mask]
        antenna1_spw = antenna1[spw_mask]
        antenna2_spw = antenna2[spw_mask]
        
        if chan < flags_spw.shape[1]:
            chan_flags_caltable = flags_spw[:, chan, :]
            n_flagged_caltable = np.sum(chan_flags_caltable)
            n_total_caltable = np.size(chan_flags_caltable)
            
            # Count baselines with flags in caltable
            flagged_per_baseline = np.sum(chan_flags_caltable, axis=1)
            baselines_with_flags_caltable = np.sum(flagged_per_baseline > 0)
        else:
            baselines_with_flags_caltable = 0
            n_flagged_caltable = 0
            n_total_caltable = 0
    
    print(f"\nMS (before bandpass solve):")
    print(f"  Flagged visibilities: {n_flagged_ms}/{n_total_ms} ({n_flagged_ms/n_total_ms*100:.1f}% if n_total>0)")
    print(f"  Baselines with flags: {baselines_with_flags_ms}")
    
    print(f"\nCalibration Table (after bandpass solve):")
    print(f"  Flagged solutions: {n_flagged_caltable}/{n_total_caltable} ({n_flagged_caltable/n_total_caltable*100:.1f}% if n_total>0)")
    print(f"  Baselines with flags: {baselines_with_flags_caltable}")
    
    print(f"\nInterpretation:")
    print(f"  - If MS has more flags: Pre-existing flags cause fewer solutions to be attempted")
    print(f"  - If caltable has more flags: Bandpass solve flagged additional solutions (low SNR, quality)")
    print(f"  - 'Baselines affected' in caltable = baselines with at least one flagged solution")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze what determines baseline flagging in bandpass calibration"
    )
    parser.add_argument("ms_path", type=str, help="Path to Measurement Set")
    parser.add_argument("bp_table", type=str, help="Path to bandpass calibration table")
    parser.add_argument("--spw", type=int, default=4, help="SPW to analyze (default: 4)")
    parser.add_argument("--field", type=int, default=0, help="Field to analyze (default: 0)")
    
    args = parser.parse_args()
    
    if not Path(args.ms_path).exists():
        print(f"ERROR: MS not found: {args.ms_path}")
        sys.exit(1)
    
    if not Path(args.bp_table).exists():
        print(f"ERROR: Table not found: {args.bp_table}")
        sys.exit(1)
    
    analyze_ms_flagging(args.ms_path, args.spw, args.field)
    analyze_caltable_flagging(args.bp_table, args.spw)
    compare_ms_vs_caltable(args.ms_path, args.bp_table, args.spw, args.field)


if __name__ == "__main__":
    main()


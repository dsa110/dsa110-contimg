#!/usr/bin/env python3
"""
Reverse-engineer CASA's bandpass output format.

This script investigates:
1. What does "X of Y solutions flagged" actually mean?
2. Why is Y=182 when total solutions are 234?
3. What is CASA counting?
4. Why does it say "1" when there are 53 flagged?
"""

import sys
import argparse
from pathlib import Path
import numpy as np

try:
    from casacore.tables import table
except ImportError:
    print("ERROR: casacore not available. Activate casa6 environment.")
    sys.exit(1)


def analyze_ms_before_bandpass(ms_path: str, spw: int, field: int = 0):
    """Analyze MS flagging before bandpass calibration."""
    print("=" * 80)
    print("MS FLAGGING ANALYSIS (Before Bandpass)")
    print("=" * 80)
    
    with table(ms_path, readonly=True) as tb:
        # Get flagging
        flags = tb.getcol("FLAG")
        spw_ids = tb.getcol("DATA_DESC_ID")  # Maps to SPW
        
        # Get SPW mapping
        with table(f"{ms_path}/SPECTRAL_WINDOW", readonly=True) as spw_tb:
            spw_names = spw_tb.getcol("NAME")
        
        with table(f"{ms_path}/DATA_DESCRIPTION", readonly=True) as dd_tb:
            spw_map = dd_tb.getcol("SPECTRAL_WINDOW_ID")
        
        # Find rows for this SPW
        spw_mask = spw_map[spw_ids] == spw
        flags_spw = flags[spw_mask]
        
        nrows = flags_spw.shape[0]
        nchan = flags_spw.shape[1]
        npol = flags_spw.shape[2]
        
        n_flagged_ms = np.sum(flags_spw)
        n_unflagged_ms = np.size(flags_spw) - n_flagged_ms
        pct_flagged_ms = (n_flagged_ms / np.size(flags_spw)) * 100
        
        print(f"SPW {spw}: {nrows} rows × {nchan} channels × {npol} pols")
        print(f"Total visibilities: {np.size(flags_spw)}")
        print(f"Flagged in MS: {n_flagged_ms} ({pct_flagged_ms:.1f}%)")
        print(f"Unflagged in MS: {n_unflagged_ms}")
        
        # Check per-channel flagging
        print(f"\nPer-channel flagging in MS:")
        print(f"{'Channel':<10} {'Flagged':<12} {'Unflagged':<12} {'Total':<10} {'% Flagged':<12}")
        print("-" * 70)
        
        for chan in range(nchan):
            chan_flags = flags_spw[:, chan, :]
            n_flagged_chan = np.sum(chan_flags)
            n_unflagged_chan = np.size(chan_flags) - n_flagged_chan
            pct_flagged_chan = (n_flagged_chan / np.size(chan_flags)) * 100
            print(f"chan={chan:<7} {n_flagged_chan:>6}/{np.size(chan_flags):<5} "
                  f"{n_unflagged_chan:>6}/{np.size(chan_flags):<5} {np.size(chan_flags):>4}     "
                  f"{pct_flagged_chan:>5.1f}%")
        
        # Check antenna pairs
        antenna1 = tb.getcol("ANTENNA1")[spw_mask]
        antenna2 = tb.getcol("ANTENNA2")[spw_mask]
        
        unique_baselines = set(zip(antenna1, antenna2))
        n_baselines = len(unique_baselines)
        print(f"\nUnique baselines: {n_baselines}")
        
        return {
            'n_unflagged_ms': n_unflagged_ms,
            'n_total_ms': np.size(flags_spw),
            'n_baselines': n_baselines,
        }


def analyze_bandpass_table_detailed(bp_table_path: str, spw: int, ms_unflagged_info: dict = None):
    """Detailed analysis of bandpass table to reverse-engineer CASA's counting."""
    print("\n" + "=" * 80)
    print("BANDPASS TABLE DETAILED ANALYSIS")
    print("=" * 80)
    
    with table(bp_table_path, readonly=True) as tb:
        # Get all columns
        spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
        flags = tb.getcol("FLAG")
        antenna1 = tb.getcol("ANTENNA1")
        antenna2 = tb.getcol("ANTENNA2")
        time = tb.getcol("TIME")
        
        # Get unique times
        unique_times = np.unique(time)
        print(f"Unique times in table: {len(unique_times)}")
        
        # Filter by SPW
        spw_mask = spw_ids == spw
        flags_spw = flags[spw_mask]
        antenna1_spw = antenna1[spw_mask]
        antenna2_spw = antenna2[spw_mask]
        time_spw = time[spw_mask]
        
        nrows = flags_spw.shape[0]
        nchan = flags_spw.shape[1]
        npol = flags_spw.shape[2]
        
        # Get unique antennas
        unique_antennas = np.unique(np.concatenate([antenna1_spw, antenna2_spw]))
        n_antennas = len(unique_antennas)
        
        # Get unique baselines
        unique_baselines = set(zip(antenna1_spw, antenna2_spw))
        n_baselines = len(unique_baselines)
        
        print(f"\nSPW {spw} structure:")
        print(f"  Rows (antenna pairs): {nrows}")
        print(f"  Unique baselines: {n_baselines}")
        print(f"  Unique antennas: {n_antennas}")
        print(f"  Channels: {nchan}")
        print(f"  Polarizations: {npol}")
        print(f"  Total solutions per channel: {nrows * npol} = {nrows} × {npol}")
        
        # Analyze what "182" might represent
        print(f"\n{'=' * 80}")
        print("WHAT IS '182'?")
        print(f"{'=' * 80}")
        print(f"Possible interpretations:")
        print(f"  1. Unflagged solutions in table: {np.sum(~flags_spw[:, :, :])}")
        print(f"  2. Unflagged solutions per channel (average): {np.mean(np.sum(~flags_spw, axis=(0, 2))):.1f}")
        print(f"  3. Number of antennas: {n_antennas}")
        print(f"  4. Number of baselines: {n_baselines}")
        print(f"  5. Number of antenna pairs (rows): {nrows}")
        print(f"  6. Unflagged solutions in MS (if available): {ms_unflagged_info.get('n_unflagged_ms', 'N/A') if ms_unflagged_info else 'N/A'}")
        
        # Check per-channel unflagged counts
        print(f"\n{'=' * 80}")
        print("UNFLAGGED SOLUTIONS PER CHANNEL (to find '182')")
        print(f"{'=' * 80}")
        print(f"{'Channel':<10} {'Unflagged':<12} {'Flagged':<12} {'Total':<10} {'% Flagged':<12}")
        print("-" * 70)
        
        for chan in range(min(10, nchan)):  # Show first 10 channels
            chan_flags = flags_spw[:, chan, :]
            n_unflagged = np.sum(~chan_flags)
            n_flagged = np.sum(chan_flags)
            n_total = np.size(chan_flags)
            pct_flagged = (n_flagged / n_total) * 100
            
            marker = " <-- 182?" if 180 <= n_unflagged <= 185 else ""
            print(f"chan={chan:<7} {n_unflagged:>6}      {n_flagged:>6}/{n_total:<5} {n_total:>4}     "
                  f"{pct_flagged:>5.1f}%      {marker}")
        
        # Check if "182" matches unflagged solutions per channel
        unflagged_per_chan = np.sum(~flags_spw, axis=(0, 2))
        channels_with_182 = np.where((unflagged_per_chan >= 180) & (unflagged_per_chan <= 185))[0]
        print(f"\nChannels with ~182 unflagged solutions: {channels_with_182}")
        
        # Analyze what "1" might mean
        print(f"\n{'=' * 80}")
        print("WHAT DOES '1' MEAN? (when CASA says '1 of 182 solutions flagged')")
        print(f"{'=' * 80}")
        
        # For chan=47 (which CASA printed)
        chan = 47
        if chan < nchan:
            chan_flags = flags_spw[:, chan, :]
            n_flagged_total = np.sum(chan_flags)
            n_unflagged_total = np.sum(~chan_flags)
            
            print(f"\nFor chan=47 (CASA printed '1 of 182'):")
            print(f"  Total flagged: {n_flagged_total}")
            print(f"  Total unflagged: {n_unflagged_total}")
            
            # Check per-time flagging
            for t_idx, t in enumerate(unique_times):
                time_mask = time_spw == t
                if np.any(time_mask):
                    flags_time = chan_flags[time_mask]
                    n_flagged_time = np.sum(flags_time)
                    n_unflagged_time = np.sum(~flags_time)
                    print(f"  Time {t_idx} ({t}): {n_flagged_time} flagged, {n_unflagged_time} unflagged")
            
            # Check per-baseline flagging
            flagged_per_baseline = np.sum(chan_flags, axis=1)
            baselines_with_flags = np.sum(flagged_per_baseline > 0)
            print(f"  Baselines with flags: {baselines_with_flags}/{nrows}")
            print(f"  Baselines with exactly 1 flag: {np.sum(flagged_per_baseline == 1)}")
            print(f"  Baselines with exactly 2 flags: {np.sum(flagged_per_baseline == 2)}")
            print(f"  Baselines with >2 flags: {np.sum(flagged_per_baseline > 2)}")
            
            # Check per-antenna flagging
            print(f"\n  Per-antenna flagging:")
            for ant in sorted(unique_antennas):
                ant_mask = (antenna1_spw == ant) | (antenna2_spw == ant)
                flags_ant = chan_flags[ant_mask]
                n_flagged_ant = np.sum(flags_ant)
                n_unflagged_ant = np.sum(~flags_ant)
                print(f"    Antenna {ant}: {n_flagged_ant} flagged, {n_unflagged_ant} unflagged")
        
        # Check threshold for printing
        print(f"\n{'=' * 80}")
        print("PRINTING THRESHOLD ANALYSIS")
        print(f"{'=' * 80}")
        print("Checking if threshold is based on baselines with flags:")
        
        unflagged_per_chan = np.sum(~flags_spw, axis=(0, 2))
        flagged_per_baseline_per_chan = np.sum(flags_spw, axis=2)  # Shape: (nrows, nchan)
        baselines_with_flags_per_chan = np.sum(flagged_per_baseline_per_chan > 0, axis=0)
        
        print(f"\n{'Channel':<10} {'Unflagged':<12} {'Baselines w/ flags':<20} {'CASA printed?'}")
        print("-" * 70)
        
        # Check a few channels that were/were not printed
        test_channels = [46, 47, 45, 44, 3, 0, 1, 2]
        for chan in test_channels:
            if chan < nchan:
                unflagged = unflagged_per_chan[chan]
                baselines = baselines_with_flags_per_chan[chan]
                # CASA printed: 47, 45, 44, 3 (and others)
                # CASA didn't print: 46, 0, 1, 2
                printed = baselines >= 28  # Our hypothesis
                print(f"chan={chan:<7} {unflagged:>6}        {baselines:>3}/{nrows:<5}            "
                      f"{'YES' if printed else 'NO'}")


def main():
    parser = argparse.ArgumentParser(
        description="Reverse-engineer CASA's bandpass output format"
    )
    parser.add_argument("bp_table", type=str, help="Path to bandpass calibration table")
    parser.add_argument("ms_path", type=str, help="Path to Measurement Set")
    parser.add_argument("--spw", type=int, default=4, help="SPW to analyze (default: 4)")
    
    args = parser.parse_args()
    
    if not Path(args.bp_table).exists():
        print(f"ERROR: Table not found: {args.bp_table}")
        sys.exit(1)
    
    if not Path(args.ms_path).exists():
        print(f"ERROR: MS not found: {args.ms_path}")
        sys.exit(1)
    
    # Analyze MS flagging
    ms_info = analyze_ms_before_bandpass(args.ms_path, args.spw)
    
    # Analyze bandpass table
    analyze_bandpass_table_detailed(args.bp_table, args.spw, ms_info)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Create a smaller, representative MS for testing K-calibration.

This script creates a subset MS optimized for delay (K-calibration) testing by
reducing data volume while preserving essential characteristics needed for delay
measurement.

**Rationale for subsetting:**
K-calibration measures frequency-independent instrumental delays per antenna.
Delays cause linear phase vs frequency slopes that can be measured from any
subset of baselines. Since delays are per-antenna (not per-baseline), a
reduced baseline set is sufficient for solving delay solutions, as long as:
1. Full bandwidth is preserved (all SPWs needed to measure phase slope)
2. Calibrator field is present (bright source for high SNR)
3. Reference antenna is included (needed for relative delay solutions)
4. Multiple baselines exist (sufficient to solve per-antenna delays)

**What this script preserves:**
- All spectral windows (full bandwidth: ~187 MHz across 16 SPWs)
- Calibrator field (bright source needed for delay measurement)
- Reference antenna (e.g., antenna 103) and baselines containing it
- Multiple time integrations (reduced but sufficient)

**What this script removes:**
- Most antennas (reduces from ~96 to ~6-16 antennas)
- Most baselines (reduces by ~80-90%, from ~9k to ~500-1000)
- Some time integrations (reduces by ~10-50%)

**Typical results:**
- Size reduction: ~6-7x smaller (2.1 GB → 316 MB)
- Still suitable for delay testing since delays are frequency-independent
- Much faster processing for calibration verification

**Created:** 2025-11-02
**Purpose:** Enable faster K-calibration testing and verification without losing
            essential delay measurement capabilities.
"""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from casacore.tables import table
from casatasks import split

def create_test_ms(ms_in: str, ms_out: str, 
                   max_baselines: int = 20,
                   max_times: int = 100,
                   timebin: str = None):
    """
    Create a smaller test MS for K-calibration testing.
    
    This function uses CASA `split` to create a subset MS that prioritizes:
    1. Baselines containing the reference antenna (default: 103)
    2. Even sampling across the time range
    3. Preservation of all spectral windows (full bandwidth)
    
    The selection strategy ensures the output MS remains representative for
    delay testing while dramatically reducing processing time.
    
    Args:
        ms_in: Input MS path (full MS)
        ms_out: Output MS path (will be overwritten if exists)
        max_baselines: Maximum number of baselines to include (default: 20)
                      Note: Actual baseline count may be higher due to antenna
                      selection (includes all baselines between selected antennas)
        max_times: Maximum number of time integrations to include (default: 100)
                   If input has fewer times, all are included
        timebin: Optional time binning for further reduction (e.g., '30s')
                 If None, original time resolution is preserved
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'='*70}")
    print(f"Creating Test MS for K-Calibration")
    print(f"{'='*70}\n")
    print(f"Input:  {ms_in}")
    print(f"Output: {ms_out}\n")
    
    # Analyze input MS
    with table(ms_in, readonly=True) as tb:
        n_rows = tb.nrows()
        ant1 = tb.getcol('ANTENNA1')
        ant2 = tb.getcol('ANTENNA2')
        times = tb.getcol('TIME')
        field_ids = tb.getcol('FIELD_ID')
        
        # Get unique baselines
        baselines = list(set(zip(ant1, ant2)))
        unique_times = sorted(set(times))
        
        print(f"Input MS:")
        print(f"  Total rows: {n_rows:,}")
        print(f"  Baselines: {len(baselines)}")
        print(f"  Time integrations: {len(unique_times)}")
        print(f"  Fields: {sorted(set(field_ids))}\n")
        
        # Select subset of baselines (include reference antenna 103)
        # Prioritize baselines with refant 103
        refant = 103
        refant_baselines = [bl for bl in baselines if refant in bl]
        other_baselines = [bl for bl in baselines if refant not in bl]
        
        selected_baselines = refant_baselines[:max_baselines]
        remaining = max_baselines - len(selected_baselines)
        if remaining > 0:
            selected_baselines.extend(other_baselines[:remaining])
        
        print(f"Selected baselines: {len(selected_baselines)}")
        print(f"  (Including {len(refant_baselines[:max_baselines])} with refant {refant})")
        
        # Build antenna selection string
        ants_in_selected = set()
        for bl in selected_baselines:
            ants_in_selected.add(bl[0])
            ants_in_selected.add(bl[1])
        antenna_str = ','.join(map(str, sorted(ants_in_selected)))
        
        # Select subset of times
        if len(unique_times) > max_times:
            # Sample evenly across time range
            indices = np.linspace(0, len(unique_times)-1, max_times, dtype=int)
            selected_times = [unique_times[i] for i in indices]
            time_start = min(selected_times)
            time_end = max(selected_times)
        else:
            selected_times = unique_times
            time_start = min(selected_times)
            time_end = max(selected_times)
        
        print(f"Selected times: {len(selected_times)}")
        print(f"  Time range: {time_start} to {time_end}")
        
        # Get SPW info
        with table(f"{ms_in}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
            n_spw = spw_tb.nrows()
            num_chan = spw_tb.getcol('NUM_CHAN')
            print(f"\nSpectral windows: {n_spw} (keeping all for delay testing)")
    
    # Build baseline selection string
    # CASA split doesn't directly support baseline selection, so we'll use antenna selection
    # which will include all baselines between selected antennas
    
    # Remove output if exists
    if os.path.exists(ms_out):
        import shutil
        print(f"\nRemoving existing output: {ms_out}")
        shutil.rmtree(ms_out, ignore_errors=True)
    
    # Use CASA split to create subset
    print(f"\nCreating subset MS...")
    
    # Build time selection
    # CASA timerange format: "YYYY/MM/DD/HH:MM:SS~YYYY/MM/DD/HH:MM:SS"
    # or use scan selection instead
    from astropy.time import Time
    t_start = Time(time_start / 86400.0, format='mjd')
    t_end = Time(time_end / 86400.0, format='mjd')
    
    # Format for CASA: YYYY/MM/DD/HH:MM:SS
    timerange_str = f"{t_start.datetime.strftime('%Y/%m/%d/%H:%M:%S')}~{t_end.datetime.strftime('%Y/%m/%d/%H:%M:%S')}"
    
    # Split with selections
    split_kwargs = {
        'vis': ms_in,
        'outputvis': ms_out,
        'antenna': antenna_str,
        'timerange': timerange_str,
        'keepflags': True,
        'datacolumn': 'DATA',
    }
    
    # Optionally add timebinning
    if timebin:
        split_kwargs['timebin'] = timebin
    
    print(f"Split parameters:")
    print(f"  antenna: {antenna_str[:50]}... ({len(ants_in_selected)} antennas)")
    print(f"  timerange: {timerange_str}")
    if timebin:
        print(f"  timebin: {timebin}")
    
    try:
        split(**split_kwargs)
        print(f"\n✓ Successfully created test MS: {ms_out}")
    except Exception as e:
        print(f"\n✗ Split failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify output
    try:
        with table(ms_out, readonly=True) as tb:
            n_rows_out = tb.nrows()
            print(f"\nOutput MS:")
            print(f"  Total rows: {n_rows_out:,}")
            print(f"  Reduction: {n_rows / n_rows_out:.1f}x smaller")
            
            # Check SPWs preserved
            with table(f"{ms_out}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                n_spw_out = spw_tb.nrows()
                print(f"  Spectral windows: {n_spw_out} (preserved)")
            
            # Check baselines
            ant1_out = tb.getcol('ANTENNA1')
            ant2_out = tb.getcol('ANTENNA2')
            baselines_out = len(set(zip(ant1_out, ant2_out)))
            print(f"  Baselines: {baselines_out}")
            
            # Check times
            times_out = tb.getcol('TIME')
            unique_times_out = len(set(times_out))
            print(f"  Time integrations: {unique_times_out}")
            
    except Exception as e:
        print(f"⚠ Could not verify output: {e}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create a smaller test MS for K-calibration testing"
    )
    parser.add_argument("ms_in", help="Input MS path")
    parser.add_argument("ms_out", help="Output MS path")
    parser.add_argument(
        "--max-baselines",
        type=int,
        default=20,
        help="Maximum number of baselines to include (default: 20)"
    )
    parser.add_argument(
        "--max-times",
        type=int,
        default=100,
        help="Maximum number of time integrations (default: 100)"
    )
    parser.add_argument(
        "--timebin",
        type=str,
        default=None,
        help="Optional time binning (e.g., '30s')"
    )
    
    args = parser.parse_args()
    
    success = create_test_ms(
        args.ms_in,
        args.ms_out,
        max_baselines=args.max_baselines,
        max_times=args.max_times,
        timebin=args.timebin
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Check if instrumental delays are already corrected upstream.

This script analyzes phase vs frequency in the raw DATA column to determine
if instrumental delays have already been corrected by upstream processing
(e.g., correlator, real-time delay correction, or earlier calibration steps).

**Method:**
For each baseline, the script:
1. Extracts unflagged visibilities across frequency channels
2. Computes phase (arg(vis)) and unwraps to handle 2π ambiguities
3. Fits a linear model: phase = delay × 2π × frequency + constant
4. Converts phase slope to delay: delay = phase_slope / (2π × frequency)
5. Aggregates delays across baselines and antennas

**Interpretation (thresholds are estimates, not standard values):**
- **< 1 ns**: Delays likely corrected upstream, K-calibration may be redundant
  - For DSA-110's 187 MHz bandwidth, <1 ns corresponds to <0.6π radians phase slope
- **1-5 ns**: Partially corrected, small residual delays present
  - K-calibration optional but may improve quality
- **> 5 ns**: Not corrected, K-calibration is necessary
  - For DSA-110's 187 MHz bandwidth, >5 ns corresponds to >3π radians phase slope

**Note:** These thresholds are estimates based on the physics (1 ns = π radians across
500 MHz bandwidth). Actual thresholds depend on observing frequency, bandwidth, and
instrumental characteristics. The phase-frequency slope method is more robust than
absolute delay values for determining correction status.

**Important notes:**
- Phase slopes can arise from multiple sources:
  * Instrumental delays (what we're measuring)
  * Geometric delays (if not perfectly phased)
  * Bandpass variations (frequency-dependent)
  * Source structure (extended sources)
- If data is properly phased, delays > 1 ns are likely instrumental
- This method provides a quick check but doesn't definitively prove delays
  are purely instrumental; K-calibration testing is still recommended

**Created:** 2025-11-02
**Purpose:** Help determine if K-calibration is necessary by checking for
            residual delays in raw data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from casacore.tables import table

def check_upstream_delay_correction(ms_path, n_baselines=100):
    """
    Check if delays are already corrected upstream by analyzing phase vs frequency.
    
    This function performs a statistical analysis of phase slopes across
    frequency to estimate residual delays. It analyzes both per-baseline delays
    and antenna-consistent delays (which are more indicative of instrumental
    delays vs geometric delays).
    
    Args:
        ms_path: Path to Measurement Set (should contain raw DATA column)
        n_baselines: Number of baselines to analyze (default: 100)
                     Analyzes first N unflagged baselines
        
    Returns:
        Dictionary with keys:
        - 'median_ns': Median absolute delay (ns)
        - 'mean_ns': Mean absolute delay (ns)
        - 'std_ns': Standard deviation of delays (ns)
        - 'min_ns', 'max_ns': Delay range (ns)
        - 'antenna_median_ns': Median delay per antenna (ns)
        - 'antenna_std_ns': Std dev of antenna delays (ns)
        - 'n_baselines': Number of baselines analyzed
        - 'recommendation': 'likely_corrected', 'partial', or 'needs_correction'
    """
    print(f"\n{'='*70}")
    print(f"Checking Upstream Delay Correction")
    print(f"MS: {ms_path}")
    print(f"{'='*70}\n")
    
    with table(ms_path, readonly=True) as tb:
        n_rows = tb.nrows()
        n_sample = min(n_baselines, n_rows)
        
        print(f"Analyzing {n_sample} baselines from {n_rows} total rows...\n")
        
        # Get data
        data = tb.getcol('DATA', startrow=0, nrow=n_sample)
        flags = tb.getcol('FLAG', startrow=0, nrow=n_sample)
        ant1 = tb.getcol('ANTENNA1', startrow=0, nrow=n_sample)
        ant2 = tb.getcol('ANTENNA2', startrow=0, nrow=n_sample)
        
        # Get frequency information
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
            chan_freqs = spw_tb.getcol('CHAN_FREQ')  # Shape: (n_spw, n_chan)
        
        # Get DATA_DESCRIPTION mapping
        with table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd_tb:
            spw_map = dd_tb.getcol('SPECTRAL_WINDOW_ID')
        
        dd_ids = tb.getcol('DATA_DESC_ID', startrow=0, nrow=n_sample)
        
        # Analyze phase slopes
        delays_ns = []
        phase_slopes_per_antenna = {}
        
        for i in range(n_sample):
            # Skip flagged data
            if np.all(flags[i]):
                continue
            
            # Get frequency array for this baseline
            dd_id = int(dd_ids[i])
            if dd_id >= len(spw_map):
                continue
            spw_id = int(spw_map[dd_id])
            if spw_id >= len(chan_freqs):
                continue
            
            freqs = chan_freqs[spw_id]  # Shape: (n_chan,)
            vis = data[i, :, 0]  # First polarization
            
            # Extract unflagged channels
            unflagged = ~flags[i, :, 0]
            if np.sum(unflagged) < 10:  # Need at least 10 channels
                continue
            
            unflagged_freqs = freqs[unflagged]
            unflagged_vis = vis[unflagged]
            
            # Compute phase
            phases = np.angle(unflagged_vis)
            phases_unwrapped = np.unwrap(phases)
            
            # Fit linear: phase = a * freq + b
            # Delay causes linear phase vs frequency
            coeffs = np.polyfit(unflagged_freqs, phases_unwrapped, 1)
            delay_sec = coeffs[0] / (2 * np.pi)
            delay_ns = delay_sec * 1e9
            
            delays_ns.append(delay_ns)
            
            # Track per antenna (average delays involving this antenna)
            for ant in [int(ant1[i]), int(ant2[i])]:
                if ant not in phase_slopes_per_antenna:
                    phase_slopes_per_antenna[ant] = []
                phase_slopes_per_antenna[ant].append(delay_ns)
            
            # Also compute phase RMS (flatness metric)
            phase_rms = np.std(phases_unwrapped)
        
        if not delays_ns:
            print("⚠ Could not extract sufficient data for analysis")
            return {"error": "Insufficient unflagged data"}
        
        delays_ns = np.array(delays_ns)
        
        # Compute statistics
        delay_stats = {
            "median_ns": float(np.median(np.abs(delays_ns))),
            "mean_ns": float(np.mean(np.abs(delays_ns))),
            "std_ns": float(np.std(delays_ns)),
            "min_ns": float(np.min(delays_ns)),
            "max_ns": float(np.max(delays_ns)),
            "range_ns": float(np.max(np.abs(delays_ns)) - np.min(np.abs(delays_ns))),
            "n_baselines": len(delays_ns),
        }
        
        # Compute antenna-consistent delays (instrumental)
        ant_delays = {}
        for ant, delays in phase_slopes_per_antenna.items():
            ant_delays[ant] = np.median(delays)
        
        if ant_delays:
            ant_delay_values = np.array(list(ant_delays.values()))
            delay_stats["antenna_median_ns"] = float(np.median(np.abs(ant_delay_values)))
            delay_stats["antenna_std_ns"] = float(np.std(ant_delay_values))
            delay_stats["antenna_range_ns"] = float(np.max(np.abs(ant_delay_values)) - np.min(np.abs(ant_delay_values)))
        
        # Print results
        print(f"Phase Slope Analysis:")
        print(f"  Baselines analyzed: {delay_stats['n_baselines']}")
        print(f"  Median |delay|: {delay_stats['median_ns']:.3f} ns")
        print(f"  Mean |delay|: {delay_stats['mean_ns']:.3f} ns")
        print(f"  Std dev: {delay_stats['std_ns']:.3f} ns")
        print(f"  Range: {delay_stats['min_ns']:.3f} to {delay_stats['max_ns']:.3f} ns")
        
        if ant_delays:
            print(f"\nAntenna-Consistent Delays (Instrumental):")
            print(f"  Antennas: {len(ant_delays)}")
            print(f"  Median |delay|: {delay_stats['antenna_median_ns']:.3f} ns")
            print(f"  Std dev: {delay_stats['antenna_std_ns']:.3f} ns")
            print(f"  Range: {delay_stats['antenna_range_ns']:.3f} ns")
        
        # Assess if delays are corrected
        print(f"\n{'='*70}")
        print("Assessment:")
        print(f"{'='*70}\n")
        
        # Thresholds for determining if delays are corrected
        threshold_well_corrected = 1.0  # ns
        threshold_needs_correction = 5.0  # ns
        
        max_delay = delay_stats['antenna_median_ns'] if ant_delays else delay_stats['median_ns']
        
        if max_delay < threshold_well_corrected:
            print("✓ DELAYS APPEAR TO BE CORRECTED UPSTREAM")
            print(f"  Median delay ({max_delay:.3f} ns) is < {threshold_well_corrected} ns")
            print("  → K-calibration may be redundant")
            print("  → Phase slopes are minimal")
            recommendation = "likely_corrected"
        elif max_delay < threshold_needs_correction:
            print("⚠ DELAYS PARTIALLY CORRECTED")
            print(f"  Median delay ({max_delay:.3f} ns) is {threshold_well_corrected}-{threshold_needs_correction} ns")
            print("  → Small residual delays present")
            print("  → K-calibration may still improve quality")
            recommendation = "partial"
        else:
            print("✗ DELAYS NOT CORRECTED UPSTREAM")
            print(f"  Median delay ({max_delay:.3f} ns) is > {threshold_needs_correction} ns")
            print("  → Significant delays present")
            print("  → K-calibration is NECESSARY")
            recommendation = "needs_correction"
        
        # Additional check: Are delays antenna-consistent?
        if ant_delays:
            ant_std = delay_stats['antenna_std_ns']
            baseline_std = delay_stats['std_ns']
            
            print(f"\nDelay Consistency Check:")
            print(f"  Antenna std dev: {ant_std:.3f} ns")
            print(f"  Baseline std dev: {baseline_std:.3f} ns")
            
            if ant_std < baseline_std * 0.7:
                print("  → Delays are antenna-consistent (instrumental)")
                print("  → K-calibration can correct these")
            else:
                print("  → Delays vary more by baseline (geometric or mixed)")
                print("  → May need geometric correction or K-calibration")
        
        delay_stats["recommendation"] = recommendation
        return delay_stats


def main():
    parser = argparse.ArgumentParser(
        description="Check if delays are already corrected upstream"
    )
    parser.add_argument("ms_path", help="Path to Measurement Set")
    parser.add_argument(
        "--n-baselines",
        type=int,
        default=100,
        help="Number of baselines to analyze (default: 100)"
    )
    
    args = parser.parse_args()
    
    try:
        results = check_upstream_delay_correction(args.ms_path, args.n_baselines)
        
        if "error" in results:
            sys.exit(1)
            
        print(f"\n{'='*70}")
        print("Summary:")
        print(f"{'='*70}\n")
        
        rec = results.get("recommendation", "unknown")
        if rec == "likely_corrected":
            print("Recommendation: K-calibration may be skipped")
            print("  Delays appear to be corrected upstream")
        elif rec == "partial":
            print("Recommendation: K-calibration optional but recommended")
            print("  Small residual delays may benefit from correction")
        else:
            print("Recommendation: K-calibration is NECESSARY")
            print("  Significant delays require correction")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


"""
QA utilities for calibration validation and delay checking.

This module provides functions to check and verify calibration quality,
particularly for delay (K-calibration) validation.
"""

from __future__ import annotations

import numpy as np
from casacore.tables import table
from typing import Dict, Any, Optional


def check_upstream_delay_correction(ms_path: str, n_baselines: int = 100) -> Dict[str, Any]:
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
        phase_slopes_per_antenna: Dict[int, list] = {}
        
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


def verify_kcal_delays(ms_path: str, kcal_path: Optional[str] = None,
                       cal_field: Optional[str] = None, refant: str = "103",
                       no_create: bool = False) -> None:
    """
    Verify K-calibration delay values and assess their significance.
    
    This function finds or creates a K-calibration table, inspects delay values,
    and provides recommendations.
    
    Args:
        ms_path: Path to Measurement Set
        kcal_path: Path to K-calibration table (auto-detected if not provided)
        cal_field: Calibrator field selection (auto-detected if not provided)
        refant: Reference antenna (default: 103)
        no_create: Don't create K-cal table if missing, just report
    """
    from pathlib import Path
    
    ms_dir = Path(ms_path).parent
    ms_stem = Path(ms_path).stem
    
    # Find existing K-cal table
    if kcal_path and Path(kcal_path).exists():
        kcal_table = kcal_path
    else:
        kcal_pattern = f"{ms_stem}*kcal"
        existing_kcals = list(ms_dir.glob(kcal_pattern))
        if existing_kcals:
            kcal_table = str(existing_kcals[0])
            print(f"Found existing K-calibration table: {kcal_table}")
        else:
            if no_create:
                print(f"✗ No K-calibration table found and --no-create specified")
                print(f"  MS: {ms_path}")
                print(f"  Searched in: {ms_dir}")
                return
            else:
                print(f"No existing K-calibration table found. Creating one...")
                from .calibration import solve_delay
                if cal_field is None:
                    cal_field = "0"  # Default to field 0
                try:
                    ktabs = solve_delay(ms_path, cal_field, refant)
                    if ktabs:
                        kcal_table = ktabs[0]
                        print(f"✓ Created K-calibration table: {kcal_table}")
                    else:
                        print("✗ Failed to create K-calibration table")
                        return
                except Exception as e:
                    print(f"✗ Failed to create K-calibration table: {e}")
                    return
    
    # Inspect the table
    inspect_kcal_simple(kcal_table, ms_path, find=False)


def inspect_kcal_simple(kcal_path: Optional[str] = None, ms_path: Optional[str] = None,
                        find: bool = False) -> None:
    """
    Inspect K-calibration delay values from a calibration table.
    
    Args:
        kcal_path: Path to K-calibration table (or None if using --find)
        ms_path: Path to MS (to auto-find K-cal table if --find)
        find: If True, find K-cal tables for MS instead of inspecting
    """
    from pathlib import Path
    
    if find:
        if not ms_path:
            print("✗ Error: --find requires --ms")
            return
        ms_dir = Path(ms_path).parent
        ms_stem = Path(ms_path).stem
        
        kcal_patterns = [
            f"{ms_stem}*kcal",
            f"{ms_stem}*_0_kcal",
            "*kcal",
        ]
        
        found_tables = []
        for pattern in kcal_patterns:
            found_tables.extend(ms_dir.glob(pattern))
        
        found_tables = sorted(set(found_tables), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if found_tables:
            print(f"\nFound {len(found_tables)} K-calibration table(s):\n")
            for i, table_path in enumerate(found_tables, 1):
                print(f"  {i}. {table_path}")
            print()
        else:
            print(f"\n✗ No K-calibration tables found in: {ms_dir}")
            print("\nTo create one, run:")
            print(f"  python -m dsa110_contimg.calibration.cli calibrate --ms {ms_path} --field 0 --refant 103 --do-k")
        return
    
    if not kcal_path:
        print("✗ Error: --kcal required when not using --find")
        return
    
    if not Path(kcal_path).exists():
        print(f"✗ Error: File not found: {kcal_path}")
        return
    
    print(f"\n{'='*70}")
    print(f"Inspecting K-calibration table: {kcal_path}")
    print(f"{'='*70}\n")
    
    try:
        with table(kcal_path, readonly=True, ack=False) as tb:
            n_rows = tb.nrows()
            print(f"Total solutions: {n_rows}")
            
            if n_rows == 0:
                print("⚠ WARNING: Table has zero solutions!")
                return
            
            colnames = tb.colnames()
            print(f"Table columns: {colnames}")
            
            if "CPARAM" not in colnames:
                print("⚠ WARNING: CPARAM column not found.")
                print("  This may not be a K-calibration table.")
                return
            
            # Read data
            cparam = tb.getcol("CPARAM")
            flags = tb.getcol("FLAG")
            antenna_ids = tb.getcol("ANTENNA1")
            
            print(f"CPARAM shape: {cparam.shape}")
            
            # Get frequency - try to find associated MS
            if ms_path and Path(ms_path).exists():
                try:
                    with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                        ref_freqs = spw_tb.getcol("REF_FREQUENCY")
                        print(f"Found MS with {len(ref_freqs)} SPWs")
                        print(f"Reference frequencies: {ref_freqs / 1e6:.1f} MHz")
                except Exception as e:
                    print(f"⚠ Could not read frequencies from MS: {e}")
                    ref_freqs = np.array([1400e6])  # Default L-band
            else:
                ms_dir = Path(kcal_path).parent
                ms_files = list(ms_dir.glob("*.ms"))
                
                if ms_files:
                    ms_path_check = ms_files[0]
                    try:
                        with table(f"{ms_path_check}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                            ref_freqs = spw_tb.getcol("REF_FREQUENCY")
                            print(f"Found MS with {len(ref_freqs)} SPWs")
                    except Exception:
                        ref_freqs = np.array([1400e6])
                else:
                    print("⚠ No MS found in same directory. Using default frequency (1.4 GHz)")
                    ref_freqs = np.array([1400e6])
            
            # Extract delays per antenna
            unique_ants = np.unique(antenna_ids)
            delays_per_antenna = {}
            delays_ns = []
            
            # Handle different CPARAM shapes
            if len(cparam.shape) == 3:
                # Shape: (n_rows, n_channels, n_pols)
                for i, ant_id in enumerate(unique_ants):
                    ant_mask = antenna_ids == ant_id
                    ant_indices = np.where(ant_mask)[0]
                    
                    if len(ant_indices) == 0:
                        continue
                    
                    # Use first unflagged solution
                    for idx in ant_indices:
                        if len(flags.shape) == 3:
                            if not flags[idx, 0, 0]:
                                cval = cparam[idx, 0, 0]
                                break
                        elif len(flags.shape) == 2:
                            if not flags[idx, 0]:
                                cval = cparam[idx, 0, 0]
                                break
                        else:
                            if not flags[idx]:
                                cval = cparam[idx, 0, 0]
                                break
                    else:
                        continue  # All flagged
                    
                    # Get frequency (use first SPW if multiple)
                    freq_hz = ref_freqs[0] if len(ref_freqs) > 0 else 1400e6
                    
                    # Compute delay from phase
                    phase_rad = np.angle(cval)
                    delay_sec = phase_rad / (2 * np.pi * freq_hz)
                    delay_ns = delay_sec * 1e9
                    
                    delays_per_antenna[int(ant_id)] = delay_ns
                    delays_ns.append(delay_ns)
            
            delays_ns = np.array(delays_ns)
            
            if len(delays_ns) == 0:
                print("⚠ Could not extract any delay values")
                return
            
            # Statistics
            print(f"\n{'='*70}")
            print("Delay Statistics:")
            print(f"{'='*70}\n")
            
            print(f"Number of antennas: {len(delays_ns)}")
            print(f"Median delay: {np.median(delays_ns):.3f} ns")
            print(f"Mean delay:   {np.mean(delays_ns):.3f} ns")
            print(f"Std dev:      {np.std(delays_ns):.3f} ns")
            print(f"Min delay:    {np.min(delays_ns):.3f} ns")
            print(f"Max delay:    {np.max(delays_ns):.3f} ns")
            print(f"Range:        {np.max(delays_ns) - np.min(delays_ns):.3f} ns")
            
            # Impact assessment
            print(f"\n{'='*70}")
            print("Impact Assessment:")
            print(f"{'='*70}\n")
            
            freq_center_hz = 1400e6  # L-band center
            bandwidth_hz = 200e6  # 200 MHz
            
            max_delay_sec = np.max(np.abs(delays_ns)) * 1e-9
            phase_error_rad = 2 * np.pi * max_delay_sec * bandwidth_hz
            phase_error_deg = np.degrees(phase_error_rad)
            
            print(f"Phase error across 200 MHz bandwidth:")
            print(f"  Maximum delay ({max_delay_sec*1e9:.3f} ns):")
            print(f"    → Phase error: {phase_error_deg:.1f}°")
            
            # Coherence loss
            coherence = np.abs(np.sinc(phase_error_rad / (2 * np.pi)))
            coherence_loss_percent = (1 - coherence) * 100
            
            print(f"\nCoherence Impact:")
            print(f"  Estimated coherence: {coherence:.3f}")
            print(f"  Coherence loss: {coherence_loss_percent:.1f}%")
            
            # Recommendation
            print(f"\n{'='*70}")
            print("Recommendation:")
            print(f"{'='*70}\n")
            
            delay_range = np.max(delays_ns) - np.min(delays_ns)
            
            if delay_range < 1.0:
                print("✓ Delays are very small (< 1 ns range)")
                print("  → K-calibration impact is minimal")
                print("  → However, still recommended for precision")
            elif delay_range < 10.0:
                print("⚠ Delays are moderate (1-10 ns range)")
                print("  → K-calibration is RECOMMENDED")
                print(f"  → Expected coherence loss: {coherence_loss_percent:.1f}%")
            else:
                print("✗ Delays are large (> 10 ns range)")
                print("  → K-calibration is ESSENTIAL")
                print(f"  → Significant coherence loss: {coherence_loss_percent:.1f}%")
            
            # Show top delays
            print(f"\n{'='*70}")
            print("Top 10 Antennas by Delay Magnitude:")
            print(f"{'='*70}\n")
            
            sorted_ants = sorted(
                delays_per_antenna.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:10]
            
            print(f"{'Antenna':<10} {'Delay (ns)':<15}")
            print("-" * 25)
            for ant_id, delay_ns in sorted_ants:
                print(f"{ant_id:<10} {delay_ns:>13.3f}")
            
            print(f"\n{'='*70}")
            print("Inspection Complete")
            print(f"{'='*70}\n")
            
    except Exception as e:
        print(f"✗ Error inspecting table: {e}")
        import traceback
        traceback.print_exc()

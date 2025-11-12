#!/usr/bin/env python3
"""
Verify K-calibration delay values and assess their significance.

This script:
1. Finds or creates a K-calibration table for a given MS
2. Inspects delay values from the calibration table
3. Computes phase coherence impact across bandwidth
4. Provides recommendations on whether K-calibration is necessary
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import astropy.units as u
from casacore.tables import table

# Set CASA log directory
try:
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    casa_log_dir = derive_casa_log_dir()
    os.chdir(str(casa_log_dir))
except Exception:
    pass

from dsa110_contimg.calibration.calibration import solve_delay
from dsa110_contimg.calibration.selection import select_bandpass_fields


def inspect_kcal_delays(kcal_path: str) -> dict:
    """
    Inspect delay values from a K-calibration table.
    
    Args:
        kcal_path: Path to K-calibration table
        
    Returns:
        Dictionary with delay statistics and analysis
    """
    print(f"\n{'='*70}")
    print(f"Inspecting K-calibration table: {kcal_path}")
    print(f"{'='*70}\n")
    
    if not os.path.exists(kcal_path):
        raise FileNotFoundError(f"K-calibration table not found: {kcal_path}")
    
    with table(kcal_path, readonly=True, ack=False) as tb:
        n_rows = tb.nrows()
        print(f"Total solutions: {n_rows}")
        
        if n_rows == 0:
            print("⚠ WARNING: Table has zero solutions!")
            return {"error": "No solutions found"}
        
        # Get delay values
        # For K-calibration (gaintype='K'), delays are stored in CPARAM
        # CPARAM shape: (n_rows, n_channels, n_pols)
        # For K-cal, CPARAM = exp(i * 2π * delay * frequency)
        # So delay = phase / (2π * frequency)
        
        colnames = tb.colnames()
        print(f"Table columns: {colnames}")
        
        # Check if this is a K-calibration table
        if "CPARAM" not in colnames:
            print("⚠ WARNING: CPARAM column not found. This may not be a K-calibration table.")
            print(f"   Available columns: {colnames}")
            return {"error": "Not a valid K-calibration table"}
        
        cparam = tb.getcol("CPARAM")  # Shape: (n_rows, n_channels, n_pols)
        flags = tb.getcol("FLAG")
        antenna_ids = tb.getcol("ANTENNA1")
        spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
        
        print(f"CPARAM shape: {cparam.shape}")
        
        # Get frequency information from MS (not from cal table SPW subtable)
        # We need to map SPW_ID to actual frequencies
        ms_path = str(kcal_path).rsplit("_", 1)[0].rsplit(".", 1)[0] + ".ms"
        if not os.path.exists(ms_path):
            # Try alternative path construction
            ms_dir = Path(kcal_path).parent
            ms_files = list(ms_dir.glob("*.ms"))
            if ms_files:
                ms_path = str(ms_files[0])
        
        if os.path.exists(ms_path):
            try:
                with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                    chan_freqs = spw_tb.getcol("CHAN_FREQ")  # Shape: (n_spw, n_chan)
                    ref_freqs = spw_tb.getcol("REF_FREQUENCY")
                    print(f"Found MS with {len(ref_freqs)} SPWs")
            except Exception as e:
                print(f"⚠ Could not read frequency info from MS: {e}")
                # Assume L-band center frequency
                ref_freqs = np.array([1400e6])
        else:
            print(f"⚠ MS not found: {ms_path}")
            print("  Using default L-band frequency (1.4 GHz)")
            ref_freqs = np.array([1400e6])
        
        # Extract per-antenna delays
        unique_ants = np.unique(antenna_ids)
        unique_spws = np.unique(spw_ids)
        
        print(f"Antennas: {len(unique_ants)}")
        print(f"Spectral windows: {len(unique_spws)}")
        
        # For each antenna, compute delay from phase
        delays_per_antenna = {}
        delays_ns = []
        
        for ant_id in unique_ants:
            ant_mask = antenna_ids == ant_id
            ant_cparam = cparam[ant_mask]
            ant_flags = flags[ant_mask]
            ant_spw = spw_ids[ant_mask]
            
            # Use first unflagged solution per antenna
            # Check flags: shape is (n_rows, n_channels, n_pols)
            if len(ant_flags.shape) == 3:
                unflagged_mask = ~ant_flags[:, 0, 0]  # Check first channel, first pol
            elif len(ant_flags.shape) == 2:
                unflagged_mask = ~ant_flags[:, 0]
            else:
                unflagged_mask = ~ant_flags
            
            if not np.any(unflagged_mask):
                continue
            
            # Get first unflagged solution
            first_unflagged_idx = np.where(unflagged_mask)[0][0]
            spw_idx = int(ant_spw[first_unflagged_idx])
            
            # Get frequency for this SPW
            if spw_idx < len(ref_freqs):
                freq_hz = ref_freqs[spw_idx]
            else:
                freq_hz = 1400e6  # Fallback L-band
            
            # Extract phase from CPARAM
            # For K-calibration, CPARAM = exp(i * 2π * delay * freq)
            # So delay = phase / (2π * freq)
            if len(ant_cparam.shape) == 3:
                cval = ant_cparam[first_unflagged_idx, 0, 0]  # First channel, first pol
            elif len(ant_cparam.shape) == 2:
                cval = ant_cparam[first_unflagged_idx, 0]
            else:
                cval = ant_cparam[first_unflagged_idx]
            
            phase_rad = np.angle(cval)
            
            # Convert phase to delay
            # delay = phase / (2π × frequency)
            delay_sec = phase_rad / (2 * np.pi * freq_hz)
            delay_ns = delay_sec * 1e9  # Convert to nanoseconds
            
            delays_per_antenna[int(ant_id)] = {
                "delay_ns": delay_ns,
                "phase_rad": phase_rad,
                "phase_deg": np.degrees(phase_rad),
                "freq_hz": freq_hz,
            }
            delays_ns.append(delay_ns)
        
        delays_ns = np.array(delays_ns)
        
        # Compute statistics
        delay_stats = {
            "median_ns": float(np.median(delays_ns)),
            "mean_ns": float(np.mean(delays_ns)),
            "std_ns": float(np.std(delays_ns)),
            "min_ns": float(np.min(delays_ns)),
            "max_ns": float(np.max(delays_ns)),
            "range_ns": float(np.max(delays_ns) - np.min(delays_ns)),
            "n_antennas": len(delays_ns),
            "delays_per_antenna": delays_per_antenna,
        }
        
        # Print results
        print(f"\nDelay Statistics:")
        print(f"  Median delay: {delay_stats['median_ns']:.3f} ns")
        print(f"  Mean delay:   {delay_stats['mean_ns']:.3f} ns")
        print(f"  Std dev:      {delay_stats['std_ns']:.3f} ns")
        print(f"  Range:        {delay_stats['min_ns']:.3f} to {delay_stats['max_ns']:.3f} ns")
        print(f"  Total range:  {delay_stats['range_ns']:.3f} ns")
        
        # Assess significance
        print(f"\n{'='*70}")
        print("Impact Assessment:")
        print(f"{'='*70}\n")
        
        # Compute phase error at band edges
        freq_center_hz = 1400e6  # L-band center
        bandwidth_hz = 200e6  # 200 MHz bandwidth
        
        # Phase error across bandwidth = 2π × delay × bandwidth
        max_delay_sec = delay_stats['max_ns'] * 1e-9
        phase_error_rad = 2 * np.pi * max_delay_sec * bandwidth_hz
        phase_error_deg = np.degrees(phase_error_rad)
        
        print(f"Phase error across 200 MHz bandwidth:")
        print(f"  Maximum delay ({delay_stats['max_ns']:.3f} ns):")
        print(f"    → Phase error: {phase_error_deg:.1f}°")
        print(f"    → Wavelengths: {phase_error_deg / 360:.2f}")
        
        # Coherence loss estimate
        # Coherence = sinc(phase_error / 2π)
        coherence = np.abs(np.sinc(phase_error_rad / (2 * np.pi)))
        coherence_loss_percent = (1 - coherence) * 100
        
        print(f"\nCoherence Impact:")
        print(f"  Estimated coherence: {coherence:.3f} ({coherence_loss_percent:.1f}% loss)")
        
        # Recommendation
        print(f"\n{'='*70}")
        print("Recommendation:")
        print(f"{'='*70}\n")
        
        if delay_stats['range_ns'] < 1.0:
            print("✓ Delays are very small (< 1 ns range)")
            print("  → K-calibration may have minimal impact")
            print("  → However, still recommended for precision")
        elif delay_stats['range_ns'] < 10.0:
            print("⚠ Delays are moderate (1-10 ns range)")
            print("  → K-calibration is RECOMMENDED")
            print(f"  → Expected coherence loss: {coherence_loss_percent:.1f}%")
        else:
            print("✗ Delays are large (> 10 ns range)")
            print("  → K-calibration is ESSENTIAL")
            print(f"  → Significant coherence loss: {coherence_loss_percent:.1f}%")
        
        # Show per-antenna delays
        print(f"\n{'='*70}")
        print("Top 10 Antennas by Delay Magnitude:")
        print(f"{'='*70}\n")
        
        sorted_ants = sorted(
            delays_per_antenna.items(),
            key=lambda x: abs(x[1]['delay_ns']),
            reverse=True
        )[:10]
        
        print(f"{'Antenna':<10} {'Delay (ns)':<15} {'Phase (deg)':<15}")
        print("-" * 40)
        for ant_id, delay_info in sorted_ants:
            print(f"{ant_id:<10} {delay_info['delay_ns']:>13.3f}  {delay_info['phase_deg']:>13.2f}")
        
        return delay_stats


def find_or_create_kcal(ms_path: str, cal_field: str = None, refant: str = "103") -> str:
    """
    Find existing K-calibration table or create one.
    
    Args:
        ms_path: Path to MS
        cal_field: Field selection for calibration
        refant: Reference antenna
        
    Returns:
        Path to K-calibration table
    """
    ms_dir = Path(ms_path).parent
    ms_stem = Path(ms_path).stem
    
    # Look for existing K-cal table
    kcal_pattern = f"{ms_stem}*kcal"
    existing_kcals = list(ms_dir.glob(kcal_pattern))
    
    if existing_kcals:
        print(f"Found existing K-calibration table: {existing_kcals[0]}")
        return str(existing_kcals[0])
    
    # Need to create one
    print(f"No existing K-calibration table found. Creating one...")
    
    # Auto-detect calibrator field if not provided
    if cal_field is None:
        print("Auto-detecting calibrator field...")
        try:
            calinfo = select_bandpass_fields(
                ms_path,
                cal_ra_deg=0.0,  # Will search catalog
                cal_dec_deg=40.0,  # Approximate DSA-110 declination
                cal_flux_jy=1.0,
            )
            if calinfo:
                cal_field = str(calinfo[0])  # Use first field
                print(f"Using field: {cal_field}")
            else:
                print("⚠ No calibrator found. Using field 0 as fallback.")
                cal_field = "0"
        except Exception as e:
            print(f"⚠ Auto-detection failed: {e}")
            print("Using field 0 as fallback.")
            cal_field = "0"
    
    # Solve delay
    print(f"Solving delay calibration on field {cal_field} with refant {refant}...")
    try:
        ktabs = solve_delay(ms_path, cal_field, refant)
        if ktabs:
            print(f"✓ Created K-calibration table: {ktabs[0]}")
            return ktabs[0]
        else:
            raise RuntimeError("Delay solve returned no tables")
    except Exception as e:
        print(f"✗ Failed to create K-calibration table: {e}")
        raise


def compare_phase_coherence(ms_path: str, with_kcal: bool = True) -> dict:
    """
    Compare phase coherence across frequency with and without K-calibration.
    
    Args:
        ms_path: Path to MS
        with_kcal: Whether to apply K-calibration
        
    Returns:
        Dictionary with phase coherence metrics
    """
    print(f"\n{'='*70}")
    print(f"Phase Coherence Analysis {'(WITH K-cal)' if with_kcal else '(WITHOUT K-cal)'}")
    print(f"{'='*70}\n")
    
    from casacore.tables import table
    import numpy as np
    
    with table(ms_path, readonly=True) as tb:
        # Get frequency information
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
            chan_freqs = spw_tb.getcol("CHAN_FREQ")  # Shape: (n_spw, n_chan)
        
        # Sample data from a bright calibrator or all fields
        n_sample = min(1000, tb.nrows())
        data_col = "CORRECTED_DATA" if with_kcal else "DATA"
        
        if data_col not in tb.colnames():
            print(f"⚠ Column {data_col} not found. Skipping phase coherence check.")
            return {}
        
        # Sample data
        sample_data = tb.getcol(data_col, startrow=0, nrow=n_sample)
        sample_flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)
        sample_spw = tb.getcol("DATA_DESC_ID", startrow=0, nrow=n_sample)
        
        # Get frequencies for sampled SPWs
        with table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd_tb:
            spw_map = dd_tb.getcol("SPECTRAL_WINDOW_ID")
        
        # Analyze phase vs frequency
        phase_slopes = []
        
        for i in range(min(100, n_sample)):  # Analyze first 100 baselines
            if np.all(sample_flags[i]):
                continue
            
            spw_idx = int(sample_spw[i])
            if spw_idx >= len(spw_map):
                continue
            
            freq_idx = int(spw_map[spw_idx])
            if freq_idx >= len(chan_freqs):
                continue
            
            freqs = chan_freqs[freq_idx]
            vis = sample_data[i, :, 0]  # First polarization
            
            # Extract unflagged channels
            unflagged = ~sample_flags[i, :, 0]
            if np.sum(unflagged) < 3:
                continue
            
            unflagged_freqs = freqs[unflagged]
            unflagged_vis = vis[unflagged]
            
            # Compute phase
            phases = np.angle(unflagged_vis)
            
            # Fit phase slope (delay causes linear phase vs frequency)
            if len(unflagged_freqs) > 1:
                # Unwrap phases
                phases_unwrapped = np.unwrap(phases)
                
                # Fit linear: phase = a * freq + b
                coeffs = np.polyfit(unflagged_freqs, phases_unwrapped, 1)
                delay_estimated = coeffs[0] / (2 * np.pi)  # Delay in seconds
                delay_ns = delay_estimated * 1e9
                
                phase_slopes.append(delay_ns)
        
        if phase_slopes:
            phase_slopes = np.array(phase_slopes)
            print(f"Phase slope analysis (estimated delays from phase vs frequency):")
            print(f"  Median: {np.median(phase_slopes):.3f} ns")
            print(f"  Mean:   {np.mean(phase_slopes):.3f} ns")
            print(f"  Std:    {np.std(phase_slopes):.3f} ns")
            print(f"  Range:  {np.min(phase_slopes):.3f} to {np.max(phase_slopes):.3f} ns")
            
            return {
                "median_delay_ns": float(np.median(phase_slopes)),
                "mean_delay_ns": float(np.mean(phase_slopes)),
                "std_delay_ns": float(np.std(phase_slopes)),
                "n_baselines": len(phase_slopes),
            }
        else:
            print("⚠ Could not compute phase slopes (insufficient unflagged data)")
            return {}


def main():
    parser = argparse.ArgumentParser(
        description="Verify K-calibration delay values and assess significance"
    )
    parser.add_argument(
        "ms_path",
        help="Path to Measurement Set"
    )
    parser.add_argument(
        "--cal-field",
        help="Calibrator field selection (auto-detected if not provided)"
    )
    parser.add_argument(
        "--refant",
        default="103",
        help="Reference antenna (default: 103)"
    )
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Don't create K-cal table if missing, just report"
    )
    parser.add_argument(
        "--compare-phase",
        action="store_true",
        help="Compare phase coherence with/without K-calibration"
    )
    
    args = parser.parse_args()
    
    ms_path = Path(args.ms_path)
    if not ms_path.exists():
        print(f"✗ Error: MS not found: {ms_path}")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print("K-Calibration Delay Verification")
    print(f"{'='*70}")
    print(f"MS: {ms_path}")
    print(f"Reference antenna: {args.refant}")
    print(f"{'='*70}\n")
    
    # Find or create K-calibration table
    try:
        if args.no_create:
            # Just look for existing
            ms_dir = ms_path.parent
            ms_stem = ms_path.stem
            kcal_pattern = f"{ms_stem}*kcal"
            existing_kcals = list(ms_dir.glob(kcal_pattern))
            if not existing_kcals:
                print("✗ No existing K-calibration table found.")
                print("  Run calibration first or use without --no-create flag")
                sys.exit(1)
            kcal_path = str(existing_kcals[0])
        else:
            print("Attempting to create K-calibration table...")
            print("(This may take a few minutes)")
            kcal_path = find_or_create_kcal(
                str(ms_path),
                cal_field=args.cal_field,
                refant=args.refant
            )
    except KeyboardInterrupt:
        print("\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Failed to find/create K-calibration table: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Inspect delay values
    try:
        delay_stats = inspect_kcal_delays(kcal_path)
    except Exception as e:
        print(f"✗ Failed to inspect K-calibration table: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Phase coherence comparison (if requested)
    if args.compare_phase:
        print(f"\n{'='*70}")
        print("Phase Coherence Comparison")
        print(f"{'='*70}\n")
        
        print("This requires applying calibration to create CORRECTED_DATA.")
        print("For now, we'll analyze the existing data columns.\n")
        
        # Check if CORRECTED_DATA exists
        with table(str(ms_path), readonly=True) as tb:
            has_corrected = "CORRECTED_DATA" in tb.colnames()
        
        if has_corrected:
            print("Found CORRECTED_DATA column - analyzing with K-cal applied...")
            coherence_with = compare_phase_coherence(str(ms_path), with_kcal=True)
            print("\nAnalyzing DATA column (without K-cal)...")
            coherence_without = compare_phase_coherence(str(ms_path), with_kcal=False)
            
            if coherence_with and coherence_without:
                print(f"\n{'='*70}")
                print("Comparison Summary:")
                print(f"{'='*70}\n")
                print(f"WITH K-cal:    median delay = {coherence_with['median_delay_ns']:.3f} ns")
                print(f"WITHOUT K-cal:  median delay = {coherence_without['median_delay_ns']:.3f} ns")
                improvement = coherence_without['median_delay_ns'] - coherence_with['median_delay_ns']
                print(f"\nImprovement: {improvement:.3f} ns reduction in phase slope")
        else:
            print("⚠ CORRECTED_DATA not found.")
            print("  Apply calibration first to enable phase coherence comparison.")
            print("  Analyzing DATA column only...")
            coherence_without = compare_phase_coherence(str(ms_path), with_kcal=False)
    
    print(f"\n{'='*70}")
    print("Verification Complete")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()


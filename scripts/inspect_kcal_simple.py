#!/usr/bin/env python3
"""
Simple script to inspect K-calibration delay values from existing calibration tables.

Usage:
    python scripts/inspect_kcal_simple.py <kcal_table_path>
    python scripts/inspect_kcal_simple.py --find <ms_path>
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from casacore.tables import table


def inspect_kcal(kcal_path: str):
    """Inspect delay values from a K-calibration table."""
    
    print(f"\n{'='*70}")
    print(f"Inspecting K-calibration table: {kcal_path}")
    print(f"{'='*70}\n")
    
    if not Path(kcal_path).exists():
        print(f"✗ Error: File not found: {kcal_path}")
        return
    
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
            ms_dir = Path(kcal_path).parent
            ms_files = list(ms_dir.glob("*.ms"))
            
            if ms_files:
                ms_path = ms_files[0]
                try:
                    with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                        ref_freqs = spw_tb.getcol("REF_FREQUENCY")
                        print(f"Found MS with {len(ref_freqs)} SPWs")
                        print(f"Reference frequencies: {ref_freqs / 1e6:.1f} MHz")
                except Exception as e:
                    print(f"⚠ Could not read frequencies from MS: {e}")
                    ref_freqs = np.array([1400e6])  # Default L-band
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


def find_kcal_tables(ms_path: str):
    """Find K-calibration tables associated with an MS."""
    
    ms_dir = Path(ms_path).parent
    ms_stem = Path(ms_path).stem
    
    # Look for K-cal tables
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
        for i, kcal_path in enumerate(found_tables, 1):
            print(f"  {i}. {kcal_path}")
        print()
        return found_tables[0]  # Return most recent
    else:
        print(f"\n✗ No K-calibration tables found in: {ms_dir}")
        print("\nTo create one, run:")
        print(f"  python -m dsa110_contimg.calibration.cli calibrate --ms {ms_path} --field 0 --refant 103")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Inspect K-calibration delay values"
    )
    parser.add_argument(
        "kcal_path",
        nargs="?",
        help="Path to K-calibration table (or MS path if --find is used)"
    )
    parser.add_argument(
        "--find",
        action="store_true",
        help="Find K-calibration tables for the given MS path"
    )
    
    args = parser.parse_args()
    
    if not args.kcal_path:
        parser.print_help()
        sys.exit(1)
    
    if args.find:
        kcal_path = find_kcal_tables(args.kcal_path)
        if not kcal_path:
            sys.exit(1)
        inspect_kcal(str(kcal_path))
    else:
        inspect_kcal(args.kcal_path)


if __name__ == "__main__":
    main()


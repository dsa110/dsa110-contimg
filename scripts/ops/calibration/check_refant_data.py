#!/opt/miniforge/envs/casa6/bin/python
"""
Check if reference antenna has data in a Measurement Set.

Usage:
    python scripts/check_refant_data.py --ms /path/to/ms.ms --refant 103
"""

import argparse
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import numpy as np
from casacore.tables import table


def check_refant_data(ms_path, refant):
    """
    Check if reference antenna has data in MS.
    
    Args:
        ms_path: Path to Measurement Set
        refant: Reference antenna ID
    
    Returns:
        Dictionary with statistics
    """
    refant = int(refant)
    stats = {
        "refant": refant,
        "exists_in_antenna_table": False,
        "n_baselines": 0,
        "n_rows": 0,
        "fraction_flagged": 0.0,
        "n_unflagged": 0,
        "median_amplitude": 0.0,
        "has_data": False,
        "issues": [],
    }
    
    print(f"Checking reference antenna {refant} in {ms_path}...")
    
    # Check ANTENNA table
    try:
        with table(f"{ms_path}::ANTENNA", readonly=True, ack=False) as ant_tb:
            n_antennas = ant_tb.nrows()
            # In CASA MS, antenna IDs are implicit (row indices 0 to n_antennas-1)
            # But actual antenna IDs in the data may be different
            if refant < n_antennas:
                ant_name = ant_tb.getcol("NAME")[refant] if "NAME" in ant_tb.colnames() else f"Antenna{refant}"
                print(f":check: Antenna {refant} ({ant_name}) exists in ANTENNA table (row {refant})")
                stats["exists_in_antenna_table"] = True
            else:
                stats["issues"].append(f"Antenna {refant} not found in ANTENNA table (only {n_antennas} antennas)")
                print(f":cross: Antenna {refant} NOT found in ANTENNA table")
                print(f"  ANTENNA table has {n_antennas} rows (indices 0-{n_antennas-1})")
                # Note: Antenna IDs in data may not match row indices
    except Exception as e:
        stats["issues"].append(f"Error reading ANTENNA table: {e}")
        print(f":cross: Error reading ANTENNA table: {e}")
        return stats
    
    # Check main table for baselines involving refant
    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            n_rows = tb.nrows()
            if n_rows == 0:
                stats["issues"].append("MS has zero rows")
                print(f":cross: MS has zero rows")
                return stats
            
            # Get antenna columns
            ant1 = tb.getcol("ANTENNA1")
            ant2 = tb.getcol("ANTENNA2")
            
            # Find rows where refant appears
            refant_rows = (ant1 == refant) | (ant2 == refant)
            n_refant_rows = np.sum(refant_rows)
            stats["n_rows"] = int(n_refant_rows)
            
            if n_refant_rows == 0:
                stats["issues"].append(f"No baselines involving antenna {refant}")
                print(f":cross: No baselines involving antenna {refant}")
                print(f"  Total rows in MS: {n_rows}")
                print(f"  Antenna range: {ant1.min()}-{ant1.max()}")
                return stats
            
            print(f":check: Found {n_refant_rows:,} rows involving antenna {refant} (out of {n_rows:,} total)")
            
            # Count unique baselines
            refant_ant1 = ant1[refant_rows]
            refant_ant2 = ant2[refant_rows]
            baselines = set(zip(refant_ant1, refant_ant2))
            stats["n_baselines"] = len(baselines)
            print(f":check: Antenna {refant} appears in {len(baselines)} unique baselines")
            
            # Check flagging
            flags = tb.getcol("FLAG")
            refant_flags = flags[refant_rows]
            
            # Count flagged points
            total_points = refant_flags.size
            flagged_points = np.sum(refant_flags)
            stats["fraction_flagged"] = float(flagged_points / total_points) if total_points > 0 else 0.0
            stats["n_unflagged"] = int(total_points - flagged_points)
            
            print(f"  Flagging: {stats['fraction_flagged']:.1%} flagged ({flagged_points:,}/{total_points:,} points)")
            print(f"  Unflagged: {stats['n_unflagged']:,} points available")
            
            if stats["fraction_flagged"] > 0.9:
                stats["issues"].append(f"Very high flagging fraction: {stats['fraction_flagged']:.1%}")
                print(f":warning: WARNING: Very high flagging fraction ({stats['fraction_flagged']:.1%})")
            
            # Check amplitudes in unflagged data
            if stats["n_unflagged"] > 0:
                data = tb.getcol("DATA")
                refant_data = data[refant_rows]
                unflagged_data = refant_data[~refant_flags]
                
                if len(unflagged_data) > 0:
                    amps = np.abs(unflagged_data)
                    stats["median_amplitude"] = float(np.median(amps))
                    stats["has_data"] = True
                    
                    print(f"  Median amplitude (unflagged): {stats['median_amplitude']:.3e}")
                    print(f"  Amplitude range: {np.min(amps):.3e} - {np.max(amps):.3e}")
                    
                    if stats["median_amplitude"] < 1e-5:
                        stats["issues"].append(f"Very low median amplitude: {stats['median_amplitude']:.3e}")
                        print(f":warning: WARNING: Very low median amplitude")
                else:
                    stats["issues"].append("No unflagged data points")
                    print(f":cross: No unflagged data points")
            else:
                stats["issues"].append("All data involving refant is flagged")
                print(f":cross: All data involving antenna {refant} is flagged")
    
    except Exception as e:
        stats["issues"].append(f"Error reading main table: {e}")
        print(f":cross: Error reading main table: {e}")
        import traceback
        traceback.print_exc()
        return stats
    
    # Summary
    if stats["has_data"] and stats["fraction_flagged"] < 0.9:
        print(f"\n:check: Reference antenna {refant} has usable data")
        print(f"  {stats['n_unflagged']:,} unflagged points available")
        print(f"  {stats['n_baselines']} baselines involving refant")
    else:
        print(f"\n:cross: Reference antenna {refant} has issues:")
        for issue in stats["issues"]:
            print(f"  - {issue}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Check reference antenna data quality")
    parser.add_argument("--ms", required=True, help="Path to Measurement Set")
    parser.add_argument("--refant", type=int, default=103, help="Reference antenna ID (default: 103)")
    
    args = parser.parse_args()
    
    if not Path(args.ms).exists():
        print(f"Error: MS not found: {args.ms}")
        return 1
    
    stats = check_refant_data(args.ms, args.refant)
    
    if stats["issues"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


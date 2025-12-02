#!/opt/miniforge/envs/casa6/bin/python
"""
Check MS phasing and model alignment for calibrator.

Usage:
    python scripts/check_ms_phasing.py --ms /path/to/ms.ms --calibrator 0834+555
"""

import argparse
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from casacore.tables import table


def check_ms_phasing(ms_path, calibrator_name=None, calibrator_ra=None, calibrator_dec=None):
    """
    Check MS phasing and model alignment.
    
    Args:
        ms_path: Path to Measurement Set
        calibrator_name: Name of calibrator (optional)
        calibrator_ra: Calibrator RA in degrees (optional)
        calibrator_dec: Calibrator Dec in degrees (optional)
    """
    print(f"Checking MS phasing for {ms_path}...")
    print("=" * 70)
    
    # Read MS phase center
    try:
        with table(f"{ms_path}::FIELD", readonly=True, ack=False) as field_tb:
            if field_tb.nrows() == 0:
                print(":cross: FIELD table has no rows")
                return False
            
            field_ra = field_tb.getcol("REFERENCE_DIR")[0][0][0] * 180.0 / np.pi  # Convert to degrees
            field_dec = field_tb.getcol("REFERENCE_DIR")[0][0][1] * 180.0 / np.pi  # Convert to degrees
            field_name = field_tb.getcol("NAME")[0] if "NAME" in field_tb.colnames() else "Field_0"
            
            print(f"MS Phase Center:")
            print(f"  Field: {field_name}")
            print(f"  RA: {field_ra:.6f} deg ({field_ra*15:.4f} hours)")
            print(f"  Dec: {field_dec:.6f} deg")
    except Exception as e:
        print(f":cross: Error reading FIELD table: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # If calibrator coordinates provided, check separation
    if calibrator_ra is not None and calibrator_dec is not None:
        calibrator_coord = SkyCoord(ra=calibrator_ra*u.deg, dec=calibrator_dec*u.deg, frame='icrs')
        ms_coord = SkyCoord(ra=field_ra*u.deg, dec=field_dec*u.deg, frame='icrs')
        separation = ms_coord.separation(calibrator_coord)
        
        print(f"\nCalibrator Position:")
        print(f"  Name: {calibrator_name or 'Unknown'}")
        print(f"  RA: {calibrator_ra:.6f} deg ({calibrator_ra*15:.4f} hours)")
        print(f"  Dec: {calibrator_dec:.6f} deg")
        
        print(f"\nSeparation:")
        print(f"  Angular: {separation.to(u.arcmin):.4f} ({separation.to(u.deg):.6f} deg)")
        print(f"  Primary beam FWHM @ 1.4 GHz: ~2.0 deg")
        print(f"  Separation / FWHM: {separation.to(u.deg).value / 2.0:.3f}")
        
        # Check if separation is reasonable
        if separation.to(u.arcmin).value < 5.0:
            print(f"  :check: Separation is very small (<5 arcmin) - good phasing")
        elif separation.to(u.arcmin).value < 30.0:
            print(f"  :warning: Separation is moderate ({separation.to(u.arcmin):.2f}) - may cause phase decorrelation")
        else:
            print(f"  :cross: Separation is large ({separation.to(u.arcmin):.2f}) - likely causing phase decorrelation!")
    
    # Check MODEL_DATA phase structure
    print(f"\nMODEL_DATA Phase Structure:")
    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            if "MODEL_DATA" not in tb.colnames():
                print("  :cross: MODEL_DATA column not present")
                return False
            
            # Sample MODEL_DATA
            n_rows = tb.nrows()
            sample_size = min(1000, n_rows)
            indices = np.linspace(0, n_rows - 1, sample_size, dtype=int)
            
            model_data = tb.getcol("MODEL_DATA", startrow=indices[0], nrow=len(indices))
            flags = tb.getcol("FLAG", startrow=indices[0], nrow=len(indices))
            
            # Check for unflagged MODEL_DATA
            unflagged_model = model_data[~flags]
            
            if len(unflagged_model) == 0:
                print("  :cross: No unflagged MODEL_DATA")
                return False
            
            # Check MODEL_DATA phase structure
            model_phases = np.angle(unflagged_model)
            model_amps = np.abs(unflagged_model)
            
            print(f"  Sample size: {len(unflagged_model)} points")
            print(f"  Median amplitude: {np.median(model_amps):.6f} Jy")
            print(f"  Amplitude range: {np.min(model_amps):.6e} - {np.max(model_amps):.6e} Jy")
            
            # Check phase scatter
            phase_scatter = np.std(model_phases)
            print(f"  Phase scatter: {np.degrees(phase_scatter):.2f} deg")
            
            if phase_scatter < 0.1:  # < 5.7 deg
                print(f"  :check: Low phase scatter - model is well-phased")
            elif phase_scatter < 0.5:  # < 28.6 deg
                print(f"  :warning: Moderate phase scatter - some phase variation")
            else:
                print(f"  :cross: High phase scatter - model phase structure may be incorrect")
            
            # Check for phase wrapping or rapid variation
            phase_diff = np.diff(np.sort(model_phases))
            large_jumps = np.sum(np.abs(phase_diff) > np.pi)
            if large_jumps > len(phase_diff) * 0.1:
                print(f"  :warning: Many phase jumps detected ({large_jumps}/{len(phase_diff)}) - possible phase wrapping")
            
    except Exception as e:
        print(f"  :cross: Error reading MODEL_DATA: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check DATA vs MODEL_DATA phase alignment
    print(f"\nDATA vs MODEL_DATA Phase Alignment:")
    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            if "DATA" not in tb.colnames():
                print("  :cross: DATA column not present")
                return False
            
            # Sample DATA and MODEL_DATA
            n_rows = tb.nrows()
            sample_size = min(1000, n_rows)
            indices = np.linspace(0, n_rows - 1, sample_size, dtype=int)
            
            data = tb.getcol("DATA", startrow=indices[0], nrow=len(indices))
            model_data = tb.getcol("MODEL_DATA", startrow=indices[0], nrow=len(indices))
            flags = tb.getcol("FLAG", startrow=indices[0], nrow=len(indices))
            
            # Check for unflagged data
            unflagged_mask = ~flags
            unflagged_data = data[unflagged_mask]
            unflagged_model = model_data[unflagged_mask]
            
            if len(unflagged_data) == 0:
                print("  :cross: No unflagged DATA")
                return False
            
            # Compute phase difference
            data_phases = np.angle(unflagged_data)
            model_phases = np.angle(unflagged_model)
            phase_diff = data_phases - model_phases
            
            # Normalize phase difference to [-pi, pi]
            phase_diff = np.angle(np.exp(1j * phase_diff))
            
            phase_diff_deg = np.degrees(phase_diff)
            phase_diff_scatter = np.std(phase_diff_deg)
            
            print(f"  Sample size: {len(unflagged_data)} points")
            print(f"  Mean phase difference: {np.mean(phase_diff_deg):.2f} deg")
            print(f"  Phase difference scatter: {phase_diff_scatter:.2f} deg")
            
            if phase_diff_scatter < 30.0:
                print(f"  :check: Low phase difference scatter - DATA and MODEL_DATA are well-aligned")
            elif phase_diff_scatter < 60.0:
                print(f"  :warning: Moderate phase difference scatter - some misalignment")
            else:
                print(f"  :cross: High phase difference scatter - DATA and MODEL_DATA are misaligned!")
                print(f"     This could cause low SNR in calibration")
            
            # Check amplitude ratio
            data_amps = np.abs(unflagged_data)
            model_amps = np.abs(unflagged_model)
            
            # Only check where model is non-zero
            non_zero_model = model_amps > 1e-10
            if np.sum(non_zero_model) > 0:
                amp_ratio = data_amps[non_zero_model] / model_amps[non_zero_model]
                median_amp_ratio = np.median(amp_ratio)
                
                print(f"  Median amplitude ratio (DATA/MODEL): {median_amp_ratio:.4f}")
                
                if 0.5 < median_amp_ratio < 2.0:
                    print(f"  :check: Reasonable amplitude ratio")
                elif median_amp_ratio < 0.1:
                    print(f"  :cross: Very low amplitude ratio - DATA much weaker than MODEL")
                    print(f"     This indicates decorrelation or data quality issues")
                else:
                    print(f"  :warning: Unusual amplitude ratio - may indicate calibration or model issues")
    
    except Exception as e:
        print(f"  :cross: Error comparing DATA vs MODEL_DATA: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("  Check separation between MS phase center and calibrator position")
    print("  Check MODEL_DATA phase structure consistency")
    print("  Check DATA vs MODEL_DATA phase alignment")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Check MS phasing and model alignment")
    parser.add_argument("--ms", required=True, help="Path to Measurement Set")
    parser.add_argument("--calibrator", help="Calibrator name (e.g., 0834+555)")
    parser.add_argument("--cal-ra", type=float, help="Calibrator RA in degrees")
    parser.add_argument("--cal-dec", type=float, help="Calibrator Dec in degrees")
    
    args = parser.parse_args()
    
    if not Path(args.ms).exists():
        print(f"Error: MS not found: {args.ms}")
        return 1
    
    # If calibrator name provided, try to look up coordinates
    if args.calibrator and not args.cal_ra:
        # Try to load calibrator catalog
        try:
            from dsa110_contimg.calibration.catalog import \
              load_calibrator_catalog
            catalog = load_calibrator_catalog()
            if catalog is not None:
                cal_info = catalog.get(args.calibrator.upper())
                if cal_info:
                    args.cal_ra = cal_info['ra_deg']
                    args.cal_dec = cal_info['dec_deg']
                    print(f"Found calibrator {args.calibrator} in catalog: RA={args.cal_ra:.6f}, Dec={args.cal_dec:.6f}")
        except Exception:
            pass
    
    check_ms_phasing(
        args.ms,
        calibrator_name=args.calibrator,
        calibrator_ra=args.cal_ra,
        calibrator_dec=args.cal_dec
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


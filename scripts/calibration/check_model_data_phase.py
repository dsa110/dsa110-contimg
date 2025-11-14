#!/usr/bin/env python3
"""
Check MODEL_DATA phase scatter and DATA vs MODEL_DATA alignment.

Usage:
    python check_model_data_phase.py <ms_path> <cal_ra_deg> <cal_dec_deg>
"""

import sys
from casacore.tables import table
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

def check_model_data_phase(ms_path, cal_ra_deg, cal_dec_deg):
    """Check MODEL_DATA phase scatter and alignment with DATA."""
    
    print("=" * 100)
    print(f"MODEL_DATA Phase Diagnostic: {ms_path}")
    print("=" * 100)
    
    with table(ms_path, readonly=True) as tb:
        if "MODEL_DATA" not in tb.colnames():
            print("ERROR: MODEL_DATA column not found")
            return
        
        n_sample = min(10000, tb.nrows())
        print(f"Sampling {n_sample} rows...")
        
        model_data = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)
        data = tb.getcol("DATA", startrow=0, nrow=n_sample)
        flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)
        field_id = tb.getcol("FIELD_ID", startrow=0, nrow=n_sample)
        
        # Get unflagged data
        unflagged_mask = ~flags.any(axis=(1, 2))
        if unflagged_mask.sum() == 0:
            print("ERROR: All data is flagged")
            return
        
        model_unflagged = model_data[unflagged_mask]
        data_unflagged = data[unflagged_mask]
        
        # Check MODEL_DATA phase scatter
        model_phases = np.angle(model_unflagged[:, :, 0])  # Use first polarization
        model_phases_deg = np.degrees(model_phases)
        model_phase_scatter = np.std(model_phases_deg)
        
        print(f"\nMODEL_DATA Statistics:")
        print(f"  Unflagged samples: {unflagged_mask.sum()}")
        print(f"  Phase scatter: {model_phase_scatter:.2f}°")
        print(f"  Expected (for point source at phase center): < 10°")
        
        if model_phase_scatter > 10:
            print(f"  ✗ MODEL_DATA phase scatter is HIGH (expected < 10°)")
        else:
            print(f"  ✓ MODEL_DATA phase scatter is acceptable")
        
        # Check DATA vs MODEL_DATA alignment
        data_phases = np.angle(data_unflagged[:, :, 0])
        phase_diff = data_phases - model_phases
        phase_diff_deg = np.degrees(phase_diff)
        phase_diff_scatter = np.std(phase_diff_deg)
        
        print(f"\nDATA vs MODEL_DATA Alignment:")
        print(f"  Phase difference scatter: {phase_diff_scatter:.2f}°")
        print(f"  Expected (for aligned data): < 20°")
        
        if phase_diff_scatter > 20:
            print(f"  ✗ DATA and MODEL_DATA are MISALIGNED")
        else:
            print(f"  ✓ DATA and MODEL_DATA are aligned")
        
        # Check amplitude ratio
        model_amp = np.abs(model_unflagged[:, :, 0])
        data_amp = np.abs(data_unflagged[:, :, 0])
        
        # Only use non-zero amplitudes
        valid_mask = (model_amp > 1e-10) & (data_amp > 1e-10)
        if valid_mask.sum() > 0:
            amp_ratio = np.median(data_amp[valid_mask] / model_amp[valid_mask])
            print(f"\nAmplitude Ratio (DATA/MODEL):")
            print(f"  Median ratio: {amp_ratio:.4f}")
            print(f"  Expected (for aligned data): ~0.5-1.0 (depends on primary beam)")
            
            if amp_ratio < 0.1:
                print(f"  ✗ DATA amplitude is very weak compared to MODEL (decorrelation?)")
            elif amp_ratio > 2.0:
                print(f"  ✗ DATA amplitude is very strong compared to MODEL (unexpected)")
            else:
                print(f"  ✓ Amplitude ratio is reasonable")
        
        # Check by field
        print(f"\nPhase Scatter by Field:")
        print(f"Field\tMODEL scatter\tDATA-MODEL diff\tSamples")
        print("-" * 60)
        
        unique_fields = np.unique(field_id[unflagged_mask])
        for field_idx in unique_fields[:10]:  # Show first 10 fields
            field_mask = (field_id[unflagged_mask] == field_idx)
            if field_mask.sum() == 0:
                continue
            
            field_model_phases = model_phases_deg[field_mask]
            field_phase_diff = phase_diff_deg[field_mask]
            
            field_model_scatter = np.std(field_model_phases)
            field_diff_scatter = np.std(field_phase_diff)
            
            print(f"{field_idx}\t{field_model_scatter:.2f}°\t\t{field_diff_scatter:.2f}°\t\t{field_mask.sum()}")
        
        print("\n" + "=" * 100)
        
        # Summary
        if model_phase_scatter > 10:
            print("RECOMMENDATION: MODEL_DATA phase scatter is high.")
            print("  - Verify MODEL_DATA was calculated using correct phase centers")
            print("  - Check if manual MODEL_DATA calculation is being used")
            print("  - Verify calibrator position matches phase center")
        
        if phase_diff_scatter > 20:
            print("RECOMMENDATION: DATA and MODEL_DATA are misaligned.")
            print("  - Check if DATA column is correctly phased")
            print("  - Verify UVW coordinates are correct")
            print("  - May need to re-run phaseshift to transform DATA column")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    
    ms_path = sys.argv[1]
    cal_ra_deg = float(sys.argv[2])
    cal_dec_deg = float(sys.argv[3])
    
    check_model_data_phase(ms_path, cal_ra_deg, cal_dec_deg)


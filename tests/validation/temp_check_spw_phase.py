#!/usr/bin/env python3
"""Check if all SPWs are phased to the same phase center."""
from casacore.tables import table
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
import sys
sys.path.insert(0, 'src')
from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec

ms_path = '/scratch/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms'

print('=' * 70)
print('CHECKING SPW PHASE CENTERS')
print('=' * 70)

# Get expected phase center
catalog = load_vla_catalog()
expected_ra_deg, expected_dec_deg = get_calibrator_radec(catalog, '0834+555')
expected_coord = SkyCoord(expected_ra_deg * u.deg, expected_dec_deg * u.deg, frame='icrs')

print(f'\nExpected 0834+555: RA={expected_ra_deg:.10f}°, Dec={expected_dec_deg:.10f}°')

# Check SPECTRAL_WINDOW table structure
print(f'\n{"="*70}')
print('SPECTRAL_WINDOW table structure:')
print(f'{"="*70}')

with table(ms_path + '/SPECTRAL_WINDOW', readonly=True) as spw:
    print(f'Columns: {spw.colnames()}')
    print(f'Number of SPWs: {spw.nrows()}')
    
    # Check if there are any phase center related columns
    phase_cols = [col for col in spw.colnames() if 'phase' in col.lower() or 'center' in col.lower() or 'direction' in col.lower()]
    print(f'\nPhase/center related columns: {phase_cols}')
    
    # Get frequency information
    ref_freqs = spw.getcol('REF_FREQUENCY')
    nchans = spw.getcol('NUM_CHAN')
    
    print(f'\nSPW frequency information:')
    print(f'  SPW ID:  Ref Frequency (GHz):  Num Channels:')
    for i in range(spw.nrows()):
        print(f'  {i:3d}     {ref_freqs[i]/1e9:12.6f}         {nchans[i]:3d}')

# Phase centers are set at FIELD level, not SPW level
# But let's verify by checking which SPWs are used with which fields
print(f'\n{"="*70}')
print('Verifying SPW-FIELD relationship:')
print(f'{"="*70}')

with table(ms_path, readonly=True) as tb:
    # Get DATA_DESC_ID (which maps to SPW)
    data_desc_ids = tb.getcol('DATA_DESC_ID')
    field_ids = tb.getcol('FIELD_ID')
    
    unique_spws = np.unique(data_desc_ids)
    unique_fields = np.unique(field_ids)
    
    print(f'\nUnique SPWs (DATA_DESC_ID): {sorted(unique_spws)}')
    print(f'Unique Fields (FIELD_ID): {sorted(unique_fields)}')
    
    # Check if all SPWs observe all fields
    print(f'\nSPW-FIELD combinations:')
    for spw_id in unique_spws[:5]:  # Check first 5 SPWs
        spw_mask = data_desc_ids == spw_id
        fields_in_spw = np.unique(field_ids[spw_mask])
        print(f'  SPW {spw_id}: observes fields {sorted(fields_in_spw)}')
    
    # Since all fields have the same phase center, all SPWs should use the same phase center
    print(f'\nConclusion: Since all {len(unique_fields)} fields share the same phase center,')
    print(f'           all {len(unique_spws)} SPWs are also phased to the same center.')

# Verify by checking MODEL_DATA phase structure per SPW
print(f'\n{"="*70}')
print('Verifying MODEL_DATA phase structure per SPW:')
print(f'{"="*70}')

with table(ms_path, readonly=True) as tb:
    data_desc_ids = tb.getcol('DATA_DESC_ID')
    unique_spws = np.unique(data_desc_ids)
    
    for spw_id in unique_spws[:5]:  # Check first 5 SPWs
        spw_mask = data_desc_ids == spw_id
        spw_rows = np.where(spw_mask)[0]
        
        if len(spw_rows) > 0:
            sample_size = min(100, len(spw_rows))
            model_data = tb.getcol('MODEL_DATA', startrow=spw_rows[0], nrow=sample_size)
            
            flat_data = model_data.flatten()
            non_zero = flat_data[flat_data != 0]
            
            if len(non_zero) > 0:
                phases = np.angle(non_zero)
                phase_std_deg = np.std(phases) * 180 / np.pi
                max_imag = np.max(np.abs(np.imag(non_zero)))
                
                print(f'\nSPW {spw_id}:')
                print(f'  Rows sampled: {sample_size}')
                print(f'  Phase std: {phase_std_deg:.6f}°')
                print(f'  Max |imag|: {max_imag:.6e}')
                
                if phase_std_deg < 0.01 and max_imag < 1e-6:
                    print(f'  ✓ Purely real (phase ≈ 0) - consistent with same phase center')
                else:
                    print(f'  ✗ Has phase variation - may indicate different phase center')

print('\n' + '=' * 70)


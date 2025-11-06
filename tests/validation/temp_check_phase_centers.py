#!/usr/bin/env python3
"""Check field phase centers vs MODEL_DATA phase center."""
from casacore.tables import table
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
import sys
sys.path.insert(0, 'src')
from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec

ms_path = '/scratch/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms'

# Get 0834+555 coordinates (expected phase center)
catalog = load_vla_catalog()
expected_ra_deg, expected_dec_deg = get_calibrator_radec(catalog, '0834+555')
expected_coord = SkyCoord(expected_ra_deg * u.deg, expected_dec_deg * u.deg, frame='icrs')

print('=' * 70)
print('FIELD PHASE CENTERS vs MODEL_DATA PHASE CENTER')
print('=' * 70)
print(f'\nExpected (0834+555 catalog):')
print(f'  RA: {expected_ra_deg:.10f}° ({expected_coord.ra.to_string(unit=u.hour, precision=2, pad=True)})')
print(f'  Dec: {expected_dec_deg:.10f}° ({expected_coord.dec.to_string(unit=u.deg, precision=2, pad=True, alwayssign=True)})')

# Get field phase centers
print(f'\nField phase centers in phased MS:')
print('-' * 70)

with table(ms_path + '/FIELD', readonly=True) as field:
    nfields = field.nrows()
    field_names = field.getcol('NAME')
    phase_dirs = field.getcol('PHASE_DIR')  # Shape: (nfields, 1, 2) - (RA, Dec) in radians
    
    header = 'Field ID'.ljust(8) + 'Field Name'.ljust(25) + 'RA (deg)'.ljust(15) + 'Dec (deg)'.ljust(15) + 'Offset (arcsec)'.ljust(15)
    print(f'\n{header}')
    print('-' * 90)
    
    max_offset = 0
    offsets = []
    
    for i in range(nfields):
        ra_rad = phase_dirs[i][0][0]
        dec_rad = phase_dirs[i][0][1]
        ra_deg = ra_rad * 180 / np.pi
        dec_deg = dec_rad * 180 / np.pi
        
        coord = SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame='icrs')
        
        # Calculate angular separation
        sep = coord.separation(expected_coord)
        sep_arcsec = sep.arcsec
        
        offsets.append(sep_arcsec)
        if sep_arcsec > max_offset:
            max_offset = sep_arcsec
        
        match_symbol = '✓' if sep_arcsec < 0.1 else '✗'
        
        row = f'{i:<8} {field_names[i]:<25} {ra_deg:>14.10f} {dec_deg:>14.10f} {sep_arcsec:>14.6f} {match_symbol}'
        print(row)
    
    print(f'\nOffset statistics:')
    print(f'  Mean: {np.mean(offsets):.6f} arcsec')
    print(f'  Std: {np.std(offsets):.6f} arcsec')
    print(f'  Min: {np.min(offsets):.6f} arcsec')
    print(f'  Max: {np.max(offsets):.6f} arcsec')
    
    if max_offset < 0.1:
        print(f'\n✓ All fields match expected phase center (max offset < 0.1 arcsec)')
    else:
        print(f'\n✗ Some fields do not match expected phase center (max offset = {max_offset:.6f} arcsec)')
        
        # Investigate why MODEL_DATA might have different phase center
        print(f'\n{"="*70}')
        print('INVESTIGATION: Why MODEL_DATA phase center might differ')
        print(f'{"="*70}')
        
        # Check REFERENCE_DIR vs PHASE_DIR
        if 'REFERENCE_DIR' in field.colnames():
            ref_dirs = field.getcol('REFERENCE_DIR')
            print(f'\nChecking REFERENCE_DIR vs PHASE_DIR:')
            for i in range(min(3, nfields)):
                ref_ra = np.rad2deg(ref_dirs[i][0][0])
                ref_dec = np.rad2deg(ref_dirs[i][0][1])
                phase_ra = np.rad2deg(phase_dirs[i][0][0])
                phase_dec = np.rad2deg(phase_dirs[i][0][1])
                
                ref_coord = SkyCoord(ref_ra * u.deg, ref_dec * u.deg, frame='icrs')
                phase_coord = SkyCoord(phase_ra * u.deg, phase_dec * u.deg, frame='icrs')
                ref_phase_sep = ref_coord.separation(phase_coord).arcsec
                
                print(f'  Field {i}: REFERENCE_DIR vs PHASE_DIR offset: {ref_phase_sep:.6f} arcsec')
        
        print(f'\nNote: MODEL_DATA was created using ft() with component list.')
        print(f'ft() uses PHASE_DIR from the FIELD table, but may have phase center bugs.')
        print(f'If fields have different phase centers, MODEL_DATA may be calculated')
        print(f'at different positions for different fields.')

print('\n' + '=' * 70)


#!/usr/bin/env python3
"""Analyze phase structure of DATA columns."""
from casacore.tables import table
import numpy as np

ms_path = '/scratch/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms'

print('=' * 70)
print('DETAILED PHASE STRUCTURE ANALYSIS')
print('=' * 70)

with table(ms_path, readonly=True) as tb:
    # Get spectral window info
    with table(ms_path + '/SPECTRAL_WINDOW', readonly=True) as spw:
        nspw = spw.nrows()
        nchans = spw.getcol('NUM_CHAN')[0]
        print(f'\nSpectral windows: {nspw}, Channels per SPW: {nchans}')
    
    # Analyze each data column
    sample_size = 5000
    
    for col in ['DATA', 'MODEL_DATA', 'CORRECTED_DATA']:
        print(f'\n{"="*70}')
        print(f'{col}')
        print(f'{"="*70}')
        
        try:
            data = tb.getcol(col, startrow=0, nrow=sample_size)
            print(f'\nShape: {data.shape} (rows, channels, pols)')
            
            if np.all(data == 0):
                print(f'\n✗ All zeros - column not populated')
                continue
            
            # Analyze by polarization
            for pol in range(data.shape[2]):
                pol_data = data[:, :, pol]
                flat_data = pol_data.flatten()
                non_zero = flat_data[flat_data != 0]
                
                if len(non_zero) == 0:
                    print(f'\nPol {pol}: All zeros')
                    continue
                
                amp = np.abs(non_zero)
                phase = np.angle(non_zero)
                
                print(f'\nPol {pol}:')
                print(f'  Non-zero: {len(non_zero):,}/{len(flat_data):,} ({100*len(non_zero)/len(flat_data):.1f}%)')
                print(f'  Amplitude: mean={np.mean(amp):.6f}, std={np.std(amp):.6f}, range=[{np.min(amp):.6f}, {np.max(amp):.6f}]')
                print(f'  Phase: mean={np.mean(phase):.6f} rad ({np.mean(phase)*180/np.pi:.2f}°), std={np.std(phase):.6f} rad ({np.std(phase)*180/np.pi:.2f}°)')
                print(f'  Phase range: [{np.min(phase):.6f}, {np.max(phase):.6f}] rad')
                
                # Check imaginary component
                imag_part = np.imag(non_zero)
                max_imag = np.max(np.abs(imag_part))
                mean_imag = np.mean(np.abs(imag_part))
                print(f'  Imaginary: max={max_imag:.6e}, mean={mean_imag:.6e}')
                
                if max_imag < 1e-6:
                    print(f'  ✓ Purely real')
                elif max_imag < 0.01:
                    print(f'  ⚠ Mostly real (small imag)')
                else:
                    print(f'  ✓ Complex')
                
                # Sample values
                if len(non_zero) >= 3:
                    print(f'\n  Samples (first 3):')
                    for i, val in enumerate(non_zero[:3]):
                        print(f'    {i+1}: {val:.4f} = {np.abs(val):.4f} ∠ {np.angle(val)*180/np.pi:.2f}°')
            
            # Cross-comparison: DATA vs MODEL_DATA
            if col == 'DATA':
                print(f'\n{"="*70}')
                print('DATA vs MODEL_DATA Comparison')
                print(f'{"="*70}')
                
                model_data = tb.getcol('MODEL_DATA', startrow=0, nrow=sample_size)
                
                # Compare for pol 0
                data_pol0 = data[:, :, 0].flatten()
                model_pol0 = model_data[:, :, 0].flatten()
                
                valid = (model_pol0 != 0) & (data_pol0 != 0)
                if np.any(valid):
                    ratio = data_pol0[valid] / model_pol0[valid]
                    ratio_amp = np.abs(ratio)
                    ratio_phase = np.angle(ratio)
                    
                    print(f'\nRatio (DATA/MODEL_DATA) where both non-zero:')
                    print(f'  Valid pairs: {np.sum(valid):,} / {len(valid):,}')
                    print(f'  Amplitude ratio: mean={np.mean(ratio_amp):.6f}, std={np.std(ratio_amp):.6f}')
                    print(f'  Phase difference: mean={np.mean(ratio_phase):.6f} rad ({np.mean(ratio_phase)*180/np.pi:.2f}°), std={np.std(ratio_phase):.6f} rad ({np.std(ratio_phase)*180/np.pi:.2f}°)')
                    
                    # Check if DATA is scaled MODEL_DATA
                    if np.std(ratio_phase) < 0.1:  # Low phase scatter
                        print(f'  ✓ Phase consistent (low scatter) - DATA may be scaled MODEL_DATA')
                    else:
                        print(f'  ⚠ Phase scatter - DATA has different phase structure')
                        
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()

print('\n' + '=' * 70)


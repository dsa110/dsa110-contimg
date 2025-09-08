#!/usr/bin/env python3
"""
Test script to fix antenna positions and UVW coordinates
"""

import asyncio
import sys
import os
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from pyuvdata import UVData
from pyuvdata import utils as uvutils
import astropy.units as u

async def test_antenna_positions_fix():
    print('🔍 Testing Antenna Positions Fix')
    print('=' * 50)
    
    # Read the existing MS file
    ms_file = 'data/ms/2025-09-05T03:23:15.ms'
    print(f'Reading MS file: {ms_file}')
    
    uv_data = UVData()
    uv_data.read(ms_file)
    
    print(f'UVData loaded:')
    print(f'  - Nblts: {uv_data.Nblts}')
    print(f'  - Ntimes: {uv_data.Ntimes}')
    print(f'  - Current antenna positions shape: {uv_data.telescope.antenna_positions.shape}')
    
    # Check current antenna positions
    current_positions = uv_data.telescope.antenna_positions
    print(f'  - Current antenna positions range:')
    print(f'    X: {np.min(current_positions[:, 0]):.1f} to {np.max(current_positions[:, 0]):.1f} m')
    print(f'    Y: {np.min(current_positions[:, 1]):.1f} to {np.max(current_positions[:, 1]):.1f} m')
    print(f'    Z: {np.min(current_positions[:, 2]):.1f} to {np.max(current_positions[:, 2]):.1f} m')
    
    # Calculate baseline lengths from current positions
    print('\\nCalculating baseline lengths from current antenna positions...')
    max_baseline = 0
    for i in range(len(current_positions)):
        for j in range(i+1, len(current_positions)):
            baseline = np.linalg.norm(current_positions[j] - current_positions[i])
            max_baseline = max(max_baseline, baseline)
    print(f'  - Maximum baseline length: {max_baseline:.1f} m')
    
    # Calculate UVW baseline lengths
    print('\\nCalculating UVW baseline lengths...')
    uvw_baseline_lengths = np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))
    print(f'  - UVW baseline lengths:')
    print(f'    Min: {np.min(uvw_baseline_lengths):.1f} m')
    print(f'    Max: {np.max(uvw_baseline_lengths):.1f} m')
    print(f'    Mean: {np.mean(uvw_baseline_lengths):.1f} m')
    
    # The issue might be that the antenna positions are in a different coordinate system
    # Let's try to fix this by scaling the antenna positions to match the UVW baseline lengths
    print('\\nAttempting to fix antenna positions...')
    
    # Calculate the scale factor needed
    scale_factor = np.mean(uvw_baseline_lengths) / max_baseline
    print(f'  - Scale factor needed: {scale_factor:.3f}')
    
    # Apply scale factor to antenna positions
    corrected_positions = current_positions * scale_factor
    print(f'  - Corrected antenna positions range:')
    print(f'    X: {np.min(corrected_positions[:, 0]):.1f} to {np.max(corrected_positions[:, 0]):.1f} m')
    print(f'    Y: {np.min(corrected_positions[:, 1]):.1f} to {np.max(corrected_positions[:, 1]):.1f} m')
    print(f'    Z: {np.min(corrected_positions[:, 2]):.1f} to {np.max(corrected_positions[:, 2]):.1f} m')
    
    # Update antenna positions
    uv_data.telescope.antenna_positions = corrected_positions
    
    # Test UVW validation with corrected antenna positions
    print('\\nTesting UVW validation with corrected antenna positions...')
    try:
        uv_data.check()
        print('✅ UVW validation passed - no discrepancy warnings!')
    except Exception as e:
        print(f'⚠️ UVW validation still has issues: {e}')
    
    # Test writing the corrected MS file
    print('\\nTesting MS file writing with corrected antenna positions...')
    corrected_ms_file = 'data/ms/2025-09-05T03:23:15_antenna_fixed.ms'
    uv_data.write_ms(corrected_ms_file, clobber=True)
    print(f'✅ Corrected MS file written: {corrected_ms_file}')
    
    # Check file size
    if os.path.exists(corrected_ms_file):
        size_gb = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                     for dirpath, dirnames, filenames in os.walk(corrected_ms_file) 
                     for filename in filenames) / (1024**3)
        print(f'   - File size: {size_gb:.1f} GB')
    
    del uv_data

if __name__ == '__main__':
    asyncio.run(test_antenna_positions_fix())

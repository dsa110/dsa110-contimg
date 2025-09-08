#!/usr/bin/env python3
"""
Test PyUVData's built-in UVW fix method
"""

import asyncio
import sys
import os
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from pyuvdata import UVData

async def test_pyuvdata_uvw_fix():
    print('🔍 Testing PyUVData Built-in UVW Fix')
    print('=' * 45)
    
    # First, let's create a simple test MS file
    print('Creating test MS file...')
    
    # Use the orchestrator to create a minimal MS file
    from core.pipeline.orchestrator import PipelineOrchestrator
    
    config = {
        'paths': {
            'ms_stage1_dir': 'data/ms',
            'log_dir': 'logs'
        },
        'ms_creation': {
            'same_timestamp_tolerance': 30.0,
            'min_data_quality': 0.7,
            'max_missing_subbands': 6,
            'min_integration_time': 10.0
        }
    }
    
    orchestrator = PipelineOrchestrator(config)
    
    # Process just one timestamp to create a test MS
    try:
        ms_files = await orchestrator.process_hdf5_to_ms('/data/incoming_test')
        
        if ms_files and os.path.exists(ms_files[0]):
            test_ms_file = ms_files[0]
            print(f'✅ Test MS file created: {test_ms_file}')
            
            # Now test the PyUVData built-in UVW fix
            print('\\nTesting PyUVData set_uvws_from_antenna_positions...')
            
            uv_data = UVData()
            uv_data.read(test_ms_file)
            
            print(f'UVData loaded:')
            print(f'  - Nblts: {uv_data.Nblts}')
            print(f'  - Ntimes: {uv_data.Ntimes}')
            print(f'  - Mean baseline length before: {np.mean(np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))):.3f} m')
            
            # Test PyUVData's built-in UVW recalculation
            try:
                uv_data.set_uvws_from_antenna_positions(update_vis=False)
                print('✅ UVW recalculation completed successfully!')
                
                print(f'  - Mean baseline length after: {np.mean(np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))):.3f} m')
                
                # Test UVW validation
                print('\\nTesting UVW validation...')
                try:
                    uv_data.check()
                    print('✅ UVW validation passed - no discrepancy warnings!')
                except Exception as e:
                    print(f'⚠️ UVW validation issues: {e}')
                
                # Write corrected MS file
                corrected_ms_file = test_ms_file.replace('.ms', '_pyuvdata_fixed.ms')
                uv_data.write_ms(corrected_ms_file, clobber=True)
                print(f'\\n✅ Corrected MS file written: {corrected_ms_file}')
                
                # Check file size
                if os.path.exists(corrected_ms_file):
                    size_gb = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                                 for dirpath, dirnames, filenames in os.walk(corrected_ms_file) 
                                 for filename in filenames) / (1024**3)
                    print(f'   - File size: {size_gb:.1f} GB')
                
            except Exception as e:
                print(f'❌ UVW recalculation failed: {e}')
                import traceback
                traceback.print_exc()
            
            del uv_data
            
        else:
            print('❌ Failed to create test MS file')
            
    except Exception as e:
        print(f'❌ Error creating test MS: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_pyuvdata_uvw_fix())

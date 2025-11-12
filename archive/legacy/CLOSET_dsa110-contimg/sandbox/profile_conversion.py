#!/usr/bin/env python
"""
Profile the UVH5 to MS conversion to identify bottlenecks.
"""

import time
import warnings
import numpy as np
from pyuvdata import UVData

def timed_section(name):
    """Context manager for timing code sections."""
    class Timer:
        def __enter__(self):
            self.start = time.time()
            print(f"\n{'='*70}")
            print(f"{name}")
            print('='*70)
            return self
        
        def __exit__(self, *args):
            elapsed = time.time() - self.start
            print(f"  → {name}: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    return Timer()


def profile_conversion(input_files, output_ms):
    """Profile each step of the conversion."""
    
    total_start = time.time()
    
    # Step 1: Read first file
    with timed_section("1. Reading first file"):
        uv = UVData()
        uv.read(input_files[0], file_type='uvh5', run_check=False, check_extra=False)
        if uv.uvw_array.dtype != np.float64:
            uv.uvw_array = uv.uvw_array.astype(np.float64)
        print(f"  Shape: {uv.Nblts} blts × {uv.Nfreqs} freqs × {uv.Npols} pols")
    
    # Step 2: Read and concatenate remaining files
    with timed_section(f"2. Reading and concatenating {len(input_files)-1} more files"):
        for i, filename in enumerate(input_files[1:], start=2):
            file_start = time.time()
            
            uv_new = UVData()
            uv_new.read(filename, file_type='uvh5', run_check=False, check_extra=False)
            if uv_new.uvw_array.dtype != np.float64:
                uv_new.uvw_array = uv_new.uvw_array.astype(np.float64)
            
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                uv.fast_concat(
                    uv_new,
                    axis='freq',
                    inplace=True,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                    ignore_name=True
                )
            
            file_elapsed = time.time() - file_start
            print(f"  File {i:2d}: {file_elapsed:.2f}s | Now {uv.Nfreqs} freqs")
    
    # Step 3: Reorder frequencies
    with timed_section("3. Reordering frequencies"):
        uv.reorder_freqs(channel_order='freq', run_check=False)
    
    # Step 4: Write MS
    with timed_section("4. Writing MS"):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            uv.write_ms(
                output_ms,
                force_phase='drift',
                run_check=False,
                check_extra=False,
                run_check_acceptability=False,
                clobber=True
            )
    
    total_elapsed = time.time() - total_start
    print(f"\n{'='*70}")
    print(f"TOTAL TIME: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
    print('='*70)


if __name__ == '__main__':
    import sys
    import glob
    import os
    import shutil
    
    # Use just 4 files for quick profiling
    pattern = '/data/incoming/2025-09-28T15:58:0*.hdf5'
    files = sorted(glob.glob(pattern))[:4]
    
    if len(files) < 4:
        print(f"Error: Need at least 4 files, found {len(files)}")
        sys.exit(1)
    
    print(f"Profiling conversion with {len(files)} files...")
    print(f"Files: {[f.split('/')[-1] for f in files]}\n")
    
    output_ms = '/tmp/profile_test.ms'
    profile_conversion(files, output_ms)
    
    # Clean up
    import shutil
    if os.path.exists(output_ms):
        shutil.rmtree(output_ms)
        print(f"\n✓ Cleaned up test MS")


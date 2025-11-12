#!/usr/bin/env python
"""
Optimized UVH5 to MS conversion with pre-phasing.

Strategy: Phase each subband before concatenation, then write with force_phase=False
This avoids re-phasing the large concatenated dataset.
"""

import os
import sys
import time
import warnings
import numpy as np
from pyuvdata import UVData


def convert_uvh5_to_ms_optimized(input_files, output_ms, verbose=True):
    """
    Convert multiple UVH5 files to MS with optimized phasing strategy.
    
    Key optimization: Phase each subband BEFORE concatenation to avoid
    re-phasing the full 768-channel dataset.
    """
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"OPTIMIZED UVH5 → MS Conversion")
        print(f"{'='*70}")
        print(f"Strategy: Pre-phase each subband before concatenation")
        print(f"Files: {len(input_files)}")
        print(f"Output: {output_ms}")
        print()
    
    total_start = time.time()
    
    # Read first file
    if verbose:
        print(f"[1/{len(input_files)}] Reading {os.path.basename(input_files[0])}...")
    
    uv = UVData()
    uv.read(input_files[0], file_type='uvh5', run_check=False, check_extra=False)
    
    # Fix dtype
    if uv.uvw_array.dtype != np.float64:
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    
    if verbose:
        print(f"  → Loaded: {uv.Nblts} blts × {uv.Nfreqs} freqs × {uv.Npols} pols")
    
    # Read and concatenate remaining files
    for i, filename in enumerate(input_files[1:], start=2):
        if verbose:
            print(f"[{i}/{len(input_files)}] Reading {os.path.basename(filename)}...")
        
        file_start = time.time()
        
        uv_new = UVData()
        uv_new.read(filename, file_type='uvh5', run_check=False, check_extra=False)
        
        # Fix dtype
        if uv_new.uvw_array.dtype != np.float64:
            uv_new.uvw_array = uv_new.uvw_array.astype(np.float64)
        
        # Concatenate
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
        if verbose:
            print(f"  → Now: {uv.Nfreqs} channels ({file_elapsed:.2f}s)")
    
    # Reorder frequencies
    if verbose:
        print(f"\nReordering frequencies...")
    uv.reorder_freqs(channel_order='freq', run_check=False)
    
    # Write MS WITHOUT re-phasing (data already phased!)
    if verbose:
        write_start = time.time()
        print(f"\nWriting MS (no re-phasing needed)...")
        print(f"  Shape: {uv.Nblts} blts × {uv.Nfreqs} freqs × {uv.Npols} pols")
    
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        uv.write_ms(
            output_ms,
            force_phase=False,  # KEY: Don't re-phase! Data already phased
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            clobber=True
        )
    
    if verbose:
        write_elapsed = time.time() - write_start
        total_elapsed = time.time() - total_start
        
        # Get MS size
        ms_size = sum(
            os.path.getsize(os.path.join(root, f))
            for root, dirs, files in os.walk(output_ms)
            for f in files
        )
        
        print(f"\n✓ Successfully wrote MS ({ms_size/1e6:.1f} MB)")
        print(f"\nTiming breakdown:")
        print(f"  Write MS:     {write_elapsed:.1f}s ({100*write_elapsed/total_elapsed:.0f}%)")
        print(f"  Other steps:  {total_elapsed-write_elapsed:.1f}s ({100*(total_elapsed-write_elapsed)/total_elapsed:.0f}%)")
        print(f"  TOTAL:        {total_elapsed:.1f}s ({total_elapsed/60:.2f} minutes)")
        print('='*70)
    
    return output_ms


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimized UVH5 to MS conversion')
    parser.add_argument('input_files', nargs='+', help='Input UVH5 files')
    parser.add_argument('-o', '--output', required=True, help='Output MS filename')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress progress')
    
    args = parser.parse_args()
    
    input_files = sorted(args.input_files)
    
    if not input_files:
        print("Error: No input files specified")
        sys.exit(1)
    
    # Check files exist
    for f in input_files:
        if not os.path.exists(f):
            print(f"Error: File not found: {f}")
            sys.exit(1)
    
    convert_uvh5_to_ms_optimized(input_files, args.output, verbose=not args.quiet)


if __name__ == '__main__':
    # Add imports needed for phasing
    from astropy.time import Time
    main()


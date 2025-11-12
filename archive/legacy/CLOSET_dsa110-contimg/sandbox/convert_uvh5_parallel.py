#!/usr/bin/env python
"""
Parallel UVH5 to MS converter with optimizations for DSA-110.
Can potentially achieve 2-3x speedup through:
1. Parallel file reading
2. Memory-mapped I/O
3. Reduced validation overhead
"""

import os
import sys
import glob
import warnings
import argparse
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyuvdata import UVData

def read_single_uvh5(filename, verbose=False):
    """Read a single UVH5 file with error handling."""
    if verbose:
        print(f"  → Reading {os.path.basename(filename)}...")
    
    uv = UVData()
    uv.read(filename, file_type='uvh5', run_check=False, check_extra=False)
    
    # Fix dtype immediately after reading
    if uv.uvw_array.dtype != np.float64:
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    
    if verbose:
        print(f"     Loaded: {uv.Nblts} baselines × {uv.Nfreqs} channels")
    
    return uv

def convert_uvh5_to_ms_parallel(input_files, output_ms, max_workers=4, verbose=True):
    """
    Convert UVH5 files to MS using parallel file reading.
    
    Parameters
    ----------
    input_files : list
        List of UVH5 files to convert
    output_ms : str
        Output MS filename
    max_workers : int
        Number of parallel readers (default: 4)
    verbose : bool
        Print progress
    """
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"Parallel UVH5 to MS Conversion")
        print(f"{'='*70}")
        print(f"Input files: {len(input_files)}")
        print(f"Parallel workers: {max_workers}")
        print(f"Output: {output_ms}")
        print()
    
    # Strategy: Read multiple files in parallel, then combine sequentially
    # (pyuvdata's fast_concat requires sequential access due to metadata merging)
    
    # Read first file
    uv_combined = read_single_uvh5(input_files[0], verbose=verbose)
    
    if len(input_files) == 1:
        # Single file, just write it
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            uv_combined.write_ms(
                output_ms,
                force_phase='drift',
                run_check=False,
                check_extra=False,
                run_check_acceptability=False,
                clobber=True
            )
        return output_ms
    
    # For multiple files: read in batches and concatenate
    # This provides parallelism while keeping memory under control
    batch_size = max_workers
    n_remaining = len(input_files) - 1
    
    for batch_start in range(1, len(input_files), batch_size):
        batch_end = min(batch_start + batch_size, len(input_files))
        batch_files = input_files[batch_start:batch_end]
        
        if verbose:
            print(f"\nReading batch: files {batch_start+1}-{batch_end}/{len(input_files)}")
        
        # Read batch in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(read_single_uvh5, f, False): f for f in batch_files}
            batch_uvs = []
            
            for future in as_completed(futures):
                try:
                    uv = future.result()
                    batch_uvs.append(uv)
                except Exception as e:
                    filename = futures[future]
                    print(f"  ⚠ Error reading {filename}: {e}")
                    raise
        
        # Sort batch by filename to maintain frequency order
        batch_uvs_sorted = sorted(zip(batch_files, batch_uvs), key=lambda x: x[0])
        
        # Concatenate batch sequentially
        for filename, uv_new in batch_uvs_sorted:
            if verbose:
                print(f"  → Concatenating {os.path.basename(filename)}...")
            
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                uv_combined.fast_concat(
                    uv_new,
                    axis='freq',
                    inplace=True,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                    ignore_name=True
                )
            
            if verbose:
                print(f"     Now: {uv_combined.Nfreqs} total channels")
    
    # Reorder frequencies
    if verbose:
        print("\nReordering frequencies...")
    uv_combined.reorder_freqs(channel_order='freq', run_check=False)
    
    # Write to MS
    if verbose:
        print(f"Writing to MS: {output_ms}")
        print(f"  Final shape: {uv_combined.Nblts} baselines × {uv_combined.Nfreqs} channels × {uv_combined.Npols} pols")
    
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        uv_combined.write_ms(
            output_ms,
            force_phase='drift',
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            clobber=True
        )
    
    # Get MS size
    ms_size = 0
    for root, dirs, files in os.walk(output_ms):
        ms_size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    
    if verbose:
        print(f"✓ Successfully wrote MS ({ms_size/1e6:.1f} MB)")
        print("="*70)
    
    return output_ms


def main():
    parser = argparse.ArgumentParser(
        description='Convert UVH5 files to CASA Measurement Set (parallel version)'
    )
    parser.add_argument('input_files', nargs='+', help='Input UVH5 files')
    parser.add_argument('-o', '--output', required=True, help='Output MS filename')
    parser.add_argument('-j', '--jobs', type=int, default=4, 
                       help='Number of parallel readers (default: 4)')
    parser.add_argument('-q', '--quiet', action='store_true', 
                       help='Suppress progress messages')
    
    args = parser.parse_args()
    
    # Sort input files
    input_files = sorted(args.input_files)
    
    # Basic validation
    if not input_files:
        print("Error: No input files specified")
        sys.exit(1)
    
    for f in input_files:
        if not os.path.exists(f):
            print(f"Error: Input file not found: {f}")
            sys.exit(1)
    
    # Convert
    convert_uvh5_to_ms_parallel(
        input_files,
        args.output,
        max_workers=args.jobs,
        verbose=not args.quiet
    )


if __name__ == '__main__':
    main()


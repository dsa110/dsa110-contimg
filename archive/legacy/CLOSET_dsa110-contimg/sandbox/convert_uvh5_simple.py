#!/usr/bin/env python
"""
Simple UVH5 to MS conversion script using pyuvdata 3.2+ directly.
Avoids all the complex API compatibility issues in makems_rk.
"""

import os
import sys
import glob
import warnings
import numpy as np
from pyuvdata import UVData

def convert_uvh5_to_ms(input_files, output_ms, verbose=True):
    """
    Convert one or more UVH5 files to a single CASA Measurement Set.
    
    Parameters
    ----------
    input_files : list of str
        Paths to input UVH5 files (one per sub-band)
    output_ms : str
        Path to output MS file
    verbose : bool
        Print progress messages
    """
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"Converting {len(input_files)} UVH5 files to MS")
        print(f"{'='*70}")
    
    # Read the first file
    if verbose:
        print(f"\n[1/{len(input_files)}] Reading {os.path.basename(input_files[0])}...")
    
    uv = UVData()
    uv.read(input_files[0], file_type='uvh5', run_check=False, check_extra=False)
    
    # Fix dtype issues (UVH5 files have float32 but pyuvdata 3.2 requires float64)
    if uv.uvw_array.dtype != np.float64:
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    
    if verbose:
        print(f"  → Loaded: {uv.Nblts} baselines × {uv.Nfreqs} channels × {uv.Npols} pols")
    
    # Concatenate additional files along frequency axis
    if len(input_files) > 1:
        for i, filename in enumerate(input_files[1:], start=2):
            if verbose:
                print(f"\n[{i}/{len(input_files)}] Reading {os.path.basename(filename)}...")
            
            uv_new = UVData()
            uv_new.read(filename, file_type='uvh5', run_check=False, check_extra=False)
            
            # Fix dtype issues
            if uv_new.uvw_array.dtype != np.float64:
                uv_new.uvw_array = uv_new.uvw_array.astype(np.float64)
            
            if verbose:
                print(f"  → Loaded: {uv_new.Nblts} baselines × {uv_new.Nfreqs} channels")
                print(f"  → Concatenating along frequency axis...")
            
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
            
            if verbose:
                print(f"  → Now: {uv.Nfreqs} total channels")
    
    # Reorder frequencies
    if verbose:
        print(f"\nReordering frequencies...")
    uv.reorder_freqs(channel_order='freq', run_check=False)
    
    # Write to MS
    if verbose:
        print(f"\nWriting to MS: {output_ms}")
        print(f"  Final shape: {uv.Nblts} baselines × {uv.Nfreqs} channels × {uv.Npols} pols")
    
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
    
    if verbose:
        # Get MS size
        ms_size = sum(
            os.path.getsize(os.path.join(dirpath, f))
            for dirpath, _, filenames in os.walk(output_ms)
            for f in filenames
        )
        print(f"\n✓ Successfully wrote MS ({ms_size / (1024**2):.1f} MB)")
        print(f"{'='*70}\n")
    
    return output_ms


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Convert UVH5 files to CASA Measurement Set',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all sb*.hdf5 files in a directory to a single MS
  %(prog)s /data/incoming_test/*.hdf5 -o /data/output/test.ms
  
  # Convert with a specific file list
  %(prog)s file1.hdf5 file2.hdf5 file3.hdf5 -o output.ms
        """
    )
    
    parser.add_argument(
        'input_files',
        nargs='+',
        help='Input UVH5 files (will be sorted and concatenated)'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output MS filename'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )
    
    args = parser.parse_args()
    
    # Sort input files to ensure correct frequency ordering
    input_files = sorted(args.input_files)
    
    if not input_files:
        print("ERROR: No input files provided")
        sys.exit(1)
    
    # Check that all files exist
    missing = [f for f in input_files if not os.path.exists(f)]
    if missing:
        print(f"ERROR: The following files do not exist:")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)
    
    # Convert
    try:
        convert_uvh5_to_ms(input_files, args.output, verbose=not args.quiet)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()


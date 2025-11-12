#!/usr/bin/env python
"""
Fast UVH5 to MS conversion using pyuvdata's multi-file read capability.
"""

import os
import sys
import warnings
import numpy as np
from pyuvdata import UVData

def convert_uvh5_to_ms(input_files, output_ms):
    """
    Convert multiple UVH5 files to a single CASA Measurement Set.
    Uses pyuvdata's native multi-file reading which is more efficient.
    """
    
    print(f"\n{'='*70}")
    print(f"Converting {len(input_files)} UVH5 files to MS")
    print(f"{'='*70}\n")
    
    # Read all files at once (pyuvdata handles concatenation internally)
    print(f"Reading {len(input_files)} files...")
    uv = UVData()
    
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        uv.read(
            input_files,
            file_type='uvh5',
            run_check=False,
            check_extra=False,
            axis='freq'  # Concatenate along frequency
        )
    
    print(f"✓ Loaded: {uv.Nblts} baselines × {uv.Nfreqs} channels × {uv.Npols} pols")
    
    # Fix dtype if needed
    if uv.uvw_array.dtype != np.float64:
        print(f"  Converting UVW array to float64...")
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    
    # Reorder frequencies
    print(f"Reordering frequencies...")
    uv.reorder_freqs(channel_order='freq', run_check=False)
    
    # Write MS
    print(f"Writing MS to {output_ms}...")
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
    
    print(f"\n{'='*70}")
    print(f"✓ Conversion complete!")
    print(f"{'='*70}\n")
    
    return output_ms

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fast UVH5 to MS converter')
    parser.add_argument('input_files', nargs='+', help='Input UVH5 files')
    parser.add_argument('-o', '--output', required=True, help='Output MS filename')
    
    args = parser.parse_args()
    
    input_files = sorted(args.input_files)
    
    if not input_files:
        print("Error: No input files specified")
        sys.exit(1)
    
    # Verify files exist
    for f in input_files:
        if not os.path.exists(f):
            print(f"Error: File not found: {f}")
            sys.exit(1)
    
    convert_uvh5_to_ms(input_files, args.output)

if __name__ == '__main__':
    main()


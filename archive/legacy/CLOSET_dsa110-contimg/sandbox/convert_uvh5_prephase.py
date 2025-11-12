#!/usr/bin/env python
import os
import sys
import time
import warnings
import numpy as np
from astropy.time import Time
from pyuvdata import UVData

def convert_uvh5_prephase(input_files, output_ms, verbose=True):
    t0 = time.time()
    if verbose:
        print("\n======================================================================")
        print("Pre-phase UVH5 → MS Conversion (phase_to_time @ t0, then write_ms force_phase=False)")
        print("======================================================================")
        print(f"Files: {len(input_files)}")
        print(f"Output: {output_ms}")

    uv = UVData()
    # Read all files sequentially and concat along freq
    if verbose:
        print(f"Reading {os.path.basename(input_files[0])}...")
    uv.read(input_files[0], file_type='uvh5', run_check=False, check_extra=False)
    if uv.uvw_array.dtype != np.float64:
        uv.uvw_array = uv.uvw_array.astype(np.float64)

    for f in input_files[1:]:
        if verbose:
            print(f"Reading {os.path.basename(f)}...")
        uv2 = UVData()
        uv2.read(f, file_type='uvh5', run_check=False, check_extra=False)
        if uv2.uvw_array.dtype != np.float64:
            uv2.uvw_array = uv2.uvw_array.astype(np.float64)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            uv.fast_concat(
                uv2,
                axis='freq',
                inplace=True,
                run_check=False,
                check_extra=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
                ignore_name=True,
            )
    uv.reorder_freqs(channel_order='freq', run_check=False)

    # Phase to time (zenith at first timestamp)
    if verbose:
        print("Phasing to first timestamp (phase_to_time)...")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        phase_time = Time(uv.time_array[0], format='jd')
        uv.phase_to_time(phase_time, use_ant_pos=True)

    if verbose:
        print(f"Writing MS (force_phase=False): {output_ms}")
        print(f"  Shape: {uv.Nblts} blts × {uv.Nfreqs} freqs × {uv.Npols} pols")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        uv.write_ms(
            output_ms,
            force_phase=False,
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            clobber=True,
        )

    if verbose:
        ms_size = 0
        for root, _, files in os.walk(output_ms):
            for name in files:
                p = os.path.join(root, name)
                try:
                    ms_size += os.path.getsize(p)
                except FileNotFoundError:
                    pass
        dt = time.time() - t0
        print(f"\n✓ Wrote MS ({ms_size/1e6:.1f} MB) in {dt:.1f}s")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pre-phase UVH5 files and write MS quickly')
    parser.add_argument('input_files', nargs='+', help='Input UVH5 files')
    parser.add_argument('-o', '--output', required=True, help='Output MS path')
    parser.add_argument('-q', '--quiet', action='store_true')
    args = parser.parse_args()
    files = sorted(args.input_files)
    for f in files:
        if not os.path.exists(f):
            print(f"Error: missing {f}")
            sys.exit(1)
    convert_uvh5_prephase(files, args.output, verbose=not args.quiet)

if __name__ == '__main__':
    main()

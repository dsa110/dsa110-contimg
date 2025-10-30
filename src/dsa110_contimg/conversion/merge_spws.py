"""Utility to merge multiple SPWs into a single SPW Measurement Set.

This module provides functions to convert multi-SPW MS files (created by
direct-subband writer) into single-SPW MS files using CASA mstransform.
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

import numpy as np
from casacore.tables import table  # type: ignore[import]
from casatasks import mstransform  # type: ignore[import]


def merge_spws(
    ms_in: str,
    ms_out: str,
    *,
    datacolumn: str = "DATA",
    regridms: bool = True,
    interpolation: str = "linear",
    keepflags: bool = True,
) -> str:
    """
    Merge multiple SPWs into a single SPW using CASA mstransform.
    
    This function takes a multi-SPW MS (e.g., created by direct-subband writer
    with 16 SPWs) and creates a single-SPW MS with all frequencies combined.
    
    Args:
        ms_in: Input multi-SPW Measurement Set path
        ms_out: Output single-SPW Measurement Set path
        datacolumn: Data column to use ('DATA', 'CORRECTED_DATA', etc.)
        regridms: If True, regrid to a contiguous frequency grid. If False,
                  combine SPWs without regridding (may have gaps).
        interpolation: Interpolation method when regridding ('linear', 'nearest', etc.)
        keepflags: Preserve flagging information
        
    Returns:
        Path to output MS
        
    Raises:
        FileNotFoundError: If input MS doesn't exist
        RuntimeError: If mstransform fails
    """
    if not os.path.exists(ms_in):
        raise FileNotFoundError(f"Input MS not found: {ms_in}")
    
    # Remove existing output if present
    if os.path.isdir(ms_out):
        shutil.rmtree(ms_out, ignore_errors=True)
    
    kwargs = dict(
        vis=ms_in,
        outputvis=ms_out,
        datacolumn=datacolumn,
        combinespws=True,
        regridms=regridms,
        keepflags=keepflags,
    )
    
    if regridms:
        # Build global frequency grid from all SPWs
        with table(f"{ms_in}::SPECTRAL_WINDOW", readonly=True) as spw:
            cf = np.asarray(spw.getcol('CHAN_FREQ'))  # shape (nspw, nchan)
        
        # Flatten and sort all frequencies
        all_freq = np.sort(cf.reshape(-1))
        
        # Calculate channel width (median of frequency differences)
        freq_diffs = np.diff(all_freq)
        dnu = float(np.median(freq_diffs[freq_diffs > 0]))
        
        nchan = int(all_freq.size)
        start = float(all_freq[0])
        
        kwargs.update(
            mode='frequency',
            nchan=nchan,
            start=f'{start}Hz',
            width=f'{dnu}Hz',
            interpolation=interpolation,
        )
    
    mstransform(**kwargs)
    
    if not os.path.exists(ms_out):
        raise RuntimeError(f"mstransform failed to create output MS: {ms_out}")
    
    return ms_out


def merge_spws_simple(
    ms_in: str,
    ms_out: str,
    *,
    datacolumn: str = "DATA",
    keepflags: bool = True,
) -> str:
    """
    Simple SPW merging without regridding (combines SPWs but may have gaps).
    
    This is faster than merge_spws() but may result in discontinuous frequency
    coverage if subbands have gaps.
    
    Args:
        ms_in: Input multi-SPW Measurement Set path
        ms_out: Output single-SPW Measurement Set path
        datacolumn: Data column to use
        keepflags: Preserve flagging information
        
    Returns:
        Path to output MS
    """
    return merge_spws(
        ms_in=ms_in,
        ms_out=ms_out,
        datacolumn=datacolumn,
        regridms=False,
        keepflags=keepflags,
    )


def get_spw_count(ms_path: str) -> Optional[int]:
    """
    Get the number of spectral windows in an MS.
    
    Args:
        ms_path: Path to Measurement Set
        
    Returns:
        Number of SPWs, or None if unable to read
    """
    try:
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
            return spw.nrows()
    except Exception:
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Merge multiple SPWs into a single SPW Measurement Set"
    )
    parser.add_argument("ms_in", help="Input multi-SPW MS path")
    parser.add_argument("ms_out", help="Output single-SPW MS path")
    parser.add_argument(
        "--datacolumn",
        default="DATA",
        choices=["DATA", "CORRECTED_DATA", "MODEL_DATA"],
        help="Data column to use",
    )
    parser.add_argument(
        "--no-regrid",
        action="store_true",
        help="Combine SPWs without regridding (faster but may have gaps)",
    )
    parser.add_argument(
        "--interpolation",
        default="linear",
        choices=["linear", "nearest", "cubic"],
        help="Interpolation method for regridding",
    )
    
    args = parser.parse_args()
    
    print(f"Input MS: {args.ms_in}")
    n_spw_in = get_spw_count(args.ms_in)
    if n_spw_in:
        print(f"Input SPWs: {n_spw_in}")
    
    print(f"Output MS: {args.ms_out}")
    print(f"Regridding: {not args.no_regrid}")
    
    merge_spws(
        ms_in=args.ms_in,
        ms_out=args.ms_out,
        datacolumn=args.datacolumn,
        regridms=not args.no_regrid,
        interpolation=args.interpolation,
    )
    
    n_spw_out = get_spw_count(args.ms_out)
    if n_spw_out:
        print(f"Output SPWs: {n_spw_out}")
        if n_spw_out == 1:
            print("✓ Successfully merged SPWs into single SPW")
        else:
            print(f"⚠ Warning: Expected 1 SPW, got {n_spw_out}")


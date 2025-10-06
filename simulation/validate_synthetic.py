#!/usr/bin/env python3
"""
Validation utility for generated synthetic UVH5 files.

Checks that generated files meet DSA-110 specifications and are compatible
with the conversion pipeline.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from pyuvdata import UVData


def validate_uvh5_file(filepath: Path) -> Tuple[bool, List[str]]:
    """
    Validate a single UVH5 file.
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    try:
        uv = UVData()
        uv.read(str(filepath), file_type='uvh5', run_check=False,
                run_check_acceptability=False, strict_uvw_antpos_check=False)
    except Exception as e:
        return False, [f"Failed to read file: {e}"]
    
    # Check antenna count (DSA-110 has 117 antennas)
    if uv.Nants_telescope != 117:
        errors.append(f"Expected 117 antennas, got {uv.Nants_telescope}")
    
    # Check polarizations (should be 4: XX, XY, YX, YY)
    if uv.Npols != 4:
        errors.append(f"Expected 4 polarizations, got {uv.Npols}")
    
    # Check frequency channels (should be 384 per subband)
    if uv.Nfreqs not in [64, 384]:  # 64 for minimal test, 384 for full
        errors.append(f"Expected 384 (or 64 for minimal) channels, got {uv.Nfreqs}")
    
    # Check integration time (DSA-110 typical: ~12-13 seconds)
    int_time = uv.integration_time[0]
    if not (10.0 < int_time < 20.0):
        errors.append(f"Integration time {int_time:.2f}s is unusual for DSA-110")
    
    # Check data array shape
    expected_shape = (uv.Nblts, uv.Nspws, uv.Nfreqs, uv.Npols)
    if uv.data_array.shape != expected_shape:
        errors.append(f"Data array shape {uv.data_array.shape} != expected {expected_shape}")
    
    # Check for NaN or Inf in data
    if np.any(np.isnan(uv.data_array)):
        errors.append("Data array contains NaN values")
    if np.any(np.isinf(uv.data_array)):
        errors.append("Data array contains Inf values")
    
    # Check flag array
    if uv.flag_array.shape != uv.data_array.shape:
        errors.append(f"Flag array shape mismatch: {uv.flag_array.shape} vs {uv.data_array.shape}")
    
    return (len(errors) == 0), errors


def validate_subband_group(directory: Path, timestamp: str) -> Tuple[bool, List[str]]:
    """
    Validate a complete subband group.
    
    Args:
        directory: Directory containing subband files
        timestamp: Expected timestamp string (e.g., "2025-10-06T12:00:00")
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # Find all subbands for this timestamp
    pattern = f"{timestamp}_sb*.hdf5"
    subband_files = sorted(directory.glob(pattern))
    
    if len(subband_files) == 0:
        return False, [f"No subband files found matching {pattern}"]
    
    # Check subband count
    if len(subband_files) not in [4, 16]:  # 4 for minimal, 16 for full
        errors.append(f"Expected 16 subbands (or 4 for minimal), found {len(subband_files)}")
    
    # Validate each subband
    for sb_file in subband_files:
        is_valid, sb_errors = validate_uvh5_file(sb_file)
        if not is_valid:
            errors.append(f"{sb_file.name}: {'; '.join(sb_errors)}")
    
    # Check timestamps match
    timestamps = set()
    for sb_file in subband_files:
        # Extract timestamp from filename
        ts = sb_file.stem.rsplit('_sb', 1)[0]
        timestamps.add(ts)
    
    if len(timestamps) > 1:
        errors.append(f"Multiple timestamps found in group: {timestamps}")
    
    return (len(errors) == 0), errors


def print_summary(filepath: Path):
    """Print summary information about a UVH5 file."""
    try:
        uv = UVData()
        uv.read(str(filepath), file_type='uvh5', run_check=False,
                run_check_acceptability=False, strict_uvw_antpos_check=False)
        
        print(f"\n{filepath.name}:")
        print(f"  Antennas: {uv.Nants_telescope}")
        print(f"  Baselines: {uv.Nbls}")
        print(f"  Times: {uv.Ntimes}")
        print(f"  Frequencies: {uv.Nfreqs}")
        print(f"  Polarizations: {uv.Npols}")
        print(f"  Integration time: {uv.integration_time[0]:.2f} s")
        print(f"  Freq range: {uv.freq_array.min()/1e6:.1f} - {uv.freq_array.max()/1e6:.1f} MHz")
        print(f"  Data shape: {uv.data_array.shape}")
        
    except Exception as e:
        print(f"\n{filepath.name}: ERROR - {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Validate synthetic UVH5 files for DSA-110',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single file
  %(prog)s file.hdf5
  
  # Validate entire observation group
  %(prog)s --group /path/to/subbands --timestamp "2025-10-06T12:00:00"
  
  # Print summary of all files in directory
  %(prog)s --summary /path/to/subbands/*.hdf5
        """
    )
    
    parser.add_argument('files', nargs='*', type=Path,
                        help='UVH5 files to validate')
    parser.add_argument('--group', type=Path,
                        help='Directory containing subband group')
    parser.add_argument('--timestamp', type=str,
                        help='Timestamp for subband group validation')
    parser.add_argument('--summary', action='store_true',
                        help='Print summary instead of validation')
    
    args = parser.parse_args()
    
    # Group validation mode
    if args.group and args.timestamp:
        print(f"Validating subband group: {args.timestamp}")
        is_valid, errors = validate_subband_group(args.group, args.timestamp)
        
        if is_valid:
            print("✓ Subband group is valid")
            return 0
        else:
            print("✗ Subband group validation failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
    
    # File validation mode
    if not args.files:
        parser.print_help()
        return 1
    
    if args.summary:
        # Summary mode
        for filepath in args.files:
            if filepath.exists():
                print_summary(filepath)
        return 0
    
    # Validation mode
    all_valid = True
    for filepath in args.files:
        if not filepath.exists():
            print(f"✗ {filepath}: File not found")
            all_valid = False
            continue
        
        is_valid, errors = validate_uvh5_file(filepath)
        if is_valid:
            print(f"✓ {filepath.name}: Valid")
        else:
            print(f"✗ {filepath.name}: Invalid")
            for error in errors:
                print(f"  - {error}")
            all_valid = False
    
    return 0 if all_valid else 1


if __name__ == '__main__':
    sys.exit(main())

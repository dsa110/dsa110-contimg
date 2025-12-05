"""
Shared MS conversion helpers for ops pipeline scripts.

This module consolidates duplicate MS conversion functions from multiple
pipeline scripts.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional

from dsa110_contimg.conversion.uvh5_to_ms import convert_single_file


def write_ms_group_via_uvh5_to_ms(
    file_list: List[str],
    ms_out: Path,
    add_imaging_columns: bool = True,
    configure_final_ms: bool = True,
) -> None:
    """
    Convert each subband UVH5 to a per-subband MS via uvh5_to_ms, then concat.
    
    This function:
    1. Converts each subband UVH5 file to an MS part
    2. Concatenates all parts into a final MS
    3. Optionally adds/ensures imaging columns exist
    4. Cleans up intermediate parts
    
    Args:
        file_list: List of UVH5 file paths to convert
        ms_out: Output MS path
        add_imaging_columns: If True, let convert_single_file handle imaging columns.
                            If False, columns will be added manually after conversion (legacy behavior)
        configure_final_ms: If True, call configure_ms_for_imaging on final MS (for some workflows)
    
    This mirrors the central pipeline approach and ensures imaging columns exist.
    """
    from casatasks import concat as casa_concat
    
    part_base = ms_out.parent / (ms_out.stem + '.parts')
    part_base.mkdir(parents=True, exist_ok=True)
    parts: List[str] = []
    
    for idx, sb in enumerate(sorted(file_list)):
        part_out = part_base / f"{ms_out.stem}.sb{idx:02d}.ms"
        
        # Remove existing part if present
        if part_out.exists():
            shutil.rmtree(part_out, ignore_errors=True)
        
        # Convert single UVH5 file to MS
        convert_single_file(
            sb,
            os.fspath(part_out),
            add_imaging_columns=add_imaging_columns,
            create_time_binned_fields=False,
            field_time_bin_minutes=5.0,
            write_recommendations=False,
            enable_phasing=True,
            phase_reference_time=None,
        )
        
        # If add_imaging_columns=False, manually add columns (legacy behavior)
        if not add_imaging_columns:
            try:
                from casacore.tables import addImagingColumns as _addImCols
                _addImCols(os.fspath(part_out))
            except Exception:
                pass
            
            try:
                from dsa110_contimg.conversion.uvh5_to_ms import _ensure_imaging_columns_populated as _fill_cols
                _fill_cols(os.fspath(part_out))
            except Exception:
                pass
        
        parts.append(os.fspath(part_out))
    
    # Remove existing output MS if present
    if ms_out.exists():
        shutil.rmtree(ms_out, ignore_errors=True)
    
    # Concatenate parts into final MS
    casa_concat(
        vis=sorted(parts),
        concatvis=os.fspath(ms_out),
        copypointing=False
    )
    
    # Ensure imaging columns exist on final MS
    if not add_imaging_columns:
        try:
            from casacore.tables import addImagingColumns as _addImCols
            _addImCols(os.fspath(ms_out))
        except Exception:
            pass
        
        try:
            from dsa110_contimg.conversion.uvh5_to_ms import _ensure_imaging_columns_populated as _fill_cols
            _fill_cols(os.fspath(ms_out))
        except Exception:
            pass
    
    # Configure final MS for imaging (some workflows need this)
    if configure_final_ms:
        try:
            from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
            configure_ms_for_imaging(os.fspath(ms_out))
        except Exception:
            pass
    
    # Cleanup intermediate parts
    try:
        shutil.rmtree(part_base, ignore_errors=True)
    except Exception:
        pass


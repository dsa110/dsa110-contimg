"""
Direct MS writer for DSA-110 subband UVH5 files.

This strategy creates per-subband MS files in parallel and then concatenates
them into a single multi-SPW Measurement Set.
"""

import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from .base import MSWriter
from dsa110_contimg.conversion.helpers import (
    set_antenna_positions,
    _ensure_antenna_diameters,
    get_meridian_coords,
    compute_and_set_uvw,
)

if TYPE_CHECKING:
    from pyuvdata import UVData


class DirectSubbandWriter(MSWriter):
    """Writes an MS by creating and concatenating per-subband parts."""

    def __init__(self, uv: "UVData", ms_path: str, **kwargs: Any) -> None:
        super().__init__(uv, ms_path, **kwargs)
        self.file_list: List[str] = self.kwargs.get("file_list", [])
        if not self.file_list:
            raise ValueError(
                "DirectSubbandWriter requires 'file_list' in kwargs.")
        self.scratch_dir: Optional[str] = self.kwargs.get("scratch_dir")
        self.max_workers: int = self.kwargs.get("max_workers", 4)

    def get_files_to_process(self) -> Optional[List[str]]:
        return self.file_list

    def write(self) -> str:
        """Execute the parallel subband write and concatenation."""
        from casatasks import concat as casa_concat
        from concurrent.futures import ProcessPoolExecutor, as_completed

        ms_stage_path = self.ms_path
        part_base = Path(self.scratch_dir or Path(
            ms_stage_path).parent) / Path(ms_stage_path).stem
        part_base.mkdir(parents=True, exist_ok=True)

        # Use processes, not threads: casatools/casacore are not thread-safe
        # for concurrent Simulator usage.
        futures = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as ex:
            for idx, sb_file in enumerate(sorted(self.file_list)):
                part_out = part_base / \
                    f"{Path(ms_stage_path).stem}.sb{idx:02d}.ms"
                futures.append(
                    ex.submit(
                        _write_ms_subband_part,
                        sb_file,
                        str(part_out)))

            parts = []
            for i, future in enumerate(as_completed(futures)):
                try:
                    parts.append(future.result())
                    if (i + 1) % 4 == 0 or (i + 1) == len(futures):
                        print(
                            f"Per-subband writes completed: {i + 1}/{len(futures)}")
                except Exception as e:
                    raise RuntimeError(f"A subband writer process failed: {e}")

        # Concatenate parts into the final MS
        print(f"Concatenating {len(parts)} parts into {ms_stage_path}")
        casa_concat(
            vis=sorted(parts),
            concatvis=ms_stage_path,
            copypointing=False)

        # Clean up temporary per-subband Measurement Sets.
        try:
            for part in parts:
                shutil.rmtree(part, ignore_errors=True)
            shutil.rmtree(part_base, ignore_errors=True)
        except Exception as cleanup_err:
            print(f"Warning: failed to clean subband parts: {cleanup_err}")

        return "direct-subband"


def _write_ms_subband_part(subband_file: str, part_out: str) -> str:
    """
    Write a single-subband MS using pyuvdata.write_ms.

    This is a top-level function to be safely used with multiprocessing.
    """
    from pyuvdata import UVData
    from astropy.time import Time
    import numpy as np
    import astropy.units as u

    uv = UVData()
    uv.read(
        subband_file,
        file_type="uvh5",
        run_check=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        check_extra=False,
    )

    part_out_path = Path(part_out)
    if part_out_path.exists():
        shutil.rmtree(part_out_path, ignore_errors=True)
    part_out_path.parent.mkdir(parents=True, exist_ok=True)

    # Reorder freqs ascending to keep CASA concat happy
    uv.reorder_freqs(channel_order="freq", run_check=False)

    # Set antenna metadata
    set_antenna_positions(uv)
    _ensure_antenna_diameters(uv)

    # Create a single ICRS phase center for the subband
    pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
    t_mid = Time(float(np.mean(uv.time_array)), format="jd").mjd
    ra_icrs, dec_icrs = get_meridian_coords(pt_dec, t_mid)
    uv.phase_center_catalog = {}
    pc_id = uv._add_phase_center(
        cat_name=os.path.basename(part_out_path),
        cat_type="sidereal",
        cat_lon=float(ra_icrs.to_value(u.rad)),
        cat_lat=float(dec_icrs.to_value(u.rad)),
        cat_frame="icrs",
        cat_epoch=2000.0,
    )
    if not hasattr(
            uv,
            "phase_center_id_array") or uv.phase_center_id_array is None:
        uv.phase_center_id_array = np.zeros(uv.Nblts, dtype=int)
    uv.phase_center_id_array[:] = pc_id
    uv.phase_type = "phased"
    uv.phase_center_frame = "icrs"
    uv.phase_center_epoch = 2000.0

    # Recompute UVW using pyuvdata utilities (meridian phasing)
    compute_and_set_uvw(uv, pt_dec)

    # Write the single-subband MS
    uv.write_ms(
        str(part_out_path),
        clobber=True,
        run_check=False,
        check_extra=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        check_autos=False,
        fix_autos=False,
    )
    return str(part_out_path)


def write_ms_from_subbands(file_list, ms_path, scratch_dir=None):
    """Write MS from subband files using direct subband approach.
    
    This function creates per-subband MS files and then concatenates them.
    
    Args:
        file_list: List of subband file paths
        ms_path: Output MS path
        scratch_dir: Optional scratch directory for intermediate files
        
    Returns:
        str: Writer type used
    """
    from casatasks import concat as casa_concat
    import os
    from pathlib import Path
    
    ms_stage_path = ms_path
    part_base = Path(scratch_dir or Path(ms_stage_path).parent) / Path(ms_stage_path).stem
    part_base.mkdir(parents=True, exist_ok=True)
    
    # Create per-subband MS files
    parts = []
    for idx, sb in enumerate(sorted(file_list)):
        part_out = part_base / f"{Path(ms_stage_path).stem}.sb{idx:02d}.ms"
        try:
            result = _write_ms_subband_part(sb, str(part_out))
            parts.append(result)
        except Exception as e:
            print(f"Failed to write subband {idx}: {e}")
            continue
    
    if not parts:
        raise RuntimeError("No subband MS files were created successfully")
    
    # Concatenate parts into the final MS
    print(f"Concatenating {len(parts)} parts into {ms_stage_path}")
    casa_concat(
        vis=sorted(parts),
        concatvis=ms_stage_path,
        copypointing=False)

    # Clean up the temporary per-subband Measurement Sets.
    try:
        for part in parts:
            shutil.rmtree(part, ignore_errors=True)
        shutil.rmtree(part_base, ignore_errors=True)
    except Exception as cleanup_err:
        print(f"Warning: failed to clean subband parts: {cleanup_err}")

    return "direct-subband"

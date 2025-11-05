"""
Parallel MS writer for DSA-110 subband UVH5 files.

This strategy creates per-subband MS files in parallel, concatenates them,
and then merges all SPWs into a single SPW Measurement Set.
"""

import os
import shutil
import time
import uuid
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

import numpy as np
import astropy.units as u
from astropy.time import Time

logger = logging.getLogger(__name__)

from .base import MSWriter
from dsa110_contimg.conversion.helpers import (
    set_antenna_positions,
    _ensure_antenna_diameters,
    get_meridian_coords,
    compute_and_set_uvw,
    set_telescope_identity,
)

if TYPE_CHECKING:
    from pyuvdata import UVData


class DirectSubbandWriter(MSWriter):
    """Writes an MS by creating and concatenating per-subband parts, optionally merging SPWs.
    
    This writer creates per-subband MS files in parallel, concatenates them into
    a multi-SPW MS, and optionally merges all SPWs into a single SPW.
    
    Note: By default, SPW merging is disabled (merge_spws=False) to avoid
    mstransform incompatibility with CASA gaincal. Calibration should be performed
    on the multi-SPW MS before merging if needed.
    """

    def __init__(self, uv: "UVData", ms_path: str, **kwargs: Any) -> None:
        super().__init__(uv, ms_path, **kwargs)
        self.file_list: List[str] = self.kwargs.get("file_list", [])
        if not self.file_list:
            raise ValueError(
                "DirectSubbandWriter requires 'file_list' in kwargs.")
        self.scratch_dir: Optional[str] = self.kwargs.get("scratch_dir")
        self.max_workers: int = self.kwargs.get("max_workers", 4)
        # Optional tmpfs staging
        self.stage_to_tmpfs: bool = bool(
            self.kwargs.get("stage_to_tmpfs", False)
        )
        self.tmpfs_path: str = str(self.kwargs.get("tmpfs_path", "/dev/shm"))
        # Optional: disable SPW merging (for backward compatibility)
        # Default: False (don't merge) to avoid mstransform incompatibility with gaincal
        self.merge_spws: bool = bool(
            self.kwargs.get("merge_spws", False)  # Default: don't merge SPWs
        )
        # Optional: control SIGMA_SPECTRUM removal after merge
        self.remove_sigma_spectrum: bool = bool(
            self.kwargs.get("remove_sigma_spectrum", True)  # Default: remove to save space
        )

    def get_files_to_process(self) -> Optional[List[str]]:
        return self.file_list

    def write(self) -> str:
        """Execute the parallel subband write and concatenation."""
        from casatasks import concat as casa_concat
        from concurrent.futures import ProcessPoolExecutor, as_completed

        # Determine staging locations
        ms_final_path = Path(self.ms_path)
        ms_stage_path = ms_final_path

        # Decide whether to use tmpfs for staging
        use_tmpfs = False
        tmpfs_root = Path(self.tmpfs_path)
        if self.stage_to_tmpfs and tmpfs_root.is_dir():
            # PRECONDITION CHECK: Validate tmpfs is writable before staging
            # This ensures we follow "measure twice, cut once" - establish requirements upfront
            # before expensive staging operations.
            if not os.access(str(tmpfs_root), os.W_OK):
                logger.warning(
                    f"Tmpfs staging directory is not writable: {self.tmpfs_path}. "
                    f"Falling back to scratch directory."
                )
                use_tmpfs = False
            else:
                try:
                    # Rough size estimate: sum of input subband sizes × 2 margin
                    est_needed = 0
                    for p in self.file_list:
                        try:
                            est_needed += max(0, os.path.getsize(p))
                        except Exception:
                            pass
                    est_needed = int(est_needed * 2.0)
                    du = shutil.disk_usage(str(tmpfs_root))
                    free_bytes = int(du.free)
                    if free_bytes > est_needed:
                        use_tmpfs = True
                except Exception:
                    use_tmpfs = False

        if use_tmpfs:
            # Stage parts and final concat under tmpfs
            # Solution 2: Use unique identifier to avoid conflicts between groups
            unique_id = f"{ms_final_path.stem}_{uuid.uuid4().hex[:8]}"
            part_base = tmpfs_root / "dsa110-contimg" / unique_id
            part_base.mkdir(parents=True, exist_ok=True)
            ms_stage_path = part_base.parent / (
                ms_final_path.stem + ".staged.ms"
            )
        else:
            # Use provided scratch or output directory parent
            part_base = Path(
                self.scratch_dir or ms_final_path.parent
            ) / ms_final_path.stem
        part_base.mkdir(parents=True, exist_ok=True)

        # Compute single phase center for entire group to ensure phase coherence
        # This prevents phase discontinuities when subbands are concatenated
        group_phase_ra = None
        group_phase_dec = None
        group_pt_dec = None
        
        try:
            # Calculate group midpoint time by averaging all subband midpoints
            mid_times = []
            for sb_file in self.file_list:
                try:
                    # Use lightweight peek to get midpoint time without full read
                    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                        _peek_uvh5_phase_and_midtime
                    )
                    _, pt_dec, mid_mjd = _peek_uvh5_phase_and_midtime(sb_file)
                    if group_pt_dec is None:
                        group_pt_dec = pt_dec
                    if np.isfinite(mid_mjd) and mid_mjd > 0:
                        mid_times.append(mid_mjd)
                except Exception:
                    # Fallback: read first file fully if peek fails
                    if group_phase_ra is None:
                        try:
                            from pyuvdata import UVData
                            temp_uv = UVData()
                            temp_uv.read(
                                sb_file,
                                file_type='uvh5',
                                read_data=False,
                                run_check=False,
                                check_extra=False,
                                run_check_acceptability=False,
                                strict_uvw_antpos_check=False,
                            )
                            if group_pt_dec is None:
                                group_pt_dec = temp_uv.extra_keywords.get(
                                    "phase_center_dec", 0.0) * u.rad
                            mid_mjd = Time(
                                float(np.mean(temp_uv.time_array)),
                                format="jd"
                            ).mjd
                            mid_times.append(mid_mjd)
                            del temp_uv
                        except Exception:
                            pass
            
            if group_pt_dec is not None and len(mid_times) > 0:
                # Compute group midpoint time (average of all subband midpoints)
                group_mid_mjd = float(np.mean(mid_times))
                
                # Compute shared phase center coordinates at group midpoint
                group_phase_ra, group_phase_dec = get_meridian_coords(
                    group_pt_dec, group_mid_mjd
                )
                print(
                    f"Computed shared phase center for group: "
                    f"RA={group_phase_ra.to(u.deg).value:.6f}°, "
                    f"Dec={group_phase_dec.to(u.deg).value:.6f}° "
                    f"(MJD={group_mid_mjd:.6f})"
                )
        except Exception as e:
            print(f"Warning: Failed to compute shared phase center: {e}")
            print("Falling back to per-subband phase center calculation")
            group_phase_ra = None
            group_phase_dec = None
            group_pt_dec = None

        # Use processes, not threads: casatools/casacore are not thread-safe
        # for concurrent Simulator usage.
        # CRITICAL: DSA-110 subbands use DESCENDING frequency order:
        #   sb00 = highest frequency (~1498 MHz)
        #   sb15 = lowest frequency (~1311 MHz)
        # For MFS imaging, we need ASCENDING frequency order (low to high).
        # Therefore, we must REVERSE the subband number sort.
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import _extract_subband_code
        def sort_by_subband(fpath):
            fname = os.path.basename(fpath)
            sb = _extract_subband_code(fname)
            sb_num = int(sb.replace('sb', '')) if sb else 999
            return sb_num
        
        # CRITICAL: Sort in REVERSE subband order (15, 14, ..., 1, 0) to get
        # ascending frequency order (lowest to highest) for proper MFS imaging
        # and bandpass calibration. If frequencies are out of order, imaging will
        # produce fringes and bandpass calibration will fail.
        sorted_files = sorted(self.file_list, key=sort_by_subband, reverse=True)
        
        futures = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as ex:
            for idx, sb_file in enumerate(sorted_files):
                part_out = (
                    part_base / f"{Path(ms_stage_path).stem}.sb{idx:02d}.ms"
                )
                futures.append((
                    idx,
                    ex.submit(
                        _write_ms_subband_part,
                        sb_file,
                        str(part_out),
                        group_phase_ra,  # Pass shared phase center
                        group_phase_dec,
                        group_pt_dec)
                ))

        # Collect results in order (idx 0, 1, 2, ..., 15) to maintain spectral order
        parts = [None] * len(futures)
        completed = 0
        for future in as_completed([f for _, f in futures]):
            try:
                result = future.result()
                # Find which idx this future corresponds to
                for orig_idx, orig_future in futures:
                    if orig_future == future:
                        parts[orig_idx] = result
                        completed += 1
                        break
                if completed % 4 == 0 or completed == len(futures):
                    msg = (
                        f"Per-subband writes completed: {completed}/"
                        f"{len(futures)}"
                    )
                    print(msg)
            except Exception as e:
                raise RuntimeError(
                    f"A subband writer process failed: {e}"
                )
        
        # Remove None entries (shouldn't happen, but safety check)
        parts = [p for p in parts if p is not None]

        # Solution 4: Ensure subband write processes fully terminate before concat
        # Allow processes to fully terminate and release file handles
        time.sleep(0.5)

        # Solution 3: Retry logic for concat failures
        # Concatenate parts into the final MS with retry on file locking errors
        print(
            f"Concatenating {len(parts)} parts into {ms_stage_path}"
        )
        max_retries = 2
        concat_success = False
        for attempt in range(max_retries):
            try:
                # CRITICAL: Parts are already in correct subband order (0-15)
                # Do NOT sort here - parts are already ordered by subband number
                # from the futures collection above. Sorting would break spectral order.
                casa_concat(
                    vis=parts,  # Already in correct subband order
                    concatvis=str(ms_stage_path),
                    copypointing=False)
                concat_success = True
                break
            except RuntimeError as e:
                error_msg = str(e)
                if ("cannot be opened" in error_msg or 
                    "readBlock" in error_msg or 
                    "read/write" in error_msg):
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Concat failed (attempt {attempt + 1}/{max_retries}), "
                            f"retrying after cleanup: {e}"
                        )
                        # Cleanup and retry
                        for part in parts:
                            try:
                                shutil.rmtree(part, ignore_errors=True)
                            except Exception:
                                pass
                        time.sleep(1.0)
                        continue
                raise
        
        if not concat_success:
            raise RuntimeError("Concat failed after all retry attempts")

        # Solution 1: Explicit cleanup verification after concat
        # Close any CASA handles that might still be open
        try:
            import casatools
            ms_tool = casatools.ms()
            try:
                ms_tool.close()
            except Exception:
                pass
        except ImportError:
            pass

        # If staged on tmpfs, move final MS atomically (or via copy on
        # cross-device)
        if use_tmpfs:
            try:
                # Ensure destination parent exists
                ms_final_path.parent.mkdir(parents=True, exist_ok=True)
                src_path = str(ms_stage_path)
                dst_path = str(ms_final_path)
                shutil.move(src_path, dst_path)
                ms_stage_path = ms_final_path
                print(
                    f"Moved staged MS to final location: {ms_final_path}"
                )
            except Exception:
                # If move failed, try copytree (for directory MS)
                if ms_final_path.exists():
                    shutil.rmtree(ms_final_path, ignore_errors=True)
                src_path = str(ms_stage_path)
                dst_path = str(ms_final_path)
                shutil.copytree(src_path, dst_path)
                shutil.rmtree(ms_stage_path, ignore_errors=True)
                ms_stage_path = ms_final_path
                print(
                    f"Copied staged MS to final location: {ms_final_path}"
                )

        # Merge SPWs into a single SPW if requested
        if self.merge_spws:
            try:
                from dsa110_contimg.conversion.merge_spws import merge_spws, get_spw_count
                
                n_spw_before = get_spw_count(str(ms_stage_path))
                if n_spw_before and n_spw_before > 1:
                    print(f"Merging {n_spw_before} SPWs into a single SPW...")
                    ms_multi_spw = str(ms_stage_path)
                    ms_single_spw = str(ms_stage_path) + ".merged"
                    
                    merge_spws(
                        ms_in=ms_multi_spw,
                        ms_out=ms_single_spw,
                        datacolumn="DATA",
                        regridms=True,
                        keepflags=True,
                        remove_sigma_spectrum=self.remove_sigma_spectrum,
                    )
                    
                    # Replace multi-SPW MS with single-SPW MS
                    shutil.rmtree(ms_multi_spw, ignore_errors=True)
                    shutil.move(ms_single_spw, ms_multi_spw)
                    
                    n_spw_after = get_spw_count(str(ms_stage_path))
                    if n_spw_after == 1:
                        print(f"✓ Successfully merged SPWs: {n_spw_before} → 1")
                    else:
                        print(f"⚠ Warning: Expected 1 SPW after merge, got {n_spw_after}")
            except Exception as merge_err:
                print(f"Warning: SPW merging failed (non-fatal): {merge_err}")
                import traceback
                traceback.print_exc()

        # Solution 1: Clean up temporary per-subband Measurement Sets and staging dir
        # with verification that cleanup completed
        cleanup_attempts = 0
        max_cleanup_attempts = 3
        while cleanup_attempts < max_cleanup_attempts:
            try:
                for part in parts:
                    if Path(part).exists():
                        shutil.rmtree(part, ignore_errors=True)
                if part_base.exists():
                    shutil.rmtree(part_base, ignore_errors=True)
                
                # Verify cleanup completed
                if part_base.exists():
                    cleanup_attempts += 1
                    if cleanup_attempts < max_cleanup_attempts:
                        logger.warning(
                            f"Cleanup incomplete (attempt {cleanup_attempts}), "
                            f"retrying: {part_base}"
                        )
                        time.sleep(0.5)
                        continue
                    else:
                        logger.warning(
                            f"Cleanup incomplete after {max_cleanup_attempts} attempts: "
                            f"{part_base}"
                        )
                break
            except Exception as cleanup_err:
                cleanup_attempts += 1
                if cleanup_attempts < max_cleanup_attempts:
                    logger.warning(
                        f"Cleanup failed (attempt {cleanup_attempts}), retrying: {cleanup_err}"
                    )
                    time.sleep(0.5)
                else:
                    logger.warning(
                        f"Failed to clean subband parts after {max_cleanup_attempts} attempts: "
                        f"{cleanup_err}"
                    )

        return "parallel-subband"


def _write_ms_subband_part(
    subband_file: str,
    part_out: str,
    shared_phase_ra: Optional[u.Quantity] = None,
    shared_phase_dec: Optional[u.Quantity] = None,
    shared_pt_dec: Optional[u.Quantity] = None,
) -> str:
    """
    Write a single-subband MS using pyuvdata.write_ms.

    This is a top-level function to be safely used with multiprocessing.

    Args:
        subband_file: Path to input UVH5 subband file
        part_out: Path to output MS file
        shared_phase_ra: Optional shared phase center RA (for phase coherence)
        shared_phase_dec: Optional shared phase center Dec (for phase coherence)
        shared_pt_dec: Optional shared pointing declination (for UVW computation)

    Returns:
        Path to created MS file
    """
    from pyuvdata import UVData
    from astropy.time import Time

    uv = UVData()
    uv.read(
        subband_file,
        file_type="uvh5",
        run_check=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        check_extra=False,
    )

    # Stamp telescope identity prior to phasing/UVW
    try:
        set_telescope_identity(
            uv,
            os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110"),
            -118.2817,
            37.2314,
            1222.0,
        )
    except Exception:
        pass

    part_out_path = Path(part_out)
    if part_out_path.exists():
        shutil.rmtree(part_out_path, ignore_errors=True)
    part_out_path.parent.mkdir(parents=True, exist_ok=True)

    # Reorder freqs ascending to keep CASA concat happy
    uv.reorder_freqs(channel_order="freq", run_check=False)

    # Set antenna metadata
    set_antenna_positions(uv)
    _ensure_antenna_diameters(uv)

    # Use shared phase center if provided (for phase coherence across subbands),
    # otherwise compute per-subband (fallback for backward compatibility)
    if shared_phase_ra is not None and shared_phase_dec is not None:
        # Use shared phase center coordinates
        ra_icrs = shared_phase_ra
        dec_icrs = shared_phase_dec
        pt_dec = shared_pt_dec if shared_pt_dec is not None else uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
        phase_center_name = "meridian_icrs"  # Same name for all subbands
    else:
        # Fallback: compute per-subband phase center (old behavior)
        pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
        t_mid = Time(float(np.mean(uv.time_array)), format="jd").mjd
        ra_icrs, dec_icrs = get_meridian_coords(pt_dec, t_mid)
        phase_center_name = os.path.basename(part_out_path)  # Unique per subband

    # Set phase center catalog with shared or per-subband coordinates
    uv.phase_center_catalog = {}
    pc_id = uv._add_phase_center(
        cat_name=phase_center_name,
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
    # UVW computation uses actual observation times, so it's correct even with
    # shared phase center metadata
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
    import numpy as np

    ms_stage_path = ms_path
    part_base = Path(
        scratch_dir or Path(ms_stage_path).parent
    ) / Path(ms_stage_path).stem
    part_base.mkdir(parents=True, exist_ok=True)

    # Compute single phase center for entire group to ensure phase coherence
    group_phase_ra = None
    group_phase_dec = None
    group_pt_dec = None
    
    try:
        # Calculate group midpoint time by averaging all subband midpoints
        mid_times = []
        for sb_file in file_list:
            try:
                from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                    _peek_uvh5_phase_and_midtime
                )
                _, pt_dec, mid_mjd = _peek_uvh5_phase_and_midtime(sb_file)
                if group_pt_dec is None:
                    group_pt_dec = pt_dec
                if np.isfinite(mid_mjd) and mid_mjd > 0:
                    mid_times.append(mid_mjd)
            except Exception:
                # Fallback: read file fully if peek fails
                try:
                    from pyuvdata import UVData
                    temp_uv = UVData()
                    temp_uv.read(
                        sb_file,
                        file_type='uvh5',
                        read_data=False,
                        run_check=False,
                        check_extra=False,
                        run_check_acceptability=False,
                        strict_uvw_antpos_check=False,
                    )
                    if group_pt_dec is None:
                        group_pt_dec = temp_uv.extra_keywords.get(
                            "phase_center_dec", 0.0) * u.rad
                    mid_mjd = Time(
                        float(np.mean(temp_uv.time_array)),
                        format="jd"
                    ).mjd
                    if np.isfinite(mid_mjd) and mid_mjd > 0:
                        mid_times.append(mid_mjd)
                    del temp_uv
                except Exception:
                    pass
        
        if group_pt_dec is not None and len(mid_times) > 0:
            group_mid_mjd = float(np.mean(mid_times))
            group_phase_ra, group_phase_dec = get_meridian_coords(
                group_pt_dec, group_mid_mjd
            )
            print(
                f"Computed shared phase center for group: "
                f"RA={group_phase_ra.to(u.deg).value:.6f}°, "
                f"Dec={group_phase_dec.to(u.deg).value:.6f}° "
                f"(MJD={group_mid_mjd:.6f})"
            )
    except Exception:
        # Fallback: per-subband phase centers
        pass

    # Create per-subband MS files
    # CRITICAL: DSA-110 subbands use DESCENDING frequency order (sb00=highest, sb15=lowest).
    # For MFS imaging, we need ASCENDING frequency order, so REVERSE the sort.
    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import _extract_subband_code
    def sort_by_subband(fpath):
        fname = os.path.basename(fpath)
        sb = _extract_subband_code(fname)
        sb_num = int(sb.replace('sb', '')) if sb else 999
        return sb_num
    
    parts = []
    for idx, sb in enumerate(sorted(file_list, key=sort_by_subband, reverse=True)):
        part_out = part_base / f"{Path(ms_stage_path).stem}.sb{idx:02d}.ms"
        try:
            result = _write_ms_subband_part(
                sb, str(part_out),
                group_phase_ra,  # Pass shared phase center
                group_phase_dec,
                group_pt_dec
            )
            parts.append(result)
        except Exception as e:
            print(f"Failed to write subband {idx}: {e}")
            continue

    if not parts:
        raise RuntimeError("No subband MS files were created successfully")

    # Concatenate parts into the final MS
    # CRITICAL: Parts are already in correct subband order (0-15) from the sorted
    # file_list iteration above. Do NOT sort here - sorting would break spectral order
    # and cause frequency channels to be scrambled, leading to incorrect bandpass calibration.
    print(
        f"Concatenating {len(parts)} parts into {ms_stage_path}"
    )
    casa_concat(
        vis=parts,  # Already in correct subband order
        concatvis=ms_stage_path,
        copypointing=False)

    # Clean up the temporary per-subband Measurement Sets.
    try:
        for part in parts:
            shutil.rmtree(part, ignore_errors=True)
        shutil.rmtree(part_base, ignore_errors=True)
    except Exception as cleanup_err:
        print(f"Warning: failed to clean subband parts: {cleanup_err}")

    return "parallel-subband"

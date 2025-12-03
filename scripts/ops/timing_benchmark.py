#!/usr/bin/env python3
"""
DSA-110 Pipeline Timing Benchmark

This script performs detailed timing analysis of each pipeline stage using the
ACTUAL pipeline functions (not standalone reimplementations). This ensures
timing reflects real-world behavior including:
- Precondition validation (MODEL_DATA checks)
- Caltable quality checks
- Provenance tracking
- Error handling overhead

Usage:
    conda activate casa6
    python scripts/ops/timing_benchmark.py --ms /path/to/test.ms --output timing_results.json

    # Or test full pipeline from HDF5:
    python scripts/ops/timing_benchmark.py --hdf5-dir /data/incoming --timestamp "2025-10-02T00:12:00" --output timing_results.json
"""

import argparse
import gc
import json
import logging
import os
import resource
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class TimingResult:
    """Result from a single timed operation."""

    operation: str
    wall_time_s: float
    cpu_user_s: float
    cpu_system_s: float
    memory_peak_mb: float
    success: bool
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def cpu_total_s(self) -> float:
        return self.cpu_user_s + self.cpu_system_s

    @property
    def io_wait_s(self) -> float:
        """Estimated I/O wait = wall time - CPU time (rough approximation)."""
        return max(0, self.wall_time_s - self.cpu_total_s)

    @property
    def io_fraction(self) -> float:
        """Fraction of time spent waiting for I/O."""
        if self.wall_time_s == 0:
            return 0
        return self.io_wait_s / self.wall_time_s


class TimingContext:
    """Context manager for timing operations with resource tracking."""

    def __init__(self, operation_name: str):
        self.operation = operation_name
        self.start_wall = 0.0
        self.start_rusage = None
        self.result: Optional[TimingResult] = None

    def __enter__(self):
        gc.collect()  # Clean up before measurement
        self.start_wall = time.perf_counter()
        self.start_rusage = resource.getrusage(resource.RUSAGE_SELF)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_wall = time.perf_counter()
        end_rusage = resource.getrusage(resource.RUSAGE_SELF)

        wall_time = end_wall - self.start_wall
        cpu_user = end_rusage.ru_utime - self.start_rusage.ru_utime
        cpu_system = end_rusage.ru_stime - self.start_rusage.ru_stime
        memory_peak = end_rusage.ru_maxrss / 1024  # Convert KB to MB

        self.result = TimingResult(
            operation=self.operation,
            wall_time_s=wall_time,
            cpu_user_s=cpu_user,
            cpu_system_s=cpu_system,
            memory_peak_mb=memory_peak,
            success=exc_type is None,
            error=str(exc_val) if exc_val else None,
        )

        return False  # Don't suppress exceptions


def format_time(seconds: float) -> str:
    """Format seconds as human-readable string."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def print_result(result: TimingResult):
    """Print a timing result in a readable format."""
    status = ":check:" if result.success else ":cross:"
    io_pct = result.io_fraction * 100

    logger.info(
        f"{status} {result.operation}: "
        f"wall={format_time(result.wall_time_s)}, "
        f"cpu={format_time(result.cpu_total_s)}, "
        f"io_wait={format_time(result.io_wait_s)} ({io_pct:.0f}%), "
        f"mem={result.memory_peak_mb:.0f}MB"
    )

    if result.error:
        logger.error(f"  Error: {result.error}")


# =============================================================================
# STAGE 1: HDF5 LOADING
# =============================================================================


def time_hdf5_loading(hdf5_files: List[Path]) -> List[TimingResult]:
    """Time HDF5 file loading operations."""
    results = []

    # Import pyuvdata
    with TimingContext("import_pyuvdata") as ctx:
        from pyuvdata import UVData
    results.append(ctx.result)
    print_result(ctx.result)

    # Load single subband
    if hdf5_files:
        with TimingContext("load_single_subband") as ctx:
            uv = UVData()
            uv.read(str(hdf5_files[0]), file_type="uvh5")
            ctx.result.details["nblts"] = uv.Nblts
            ctx.result.details["nfreqs"] = uv.Nfreqs
            ctx.result.details["file_size_mb"] = hdf5_files[0].stat().st_size / 1e6
        results.append(ctx.result)
        print_result(ctx.result)

        # Load all subbands and combine
        if len(hdf5_files) > 1:
            with TimingContext(f"load_combine_{len(hdf5_files)}_subbands") as ctx:
                uv_combined = UVData()
                uv_combined.read(str(hdf5_files[0]), file_type="uvh5")
                for f in hdf5_files[1:]:
                    uv_next = UVData()
                    uv_next.read(str(f), file_type="uvh5")
                    uv_combined += uv_next
                ctx.result.details["total_nfreqs"] = uv_combined.Nfreqs
                ctx.result.details["num_files"] = len(hdf5_files)
            results.append(ctx.result)
            print_result(ctx.result)

    return results


# =============================================================================
# STAGE 2: MS WRITING
# =============================================================================


def time_ms_writing(uv_data, output_path: Path) -> List[TimingResult]:
    """Time MS writing operations."""
    results = []

    with TimingContext("write_ms_pyuvdata") as ctx:
        uv_data.write_ms(str(output_path), clobber=True)
        ctx.result.details["output_size_mb"] = sum(
            f.stat().st_size for f in output_path.rglob("*") if f.is_file()
        ) / 1e6
    results.append(ctx.result)
    print_result(ctx.result)

    return results


# =============================================================================
# STAGE 3: CALIBRATION
# =============================================================================


def time_calibration(ms_path: Path) -> List[TimingResult]:
    """Time calibration operations using ACTUAL PIPELINE FUNCTIONS.

    This uses the real dsa110_contimg.calibration functions which include:
    - MODEL_DATA precondition validation
    - Caltable quality checks
    - Reference antenna validation
    - Provenance tracking
    - Error handling and logging

    This gives accurate timing for production workloads.
    """
    results = []

    # Import pipeline calibration functions (NOT standalone CASA tasks)
    with TimingContext("import_pipeline_calibration") as ctx:
        from dsa110_contimg.calibration.calibration import (
            solve_bandpass,
            solve_delay,
            solve_gains,
        )
        from dsa110_contimg.calibration.flagging import (
            flag_rfi,
            flag_zeros,
            reset_flags,
        )
        from dsa110_contimg.calibration.selection import select_bandpass_from_catalog
        from dsa110_contimg.calibration.model import populate_model_from_catalog
    results.append(ctx.result)
    print_result(ctx.result)

    ms_str = str(ms_path)
    caltable_dir = ms_path.parent / f"{ms_path.stem}_caltables_timing"
    caltable_dir.mkdir(exist_ok=True)

    # Get field info using casacore
    with TimingContext("get_ms_metadata") as ctx:
        import casacore.tables as ct
        with ct.table(f"{ms_str}/FIELD", readonly=True) as t:
            field_names = t.getcol("NAME")
        with ct.table(ms_str, readonly=True) as t:
            n_rows = t.nrows()
    ctx.result.details["n_fields"] = len(field_names)
    ctx.result.details["n_rows"] = n_rows
    results.append(ctx.result)
    print_result(ctx.result)

    # Step 1: Automatic calibrator/field selection (pipeline function)
    # This simulates what --auto-fields does
    cal_field = "0"  # Default fallback
    peak_field_idx = None
    with TimingContext("select_calibrator_field") as ctx:
        try:
            # Use pipeline's catalog-based selection
            catalog_db = Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")
            if catalog_db.exists():
                selection = select_bandpass_from_catalog(
                    ms_str,
                    str(catalog_db),
                    search_radius_deg=1.5,
                    bp_window=3,
                )
                if selection and selection.get("field_range"):
                    cal_field = selection["field_range"]
                    peak_field_idx = selection.get("peak_field_idx")
                    ctx.result.details["calibrator"] = selection.get("calibrator_name", "unknown")
                    ctx.result.details["peak_field"] = peak_field_idx
        except Exception as e:
            logger.warning(f"Calibrator selection failed: {e}, using field 0")
    results.append(ctx.result)
    print_result(ctx.result)

    # Step 2: Flagging using pipeline functions
    with TimingContext("pipeline_reset_flags") as ctx:
        try:
            reset_flags(ms_str)
        except Exception as e:
            ctx.result.error = str(e)
    results.append(ctx.result)
    print_result(ctx.result)

    with TimingContext("pipeline_flag_zeros") as ctx:
        try:
            flag_zeros(ms_str)
        except Exception as e:
            ctx.result.error = str(e)
    results.append(ctx.result)
    print_result(ctx.result)

    with TimingContext("pipeline_flag_rfi") as ctx:
        try:
            flag_rfi(ms_str)
        except Exception as e:
            ctx.result.error = str(e)
    results.append(ctx.result)
    print_result(ctx.result)

    # Step 3: MODEL_DATA population (required precondition for calibration)
    with TimingContext("pipeline_populate_model") as ctx:
        try:
            populate_model_from_catalog(ms_str, field=cal_field)
        except Exception as e:
            # Fall back to setjy if populate_model_from_catalog fails
            logger.warning(f"populate_model_from_catalog failed: {e}, trying setjy")
            try:

# --- CASA log directory setup ---
# Ensure CASA logs go to centralized directory, not CWD
import os as _os
try:
    from pathlib import Path as _Path
    _REPO_ROOT = _Path(__file__).resolve().parents[2]
    _sys_path_entry = str(_REPO_ROOT / 'backend' / 'src')
    import sys as _sys
    if _sys_path_entry not in _sys.path:
        _sys.path.insert(0, _sys_path_entry)
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    _os.makedirs(str(_casa_log_dir), exist_ok=True)
    _os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort - CASA logs may go to CWD
# --- End CASA log directory setup ---

                from casatasks import setjy
                setjy(vis=ms_str, field=cal_field, standard="Perley-Butler 2017")
            except Exception as e2:
                ctx.result.error = str(e2)
    results.append(ctx.result)
    print_result(ctx.result)

    # Reference antenna (pipeline uses outrigger-priority selection)
    refant = "103,113,114,106,112"  # DSA-110 default chain

    # Step 4: K-cal (delay) - uses pipeline solve_delay
    # NOTE: K-cal is skipped by default for DSA-110 (connected-element array)
    # We time it anyway to measure full capability
    with TimingContext("pipeline_solve_delay") as ctx:
        try:
            ktabs = solve_delay(
                ms_str,
                cal_field,
                refant,
                table_prefix=str(caltable_dir / "timing"),
                combine_spw=False,
                uvrange="",
                minsnr=3.0,
            )
            ctx.result.details["num_tables"] = len(ktabs) if ktabs else 0
        except Exception as e:
            ctx.result = TimingResult(
                operation="pipeline_solve_delay",
                wall_time_s=0,
                cpu_user_s=0,
                cpu_system_s=0,
                memory_peak_mb=0,
                success=False,
                error=str(e),
            )
    results.append(ctx.result)
    print_result(ctx.result)

    # Step 5: BP-cal (bandpass) - uses pipeline solve_bandpass
    # This includes MODEL_DATA validation, caltable quality checks
    with TimingContext("pipeline_solve_bandpass") as ctx:
        try:
            bptabs = solve_bandpass(
                ms_str,
                cal_field,
                refant,
                None,  # No K-table (DSA-110 default)
                table_prefix=str(caltable_dir / "timing"),
                combine_fields=False,
                combine_spw=False,
                uvrange="",
                minsnr=3.0,
                peak_field_idx=peak_field_idx,
            )
            ctx.result.details["num_tables"] = len(bptabs) if bptabs else 0
        except Exception as e:
            ctx.result = TimingResult(
                operation="pipeline_solve_bandpass",
                wall_time_s=0,
                cpu_user_s=0,
                cpu_system_s=0,
                memory_peak_mb=0,
                success=False,
                error=str(e),
            )
    results.append(ctx.result)
    print_result(ctx.result)

    # Step 6: G-cal (gain) - uses pipeline solve_gains
    # This includes bptable validation, MODEL_DATA checks
    bptabs_for_gains = bptabs if 'bptabs' in dir() and bptabs else []
    with TimingContext("pipeline_solve_gains") as ctx:
        try:
            gtabs = solve_gains(
                ms_str,
                cal_field,
                refant,
                None,  # No K-table
                bptabs_for_gains,
                table_prefix=str(caltable_dir / "timing"),
                combine_fields=False,
                uvrange="",
                minsnr=3.0,
                peak_field_idx=peak_field_idx,
            )
            ctx.result.details["num_tables"] = len(gtabs) if gtabs else 0
        except Exception as e:
            ctx.result = TimingResult(
                operation="pipeline_solve_gains",
                wall_time_s=0,
                cpu_user_s=0,
                cpu_system_s=0,
                memory_peak_mb=0,
                success=False,
                error=str(e),
            )
    results.append(ctx.result)
    print_result(ctx.result)

    # Step 7: Apply calibration using CASA applycal
    with TimingContext("applycal") as ctx:
        try:
            from casatasks import applycal
            gaintables = []
            if 'bptabs' in dir() and bptabs:
                gaintables.extend(bptabs)
            if 'gtabs' in dir() and gtabs:
                gaintables.extend(gtabs)
            if gaintables:
                applycal(
                    vis=ms_str,
                    field="",  # all fields
                    gaintable=gaintables,
                    applymode="calflag",
                )
        except Exception as e:
            ctx.result = TimingResult(
                operation="applycal",
                wall_time_s=0,
                cpu_user_s=0,
                cpu_system_s=0,
                memory_peak_mb=0,
                success=False,
                error=str(e),
            )
    results.append(ctx.result)
    print_result(ctx.result)

    return results


# =============================================================================
# STAGE 4: IMAGING
# =============================================================================


def time_imaging(ms_path: Path, output_dir: Path) -> List[TimingResult]:
    """Time imaging operations."""
    results = []

    import shutil
    import subprocess

    wsclean_cmd = shutil.which("wsclean")
    if not wsclean_cmd:
        logger.warning("wsclean not found in PATH, skipping imaging timing")
        return results

    output_prefix = str(output_dir / "timing_test")

    # Quick dirty image (no CLEAN)
    with TimingContext("wsclean_dirty") as ctx:
        cmd = [
            wsclean_cmd,
            "-name", output_prefix + "_dirty",
            "-size", "2048", "2048",
            "-scale", "5asec",
            "-niter", "0",  # dirty image only
            "-pol", "I",
            "-weight", "briggs", "0",
            str(ms_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        ctx.result.details["returncode"] = proc.returncode
        if proc.returncode != 0:
            ctx.result.error = proc.stderr[:500]
    results.append(ctx.result)
    print_result(ctx.result)

    # CLEAN image (few iterations)
    with TimingContext("wsclean_clean_1000iter") as ctx:
        cmd = [
            wsclean_cmd,
            "-name", output_prefix + "_clean",
            "-size", "2048", "2048",
            "-scale", "5asec",
            "-niter", "1000",
            "-auto-threshold", "3",
            "-pol", "I",
            "-weight", "briggs", "0",
            str(ms_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        ctx.result.details["returncode"] = proc.returncode
        if proc.returncode != 0:
            ctx.result.error = proc.stderr[:500]
    results.append(ctx.result)
    print_result(ctx.result)

    # Full-size image with IDG if GPU available
    with TimingContext("wsclean_4200_idg") as ctx:
        cmd = [
            wsclean_cmd,
            "-name", output_prefix + "_full",
            "-size", "4200", "4200",
            "-scale", "3asec",
            "-niter", "0",  # dirty only for timing
            "-pol", "I",
            "-weight", "briggs", "0",
            "-gridder", "idg",
            "-idg-mode", "hybrid",
            str(ms_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        ctx.result.details["returncode"] = proc.returncode
        if proc.returncode != 0:
            # Try without IDG
            ctx.result.details["idg_failed"] = True
            ctx.result.error = "IDG failed, would retry with wgridder"
    results.append(ctx.result)
    print_result(ctx.result)

    return results


# =============================================================================
# STAGE 5: PHOTOMETRY
# =============================================================================


def time_photometry(fits_path: Path) -> List[TimingResult]:
    """Time forced photometry operations."""
    results = []

    if not fits_path.exists():
        logger.warning(f"FITS file not found: {fits_path}, skipping photometry timing")
        return results

    with TimingContext("import_photometry") as ctx:
        from dsa110_contimg.photometry.forced import measure_forced_peak
        from astropy.io import fits
        from astropy.wcs import WCS
    results.append(ctx.result)
    print_result(ctx.result)

    with TimingContext("read_fits_header") as ctx:
        with fits.open(fits_path) as hdul:
            header = hdul[0].header
            data = hdul[0].data
            wcs = WCS(header, naxis=2)
            ctx.result.details["shape"] = list(data.shape) if data is not None else None
    results.append(ctx.result)
    print_result(ctx.result)

    # Measure at image center
    if data is not None:
        ra_center = header.get("CRVAL1", 0)
        dec_center = header.get("CRVAL2", 0)

        with TimingContext("forced_photometry_single") as ctx:
            try:
                result = measure_forced_peak(
                    fits_path=fits_path,
                    ra_deg=ra_center,
                    dec_deg=dec_center,
                )
                ctx.result.details["peak_jyb"] = result.peak_jyb if result else None
            except Exception as e:
                ctx.result.error = str(e)
        results.append(ctx.result)
        print_result(ctx.result)

        # Batch photometry (10 positions)
        with TimingContext("forced_photometry_batch_10") as ctx:
            try:
                for i in range(10):
                    offset = i * 0.01  # small offset
                    measure_forced_peak(
                        fits_path=fits_path,
                        ra_deg=ra_center + offset,
                        dec_deg=dec_center + offset,
                    )
            except Exception as e:
                ctx.result.error = str(e)
        results.append(ctx.result)
        print_result(ctx.result)

    return results


# =============================================================================
# MAIN
# =============================================================================


def run_benchmark(
    ms_path: Optional[Path] = None,
    hdf5_dir: Optional[Path] = None,
    timestamp: Optional[str] = None,
    output_file: Optional[Path] = None,
    skip_imaging: bool = False,
) -> Dict[str, Any]:
    """Run full benchmark suite."""

    all_results: List[TimingResult] = []
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stages": {},
    }

    logger.info("=" * 60)
    logger.info("DSA-110 Pipeline Timing Benchmark")
    logger.info("=" * 60)

    # Stage 1: HDF5 Loading (if HDF5 files provided)
    if hdf5_dir and timestamp:
        logger.info("\n[STAGE 1] HDF5 Loading")
        logger.info("-" * 40)

        # Find matching files
        hdf5_files = sorted(hdf5_dir.glob(f"{timestamp}*.hdf5"))
        if not hdf5_files:
            # Try with tolerance
            hdf5_files = sorted(hdf5_dir.glob(f"{timestamp[:16]}*.hdf5"))

        if hdf5_files:
            logger.info(f"Found {len(hdf5_files)} HDF5 files")
            results = time_hdf5_loading(hdf5_files)
            all_results.extend(results)
            summary["stages"]["hdf5_loading"] = [asdict(r) for r in results]
        else:
            logger.warning(f"No HDF5 files found for timestamp {timestamp}")

    # Stage 2: Calibration (if MS provided)
    if ms_path and ms_path.exists():
        logger.info("\n[STAGE 2] Calibration")
        logger.info("-" * 40)
        logger.info(f"Using MS: {ms_path}")

        results = time_calibration(ms_path)
        all_results.extend(results)
        summary["stages"]["calibration"] = [asdict(r) for r in results]

    # Stage 3: Imaging
    if ms_path and ms_path.exists() and not skip_imaging:
        logger.info("\n[STAGE 3] Imaging")
        logger.info("-" * 40)

        output_dir = Path("/tmp/timing_benchmark_images")
        output_dir.mkdir(exist_ok=True)

        results = time_imaging(ms_path, output_dir)
        all_results.extend(results)
        summary["stages"]["imaging"] = [asdict(r) for r in results]

        # Stage 4: Photometry (on generated image)
        dirty_fits = output_dir / "timing_test_dirty-image.fits"
        if dirty_fits.exists():
            logger.info("\n[STAGE 4] Photometry")
            logger.info("-" * 40)

            results = time_photometry(dirty_fits)
            all_results.extend(results)
            summary["stages"]["photometry"] = [asdict(r) for r in results]

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    total_wall = sum(r.wall_time_s for r in all_results)
    total_cpu = sum(r.cpu_total_s for r in all_results)
    total_io = sum(r.io_wait_s for r in all_results)

    logger.info(f"Total wall time:  {format_time(total_wall)}")
    logger.info(f"Total CPU time:   {format_time(total_cpu)}")
    logger.info(f"Total I/O wait:   {format_time(total_io)} ({total_io/total_wall*100:.0f}%)")

    # Find top bottlenecks
    sorted_results = sorted(all_results, key=lambda r: r.wall_time_s, reverse=True)
    logger.info("\nTop 5 time-consuming operations:")
    for i, r in enumerate(sorted_results[:5], 1):
        logger.info(f"  {i}. {r.operation}: {format_time(r.wall_time_s)} (IO: {r.io_fraction*100:.0f}%)")

    # Identify I/O vs CPU bound operations
    io_bound = [r for r in all_results if r.io_fraction > 0.5 and r.wall_time_s > 1]
    cpu_bound = [r for r in all_results if r.io_fraction <= 0.5 and r.wall_time_s > 1]

    if io_bound:
        logger.info("\nI/O-bound operations (>50% I/O wait):")
        for r in io_bound:
            logger.info(f"  - {r.operation}: {r.io_fraction*100:.0f}% I/O")

    if cpu_bound:
        logger.info("\nCPU-bound operations:")
        for r in cpu_bound:
            logger.info(f"  - {r.operation}: {(1-r.io_fraction)*100:.0f}% CPU")

    summary["totals"] = {
        "wall_time_s": total_wall,
        "cpu_time_s": total_cpu,
        "io_wait_s": total_io,
        "io_fraction": total_io / total_wall if total_wall > 0 else 0,
    }

    # Save results
    if output_file:
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"\nResults saved to: {output_file}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="DSA-110 Pipeline Timing Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test calibration on existing MS:
    python timing_benchmark.py --ms /stage/dsa110-contimg/ms/2025-10-18T14:35:20.ms

    # Test full pipeline from HDF5:
    python timing_benchmark.py --hdf5-dir /data/incoming --timestamp "2025-10-02T00:12:00"

    # Skip imaging (faster):
    python timing_benchmark.py --ms /path/to/test.ms --skip-imaging
        """,
    )

    parser.add_argument(
        "--ms",
        type=Path,
        help="Path to Measurement Set for calibration/imaging timing",
    )
    parser.add_argument(
        "--hdf5-dir",
        type=Path,
        help="Directory containing HDF5 files",
    )
    parser.add_argument(
        "--timestamp",
        type=str,
        help="Timestamp prefix for HDF5 files (e.g., '2025-10-02T00:12:00')",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("timing_results.json"),
        help="Output JSON file for results (default: timing_results.json)",
    )
    parser.add_argument(
        "--skip-imaging",
        action="store_true",
        help="Skip imaging stage (faster for calibration-only testing)",
    )

    args = parser.parse_args()

    if not args.ms and not (args.hdf5_dir and args.timestamp):
        parser.error("Either --ms or both --hdf5-dir and --timestamp are required")

    run_benchmark(
        ms_path=args.ms,
        hdf5_dir=args.hdf5_dir,
        timestamp=args.timestamp,
        output_file=args.output,
        skip_imaging=args.skip_imaging,
    )


if __name__ == "__main__":
    main()

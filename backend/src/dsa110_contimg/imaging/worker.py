"""
Imaging worker: watches a directory of freshly converted 5-minute MS files,
looks up an active calibration apply list from the registry by observation
time, applies calibration, and makes quick continuum images.

This is a first-pass skeleton that can run in one-shot (scan) mode or in a
simple polling loop. It records products in a small SQLite DB for later
mosaicking.

GPU Safety:
    All imaging entry points are wrapped with @memory_safe decorator to ensure
    system RAM limits are respected before processing. This prevents OOM crashes
    that could cause disk disconnection (ref: Dec 2 2025 incident).

GPU Acceleration (Phase 3.3):
    The worker now supports GPU-accelerated dirty imaging via gpu_grid_visibilities().
    This provides ~10x speedup for gridding operations when CuPy is available.
    Falls back to CPU gridding or CASA tclean when GPU is unavailable.
"""

import argparse
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from dsa110_contimg.database import (
    ensure_products_db,
    images_insert,
    ms_index_upsert,
    get_active_applylist,
)
from dsa110_contimg.imaging.fast_imaging import run_fast_imaging
from dsa110_contimg.utils.gpu_safety import (
    memory_safe,
    gpu_safe,
    initialize_gpu_safety,
    check_gpu_memory_available,
    is_gpu_available,
)

logger = logging.getLogger("imaging_worker")

# Initialize GPU safety limits at module load time
# This sets up CuPy memory pool limits and system memory thresholds
initialize_gpu_safety()

# Check if GPU gridding is available
try:
    from dsa110_contimg.imaging.gpu_gridding import (
        gpu_grid_visibilities,
        cpu_grid_visibilities,
        GriddingConfig,
    )
    GPU_GRIDDING_AVAILABLE = True
except ImportError:
    GPU_GRIDDING_AVAILABLE = False
    gpu_grid_visibilities = None
    cpu_grid_visibilities = None
    GriddingConfig = None

try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except ImportError:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _read_ms_visibilities(
    ms_path: str,
    datacolumn: str = "CORRECTED_DATA",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read visibilities from MS for GPU gridding.

    Args:
        ms_path: Path to Measurement Set
        datacolumn: Data column to read (default: CORRECTED_DATA)

    Returns:
        Tuple of (uvw, vis, weights, flags) arrays
    """
    from dsa110_contimg.utils.casa_init import ensure_casa_path
    ensure_casa_path()
    import casacore.tables as casatables

    with casatables.table(ms_path, readonly=True) as tb:
        uvw = tb.getcol("UVW")  # (n_rows, 3) in meters

        # Get wavelength from SPECTRAL_WINDOW table for UV conversion
        try:
            with casatables.table(f"{ms_path}/SPECTRAL_WINDOW", readonly=True) as spw:
                ref_freq = spw.getcol("REF_FREQUENCY")[0]  # Hz
                wavelength = 299792458.0 / ref_freq  # meters
        except (OSError, KeyError):
            # Default to 1.4 GHz (21cm line)
            wavelength = 0.2142

        # Convert UVW from meters to wavelengths
        uvw = uvw / wavelength

        # Read data
        data = tb.getcol(datacolumn)  # (n_rows, n_chan, n_pol)
        flags = tb.getcol("FLAG")  # (n_rows, n_chan, n_pol)

        # Get weights - prefer WEIGHT_SPECTRUM if available
        colnames = tb.colnames()
        if "WEIGHT_SPECTRUM" in colnames:
            weights = tb.getcol("WEIGHT_SPECTRUM")
        elif "WEIGHT" in colnames:
            weights = tb.getcol("WEIGHT")
            # Expand to match data shape if needed
            if weights.ndim == 2:  # (n_rows, n_pol)
                weights = np.broadcast_to(
                    weights[:, np.newaxis, :],
                    data.shape
                ).copy()
        else:
            weights = np.ones_like(data, dtype=np.float32)

        # Average over channels and polarizations for dirty image
        # Take first Stokes I (average of XX and YY) or first pol
        n_pol = data.shape[2]
        if n_pol >= 2:
            vis_avg = 0.5 * (data[:, :, 0] + data[:, :, -1])
            flag_avg = flags[:, :, 0] | flags[:, :, -1]
            wt_avg = 0.5 * (weights[:, :, 0] + weights[:, :, -1])
        else:
            vis_avg = data[:, :, 0]
            flag_avg = flags[:, :, 0]
            wt_avg = weights[:, :, 0]

        # Average over frequency channels
        vis_flat = np.nanmean(vis_avg, axis=1)
        flag_flat = np.any(flag_avg, axis=1)
        wt_flat = np.nanmean(wt_avg, axis=1)

        return uvw, vis_flat, wt_flat, flag_flat


@gpu_safe(max_gpu_gb=9.0, max_system_gb=6.0)
def gpu_dirty_image(
    ms_path: str,
    output_path: str,
    *,
    image_size: int = 512,
    cell_size_arcsec: float = 12.0,
    gpu_id: int = 0,
    datacolumn: str = "CORRECTED_DATA",
) -> Optional[str]:
    """Create dirty image using GPU gridding.

    GPU Acceleration:
        Uses CuPy-based gridding for ~10x speedup over CASA tclean.
        Falls back to CPU gridding if GPU unavailable.

    Args:
        ms_path: Path to Measurement Set
        output_path: Output FITS file path (without extension)
        image_size: Image size in pixels (default 512)
        cell_size_arcsec: Cell size in arcseconds (default 12.0)
        gpu_id: GPU device ID (default 0)
        datacolumn: Data column to image (default CORRECTED_DATA)

    Returns:
        Path to output FITS file, or None if failed
    """
    if not GPU_GRIDDING_AVAILABLE:
        logger.warning("GPU gridding not available, skipping GPU dirty image")
        return None

    start_time = time.time()
    logger.info(f"GPU dirty imaging {ms_path} -> {output_path}")

    try:
        # Read visibilities
        uvw, vis, weights, flags = _read_ms_visibilities(ms_path, datacolumn)
        logger.info(
            f"Read {len(vis):,} visibilities, {np.sum(flags):,} flagged "
            f"({100*np.sum(flags)/len(flags):.1f}%)"
        )

        # Configure gridding
        config = GriddingConfig(
            image_size=image_size,
            cell_size_arcsec=cell_size_arcsec,
            gpu_id=gpu_id,
        )

        # Check GPU memory
        gpu_ok, gpu_reason = check_gpu_memory_available(2.0)  # Need ~2GB for gridding
        use_gpu = gpu_ok and is_gpu_available()

        # Run gridding
        if use_gpu:
            logger.info(f"Using GPU {gpu_id} for gridding")
            result = gpu_grid_visibilities(
                uvw, vis, weights,
                config=config,
                flags=flags.astype(np.int32),
            )
        else:
            logger.info(f"Using CPU for gridding (reason: {gpu_reason})")
            result = cpu_grid_visibilities(
                uvw, vis, weights,
                config=config,
                flags=flags.astype(np.int32),
            )

        if result.error:
            logger.error(f"Gridding failed: {result.error}")
            return None

        # Save as FITS
        from astropy.io import fits as pyfits

        fits_path = f"{output_path}.dirty.fits"
        hdu = pyfits.PrimaryHDU(result.image.astype(np.float32))
        hdu.header["BUNIT"] = "JY/BEAM"
        hdu.header["CDELT1"] = -cell_size_arcsec / 3600.0
        hdu.header["CDELT2"] = cell_size_arcsec / 3600.0
        hdu.header["CRPIX1"] = image_size / 2 + 1
        hdu.header["CRPIX2"] = image_size / 2 + 1
        hdu.header["CTYPE1"] = "RA---SIN"
        hdu.header["CTYPE2"] = "DEC--SIN"
        hdu.header["NVIS"] = result.n_vis
        hdu.header["NFLAG"] = result.n_flagged
        hdu.header["WSUM"] = result.weight_sum
        hdu.header["GPU"] = use_gpu
        hdu.header["GPUID"] = gpu_id if use_gpu else -1
        hdu.header["PROCTIME"] = result.processing_time_s

        hdu.writeto(fits_path, overwrite=True)

        elapsed = time.time() - start_time
        logger.info(
            f"GPU dirty image complete in {elapsed:.2f}s "
            f"(gridding: {result.processing_time_s:.2f}s)"
        )

        return fits_path

    except (OSError, RuntimeError, ValueError) as exc:
        logger.error(f"GPU dirty imaging failed: {exc}")
        return None


@memory_safe(max_system_gb=6.0)
def _apply_and_image(
    ms_path: str,
    out_dir: Path,
    gaintables: List[str],
    *,
    use_gpu: bool = True,
) -> List[str]:
    """Apply calibration and produce a quick image; returns artifact paths.

    GPU Acceleration (Phase 3.3):
        When use_gpu=True and CuPy is available, creates an additional
        GPU-accelerated dirty image for fast initial assessment.

    Memory Safety:
        Wrapped with @memory_safe to check system RAM availability before
        processing. Rejects if less than 30% RAM available or less than 2GB
        free to prevent OOM conditions.
    """
    artifacts: List[str] = []
    # Route temp files to scratch and chdir to output directory to avoid repo pollution
    try:
        if prepare_temp_environment is not None:
            prepare_temp_environment(
                os.getenv("CONTIMG_SCRATCH_DIR") or "/stage/dsa110-contimg",
                cwd_to=os.fspath(out_dir),
            )
    except (OSError, RuntimeError):
        pass
    # Apply to all fields by default
    try:
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.imaging.cli import image_ms

        apply_to_target(ms_path, field="", gaintables=gaintables, calwt=True)
        imgroot = out_dir / (Path(ms_path).stem + ".img")

        # Run deep imaging (standard) and fast imaging (transients) in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Task 1: Standard Deep Imaging (CASA tclean)
            future_deep = executor.submit(
                image_ms,
                ms_path,
                imagename=str(imgroot),
                field="",
                quality_tier="standard",
                skip_fits=True,
            )

            # Task 2: Fast Transient Imaging
            # Note: Running on CORRECTED_DATA (calibrated visibilities).
            # Ideally requires residuals for pure transient detection.
            future_fast = executor.submit(
                run_fast_imaging,
                ms_path,
                interval_seconds=None,  # Auto-detect
                threshold_sigma=6.0,
                datacolumn="CORRECTED_DATA",
                work_dir=str(out_dir),
            )

            # Task 3: GPU Dirty Image (new in Phase 3.3)
            future_gpu = None
            if use_gpu and GPU_GRIDDING_AVAILABLE:
                future_gpu = executor.submit(
                    gpu_dirty_image,
                    ms_path,
                    str(imgroot),
                    image_size=512,
                    cell_size_arcsec=12.0,
                )

            # Wait for deep imaging (critical path)
            try:
                future_deep.result()
            except Exception as e:
                logger.error("Deep imaging failed: %s", e)
                raise e

            # Wait for fast imaging (auxiliary)
            try:
                future_fast.result()
            except Exception as e:
                logger.warning("Fast imaging failed (non-fatal): %s", e)

            # Wait for GPU dirty image (auxiliary)
            if future_gpu is not None:
                try:
                    gpu_fits = future_gpu.result()
                    if gpu_fits and os.path.exists(gpu_fits):
                        artifacts.append(gpu_fits)
                        logger.info("GPU dirty image created: %s", gpu_fits)
                except (RuntimeError, OSError, ValueError) as e:
                    logger.warning("GPU dirty imaging failed (non-fatal): %s", e)

        # Return whatever CASA produced
        for ext in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            p = f"{imgroot}{ext}"
            if os.path.exists(p):
                artifacts.append(p)
    except (RuntimeError, OSError, ValueError) as e:
        logger.error("apply/image failed for %s: %s", ms_path, e)
    return artifacts


@memory_safe(max_system_gb=6.0)
def process_once(
    ms_dir: Path,
    out_dir: Path,
    registry_db: Path,
    products_db: Path,
) -> int:
    """Process all MS files in directory once."""
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = ensure_products_db(products_db)
    processed = 0
    for ms in sorted(ms_dir.glob("**/*.ms")):
        row = conn.execute(
            "SELECT status FROM ms_index WHERE path = ?", (os.fspath(ms),)
        ).fetchone()
        if row and row[0] == "done":
            continue
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(os.fspath(ms))
        if mid_mjd is None:
            # Fallback: use current time in MJD
            from astropy.time import Time

            mid_mjd = Time.now().mjd
        applylist = get_active_applylist(registry_db, mid_mjd)
        if not applylist:
            logger.warning("No active caltables for %s (mid MJD %.5f)", ms, mid_mjd)
            status = "skipped_no_caltables"
            ms_index_upsert(
                conn,
                os.fspath(ms),
                start_mjd=start_mjd,
                end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                processed_at=time.time(),
                status=status,
            )
            conn.commit()
            continue

        artifacts = _apply_and_image(os.fspath(ms), out_dir, applylist)
        status = "done" if artifacts else "failed"
        ms_index_upsert(
            conn,
            os.fspath(ms),
            start_mjd=start_mjd,
            end_mjd=end_mjd,
            mid_mjd=mid_mjd,
            processed_at=time.time(),
            status=status,
        )
        for art in artifacts:
            images_insert(
                conn,
                art,
                os.fspath(ms),
                time.time(),
                "5min",
                1 if art.endswith(".image.pbcor") else 0,
            )
        conn.commit()
        processed += 1
        logger.info("Processed %s (artifacts: %d)", ms, len(artifacts))
    return processed


def cmd_scan(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    n = process_once(
        Path(args.ms_dir),
        Path(args.out_dir),
        Path(args.registry_db),
        Path(args.products_db),
    )
    logger.info("Scan complete: %d MS processed", n)
    return 0 if n >= 0 else 1


def cmd_daemon(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    ms_dir = Path(args.ms_dir)
    out_dir = Path(args.out_dir)
    registry_db = Path(args.registry_db)
    products_db = Path(args.products_db)
    poll = float(args.poll_interval)
    while True:
        try:
            process_once(ms_dir, out_dir, registry_db, products_db)
        except Exception as e:
            logger.error("Worker loop error: %s", e)
        time.sleep(poll)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Imaging worker for 5-min MS")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("scan", help="One-shot scan of an MS directory")
    sp.add_argument("--ms-dir", required=True)
    sp.add_argument("--out-dir", required=True)
    sp.add_argument("--registry-db", required=True)
    sp.add_argument("--products-db", required=True)
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("daemon", help="Poll and process arriving MS")
    sp.add_argument("--ms-dir", required=True)
    sp.add_argument("--out-dir", required=True)
    sp.add_argument("--registry-db", required=True)
    sp.add_argument("--products-db", required=True)
    sp.add_argument("--poll-interval", type=float, default=60.0)
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_daemon)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, "func"):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

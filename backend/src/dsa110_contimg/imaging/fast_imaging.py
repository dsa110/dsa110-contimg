"""
Fast transient imaging prototype for DSA-110 pipeline.

Based on VASTER logic (askap-vast/vast-fastdetection), this module implements
short-timescale "snapshot" imaging of residuals to detect fast transients.

Workflow:
1. Assumes a static sky model has already been subtracted (CORRECTED_DATA contains residuals).
2. Splits observation into short time chunks (e.g. 30s).
3. Creates dirty images (niter=0) for each chunk.
4. Performs simple peak finding on the dirty images.

GPU Safety:
    Entry point run_fast_imaging() is wrapped with @gpu_safe to ensure both
    GPU VRAM and system RAM limits are respected before processing.
"""

import logging
import os
import shutil
import sqlite3
import subprocess
import time
from typing import Any, Dict, List, Optional

import numpy as np

# Ensure CASA environment is initialized before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

# Use casatools for metadata if available
try:
    from casatools import msmetadata as _msmd
    from casatools import table as _tb
except ImportError:
    _msmd = None
    _tb = None

# Fallback to astropy for FITS handling if needed
from astropy.io import fits

from dsa110_contimg.utils.decorators import timed
from dsa110_contimg.utils.gpu_safety import gpu_safe, initialize_gpu_safety

ensure_casa_path()

# Initialize GPU safety limits at module load time
initialize_gpu_safety()

LOG = logging.getLogger(__name__)


class FastImagingError(Exception):
    """Custom exception for fast imaging errors."""

    pass


def get_scan_duration(ms_path: str) -> float:
    """Get total duration of the scan in seconds using casacore."""
    if _msmd is not None:
        try:
            md = _msmd()
            md.open(ms_path)
            # Get time range from metadata (faster)
            times = md.timerangeforobs(0)
            md.close()
            if times and "begin" in times and "end" in times:
                return (
                    times["end"]["m0"]["value"] * 86400.0 - times["begin"]["m0"]["value"] * 86400.0
                )
        except (OSError, RuntimeError, KeyError):
            # Fallback to table if metadata fails
            pass

    if _tb is None:
        raise ImportError("casatools not available")

    try:
        tb = _tb()
        tb.open(ms_path)
        # Optimized: get first and last time only
        # Assumes TIME is sorted, which is standard for MS
        t_start = tb.getcell("TIME", 0)
        t_end = tb.getcell("TIME", tb.nrows() - 1)
        tb.close()

        return float(t_end - t_start)
    except Exception as e:
        LOG.error(f"Failed to get scan duration: {e}")
        raise


def get_integration_time(ms_path: str) -> float:
    """Get the integration time from the MS."""
    if _tb is None:
        # Default fallback if casatools not available
        return 1.0

    try:
        tb = _tb()
        tb.open(ms_path)
        interval = tb.getcell("INTERVAL", 0)
        tb.close()
        return float(interval)
    except Exception as e:
        LOG.warning(f"Failed to get integration time: {e}, defaulting to 1.0s")
        return 1.0


@timed("imaging.wsclean_snapshots")
def run_wsclean_snapshots(
    ms_path: str,
    output_prefix: str,
    interval_seconds: Optional[float] = None,
    imsize: int = 1024,
    cell_arcsec: float = 2.5,
    datacolumn: str = "CORRECTED_DATA",
    subtract_model: bool = False,
    n_threads: int = 4,
    mem_gb: int = 16,
) -> List[str]:
    """Run WSClean to produce snapshot images.

    Uses -intervals-out to split the measurement set into multiple images
    in a single pass.

    Args:
        ms_path: Path to Measurement Set
        output_prefix: Prefix for output images
        interval_seconds: Duration of each snapshot in seconds. If None, defaults to integration time.
        imsize: Image size in pixels
        cell_arcsec: Pixel scale in arcseconds
        datacolumn: Data column to image (should be residuals)
        subtract_model: If True, subtract MODEL_DATA from datacolumn before imaging
        n_threads: Number of threads to use
        mem_gb: Memory limit in GB

    Returns:
        List of generated FITS image paths
    """

    # Get integration time
    int_time = get_integration_time(ms_path)
    LOG.info(f"Integration time detected: {int_time:.2f}s")

    if interval_seconds is None:
        interval_seconds = int_time
        LOG.info(f"Using integration time as interval: {interval_seconds}s")
    elif interval_seconds < int_time:
        LOG.warning(
            f"Requested interval {interval_seconds}s is shorter than integration time {int_time:.2f}s. "
            "This will cause empty frames!"
        )

    # Calculate number of intervals
    duration = get_scan_duration(ms_path)
    if duration <= 0:
        raise FastImagingError("Scan duration is 0 or could not be determined")

    # Use slightly larger interval to avoid rounding errors leaving gaps?
    # WSClean splits total duration by N intervals.
    # If we want 1 image per integration, num_intervals = duration / int_time

    num_intervals = int(np.round(duration / interval_seconds))

    if num_intervals < 1:
        # Fallback to 1 interval if duration is short
        num_intervals = 1
        LOG.warning(
            f"Scan duration {duration}s is shorter than interval {interval_seconds}s. Producing 1 image."
        )

    LOG.info(
        f"Splitting {duration:.1f}s scan into {num_intervals} snapshots of ~{duration / num_intervals:.2f}s"
    )

    # Find wsclean executable
    wsclean_cmd = shutil.which("wsclean")

    # Fallback to Docker if native wsclean not found
    use_docker = False
    if not wsclean_cmd:
        docker_cmd = shutil.which("docker")
        if docker_cmd:
            LOG.info("Native wsclean not found, falling back to Docker (wsclean-everybeam:0.7.4)")
            use_docker = True
        else:
            raise FastImagingError("wsclean executable not found in PATH and Docker not available")

    # Construct command
    # Key optimization: niter=0 (Dirty Image Only)
    # We assume the static sky is already subtracted in CORRECTED_DATA
    if use_docker:
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.path.dirname(os.path.abspath(ms_path))}:/data_in",
            "-v",
            f"{os.path.dirname(os.path.abspath(output_prefix))}:/data_out",
            "wsclean-everybeam:0.7.4",
            "wsclean",
        ]
        # Adjust paths for Docker mapping
        docker_ms_path = f"/data_in/{os.path.basename(ms_path)}"
        docker_prefix = f"/data_out/{os.path.basename(output_prefix)}"
    else:
        cmd = [wsclean_cmd]
        docker_ms_path = ms_path
        docker_prefix = output_prefix

    cmd.extend(
        [
            "-name",
            docker_prefix,
            "-size",
            str(imsize),
            str(imsize),
            "-scale",
            f"{cell_arcsec}arcsec",
            "-niter",
            "0",  # Dirty image only
            "-data-column",
            datacolumn,
            "-intervals-out",
            str(num_intervals),
            "-weight",
            "briggs",
            "0.5",  # Robust 0.5 (VAST default)
            "-no-update-model-required",  # Optimization
            "-reorder",  # Required for multi-SPW
            "-j",
            str(n_threads),
            "-abs-mem",
            str(mem_gb),
            "-pol",
            "I",
            docker_ms_path,
        ]
    )

    if subtract_model:
        cmd.insert(-1, "-subtract-model")
        LOG.info("Enabling model subtraction (expecting MODEL_DATA to be populated)")

    LOG.info(f"Running WSClean: {' '.join(cmd)}")

    # Configurable timeout for Docker WSClean (default 30 min)
    # Set WSCLEAN_DOCKER_TIMEOUT env var to override (in seconds)
    wsclean_timeout = int(os.environ.get("WSCLEAN_DOCKER_TIMEOUT", "1800"))

    t0 = time.time()
    try:
        subprocess.run(cmd, check=True, capture_output=False, timeout=wsclean_timeout)
    except subprocess.TimeoutExpired:
        LOG.error(
            "WSClean timed out after %ds. If using Docker, attempting cleanup...",
            wsclean_timeout,
        )
        # Attempt to kill any orphaned Docker containers
        if use_docker:
            try:
                # Find and kill containers running wsclean image
                kill_cmd = [
                    "docker",
                    "ps",
                    "-q",
                    "--filter",
                    "ancestor=wsclean-everybeam:0.7.4",
                ]
                result = subprocess.run(kill_cmd, capture_output=True, text=True, timeout=10)
                container_ids = result.stdout.strip().split()
                for cid in container_ids:
                    if cid:
                        LOG.warning("Killing orphaned WSClean container: %s", cid)
                        subprocess.run(["docker", "kill", cid], timeout=10, check=False)
            except Exception as cleanup_err:
                LOG.warning("Failed to cleanup Docker containers: %s", cleanup_err)
        raise FastImagingError(
            f"WSClean timed out after {wsclean_timeout}s. "
            "Consider increasing WSCLEAN_DOCKER_TIMEOUT or disabling NVSS seeding."
        )
    except subprocess.CalledProcessError as e:
        raise FastImagingError(f"WSClean failed with exit code {e.returncode}")

    LOG.info(f"Snapshot imaging completed in {time.time() - t0:.2f}s")

    # Identify output files
    # WSClean names them like: prefix-t0000-image.fits
    # Note: With niter=0, WSClean produces '-dirty.fits' usually, but with -intervals-out
    # it might name them differently. Let's check the directory.

    output_dir = os.path.dirname(output_prefix) or "."
    prefix_name = os.path.basename(output_prefix)

    generated_files = []
    for f in os.listdir(output_dir):
        if f.startswith(prefix_name) and f.endswith(".fits") and "image" in f:
            generated_files.append(os.path.join(output_dir, f))

    # If no 'image' files, check for 'dirty' files (since niter=0)
    if not generated_files:
        for f in os.listdir(output_dir):
            if f.startswith(prefix_name) and f.endswith(".fits") and "dirty" in f:
                generated_files.append(os.path.join(output_dir, f))

    return sorted(generated_files)


def analyze_snapshots(image_paths: List[str], threshold_sigma: float = 6.0) -> List[Dict[str, Any]]:
    """Analyze snapshot images for transient candidates.

    Args:
        image_paths: List of FITS image paths
        threshold_sigma: Sigma threshold for peak detection

    Returns:
        List of candidate dictionaries
    """
    candidates = []

    for img_path in image_paths:
        try:
            with fits.open(img_path) as hdul:
                data = hdul[0].data
                # Handle 4D axes (Stokes, Freq, Y, X)
                if len(data.shape) == 4:
                    data = data[0, 0, :, :]
                elif len(data.shape) == 3:
                    data = data[0, :, :]

                # Calculate statistics
                # Simple MAD (Median Absolute Deviation) for robust RMS
                valid_data = data[np.isfinite(data)]
                if len(valid_data) == 0:
                    continue

                median = np.nanmedian(valid_data)
                mad = np.nanmedian(np.abs(valid_data - median))
                rms = 1.4826 * mad

                peak_val = np.nanmax(valid_data)
                min_val = np.nanmin(valid_data)

                # Check for significant positive peak
                if peak_val > (median + threshold_sigma * rms):
                    # Locate peak
                    y, x = np.unravel_index(np.argmax(data), data.shape)

                    # Get WCS coordinates
                    from astropy.wcs import WCS

                    w = WCS(hdul[0].header).celestial
                    ra, dec = w.pixel_to_world_values(x, y)

                    candidates.append(
                        {
                            "image": img_path,
                            "peak_mjy": peak_val * 1000.0,
                            "rms_mjy": rms * 1000.0,
                            "snr": (peak_val - median) / rms,
                            "ra_deg": float(ra),
                            "dec_deg": float(dec),
                            "timestamp_idx": extract_timestamp_index(img_path),
                        }
                    )

        except Exception as e:
            LOG.warning(f"Failed to analyze {img_path}: {e}")
            continue

    return candidates


def extract_timestamp_index(filename: str) -> int:
    """Extract time index from WSClean filename (e.g. image-t0001.fits)."""
    import re

    match = re.search(r"-t(\d{4})", filename)
    if match:
        return int(match.group(1))
    return -1


def save_candidates_to_db(
    candidates: List[Dict[str, Any]],
    ms_path: str,
    db_path: str = "/data/dsa110-contimg/state/db/pipeline.sqlite3",
) -> None:
    """Save candidates to SQLite database."""
    if not candidates:
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        timestamp_now = time.time()

        for cand in candidates:
            cursor.execute(
                """
                INSERT INTO transient_candidates (
                    image_path, ms_path, ra_deg, dec_deg, snr, 
                    peak_flux_mjy, local_rms_mjy, frame_index, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """,
                (
                    cand["image"],
                    ms_path,
                    float(cand["ra_deg"]),
                    float(cand["dec_deg"]),
                    float(cand["snr"]),
                    float(cand["peak_mjy"]),
                    float(cand["rms_mjy"]),
                    int(cand["timestamp_idx"]),
                    timestamp_now,
                ),
            )

        conn.commit()
        conn.close()
        LOG.info(f"Saved {len(candidates)} candidates to {db_path}")
    except Exception as e:
        LOG.error(f"Failed to save candidates to DB: {e}")


@gpu_safe(max_gpu_gb=9.0, max_system_gb=6.0)
@timed("imaging.run_fast_imaging")
def run_fast_imaging(
    ms_path: str,
    interval_seconds: Optional[float] = None,
    threshold_sigma: float = 6.0,
    imsize: int = 1024,
    datacolumn: str = "CORRECTED_DATA",
    subtract_model: bool = False,
    work_dir: str = ".",
) -> List[Dict[str, Any]]:
    """Main entry point for fast transient imaging.

    GPU Safety:
        Wrapped with @gpu_safe to check GPU VRAM and system RAM availability
        before processing. Rejects if GPU memory or RAM limits would be exceeded.

    Args:
        ms_path: Path to measurement set
        interval_seconds: Snapshot duration. If None, defaults to integration time.
        threshold_sigma: Detection threshold
        imsize: Image size
        datacolumn: Data column to image
        subtract_model: Subtract MODEL_DATA before imaging (for residuals)
        work_dir: Working directory for outputs

    Returns:
        List of candidates
    """
    ms_name = os.path.basename(ms_path)
    output_prefix = os.path.join(work_dir, f"{ms_name}.fast")

    LOG.info(f"Starting fast imaging for {ms_name}")

    # 1. Image Snapshots
    images = run_wsclean_snapshots(
        ms_path=ms_path,
        output_prefix=output_prefix,
        interval_seconds=interval_seconds,
        imsize=imsize,
        datacolumn=datacolumn,
        subtract_model=subtract_model,
    )

    if not images:
        LOG.warning("No snapshot images generated")
        return []

    # 2. Analyze
    candidates = analyze_snapshots(images, threshold_sigma)

    LOG.info(f"Found {len(candidates)} candidates above {threshold_sigma} sigma")

    # 3. Save to DB
    save_candidates_to_db(candidates, ms_path)

    for c in candidates:
        LOG.info(f"Candidate: RA={c['ra_deg']:.4f}, Dec={c['dec_deg']:.4f}, SNR={c['snr']:.1f}")

    return candidates


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Fast Transient Imaging Prototype")
    parser.add_argument(
        "ms", help="Path to Measurement Set (must have residuals in CORRECTED_DATA)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Snapshot interval in seconds (default: auto-detect)",
    )
    parser.add_argument("--threshold", type=float, default=6.0, help="Sigma threshold")
    parser.add_argument(
        "--datacolumn", type=str, default="CORRECTED_DATA", help="Data column to use"
    )
    parser.add_argument(
        "--subtract-model",
        action="store_true",
        help="Subtract MODEL_DATA from datacolumn before imaging",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    try:
        run_fast_imaging(
            args.ms,
            args.interval,
            args.threshold,
            datacolumn=args.datacolumn,
            subtract_model=args.subtract_model,
        )
    except Exception as e:
        LOG.error(f"Fast imaging failed: {e}")
        exit(1)

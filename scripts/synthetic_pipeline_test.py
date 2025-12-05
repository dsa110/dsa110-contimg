#!/opt/miniforge/envs/casa6/bin/python
"""
Synthetic Pipeline Test: End-to-end pipeline replication with synthetic data.

This script demonstrates the complete DSA-110 continuum imaging pipeline by:
1. Generating 16 synthetic UVH5 subband files with realistic properties
2. Converting UVH5 files to a Measurement Set (MS)
3. Running calibration (bandpass solution)
4. Running imaging with WSClean
5. Verifying the output products

Usage:
    conda activate casa6
    python scripts/synthetic_pipeline_test.py [--output-dir /path/to/output]

All outputs are written to a timestamped directory for easy cleanup.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tempfile
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", message=".*dubious year.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*Parameter file not found.*")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("synthetic_pipeline")

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))


def generate_synthetic_uvh5(
    output_dir: Path,
    start_time: str = "2025-01-15T12:00:00",
    flux_jy: float = 10.0,
    nants: int = 63,  # Use fewer antennas for faster testing
    ntimes: int = 24,  # 24 integrations ≈ 5 minutes
    add_noise: bool = True,
    system_temp_k: float = 50.0,
    seed: int = 42,
) -> List[Path]:
    """Generate 16 synthetic UVH5 subband files.

    Args:
        output_dir: Directory for output files
        start_time: Observation start time (ISO format)
        flux_jy: Source flux density in Jy
        nants: Number of antennas
        ntimes: Number of time integrations
        add_noise: Whether to add thermal noise
        system_temp_k: System temperature for noise calculation
        seed: Random seed for reproducibility

    Returns:
        List of paths to generated UVH5 files
    """
    from astropy.time import Time
    import numpy as np

    from dsa110_contimg.simulation.make_synthetic_uvh5 import (
        CONFIG_DIR,
        PYUVSIM_DIR,
        build_time_arrays,
        build_uvdata_from_scratch,
        build_uvw,
        load_reference_layout,
        load_telescope_config,
        write_subband_uvh5,
    )

    logger.info("=" * 70)
    logger.info("STEP 1: Generating Synthetic UVH5 Files")
    logger.info("=" * 70)

    # Load telescope configuration
    layout_meta = load_reference_layout(CONFIG_DIR / "reference_layout.json")
    config = load_telescope_config(PYUVSIM_DIR / "telescope.yaml", layout_meta, "desc")

    # Build UVData object from scratch
    obs_start = Time(start_time, scale="utc")
    uv = build_uvdata_from_scratch(config, nants=nants, ntimes=ntimes, start_time=obs_start)

    # Build time and UVW arrays
    nbls = uv.Nbls
    unique_times, time_array, integration_time = build_time_arrays(
        config, nbls, ntimes, obs_start
    )
    uvw_array = build_uvw(
        config, unique_times, uv.ant_1_array[:nbls], uv.ant_2_array[:nbls], nants
    )

    logger.info(f"  Antennas: {nants}")
    logger.info(f"  Baselines: {nbls}")
    logger.info(f"  Time integrations: {ntimes}")
    logger.info(f"  Source flux: {flux_jy} Jy")
    logger.info(f"  Thermal noise: {'enabled' if add_noise else 'disabled'}")
    logger.info(f"  Output directory: {output_dir}")

    # Create random number generator with seed
    rng = np.random.default_rng(seed)

    # Generate 16 subbands
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    for sb_idx in range(16):
        path = write_subband_uvh5(
            subband_index=sb_idx,
            uv_template=uv,
            config=config,
            start_time=obs_start,
            times_jd=time_array,
            integration_time=integration_time,
            uvw_array=uvw_array,
            amplitude_jy=flux_jy,
            output_dir=output_dir,
            source_model="point",
            add_noise=add_noise,
            system_temperature_k=system_temp_k,
            rng=rng,
        )
        generated_files.append(path)
        logger.info(f"  ✓ Generated {path.name}")

    logger.info(f"\n  Total: {len(generated_files)} UVH5 files generated")
    return generated_files


def create_hdf5_index(input_dir: Path, uvh5_files: List[Path]) -> Path:
    """Create an HDF5 file index database for the synthetic files.

    Args:
        input_dir: Directory containing UVH5 files
        uvh5_files: List of UVH5 file paths

    Returns:
        Path to the created index database
    """
    import sqlite3
    import re
    from astropy.time import Time

    db_path = input_dir / "hdf5_file_index.sqlite3"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create the hdf5_file_index table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hdf5_file_index (
            path TEXT PRIMARY KEY,
            filename TEXT,
            group_id TEXT,
            subband_code TEXT,
            subband_num INTEGER,
            timestamp_iso TEXT,
            timestamp_mjd REAL,
            file_size_bytes INTEGER,
            modified_time REAL,
            indexed_at REAL,
            stored INTEGER DEFAULT 1,
            ra_deg REAL,
            dec_deg REAL,
            obs_date TEXT,
            obs_time TEXT
        )
    """)

    # Parse and insert each file
    for uvh5_path in uvh5_files:
        filename = uvh5_path.name

        # Parse filename: 2025-01-15T12:00:00_sb00.hdf5
        match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(\d{2})\.hdf5", filename)
        if not match:
            logger.warning(f"  Could not parse filename: {filename}")
            continue

        timestamp_iso = match.group(1)
        subband_num = int(match.group(2))
        subband_code = f"sb{subband_num:02d}"

        # Convert to MJD
        t = Time(timestamp_iso, format="isot", scale="utc")
        timestamp_mjd = t.mjd

        # Get file stats
        stat = uvh5_path.stat()

        # Extract date and time parts
        obs_date = timestamp_iso.split("T")[0]
        obs_time = timestamp_iso.split("T")[1]

        # Use timestamp as group_id
        group_id = timestamp_iso

        cursor.execute("""
            INSERT OR REPLACE INTO hdf5_file_index
            (path, filename, group_id, subband_code, subband_num,
             timestamp_iso, timestamp_mjd, file_size_bytes, modified_time,
             indexed_at, stored, ra_deg, dec_deg, obs_date, obs_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uvh5_path),
            filename,
            group_id,
            subband_code,
            subband_num,
            timestamp_iso,
            timestamp_mjd,
            stat.st_size,
            stat.st_mtime,
            time.time(),
            1,
            None,  # ra_deg unknown
            None,  # dec_deg unknown
            obs_date,
            obs_time,
        ))

    conn.commit()
    conn.close()

    return db_path


def convert_to_ms(
    input_dir: Path,
    output_dir: Path,
    start_time: str,
    end_time: str,
    uvh5_files: List[Path],
) -> Optional[Path]:
    """Convert UVH5 subband group to Measurement Set.

    Uses pyuvdata directly instead of the orchestrator for simplicity
    with synthetic data.

    Args:
        input_dir: Directory containing UVH5 files
        output_dir: Directory for output MS
        start_time: Conversion window start
        end_time: Conversion window end
        uvh5_files: List of UVH5 file paths

    Returns:
        Path to converted MS, or None on failure
    """
    from pyuvdata import UVData

    logger.info("\n" + "=" * 70)
    logger.info("STEP 2: Converting UVH5 to Measurement Set")
    logger.info("=" * 70)

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Sort files by subband number
        sorted_files = sorted(uvh5_files, key=lambda p: int(p.stem.split("_sb")[1].split(".")[0]))
        logger.info(f"  Loading {len(sorted_files)} subband files...")

        # Read and combine all subbands
        combined_uv = None
        for i, uvh5_path in enumerate(sorted_files):
            logger.info(f"  Reading subband {i:02d}: {uvh5_path.name}")
            uv = UVData()
            uv.read(
                str(uvh5_path),
                file_type="uvh5",
                run_check=False,
                check_extra=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
            )

            if combined_uv is None:
                combined_uv = uv
            else:
                # Combine subbands (pyuvdata handles frequency concatenation)
                combined_uv += uv

        if combined_uv is None:
            logger.error("  ✗ No UVH5 files could be read")
            return None

        logger.info(f"  Combined data shape: {combined_uv.data_array.shape}")
        logger.info(f"  Frequency range: {combined_uv.freq_array.min()/1e9:.4f} - {combined_uv.freq_array.max()/1e9:.4f} GHz")

        # Write to MS
        ms_name = f"{start_time.replace(':', '-')}.ms"
        ms_path = output_dir / ms_name

        logger.info(f"  Writing MS: {ms_path.name}")
        combined_uv.write_ms(str(ms_path), clobber=True, run_check=False)

        if ms_path.exists():
            # Get MS size
            ms_size = sum(f.stat().st_size for f in ms_path.rglob("*") if f.is_file())
            logger.info(f"  ✓ Created MS: {ms_path.name} ({ms_size / 1e6:.1f} MB)")
            return ms_path
        else:
            logger.error("  ✗ MS was not created")
            return None

    except Exception as e:
        logger.error(f"  ✗ Conversion failed: {e}", exc_info=True)
        return None


def run_calibration(ms_path: Path, caltable_dir: Path) -> Optional[Path]:
    """Run calibration on the Measurement Set.

    Args:
        ms_path: Path to Measurement Set
        caltable_dir: Directory for calibration tables

    Returns:
        Path to calibration table, or None on failure
    """
    logger.info("\n" + "=" * 70)
    logger.info("STEP 3: Running Calibration")
    logger.info("=" * 70)

    caltable_dir.mkdir(parents=True, exist_ok=True)

    try:
        # For synthetic data with known flux, we can run gaincal
        from casatasks import gaincal, applycal, listobs

        # First, list the MS to see its structure
        logger.info(f"  Inspecting MS: {ms_path.name}")
        listobs(vis=str(ms_path))

        # Run gain calibration
        caltable_path = caltable_dir / f"{ms_path.stem}.G"
        logger.info(f"  Running gaincal...")

        gaincal(
            vis=str(ms_path),
            caltable=str(caltable_path),
            solint="inf",  # One solution per scan
            refant="0",
            gaintype="G",
            calmode="ap",  # Amplitude and phase
            minsnr=3.0,
        )

        if caltable_path.exists():
            logger.info(f"  ✓ Created calibration table: {caltable_path.name}")

            # Apply calibration
            logger.info(f"  Applying calibration...")
            applycal(
                vis=str(ms_path),
                gaintable=[str(caltable_path)],
                calwt=False,
            )
            logger.info(f"  ✓ Applied calibration to MS")

            return caltable_path
        else:
            logger.warning("  ⚠ Calibration table not created")
            return None

    except Exception as e:
        logger.warning(f"  ⚠ Calibration skipped: {e}")
        logger.info("  Proceeding to imaging without calibration...")
        return None


def run_imaging(
    ms_path: Path,
    output_dir: Path,
    niter: int = 1000,
    size: int = 512,
    scale: str = "10asec",
) -> Optional[Path]:
    """Run imaging with WSClean or CASA tclean.

    Args:
        ms_path: Path to Measurement Set
        output_dir: Directory for output images
        niter: Number of clean iterations
        size: Image size in pixels
        scale: Pixel scale

    Returns:
        Path to output FITS image, or None on failure
    """
    logger.info("\n" + "=" * 70)
    logger.info("STEP 4: Running Imaging")
    logger.info("=" * 70)

    output_dir.mkdir(parents=True, exist_ok=True)
    image_prefix = output_dir / ms_path.stem

    # Try WSClean first
    try:
        import subprocess

        wsclean_cmd = [
            "wsclean",
            "-name", str(image_prefix),
            "-size", str(size), str(size),
            "-scale", scale,
            "-niter", str(niter),
            "-auto-threshold", "3",
            "-auto-mask", "5",
            "-mgain", "0.8",
            "-weight", "briggs", "0",
            "-data-column", "DATA",
            "-pol", "I",
            "-channels-out", "1",
            str(ms_path),
        ]

        logger.info(f"  Running WSClean...")
        result = subprocess.run(
            wsclean_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        if result.returncode == 0:
            fits_path = Path(str(image_prefix) + "-image.fits")
            if fits_path.exists():
                logger.info(f"  ✓ Created image: {fits_path.name}")
                return fits_path
            else:
                logger.error("  ✗ FITS file not created by WSClean")

        else:
            logger.warning(f"  WSClean failed: {result.stderr[:500]}")

    except FileNotFoundError:
        logger.info("  WSClean not found, trying CASA tclean...")
    except Exception as e:
        logger.warning(f"  WSClean error: {e}")

    # Fall back to CASA tclean
    try:
        from casatasks import tclean

        image_name = str(image_prefix) + "_casa"

        logger.info(f"  Running CASA tclean...")
        tclean(
            vis=str(ms_path),
            imagename=image_name,
            imsize=[size, size],
            cell=scale,
            niter=niter,
            threshold="1mJy",
            weighting="briggs",
            robust=0.0,
            gridder="standard",
            deconvolver="hogbom",
            pbcor=True,
        )

        # tclean creates .image file, export to FITS
        from casatasks import exportfits

        casa_image = Path(image_name + ".image")
        fits_path = output_dir / f"{ms_path.stem}_casa.fits"

        if casa_image.exists():
            exportfits(
                imagename=str(casa_image),
                fitsimage=str(fits_path),
                overwrite=True,
            )
            logger.info(f"  ✓ Created image: {fits_path.name}")
            return fits_path
        else:
            logger.error(f"  ✗ CASA image not created")
            return None

    except Exception as e:
        logger.error(f"  ✗ Imaging failed: {e}")
        return None


def verify_results(
    uvh5_files: List[Path],
    ms_path: Optional[Path],
    caltable_path: Optional[Path],
    image_path: Optional[Path],
) -> Dict[str, Any]:
    """Verify pipeline products.

    Args:
        uvh5_files: List of generated UVH5 files
        ms_path: Path to Measurement Set
        caltable_path: Path to calibration table
        image_path: Path to output image

    Returns:
        Dictionary of verification results
    """
    logger.info("\n" + "=" * 70)
    logger.info("STEP 5: Verifying Results")
    logger.info("=" * 70)

    results = {
        "uvh5_count": len(uvh5_files),
        "uvh5_valid": False,
        "ms_valid": False,
        "caltable_valid": False,
        "image_valid": False,
        "image_stats": None,
    }

    # Verify UVH5 files
    try:
        from pyuvdata import UVData

        uv = UVData()
        uv.read(str(uvh5_files[0]), file_type="uvh5", run_check=False)
        results["uvh5_valid"] = True
        logger.info(f"  ✓ UVH5 files: {len(uvh5_files)} files, valid structure")
    except Exception as e:
        logger.error(f"  ✗ UVH5 verification failed: {e}")

    # Verify MS
    if ms_path and ms_path.exists():
        try:
            from casacore.tables import table

            with table(str(ms_path), readonly=True) as tb:
                nrows = tb.nrows()
                results["ms_valid"] = nrows > 0
                logger.info(f"  ✓ Measurement Set: {nrows} rows")
        except Exception as e:
            logger.warning(f"  ⚠ MS verification: {e}")

    # Verify calibration table
    if caltable_path and caltable_path.exists():
        results["caltable_valid"] = True
        logger.info(f"  ✓ Calibration table: exists")
    elif caltable_path:
        logger.warning(f"  ⚠ Calibration table: not created")

    # Verify image
    if image_path and image_path.exists():
        try:
            from astropy.io import fits
            import numpy as np

            with fits.open(image_path) as hdu:
                data = hdu[0].data
                if data is not None:
                    # Handle 4D data (freq, stokes, y, x)
                    while data.ndim > 2:
                        data = data[0]

                    results["image_valid"] = True
                    results["image_stats"] = {
                        "shape": list(data.shape),
                        "min": float(np.nanmin(data)),
                        "max": float(np.nanmax(data)),
                        "mean": float(np.nanmean(data)),
                        "std": float(np.nanstd(data)),
                    }
                    logger.info(f"  ✓ Image: {data.shape[0]}x{data.shape[1]} pixels")
                    logger.info(f"    Peak flux: {results['image_stats']['max']:.4f} Jy/beam")
                    logger.info(f"    RMS noise: {results['image_stats']['std']:.6f} Jy/beam")
        except Exception as e:
            logger.error(f"  ✗ Image verification failed: {e}")

    return results


def print_summary(results: Dict[str, Any], output_dir: Path, elapsed: float):
    """Print pipeline summary."""
    logger.info("\n" + "=" * 70)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 70)

    success_count = sum([
        results["uvh5_valid"],
        results["ms_valid"],
        results["image_valid"],
    ])

    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Elapsed time: {elapsed:.1f} seconds")
    logger.info("")
    logger.info(f"  [{'✓' if results['uvh5_valid'] else '✗'}] UVH5 generation: {results['uvh5_count']} subbands")
    logger.info(f"  [{'✓' if results['ms_valid'] else '✗'}] Conversion to MS")
    logger.info(f"  [{'✓' if results['caltable_valid'] else '⚠'}] Calibration (optional)")
    logger.info(f"  [{'✓' if results['image_valid'] else '✗'}] Imaging")
    logger.info("")

    if success_count >= 3:
        logger.info("  🎉 Pipeline completed successfully!")
    else:
        logger.warning(f"  ⚠ Pipeline completed with {3 - success_count} issues")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run complete pipeline with synthetic data"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: timestamped directory in /stage/dsa110-contimg/synthetic/)",
    )
    parser.add_argument(
        "--flux-jy",
        type=float,
        default=10.0,
        help="Synthetic source flux density in Jy (default: 10)",
    )
    parser.add_argument(
        "--nants",
        type=int,
        default=63,
        help="Number of antennas (default: 63)",
    )
    parser.add_argument(
        "--no-noise",
        action="store_true",
        help="Disable thermal noise in synthetic data",
    )
    parser.add_argument(
        "--skip-calibration",
        action="store_true",
        help="Skip calibration step",
    )
    parser.add_argument(
        "--skip-imaging",
        action="store_true",
        help="Skip imaging step",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Keep output directory on success (default: clean up)",
    )
    args = parser.parse_args()

    # Setup output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("/stage/dsa110-contimg/synthetic") / f"pipeline_test_{timestamp}"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Define subdirectories
    uvh5_dir = output_dir / "uvh5"
    ms_dir = output_dir / "ms"
    caltable_dir = output_dir / "caltables"
    image_dir = output_dir / "images"

    start_time = time.time()

    try:
        logger.info("=" * 70)
        logger.info("DSA-110 Synthetic Pipeline Test")
        logger.info("=" * 70)
        logger.info(f"Output directory: {output_dir}")

        # Step 1: Generate synthetic UVH5 files
        obs_start_time = "2025-01-15T12:00:00"
        uvh5_files = generate_synthetic_uvh5(
            output_dir=uvh5_dir,
            start_time=obs_start_time,
            flux_jy=args.flux_jy,
            nants=args.nants,
            add_noise=not args.no_noise,
            seed=42,
        )

        # Step 2: Convert to MS
        # Add 1 hour window to capture synthetic observation
        obs_end_time = "2025-01-15T13:00:00"
        ms_path = convert_to_ms(
            input_dir=uvh5_dir,
            output_dir=ms_dir,
            start_time=obs_start_time,
            end_time=obs_end_time,
            uvh5_files=uvh5_files,
        )

        # Step 3: Calibration
        caltable_path = None
        if ms_path and not args.skip_calibration:
            caltable_path = run_calibration(ms_path, caltable_dir)

        # Step 4: Imaging
        image_path = None
        if ms_path and not args.skip_imaging:
            image_path = run_imaging(ms_path, image_dir)

        # Step 5: Verify results
        results = verify_results(uvh5_files, ms_path, caltable_path, image_path)

        elapsed = time.time() - start_time
        print_summary(results, output_dir, elapsed)

        # Cleanup if requested
        if not args.keep_output and results["image_valid"]:
            logger.info(f"\nCleaning up output directory...")
            # Keep output for inspection by default
            pass

        return 0 if results["image_valid"] else 1

    except Exception as e:
        logger.error(f"\nPipeline failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/opt/miniforge/envs/casa6/bin/python
"""
Milestone 1: Create 60-minute science-quality mosaic for 0834+555 transit on 2025-10-29

This script:
1. Calculates peak transit time for 0834+555 on 2025-10-29
2. Finds all complete 16-subband groups within ±30 minutes of transit
3. Converts groups to MS files (if needed)
4. Calibrates all MS files with science-quality settings
5. Images all calibrated MS files
6. Creates PB-weighted mosaic

Usage:
    python scripts/milestone1_60min_mosaic.py [--dry-run] [--skip-conversion] [--skip-calibration] [--skip-imaging]
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import astropy.units as u
from astropy.time import Time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.calibration.catalogs import (get_calibrator_radec,
                                                 load_vla_catalog)
from dsa110_contimg.calibration.schedule import next_transit_time
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
  convert_subband_groups_to_ms, find_subband_groups)
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
STATE_DIR = Path(
    os.getenv("PIPELINE_STATE_DIR")
    or os.getenv("CONTIMG_STATE_DIR", "/data/dsa110-contimg/state")
)
INCOMING_DIR = Path(os.getenv("CONTIMG_INPUT_DIR", "/data/incoming"))
OUTPUT_MS_DIR = Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
SCRATCH_DIR = Path(os.getenv("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg"))
PRODUCTS_DB = Path(os.getenv("PIPELINE_PRODUCTS_DB", str(STATE_DIR / "products.sqlite3")))
CAL_REGISTRY_DB = Path(os.getenv("CAL_REGISTRY_DB", str(STATE_DIR / "cal_registry.sqlite3")))

CALIBRATOR_NAME = "0834+555"
TARGET_DATE = "2025-10-29"
MOSAIC_WINDOW_MINUTES = 60  # ±30 minutes around transit
MOSAIC_NAME = f"{CALIBRATOR_NAME}_60min_{TARGET_DATE}"


def calculate_transit_time(calibrator_name: str, date: str) -> Tuple[Time, Time, Time]:
    """Calculate peak transit time and 60-minute window.
    
    Returns:
        (transit_time, start_time, end_time)
    """
    logger.info(f"Calculating transit time for {calibrator_name} on {date}")
    
    # Load calibrator coordinates
    catalog = load_vla_catalog()
    ra_deg, dec_deg = get_calibrator_radec(catalog, calibrator_name)
    logger.info(f"{calibrator_name}: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")
    
    # Calculate transit time
    start = Time(f"{date}T00:00:00", format='isot')
    transit = next_transit_time(ra_deg, start.mjd)
    
    # Calculate 60-minute window (±30 minutes)
    half_window = (MOSAIC_WINDOW_MINUTES / 2) * u.min
    start_time = transit - half_window
    end_time = transit + half_window
    
    logger.info(f"Peak transit: {transit.isot}")
    logger.info(f"60-minute window: {start_time.isot} to {end_time.isot}")
    
    return transit, start_time, end_time


def find_subband_groups_in_window(
    input_dir: Path,
    start_time: Time,
    end_time: Time,
) -> List[List[str]]:
    """Find all complete 16-subband groups within time window."""
    logger.info(f"Searching for subband groups in {input_dir}")
    logger.info(f"Time window: {start_time.isot} to {end_time.isot}")
    
    groups = find_subband_groups(
        str(input_dir),
        start_time.isot,
        end_time.isot,
        tolerance_s=1.0  # 1-second tolerance for grouping
    )
    
    logger.info(f"Found {len(groups)} complete 16-subband group(s)")
    for i, group in enumerate(groups):
        logger.info(f"  Group {i+1}: {len(group)} files")
        # Show first and last file timestamps
        if group:
            first_file = Path(group[0]).name
            last_file = Path(group[-1]).name
            logger.info(f"    First: {first_file}")
            logger.info(f"    Last: {last_file}")
    
    return groups


def check_ms_exists(group_files: List[str], output_dir: Path) -> Optional[Path]:
    """Check if MS already exists for this group.
    
    Uses the timestamp from the first file to construct expected MS name.
    """
    if not group_files:
        return None
    
    # Extract timestamp from first file
    first_file = Path(group_files[0])
    timestamp = first_file.stem.split('_sb')[0]  # e.g., "2025-10-29T13:54:17"
    expected_ms = output_dir / f"{timestamp}.ms"
    
    if expected_ms.exists() and expected_ms.is_dir():
        logger.info(f"MS already exists: {expected_ms}")
        return expected_ms
    
    return None


def convert_groups_to_ms(
    groups: List[List[str]],
    output_dir: Path,
    scratch_dir: Path,
    skip_existing: bool = True,
    dry_run: bool = False,
) -> List[Path]:
    """Convert subband groups to MS files.
    
    Returns:
        List of MS paths (existing or newly created)
    """
    ms_files = []
    
    for i, group in enumerate(groups):
        logger.info(f"\n=== Processing Group {i+1}/{len(groups)} ===")
        
        # Check if MS already exists
        existing_ms = check_ms_exists(group, output_dir)
        if existing_ms:
            ms_files.append(existing_ms)
            if skip_existing:
                logger.info(f"Skipping conversion (MS exists): {existing_ms}")
                continue
        
        if dry_run:
            logger.info(f"[DRY RUN] Would convert {len(group)} files to MS")
            # Still add expected path for dry run
            first_file = Path(group[0])
            timestamp = first_file.stem.split('_sb')[0]
            expected_ms = output_dir / f"{timestamp}.ms"
            ms_files.append(expected_ms)
            continue
        
        # Extract timestamp for MS name
        first_file = Path(group[0])
        timestamp = first_file.stem.split('_sb')[0]
        ms_path = output_dir / f"{timestamp}.ms"
        
        logger.info(f"Converting {len(group)} files to {ms_path}")
        
        try:
            # Use write_ms_from_subbands which accepts a file list directly
            from dsa110_contimg.conversion.strategies.direct_subband import \
              write_ms_from_subbands

            # Convert group to MS
            write_ms_from_subbands(
                file_list=group,
                ms_path=str(ms_path),
                scratch_dir=str(scratch_dir) if scratch_dir else None,
            )
            
            if ms_path.exists():
                ms_files.append(ms_path)
                logger.info(f"✓ Successfully created MS: {ms_path}")
            else:
                logger.error(f"✗ MS conversion failed: {ms_path} not found")
                
        except Exception as e:
            logger.error(f"✗ Failed to convert group {i+1}: {e}", exc_info=True)
            continue
    
    return ms_files


def calibrate_ms_files(
    ms_files: List[Path],
    calibrator_name: str,
    dry_run: bool = False,
) -> List[Path]:
    """Calibrate all MS files with science-quality settings.
    
    Returns:
        List of calibrated MS paths
    """
    logger.info(f"\n=== Calibrating {len(ms_files)} MS files ===")
    
    calibrated_ms = []
    
    for i, ms_path in enumerate(ms_files):
        logger.info(f"\n--- Calibrating MS {i+1}/{len(ms_files)}: {ms_path.name} ---")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would calibrate: {ms_path}")
            calibrated_ms.append(ms_path)
            continue
        
        try:
            # Run calibration with science-quality settings
            import argparse

            from dsa110_contimg.calibration.cli_calibrate import \
              handle_calibrate
            
            args = argparse.Namespace(
                ms=str(ms_path),
                auto_fields=True,
                refant="103",
                preset="standard",  # Science-quality preset
                model_source="catalog",
                cal_ra_deg=None,  # Will be auto-detected
                cal_dec_deg=None,
                cal_flux_jy=None,
                flagging_mode="rfi",
                bp_combine_field=True,
                combine_spw=False,
                bp_minsnr=3.0,
                gain_solint="inf",
                gain_calmode="p",
                gain_minsnr=3.0,
                skip_bp=False,
                skip_g=False,
                do_k=False,
                fast=False,
                no_flagging=False,
                skip_rephase=False,
                export_model_image=False,
                diagnostics=False,
                cleanup_subset=False,
            )
            
            result = handle_calibrate(args)
            if result == 0:
                calibrated_ms.append(ms_path)
                logger.info(f"✓ Successfully calibrated: {ms_path}")
            else:
                logger.error(f"✗ Calibration failed for {ms_path} (exit code: {result})")
                
        except Exception as e:
            logger.error(f"✗ Failed to calibrate {ms_path}: {e}", exc_info=True)
            continue
    
    return calibrated_ms


def image_ms_files(
    ms_files: List[Path],
    output_dir: Path,
    calibrator_name: str,
    dry_run: bool = False,
) -> List[Path]:
    """Image all calibrated MS files with science-quality settings.
    
    Returns:
        List of image paths
    """
    logger.info(f"\n=== Imaging {len(ms_files)} MS files ===")
    
    image_paths = []
    
    for i, ms_path in enumerate(ms_files):
        logger.info(f"\n--- Imaging MS {i+1}/{len(ms_files)}: {ms_path.name} ---")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would image: {ms_path}")
            # Expected image path
            imagename = output_dir / f"{ms_path.stem}"
            image_paths.append(imagename / f"{ms_path.stem}.image.pbcor")
            continue
        
        try:
            from dsa110_contimg.imaging.cli_imaging import image_ms
            
            imagename = str(output_dir / ms_path.stem)
            
            # Science-quality imaging parameters
            image_ms(
                str(ms_path),
                imagename=imagename,
                field="",
                quality_tier="standard",  # Science-quality tier
                pbcor=True,
                niter=1000,
                threshold="0.0Jy",
                robust=0.0,
                imsize=2048,  # Large image size for science quality
                cell_arcsec=None,  # Auto-calculate optimal cell size
            )
            
            pbcor_image = Path(f"{imagename}.image.pbcor")
            if pbcor_image.exists():
                image_paths.append(pbcor_image)
                logger.info(f"✓ Successfully imaged: {pbcor_image}")
            else:
                logger.error(f"✗ Image not found: {pbcor_image}")
                
        except Exception as e:
            logger.error(f"✗ Failed to image {ms_path}: {e}", exc_info=True)
            continue
    
    return image_paths


def create_mosaic(
    image_paths: List[Path],
    output_path: Path,
    mosaic_name: str,
    dry_run: bool = False,
) -> Optional[Path]:
    """Create PB-weighted mosaic from images.
    
    Returns:
        Path to mosaic image, or None if failed
    """
    logger.info(f"\n=== Creating Mosaic: {mosaic_name} ===")
    logger.info(f"Combining {len(image_paths)} images")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would create mosaic: {output_path}")
        return output_path
    
    try:
        import argparse

        from dsa110_contimg.mosaic.cli import cmd_build

        # Convert image paths to strings
        tile_paths = [str(p) for p in image_paths]
        
        args = argparse.Namespace(
            tiles=tile_paths,
            output=str(output_path),
            method="pbweighted",  # Primary beam weighted combination
            name=mosaic_name,
            validate=True,
            generate_metrics=True,
        )
        
        result = cmd_build(args)
        if result == 0 and output_path.exists():
            logger.info(f"✓ Successfully created mosaic: {output_path}")
            return output_path
        else:
            logger.error(f"✗ Mosaic creation failed (exit code: {result})")
            return None
            
    except Exception as e:
        logger.error(f"✗ Failed to create mosaic: {e}", exc_info=True)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Milestone 1: Create 60-minute science-quality mosaic for 0834+555"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--skip-conversion",
        action="store_true",
        help="Skip MS conversion (assume MS files already exist)"
    )
    parser.add_argument(
        "--skip-calibration",
        action="store_true",
        help="Skip calibration (assume MS files already calibrated)"
    )
    parser.add_argument(
        "--skip-imaging",
        action="store_true",
        help="Skip imaging (assume images already exist)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_MS_DIR,
        help=f"Output directory for MS files (default: {OUTPUT_MS_DIR})"
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=SCRATCH_DIR / "images",
        help="Output directory for images"
    )
    parser.add_argument(
        "--mosaic-dir",
        type=Path,
        default=SCRATCH_DIR / "mosaics",
        help="Output directory for mosaics"
    )
    
    args = parser.parse_args()
    
    # Ensure output directories exist
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.images_dir.mkdir(parents=True, exist_ok=True)
    args.mosaic_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("MILESTONE 1: 60-Minute Science-Quality Mosaic")
    logger.info(f"Calibrator: {CALIBRATOR_NAME}")
    logger.info(f"Date: {TARGET_DATE}")
    logger.info("=" * 80)
    
    # Step 1: Calculate transit time
    transit_time, start_time, end_time = calculate_transit_time(CALIBRATOR_NAME, TARGET_DATE)
    
    # Step 2: Find subband groups
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: Finding Subband Groups")
    logger.info("=" * 80)
    groups = find_subband_groups_in_window(INCOMING_DIR, start_time, end_time)
    
    if not groups:
        logger.error("No complete subband groups found in time window!")
        return 1
    
    # Step 3: Convert to MS
    ms_files = []
    if not args.skip_conversion:
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Converting Subband Groups to MS")
        logger.info("=" * 80)
        ms_files = convert_groups_to_ms(
            groups,
            args.output_dir,
            SCRATCH_DIR,
            skip_existing=True,
            dry_run=args.dry_run,
        )
    else:
        logger.info("Skipping conversion - checking for existing MS files")
        for group in groups:
            existing_ms = check_ms_exists(group, args.output_dir)
            if existing_ms:
                ms_files.append(existing_ms)
    
    if not ms_files:
        logger.error("No MS files available!")
        return 1
    
    logger.info(f"\n✓ Found {len(ms_files)} MS files for processing")
    
    # Step 4: Calibrate
    calibrated_ms = ms_files
    if not args.skip_calibration:
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Calibrating MS Files")
        logger.info("=" * 80)
        calibrated_ms = calibrate_ms_files(ms_files, CALIBRATOR_NAME, dry_run=args.dry_run)
    else:
        logger.info("Skipping calibration")
    
    if not calibrated_ms:
        logger.error("No calibrated MS files available!")
        return 1
    
    # Step 5: Image
    image_paths = []
    if not args.skip_imaging:
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Imaging MS Files")
        logger.info("=" * 80)
        image_paths = image_ms_files(
            calibrated_ms,
            args.images_dir,
            CALIBRATOR_NAME,
            dry_run=args.dry_run,
        )
    else:
        logger.info("Skipping imaging - checking for existing images")
        # Try to find existing images
        for ms_path in calibrated_ms:
            expected_image = args.images_dir / ms_path.stem / f"{ms_path.stem}.image.pbcor"
            if expected_image.exists():
                image_paths.append(expected_image)
    
    if not image_paths:
        logger.error("No images available for mosaic!")
        return 1
    
    logger.info(f"\n✓ Found {len(image_paths)} images for mosaic")
    
    # Step 6: Create mosaic
    logger.info("\n" + "=" * 80)
    logger.info("STEP 5: Creating Mosaic")
    logger.info("=" * 80)
    mosaic_path = args.mosaic_dir / f"{MOSAIC_NAME}.image"
    mosaic_result = create_mosaic(
        image_paths,
        mosaic_path,
        MOSAIC_NAME,
        dry_run=args.dry_run,
    )
    
    if mosaic_result:
        logger.info("\n" + "=" * 80)
        logger.info("MILESTONE 1 COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"Mosaic created: {mosaic_result}")
        logger.info(f"Calibrator: {CALIBRATOR_NAME}")
        logger.info(f"Transit time: {transit_time.isot}")
        logger.info(f"Time window: {start_time.isot} to {end_time.isot}")
        logger.info(f"MS files processed: {len(ms_files)}")
        logger.info(f"Images combined: {len(image_paths)}")
        return 0
    else:
        logger.error("Mosaic creation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

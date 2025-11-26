#!/opt/miniforge/envs/casa6/bin/python
"""Retroactively register existing staged data files in the data registry."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

from dsa110_contimg.database.data_config import get_staging_dir
from dsa110_contimg.database.data_registration import register_pipeline_data
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_existing_ms_files():
    """Register existing MS files in staging."""
    staging_dir = get_staging_dir("ms")
    ms_files = list(staging_dir.glob("*.ms"))
    
    logger.info(f"Found {len(ms_files)} MS files to register")
    
    registered = 0
    for ms_path in ms_files:
        if not ms_path.is_dir():
            continue
            
        data_id = str(ms_path)
        metadata = {}
        
        try:
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(str(ms_path))
            if start_mjd:
                metadata["start_mjd"] = start_mjd
            if end_mjd:
                metadata["end_mjd"] = end_mjd
            if mid_mjd:
                metadata["mid_mjd"] = mid_mjd
        except Exception as e:
            logger.debug(f"Could not extract MS time range for {ms_path}: {e}")
        
        if register_pipeline_data(
            data_type="ms",
            data_id=data_id,
            file_path=ms_path,
            metadata=metadata if metadata else None,
            auto_publish=True,
        ):
            registered += 1
            logger.info(f"Registered MS: {ms_path.name}")
        else:
            logger.warning(f"Failed to register MS: {ms_path.name}")
    
    return registered


def register_existing_calib_ms_files():
    """Register existing calibrated MS files in staging."""
    staging_dir = get_staging_dir("calib_ms")
    ms_files = list(staging_dir.glob("*.ms"))
    
    logger.info(f"Found {len(ms_files)} calibrated MS files to register")
    
    registered = 0
    for ms_path in ms_files:
        if not ms_path.is_dir():
            continue
            
        data_id = f"calib_{ms_path}"
        metadata = {
            "original_ms_path": str(ms_path),
            "calibration_applied": True,
        }
        
        try:
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(str(ms_path))
            if start_mjd:
                metadata["start_mjd"] = start_mjd
            if end_mjd:
                metadata["end_mjd"] = end_mjd
            if mid_mjd:
                metadata["mid_mjd"] = mid_mjd
        except Exception as e:
            logger.debug(f"Could not extract MS time range for {ms_path}: {e}")
        
        if register_pipeline_data(
            data_type="calib_ms",
            data_id=data_id,
            file_path=ms_path,
            metadata=metadata,
            auto_publish=True,
        ):
            registered += 1
            logger.info(f"Registered calibrated MS: {ms_path.name}")
        else:
            logger.warning(f"Failed to register calibrated MS: {ms_path.name}")
    
    return registered


def register_existing_images():
    """Register existing image files in staging."""
    staging_dir = get_staging_dir("image")  # data_type is "image" (singular)
    
    # Look for both .fits and .image files
    fits_files = list(staging_dir.rglob("*.fits")) if staging_dir.exists() else []
    image_files = list(staging_dir.rglob("*.image")) if staging_dir.exists() else []
    
    # Also check MS directories for image files (they might be co-located)
    ms_staging_dir = get_staging_dir("ms")
    ms_fits_files = list(ms_staging_dir.rglob("*.fits")) if ms_staging_dir.exists() else []
    
    all_images = fits_files + image_files + ms_fits_files
    
    logger.info(f"Found {len(all_images)} image files to register")
    
    registered = 0
    for img_path in all_images:
        if not img_path.is_file():
            continue
        
        # Skip auxiliary files (beam, psf, residual, etc.)
        if any(skip in img_path.name for skip in ["beam", "psf", "residual", "mask", "model", "sumwt"]):
            continue
        
        # Only register primary image files (those with "img-image" in name)
        # Skip other FITS files that are auxiliary products
        if "img-image" not in img_path.name:
            continue
        
        data_id = str(img_path)
        metadata = {}
        
        try:
            from casacore.images import image
            with image(str(img_path)) as img:
                shape = img.shape()
                metadata["shape"] = list(shape)
                metadata["has_data"] = len(shape) > 0 and all(s > 0 for s in shape)
        except Exception as e:
            logger.debug(f"Could not extract image metadata for {img_path}: {e}")
        
        if register_pipeline_data(
            data_type="image",
            data_id=data_id,
            file_path=img_path,
            metadata=metadata if metadata else None,
            auto_publish=True,
        ):
            registered += 1
            logger.info(f"Registered image: {img_path.name}")
        else:
            logger.warning(f"Failed to register image: {img_path.name}")
    
    return registered


def main():
    """Register all existing staged data."""
    logger.info("Starting retroactive registration of existing staged data...")
    
    ms_count = register_existing_ms_files()
    calib_ms_count = register_existing_calib_ms_files()
    image_count = register_existing_images()
    
    total = ms_count + calib_ms_count + image_count
    logger.info(f"\nRegistration complete:")
    logger.info(f"  MS files: {ms_count}")
    logger.info(f"  Calibrated MS files: {calib_ms_count}")
    logger.info(f"  Image files: {image_count}")
    logger.info(f"  Total: {total}")


if __name__ == "__main__":
    main()


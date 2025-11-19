#!/usr/bin/env python3
"""
Test cleaned imaging with deconvolution on calibrated data.
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# Debug imports
import dsa110_contimg
import dsa110_contimg.imaging.cli_imaging
print(f"DEBUG: dsa110_contimg file: {dsa110_contimg.__file__}")
print(f"DEBUG: cli_imaging file: {dsa110_contimg.imaging.cli_imaging.__file__}")

from dsa110_contimg.imaging.cli_imaging import image_ms

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOG = logging.getLogger("test_clean")

MS_PATH = "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms"
# Use /dev/shm for speed
TEMP_DIR = "/dev/shm/dsa110_clean_test"
FINAL_DIR = "/stage/dsa110-contimg/test_data"
IMAGE_PREFIX = os.path.join(TEMP_DIR, "test_clean_output")

def setup_dirs():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)
    
    # Clean up previous run in final dir
    for f in os.listdir(FINAL_DIR):
        if f.startswith("test_clean_output"):
            try:
                path = os.path.join(FINAL_DIR, f)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                LOG.warning(f"Could not remove {f}: {e}")

def main():
    setup_dirs()
    
    LOG.info("=" * 80)
    LOG.info("Running CLEANED imaging with deconvolution...")
    LOG.info("=" * 80)
    
    # Run cleaned imaging with:
    # - NVSS seeding (sky model)
    # - niter > 0 (actual deconvolution)
    # - Auto-masking enabled
    # - Primary beam correction
    clean_image_prefix = IMAGE_PREFIX + "_clean"
    
    image_ms(
        ms_path=MS_PATH,
        imagename=clean_image_prefix,
        imsize=5040,
        cell_arcsec=2.5,
        quality_tier="development",
        niter=10000,  # Enable cleaning
        threshold="0.0005Jy",  # Stop at 0.5 mJy
        nvss_min_mjy=10.0,  # Trigger NVSS seeding
        backend="wsclean",
        use_nvss_mask=False  # WSClean's auto-mask is better
    )
    
    LOG.info("=" * 80)
    LOG.info("Cleaning completed successfully!")
    LOG.info("=" * 80)
    
    # List output files
    LOG.info("Output files created:")
    for f in sorted(os.listdir(TEMP_DIR)):
        if f.startswith("test_clean_output"):
            size_mb = os.path.getsize(os.path.join(TEMP_DIR, f)) / 1024 / 1024
            LOG.info(f"  {f:60s} {size_mb:8.2f} MB")
    
    # Copy final images to /stage/ for inspection
    LOG.info("\nCopying final images to /stage/ for inspection...")
    for ext in ['-image.fits', '-residual.fits', '-model.fits', '-image-pb.fits']:
        src = f"{clean_image_prefix}{ext}"
        if os.path.exists(src):
            dst = os.path.join(FINAL_DIR, f"test_clean_output{ext}")
            shutil.copy2(src, dst)
            LOG.info(f"  Copied: {os.path.basename(dst)}")

if __name__ == "__main__":
    main()

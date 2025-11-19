import logging
import os
import shutil
import sys

import numpy as np
from astropy.io import fits

# Debug imports
import dsa110_contimg
import dsa110_contimg.imaging.cli_imaging

print(f"DEBUG: dsa110_contimg file: {dsa110_contimg.__file__}")
print(f"DEBUG: cli_imaging file: {dsa110_contimg.imaging.cli_imaging.__file__}")

from dsa110_contimg.imaging.cli_imaging import image_ms

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOG = logging.getLogger("test_masking")

MS_PATH = "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms"
# Use /dev/shm for speed, then move to stage
TEMP_DIR = "/dev/shm/dsa110_masking_test"
FINAL_DIR = "/stage/dsa110-contimg/test_data"
IMAGE_PREFIX = os.path.join(TEMP_DIR, "test_masking_output")


def setup_dirs():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    # Clean up previous run in final dir
    for f in os.listdir(FINAL_DIR):
        if f.startswith("test_masking_output"):
            try:
                os.remove(os.path.join(FINAL_DIR, f))
            except Exception as e:
                LOG.warning(f"Could not remove {f}: {e}")


def main():
    setup_dirs()

    # Just test the seeding step - dirty image with NVSS seeding
    LOG.info("Testing NVSS seeding with WSClean...")
    dirty_image_prefix = IMAGE_PREFIX + "_dirty"

    # This should trigger wsclean -draw-model then -predict
    image_ms(
        ms_path=MS_PATH,
        imagename=dirty_image_prefix,
        imsize=5040,
        cell_arcsec=2.5,
        quality_tier="development",
        niter=0,  # Dirty image
        nvss_min_mjy=10.0,  # Trigger seeding
        backend="wsclean",
        use_nvss_mask=False,
    )

    LOG.info("Test completed successfully!")


if __name__ == "__main__":
    main()

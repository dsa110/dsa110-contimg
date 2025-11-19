import logging
import os
import shutil
import sys

import numpy as np
from astropy.io import fits

from dsa110_contimg.imaging.cli_imaging import image_ms

# Setup logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("test_masking")

MS_PATH = "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms"
IMAGE_PREFIX = "/stage/dsa110-contimg/test_data/test_masking_output"


def create_dummy_mask(template_fits, filename):
    """Create a dummy FITS mask using template header."""
    with fits.open(template_fits) as hdul:
        header = hdul[0].header
        shape = hdul[0].data.shape

        # Handle 2D or 4D images
        if len(shape) == 4:
            # (n_pols, n_freqs, y, x)
            img_shape = (shape[2], shape[3])
        else:
            img_shape = shape

        mask_data = np.zeros(img_shape, dtype=np.float32)

        # Create a circle in the middle
        y, x = np.ogrid[: img_shape[0], : img_shape[1]]
        center = (img_shape[0] // 2, img_shape[1] // 2)
        radius = img_shape[0] // 4
        mask = ((x - center[1]) ** 2 + (y - center[0]) ** 2) <= radius**2
        mask_data[mask] = 1.0

        # WSClean expects a 2D mask usually, but let's match dimensions?
        # WSClean mask should be 2D

        hdu = fits.PrimaryHDU(data=mask_data, header=header)
        hdu.writeto(filename, overwrite=True)
        return filename


def test_masking_imaging():
    if not os.path.exists(MS_PATH):
        LOG.error(f"Test MS not found: {MS_PATH}")
        return

    # 1. Run dirty imaging to get WCS
    LOG.info("Running dirty imaging to get template...")
    dirty_prefix = f"{IMAGE_PREFIX}_dirty"
    try:
        image_ms(
            ms_path=MS_PATH,
            imagename=dirty_prefix,
            imsize=1024,
            cell_arcsec=2.5,
            backend="wsclean",
            niter=0,  # Dirty only
            quality_tier="development",
        )
        LOG.info("Dirty imaging completed.")
    except Exception as e:
        LOG.error(f"Dirty imaging failed: {e}")
        import traceback

        traceback.print_exc()
        return

    dirty_image = f"{dirty_prefix}-image.fits"
    if not os.path.exists(dirty_image):
        LOG.error(f"Dirty image not found: {dirty_image}")
        return

    # 2. Create masks
    mask_path = f"{IMAGE_PREFIX}_mask.fits"
    create_dummy_mask(dirty_image, mask_path)
    LOG.info(f"Created dummy mask at {mask_path}")

    clip_path = f"{IMAGE_PREFIX}_clip.fits"
    create_dummy_mask(dirty_image, clip_path)
    LOG.info(f"Created dummy clip image at {clip_path}")

    # 3. Run imaging with advanced masking options
    LOG.info("Running imaging with advanced masking...")
    try:
        image_ms(
            ms_path=MS_PATH,
            imagename=IMAGE_PREFIX,
            imsize=1024,
            cell_arcsec=2.5,
            backend="wsclean",
            niter=100,
            mask_path=mask_path,
            galvin_clip_mask=clip_path,
            erode_beam_shape=True,
            quality_tier="development",
        )
        LOG.info("Imaging completed successfully.")
    except Exception as e:
        LOG.error(f"Imaging failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_masking_imaging()

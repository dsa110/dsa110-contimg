#!/usr/bin/env python3
import logging
import os
import shutil
from pathlib import Path

from casatasks import applycal, tclean

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """
    Applies calibration and creates a cleaned image from a Measurement Set.
    """
    # Find the newest Measurement Set
    ms_candidates = sorted(Path('data/ms').glob('*.ms'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not ms_candidates:
        logger.error("No MS files found in data/ms/")
        return
    ms_path = str(ms_candidates[0])

    # Define calibration tables
    bcal_table = 'data/cal_tables/test_calibration_bandpass.bcal'
    gcal_table = 'data/cal_tables/test_calibration_final_gain.gcal'

    # QA for calibration tables
    for cal_table in [bcal_table, gcal_table]:
        logger.info(f"Checking cal table: {cal_table}")
        if not os.path.exists(cal_table):
            logger.error(f"  MISSING: {cal_table}")
            print("Calibration tables QA failed")
            return

    logger.info(f"Using MS: {ms_path}")
    logger.info(f"Using bcal table: {bcal_table}")
    logger.info(f"Using gcal table: {gcal_table}")

    # Define output imagename
    imagename = 'images/clean_image'

    # Clean up previous imaging products if they exist
    for ext in ['.image', '.model', '.pb', '.psf', '.residual', '.sumwt']:
        path_to_remove = f"{imagename}{ext}"
        if os.path.exists(path_to_remove):
            logger.info(f"Removing existing file: {path_to_remove}")
            shutil.rmtree(path_to_remove)

    # Apply calibration tables
    applycal(
        vis=ms_path,
        gaintable=[bcal_table, gcal_table],
        gainfield=['', ''],
        interp=['nearest', 'linear']
    )
    logger.info("Calibration tables applied successfully.")

    # Run tclean to produce a cleaned image
    logger.info("Starting tclean for deconvolution...")
    tclean(
        vis=ms_path,
        imagename=imagename,
        specmode='mfs',
        deconvolver='hogbom',
        imsize=[4096, 4096],
        cell=['2.0arcsec', '2.0arcsec'],
        weighting='briggs',
        robust=0.5,
        gridder='standard',
        pbcor=False,
        niter=1000,
        threshold='0.75mJy',
        usemask='auto-multithresh'
    )
    logger.info(f"Deconvolution complete. Cleaned image saved to {imagename}.image")


if __name__ == '__main__':
    main()



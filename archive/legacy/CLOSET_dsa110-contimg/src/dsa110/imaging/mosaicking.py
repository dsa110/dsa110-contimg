# pipeline/mosaicking.py

import os
import numpy as np
from shutil import rmtree

# Astropy imports
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.table import Table
import astropy.units as u

# CASA imports
try:
    from casatools import linearmosaic, msmetadata, image # Added image tool
    from casatasks import exportfits # Keep exportfits here if imaging module isn't imported
    casa_available = True
except ImportError:
    print("Warning: CASA tools/tasks not found. Mosaicking module functionality will be limited.")
    casa_available = False

# Pipeline imports
from .pipeline_utils import get_logger
# Import imaging functions if they handle export/plotting, otherwise keep them here
from .imaging import export_image_to_fits, plot_image

logger = get_logger(__name__)

# --- Helper Function ---

def _calculate_mosaic_center(config: dict, image_list: list):
    """Calculates the approximate center for the mosaic from input images."""
    if not image_list:
        logger.error("Cannot calculate mosaic center: image_list is empty.")
        return None

    logger.info(f"Calculating mosaic center from {len(image_list)} input images.")
    ras = []
    decs = []

    # Use CASA image tool to get phase centers more reliably than FITS headers initially
    ia = None
    if casa_available:
        try:
            ia = image()
            for image_path in image_list:
                if os.path.exists(image_path):
                    try:
                        ia.open(image_path)
                        cs = ia.coordsys()
                        direction = cs.referencevalue(type='direction') # Get direction ref value
                        ras.append(direction['numeric'][0]) # RA in radians
                        decs.append(direction['numeric'][1]) # Dec in radians
                        cs.done()
                        ia.close()
                    except Exception as e_img:
                        logger.warning(f"Could not get phase center from {image_path} using CASA tools: {e_img}. Skipping this image for center calculation.")
                else:
                    logger.warning(f"Image path {image_path} not found. Skipping for center calculation.")

            if ia and ia.isopen(): ia.done() # Close tool if left open

        except Exception as e_ia:
            logger.error(f"Failed to use CASA image tool for center calculation: {e_ia}. Falling back to FITS WCS (if available).")
            ras, decs = [], [] # Reset lists for fallback
            if 'ia' in locals() and ia is not None and ia.isopen(): ia.done()


    # Fallback or primary method: Use FITS WCS if CASA failed or preferred
    if not ras or not decs:
        logger.info("Attempting to calculate center using FITS WCS headers...")
        for image_path in image_list:
            fits_path = f"{os.path.splitext(image_path)[0]}.fits"
            if os.path.exists(fits_path):
                try:
                    with fits.open(fits_path) as hdul:
                        w = WCS(hdul[0].header).celestial
                        # Get center pixel coords and convert to world
                        center_pix = [(ax / 2.0) for ax in w.pixel_shape]
                        center_coord = w.pixel_to_world(*center_pix)
                        ras.append(center_coord.ra.rad)
                        decs.append(center_coord.dec.rad)
                except Exception as e_fits:
                    logger.warning(f"Could not get WCS center from {fits_path}: {e_fits}. Skipping.")
            else:
                logger.warning(f"FITS file {fits_path} not found for WCS center calculation. Skipping.")

    if not ras or not decs:
        logger.error("Failed to determine mosaic center from any input images.")
        return None

    # Calculate mean RA/Dec in radians, handling RA wrap-around carefully
    # Convert RA radians to complex numbers on unit circle, average, convert back
    mean_ra_rad = np.arctan2(np.mean(np.sin(ras)), np.mean(np.cos(ras)))
    mean_dec_rad = np.mean(decs)

    center_coord = SkyCoord(ra=mean_ra_rad*u.rad, dec=mean_dec_rad*u.rad, frame='icrs')
    logger.info(f"Calculated mosaic center: {center_coord.to_string('hmsdms')}")

    # Format for CASA (e.g., J2000 HHhMMmSS.s +DDdMMmSS.s)
    casa_center_str = f"J2000 {center_coord.ra.to_string(unit=u.hour, sep='hms', precision=4)} {center_coord.dec.to_string(unit=u.deg, sep='dms', precision=3, alwayssign=True)}"
    logger.debug(f"Formatted CASA center string: {casa_center_str}")

    return casa_center_str


# --- Main Mosaicking Function ---

def create_mosaic(config: dict, image_list: list, pb_list: list, output_mosaic_basename: str):
    """Creates a mosaic from a list of images and primary beam files."""
    if not casa_available:
        logger.error("CASA not available, cannot create mosaic.")
        return None, None # Return None for mosaic path, None for weight path
    if not image_list or not pb_list or len(image_list) != len(pb_list):
        logger.error(f"Invalid input lists for mosaicking. Images: {len(image_list)}, PBs: {len(pb_list)}")
        return None, None

    logger.info(f"Starting mosaic creation for {output_mosaic_basename} using {len(image_list)} images.")
    paths_config = config['paths']
    mosaic_config = config.get('mosaicking', {})
    mosaic_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['mosaics_dir'])
    os.makedirs(mosaic_dir, exist_ok=True)

    # Define output paths
    mosaic_image_path = os.path.join(mosaic_dir, f"{output_mosaic_basename}.linmos")
    mosaic_weight_path = os.path.join(mosaic_dir, f"{output_mosaic_basename}.weightlinmos")

    # --- Check Inputs Exist ---
    missing_files = False
    for f in image_list + pb_list:
        if not os.path.exists(f):
            logger.error(f"Input file for mosaicking not found: {f}")
            missing_files = True
    if missing_files:
        return None, None

    # --- Determine Mosaic Center ---
    phase_center = _calculate_mosaic_center(config, image_list)
    if phase_center is None:
        logger.error("Could not determine phase center for mosaic. Aborting.")
        return None, None

    # --- Clean Up Old Outputs ---
    logger.debug("Checking for and removing old mosaic products...")
    for path in [mosaic_image_path, mosaic_weight_path]:
         if os.path.exists(path):
              logger.warning(f"Removing existing mosaic product: {path}")
              try:
                   if os.path.isdir(path): rmtree(path)
                   else: os.remove(path)
              except Exception as e:
                   logger.error(f"Failed to remove {path}: {e}. Mosaicking may fail.")

    # --- Setup linearmosaic ---
    try:
        lm = linearmosaic()

        # Set mosaic type (e.g., optimal, pbweight)
        lm.setlinmostype(mosaic_config.get('mosaic_type', 'optimal'))

        # Define output image grid
        # TODO: Determine nx, ny automatically? Complex. Use config for now.
        nx = mosaic_config.get('mosaic_nx', 28800) #None)
        ny = mosaic_config.get('mosaic_ny', 4800) #None)
        cell = mosaic_config.get('mosaic_cell', '3arcsec')
        if nx is None or ny is None:
             logger.error("Mosaic dimensions (mosaic_nx, mosaic_ny) must be set in config.")
             return None, None

        logger.info(f"Defining output mosaic grid: nx={nx}, ny={ny}, cell={cell}, center={phase_center}")
        lm.defineoutputimage(
            nx=nx, ny=ny,
            cellx=cell, celly=cell, # Assume square pixels
            imagecenter=phase_center,
            outputimage=mosaic_image_path,
            outputweight=mosaic_weight_path
        )

        # --- Run Mosaicking ---
        logger.info("Running linearmosaic makemosaic...")
        lm.makemosaic(images=image_list, weightimages=pb_list)
        logger.info("Mosaic creation successful.")

        lm.done() # Close the tool

    except Exception as e:
        logger.error(f"Linearmosaic task failed: {e}", exc_info=True)
        if 'lm' in locals(): lm.done() # Ensure tool is closed
        # Clean up partial outputs
        if os.path.exists(mosaic_image_path): rmtree(mosaic_image_path)
        if os.path.exists(mosaic_weight_path): rmtree(mosaic_weight_path)
        return None, None


    # --- Optional: Export FITS and Plot ---
    mosaic_fits_path = None
    if mosaic_config.get('save_fits', True):
        # Note: We assume export_image_to_fits and plot_image exist and work
        # They might need adaptation if called from here vs. imaging module directly
        logger.info("Exporting mosaic image to FITS...")
        mosaic_fits_path = export_image_to_fits(config, mosaic_image_path, suffix='.linmos')
        if mosaic_fits_path:
            # Plotting needs to be adapted for potentially large mosaics
            # plot_image(config, mosaic_fits_path, plot_suffix='.linmos')
             logger.info(f"Plotting for mosaic {mosaic_fits_path} can be added here.")
             # Consider generating plots separately due to potential size/time

    # Also export weight image if desired
    # mosaic_weight_fits_path = export_image_to_fits(config, mosaic_weight_path, suffix='.weightlinmos')


    return mosaic_image_path, mosaic_weight_path # Return paths to CASA images
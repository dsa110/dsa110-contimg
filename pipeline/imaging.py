# pipeline/imaging.py

import os
import numpy as np
from shutil import rmtree

# Astropy imports (for plotting)
try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from astropy.io import fits
    from astropy.wcs import WCS
    from astropy.visualization import (ZScaleInterval, PowerStretch, ImageNormalize)
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    plotting_available = True
except ImportError:
    print("Warning: Matplotlib/AstroPy components not found. Plotting functionality will be disabled.")
    plotting_available = False


# CASA imports
try:
    from casatasks import makemask, tclean, exportfits, immath # Added immath for potential mask manipulation
    casa_available = True
except ImportError:
    print("Warning: CASA tasks not found. Imaging module functionality will be limited.")
    # Only set to False if it wasn't already False
    if 'casa_available' not in locals() or casa_available:
        casa_available = False


# Pipeline imports
from .pipeline_utils import get_logger

logger = get_logger(__name__)


# --- Mask Creation ---

def create_clean_mask(config: dict, cl_path: str, template_image_path: str, output_mask_path: str):
    """Creates a clean mask from a component list using an image template."""
    if not casa_available:
        logger.error("CASA not available, cannot create mask.")
        return None
    if not os.path.exists(cl_path):
        logger.error(f"Component list not found for mask creation: {cl_path}")
        return None
    if not os.path.exists(template_image_path):
        logger.error(f"Template image not found for mask creation: {template_image_path}")
        # TODO: Add logic to *create* a template image if none exists based on config?
        return None

    logger.info(f"Creating clean mask {output_mask_path} from {cl_path} using template {template_image_path}")
    os.makedirs(os.path.dirname(output_mask_path), exist_ok=True)

    imaging_config = config.get('imaging', {})
    # mask_padding = imaging_config.get('mask_padding_factor', 1.5) # Example config param

    if os.path.exists(output_mask_path):
        logger.warning(f"Mask file {output_mask_path} already exists. Removing.")
        try:
            # makemask might handle overwrite, but be explicit
            if os.path.isdir(output_mask_path): # CASA masks are directories
                 rmtree(output_mask_path)
            else:
                 os.remove(output_mask_path)
        except Exception as e:
            logger.error(f"Failed to remove existing mask: {e}")
            return None

    try:
        # Use makemask to copy the template and apply the component list regions
        # Mode 'copy' creates the output based on template image structure.
        # inpmask here refers to the component list or region file defining *where* to mask.
        makemask(
            mode='copy',
            inpimage=template_image_path, # Defines the mask shape, WCS, etc.
            inpmask=cl_path,             # Component list defining regions to UNMASK (set to 1)
            output=f"'{output_mask_path}:mask0'", # CASA syntax: 'maskname:region_name' creates region 'mask0'
            overwrite=True # Ensure overwrite works
        )
        # Optionally expand the mask regions here using immath or makemask again
        # e.g., makemask(mode='expand', inpmask=output_mask_path+":mask0", ...)

        logger.info(f"Successfully created clean mask: {output_mask_path}")
        return output_mask_path
    except Exception as e:
        logger.error(f"makemask task failed: {e}", exc_info=True)
        if os.path.exists(output_mask_path): rmtree(output_mask_path) # Clean up
        return None

# --- Imaging Function ---

def run_tclean(config: dict, ms_path: str, output_imagename: str, cl_path: str = None, mask_path: str = None):
    """Runs CASA tclean on a Measurement Set."""
    if not casa_available:
        logger.error("CASA not available, cannot run tclean.")
        return None
    if not os.path.exists(ms_path):
        logger.error(f"MS file not found for tclean: {ms_path}")
        return None

    logger.info(f"Running tclean on {ms_path}")
    logger.info(f"Output imagename base: {output_imagename}")

    img_config = config.get('imaging', {})
    cal_config = config.get('calibration', {}) # May need refant or other cal info?

    # Prepare tclean parameters from config
    tclean_params = {
        'vis': ms_path,
        'imagename': output_imagename,
        'specmode': 'mfs', # Continuum imaging
        'deconvolver': img_config.get('deconvolver', 'hogbom'),
        'gridder': img_config.get('gridder', 'wproject'),
        'wprojplanes': img_config.get('wprojplanes', -1),
        'niter': img_config.get('niter', 5000),
        'threshold': img_config.get('threshold', '1mJy'),
        'interactive': False,
        'imsize': img_config.get('image_size', [4800, 4800]),
        'cell': img_config.get('cell_size', '3arcsec'),
        'weighting': img_config.get('weighting', 'briggs'),
        'robust': img_config.get('robust', 0.5),
        'pblimit': img_config.get('pblimit', 0.1),
        'pbcor': True, # Create PB-corrected image (.image.pbcor)
        'savemodel': 'modelcolumn', # Save model to MODEL_DATA column
        # Add other potential tclean params: phasecenter, uvrange, scales (for multiscale) etc.
        # 'phasecenter': ... # Get from MS metadata or config if needed
        # 'uvrange': cal_config.get('gcal_uvrange', '') # Use same uvrange as gaincal?
    }

    # Handle start model
    if cl_path and os.path.exists(cl_path):
         tclean_params['startmodel'] = cl_path
         logger.info(f"Using start model: {cl_path}")
    else:
         # Default is no start model (empty string not needed)
         pass

    # Handle mask
    use_mask_config = img_config.get('use_clean_mask', False)
    if use_mask_config and mask_path and os.path.exists(mask_path):
        tclean_params['usemask'] = 'user'
        tclean_params['mask'] = mask_path
        logger.info(f"Using user mask: {mask_path}")
    elif use_mask_config:
        logger.warning(f"Config specifies use_clean_mask=True, but no valid mask_path provided ({mask_path}). No mask used.")
    else:
        logger.info("No user mask specified.")

    # Clean up previous run outputs (tclean doesn't always overwrite reliably)
    extensions = ['.image', '.mask', '.model', '.image.pbcor', '.psf', '.residual', '.pb', '.sumwt']
    logger.debug(f"Checking for and removing old tclean products for {output_imagename}")
    for ext in extensions:
        product_path = f"{output_imagename}{ext}"
        if os.path.exists(product_path):
            try:
                logger.warning(f"Removing existing product: {product_path}")
                if os.path.isdir(product_path):
                     rmtree(product_path)
                else:
                     os.remove(product_path)
            except Exception as e:
                logger.error(f"Failed to remove existing product {product_path}: {e}. Tclean may fail.")


    # --- Run tclean ---
    try:
        tclean(**tclean_params)
        logger.info(f"tclean completed successfully for {output_imagename}")

        # Check for primary output product existence
        if not os.path.exists(f"{output_imagename}.image"):
             logger.error("tclean finished but output image is missing!")
             return None

        # Export FITS if requested
        if img_config.get('save_fits', True):
             export_image_to_fits(config, f"{output_imagename}.image") # Export .image (non-PB corrected)
             # Optionally export PB-corrected image too
             if os.path.exists(f"{output_imagename}.image.pbcor"):
                  export_image_to_fits(config, f"{output_imagename}.image.pbcor", suffix='.pbcor')

        return output_imagename # Return base name of created images

    except Exception as e:
        logger.error(f"tclean task failed for {output_imagename}: {e}", exc_info=True)
        return None


# --- FITS Export ---

def export_image_to_fits(config: dict, image_path: str, suffix=''):
    """Exports a CASA image to FITS format."""
    if not casa_available:
        logger.error("CASA not available, cannot export to FITS.")
        return None
    if not os.path.exists(image_path):
        logger.error(f"CASA image not found for FITS export: {image_path}")
        return None

    fits_path = f"{os.path.splitext(image_path)[0]}{suffix}.fits" # e.g., basename.image.fits or basename.image.pbcor.fits
    logger.info(f"Exporting {image_path} to {fits_path}")

    if os.path.exists(fits_path):
        logger.warning(f"FITS file {fits_path} already exists. Overwriting.")
        try:
            os.remove(fits_path)
        except Exception as e:
            logger.error(f"Failed to remove existing FITS file: {e}")
            # Proceed with export anyway, exportfits might handle it

    try:
        exportfits(imagename=image_path, fitsimage=fits_path, overwrite=True)
        logger.info(f"Successfully exported FITS file: {fits_path}")
        return fits_path
    except Exception as e:
        logger.error(f"exportfits task failed for {image_path}: {e}", exc_info=True)
        return None

# --- Diagnostic Plotting ---

def plot_image(config: dict, fits_path: str, source_table: Table = None, plot_suffix: str = ""):
    """Creates a diagnostic plot of a FITS image with optional source overlays."""
    if not plotting_available:
        logger.warning("Plotting libraries not available, skipping plot generation.")
        return None
    if not os.path.exists(fits_path):
        logger.error(f"FITS file not found for plotting: {fits_path}")
        return None

    logger.info(f"Generating diagnostic plot for {fits_path}")
    paths_config = config['paths']
    diag_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['diagnostics_base_dir'], 'imaging')
    os.makedirs(diag_dir, exist_ok=True)
    plot_filename = f"{os.path.basename(os.path.splitext(fits_path)[0])}{plot_suffix}.png" # e.g., basename.image.png
    plot_filepath = os.path.join(diag_dir, plot_filename)

    try:
        with fits.open(fits_path) as hdul:
            hdu = hdul[0]
            # Handle potentially >2D images (use WCS dropaxis)
            while hdu.data.ndim > 2:
                hdu.data = hdu.data[0] # Take first plane along leading axes
            if hdu.data.ndim != 2:
                 raise ValueError(f"Could not reduce FITS data in {fits_path} to 2 dimensions.")

            wcs = WCS(hdu.header).celestial # Get celestial WCS part

            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection=wcs)

            # Basic normalization (adjust as needed)
            norm = ImageNormalize(hdu.data, interval=ZScaleInterval(), stretch=PowerStretch(a=0.8))
            im = ax.imshow(hdu.data, cmap='gray_r', norm=norm, origin='lower')

            if source_table is not None and len(source_table) > 0:
                 try:
                     # Assumes source_table has RA/Dec columns parsable by SkyCoord
                     coords = SkyCoord(source_table['RAJ2000'], source_table['DEJ2000'], unit=(u.hourangle, u.deg), frame='icrs')
                     pixels = wcs.world_to_pixel(coords)
                     # Plot circles around sources
                     ax.scatter(pixels[0], pixels[1], facecolor='none', edgecolor='red', s=80, lw=0.8, label='Model Sources')
                     ax.legend()
                 except Exception as e_src:
                     logger.warning(f"Could not plot source overlays: {e_src}")

            ax.set_xlabel('Right Ascension')
            ax.set_ylabel('Declination')
            ax.set_title(os.path.basename(fits_path))
            plt.colorbar(im, ax=ax, label='Flux Density (Jy/beam?)') # Label needs verification
            plt.grid(color='lightgrey', ls='dotted')
            fig.savefig(plot_filepath)
            plt.close(fig)
            logger.info(f"Saved diagnostic plot: {plot_filepath}")
            return plot_filepath

    except Exception as e:
        logger.error(f"Failed to plot image {fits_path}: {e}", exc_info=True)
        if 'fig' in locals() and fig is not None: plt.close(fig) # Ensure plot is closed on error
        return None
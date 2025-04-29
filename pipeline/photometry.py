# pipeline/photometry.py

import os
import numpy as np
import sqlite3
import warnings
from datetime import datetime

# Astropy imports
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astropy.io import fits
from astropy.table import Table, vstack, hstack, Column
from astropy.time import Time
from astropy.wcs import WCS
import astropy.units as u

# Photutils imports
try:
    from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry
    from photutils.background import LocalBackground, Background2D, MedianBackground
    from photutils.segmentation import detect_threshold, detect_sources
    from photutils.utils import calc_total_error
    photutils_available = True
except ImportError:
    print("Warning: photutils not found. Photometry module functionality will be disabled.")
    photutils_available = False

# Astroquery import (for querying NVSS again on the specific mosaic area)
try:
    from astroquery.vizier import Vizier
    Vizier.ROW_LIMIT = -1
    Vizier.columns = ["*"]
    astroquery_available = True
except ImportError:
    print("Warning: astroquery not found. NVSS querying will be disabled.")
    astroquery_available = False

# Pipeline imports
from .pipeline_utils import get_logger

logger = get_logger(__name__)

# --- Database Handling ---

def _connect_db(config: dict):
    """Connects to the photometry database."""
    phot_config = config.get('photometry', {})
    paths_config = config['paths']
    db_type = phot_config.get('database_type', 'sqlite')
    conn = None

    if db_type == 'sqlite':
        db_path = os.path.join(paths_config['pipeline_base_dir'], paths_config['photometry_dir'], phot_config.get('database_path', 'photometry_store.db'))
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        try:
            conn = sqlite3.connect(db_path, timeout=10) # Added timeout
            logger.info(f"Connected to SQLite database: {db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite database {db_path}: {e}", exc_info=True)
            return None
    # Add 'postgresql' connection logic here if needed using psycopg2
    # elif db_type == 'postgresql':
    #     conn_string = phot_config.get('database_connection_string')
    #     if not conn_string:
    #         logger.error("database_connection_string missing in config for postgresql.")
    #         return None
    #     try:
    #         import psycopg2
    #         conn = psycopg2.connect(conn_string)
    #         logger.info("Connected to PostgreSQL database.")
    #     except ImportError:
    #         logger.error("psycopg2 library required for PostgreSQL connection.")
    #         return None
    #     except Exception as e:
    #          logger.error(f"Failed to connect to PostgreSQL database: {e}", exc_info=True)
    #          return None
    else:
        logger.error(f"Unsupported database_type in config: {db_type}")
        return None

    return conn

def _init_db(conn, config: dict):
    """Initializes the photometry database table if it doesn't exist."""
    if conn is None:
        logger.error("Database connection is None, cannot initialize.")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photometry_measurements (
                source_id TEXT NOT NULL,            -- Unique source identifier (e.g., NVSS name)
                mjd REAL NOT NULL,                  -- Modified Julian Date of observation midpoint
                mosaic_time_utc TEXT NOT NULL,      -- ISO timestamp string of observation midpoint
                relative_flux REAL,                 -- Calculated relative flux
                relative_flux_error REAL,           -- Error on relative flux
                instrumental_flux REAL,             -- Measured instrumental flux (bkg subtracted)
                instrumental_flux_error REAL,       -- Error on instrumental flux
                background REAL,                    -- Estimated background level
                photometry_flags INTEGER DEFAULT 0, -- Bitmask for flags (e.g., near edge, saturated)
                reference_source_ids TEXT,          -- Comma-separated list of reference IDs used
                median_reference_flux REAL,         -- Median flux of the reference ensemble
                PRIMARY KEY (source_id, mjd)       -- Ensure unique entry per source per time
            )
        """)
        # Add indices for faster querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_id ON photometry_measurements (source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mjd ON photometry_measurements (mjd)")
        conn.commit()
        logger.info("Database table 'photometry_measurements' initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database table: {e}", exc_info=True)
        return False

# --- Source Identification ---

def _get_nvss_sources(config: dict, mosaic_fits_path: str):
    """Queries NVSS for sources within the footprint of the mosaic."""
    if not astroquery_available:
        logger.error("astroquery unavailable, cannot query NVSS.")
        return None
    if not os.path.exists(mosaic_fits_path):
        logger.error(f"Mosaic FITS file not found: {mosaic_fits_path}")
        return None

    logger.info(f"Querying NVSS for sources within footprint of {mosaic_fits_path}")
    skymodel_config = config.get('skymodel', {})
    nvss_cat_info = skymodel_config.get('primary_catalog', {}) # Get catalog info from config
    nvss_code = nvss_cat_info.get('vizier_code', 'VIII/65/nvss') # Default if not in config

    try:
        with fits.open(mosaic_fits_path) as hdul:
            wcs = WCS(hdul[0].header).celestial
            # Get footprint corners (approximate)
            corners_pix = np.array([[0, 0], [0, hdul[0].data.shape[-2]], [hdul[0].data.shape[-1], hdul[0].data.shape[-2]], [hdul[0].data.shape[-1], 0]])
            corners_world = wcs.pixel_to_world(corners_pix[:, 0], corners_pix[:, 1])
            center_coord = corners_world.mean() # Approximate center
            # Estimate radius needed to cover the image - use diagonal
            width = corners_world[0].separation(corners_world[3])
            height = corners_world[0].separation(corners_world[1])
            radius = max(width, height) / 2.0 * 1.1 # Add 10% buffer

        logger.info(f"Querying NVSS ({nvss_code}) around {center_coord.to_string('hmsdms')} with radius {radius.to(u.deg):.2f}")
        nvss_result = Vizier.query_region(center_coord, radius=radius, catalog=nvss_code)

        if not nvss_result:
            logger.warning(f"No NVSS sources found within mosaic footprint.")
            return None
        nvss_table = nvss_result[0]
        logger.info(f"Found {len(nvss_table)} NVSS sources in footprint.")

        # Add unique ID column if not present - using NVSS name if available
        if 'NVSS' in nvss_table.colnames and nvss_table['NVSS'].dtype == object: # Check if NVSS name exists and is string-like
             nvss_table['source_id'] = [f"NVSS_{n}" if n else f"NVSS_{r}_{d}".replace(':','').replace('.','p').replace('+','p').replace('-','m')
                                        for n, r, d in zip(nvss_table['NVSS'], nvss_table['RAJ2000'], nvss_table['DEJ2000'])]
        else:
             # Create ID from coordinates if NVSS name is missing/unsuitable
             nvss_table['source_id'] = [f"NVSS_{r}_{d}".replace(':','').replace('.','p').replace('+','p').replace('-','m')
                                        for r, d in zip(nvss_table['RAJ2000'], nvss_table['DEJ2000'])]

        return nvss_table

    except Exception as e:
        logger.error(f"Failed during NVSS query or footprint calculation: {e}", exc_info=True)
        return None


def identify_sources(config: dict, mosaic_fits_path: str):
    """Identifies target and reference sources from NVSS catalog within the mosaic."""
    phot_config = config.get('photometry', {})
    target_min_flux_mjy = phot_config.get('target_nvss_min_flux_mjy', 5.0)
    ref_min_flux_mjy = phot_config.get('reference_min_catalog_flux_mjy', 100.0)
    ref_max_flux_mjy = phot_config.get('reference_max_catalog_flux_mjy', 5000.0)

    # Get NVSS sources in the mosaic area
    nvss_table = _get_nvss_sources(config, mosaic_fits_path)
    if nvss_table is None:
        logger.error("Could not retrieve NVSS source list.")
        return None, None # Return None for targets, None for references

    # Get primary catalog flux column name
    skymodel_config = config.get('skymodel', {})
    nvss_flux_col = skymodel_config.get('primary_catalog', {}).get('flux_column', 'S1.4')
    if nvss_flux_col not in nvss_table.colnames:
        logger.error(f"NVSS flux column '{nvss_flux_col}' not found in retrieved table.")
        return None, None

    # Filter out sources with invalid flux
    nvss_table = nvss_table[~nvss_table[nvss_flux_col].mask]
    nvss_table = nvss_table[np.isfinite(nvss_table[nvss_flux_col])]
    nvss_table = nvss_table[nvss_table[nvss_flux_col] > 0]

    # Identify Targets
    target_mask = nvss_table[nvss_flux_col] >= target_min_flux_mjy
    targets = nvss_table[target_mask].copy() # Make copy to avoid modifying original table
    logger.info(f"Identified {len(targets)} target sources (NVSS flux >= {target_min_flux_mjy} mJy).")

    # Identify Potential References
    reference_mask = (nvss_table[nvss_flux_col] >= ref_min_flux_mjy) & \
                     (nvss_table[nvss_flux_col] <= ref_max_flux_mjy)
    # Exclude sources already identified as targets from the reference pool
    reference_mask &= ~target_mask
    references = nvss_table[reference_mask].copy()
    logger.info(f"Identified {len(references)} potential reference sources (NVSS flux {ref_min_flux_mjy}-{ref_max_flux_mjy} mJy).")

    # Add pixel coordinates
    try:
        with fits.open(mosaic_fits_path) as hdul:
            wcs = WCS(hdul[0].header).celestial
            target_coords = SkyCoord(targets['RAJ2000'], targets['DEJ2000'], unit=(u.hourangle, u.deg), frame='icrs')
            ref_coords = SkyCoord(references['RAJ2000'], references['DEJ2000'], unit=(u.hourangle, u.deg), frame='icrs')

            targets['xpix'], targets['ypix'] = wcs.world_to_pixel(target_coords)
            references['xpix'], references['ypix'] = wcs.world_to_pixel(ref_coords)

            # Check if coordinates are within image bounds (optional but good)
            ny, nx = hdul[0].data.shape[-2:]
            targets = targets[(targets['xpix'] >= 0) & (targets['xpix'] < nx) & (targets['ypix'] >= 0) & (targets['ypix'] < ny)]
            references = references[(references['xpix'] >= 0) & (references['xpix'] < nx) & (references['ypix'] >= 0) & (references['ypix'] < ny)]
            logger.info(f"{len(targets)} targets and {len(references)} references remain within image bounds.")

    except Exception as e:
        logger.error(f"Failed to convert world to pixel coordinates: {e}", exc_info=True)
        return None, None

    if len(targets) == 0:
        logger.warning("No target sources found meeting criteria.")
    if len(references) == 0:
        logger.warning("No reference sources found meeting criteria. Relative photometry may fail.")

    return targets, references


# --- Aperture Photometry ---

def perform_aperture_photometry(config: dict, mosaic_fits_path: str, targets: Table, references: Table):
    """Performs aperture photometry on targets and references."""
    if not photutils_available:
        logger.error("photutils unavailable, cannot perform aperture photometry.")
        return None
    if not os.path.exists(mosaic_fits_path):
        logger.error(f"Mosaic FITS file not found: {mosaic_fits_path}")
        return None

    logger.info(f"Performing aperture photometry on {mosaic_fits_path}")
    phot_config = config.get('photometry', {})

    # Get aperture/annulus dimensions from config
    ap_radius = phot_config.get('aperture_radius_arcsec', 6.0) * u.arcsec
    bg_inner_radius = phot_config.get('background_inner_radius_arcsec', 9.0) * u.arcsec
    bg_outer_radius = phot_config.get('background_outer_radius_arcsec', 15.0) * u.arcsec

    # Combine targets and references for efficient photometry
    if targets is not None and references is not None:
        source_table = vstack([targets, references], join_type='outer', metadata_conflicts='silent')
    elif targets is not None:
        source_table = targets
    elif references is not None:
        source_table = references
    else:
        logger.warning("No sources provided for photometry.")
        return None

    if not ('xpix' in source_table.colnames and 'ypix' in source_table.colnames):
        logger.error("Source table missing pixel coordinate columns ('xpix', 'ypix').")
        return None

    positions = np.vstack((source_table['xpix'], source_table['ypix'])).T

    try:
        with fits.open(mosaic_fits_path) as hdul:
            data = hdul[0].data
            wcs = WCS(hdul[0].header).celestial
            # Handle potential multi-dimensional data (take first plane)
            while data.ndim > 2: data = data[0]
            if data.ndim != 2: raise ValueError("Image data is not 2D.")

            # Convert aperture/annulus sizes to pixels
            pixel_scale = wcs.proj_plane_pixel_scales()[0].to(u.arcsec / u.pixel) # Assumes square pixels
            aperture_pix = (ap_radius / pixel_scale).value
            annulus_inner_pix = (bg_inner_radius / pixel_scale).value
            annulus_outer_pix = (bg_outer_radius / pixel_scale).value

            logger.debug(f"Using aperture radius: {aperture_pix:.2f} pix")
            logger.debug(f"Using background annulus: {annulus_inner_pix:.2f} - {annulus_outer_pix:.2f} pix")

            # Define apertures and annuli
            apertures = CircularAperture(positions, r=aperture_pix)
            annuli = CircularAnnulus(positions, r_in=annulus_inner_pix, r_out=annulus_outer_pix)

            # Perform photometry with local background subtraction
            # Use LocalBackground to estimate background for each source
            # Could also use Background2D for a map, but LocalBackground is simpler here
            bkg_estimator = MedianBackground()
            # Calculate background median in annuli, sigma-clip if needed
            # Note: photutils recommends bkg subtraction *before* aperture_photometry if possible
            # Alternative: Use ApertureStats for background stats per aperture
            try:
                 from photutils.background import ApertureStats
                 aperstats = ApertureStats(data, annuli)
                 bkg_median_per_source = aperstats.median
                 data_bkg_subtracted = data - bkg_median_per_source[:, np.newaxis, np.newaxis] # Needs care if bkg varies spatially
                 # Simpler for now: calculate median once, or use photutils background subtraction
                 # Let's try aperture_photometry's built-in capabilities or do it manually
                 logger.info("Estimating background using annuli...")
                 annulus_masks = annuli.to_mask(method='center') # Use center method for pixel inclusion
                 bkg_median = []
                 for mask in annulus_masks:
                      annulus_data = mask.multiply(data) # Get data within the annulus mask
                      annulus_data_1d = annulus_data[mask.data > 0] # Select valid pixels
                      if len(annulus_data_1d) > 0:
                           # Add sigma clipping here if needed
                           with warnings.catch_warnings():
                                warnings.simplefilter("ignore", RuntimeWarning) # Ignore warnings from empty slices
                                bkg_median.append(np.nanmedian(annulus_data_1d))
                      else:
                           bkg_median.append(np.nan) # Handle cases with no data in annulus
                 bkg_median = np.array(bkg_median)
                 logger.info(f"Calculated {np.sum(np.isfinite(bkg_median))} valid background values.")

            except Exception as e_bkg:
                 logger.error(f"Failed during background estimation: {e_bkg}. Proceeding without subtraction.", exc_info=True)
                 bkg_median = np.zeros(len(positions)) # Set background to zero if estimation fails

            # Perform photometry on original data
            phot_table = aperture_photometry(data, apertures, method='exact') # Use 'exact' for part-pixels

            # Calculate background contribution in aperture and subtract
            phot_table['annulus_median'] = bkg_median
            phot_table['aperture_bkg'] = bkg_median * apertures.area # Background flux in aperture
            phot_table['flux_raw'] = phot_table['aperture_sum'] # Store raw sum
            phot_table['flux'] = phot_table['aperture_sum'] - phot_table['aperture_bkg'] # Background-subtracted flux

            # Estimate errors (basic version: assumes Poisson noise from source + background std dev)
            # A more accurate error requires exposure time, gain, etc., or estimating from background RMS
            # Simple approach: use std dev in annulus as proxy for background noise RMS per pixel
            bkg_stddev = []
            for mask in annulus_masks:
                 annulus_data = mask.multiply(data)
                 annulus_data_1d = annulus_data[mask.data > 0]
                 if len(annulus_data_1d) > 1: # Need >1 point for std dev
                      with warnings.catch_warnings():
                          warnings.simplefilter("ignore", RuntimeWarning)
                          bkg_stddev.append(np.nanstd(annulus_data_1d))
                 else:
                      bkg_stddev.append(np.nan)
            bkg_stddev = np.array(bkg_stddev)
            # Rough error estimate: sqrt(source_flux_in_adu + Npix * bkg_rms^2) - needs conversion factor
            # Simpler for relative: error ~ sqrt(flux_raw * gain + area * stddev^2 * gain) / gain
            # Even simpler: stddev * sqrt(area) - assumes background dominated
            effective_noise_per_pixel = np.nan_to_num(bkg_stddev, nan=np.nanmedian(bkg_stddev[np.isfinite(bkg_stddev)])) # Fill NaNs
            phot_table['flux_err'] = effective_noise_per_pixel * np.sqrt(apertures.area)

            # Add results back to the source table
            source_table['flux'] = phot_table['flux']
            source_table['flux_err'] = phot_table['flux_err']
            source_table['bkg_median'] = phot_table['annulus_median']

            logger.info(f"Photometry complete for {len(phot_table)} sources.")
            # Filter out sources where photometry failed (e.g., NaN flux)
            final_photometry = source_table[np.isfinite(source_table['flux']) & np.isfinite(source_table['flux_err'])]
            logger.info(f"{len(final_photometry)} sources have valid photometry results.")
            return final_photometry

    except Exception as e:
        logger.error(f"Aperture photometry failed: {e}", exc_info=True)
        return None


# --- Relative Flux Calculation ---

def calculate_relative_fluxes(config: dict, photometry_table: Table):
    """Calculates relative fluxes using a local ensemble of reference sources."""
    if photometry_table is None or len(photometry_table) == 0:
        logger.warning("Photometry table is empty, cannot calculate relative fluxes.")
        return None

    logger.info("Calculating relative fluxes...")
    phot_config = config.get('photometry', {})
    max_ref_dist_arcmin = phot_config.get('reference_max_radius_arcmin', 15.0) * u.arcmin
    min_ensemble_size = max(1, phot_config.get('reference_ensemble_size', 10) // 2) # Min refs needed

    # Separate targets and references based on original selection criteria (need a flag/column)
    # Assuming the input table contains both, we need a way to distinguish them.
    # Let's re-select based on flux criteria used in identify_sources
    target_min_flux_mjy = phot_config.get('target_nvss_min_flux_mjy', 5.0)
    ref_min_flux_mjy = phot_config.get('reference_min_catalog_flux_mjy', 100.0)
    ref_max_flux_mjy = phot_config.get('reference_max_catalog_flux_mjy', 5000.0)
    skymodel_config = config.get('skymodel', {})
    nvss_flux_col = skymodel_config.get('primary_catalog', {}).get('flux_column', 'S1.4')

    is_target_mask = photometry_table[nvss_flux_col] >= target_min_flux_mjy
    is_ref_mask = (photometry_table[nvss_flux_col] >= ref_min_flux_mjy) & \
                  (photometry_table[nvss_flux_col] <= ref_max_flux_mjy) & \
                  (~is_target_mask)

    targets = photometry_table[is_target_mask]
    references = photometry_table[is_ref_mask]

    if len(targets) == 0:
        logger.warning("No target sources found in photometry table for relative flux calculation.")
        return None
    if len(references) == 0:
        logger.error("No reference sources found in photometry table. Cannot calculate relative fluxes.")
        return None

    logger.info(f"Calculating relative flux for {len(targets)} targets using {len(references)} references.")

    # Add new columns to targets table
    targets['relative_flux'] = np.nan
    targets['relative_flux_error'] = np.nan
    targets['reference_source_ids'] = ''
    targets['median_reference_flux'] = np.nan

    # Get SkyCoords for distance calculation
    target_coords = SkyCoord(targets['RAJ2000'], targets['DEJ2000'], unit=(u.hourangle, u.deg), frame='icrs')
    ref_coords = SkyCoord(references['RAJ2000'], references['DEJ2000'], unit=(u.hourangle, u.deg), frame='icrs')

    # Find local ensemble for each target
    for i, target in enumerate(targets):
        target_coord = target_coords[i]
        separations = target_coord.separation(ref_coords)
        local_ref_mask = separations <= max_ref_dist_arcmin
        local_references = references[local_ref_mask]

        if len(local_references) < min_ensemble_size:
            logger.warning(f"Target {target['source_id']}: Found only {len(local_references)} local references (min {min_ensemble_size}). Skipping relative flux.")
            continue

        # Calculate median flux of local references (more robust to outliers than mean)
        ref_fluxes = local_references['flux']
        median_ref_flux = np.nanmedian(ref_fluxes)

        if not np.isfinite(median_ref_flux) or median_ref_flux <= 0:
             logger.warning(f"Target {target['source_id']}: Invalid median reference flux ({median_ref_flux}). Skipping relative flux.")
             continue

        # Calculate relative flux and propagate error (simplified: ignores error correlation)
        target_flux = target['flux']
        target_err = target['flux_err']
        # Approx error on median (use MAD for robustness?)
        ref_err_approx = np.nanmedian(np.abs(ref_fluxes - median_ref_flux)) * 1.4826 / np.sqrt(len(local_references)) # Error on median

        relative_flux = target_flux / median_ref_flux
        # Error propagation: (rel_err)^2 = (target_err/target_flux)^2 + (ref_err/median_ref_flux)^2
        with warnings.catch_warnings(): # Ignore division by zero if target_flux is zero
             warnings.simplefilter("ignore", RuntimeWarning)
             relative_flux_error = relative_flux * np.sqrt(
                  (target_err / target_flux)**2 + (ref_err_approx / median_ref_flux)**2
             )

        # Store results
        targets['relative_flux'][i] = relative_flux
        targets['relative_flux_error'][i] = relative_flux_error
        targets['reference_source_ids'][i] = ",".join(local_references['source_id'])
        targets['median_reference_flux'][i] = median_ref_flux
        logger.debug(f"Target {target['source_id']}: RelFlux={relative_flux:.4f} +/- {relative_flux_error:.4f} (Nref={len(local_references)})")

    # Filter targets where relative flux calculation failed
    final_targets = targets[np.isfinite(targets['relative_flux'])]
    logger.info(f"Successfully calculated relative fluxes for {len(final_targets)} targets.")

    return final_targets


# --- Storing Results ---

def store_photometry_results(config: dict, mosaic_time: Time, relative_flux_table: Table):
    """Stores relative flux results in the database."""
    if relative_flux_table is None or len(relative_flux_table) == 0:
        logger.warning("Relative flux table is empty, nothing to store.")
        return False

    logger.info(f"Storing {len(relative_flux_table)} photometry results for time {mosaic_time.isot}")

    conn = _connect_db(config)
    if conn is None: return False
    if not _init_db(conn, config): # Ensure table exists
        conn.close()
        return False

    # Prepare data for insertion
    mjd = mosaic_time.mjd
    mosaic_time_iso = mosaic_time.isot

    rows_to_insert = []
    for row in relative_flux_table:
        rows_to_insert.append((
            str(row['source_id']),
            mjd,
            mosaic_time_iso,
            float(row['relative_flux']) if np.isfinite(row['relative_flux']) else None,
            float(row['relative_flux_error']) if np.isfinite(row['relative_flux_error']) else None,
            float(row['flux']) if np.isfinite(row['flux']) else None, # Instrumental flux
            float(row['flux_err']) if np.isfinite(row['flux_err']) else None,
            float(row['bkg_median']) if np.isfinite(row['bkg_median']) else None, # Background
            int(row.get('photometry_flags', 0)), # Flags (add column if needed)
            str(row.get('reference_source_ids', '')),
            float(row.get('median_reference_flux', np.nan)) if np.isfinite(row.get('median_reference_flux', np.nan)) else None
        ))

    try:
        cursor = conn.cursor()
        # Use INSERT OR REPLACE (or INSERT OR IGNORE) to handle potential duplicate entries if reprocessing
        # Assumes PRIMARY KEY is (source_id, mjd)
        cursor.executemany("""
            INSERT OR REPLACE INTO photometry_measurements
            (source_id, mjd, mosaic_time_utc, relative_flux, relative_flux_error,
             instrumental_flux, instrumental_flux_error, background, photometry_flags,
             reference_source_ids, median_reference_flux)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)
        conn.commit()
        logger.info(f"Successfully stored/updated {len(rows_to_insert)} rows in the database.")
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to store photometry results in database: {e}", exc_info=True)
        conn.rollback() # Rollback changes on error
        conn.close()
        return False
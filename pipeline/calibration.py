# pipeline/calibration.py

import os
import numpy as np
from shutil import rmtree
import glob

# CASA imports
try:
    from casatools import msmetadata, table
    from casatasks import (
        clearcal, delmod, rmtables, flagdata, bandpass, ft, mstransform, gaincal, applycal, listobs, split
    )
    casa_available = True
except ImportError:
    print("Warning: CASA tasks/tools not found. Calibration module functionality will be limited.")
    casa_available = False

# Pipeline imports
from .pipeline_utils import get_logger
from . import skymodel # For creating calibrator models

logger = get_logger(__name__)

# --- Flagging Functions (Adapted from calib_utils.py) ---

def flag_rfi(config: dict, ms_path: str):
    """Applies RFI flagging using tfcrop."""
    if not casa_available:
        logger.error("CASA not available, skipping RFI flagging.")
        return False
    if not os.path.exists(ms_path):
        logger.error(f"MS not found for RFI flagging: {ms_path}")
        return False

    logger.info(f"Applying TFCrop RFI flagging to {ms_path}")
    flag_params = config.get('calibration', {}).get('flagging', {})
    # Get field selection if needed - assuming avg MS has fewer fields?
    # For now, flag all fields unless specified otherwise.
    # fields_str = _get_field_str(config, ms_path) # Helper needed if field selection is desired

    try:
        flagdata(
            vis=ms_path,
            mode='tfcrop',
            datacolumn='data', # Flag raw data
            field='', # Flag all fields for now
            action='apply',
            timecutoff=flag_params.get('tfcrop_timecutoff', 4.0),
            freqcutoff=flag_params.get('tfcrop_freqcutoff', 4.0),
            # Add other relevant tfcrop parameters from config if needed
            # maxnpieces=7, ntime='scan', combinescans=True, etc.
            flagbackup=False # Don't create backups by default
        )
        logger.info(f"TFCrop RFI flagging completed for {ms_path}")
        return True
    except Exception as e:
        logger.error(f"TFCrop RFI flagging failed for {ms_path}: {e}", exc_info=True)
        return False

def flag_general(config: dict, ms_path: str):
    """Applies general flags (autocorr, shadow, clip zeros)."""
    if not casa_available:
        logger.error("CASA not available, skipping general flagging.")
        return False
    if not os.path.exists(ms_path):
        logger.error(f"MS not found for general flagging: {ms_path}")
        return False

    logger.info(f"Applying general flags (autocorr, shadow, clip) to {ms_path}")
    # flag_params = config.get('calibration', {}).get('flagging', {}) # Get params if configurable

    try:
        # Flag autocorrelations
        flagdata(vis=ms_path, mode='manual', autocorr=True, flagbackup=False, action='apply')
        logger.debug(f"Autocorrelations flagged for {ms_path}")

        # Flag shadowed data
        # tolerance might need adjustment based on DSA-110 antenna diameter/layout
        flagdata(vis=ms_path, mode='shadow', tolerance=0.0, flagbackup=False, action='apply')
        logger.debug(f"Shadowed data flagged for {ms_path}")

        # Clip exact zero visibilities
        flagdata(vis=ms_path, mode='clip', clipzeros=True, flagbackup=False, action='apply')
        logger.debug(f"Zero visibilities flagged for {ms_path}")

        logger.info(f"General flagging completed for {ms_path}")
        return True
    except Exception as e:
        logger.error(f"General flagging failed for {ms_path}: {e}", exc_info=True)
        return False

def reset_ms_state(ms_path: str):
    """Resets calibration application, model data, and optionally flags."""
    if not casa_available:
        logger.error("CASA not available, cannot reset MS state.")
        return False
    if not os.path.exists(ms_path):
        logger.error(f"MS not found for state reset: {ms_path}")
        return False

    logger.info(f"Resetting calibration state (clearcal, delmod) for {ms_path}")
    try:
        # Clear previous calibration application
        clearcal(vis=ms_path, addmodel=True) # addmodel=True clears model columns too

        # Delete model visibilities (alternative/redundant if addmodel=True used)
        # delmod(vis=ms_path) # Often needed if MODEL_DATA column exists but is wrong

        # Remove old flag versions if desired (can bloat MS)
        # flagmanager(vis=ms_path, mode='delete', versionname='...')

        # Optional: Unflag all data (use with caution!)
        # logger.warning(f"Unflagging all data in {ms_path}")
        # flagdata(vis=ms_path, mode='unflag', flagbackup=False)
        # if os.path.exists(f"{ms_path}.flagversions"):
        #     logger.info(f"Removing flagversions for {ms_path}")
        #     rmtree(f"{ms_path}.flagversions")

        logger.info(f"MS state reset for {ms_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to reset MS state for {ms_path}: {e}", exc_info=True)
        return False


# --- Calibration Derivation Functions ---

def perform_bandpass_calibration(config: dict, bcal_ms_path: str, bcal_info: dict):
    """Performs bandpass calibration on a specific MS containing a BPCAL source."""
    if not casa_available:
        logger.error("CASA not available, skipping bandpass calibration.")
        return None
    if not os.path.exists(bcal_ms_path):
        logger.error(f"Bandpass calibrator MS not found: {bcal_ms_path}")
        return None

    logger.info(f"Starting bandpass calibration using {bcal_ms_path} for calibrator {bcal_info.get('name', 'UNKNOWN')}")

    paths_config = config['paths']
    cal_config = config['calibration']
    cal_tables_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['cal_tables_dir'])
    os.makedirs(cal_tables_dir, exist_ok=True)

    # Generate output table name
    timestamp = os.path.basename(bcal_ms_path).split('_')[1] # Assumes drift_TIMESTAMP.ms format
    bcal_table_name = f"bandpass_{timestamp}_{bcal_info.get('name', 'cal')}.bcal"
    bcal_table_path = os.path.join(cal_tables_dir, bcal_table_name)

    if os.path.exists(bcal_table_path):
        logger.warning(f"Bandpass table {bcal_table_path} already exists. Removing.")
        try:
            rmtree(bcal_table_path)
        except Exception as e:
            logger.error(f"Failed to remove existing BPCAL table: {e}")
            return None

    # --- Prepare BPCAL MS ---
    # Optional: Reset state? Assumes input MS is relatively clean or specific for BPCAL
    # reset_ms_state(bcal_ms_path)

    # Flagging (RFI might be crucial for BPCAL)
    if not flag_rfi(config, bcal_ms_path): return None
    if not flag_general(config, bcal_ms_path): return None

    # --- Create BPCAL Sky Model ---
    # Assume BPCAL info dict contains 'name', 'ra', 'dec', 'flux_jy', etc. needed by skymodel
    logger.info(f"Creating sky model for BPCAL: {bcal_info.get('name')}")
    # Need to adapt skymodel module to take source info directly
    cl_path, _ = skymodel.create_calibrator_component_list(config, bcal_info)
    if cl_path is None:
        logger.error("Failed to create BPCAL component list.")
        return None

    # --- Center MS on BPCAL ---
    # Need BPCAL coordinates in CASA format
    bcal_coord_str = f"J2000 {bcal_info['ra']} {bcal_info['dec']}" # Assumes RA/Dec are strings
    centered_ms_path = f"{bcal_ms_path}_centered"
    if os.path.exists(centered_ms_path): rmtree(centered_ms_path)
    try:
        logger.info(f"Centering MS {bcal_ms_path} on BPCAL at {bcal_coord_str}")
        mstransform(
            vis=bcal_ms_path,
            outputvis=centered_ms_path,
            datacolumn='data', # Transform raw data
            phasecenter=bcal_coord_str,
            mode='phasecenter'
        )
    except Exception as e:
        logger.error(f"Failed to center MS on BPCAL: {e}", exc_info=True)
        if os.path.exists(centered_ms_path): rmtree(centered_ms_path) # Clean up
        return None

    # --- Fourier Transform Model ---
    try:
        logger.info(f"Applying BPCAL model {cl_path} to {centered_ms_path}")
        ft(vis=centered_ms_path, complist=cl_path, usescratch=True)
    except Exception as e:
        logger.error(f"Failed to FT BPCAL model: {e}", exc_info=True)
        rmtree(centered_ms_path) # Clean up
        return None

    # --- Solve for Bandpass ---
    try:
        logger.info(f"Solving for bandpass solutions, saving to {bcal_table_path}")
        bandpass(
            vis=centered_ms_path,
            caltable=bcal_table_path,
            refant=cal_config.get('bcal_refant', ''),
            solint='inf', # Solve one solution for the whole observation
            combine='scan', # Combine scans if multiple exist in the MS
            bandtype='B', # Standard B polynomial solution
            uvrange=cal_config.get('bcal_uvrange', ''),
            # Add other bandpass parameters as needed (e.g., minsnr, solnorm)
            append=False # Create new table
        )
        logger.info(f"Bandpass calibration successful. Table: {bcal_table_path}")
        rmtree(centered_ms_path) # Clean up centered MS
        return bcal_table_path
    except Exception as e:
        logger.error(f"Bandpass task failed: {e}", exc_info=True)
        rmtree(centered_ms_path) # Clean up centered MS
        if os.path.exists(bcal_table_path): rmtree(bcal_table_path) # Clean up table
        return None


def perform_gain_calibration(config: dict, ms_paths: list, cl_path: str, time_segment_str: str):
    """Performs gain calibration (A&P) for a time segment using a sky model."""
    if not casa_available:
        logger.error("CASA not available, skipping gain calibration.")
        return None
    if not all(os.path.exists(p) for p in ms_paths):
        logger.error(f"One or more MS files not found for gain cal segment {time_segment_str}.")
        return None
    if not os.path.exists(cl_path):
        logger.error(f"Component list not found for gain cal: {cl_path}")
        return None

    logger.info(f"Starting gain calibration for time segment {time_segment_str} using {len(ms_paths)} MS files.")

    paths_config = config['paths']
    cal_config = config['calibration']
    cal_tables_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['cal_tables_dir'])
    os.makedirs(cal_tables_dir, exist_ok=True)

    # Generate output table name
    gcal_table_name = f"gain_{time_segment_str}.gcal"
    gcal_table_path = os.path.join(cal_tables_dir, gcal_table_name)

    if os.path.exists(gcal_table_path):
        logger.warning(f"Gain table {gcal_table_path} already exists. Removing.")
        try:
            rmtree(gcal_table_path)
        except Exception as e:
            logger.error(f"Failed to remove existing GCAL table: {e}")
            return None

    # --- Prepare MS (Combine/FT Model) ---
    # If gaincal handles lists directly, no concat needed. Assume it does for now.
    # If not, use virtualconcat or concat beforehand.
    vis_input = ms_paths # Pass list directly to gaincal
    logger.debug(f"Using MS list for gaincal: {vis_input}")

    # FT model into *each* MS file (or into a concatenated MS)
    # This requires iteration or a pre-concatenated MS. Let's assume iteration.
    try:
        logger.info(f"Applying sky model {cl_path} to MS files for gaincal...")
        for ms_path in ms_paths:
             # Important: FT into DATA column, gaincal reads MODEL unless specified
             # We need the model in the MODEL_DATA column
             # First clear any existing model, then FT
             logger.debug(f"Clearing model for {ms_path}")
             clearcal(vis=ms_path, addmodel=True) # Clears CORRECTED too, ensure this is intended timing
             logger.debug(f"FTing model {cl_path} into {ms_path}")
             ft(vis=ms_path, complist=cl_path, usescratch=True) # Puts model in MODEL_DATA
    except Exception as e:
        logger.error(f"Failed to FT sky model for gain calibration: {e}", exc_info=True)
        return None

    # --- Solve for Gains (A&P) ---
    try:
        logger.info(f"Solving for gains (A&P), saving to {gcal_table_path}")
        gaincal(
            vis=vis_input, # List of MS files
            caltable=gcal_table_path,
            gaintype='G', # Amp+Phase complex gains
            refant=cal_config.get('gcal_refant', ''),
            calmode=cal_config.get('gcal_mode', 'ap'), # 'ap' for amp & phase
            solint=cal_config.get('gcal_solint', '30min'),
            minsnr=cal_config.get('gcal_minsnr', 3.0),
            uvrange=cal_config.get('gcal_uvrange', ''),
            combine='scan', # Combine data across scans within solint
            append=False,
            # Use MODEL column populated by ft
            gaintable=[] # No prior calibration tables applied during solving
        )
        logger.info(f"Gain calibration successful. Table: {gcal_table_path}")
        return gcal_table_path
    except Exception as e:
        logger.error(f"Gaincal task failed: {e}", exc_info=True)
        if os.path.exists(gcal_table_path): rmtree(gcal_table_path) # Clean up table
        return None


# --- Calibration Application Function ---

def apply_calibration(config: dict, ms_path: str, bcal_table: str, gcal_tables: list):
    """Applies bandpass and gain calibration tables to an MS file."""
    if not casa_available:
        logger.error("CASA not available, skipping calibration application.")
        return False
    if not os.path.exists(ms_path):
        logger.error(f"MS not found for applying calibration: {ms_path}")
        return False

    logger.info(f"Applying calibration to {ms_path}")
    logger.debug(f"  BPCAL table: {bcal_table}")
    logger.debug(f"  GCAL tables: {gcal_tables}")

    # Check if calibration tables exist
    if not os.path.exists(bcal_table):
        logger.error(f"Bandpass table not found: {bcal_table}")
        return False
    if not all(os.path.exists(g) for g in gcal_tables):
        logger.error(f"One or more gain tables not found: {gcal_tables}")
        return False

    # Build list of tables for applycal
    gaintables_to_apply = [bcal_table] + gcal_tables # Order matters: B then G typically

    try:
        # Apply calibration solutions to CORRECTED_DATA column
        applycal(
            vis=ms_path,
            gaintable=gaintables_to_apply,
            gainfield=[], # Apply to all fields in MS
            interp=['nearest,linear'], # Interpolation modes for B, G (adjust if needed)
            calwt=False, # Do not modify weights based on calibration solutions
            flagbackup=False, # Don't backup flags before applying
            applymode='calonly' # Apply to CORRECTED_DATA only
        )
        logger.info(f"Successfully applied calibration tables to {ms_path}")
        return True
    except Exception as e:
        logger.error(f"Applycal task failed for {ms_path}: {e}", exc_info=True)
        return False


# --- Helper function (Example - may need refinement or move to utils) ---
# def _get_field_str(config: dict, ms_path: str) -> str:
#     """Gets a string for field selection based on config."""
#     # Placeholder: Add logic if specific field selection is needed for tasks
#     # E.g., read field IDs from config or determine dynamically
#     return '' # Default: empty string selects all fields


# --- Example of splitting off corrected data (if needed before imaging) ---
def split_corrected_column(ms_path: str, output_ms_path: str):
    """Splits the CORRECTED_DATA column to a new MS."""
    if not casa_available:
        logger.error("CASA not available, cannot split corrected column.")
        return None
    if not os.path.exists(ms_path):
        logger.error(f"Input MS not found for splitting: {ms_path}")
        return None

    if os.path.exists(output_ms_path):
        logger.warning(f"Output split MS {output_ms_path} already exists. Removing.")
        try:
            rmtree(output_ms_path)
            if os.path.exists(f"{output_ms_path}.flagversions"): rmtree(f"{output_ms_path}.flagversions")
        except Exception as e:
            logger.error(f"Failed to remove existing split MS: {e}")
            return None

    logger.info(f"Splitting CORRECTED data from {ms_path} to {output_ms_path}")
    try:
        split(
            vis=ms_path,
            outputvis=output_ms_path,
            datacolumn='corrected', # Split the corrected data
            field='', # Split all fields
            spw='' # Split all spectral windows
        )
        logger.info(f"Successfully created split MS: {output_ms_path}")
        return output_ms_path
    except Exception as e:
        logger.error(f"Split task failed: {e}", exc_info=True)
        if os.path.exists(output_ms_path): rmtree(output_ms_path) # Clean up
        return None
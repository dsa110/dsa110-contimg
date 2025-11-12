# pipeline/config_parser.py

import yaml # Requires pip install PyYAML
import os
import logging # Use standard logging

# Initialize logger for this module - will be configured by main script
logger = logging.getLogger(__name__)

def resolve_paths(config):
    """Resolves relative paths in the config based on pipeline_base_dir."""
    if 'paths' not in config:
        logger.warning("Config missing 'paths' section. Cannot resolve paths.")
        return config

    base_dir = config['paths'].get('pipeline_base_dir')
    if not base_dir:
        logger.error("Config missing 'paths:pipeline_base_dir'. Path resolution requires this key.")
        # Return config as is, calling function should check base_dir existence
        return config

    # Resolve base_dir itself if it's relative (relative to CWD where script is run)
    if not os.path.isabs(base_dir):
        logger.warning(f"pipeline_base_dir '{base_dir}' is not absolute. Resolving relative to current working directory.")
        base_dir = os.path.abspath(base_dir)
        config['paths']['pipeline_base_dir'] = base_dir
        logger.info(f"Resolved pipeline_base_dir to: {base_dir}")

    # Paths relative to pipeline_base_dir
    # Ensure keys exist before trying to resolve
    paths_to_resolve_relative_to_base = [
        'ms_stage1_dir', 'cal_tables_dir', 'skymodels_dir',
        'images_dir', 'mosaics_dir', 'photometry_dir'
    ]
    for key in paths_to_resolve_relative_to_base:
        if key in config['paths'] and config['paths'][key]:
            path_val = config['paths'][key]
            if not os.path.isabs(path_val):
                resolved_path = os.path.join(base_dir, path_val)
                config['paths'][key] = resolved_path
                logging.debug(f"Resolved relative path '{key}': {resolved_path}")

    # Paths relative to the parent of the pipeline module directory (logs, diagnostics)
    paths_relative_to_script_parent = ['log_dir', 'diagnostics_base_dir']
    try:
        # Assumes this parser script is inside the 'pipeline' directory
        pipeline_script_dir = os.path.dirname(__file__)
        pipeline_root_dir = os.path.dirname(pipeline_script_dir)
        if not pipeline_root_dir: pipeline_root_dir = '.' # Fallback to CWD if structure unexpected

        for key in paths_relative_to_script_parent:
             if key in config['paths'] and config['paths'][key]:
                 path_val = config['paths'][key]
                 if not os.path.isabs(path_val):
                     resolved_path = os.path.abspath(os.path.join(pipeline_root_dir, path_val))
                     config['paths'][key] = resolved_path
                     logging.debug(f"Resolved relative path '{key}': {resolved_path}")
    except Exception as e:
         logger.warning(f"Could not determine script parent directory for resolving log/diagnostic paths: {e}")


    # Paths that should likely be absolute (input data, maybe processed data)
    absolute_paths_expected = ['hdf5_incoming', 'hdf5_processed']
    for key in absolute_paths_expected:
         if key in config['paths'] and config['paths'][key]:
             path_val = config['paths'][key]
             if not os.path.isabs(path_val):
                 logger.warning(f"Path '{key}': '{path_val}' is relative. This path should ideally be absolute.")
                 # Optionally resolve relative to CWD or raise error
                 # config['paths'][key] = os.path.abspath(path_val)

    # Resolve BPCAL candidate catalog path (might be relative to cal_tables_dir or absolute)
    try:
         cal_path = config.get('calibration',{}).get('bcal_candidate_catalog', None)
         cal_tables_dir_path = config.get('paths',{}).get('cal_tables_dir', None)
         if cal_path and cal_tables_dir_path and not os.path.isabs(cal_path):
             # If cal_tables_dir itself was resolved to be absolute
             if os.path.isabs(cal_tables_dir_path):
                  resolved_path = os.path.join(cal_tables_dir_path, cal_path)
                  config['calibration']['bcal_candidate_catalog'] = resolved_path
                  logging.debug(f"Resolved relative path 'bcal_candidate_catalog': {resolved_path}")
             else:
                  logger.warning("Cannot resolve relative 'bcal_candidate_catalog' path as 'cal_tables_dir' is not absolute.")
    except Exception as e:
         logger.warning(f"Could not resolve bcal_candidate_catalog path: {e}")


    return config


def validate_config(config):
    """Performs basic validation checks on the loaded configuration."""
    if config is None:
        logger.error("Configuration object is None.")
        return False

    valid = True
    required_top_keys = ['paths', 'services', 'ms_creation', 'calibration', 'skymodel', 'imaging', 'mosaicking', 'photometry', 'variability_analysis']
    for key in required_top_keys:
        if key not in config:
            logger.error(f"Config validation failed: Missing required top-level key '{key}'.")
            valid = False

    if not valid: return False # Stop if top keys missing

    # --- Paths Validation ---
    required_path_keys = ['pipeline_base_dir', 'ms_stage1_dir', 'cal_tables_dir', 'skymodels_dir', 'images_dir', 'mosaics_dir', 'photometry_dir', 'log_dir', 'diagnostics_base_dir', 'hdf5_incoming']
    if 'paths' not in config: valid = False # Should have been caught already
    else:
         for key in required_path_keys:
             if key not in config['paths'] or not config['paths'][key]:
                  logger.error(f"Config validation failed: Missing required path key 'paths:{key}'.")
                  valid = False

    # --- Calibration Validation ---
    if 'calibration' not in config: valid = False
    else:
         if 'fixed_declination_deg' not in config['calibration']:
              logger.error("Config validation failed: Missing required key 'calibration:fixed_declination_deg'.")
              valid = False
         if 'bcal_candidate_catalog' not in config['calibration'] or not config['calibration']['bcal_candidate_catalog']:
              logger.error("Config validation failed: Missing required key 'calibration:bcal_candidate_catalog'.")
              valid = False

    # --- Services Validation (Example) ---
    if 'services' in config:
        if 'mosaic_duration_min' not in config['services'] or 'mosaic_overlap_min' not in config['services'] or 'ms_chunk_duration_min' not in config['services']:
             logger.warning("Config validation warning: Missing one or more mosaic timing keys in 'services'. Defaults may apply.")
        else:
             duration = config['services']['mosaic_duration_min']
             overlap = config['services']['mosaic_overlap_min']
             ms_chunk = config['services']['ms_chunk_duration_min']
             if not isinstance(duration, (int, float)) or not isinstance(overlap, (int, float)) or not isinstance(ms_chunk, (int, float)):
                  logger.error("Config validation error: Mosaic timing values must be numeric.")
                  valid = False
             elif duration <= overlap:
                  logger.error("Config validation failed: 'mosaic_duration_min' must be greater than 'mosaic_overlap_min'.")
                  valid = False
             elif duration % ms_chunk != 0 or overlap % ms_chunk != 0:
                  logger.warning("Config validation warning: Mosaic duration/overlap not integer multiple of MS chunk duration.")

    # Add more checks for other sections as needed...

    if not valid:
        logger.critical("Configuration validation failed. Please check config file structure and values.")
    return valid


def load_config(config_path):
    """Loads, validates, and resolves paths in the YAML configuration file."""
    logger.info(f"Loading configuration from: {config_path}")
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        return None

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if config is None:
             logger.error(f"Config file {config_path} is empty or invalid YAML.")
             return None

        # Resolve Paths *before* full validation that might check resolved paths
        config = resolve_paths(config)

        # Basic Validation
        if not validate_config(config):
            return None

        logger.info("Configuration loaded and validated successfully.")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML config file {config_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred loading config {config_path}: {e}", exc_info=True)
        return None
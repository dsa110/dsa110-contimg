# pipeline/config_parser.py

import yaml
import os
from .pipeline_utils import get_logger

logger = get_logger(__name__)

def resolve_paths(config):
    """Resolves relative paths in the config based on pipeline_base_dir."""
    if 'paths' not in config:
        logger.warning("Config missing 'paths' section. Cannot resolve paths.")
        return config

    base_dir = config['paths'].get('pipeline_base_dir')
    if not base_dir:
        logger.warning("Config missing 'paths:pipeline_base_dir'. Cannot resolve relative paths.")
        return config
    if not os.path.isabs(base_dir):
        # Assume base_dir itself might be relative to the config file location? Risky.
        # Best practice: Require pipeline_base_dir to be absolute or handle explicitly.
        logger.warning(f"pipeline_base_dir '{base_dir}' is not absolute. Assuming relative to CWD or config file.")
        # For now, let's assume it's relative to CWD if not absolute
        base_dir = os.path.abspath(base_dir)
        config['paths']['pipeline_base_dir'] = base_dir


    paths_to_resolve = [
        'ms_stage1_dir', 'cal_tables_dir', 'skymodels_dir',
        'images_dir', 'mosaics_dir', 'photometry_dir',
        'hdf5_incoming', 'hdf5_processed', 'log_dir', 'diagnostics_base_dir'
        # Add other paths that might be relative here
    ]

    for key in paths_to_resolve:
        if key in config['paths']:
            path_val = config['paths'][key]
            if path_val and not os.path.isabs(path_val):
                # If key is log_dir or diagnostics_base_dir, resolve relative to pipeline dir parent
                if key in ['log_dir', 'diagnostics_base_dir']:
                     # Assumes pipeline dir is one level down from root where logs are
                     pipeline_script_dir = os.path.dirname(__file__)
                     resolved_path = os.path.abspath(os.path.join(pipeline_script_dir, path_val))
                # If key is hdf5 related, keep as is or resolve relative to CWD? Assume absolute for now.
                elif key in ['hdf5_incoming', 'hdf5_processed']:
                     # Let's assume these should be absolute paths specified by user
                     logger.debug(f"Path '{key}': '{path_val}' is relative. Assuming it's correctly specified by user.")
                     resolved_path = path_val # Don't change relative path unless basedir logic applies
                # Otherwise, resolve relative to pipeline_base_dir
                else:
                     resolved_path = os.path.join(base_dir, path_val)

                config['paths'][key] = resolved_path
                logger.debug(f"Resolved path '{key}': {resolved_path}")

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

    # Add more specific validation checks as needed
    # e.g., check path existence, numerical ranges, specific values

    if 'paths' in config:
         if 'pipeline_base_dir' not in config['paths'] or not config['paths']['pipeline_base_dir']:
              logger.error("Config validation failed: 'paths:pipeline_base_dir' is required.")
              valid = False

    # Example: Check mosaic duration/overlap logic
    if 'services' in config:
        duration = config['services'].get('mosaic_duration_min', 60)
        overlap = config['services'].get('mosaic_overlap_min', 10)
        ms_chunk = config['services'].get('ms_chunk_duration_min', 5)
        if duration <= overlap:
            logger.error("Config validation failed: 'mosaic_duration_min' must be greater than 'mosaic_overlap_min'.")
            valid = False
        if duration % ms_chunk != 0 or overlap % ms_chunk != 0:
             logger.warning("Config validation warning: Mosaic duration/overlap not integer multiple of MS chunk duration.")
             # May not be critical error, but good to warn


    if not valid:
        logger.error("Configuration validation failed. Please check config file.")

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

        # Basic Validation
        if not validate_config(config):
            return None

        # Resolve Paths
        config = resolve_paths(config)

        logger.info("Configuration loaded and validated successfully.")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML config file {config_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred loading config {config_path}: {e}", exc_info=True)
        return None
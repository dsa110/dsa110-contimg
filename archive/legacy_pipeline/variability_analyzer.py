# pipeline/variability_analyzer.py

import os
import numpy as np
import pandas as pd
import sqlite3
import warnings
from datetime import datetime, timedelta

# Astropy imports
from astropy.time import Time
from astropy.stats import median_absolute_deviation

# Scipy imports (optional, for more advanced stats)
# from scipy import stats

# Pipeline imports
from .pipeline_utils import get_logger
from .photometry import _connect_db # Reuse DB connection logic

logger = get_logger(__name__)

# --- Helper Functions ---

def fetch_light_curve(config: dict, conn, source_id: str):
    """Fetches the light curve for a source from the database."""
    if conn is None:
        logger.error("Database connection is None, cannot fetch light curve.")
        return None

    phot_config = config.get('photometry', {})
    var_config = config.get('variability_analysis', {})
    lookback_days = var_config.get('lookback_days', 90)
    min_data_points = var_config.get('min_data_points_for_analysis', 10) # Min points needed

    logger.debug(f"Fetching light curve for {source_id} over last {lookback_days} days.")

    try:
        # Calculate time threshold
        time_threshold = Time.now() - timedelta(days=lookback_days)
        mjd_threshold = time_threshold.mjd

        query = """
            SELECT mjd, relative_flux, relative_flux_error
            FROM photometry_measurements
            WHERE source_id = ? AND mjd >= ? AND relative_flux IS NOT NULL AND relative_flux_error IS NOT NULL AND relative_flux_error > 0
            ORDER BY mjd ASC
        """
        # Use pandas read_sql for convenience
        lc_df = pd.read_sql_query(query, conn, params=(source_id, mjd_threshold))

        if len(lc_df) < min_data_points:
            logger.debug(f"Source {source_id}: Found only {len(lc_df)} data points (min {min_data_points}). Skipping analysis.")
            return None

        logger.debug(f"Source {source_id}: Retrieved {len(lc_df)} data points.")
        # Convert MJD back to Time objects if needed for plotting/analysis
        lc_df['time'] = Time(lc_df['mjd'].values, format='mjd')

        return lc_df # Return pandas DataFrame

    except Exception as e:
        logger.error(f"Failed to fetch light curve for {source_id}: {e}", exc_info=True)
        return None

def calculate_baseline_stats(light_curve_df: pd.DataFrame):
    """Calculates robust baseline statistics (median, MAD)."""
    if light_curve_df is None or len(light_curve_df) < 3: # Need a few points for robust stats
        return {'median': np.nan, 'mad': np.nan, 'n_points': 0}

    flux_values = light_curve_df['relative_flux'].values
    with warnings.catch_warnings(): # Ignore warnings if MAD is zero
        warnings.simplefilter("ignore", RuntimeWarning)
        median = np.nanmedian(flux_values)
        # Calculate MAD (Median Absolute Deviation), scale to estimate std dev for Normal dist
        mad = median_absolute_deviation(flux_values, nan_policy='omit')
        mad_std = mad * 1.4826 # MAD scaled to be equivalent to std dev for Gaussian

    logger.debug(f"Baseline stats: Median={median:.4f}, MAD={mad:.4f}, MAD_std={mad_std:.4f}, N={len(flux_values)}")
    return {'median': median, 'mad': mad, 'mad_std': mad_std, 'n_points': len(flux_values)}


def detect_significant_deviations(light_curve_df: pd.DataFrame, baseline_stats: dict, config: dict):
    """Identifies points significantly deviating from the baseline median."""
    if light_curve_df is None or not baseline_stats or np.isnan(baseline_stats['median']) or np.isnan(baseline_stats['mad_std']) or baseline_stats['mad_std'] == 0:
        logger.debug("Cannot detect deviations due to missing data or zero MAD.")
        light_curve_df['deviation_sigma'] = np.nan
        light_curve_df['is_deviant'] = False
        return light_curve_df # Return df with columns added but no deviants

    var_config = config.get('variability_analysis', {})
    threshold_mad = var_config.get('significance_threshold_mad', 5.0)

    median = baseline_stats['median']
    mad_std = baseline_stats['mad_std']

    # Calculate deviation in units of MAD_std (like sigma)
    light_curve_df['deviation_sigma'] = (light_curve_df['relative_flux'] - median) / mad_std
    # Flag points exceeding threshold
    light_curve_df['is_deviant'] = np.abs(light_curve_df['deviation_sigma']) >= threshold_mad

    n_deviant = light_curve_df['is_deviant'].sum()
    logger.debug(f"Found {n_deviant} points deviating by >= {threshold_mad} * MAD_std.")

    return light_curve_df

def find_candidate_events(light_curve_df: pd.DataFrame, baseline_stats: dict, config: dict):
    """Identifies potential variability events based on consecutive deviations."""
    # This is a simplified version focusing on consecutive deviations.
    # Real ESE detection might require shape fitting or more complex criteria.

    if light_curve_df is None or 'is_deviant' not in light_curve_df.columns or not baseline_stats:
        return [] # Return empty list of candidates

    var_config = config.get('variability_analysis', {})
    min_consecutive = var_config.get('min_consecutive_points', 2)
    # Could add timescale constraints here if needed

    candidates = []
    in_event = False
    event_start_idx = -1
    current_sign = 0 # Track sign of deviation (+1 or -1)

    deviant_points = light_curve_df[light_curve_df['is_deviant']]
    if len(deviant_points) < min_consecutive:
        logger.debug("Not enough deviant points to form candidate events.")
        return []

    logger.debug(f"Searching for >= {min_consecutive} consecutive deviations...")

    # Iterate through all points, checking for consecutive deviant points
    for idx in range(len(light_curve_df)):
        is_dev = light_curve_df.iloc[idx]['is_deviant']
        dev_sign = np.sign(light_curve_df.iloc[idx]['deviation_sigma']) if is_dev else 0

        if is_dev:
            if not in_event:
                # Start of a potential event
                in_event = True
                event_start_idx = idx
                current_sign = dev_sign
            elif dev_sign != current_sign:
                 # Sign of deviation flipped, end previous event if long enough
                if idx - event_start_idx >= min_consecutive:
                     candidates.append({'start_idx': event_start_idx, 'end_idx': idx - 1, 'sign': current_sign})
                     logger.info(f"  -> Found potential event (sign={current_sign}) ending at index {idx-1}")
                 # Start new event with the current sign
                event_start_idx = idx
                current_sign = dev_sign
            # else: still in event with same sign, continue
        else: # Not deviant
            if in_event:
                # End of a potential event
                if idx - event_start_idx >= min_consecutive:
                    candidates.append({'start_idx': event_start_idx, 'end_idx': idx - 1, 'sign': current_sign})
                    logger.info(f"  -> Found potential event (sign={current_sign}) ending at index {idx-1}")
                in_event = False
                event_start_idx = -1
                current_sign = 0

    # Check if loop ended while in an event
    if in_event and (len(light_curve_df) - event_start_idx) >= min_consecutive:
        candidates.append({'start_idx': event_start_idx, 'end_idx': len(light_curve_df) - 1, 'sign': current_sign})
        logger.info(f"  -> Found potential event (sign={current_sign}) ending at last data point")

    logger.debug(f"Found {len(candidates)} candidate events based on consecutive deviations.")
    # Add more details to candidate dictionary
    detailed_candidates = []
    for cand in candidates:
         start_mjd = light_curve_df.iloc[cand['start_idx']]['mjd']
         end_mjd = light_curve_df.iloc[cand['end_idx']]['mjd']
         duration = end_mjd - start_mjd
         event_points = light_curve_df.iloc[cand['start_idx']:cand['end_idx']+1]
         peak_deviation = event_points.loc[event_points['deviation_sigma'].abs().idxmax()]['deviation_sigma']
         detailed_candidates.append({
              'start_mjd': start_mjd,
              'end_mjd': end_mjd,
              'duration_days': duration,
              'sign': cand['sign'],
              'n_points': len(event_points),
              'peak_deviation_sigma': peak_deviation
         })

    return detailed_candidates


# --- Main Analysis Function ---

def analyze_variability(config: dict):
    """Main function to analyze variability for all sources in the database."""
    logger.info("Starting variability analysis run.")
    var_config = config.get('variability_analysis', {})
    paths_config = config['paths']
    phot_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['photometry_dir'])
    candidate_list_path = os.path.join(phot_dir, var_config.get('candidate_list_path', 'variable_candidates.csv'))

    conn = _connect_db(config)
    if conn is None:
        logger.error("Cannot connect to database for variability analysis.")
        return

    all_candidates = [] # List to store dicts of candidate events

    try:
        # Get list of unique sources with sufficient data within lookback period
        cursor = conn.cursor()
        lookback_days = var_config.get('lookback_days', 90)
        min_data_points = var_config.get('min_data_points_for_analysis', 10)
        time_threshold = Time.now() - timedelta(days=lookback_days)
        mjd_threshold = time_threshold.mjd

        query = f"""
            SELECT source_id, COUNT(*) as count
            FROM photometry_measurements
            WHERE mjd >= ? AND relative_flux IS NOT NULL AND relative_flux_error IS NOT NULL AND relative_flux_error > 0
            GROUP BY source_id
            HAVING count >= ?
        """
        cursor.execute(query, (mjd_threshold, min_data_points))
        sources_to_analyze = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {len(sources_to_analyze)} sources with >= {min_data_points} data points in the last {lookback_days} days.")

        # Analyze each source
        processed_count = 0
        for source_id in sources_to_analyze:
            logger.info(f"Analyzing source: {source_id}")
            lc_df = fetch_light_curve(config, conn, source_id)
            if lc_df is None:
                continue

            baseline_stats = calculate_baseline_stats(lc_df)
            if np.isnan(baseline_stats['median']):
                logger.warning(f"Source {source_id}: Could not calculate baseline stats.")
                continue

            lc_with_deviations = detect_significant_deviations(lc_df, baseline_stats, config)
            candidate_events = find_candidate_events(lc_with_deviations, baseline_stats, config)

            if candidate_events:
                logger.info(f"!!! Found {len(candidate_events)} candidate variability event(s) for {source_id} !!!")
                for event in candidate_events:
                    event['source_id'] = source_id # Add source ID to event dict
                    all_candidates.append(event)
            processed_count += 1

        logger.info(f"Finished analyzing {processed_count} sources.")

    except Exception as e:
        logger.error(f"Error during variability analysis loop: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed.")

    # --- Save Candidate List ---
    if all_candidates:
        candidate_df = pd.DataFrame(all_candidates)
        # Reorder columns for clarity
        cols = ['source_id', 'start_mjd', 'end_mjd', 'duration_days', 'sign', 'n_points', 'peak_deviation_sigma']
        candidate_df = candidate_df[cols]
        logger.info(f"Saving {len(candidate_df)} candidate events to {candidate_list_path}")
        try:
            # Append or overwrite? Overwrite for now for simplicity
            candidate_df.to_csv(candidate_list_path, index=False, float_format='%.4f')
        except Exception as e:
            logger.error(f"Failed to save candidate list: {e}", exc_info=True)
    else:
        logger.info("No candidate variability events found in this run.")
        # Optionally clear or touch the candidate file
        # open(candidate_list_path, 'w').close() # Create empty file

    logger.info("Variability analysis run finished.")


# Example of how this might be run (e.g., by cron or scheduler)
if __name__ == '__main__':
    # This block would typically be called by a scheduler
    # It needs to load the config file first
    import yaml
    from pipeline_utils import setup_logging # Assuming utils is in the same directory or PYTHONPATH

    # --- Dummy Config Loading ---
    # Replace with actual loading from config_parser.py
    config_path = '../config/pipeline_config.yaml' # Adjust path as needed
    if os.path.exists(config_path):
         with open(config_path, 'r') as f:
              config = yaml.safe_load(f)
    else:
         print(f"ERROR: Config file not found at {config_path}")
         exit(1)

    # --- Setup Logging ---
    log_dir = config['paths'].get('log_dir', '../logs')
    setup_logging(log_dir, config_name="variability_analysis")

    # --- Run Analysis ---
    analyze_variability(config)
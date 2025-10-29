import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from astropy.time import Time
from dsa110_contimg.notebooks.calibrator_helper import load_pointing
import os

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_observation_files(data_dir: Path, start_date: datetime, end_date: datetime) -> List[Tuple[datetime, Path]]:
    """Finds primary observation files (_sb00.hdf5 or .ms) within a date range."""
    files_to_process = []
    logger.info(f"Scanning for primary files in {data_dir} from {start_date.date()} to {end_date.date()}")
    
    end_date_inclusive = end_date + timedelta(days=1)

    for root, _, files in os.walk(data_dir):
        for filename in files:
            if not (filename.endswith('_sb00.hdf5') or filename.endswith('.ms')):
                continue
            
            try:
                timestamp_str = filename.split('_')[0]
                file_date = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                
                if start_date <= file_date < end_date_inclusive:
                    files_to_process.append((file_date, Path(os.path.join(root, filename))))
            except (ValueError, IndexError):
                continue

    files_to_process.sort()
    logger.info(f"Found {len(files_to_process)} primary observation files to process.")
    return files_to_process

def extract_pointing_data(files_with_dates: List[Tuple[datetime, Path]]) -> pd.DataFrame:
    """Extracts pointing data from a list of observation files."""
    pointing_data = []
    for file_date, file_path in files_with_dates:
        try:
            info = load_pointing(file_path)
            # Use the timestamp from the filename, which is more reliable
            if info and 'dec_deg' in info:
                pointing_data.append({
                    'datetime': file_date,
                    'declination': info['dec_deg']
                })
        except Exception as e:
            logger.warning(f"Could not process file {file_path}: {e}")
    return pd.DataFrame(pointing_data)

def find_temporal_gaps(data_dir: Path, start_date: datetime, end_date: datetime, gap_threshold_minutes: float = 5.0) -> List[dict]:
    """Find temporal gaps in HDF5 file timestamps.
    
    Parameters
    ----------
    data_dir : Path
        Directory containing HDF5 files
    start_date : datetime
        Start date for analysis
    end_date : datetime
        End date for analysis
    gap_threshold_minutes : float
        Minimum gap in minutes to report (default: 5.0)
        
    Returns
    -------
    List[dict]
        List of gaps with 'start', 'end', and 'duration_minutes' keys
    """
    logger.info(f"Analyzing temporal gaps in {data_dir}")
    
    # Collect all HDF5 file timestamps (any subband, not just sb00)
    timestamps = []
    end_date_inclusive = end_date + timedelta(days=1)
    
    for root, _, files in os.walk(data_dir):
        for filename in files:
            if not filename.endswith('.hdf5'):
                continue
            
            try:
                timestamp_str = filename.split('_')[0]
                file_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                
                if start_date <= file_time < end_date_inclusive:
                    timestamps.append(file_time)
            except (ValueError, IndexError):
                continue
    
    if not timestamps:
        logger.warning("No HDF5 files found")
        return []
    
    # Sort timestamps
    timestamps = sorted(set(timestamps))  # Remove duplicates and sort
    logger.info(f"Found {len(timestamps)} unique observation timestamps")
    
    # Find gaps
    gaps = []
    for i in range(1, len(timestamps)):
        time_diff_minutes = (timestamps[i] - timestamps[i-1]).total_seconds() / 60.0
        if time_diff_minutes > gap_threshold_minutes:
            gaps.append({
                'start': timestamps[i-1],
                'end': timestamps[i],
                'duration_minutes': time_diff_minutes
            })
    
    logger.info(f"Found {len(gaps)} temporal gaps > {gap_threshold_minutes} minutes")
    return gaps

def plot_declination_history(data: pd.DataFrame, output_path: Path, gap_threshold_hours: float = 2.0, temporal_gaps: List[dict] = None):
    """Plots declination vs. time and saves the figure.
    
    Parameters
    ----------
    data : pd.DataFrame
        DataFrame with 'datetime' and 'declination' columns
    output_path : Path
        Path to save the output plot
    gap_threshold_hours : float, optional
        Not used when temporal_gaps is provided (kept for backwards compatibility)
    temporal_gaps : List[dict], optional
        List of temporal gaps to highlight on the plot
    """
    if data.empty:
        logger.warning("No pointing data to plot.")
        return

    data = data.sort_values(by='datetime').reset_index(drop=True)

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(15, 7))

    # Get the full declination range
    dec_min = data['declination'].min()
    dec_max = data['declination'].max()
    dec_padding = (dec_max - dec_min) * 0.05  # 5% padding
    
    # Plot temporal gaps as vertical bands
    if temporal_gaps:
        for i, gap in enumerate(temporal_gaps):
            duration_hours = gap['duration_minutes'] / 60.0
            ax.axvspan(gap['start'], gap['end'], alpha=0.2, color='red', 
                       label=f'No data (max: {duration_hours:.1f}h)' if i == 0 else '', zorder=1)
            if duration_hours >= 1.0:  # Only log gaps >= 1 hour
                logger.info(f"Temporal gap: {gap['start']} to {gap['end']} ({duration_hours:.1f} hours)")
    
    # Plot the pointing data
    ax.plot(data['datetime'], data['declination'], 'o-', label='Pointing Declination', 
            markersize=4, color='blue', zorder=3)
    
    ax.set_xlabel('Observation Time', fontsize=12)
    ax.set_ylabel('Declination (degrees)', fontsize=12)
    ax.set_title('Telescope Pointing Declination vs. Time (with Data Gaps)', fontsize=14, fontweight='bold')
    
    # Set declination limits with padding
    ax.set_ylim(dec_min - dec_padding, dec_max + dec_padding)
    
    # Set a clear date formatter for the x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Create legend with unique labels
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='best')
    
    fig.savefig(output_path, dpi=150)
    logger.info(f"Plot saved to {output_path}")
    if temporal_gaps:
        logger.info(f"Total temporal gaps detected: {len(temporal_gaps)}")

def main():
    """Main function to generate the plot using a sparse sampling strategy."""
    parser = argparse.ArgumentParser(description="Generate a Declination vs. Time plot from observation data.")
    parser.add_argument('data_dir', type=Path, help="Directory containing the observation data.")
    parser.add_argument('--start-date', type=str, default='2025-10-01', help="Start date in YYYY-MM-DD format.")
    parser.add_argument('--end-date', type=str, default='2025-10-23', help="End date in YYYY-MM-DD format.")
    parser.add_argument('--output-path', type=Path, default='declination_vs_time.png', help="Path to save the output plot.")
    parser.add_argument('--jump-threshold-deg', type=float, default=0.1, help="Declination change to trigger granular search.")
    parser.add_argument('--gap-threshold-minutes', type=float, default=5.0, help="Temporal gap threshold in minutes to highlight missing data periods.")
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(args.end_date, '%Y-%m-%d')

    # Find temporal gaps in the data
    temporal_gaps = find_temporal_gaps(args.data_dir, start_dt, end_dt, gap_threshold_minutes=args.gap_threshold_minutes)

    all_files_with_dates = find_observation_files(args.data_dir, start_dt, end_dt)
    if not all_files_with_dates:
        logger.warning("No primary observation files found in the specified date range.")
        return

    # Create a sparse sample of files (one per day)
    sparse_files_with_dates = []
    last_day = None
    for file_date, file_path in all_files_with_dates:
        if last_day is None or (file_date.date() - last_day).days >= 1:
            sparse_files_with_dates.append((file_date, file_path))
            last_day = file_date.date()

    # Get pointing for the sparse sample
    sparse_pointing_df = extract_pointing_data(sparse_files_with_dates)
    if sparse_pointing_df.empty:
        logger.error("Could not extract any pointing data from the sparse file sample.")
        return
    sparse_pointing_df = sparse_pointing_df.sort_values(by='datetime').reset_index(drop=True)

    # Detect jumps in declination
    final_dfs = []
    last_idx = 0
    for i in range(1, len(sparse_pointing_df)):
        dec_diff = abs(sparse_pointing_df.loc[i, 'declination'] - sparse_pointing_df.loc[i-1, 'declination'])
        if dec_diff > args.jump_threshold_deg:
            logger.info(f"Declination jump of {dec_diff:.2f} deg detected. Processing granularly.")
            start_time = sparse_pointing_df.loc[i-1, 'datetime']
            end_time = sparse_pointing_df.loc[i, 'datetime']
            
            # Add the segment before the jump
            final_dfs.append(sparse_pointing_df.iloc[last_idx:i])
            
            # Get all files in the jump interval
            files_in_jump_with_dates = [(d, p) for d, p in all_files_with_dates if start_time <= d <= end_time]
            detailed_df = extract_pointing_data(files_in_jump_with_dates)
            final_dfs.append(detailed_df)
            last_idx = i

    final_dfs.append(sparse_pointing_df.iloc[last_idx:])
    
    if not final_dfs:
        logger.warning("No data to plot after processing.")
        return

    final_pointing_df = pd.concat(final_dfs, ignore_index=True)
    plot_declination_history(final_pointing_df, args.output_path, temporal_gaps=temporal_gaps)

if __name__ == '__main__':
    main()

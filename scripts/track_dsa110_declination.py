#!/usr/bin/env python3
"""
Script to track the declination of the DSA-110 over time by analyzing HDF5 visibility files.

This script:
1. Finds all *sb00.hdf5 files in /data/incoming/
2. Extracts RA, Dec, and timestamp information from each file
3. Plots Dec vs time and RA vs time
"""

import os
import glob
import h5py
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
from pathlib import Path


def extract_ra_dec_timestamp(hdf5_file):
    """
    Extract RA, Dec, and timestamp from an HDF5 file.
    
    Note: The telescope uses HADEC coordinate system, so we extract:
    - Declination from phase_center_app_dec
    - Hour Angle from extra_keywords (which is 0.0 for meridian observations)
    - Timestamp from time_array
    
    Args:
        hdf5_file (str): Path to the HDF5 file
        
    Returns:
        tuple: (hour_angle, dec, timestamp) or (None, None, None) if extraction fails
    """
    try:
        with h5py.File(hdf5_file, 'r') as f:
            # Extract declination (in radians)
            dec = f['Header']['phase_center_app_dec'][()]
            
            # Extract hour angle (in radians)
            ha = f['Header']['extra_keywords']['ha_phase_center'][()]
            
            # Extract timestamp (Julian Day)
            time_array = f['Header']['time_array'][:]
            # Use the first timestamp as representative
            jd = time_array[0]
            
            # Convert JD to datetime
            jd_epoch = 2440587.5  # Julian day of Unix epoch
            unix_time = (jd - jd_epoch) * 86400
            timestamp = datetime.fromtimestamp(unix_time)
            
            return ha, dec, timestamp
            
    except Exception as e:
        print(f"Error processing {hdf5_file}: {e}")
        return None, None, None


def find_sb00_files(data_dir):
    """
    Find all *sb00.hdf5 files in the specified directory.
    
    Args:
        data_dir (str): Directory to search for files
        
    Returns:
        list: Sorted list of file paths
    """
    pattern = os.path.join(data_dir, "*sb00.hdf5")
    files = glob.glob(pattern)
    return sorted(files)


def plot_ra_dec_tracking(ha_data, dec_data, timestamps, output_dir="."):
    """
    Create plots of Hour Angle and Dec vs time.
    
    Args:
        ha_data (list): List of Hour Angle values
        dec_data (list): List of Dec values  
        timestamps (list): List of datetime objects
        output_dir (str): Directory to save plots
    """
    # Convert to numpy arrays for easier handling
    ha_array = np.array(ha_data)
    dec_array = np.array(dec_data)
    
    # Convert timestamps to matplotlib format
    time_plot = [t for t in timestamps]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot Declination vs time
    ax1.plot(time_plot, np.degrees(dec_array), 'b-', marker='o', markersize=3)
    ax1.set_ylabel('Declination (degrees)')
    ax1.set_title('DSA-110 Declination Tracking Over Time')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot Hour Angle vs time
    ax2.plot(time_plot, np.degrees(ha_array), 'r-', marker='o', markersize=3)
    ax2.set_ylabel('Hour Angle (degrees)')
    ax2.set_xlabel('Time')
    ax2.set_title('DSA-110 Hour Angle Tracking Over Time')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    # Format x-axis to show dates nicely
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.xaxis.set_major_locator(plt.matplotlib.dates.HourLocator(interval=6))
    
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, "dsa110_ra_dec_tracking.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {output_file}")
    
    # Also save data as CSV for further analysis
    csv_file = os.path.join(output_dir, "dsa110_ra_dec_data.csv")
    with open(csv_file, 'w') as f:
        f.write("timestamp,hour_angle_degrees,dec_degrees,hour_angle_radians,dec_radians\n")
        for i, (t, ha, dec) in enumerate(zip(timestamps, ha_data, dec_data)):
            f.write(f"{t.isoformat()},{np.degrees(ha):.6f},{np.degrees(dec):.6f},{ha:.6f},{dec:.6f}\n")
    print(f"Data saved to: {csv_file}")
    
    plt.show()


def main():
    """Main function to process files and create plots."""
    parser = argparse.ArgumentParser(description='Track DSA-110 RA/Dec over time')
    parser.add_argument('--data-dir', default='/data/incoming', 
                       help='Directory containing HDF5 files (default: /data/incoming)')
    parser.add_argument('--output-dir', default='.', 
                       help='Output directory for plots and data (default: current directory)')
    parser.add_argument('--max-files', type=int, default=None,
                       help='Maximum number of files to process (default: all)')
    
    args = parser.parse_args()
    
    # Find all sb00 files
    print(f"Searching for *sb00.hdf5 files in {args.data_dir}...")
    files = find_sb00_files(args.data_dir)
    
    if not files:
        print(f"No *sb00.hdf5 files found in {args.data_dir}")
        return
    
    print(f"Found {len(files)} files")
    
    # Limit number of files if specified
    if args.max_files:
        files = files[:args.max_files]
        print(f"Processing first {len(files)} files")
    
    # Extract data from files
    ha_data = []
    dec_data = []
    timestamps = []
    
    print("Processing files...")
    for i, file_path in enumerate(files):
        if i % 10 == 0:
            print(f"  Processing file {i+1}/{len(files)}: {os.path.basename(file_path)}")
        
        ha, dec, timestamp = extract_ra_dec_timestamp(file_path)
        
        if ha is not None and dec is not None and timestamp is not None:
            ha_data.append(ha)
            dec_data.append(dec)
            timestamps.append(timestamp)
    
    print(f"Successfully processed {len(ha_data)} files")
    
    if not ha_data:
        print("No valid data extracted from any files")
        return
    
    # Create plots
    print("Creating plots...")
    plot_ra_dec_tracking(ha_data, dec_data, timestamps, args.output_dir)
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"  Time range: {min(timestamps)} to {max(timestamps)}")
    print(f"  Declination range: {np.degrees(min(dec_data)):.6f} to {np.degrees(max(dec_data)):.6f} degrees")
    print(f"  Hour Angle range: {np.degrees(min(ha_data)):.6f} to {np.degrees(max(ha_data)):.6f} degrees")
    print(f"  Declination std dev: {np.degrees(np.std(dec_data)):.6f} degrees")
    print(f"  Hour Angle std dev: {np.degrees(np.std(ha_data)):.6f} degrees")


if __name__ == "__main__":
    main()

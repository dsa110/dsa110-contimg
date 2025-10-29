#!/usr/bin/env python3
"""
Plot a simple timeline of all observation timestamps in /data/incoming/
with declination overplotted.
"""
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from dsa110_contimg.notebooks.calibrator_helper import load_pointing

def find_complete_groups(data_dir: Path, start_date: datetime = None, end_date: datetime = None):
    """Find all timestamps with any HDF5 files."""
    print(f"Scanning {data_dir} for HDF5 files...")
    
    # Collect all unique timestamps
    timestamps = set()
    
    for root, _, files in os.walk(data_dir):
        for filename in files:
            if not filename.endswith('.hdf5'):
                continue
            
            try:
                # Parse timestamp from filename
                # Format: YYYY-MM-DDTHH:MM:SS_sbXX.hdf5
                parts = filename.split('_sb')
                if len(parts) != 2:
                    continue
                
                timestamp_str = parts[0]
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                
                # Filter by date range if provided
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue
                
                timestamps.add(timestamp)
                
            except (ValueError, IndexError) as e:
                continue
    
    timestamps = sorted(list(timestamps))
    
    print(f"Found {len(timestamps)} unique observation timestamps")
    
    return timestamps, []

def get_declinations(data_dir: Path, timestamps):
    """Get declination for each timestamp by reading sb00 files."""
    print("Reading declinations from HDF5 files...")
    
    dec_data = []
    for i, timestamp in enumerate(timestamps):
        if i % 1000 == 0:
            print(f"  Processing {i}/{len(timestamps)}...")
        
        # Try to find sb00 file for this timestamp
        timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S')
        sb00_file = data_dir / f"{timestamp_str}_sb00.hdf5"
        
        if sb00_file.exists():
            try:
                info = load_pointing(sb00_file)
                if info and 'dec_deg' in info:
                    dec_data.append({
                        'datetime': timestamp,
                        'declination': info['dec_deg']
                    })
            except Exception as e:
                pass
    
    print(f"Successfully read {len(dec_data)} declinations")
    return dec_data

def plot_timeline(timestamps, output_path: Path, data_dir: Path = None):
    """Plot timeline of observation timestamps with declination overplotted."""
    if not timestamps:
        print("No timestamps to plot!")
        return
    
    print(f"Plotting {len(timestamps)} timestamps...")
    
    # Create figure with two y-axes
    fig, ax1 = plt.subplots(figsize=(16, 7))
    
    # Plot timestamps as vertical lines on bottom axis
    y_values = [0] * len(timestamps)
    ax1.scatter(timestamps, y_values, marker='|', s=100, alpha=0.4, color='gray', 
                label='Observations', zorder=1)
    
    # Format bottom axis
    ax1.set_xlabel('Observation Time', fontsize=12)
    ax1.set_ylabel('')
    ax1.set_yticks([])
    ax1.set_ylim(-0.5, 0.5)
    
    # Create second y-axis for declination
    ax2 = ax1.twinx()
    
    # Get and plot declination data if data_dir provided
    if data_dir:
        dec_data = get_declinations(data_dir, timestamps)
        if dec_data:
            dec_times = [d['datetime'] for d in dec_data]
            dec_values = [d['declination'] for d in dec_data]
            
            ax2.plot(dec_times, dec_values, 'o-', color='blue', markersize=3, 
                    linewidth=1.5, alpha=0.7, label='Declination', zorder=2)
            ax2.set_ylabel('Declination (degrees)', fontsize=12, color='blue')
            ax2.tick_params(axis='y', labelcolor='blue')
            
            # Add some padding to declination range
            dec_min, dec_max = min(dec_values), max(dec_values)
            dec_padding = (dec_max - dec_min) * 0.1
            ax2.set_ylim(dec_min - dec_padding, dec_max + dec_padding)
    
    # Title
    ax1.set_title(f'DSA-110 Observation Timeline with Declination ({len(timestamps)} timestamps)', 
                 fontsize=14, fontweight='bold')
    
    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.xticks(rotation=45, ha='right')
    
    # Add grid
    ax1.grid(True, axis='x', alpha=0.3)
    
    # Add statistics text
    time_span = (timestamps[-1] - timestamps[0]).days
    stats_text = f"First: {timestamps[0].strftime('%Y-%m-%d %H:%M:%S')}\n"
    stats_text += f"Last: {timestamps[-1].strftime('%Y-%m-%d %H:%M:%S')}\n"
    stats_text += f"Span: {time_span} days\n"
    stats_text += f"Total: {len(timestamps)} timestamps"
    
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
            verticalalignment='top', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Add legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    if data_dir:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"Plot saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Plot timeline of all observation timestamps")
    parser.add_argument('data_dir', type=Path, help="Directory containing HDF5 files")
    parser.add_argument('--start-date', type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument('--end-date', type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument('--output', type=Path, default='/tmp/observation_timeline.png',
                        help="Output plot path")
    args = parser.parse_args()
    
    start_dt = datetime.strptime(args.start_date, '%Y-%m-%d') if args.start_date else None
    end_dt = datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else None
    
    timestamps, _ = find_complete_groups(
        args.data_dir, start_dt, end_dt
    )
    
    plot_timeline(timestamps, args.output, data_dir=args.data_dir)

if __name__ == '__main__':
    main()


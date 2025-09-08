import sys
import os
import glob
from collections import defaultdict
from datetime import datetime, timedelta

# Add the pipeline parent directory to your Python path
pipeline_parent_dir = '/data/jfaber/dsa110-contimg/'  # Adjust this to your actual path
if pipeline_parent_dir not in sys.path:
    sys.path.insert(0, pipeline_parent_dir)

# Import pipeline modules
from pipeline import ms_creation, config_parser

# Load configuration from YAML file
CONFIG_PATH = 'config/pipeline_config.yaml'
config = config_parser.load_config(CONFIG_PATH)

if not config:
    raise ValueError("Failed to load configuration from YAML file")

config['services']['hdf5_post_handle'] = 'none'  # Don't delete files during testing

def find_hdf5_sets_with_time_tolerance(config, hdf5_dir, start_time_str, end_time_str, 
                                     grouping_tolerance_minutes=3, time_format="%Y%m%dT%H%M%S"):
    """
    Find complete HDF5 sets within a time range, grouping files within +/- tolerance minutes.
    Files within the tolerance window are grouped together even if they cross minute boundaries.
    
    Parameters:
    - grouping_tolerance_minutes: Files within +/- this many minutes are grouped together
    """
    
    # Parse start and end times
    try:
        start_dt = datetime.strptime(start_time_str, time_format)
        end_dt = datetime.strptime(end_time_str, time_format)
    except ValueError as e:
        print(f"Invalid time format: {e}")
        return {}
    
    print(f"Searching for HDF5 sets between {start_dt} and {end_dt}")
    print(f"Grouping files with +/- {grouping_tolerance_minutes} minute tolerance...")
    
    # Get configuration parameters
    expected_spws_set = set(config['ms_creation']['spws'])
    
    # Find all HDF5 files
    all_files = glob.glob(os.path.join(hdf5_dir, "20*T*.hdf5"))
    print(f"Found {len(all_files)} HDF5 files to examine")
    
    # Parse all files and extract their info
    file_info_list = []
    
    for f_path in all_files:
        try:
            f_name = os.path.basename(f_path)
            parts = f_name.split('_')
            
            # Parse timestamp from filename (format: YYYY-MM-DDTHH:MM:SS_sbXX.hdf5)
            timestamp_str_from_file = parts[0]
            file_dt = datetime.strptime(timestamp_str_from_file, "%Y-%m-%dT%H:%M:%S")
            
            # Check if file timestamp is within our search range
            if start_dt <= file_dt <= end_dt:
                spw_str = parts[1].replace('.hdf5', '')
                base_spw = spw_str.split('spl')[0]  # Handle any 'spl' suffixes
                
                if base_spw in expected_spws_set:
                    file_info_list.append({
                        'path': f_path,
                        'filename': f_name,
                        'datetime': file_dt,
                        'timestamp_str': timestamp_str_from_file,
                        'spw': base_spw
                    })
                    
        except (IndexError, ValueError) as e:
            print(f"Could not parse filename {f_name}: {e}")
            continue
    
    print(f"Found {len(file_info_list)} valid files in time range")
    
    # Sort files by timestamp
    file_info_list.sort(key=lambda x: x['datetime'])
    
    # Group files using time tolerance
    tolerance_delta = timedelta(minutes=grouping_tolerance_minutes)
    groups = []
    
    # Create time-based groups using a sliding window approach
    for file_info in file_info_list:
        current_time = file_info['datetime']
        
        # Check if this file can join an existing group
        joined_group = False
        for group in groups:
            # Check if current file is within tolerance of any file in this group
            for existing_file in group:
                time_diff = abs((current_time - existing_file['datetime']).total_seconds() / 60.0)
                if time_diff <= grouping_tolerance_minutes:
                    group.append(file_info)
                    joined_group = True
                    break
            if joined_group:
                break
        
        # If not joined to existing group, create new group
        if not joined_group:
            groups.append([file_info])
    
    print(f"Created {len(groups)} time-based groups")
    
    # Check each group for completeness
    complete_sets = {}
    
    for i, group in enumerate(groups):
        print(f"\nAnalyzing group {i+1} ({len(group)} files):")
        
        # Show time range of this group
        group_times = [f['datetime'] for f in group]
        min_time = min(group_times)
        max_time = max(group_times)
        time_span_minutes = (max_time - min_time).total_seconds() / 60.0
        
        print(f"  Time range: {min_time.strftime('%H:%M:%S')} to {max_time.strftime('%H:%M:%S')} (span: {time_span_minutes:.1f} min)")
        
        # Group files by SPW
        spw_files = defaultdict(list)
        for file_info in group:
            spw_files[file_info['spw']].append(file_info)
            
        # Show what SPWs we have
        present_spws = set(spw_files.keys())
        missing_spws = expected_spws_set - present_spws
        
        print(f"  Present SPWs ({len(present_spws)}): {sorted(list(present_spws))}")
        if missing_spws:
            print(f"  Missing SPWs ({len(missing_spws)}): {sorted(list(missing_spws))}")
            continue
        
        # We have all SPWs - now select best file for each SPW
        selected_files = []
        group_center_time = min_time + (max_time - min_time) / 2  # Middle of the group
        
        for spw in sorted(expected_spws_set):
            candidates = spw_files[spw]
            
            if len(candidates) == 1:
                selected_file = candidates[0]
            else:
                # Multiple candidates - select the one closest to group center time
                selected_file = min(candidates, 
                                  key=lambda x: abs((x['datetime'] - group_center_time).total_seconds()))
                print(f"    {spw}: Selected {selected_file['timestamp_str']} from {len(candidates)} candidates")
            
            selected_files.append(selected_file['path'])
        
        # Use the center time as the key for this group
        group_key = group_center_time.strftime("%Y%m%dT%H%M%S")
        complete_sets[group_key] = selected_files
        
        print(f"  ✓ Complete set for group {group_key} with {len(selected_files)} files")
    
    print(f"\nFound {len(complete_sets)} complete HDF5 sets with time tolerance grouping")
    return complete_sets

def process_time_range_with_tolerance(config, hdf5_dir, start_time_str, end_time_str, tolerance_minutes=3):
    """
    Process all complete HDF5 sets found within a time range, using time tolerance for grouping.
    """
    # Find all complete sets in the time range
    hdf5_sets = find_hdf5_sets_with_time_tolerance(config, hdf5_dir, start_time_str, end_time_str, tolerance_minutes)
    
    if not hdf5_sets:
        print("No complete HDF5 sets found in the specified time range")
        return []
    
    successful_ms_files = []
    
    # Process each complete set
    for group_timestamp, hdf5_files in sorted(hdf5_sets.items()):
        print(f"\n--- Processing group timestamp: {group_timestamp} ---")
        print(f"Files: {[os.path.basename(f) for f in hdf5_files]}")
        
        try:
            ms_path = ms_creation.process_hdf5_set(config, group_timestamp, hdf5_files)
            
            if ms_path:
                print(f"✓ Successfully created MS: {ms_path}")
                successful_ms_files.append(ms_path)
            else:
                print(f"✗ Failed to create MS for {group_timestamp}")
                
        except Exception as e:
            print(f"✗ Error processing {group_timestamp}: {e}")
            continue
    
    return successful_ms_files

# Example usage
if __name__ == "__main__":
    # Your HDF5 directory
    hdf5_dir = config['paths']['hdf5_incoming']  # Or specify directly: "/data/incoming/"
    
    # Specify your time range (format: YYYYMMDDTHHMMSS)
    start_time = "20250529T055000"  # Start of search range  
    end_time = "20250529T070000"    # End of search range
    
    # Tolerance for grouping files together (in minutes)
    tolerance_minutes = 3  # Files within +/- 3 minutes will be grouped
    
    print(f"Processing HDF5 files between {start_time} and {end_time}")
    print(f"Using +/- {tolerance_minutes} minute tolerance for grouping...")
    
    # Process all complete sets in the time range
    successful_ms_files = process_time_range_with_tolerance(config, hdf5_dir, start_time, end_time, tolerance_minutes)
    
    print(f"\n--- Final Summary ---")
    print(f"Successfully created {len(successful_ms_files)} MS files:")
    for ms_file in successful_ms_files:
        print(f"  - {os.path.basename(ms_file)}")
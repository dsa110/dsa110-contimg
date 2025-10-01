#!/usr/bin/env python3
"""
Test the new pipeline architecture with real DSA-110 HDF5 data.

This script tests our new, well-structured pipeline code with the actual
HDF5 data from /data/incoming_test/.
"""

import os
import sys
import asyncio
import h5py
import numpy as np
from pathlib import Path
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def read_dsa110_hdf5_simple(file_path):
    """Read DSA-110 HDF5 file and extract key information."""
    print(f"Reading HDF5 file: {os.path.basename(file_path)}")
    
    with h5py.File(file_path, 'r') as f:
        # Read basic info
        header = f['Header']
        
        # Data dimensions
        Nblts = header['Nblts'][()]
        Nfreqs = header['Nfreqs'][()]
        Npols = header['Npols'][()]
        Nants_data = header['Nants_data'][()]
        
        # Time and frequency
        time_array = header['time_array'][()]
        freq_array = header['freq_array'][()]
        
        # Telescope info
        telescope_name = header['telescope_name'][()].decode()
        lat = header['latitude'][()]
        lon = header['longitude'][()]
        alt = header['altitude'][()]
        
        # Antenna info
        antenna_names = [name.decode() for name in header['antenna_names'][()]]
        antenna_numbers = header['antenna_numbers'][()]
        
        print(f"  Telescope: {telescope_name}")
        print(f"  Location: lat={lat:.6f}, lon={lon:.6f}, alt={alt:.1f}m")
        print(f"  Data shape: ({Nblts}, 1, {Nfreqs}, {Npols})")
        print(f"  Antennas: {Nants_data} data, {len(antenna_names)} total")
        print(f"  Frequency range: {freq_array.min()/1e9:.3f} - {freq_array.max()/1e9:.3f} GHz")
        print(f"  Time range: {Time(time_array.min(), format='mjd').iso} - {Time(time_array.max(), format='mjd').iso}")
        
        return {
            'telescope_name': telescope_name,
            'location': (lat, lon, alt),
            'dimensions': (Nblts, Nfreqs, Npols, Nants_data),
            'time_array': time_array,
            'freq_array': freq_array,
            'antenna_names': antenna_names,
            'antenna_numbers': antenna_numbers
        }

def test_hdf5_reading():
    """Test reading HDF5 files."""
    print("=== Testing HDF5 File Reading ===")
    
    test_dir = Path("/data/incoming_test/")
    hdf5_files = list(test_dir.glob("*.hdf5"))
    
    if not hdf5_files:
        print("❌ No HDF5 files found")
        return False
    
    print(f"Found {len(hdf5_files)} HDF5 files")
    
    # Test reading first few files
    success_count = 0
    for i, file_path in enumerate(hdf5_files[:3]):
        try:
            data = read_dsa110_hdf5_simple(file_path)
            success_count += 1
            print(f"✅ File {i+1}: {file_path.name}")
        except Exception as e:
            print(f"❌ File {i+1}: {file_path.name} - Error: {e}")
    
    print(f"Successfully read {success_count}/{min(3, len(hdf5_files))} files")
    return success_count > 0

def test_data_analysis():
    """Test basic data analysis."""
    print("\n=== Testing Data Analysis ===")
    
    test_dir = Path("/data/incoming_test/")
    hdf5_files = list(test_dir.glob("*.hdf5"))
    
    if not hdf5_files:
        print("❌ No HDF5 files found")
        return False
    
    # Group files by timestamp
    timestamp_groups = {}
    for file in hdf5_files:
        timestamp = file.name.split('_')[0]
        if timestamp not in timestamp_groups:
            timestamp_groups[timestamp] = []
        timestamp_groups[timestamp].append(file)
    
    print(f"Found {len(timestamp_groups)} timestamp groups")
    
    # Analyze first group
    first_timestamp = list(timestamp_groups.keys())[0]
    files = sorted(timestamp_groups[first_timestamp])
    
    print(f"Analyzing timestamp group: {first_timestamp}")
    print(f"Files in group: {len(files)}")
    
    # Check subband coverage
    subbands = set()
    for file in files:
        if '_sb' in file.name:
            subband = file.name.split('_sb')[1].split('.')[0]
            subbands.add(subband)
    
    print(f"Subbands found: {sorted(subbands)}")
    print(f"Expected subbands: 16 (sb00-sb15)")
    print(f"Coverage: {len(subbands)}/16 subbands")
    
    return len(subbands) > 0

def test_pipeline_config():
    """Test pipeline configuration."""
    print("\n=== Testing Pipeline Configuration ===")
    
    try:
        from dsa110.utils.config_loader import load_pipeline_config
        
        config = load_pipeline_config(environment="development")
        
        print("✅ Configuration loaded successfully")
        print(f"  HDF5 incoming: {config['paths']['hdf5_incoming']}")
        print(f"  Pipeline base: {config['paths']['pipeline_base_dir']}")
        print(f"  Expected subbands: {config['services']['hdf5_expected_subbands']}")
        print(f"  SPWs: {config['ms_creation']['spws']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_services():
    """Test service initialization."""
    print("\n=== Testing Service Initialization ===")
    
    try:
        from services.hdf5_watcher import HDF5WatcherService
        from services.ms_processor import MSProcessorService
        from services.variability_analyzer import VariabilityAnalyzerService
        
        print("✅ Service imports successful")
        
        # Test service creation (without starting)
        config_path = "config/pipeline_config.yaml"
        
        hdf5_service = HDF5WatcherService(config_path, "development")
        ms_service = MSProcessorService(config_path, "development")
        var_service = VariabilityAnalyzerService(config_path, "development")
        
        print("✅ Service objects created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

async def test_async_functionality():
    """Test async functionality."""
    print("\n=== Testing Async Functionality ===")
    
    try:
        from dsa110.utils.logging import setup_logging
        from dsa110.data_ingestion.ms_creation import MSCreationManager
        from dsa110.utils.config_loader import load_pipeline_config
        
        # Setup logging
        setup_logging(log_dir="logs", config_name="test_new_pipeline")
        
        # Load config
        config = load_pipeline_config(environment="development")
        
        # Create MS manager
        ms_manager = MSCreationManager(config)
        
        print("✅ Async components initialized successfully")
        
        # Test with a simple HDF5 file
        test_file = "/data/incoming_test/2025-09-05T03:23:14_sb00.hdf5"
        output_ms = "test_outputs/test_async.ms"
        
        # Ensure output directory exists
        os.makedirs("test_outputs", exist_ok=True)
        
        print(f"Testing MS creation: {os.path.basename(test_file)}")
        
        # This might fail due to PyUVData compatibility issues, but let's try
        try:
            success = await ms_manager.create_ms_from_hdf5(test_file, output_ms)
            if success:
                print("✅ MS creation successful")
                return True
            else:
                print("⚠️ MS creation failed (expected due to data format)")
                return False
        except Exception as e:
            print(f"⚠️ MS creation failed (expected): {e}")
            return False
        
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False

async def main():
    """Main test function."""
    print("DSA-110 New Pipeline Architecture Test")
    print("=" * 50)
    
    tests = [
        ("HDF5 File Reading", test_hdf5_reading),
        ("Data Analysis", test_data_analysis),
        ("Pipeline Configuration", test_pipeline_config),
        ("Service Initialization", test_services),
        ("Async Functionality", test_async_functionality)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- Running {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
        except Exception as e:
            print(f"{test_name}: ❌ FAILED - {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed - this is expected for a work in progress")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())

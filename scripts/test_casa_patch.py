#!/usr/bin/env python3
"""
Test script to verify CASA logging patch works.

This script tests that the CASA logging patch successfully redirects
all casalog.setlogfile() calls to the casalogs directory.
"""

import os
import sys
import yaml
from pathlib import Path
import time

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.casa_logging import get_casa_log_directory
from dsa110.utils.casa_logging_patch import patch_casa_logging, apply_casa_logging_patch

def test_casa_patch():
    """Test CASA logging patch."""
    
    print("Testing CASA logging patch...")
    
    # Load configuration
    config_path = project_root / "config" / "pipeline_config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get CASA log directory
    casa_log_dir = get_casa_log_directory(config)
    print(f"CASA log directory: {casa_log_dir}")
    
    # Count existing log files
    root_logs_before = list(project_root.glob("casa-*.log"))
    casalogs_dir = project_root / "casalogs"
    casalogs_logs_before = list(casalogs_dir.glob("*.log")) if casalogs_dir.exists() else []
    
    print(f"Log files before patch:")
    print(f"  Root directory: {len(root_logs_before)}")
    print(f"  Casalogs directory: {len(casalogs_logs_before)}")
    
    # Apply the patch
    print("\nApplying CASA logging patch...")
    patch_casa_logging(casa_log_dir)
    success = apply_casa_logging_patch()
    
    if not success:
        print("❌ FAILED: Could not apply CASA logging patch")
        return
    
    print("✅ CASA logging patch applied successfully")
    
    # Test the patch by calling casalog.setlogfile() with various paths
    try:
        from casatasks import casalog
        
        print("\nTesting patch with various log file paths...")
        
        # Test 1: Call setlogfile with a path in the root directory
        test_path_1 = str(project_root / "test_casa_log_1.log")
        print(f"Calling casalog.setlogfile('{test_path_1}')")
        casalog.setlogfile(test_path_1)
        print(f"Current CASA log file: {casalog.logfile()}")
        
        # Test 2: Call setlogfile with a relative path
        test_path_2 = "test_casa_log_2.log"
        print(f"Calling casalog.setlogfile('{test_path_2}')")
        casalog.setlogfile(test_path_2)
        print(f"Current CASA log file: {casalog.logfile()}")
        
        # Test 3: Call setlogfile with a path that's already in casalogs
        test_path_3 = str(casalogs_dir / "test_casa_log_3.log")
        print(f"Calling casalog.setlogfile('{test_path_3}')")
        casalog.setlogfile(test_path_3)
        print(f"Current CASA log file: {casalog.logfile()}")
        
        # Create some test log entries
        print("\nCreating test log entries...")
        casalog.post("Test log entry 1 - should go to casalogs directory")
        casalog.post("Test log entry 2 - should go to casalogs directory")
        
        # Wait for log files to be written
        time.sleep(2)
        
        # Check results
        root_logs_after = list(project_root.glob("casa-*.log"))
        casalogs_logs_after = list(casalogs_dir.glob("*.log")) if casalogs_dir.exists() else []
        
        print(f"\nLog files after patch:")
        print(f"  Root directory: {len(root_logs_after)}")
        print(f"  Casalogs directory: {len(casalogs_logs_after)}")
        
        # Check if any new log files were created in root directory
        new_root_logs = [log for log in root_logs_after if log not in root_logs_before]
        if new_root_logs:
            print(f"❌ FAILED: {len(new_root_logs)} new log files created in root directory:")
            for log_file in new_root_logs:
                print(f"  - {log_file.name}")
        else:
            print("✅ SUCCESS: No new log files created in root directory")
        
        # Check if new log files were created in casalogs directory
        new_casalogs_logs = [log for log in casalogs_logs_after if log not in casalogs_logs_before]
        if new_casalogs_logs:
            print(f"✅ SUCCESS: {len(new_casalogs_logs)} new log files created in casalogs directory:")
            for log_file in new_casalogs_logs:
                print(f"  - {log_file.name}")
        else:
            print("⚠️  No new log files detected in casalogs directory")
        
    except ImportError:
        print("⚠️  casatasks not available for testing")
    except Exception as e:
        print(f"⚠️  Error testing CASA patch: {e}")

if __name__ == "__main__":
    test_casa_patch()

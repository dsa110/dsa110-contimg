#!/usr/bin/env python3
"""
Final test to verify CASA logging is working correctly.

This script tests that CASA log files are properly saved to the casalogs/ directory
and not in the root directory.
"""

import os
import sys
import yaml
from pathlib import Path
import time

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.casa_logging import force_casa_logging_to_directory, get_casa_log_directory

def test_casa_logging():
    """Test CASA logging configuration."""
    
    print("Testing CASA logging configuration...")
    
    # Load configuration
    config_path = project_root / "config" / "pipeline_config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get CASA log directory
    casa_log_dir = get_casa_log_directory(config)
    print(f"CASA log directory: {casa_log_dir}")
    
    # Count existing log files in root directory
    root_logs = list(project_root.glob("casa-*.log"))
    print(f"Log files in root directory: {len(root_logs)}")
    
    # Count existing log files in casalogs directory
    casalogs_dir = project_root / "casalogs"
    casalogs_logs = list(casalogs_dir.glob("*.log")) if casalogs_dir.exists() else []
    print(f"Log files in casalogs directory: {len(casalogs_logs)}")
    
    # Force CASA logging to casalogs directory
    print("\nForcing CASA logging to casalogs directory...")
    success = force_casa_logging_to_directory(casa_log_dir)
    
    if success:
        print("✅ SUCCESS: CASA logging forced to casalogs directory")
        
        # Test by creating a CASA operation
        try:
            from casatasks import casalog
            print(f"Current CASA log file: {casalog.logfile()}")
            
            # Create a test log entry
            casalog.post("Test log entry - this should go to casalogs directory")
            print("✅ Test log entry created successfully")
            
            # Wait a moment for the log file to be written
            time.sleep(1)
            
            # Check if a new log file was created in casalogs
            new_casalogs_logs = list(casalogs_dir.glob("*.log")) if casalogs_dir.exists() else []
            if len(new_casalogs_logs) > len(casalogs_logs):
                print("✅ SUCCESS: New log file created in casalogs directory")
            else:
                print("⚠️  No new log file detected in casalogs directory")
            
            # Check if any new log files were created in root directory
            new_root_logs = list(project_root.glob("casa-*.log"))
            if len(new_root_logs) > len(root_logs):
                print("❌ FAILED: New log file created in root directory")
                print("New root log files:")
                for log_file in new_root_logs:
                    if log_file not in root_logs:
                        print(f"  - {log_file.name}")
            else:
                print("✅ SUCCESS: No new log files created in root directory")
            
        except ImportError:
            print("⚠️  casatasks not available for testing")
        except Exception as e:
            print(f"⚠️  Error testing CASA logging: {e}")
    else:
        print("❌ FAILED: Could not force CASA logging to casalogs directory")
    
    # Show final status
    print(f"\nFinal status:")
    print(f"  Root directory log files: {len(list(project_root.glob('casa-*.log')))}")
    print(f"  Casalogs directory log files: {len(list(casalogs_dir.glob('*.log')))}")

if __name__ == "__main__":
    test_casa_logging()

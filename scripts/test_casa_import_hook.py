#!/usr/bin/env python3
"""
Test CASA import hook.

This script tests that the CASA import hook properly redirects CASA log files
to the casalogs directory.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the CASA import hook BEFORE any CASA imports
from dsa110.utils.casa_import_hook import setup_casa_logging_environment

def test_casa_import_hook():
    """Test CASA import hook."""
    
    print("Testing CASA import hook...")
    
    # Count existing log files
    root_logs_before = list(project_root.glob("casa-*.log"))
    casalogs_dir = project_root / "casalogs"
    casalogs_logs_before = list(casalogs_dir.glob("*.log")) if casalogs_dir.exists() else []
    
    print(f"Log files before CASA import:")
    print(f"  Root directory: {len(root_logs_before)}")
    print(f"  Casalogs directory: {len(casalogs_logs_before)}")
    
    # Import CASA (this should create a log file in casalogs directory)
    try:
        from casatasks import casalog
        print("✅ CASA imported successfully")
        
        # Check current log file
        current_log_file = casalog.logfile()
        print(f"Current CASA log file: {current_log_file}")
        
        # Create a test log entry
        casalog.post("Test log entry from import hook test")
        print("✅ Test log entry created")
        
    except ImportError as e:
        print(f"⚠️  CASA not available: {e}")
        return
    except Exception as e:
        print(f"⚠️  Error importing CASA: {e}")
        return
    
    # Count log files after CASA import
    root_logs_after = list(project_root.glob("casa-*.log"))
    casalogs_logs_after = list(casalogs_dir.glob("*.log")) if casalogs_dir.exists() else []
    
    print(f"\nLog files after CASA import:")
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

if __name__ == "__main__":
    test_casa_import_hook()

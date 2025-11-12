#!/usr/bin/env python3
"""
Force CASA logging to use the casalogs directory.

This script forces CASA to use the casalogs directory for all log files,
overriding any existing configuration.
"""

import os
import sys
import yaml
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.casa_logging import force_casa_logging_to_directory, get_casa_log_directory

def main():
    """Force CASA logging to casalogs directory."""
    
    # Load configuration
    config_path = project_root / "config" / "pipeline_config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("Forcing CASA logging to casalogs directory...")
    
    # Get CASA log directory
    casa_log_dir = get_casa_log_directory(config)
    print(f"CASA log directory: {casa_log_dir}")
    
    # Force CASA logging to this directory
    success = force_casa_logging_to_directory(casa_log_dir)
    
    if success:
        print("✅ SUCCESS: CASA logging forced to casalogs directory")
        
        # Test by creating a simple CASA operation
        try:
            from casatasks import casalog
            print(f"Current CASA log file: {casalog.logfile()}")
            
            # Create a test log entry
            casalog.post("CASA logging test - this should go to casalogs directory")
            print("✅ Test log entry created successfully")
            
        except ImportError:
            print("⚠️  casatasks not available for testing")
        except Exception as e:
            print(f"⚠️  Error testing CASA logging: {e}")
    else:
        print("❌ FAILED: Could not force CASA logging to casalogs directory")
    
    # Show current directory contents
    casalogs_dir = project_root / "casalogs"
    if casalogs_dir.exists():
        log_files = list(casalogs_dir.glob("*.log"))
        print(f"\nLog files in casalogs/: {len(log_files)}")
        for log_file in sorted(log_files)[-5:]:  # Show last 5 files
            print(f"  - {log_file.name}")

if __name__ == "__main__":
    main()

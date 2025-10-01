#!/usr/bin/env python3
"""
Test script to verify CASA logging configuration.

This script tests that CASA log files are properly saved to the casalogs/ directory.
"""

import os
import sys
import yaml
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.casa_logging import setup_casa_logging, ensure_casa_log_directory, get_casa_log_directory

def test_casa_logging():
    """Test CASA logging configuration."""
    
    # Load configuration
    config_path = project_root / "config" / "pipeline_config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("Testing CASA logging configuration...")
    print(f"Project root: {project_root}")
    
    # Test getting CASA log directory
    casa_log_dir = get_casa_log_directory(config)
    print(f"CASA log directory: {casa_log_dir}")
    
    # Test ensuring directory exists
    success = ensure_casa_log_directory(config)
    print(f"Directory creation: {'SUCCESS' if success else 'FAILED'}")
    
    # Test setting up CASA logging
    log_file = setup_casa_logging(casa_log_dir, "test_casa")
    if log_file:
        print(f"CASA log file: {log_file}")
        print(f"Log file exists: {os.path.exists(log_file)}")
        
        # Check if the file is in the casalogs directory
        if "casalogs" in log_file:
            print("✅ SUCCESS: CASA log file is in casalogs directory")
        else:
            print("❌ FAILED: CASA log file is not in casalogs directory")
    else:
        print("❌ FAILED: Could not set up CASA logging")
    
    # List existing log files in casalogs directory
    casalogs_dir = project_root / "casalogs"
    if casalogs_dir.exists():
        log_files = list(casalogs_dir.glob("*.log"))
        print(f"\nExisting log files in casalogs/: {len(log_files)}")
        for log_file in sorted(log_files)[-5:]:  # Show last 5 files
            print(f"  - {log_file.name}")
    else:
        print("\n❌ casalogs directory does not exist")

if __name__ == "__main__":
    test_casa_logging()

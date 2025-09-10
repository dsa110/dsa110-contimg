#!/usr/bin/env python3
"""
Fix CASA data update lock issue.
"""

import os
import shutil
from pathlib import Path

def fix_casa_lock():
    """Fix CASA data update lock issue."""
    casa_data_dir = Path.home() / ".casa" / "data"
    lock_file = casa_data_dir / "data_update.lock"
    
    print(f"CASA data directory: {casa_data_dir}")
    print(f"Lock file: {lock_file}")
    
    if lock_file.exists():
        print("✓ CASA lock file exists, removing it...")
        try:
            lock_file.unlink()
            print("✓ Lock file removed successfully")
        except Exception as e:
            print(f"✗ Failed to remove lock file: {e}")
            return False
    else:
        print("✓ No lock file found")
    
    # Check if CASA data directory is accessible
    if not casa_data_dir.exists():
        print(f"✓ Creating CASA data directory: {casa_data_dir}")
        casa_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Test CASA access
    try:
        from casatools import measures
        print("✓ CASA tools can be imported")
        
        # Try to create a measures object
        me = measures()
        print("✓ CASA measures object created successfully")
        me.done()
        
    except Exception as e:
        print(f"✗ CASA tools test failed: {e}")
        return False
    
    print("✓ CASA lock issue resolved")
    return True

if __name__ == "__main__":
    fix_casa_lock()

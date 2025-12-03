#!/opt/miniforge/envs/casa6/bin/python
"""
Test script to verify Python environment and CASA availability.

This script checks:
1. Which Python executable is being used
2. Python version
3. Whether CASA tools are available
4. Whether required scientific packages are available
"""

import os
import sys


def main():
    print("=" * 60)
    print("Python Environment Test")
    print("=" * 60)
    
    # Check Python executable
    python_exe = sys.executable
    print(f"\nPython executable: {python_exe}")
    
    # Check Python version
    python_version = sys.version
    print(f"Python version: {python_version.split()[0]}")
    
    # Expected casa6 path
    expected_casa6 = "/opt/miniforge/envs/casa6/bin/python"
    if python_exe == expected_casa6:
        print(f":check: Using casa6 environment (CORRECT)")
    else:
        print(f":cross: NOT using casa6 environment (WRONG)")
        print(f"  Expected: {expected_casa6}")
        print(f"  Actual:   {python_exe}")
    
    # Check CASA availability
    print("\n" + "-" * 60)
    print("Checking CASA availability...")
    try:

# --- CASA log directory setup ---
# Ensure CASA logs go to centralized directory, not CWD
import os as _os
try:
    from pathlib import Path as _Path
    _REPO_ROOT = _Path(__file__).resolve().parents[3]
    _sys_path_entry = str(_REPO_ROOT / 'backend' / 'src')
    import sys as _sys
    if _sys_path_entry not in _sys.path:
        _sys.path.insert(0, _sys_path_entry)
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    _os.makedirs(str(_casa_log_dir), exist_ok=True)
    _os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort - CASA logs may go to CWD
# --- End CASA log directory setup ---

        import casatools
        print(":check: casatools imported successfully")
    except ImportError as e:
        print(f":cross: casatools import failed: {e}")
    
    try:
        import casatasks
        print(":check: casatasks imported successfully")
    except ImportError as e:
        print(f":cross: casatasks import failed: {e}")
    
    # Check other scientific packages
    print("\n" + "-" * 60)
    print("Checking scientific packages...")
    
    packages = ['astropy', 'pyuvdata', 'numpy']
    for pkg in packages:
        try:
            mod = __import__(pkg)
            version = getattr(mod, '__version__', 'unknown')
            print(f":check: {pkg} imported successfully (version: {version})")
        except ImportError as e:
            print(f":cross: {pkg} import failed: {e}")
    
    print("\n" + "=" * 60)
    
    # Final verdict
    if python_exe == expected_casa6:
        print("RESULT: :check: Test PASSED - Using correct casa6 environment")
        return 0
    else:
        print("RESULT: :cross: Test FAILED - Not using casa6 environment")
        return 1

if __name__ == "__main__":
    sys.exit(main())


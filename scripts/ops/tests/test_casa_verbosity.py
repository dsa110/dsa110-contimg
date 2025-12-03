#!/opt/miniforge/envs/casa6/bin/python
"""
Test CASA verbosity settings to see if we can get bandpass to print all channels.
"""

import os
import sys

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

# Test different CASA logging configurations
print("Testing CASA verbosity options...")

try:
    # Try to import and configure CASA logger
    from casatasks import casalog
    
    print("\n1. Current CASA logger settings:")
    print(f"   Log file: {casalog.logfile()}")
    print(f"   Origin: {casalog.origin()}")
    
    # Try setting log level to DEBUG or INFO
    print("\n2. Attempting to set CASA logger to INFO level...")
    try:
        casalog.setlogfile("")  # Console output
        casalog.setlogfile("casa_test.log")  # Also write to file
        print("   :check: CASA logger configured")
    except Exception as e:
        print(f"   :cross: Failed to configure logger: {e}")
    
    # Check if there's a verbosity parameter
    print("\n3. Checking for bandpass verbosity parameter...")
    import inspect

    from casatasks import bandpass
    sig = inspect.signature(bandpass)
    params = list(sig.parameters.keys())
    
    verbose_params = [p for p in params if 'verbose' in p.lower() or 'log' in p.lower() or 'verbosity' in p.lower()]
    print(f"   Parameters with 'verbose'/'log'/'verbosity': {verbose_params}")
    
    print("\n4. All bandpass parameters:")
    print(f"   {params}")
    
except ImportError as e:
    print(f"ERROR: Could not import CASA: {e}")
    print("   Activate casa6 environment first.")
    sys.exit(1)

# Check environment variables
print("\n5. CASA-related environment variables:")
casa_env_vars = [k for k in os.environ.keys() if 'CASA' in k.upper() or 'LOG' in k.upper()]
for var in casa_env_vars:
    print(f"   {var} = {os.environ[var]}")

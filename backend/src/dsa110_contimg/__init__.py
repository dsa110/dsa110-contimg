# backend/src/dsa110_contimg/__init__.py

"""
This file initializes the dsa110_contimg package.

DSA-110 Continuum Imaging Pipeline for radio astronomy data processing.

Database conventions:
- All databases MUST be SQLite (.sqlite3)
- Catalog databases MUST be in state/catalogs/
"""

# =============================================================================
# CASA Log Directory Setup (MUST be first - before any CASA imports)
# =============================================================================
# CASA writes log files (casa-YYYYMMDD-HHMMSS.log) to the current working
# directory when any CASA module is first imported. We change CWD to the
# dedicated logs directory BEFORE any CASA imports can happen.
#
# This is done here (in package __init__.py) to ensure it happens before
# any submodule that might import casacore/casatools/casatasks.
import os as _os
from pathlib import Path as _Path

_CASA_LOG_DIR = _Path("/data/dsa110-contimg/state/logs/casa")
try:
    _CASA_LOG_DIR.mkdir(parents=True, exist_ok=True)
    _os.chdir(_CASA_LOG_DIR)
except (OSError, PermissionError):
    pass  # Best effort - CASA logs may go to CWD
# =============================================================================

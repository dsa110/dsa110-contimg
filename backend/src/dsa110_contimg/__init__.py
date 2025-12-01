# backend/src/dsa110_contimg/__init__.py

"""
This file initializes the dsa110_contimg package.

DSA-110 Continuum Imaging Pipeline for radio astronomy data processing.

IMPORTANT: This package enforces strict path rules:
- Access to .local/archive/ is FORBIDDEN
- All databases MUST be SQLite (.sqlite3)
- Catalog databases MUST be in state/catalogs/

These rules ensure reproducibility and prevent use of deprecated code.
"""

# Import path enforcement at package load time
from .utils.path_enforcement import check_environment as _check_env

# Run environment check on import (warns about suspicious configs)
_check_env()

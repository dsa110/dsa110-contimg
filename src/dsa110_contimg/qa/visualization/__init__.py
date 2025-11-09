"""
QA Visualization Framework

Provides RadioPadre-like functionality for interactive QA visualization:
- FITS file viewing with JS9
- CASA table browsing
- Directory browsing and file discovery
- Notebook generation

This module provides an in-house implementation of RadioPadre-like functionality,
designed to be compatible with our architecture, Python version, and dependencies.
"""

# Core classes will be imported here as they are implemented
# For now, we'll add imports incrementally

__version__ = "0.1.0"

# Import implemented modules
from .filelist import FileList
from .datadir import DataDir, ls
from .render import (
    render_table,
    render_status_message,
    render_error,
    render_preamble,
    rich_string,
    display_html,
)
from .fitsfile import FITSFile
from .casatable import CasaTable
from .js9 import init_js9, is_js9_available

# Placeholder imports - will be uncommented as modules are implemented
# from .notebook import generate_qa_notebook

__all__ = [
    'FITSFile',
    'CasaTable',
    'FileList',
    'DataDir',
    'ls',
    'render_table',
    'render_status_message',
    'render_error',
    'render_preamble',
    'rich_string',
    'display_html',
    'init_js9',
    'is_js9_available',
    # 'generate_qa_notebook',
]

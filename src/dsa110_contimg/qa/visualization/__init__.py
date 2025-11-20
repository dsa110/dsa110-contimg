"""
QA Visualization Framework

Provides RadioPadre-like functionality for interactive QA visualization:
- FITS file viewing with JS9
- CASA table browsing
- Directory browsing and file discovery
- Notebook generation
- Image file handling with thumbnails
- Text file viewing with grep/head/tail
- Advanced table rendering
- HTML/PDF file support
- Settings management
- Layouts and navigation

This module provides an in-house implementation of RadioPadre-like functionality,
designed to be compatible with our architecture, Python version, and dependencies.
"""

from .notebook import generate_qa_notebook, generate_fits_viewer_notebook
from .integration import (
    browse_qa_outputs,
    display_qa_summary,
    generate_qa_notebook_from_result,
)
from .js9 import init_js9, is_js9_available
from .thumbnail import (
    get_cache_dir,
    get_cache_file,
    make_thumbnail,
    render_thumbnail_html,
)
from .executor import executor, ncpu, shutdown_executor
from .layouts import (
    Title,
    Section as LayoutSection,
    add_section,
    render_bookmarks_bar,
)
from .settings_manager import (
    QAVisualizationSettingsManager,
    Section,
    SettingsManager,
    get_settings,
    settings,
)
from .table import Table, tabulate
from .render import (
    RenderingProxy,
    display_html,
    htmlize,
    render_error,
    render_preamble,
    render_refresh_button,
    render_status_message,
    render_table,
    render_titled_content,
    rich_string,
)
from .pdffile import PDFFile
from .htmlfile import HTMLFile, URL

__version__ = "0.2.0"

# Core file types
from .casatable import CasaTable
from .datadir import DataDir, ls
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .textfile import TextFile, NumberedLineList

# Rendering utilities

# Advanced features

# JS9 integration

# Notebook generation

__all__ = [
    # File types
    "FITSFile",
    "CasaTable",
    "FileList",
    "DataDir",
    "ImageFile",
    "TextFile",
    "NumberedLineList",
    "HTMLFile",
    "URL",
    "PDFFile",
    # Directory utilities
    "ls",
    # Rendering utilities
    "render_table",
    "render_status_message",
    "render_error",
    "render_preamble",
    "render_refresh_button",
    "render_titled_content",
    "rich_string",
    "htmlize",
    "display_html",
    "RenderingProxy",
    # Advanced features
    "Table",
    "tabulate",
    "settings",
    "get_settings",
    "SettingsManager",
    "Section",
    "QAVisualizationSettingsManager",
    "Title",
    "LayoutSection",
    "add_section",
    "render_bookmarks_bar",
    "executor",
    "ncpu",
    "shutdown_executor",
    # Thumbnail utilities
    "get_cache_dir",
    "get_cache_file",
    "make_thumbnail",
    "render_thumbnail_html",
    # JS9
    "init_js9",
    "is_js9_available",
    # Notebook generation
    "generate_qa_notebook",
    "generate_fits_viewer_notebook",
    "browse_qa_outputs",
    "display_qa_summary",
    "generate_qa_notebook_from_result",
]

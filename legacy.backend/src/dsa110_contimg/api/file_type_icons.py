"""File type icon generation service.

Generates SVG icons for different file types (folders, FITS, MS, images, etc.)
to replace text-based thumbnails with visual icons.
"""

import base64
from pathlib import Path
from typing import Optional


def get_file_type_icon_svg(file_path: str, size: int = 64) -> str:
    """Get SVG icon for a file based on its type.

    Args:
        file_path: Path to the file
        size: Icon size in pixels (default: 64)

    Returns:
        SVG string representing the file type icon
    """
    path = Path(file_path)

    if path.is_dir():
        return _folder_icon_svg(size)

    suffix = path.suffix.lower()

    # Map file extensions to icon generators
    icon_map = {
        ".fits": _fits_icon_svg,
        ".ms": _ms_icon_svg,
        ".png": _image_icon_svg,
        ".jpg": _image_icon_svg,
        ".jpeg": _image_icon_svg,
        ".gif": _image_icon_svg,
        ".svg": _image_icon_svg,
        ".h5": _hdf5_icon_svg,
        ".hdf5": _hdf5_icon_svg,
        ".uvh5": _hdf5_icon_svg,
        ".txt": _text_icon_svg,
        ".log": _text_icon_svg,
        ".md": _text_icon_svg,
        ".json": _code_icon_svg,
        ".yaml": _code_icon_svg,
        ".yml": _code_icon_svg,
        ".py": _code_icon_svg,
        ".sh": _code_icon_svg,
    }

    # Get appropriate icon generator
    icon_generator = icon_map.get(suffix, _generic_file_icon_svg)
    return icon_generator(size)


def _folder_icon_svg(size: int = 64) -> str:
    """Generate folder icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="16" width="48" height="40" rx="4" fill="#FFB84D" stroke="#CC8800" stroke-width="2"/>
  <path d="M 8 24 L 28 24 L 32 16 L 56 16 L 56 24" fill="#FFA500" stroke="#CC8800" stroke-width="2"/>
  <text x="32" y="44" font-family="Arial, sans-serif" font-size="24" fill="#FFF" text-anchor="middle">:file_folder:</text>
</svg>"""


def _fits_icon_svg(size: int = 64) -> str:
    """Generate FITS file icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect x="12" y="8" width="40" height="48" rx="3" fill="#4A90E2" stroke="#2E5C8A" stroke-width="2"/>
  <rect x="16" y="12" width="32" height="16" fill="#2E5C8A"/>
  <text x="32" y="42" font-family="monospace" font-size="10" fill="#FFF" text-anchor="middle" font-weight="bold">FITS</text>
  <circle cx="24" cy="20" r="2" fill="#FFD700"/>
  <circle cx="32" cy="20" r="3" fill="#FFD700"/>
  <circle cx="40" cy="20" r="2" fill="#FFF"/>
</svg>"""


def _ms_icon_svg(size: int = 64) -> str:
    """Generate Measurement Set (MS) icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect x="12" y="8" width="40" height="48" rx="3" fill="#8B4789" stroke="#5C2E5B" stroke-width="2"/>
  <rect x="16" y="14" width="32" height="8" fill="#5C2E5B"/>
  <rect x="16" y="26" width="32" height="2" fill="#A567A3"/>
  <rect x="16" y="32" width="32" height="2" fill="#A567A3"/>
  <rect x="16" y="38" width="32" height="2" fill="#A567A3"/>
  <text x="32" y="50" font-family="monospace" font-size="10" fill="#FFF" text-anchor="middle" font-weight="bold">MS</text>
</svg>"""


def _image_icon_svg(size: int = 64) -> str:
    """Generate image file icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect x="12" y="8" width="40" height="48" rx="3" fill="#4CAF50" stroke="#2E7D32" stroke-width="2"/>
  <circle cx="24" cy="24" r="4" fill="#FFD700"/>
  <path d="M 16 48 L 28 32 L 36 40 L 48 24 L 48 48 Z" fill="#81C784"/>
  <rect x="16" y="48" width="32" height="4" fill="#2E7D32"/>
</svg>"""


def _hdf5_icon_svg(size: int = 64) -> str:
    """Generate HDF5/UVH5 file icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect x="12" y="8" width="40" height="48" rx="3" fill="#E67E22" stroke="#A04000" stroke-width="2"/>
  <rect x="16" y="16" width="14" height="12" fill="#A04000" opacity="0.5"/>
  <rect x="34" y="16" width="14" height="12" fill="#A04000" opacity="0.5"/>
  <rect x="16" y="32" width="14" height="12" fill="#A04000" opacity="0.5"/>
  <rect x="34" y="32" width="14" height="12" fill="#A04000" opacity="0.5"/>
  <text x="32" y="52" font-family="monospace" font-size="9" fill="#FFF" text-anchor="middle" font-weight="bold">HDF5</text>
</svg>"""


def _text_icon_svg(size: int = 64) -> str:
    """Generate text file icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect x="12" y="8" width="40" height="48" rx="3" fill="#ECEFF1" stroke="#90A4AE" stroke-width="2"/>
  <line x1="18" y1="18" x2="46" y2="18" stroke="#546E7A" stroke-width="2"/>
  <line x1="18" y1="26" x2="46" y2="26" stroke="#546E7A" stroke-width="2"/>
  <line x1="18" y1="34" x2="46" y2="34" stroke="#546E7A" stroke-width="2"/>
  <line x1="18" y1="42" x2="38" y2="42" stroke="#546E7A" stroke-width="2"/>
</svg>"""


def _code_icon_svg(size: int = 64) -> str:
    """Generate code file icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect x="12" y="8" width="40" height="48" rx="3" fill="#263238" stroke="#000" stroke-width="2"/>
  <text x="18" y="22" font-family="monospace" font-size="8" fill="#00FF00">#!/bin</text>
  <text x="18" y="32" font-family="monospace" font-size="8" fill="#FFF">def fn</text>
  <text x="18" y="42" font-family="monospace" font-size="8" fill="#FFF">  ret</text>
</svg>"""


def _generic_file_icon_svg(size: int = 64) -> str:
    """Generate generic file icon SVG."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <path d="M 12 8 L 12 56 L 52 56 L 52 20 L 40 8 Z" fill="#90A4AE" stroke="#546E7A" stroke-width="2"/>
  <path d="M 40 8 L 40 20 L 52 20" fill="#CFD8DC" stroke="#546E7A" stroke-width="2"/>
  <line x1="20" y1="32" x2="44" y2="32" stroke="#FFF" stroke-width="2"/>
  <line x1="20" y1="40" x2="44" y2="40" stroke="#FFF" stroke-width="2"/>
  <line x1="20" y1="48" x2="36" y2="48" stroke="#FFF" stroke-width="2"/>
</svg>"""


def get_file_type_icon_data_uri(file_path: str, size: int = 64) -> str:
    """Get data URI for file type icon.

    Args:
        file_path: Path to the file
        size: Icon size in pixels (default: 64)

    Returns:
        Data URI string (data:image/svg+xml;base64,...) for embedding in HTML
    """
    svg = get_file_type_icon_svg(file_path, size)
    svg_base64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{svg_base64}"


def get_file_type_icon_html(file_path: str, size: int = 64, alt: Optional[str] = None) -> str:
    """Get HTML img tag for file type icon.

    Args:
        file_path: Path to the file
        size: Icon size in pixels (default: 64)
        alt: Alt text for the image (default: filename)

    Returns:
        HTML img tag string
    """
    path = Path(file_path)
    if alt is None:
        alt = path.name

    data_uri = get_file_type_icon_data_uri(file_path, size)
    return f'<img src="{data_uri}" alt="{alt}" width="{size}" height="{size}" style="display: inline-block; vertical-align: middle;" />'

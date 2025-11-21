"""
Thumbnail generation and caching utilities for QA visualization.

Provides thumbnail generation with caching support, similar to RadioPadre's
thumbnail system.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None


def get_cache_dir(file_path: str, subdir: Optional[str] = None) -> Tuple[str, str]:
    """
    Get cache directory for a file.

    Creates a `.radiopadre` cache directory in the same directory as the file.

    Args:
        file_path: Path to the file
        subdir: Optional subdirectory name (e.g., "thumbs")

    Returns:
        Tuple of (cache_dir_path, cache_dir_url)
        Note: URL is same as path for now (can be enhanced for web serving)
    """
    file_path_obj = Path(file_path).resolve()
    base_dir = file_path_obj.parent

    # Create .radiopadre cache directory
    cache_dir = base_dir / ".radiopadre"
    if subdir:
        cache_dir = cache_dir / subdir

    # Create directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    return str(cache_dir), str(cache_dir)


def get_cache_file(
    file_path: str, cache_type: str, extension: str, keydict: Optional[dict] = None
) -> Tuple[str, str, bool]:
    """
    Get cache file path for a file.

    Args:
        file_path: Path to the source file
        cache_type: Type of cache (e.g., "thumbs", "html-render")
        extension: File extension for cache file (e.g., "png")
        keydict: Optional dictionary of cache parameters (for versioning)

    Returns:
        Tuple of (cache_file_path, cache_file_url, needs_update)
        needs_update is True if cache file doesn't exist or is older than source
    """
    cache_dir, cache_url_base = get_cache_dir(file_path, cache_type)

    # Generate cache filename
    file_path_obj = Path(file_path)
    base_name = file_path_obj.stem

    # Include keydict in filename hash if provided
    if keydict:
        key_str = "_".join(f"{k}={v}" for k, v in sorted(keydict.items()))
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:8]
        cache_name = f"{base_name}_{key_hash}{extension}"
    else:
        cache_name = f"{base_name}{extension}"

    cache_file = os.path.join(cache_dir, cache_name)
    cache_url = os.path.join(cache_url_base, cache_name)

    # Check if cache needs update
    needs_update = True
    if os.path.exists(cache_file):
        cache_mtime = os.path.getmtime(cache_file)
        source_mtime = os.path.getmtime(file_path)
        needs_update = cache_mtime < source_mtime

    return cache_file, cache_url, needs_update


def make_thumbnail(
    image_path: str, width: int = 200, height: Optional[int] = None
) -> Optional[Tuple[str, str]]:
    """
    Generate a thumbnail for an image file.

    Args:
        image_path: Path to the source image
        width: Thumbnail width in pixels
        height: Optional thumbnail height (auto-calculated if None)

    Returns:
        Tuple of (thumbnail_path, thumbnail_url) or None if generation failed
    """
    if not HAS_PIL:
        return None

    if not os.path.exists(image_path):
        return None

    try:
        # Get cache file
        cache_file, cache_url, needs_update = get_cache_file(
            image_path, "thumbs", ".png", keydict={"width": width, "height": height}
        )

        if not needs_update and os.path.exists(cache_file):
            return cache_file, cache_url

        # Generate thumbnail
        img = Image.open(image_path)

        # Calculate height if not provided
        if height is None:
            aspect_ratio = img.height / img.width
            height = int(width * aspect_ratio)

        # Create thumbnail
        img.thumbnail((width, height), Image.LANCZOS)

        # Save thumbnail
        img.save(cache_file, "PNG")

        return cache_file, cache_url

    except Exception:
        # Silently fail - return None
        return None


def is_svg_file(file_path: str) -> bool:
    """
    Check if a file is an SVG file.

    Args:
        file_path: Path to the file

    Returns:
        True if file is SVG
    """
    return os.path.splitext(file_path)[1].lower() == ".svg"


def render_thumbnail_html(
    image_path: str,
    url: Optional[str] = None,
    width: Optional[int] = None,
    mtime: Optional[float] = None,
) -> str:
    """
    Render HTML for a thumbnail image.

    Args:
        image_path: Path to the source image
        url: Optional URL for the full image (defaults to image_path)
        width: Optional display width in pixels
        mtime: Optional modification time for cache busting

    Returns:
        HTML string for thumbnail
    """
    if url is None:
        url = image_path

    # Add mtime to URL for cache busting
    if mtime is not None:
        url += f"?mtime={int(mtime)}"

    # Try to generate thumbnail
    if is_svg_file(image_path):
        # SVG files don't need thumbnails
        thumb_url = url
    else:
        thumb_result = make_thumbnail(image_path, width=width or 200)
        if thumb_result:
            thumb_path, thumb_url = thumb_result
        else:
            thumb_url = url

    width_attr = f' width="{width}"' if width else ""
    return (
        f'<a href="{url}" target="_blank"><img src="{thumb_url}"{width_attr} alt="thumbnail"></a>'
    )

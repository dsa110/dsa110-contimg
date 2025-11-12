"""
Image file handling for QA visualization framework.

Provides ImageFile class for viewing image files (PNG, JPEG, etc.) with
thumbnail generation, similar to RadioPadre's ImageFile functionality.
"""

import os
from typing import Optional

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    from IPython.display import HTML, Image as IPythonImage, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    HTML = str
    IPythonImage = None

    def display(*args, **kwargs):
        pass


from .file import FileBase
from .render import render_error, render_url
from .thumbnail import is_svg_file, make_thumbnail, render_thumbnail_html


class ImageFile(FileBase):
    """
    Image file handler with thumbnail generation.

    Supports PNG, JPEG, GIF, and SVG files with automatic thumbnail
    generation and caching.
    """

    def __init__(self, *args, **kwargs):
        """Initialize an image file handler."""
        self._image_info = None
        super().__init__(*args, **kwargs)

    def _scan_impl(self) -> None:
        """Extract image metadata."""
        if not HAS_PIL:
            self.description = "PIL not available"
            return

        if not self.exists:
            self.description = "File not found"
            return

        try:
            if is_svg_file(self.fullpath):
                self.description = "SVG"
                self._image_info = {"format": "SVG", "size": None, "mode": None}
            else:
                img = Image.open(self.fullpath)
                self._image_info = {
                    "format": img.format,
                    "size": img.size,
                    "mode": img.mode,
                }
                size_str = f"{img.format} {img.width}×{img.height}"
                self.description = size_str
        except Exception as e:
            self.description = f"Error: {e}"
            self._image_info = None

    @property
    def image_info(self) -> Optional[dict]:
        """Get image metadata."""
        if self._image_info is None:
            self._scan_impl()
        return self._image_info

    def render_thumb(self, width: Optional[int] = None, **kwargs) -> str:
        """
        Render a thumbnail for this image.

        Args:
            width: Optional thumbnail width (default: 200)
            **kwargs: Additional rendering options

        Returns:
            HTML string for thumbnail
        """
        if width is None:
            width = 200

        url = render_url(self.fullpath)
        mtime = self.mtime

        return render_thumbnail_html(self.fullpath, url=url, width=width, mtime=mtime)

    def show(self, width: Optional[int] = None) -> None:
        """
        Display the image.

        Args:
            width: Optional display width in pixels
        """
        self.mark_shown()

        if not self.exists:
            if HAS_IPYTHON:
                display(HTML(render_error(f"Image file not found: {self.fullpath}")))
            return

        if not HAS_IPYTHON or IPythonImage is None:
            return

        try:
            display_width = width * 100 if width else None
            display(IPythonImage(self.fullpath, width=display_width))
        except Exception as e:
            if HAS_IPYTHON:
                display(HTML(render_error(f"Error displaying image: {e}")))

    def _repr_html_(self) -> str:
        """HTML representation for Jupyter."""
        return self.render_thumb()

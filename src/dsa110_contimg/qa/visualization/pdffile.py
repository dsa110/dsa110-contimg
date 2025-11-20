"""
PDF file handling for QA visualization framework.

Provides PDFFile class for viewing PDF files with thumbnail generation,
similar to RadioPadre's PDFFile.
"""

import shlex
import subprocess
from typing import Optional

try:
    from IPython.display import HTML, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    HTML = str

    def display(*args, **kwargs):
        pass


from .file import FileBase
from .render import render_error


def _find_ghostscript() -> Optional[str]:
    """Find Ghostscript executable."""
    for cmd in ["gs", "gswin64c", "gswin32c"]:
        try:
            result = subprocess.run(["which", cmd], capture_output=True, check=True, text=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None


class PDFFile(FileBase):
    """
    PDF file handler with thumbnail generation.

    Supports PDF viewing with first-page thumbnail generation using Ghostscript.
    """

    def __init__(self, *args, **kwargs):
        """Initialize a PDF file handler."""
        super().__init__(*args, **kwargs)

    def _render_thumb_impl(
        self, npix: Optional[int] = None, refresh: bool = False, **kwargs
    ) -> str:
        """
        Render thumbnail for PDF file.

        Args:
            npix: Thumbnail size in pixels
            refresh: Force refresh thumbnail
            **kwargs: Additional options

        Returns:
            HTML string for thumbnail
        """
        npix = npix or 800

        thumbnail, thumbnail_url, needs_update = self._get_cache_file("pdf-render", "png")

        if needs_update or refresh:
            gs = _find_ghostscript()
            if not gs:
                return render_error("Ghostscript not found (required for PDF thumbnails)")

            cmd = (
                f"{shlex.quote(gs)} -sDEVICE=png16m "
                f"-sOutputFile={shlex.quote(thumbnail)} "
                f"-dLastPage=1 -r300 -dDownScaleFactor=4 -dBATCH -dNOPAUSE "
                f"{shlex.quote(self.fullpath)}"
            )

            try:
                subprocess.run(cmd, check=True, shell=True, capture_output=True, timeout=30)
            except subprocess.CalledProcessError as e:
                return render_error(f"Ghostscript error (code {e.returncode})")
            except subprocess.TimeoutExpired:
                return render_error("PDF rendering timeout")

        # Use ImageFile to render thumbnail
        from .imagefile import ImageFile

        img_file = ImageFile(thumbnail)
        return img_file.render_thumb(width=npix // 4)

    def render_html(self, **kwargs) -> str:
        """Render PDF file as HTML."""
        return self._render_thumb_impl(**kwargs)

    def show(self, **kwargs) -> None:
        """Display PDF file."""
        self.mark_shown()
        html = self.render_html(**kwargs)
        if HAS_IPYTHON:
            display(HTML(html))

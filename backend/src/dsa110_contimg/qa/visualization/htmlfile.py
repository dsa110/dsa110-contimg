"""
HTML file handling for QA visualization framework.

Provides HTMLFile class for viewing HTML files with iframe embedding
and thumbnail generation, similar to RadioPadre's HTMLFile.
"""

import os
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
from .render import render_error, render_preamble, render_titled_content, render_url
from .settings_manager import settings


def _find_chromium() -> Optional[str]:
    """Find Chromium executable."""
    for cmd in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        try:
            result = subprocess.run(["which", cmd], capture_output=True, check=True, text=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None


def _render_html_thumbnail(
    url_or_path: str, img_repr_path: str, width: int, height: int, timeout: int = 200
) -> None:
    """
    Render an HTML document to a PNG thumbnail.

    Args:
        url_or_path: URL or file path to render
        img_repr_path: Output PNG path
        width: Canvas width
        height: Canvas height
        timeout: Timeout in seconds
    """
    chromium = _find_chromium()
    if not chromium:
        raise RuntimeError("Chromium/Chrome not found for HTML rendering")

    # Use Chromium headless mode
    cmd = [
        chromium,
        "--headless",
        "--disable-gpu",
        f"--screenshot={img_repr_path}",
        f"--window-size={width},{height}",
        url_or_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Chromium error (code {e.returncode}): {e.stderr.decode()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"HTML rendering timeout after {timeout}s")


class HTMLFile(FileBase):
    """
    HTML file handler with iframe embedding and thumbnail generation.

    Supports HTML file viewing in iframes and thumbnail generation using headless browsers.
    """

    def __init__(self, *args, **kwargs):
        """Initialize an HTML file handler."""
        super().__init__(*args, **kwargs)

    def render_html(
        self,
        width: str = "99%",
        height: Optional[int] = None,
        title: Optional[str] = None,
        collapsed: Optional[bool] = None,
        **kwargs,
    ) -> str:
        """
        Render HTML file in an iframe.

        Args:
            width: Iframe width
            height: Iframe height
            title: Optional title
            collapsed: If True, start collapsed
            **kwargs: Additional options

        Returns:
            HTML string
        """
        if height is None:
            height = settings.html.height
        width = width or settings.display.cell_width
        height = height or settings.display.window_height

        url = render_url(self.fullpath)
        title_html = f"<h3>{title or self.basename}</h3>" if title or self.basename else ""
        content_html = f'<iframe width="{width}" height="{height}" src="{url}"></iframe>'

        if collapsed is None:
            collapsed = settings.gen.collapsible

        return render_preamble() + render_titled_content(
            title_html=title_html, content_html=content_html, collapsed=collapsed
        )

    def _render_thumb_impl(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        refresh: bool = False,
        **kwargs,
    ) -> str:
        """
        Render thumbnail for HTML file.

        Args:
            width: Thumbnail width
            height: Thumbnail height
            refresh: Force refresh thumbnail
            **kwargs: Additional options

        Returns:
            HTML string for thumbnail
        """
        width = width or settings.html.width
        height = height or settings.html.height

        img_representation, thumbnail_url, needs_update = self._get_cache_file(
            "html-render", "png", keydict={"width": width, "height": height}
        )

        if needs_update or refresh:
            try:
                url = "file://" + os.path.abspath(self.fullpath)
                _render_html_thumbnail(url, img_representation, width, height, timeout=200)
            except Exception as e:
                return render_error(str(e))

        # Use ImageFile to render thumbnail
        from .imagefile import ImageFile

        img_file = ImageFile(img_representation)
        return img_file.render_thumb(width=width // 4)  # Smaller thumbnail

    def show(self, **kwargs) -> None:
        """Display HTML file."""
        self.mark_shown()
        html = self.render_html(**kwargs)
        if HAS_IPYTHON:
            display(HTML(html))


class URL(FileBase):
    """
    URL handler for remote HTML content.

    Similar to HTMLFile but for remote URLs.
    """

    def __init__(self, url: str, title: Optional[str] = None):
        """
        Initialize a URL handler.

        Args:
            url: URL to display
            title: Optional title
        """
        super().__init__(url, title=title or url)
        self.url = url

    def render_html(
        self,
        width: str = "99%",
        height: Optional[int] = None,
        title: Optional[str] = None,
        collapsed: Optional[bool] = None,
        **kwargs,
    ) -> str:
        """Render URL in an iframe."""
        if height is None:
            height = settings.html.height
        width = width or settings.display.cell_width
        height = height or settings.display.window_height

        title_html = f"<h3>{title or self.url}</h3>" if title or self.url else ""
        content_html = f'<iframe width="{width}" height="{height}" src="{self.url}"></iframe>'

        if collapsed is None:
            collapsed = settings.gen.collapsible

        return render_preamble() + render_titled_content(
            title_html=title_html, content_html=content_html, collapsed=collapsed
        )

    def show(self, **kwargs) -> None:
        """Display URL."""
        self.mark_shown()
        html = self.render_html(**kwargs)
        if HAS_IPYTHON:
            display(HTML(html))

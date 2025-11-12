"""
FITS file handling for QA visualization framework.

Provides FITSFile class for viewing FITS files with JS9 integration,
similar to RadioPadre's FITSFile functionality.
"""

import os
import sys
import traceback
import uuid
from typing import Dict, List, Optional, Tuple

try:
    from IPython.display import HTML, Javascript, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False

    def display(*args, **kwargs):
        pass

    HTML = str
    Javascript = str

try:
    from astropy.io import fits

    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False
    fits = None

from .file import FileBase
from .js9 import JS9_ERROR, get_js9_init_html, init_js9
from .render import render_error, render_table, rich_string


class FITSFile(FileBase):
    """
    FITS file handler with JS9 integration for browser-based viewing.

    Provides FITS header parsing, summary information, and JS9 viewer integration.
    """

    FITSAxisLabels = {
        "STOKES": ["I", "Q", "U", "V", "YX", "XY", "YY", "XX", "LR", "RL", "LL", "RR"],
        "COMPLEX": ["real", "imag", "weight"],
    }

    def __init__(self, *args, **kwargs):
        """Initialize a FITS file handler."""
        self._header = None
        self._hdrobj = None
        self._shape = None
        self._summary_data = None
        self._js9_id = None
        super().__init__(*args, **kwargs)

    @property
    def fitsobj(self):
        """Open and return FITS file object."""
        if not HAS_ASTROPY:
            raise ImportError("astropy.io.fits is required for FITS file handling")
        return fits.open(self.fullpath)

    @property
    def hdrobj(self):
        """Get FITS header object."""
        if not HAS_ASTROPY:
            raise ImportError("astropy.io.fits is required for FITS file handling")
        if self._hdrobj is None or self.is_updated():
            with self.fitsobj as hdul:
                self._hdrobj = hdul[0].header.copy()
            self.update_mtime()
        return self._hdrobj

    @property
    def header(self):
        """Get FITS header as a formatted string."""
        if self._header is None or self.is_updated():
            try:
                hdr = self.hdrobj
                lines = [x.strip() for x in repr(hdr).split("\n")]
                self._header = "\n".join(lines)
            except Exception as e:
                self._header = f"Error reading header: {e}"
        return self._header

    @property
    def shape(self) -> Optional[List[int]]:
        """Get image dimensions."""
        if self._shape is None:
            try:
                hdr = self.hdrobj
                naxis = hdr.get("NAXIS", 0)
                if naxis > 0:
                    self._shape = [hdr.get(f"NAXIS{i}", 0) for i in range(1, naxis + 1)]
                else:
                    self._shape = []
            except Exception:
                self._shape = None
        return self._shape

    def _get_summary_items(self) -> Tuple[str, str, str, str, str]:
        """
        Get summary items for display.

        Returns:
            Tuple of (name, size, resolution, axes, modified_time)
        """
        name = self.basename
        size = resolution = axes = "?"
        mtime_str = "?"

        try:
            hdr = self.hdrobj
            naxis = hdr.get("NAXIS", 0)

            # Size
            if naxis > 0:
                dims = [str(hdr.get(f"NAXIS{i}", 0)) for i in range(1, naxis + 1)]
                size = "×".join(dims)
                if hdr.get("EXTEND", False):
                    size += "+EXT"
            else:
                size = "FITS EXT"

            # Axes
            if naxis > 0:
                axis_types = []
                for i in range(1, naxis + 1):
                    ctype = hdr.get(f"CTYPE{i}", "?")
                    axis_types.append(ctype.split("-")[0] if "-" in ctype else ctype)
                axes = ",".join(axis_types)
            else:
                axes = "?"

            # Resolution
            resolution_parts = []
            if naxis >= 2:
                delt1 = abs(hdr.get("CDELT1", 0))
                delt2 = abs(hdr.get("CDELT2", 0))
                if delt1 > 0 and delt2 > 0:
                    delts = [delt1, delt2]
                    if delt1 == delt2:
                        delts = [delt1]
                    for d in delts:
                        if d >= 1:
                            resolution_parts.append(f"{d:.2f}°")
                        elif d >= 1 / 60:
                            resolution_parts.append(f"{d * 60:.2f}'")
                        elif d >= 1 / 3600:
                            resolution_parts.append(f'{d * 3600:.2f}"')
                        else:
                            resolution_parts.append(f'{d * 3600:.2g}"')
            resolution = "×".join(resolution_parts) if resolution_parts else "?"

            # Modified time
            mtime = self.mtime
            if mtime:
                from datetime import datetime

                mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

        except Exception:
            traceback.print_exc()

        return (name, size, resolution, axes, mtime_str)

    def _setup_summary(self) -> None:
        """Setup summary information."""
        if self._summary_data is None:
            self._summary_data = [self._get_summary_items()]

    @property
    def summary(self) -> str:
        """Get summary string."""
        self._setup_summary()
        if self._summary_data:
            items = self._summary_data[0]
            return f"{items[0]}: {items[1]} ({items[2]}) [{items[3]}]"
        return self.basename

    def show(
        self,
        js9_id: Optional[str] = None,
        width: int = 600,
        height: int = 600,
        dual_window: bool = False,
        scale: str = "linear",
        colormap: str = "grey",
    ) -> None:
        """
        Display FITS file using JS9 viewer.

        Args:
            js9_id: Optional JS9 display ID (auto-generated if not provided)
            width: Display width in pixels
            height: Display height in pixels
            dual_window: If True, use dual-window JS9 display
            scale: Image scaling ("linear", "log", "sqrt", "squared", "histeq", "minmax")
            colormap: Color map name ("grey", "heat", "cool", "cubehelix", etc.)
        """
        self.mark_shown()

        if not HAS_ASTROPY:
            display(
                HTML(render_error("astropy.io.fits is required for FITS file viewing"))
            )
            return

        if not self.exists:
            display(HTML(render_error(f"FITS file not found: {self.fullpath}")))
            return

        # Initialize JS9 if needed
        if not init_js9():
            if JS9_ERROR:
                display(HTML(render_error(f"JS9 initialization failed: {JS9_ERROR}")))
            return

        # Generate JS9 ID if not provided
        if js9_id is None:
            self._js9_id = f"js9_{uuid.uuid4().hex[:8]}"
        else:
            self._js9_id = js9_id

        try:
            # Get summary
            self._setup_summary()
            summary_html = self._render_summary_html()

            # JS9 display HTML
            js9_html = self._render_js9_html(
                width=width,
                height=height,
                dual_window=dual_window,
                scale=scale,
                colormap=colormap,
            )

            # Combine and display
            full_html = summary_html + js9_html
            display(HTML(full_html))

        except Exception as e:
            error_msg = f"Error displaying FITS file: {e}\n{traceback.format_exc()}"
            display(HTML(render_error(error_msg, title="FITS Display Error")))

    def _render_summary_html(self) -> str:
        """Render summary information as HTML."""
        if not self._summary_data:
            return ""

        items = self._summary_data[0]
        data = [
            ("Name", items[0]),
            ("Size", items[1]),
            ("Resolution", items[2]),
            ("Axes", items[3]),
            ("Modified", items[4]),
        ]

        html = f'<div class="qa-fits-summary"><h3>{self.basename}</h3>'
        html += render_table(data, headers=["Property", "Value"], numbering=False)
        html += "</div>"
        return html

    def _render_js9_html(
        self,
        width: int = 600,
        height: int = 600,
        dual_window: bool = False,
        scale: str = "linear",
        colormap: str = "grey",
    ) -> str:
        """
        Render JS9 viewer HTML.

        Args:
            width: Display width in pixels
            height: Display height in pixels
            dual_window: If True, use dual-window JS9 display
            scale: Image scaling
            colormap: Color map name

        Returns:
            HTML string for JS9 viewer
        """
        js9_id = self._js9_id or f"js9_{uuid.uuid4().hex[:8]}"

        # Check if image is large (needs segmentation)
        shape = self.shape
        is_large = False
        max_slice_size = 2048  # Default max slice size

        if shape and len(shape) >= 2:
            # Check if either dimension exceeds max_slice_size
            if shape[0] > max_slice_size or shape[1] > max_slice_size:
                is_large = True

        # Note: JS9.Load() expects a URL, not a file path
        # For local files, we need to serve them or use a data URL
        # For now, we'll use the file path and let JS9 handle it
        # In a production setup, files should be served via HTTP

        if dual_window:
            # Dual window display
            html = f"""
            <div class="qa-js9-container" id="{js9_id}_container" style="margin: 10px 0;">
                <div style="display: flex; gap: 10px;">
                    <div id="{js9_id}_1" class="js9" style="width: {width}px; height: {height}px; border: 1px solid #ccc;"></div>
                    <div id="{js9_id}_2" class="js9" style="width: {width}px; height: {height}px; border: 1px solid #ccc;"></div>
                </div>
            </div>
            <script>
            (function() {{
                var js9Id1 = "{js9_id}_1";
                var js9Id2 = "{js9_id}_2";
                var fitsPath = "{self.fullpath}";
                
                function loadFITS() {{
                    if (typeof JS9 !== 'undefined') {{
                        // Load same file in both windows
                        JS9.Load(fitsPath, {{
                            display: js9Id1,
                            scale: "{scale}",
                            colormap: "{colormap}"
                        }});
                        JS9.Load(fitsPath, {{
                            display: js9Id2,
                            scale: "{scale}",
                            colormap: "{colormap}"
                        }});
                    }} else {{
                        setTimeout(loadFITS, 100);
                    }}
                }}
                
                loadFITS();
            }})();
            </script>
            """
        else:
            # Single window display
            html = f"""
            <div class="qa-js9-container" id="{js9_id}_container" style="margin: 10px 0;">
                <div id="{js9_id}" class="js9" style="width: {width}px; height: {height}px; border: 1px solid #ccc;"></div>
            </div>
            <script>
            (function() {{
                var js9Id = "{js9_id}";
                var fitsPath = "{self.fullpath}";
                
                function loadFITS() {{
                    if (typeof JS9 !== 'undefined') {{
                        var options = {{
                            display: js9Id,
                            scale: "{scale}",
                            colormap: "{colormap}"
                        }};
                        {"options.maxSliceSize = " + str(max_slice_size) + ";" if is_large else ""}
                        JS9.Load(fitsPath, options);
                    }} else {{
                        setTimeout(loadFITS, 100);
                    }}
                }}
                
                loadFITS();
            }})();
            </script>
            """
        return html

    def _repr_html_(self) -> str:
        """HTML representation for Jupyter."""
        self.show()
        return ""

    def __str__(self) -> str:
        """String representation."""
        return f"FITSFile({self.path})"

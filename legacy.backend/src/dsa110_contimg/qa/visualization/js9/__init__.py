"""
JS9 integration for QA visualization framework.

Provides JS9 initialization and helper functions for browser-based FITS viewing.
"""

import os
from pathlib import Path

try:
    from IPython.display import HTML, Javascript, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    HTML = str
    Javascript = str

    def display(*args, **kwargs):
        pass


# Path to JS9 static files
JS9_STATIC_DIR = Path(__file__).parent / "static" / "js9"

# JS9 initialization status
_js9_initialized = False
JS9_ERROR = None


def get_js9_static_path() -> Path:
    """Get path to JS9 static files directory."""
    return JS9_STATIC_DIR


def is_js9_available() -> bool:
    """Check if JS9 static files are available."""
    return JS9_STATIC_DIR.exists() and (JS9_STATIC_DIR / "js9.js").exists()


def init_js9(force: bool = False) -> bool:
    """
    Initialize JS9 in Jupyter notebook.

    Args:
        force: Force re-initialization even if already initialized

    Returns:
        True if initialization successful, False otherwise
    """
    global _js9_initialized, JS9_ERROR

    if _js9_initialized and not force:
        return True

    if not HAS_IPYTHON:
        JS9_ERROR = "IPython not available"
        return False

    # Check if JS9 files are available
    if not is_js9_available():
        JS9_ERROR = f"JS9 static files not found at {JS9_STATIC_DIR}"
        # Try CDN fallback
        return _init_js9_cdn()

    try:
        # Load JS9 CSS
        css_path = JS9_STATIC_DIR / "js9.css"
        if css_path.exists():
            with open(css_path) as f:
                css_content = f.read()
            display(HTML(f"<style>{css_content}</style>"))

        # Load JS9 JavaScript
        js_path = JS9_STATIC_DIR / "js9.js"
        if js_path.exists():
            with open(js_path) as f:
                js_content = f.read()
            display(Javascript(js_content))

        # Load JS9 preferences if available
        prefs_path = JS9_STATIC_DIR / "js9_prefs.js"
        if prefs_path.exists():
            with open(prefs_path) as f:
                prefs_content = f.read()
            display(Javascript(prefs_content))

        _js9_initialized = True
        JS9_ERROR = None
        return True

    except Exception as e:
        JS9_ERROR = f"Error initializing JS9: {e}"
        # Try CDN fallback
        return _init_js9_cdn()


def _init_js9_cdn() -> bool:
    """
    Initialize JS9 from CDN as fallback.

    Returns:
        True if CDN initialization successful
    """
    global _js9_initialized, JS9_ERROR

    try:
        # JS9 CDN URLs (using jsdelivr CDN)
        js9_cdn_base = "https://cdn.jsdelivr.net/npm/js9@latest"

        html = f"""
        <link rel="stylesheet" href="{js9_cdn_base}/js9.css">
        <script src="{js9_cdn_base}/js9.js"></script>
        <script src="{js9_cdn_base}/js9Helper.js"></script>
        """

        display(HTML(html))
        _js9_initialized = True
        JS9_ERROR = None
        return True

    except Exception as e:
        JS9_ERROR = f"Error initializing JS9 from CDN: {e}"
        return False


def get_js9_init_html() -> str:
    """
    Get HTML for JS9 initialization.

    Returns:
        HTML string for JS9 initialization
    """
    if not is_js9_available():
        # Use CDN
        js9_cdn_base = "https://cdn.jsdelivr.net/npm/js9@latest"
        return f"""
        <link rel="stylesheet" href="{js9_cdn_base}/js9.css">
        <script src="{js9_cdn_base}/js9.js"></script>
        <script src="{js9_cdn_base}/js9Helper.js"></script>
        """
    else:
        # Use local files
        css_path = JS9_STATIC_DIR / "js9.css"
        js_path = JS9_STATIC_DIR / "js9.js"

        html_parts = []
        if css_path.exists():
            with open(css_path) as f:
                html_parts.append(f"<style>{f.read()}</style>")
        if js_path.exists():
            with open(js_path) as f:
                html_parts.append(f"<script>{f.read()}</script>")

        return "\n".join(html_parts)


# Auto-initialize if in Jupyter
if HAS_IPYTHON:
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is not None:
            # We're in a Jupyter environment
            # Don't auto-init here - let user call init_js9() explicitly
            # or it will be called when FITSFile.show() is called
            pass
    except Exception:
        pass

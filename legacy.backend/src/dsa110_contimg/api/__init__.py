"""API module exposure for the monitoring service.

Exposes a default ``app`` for ASGI servers, while retaining the
``create_app`` factory for programmatic use.
"""

# CRITICAL: Suppress CASA deprecation warnings BEFORE any imports
# Must be at the very top to catch warnings from casaconfig imports
import warnings

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="casaconfig.private.measures_update",
)


# Lazy import to avoid expensive operations during module import
def _get_create_app():
    """Lazy import of create_app to avoid triggering imports during test collection."""
    from .routes import create_app

    return create_app


# Make create_app available but don't import it yet
def __getattr__(name):
    if name == "create_app":
        return _get_create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Default ASGI application for `uvicorn dsa110_contimg.api:app`
# Use lazy initialization to avoid expensive operations during import
_app = None


def _get_app():
    """Lazy initialization of the app."""
    global _app
    if _app is None:
        _app = _get_create_app()()
    return _app


# Expose app as a property that creates it on first access
# This allows `uvicorn dsa110_contimg.api:app` to work while avoiding
# expensive operations during module import (e.g., during test collection)


class _LazyApp:
    def __getattr__(self, name):
        return getattr(_get_app(), name)

    async def __call__(self, scope, receive, send):
        """ASGI protocol handler - properly delegate to FastAPI app."""
        app = _get_app()
        await app(scope, receive, send)


app = _LazyApp()

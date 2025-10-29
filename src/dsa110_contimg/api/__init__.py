"""API module exposure for the monitoring service.

Exposes a default ``app`` for ASGI servers, while retaining the
``create_app`` factory for programmatic use.
"""

from .routes import create_app  # noqa: F401

# Default ASGI application for `uvicorn dsa110_contimg.api:app`
app = create_app()

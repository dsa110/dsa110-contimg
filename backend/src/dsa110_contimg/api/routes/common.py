"""
Common utilities and dependencies for routes.
"""

from fastapi.responses import JSONResponse

from ..errors import ErrorEnvelope


def error_response(error: ErrorEnvelope) -> JSONResponse:
    """Convert an ErrorEnvelope to a JSONResponse."""
    return JSONResponse(
        status_code=error.http_status,
        content=error.to_dict(),
    )

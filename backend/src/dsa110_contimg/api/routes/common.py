"""
Common utilities and dependencies for routes.
"""

from fastapi.responses import JSONResponse

from ..exceptions import DSA110APIError, map_exception_to_http_status


def error_response(error: DSA110APIError) -> JSONResponse:
    """Convert a DSA110APIError to a JSONResponse."""
    return JSONResponse(
        status_code=map_exception_to_http_status(error),
        content=error.to_dict(),
    )

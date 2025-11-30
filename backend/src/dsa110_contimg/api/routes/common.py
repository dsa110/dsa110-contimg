"""
Common utilities and dependencies for routes.
"""

from typing import Union

from fastapi.responses import JSONResponse

from ..errors import ErrorEnvelope
from ..exceptions import DSA110APIError, map_exception_to_http_status


def error_response(error: Union[ErrorEnvelope, DSA110APIError]) -> JSONResponse:
    """Convert an error to a JSONResponse.
    
    Supports both the old ErrorEnvelope format and new DSA110APIError exceptions.
    """
    if isinstance(error, DSA110APIError):
        return JSONResponse(
            status_code=map_exception_to_http_status(error),
            content=error.to_dict(),
        )
    else:
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_dict(),
        )

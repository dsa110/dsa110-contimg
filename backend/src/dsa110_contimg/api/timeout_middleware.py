"""
Request timeout middleware for FastAPI
Ensures requests don't hang indefinitely
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Default timeout: 60 seconds
DEFAULT_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeouts"""

    def __init__(self, app: Any, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize timeout middleware

        Args:
            app: ASGI application
            timeout: Request timeout in seconds
        """
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Process request with timeout"""
        try:
            # Run request with timeout
            response = await asyncio.wait_for(call_next(request), timeout=self.timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout after {self.timeout}s: {request.url}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "Request timeout",
                    "message": f"Request exceeded maximum time limit of {self.timeout} seconds",
                },
            )
        except Exception as e:
            logger.error(f"Error in timeout middleware: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "message": str(e)},
            )


def setup_timeout_middleware(app: Any, timeout: int = DEFAULT_TIMEOUT) -> None:
    """
    Setup timeout middleware for FastAPI app

    Args:
        app: FastAPI application instance
        timeout: Request timeout in seconds
    """
    app.add_middleware(TimeoutMiddleware, timeout=timeout)
    logger.info(f"Request timeout middleware configured (timeout: {timeout}s)")

"""
Exception handler middleware for the DSA-110 API.

This module provides centralized exception handling, converting our custom
exception hierarchy into appropriate HTTP responses.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..exceptions import (
    BatchJobInvalidStateError,
    BatchJobNotFoundError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DSA110APIError,
    ExternalServiceError,
    FileNotAccessibleError,
    FITSParsingError,
    InvalidPathError,
    MSParsingError,
    RecordAlreadyExistsError,
    RecordNotFoundError,
    ValidationError,
    map_exception_to_http_status,
)

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to the FastAPI application.

    This function registers handlers for all custom exception types,
    converting them to appropriate HTTP responses.

    Args:
        app: The FastAPI application instance
    """

    @app.exception_handler(RecordNotFoundError)
    async def record_not_found_handler(request: Request, exc: RecordNotFoundError) -> JSONResponse:
        """Handle record not found errors (404)."""
        logger.info(f"Record not found: {exc.message}")
        return JSONResponse(
            status_code=404,
            content=exc.to_dict(),
        )

    @app.exception_handler(RecordAlreadyExistsError)
    async def record_already_exists_handler(
        request: Request, exc: RecordAlreadyExistsError
    ) -> JSONResponse:
        """Handle record already exists errors (409)."""
        logger.info(f"Record already exists: {exc.message}")
        return JSONResponse(
            status_code=409,
            content=exc.to_dict(),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """Handle validation errors (400)."""
        logger.info(f"Validation error: {exc.message}")
        return JSONResponse(
            status_code=400,
            content=exc.to_dict(),
        )

    @app.exception_handler(InvalidPathError)
    async def invalid_path_handler(request: Request, exc: InvalidPathError) -> JSONResponse:
        """Handle invalid path errors (400)."""
        logger.warning(f"Invalid path: {exc.message}")
        return JSONResponse(
            status_code=400,
            content=exc.to_dict(),
        )

    @app.exception_handler(FileNotAccessibleError)
    async def file_not_accessible_handler(
        request: Request, exc: FileNotAccessibleError
    ) -> JSONResponse:
        """Handle file not accessible errors (404)."""
        logger.warning(f"File not accessible: {exc.message}")
        return JSONResponse(
            status_code=404,
            content=exc.to_dict(),
        )

    @app.exception_handler(FITSParsingError)
    async def fits_parsing_handler(request: Request, exc: FITSParsingError) -> JSONResponse:
        """Handle FITS parsing errors (500)."""
        logger.error(f"FITS parsing error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content=exc.to_dict(),
        )

    @app.exception_handler(MSParsingError)
    async def ms_parsing_handler(request: Request, exc: MSParsingError) -> JSONResponse:
        """Handle Measurement Set parsing errors (500)."""
        logger.error(f"MS parsing error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content=exc.to_dict(),
        )

    @app.exception_handler(DatabaseConnectionError)
    async def db_connection_handler(request: Request, exc: DatabaseConnectionError) -> JSONResponse:
        """Handle database connection errors (503)."""
        logger.error(f"Database connection error: {exc.message}")
        return JSONResponse(
            status_code=503,
            content=exc.to_dict(),
        )

    @app.exception_handler(DatabaseQueryError)
    async def db_query_handler(request: Request, exc: DatabaseQueryError) -> JSONResponse:
        """Handle database query errors (500)."""
        logger.error(f"Database query error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content=exc.to_dict(),
        )

    @app.exception_handler(BatchJobNotFoundError)
    async def batch_job_not_found_handler(
        request: Request, exc: BatchJobNotFoundError
    ) -> JSONResponse:
        """Handle batch job not found errors (404)."""
        logger.info(f"Batch job not found: {exc.message}")
        return JSONResponse(
            status_code=404,
            content=exc.to_dict(),
        )

    @app.exception_handler(BatchJobInvalidStateError)
    async def batch_job_invalid_state_handler(
        request: Request, exc: BatchJobInvalidStateError
    ) -> JSONResponse:
        """Handle batch job invalid state errors (409)."""
        logger.info(f"Batch job invalid state: {exc.message}")
        return JSONResponse(
            status_code=409,
            content=exc.to_dict(),
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
        """Handle external service errors (502)."""
        logger.error(f"External service error: {exc.message}")
        return JSONResponse(
            status_code=502,
            content=exc.to_dict(),
        )

    # Catch-all for any DSA110APIError not specifically handled
    @app.exception_handler(DSA110APIError)
    async def dsa110_api_error_handler(request: Request, exc: DSA110APIError) -> JSONResponse:
        """Handle any unhandled DSA110APIError (500)."""
        status_code = map_exception_to_http_status(exc)
        logger.error(f"API error (status={status_code}): {exc.message}")
        return JSONResponse(
            status_code=status_code,
            content=exc.to_dict(),
        )


class DSA110ExceptionMiddleware(BaseHTTPMiddleware):
    """Middleware for catching and logging unexpected exceptions.

    This middleware catches any exceptions that escape the route handlers
    and converts them to a standard error response format.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Process a request, catching any unhandled exceptions."""
        try:
            response = await call_next(request)
            return response
        except DSA110APIError as exc:
            # Should be handled by exception handlers, but catch just in case
            status_code = map_exception_to_http_status(exc)
            logger.error(f"Unhandled API error: {exc.message}")
            return JSONResponse(
                status_code=status_code,
                content=exc.to_dict(),
            )
        except Exception:
            # Log the unexpected error
            logger.exception(f"Unexpected error during request to {request.url}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                },
            )

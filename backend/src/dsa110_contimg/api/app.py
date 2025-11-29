"""
Main FastAPI application for the DSA-110 Continuum Imaging Pipeline.

This module creates and configures the FastAPI app, including:
- API routers for all resource types
- Error handling middleware
- CORS configuration for frontend integration
- Static file serving for the UI
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .errors import validation_failed, internal_error
from .routes import (
    images_router,
    ms_router,
    sources_router,
    jobs_router,
    qa_router,
    cal_router,
    logs_router,
)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="DSA-110 Continuum Imaging Pipeline API",
        description="REST API for the DSA-110 continuum imaging pipeline",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # Configure CORS for frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://dsa110.github.io",  # GitHub Pages
            "http://code.deepsynoptic.org",  # Custom domain
            "https://code.deepsynoptic.org",  # Custom domain HTTPS
            "*.ngrok-free.app",  # ngrok for development
            "*.ngrok-free.dev",  # ngrok alt domain
            "http://localhost:3000",  # Vite dev server
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register API routers
    app.include_router(images_router, prefix="/api")
    app.include_router(ms_router, prefix="/api")
    app.include_router(sources_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(qa_router, prefix="/api")
    app.include_router(cal_router, prefix="/api")
    app.include_router(logs_router, prefix="/api")
    
    # Register exception handlers
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors with standardized envelope."""
        errors = [
            {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        error = validation_failed(errors)
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_dict(),
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions with standardized envelope."""
        # Log the exception for debugging
        # logger.exception("Unhandled exception")
        
        error = internal_error(str(exc) if app.debug else "An unexpected error occurred")
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_dict(),
        )
    
    # Health check endpoint
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {"status": "healthy", "service": "dsa110-contimg-api"}
    
    return app


# Create the app instance
app = create_app()


# Optional: Mount static files for production (frontend build)
# Uncomment when deploying with frontend dist
# app.mount("/ui", StaticFiles(directory="../frontend/dist", html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
Main FastAPI application for the DSA-110 Continuum Imaging Pipeline.

This module creates and configures the FastAPI app, including:
- API routers for all resource types
- Error handling middleware
- CORS configuration for frontend integration
- IP-based access control
- Static file serving for the UI
"""

from __future__ import annotations

import ipaddress
import os
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError


# Allowed IP addresses/networks for API access
# Can be overridden with DSA110_ALLOWED_IPS environment variable (comma-separated)
DEFAULT_ALLOWED_IPS = [
    "127.0.0.1",        # localhost
    "::1",              # localhost IPv6
    "10.0.0.0/8",       # Private network
    "172.16.0.0/12",    # Private network
    "192.168.0.0/16",   # Private network
]


def get_allowed_networks():
    """Parse allowed IPs from environment or use defaults."""
    env_ips = os.getenv("DSA110_ALLOWED_IPS")
    if env_ips:
        ip_list = [ip.strip() for ip in env_ips.split(",")]
    else:
        ip_list = DEFAULT_ALLOWED_IPS
    
    networks = []
    for ip in ip_list:
        try:
            if "/" in ip:
                networks.append(ipaddress.ip_network(ip, strict=False))
            else:
                # Single IP - treat as /32 or /128
                networks.append(ipaddress.ip_network(ip))
        except ValueError:
            pass  # Skip invalid entries
    return networks


def is_ip_allowed(client_ip: str, allowed_networks: list) -> bool:
    """Check if client IP is in allowed networks."""
    try:
        ip = ipaddress.ip_address(client_ip)
        return any(ip in network for network in allowed_networks)
    except ValueError:
        return False

from .errors import validation_failed, internal_error
from .routes import (
    images_router,
    ms_router,
    sources_router,
    jobs_router,
    qa_router,
    cal_router,
    logs_router,
    stats_router,
    cache_router,
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
    app.include_router(stats_router, prefix="/api")
    app.include_router(cache_router, prefix="/api")
    
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
    
    # Health check endpoint (always allowed, before IP check)
    @app.get("/api/health")
    async def health_check(detailed: bool = False):
        """Health check endpoint for monitoring.
        
        Args:
            detailed: If True, include database and disk space checks
        """
        import shutil
        from pathlib import Path
        
        response = {
            "status": "healthy",
            "service": "dsa110-contimg-api",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if detailed:
            # Check database connectivity
            db_status = {}
            try:
                from dsa110_contimg.database.session import get_db_path
                for db_name in ["products", "cal_registry", "hdf5", "ingest"]:
                    try:
                        db_path = Path(get_db_path(db_name))
                        if db_path.exists():
                            import sqlite3
                            conn = sqlite3.connect(str(db_path), timeout=2.0)
                            conn.execute("SELECT 1")
                            conn.close()
                            db_status[db_name] = "ok"
                        else:
                            db_status[db_name] = "not_found"
                    except Exception as e:
                        db_status[db_name] = f"error: {str(e)[:50]}"
            except Exception:
                db_status["error"] = "Could not check databases"
            response["databases"] = db_status
            
            # Check disk space
            disk_status = {}
            for path_str in ["/data/dsa110-contimg/state", "/stage/dsa110-contimg"]:
                path = Path(path_str)
                if path.exists():
                    try:
                        usage = shutil.disk_usage(path)
                        free_gb = usage.free / (1024 ** 3)
                        disk_status[path_str] = {
                            "free_gb": round(free_gb, 2),
                            "status": "ok" if free_gb > 5 else ("warning" if free_gb > 1 else "critical"),
                        }
                    except Exception:
                        disk_status[path_str] = {"status": "error"}
            response["disk"] = disk_status
            
            # Check if any component is unhealthy
            has_errors = any(
                v != "ok" for v in db_status.values() if isinstance(v, str)
            ) or any(
                d.get("status") == "critical" for d in disk_status.values() if isinstance(d, dict)
            )
            if has_errors:
                response["status"] = "degraded"
        
        return response
    
    # IP-based access control middleware
    allowed_networks = get_allowed_networks()
    
    @app.middleware("http")
    async def ip_filter_middleware(request: Request, call_next):
        """Restrict API access to allowed IP addresses."""
        # Always allow health checks and metrics (for external monitoring)
        if request.url.path in ("/api/health", "/metrics"):
            return await call_next(request)
        
        # Get client IP (handle proxies)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "0.0.0.0"
        
        if not is_ip_allowed(client_ip, allowed_networks):
            return JSONResponse(
                status_code=403,
                content={
                    "code": "FORBIDDEN",
                    "message": f"Access denied from {client_ip}",
                    "hint": "Contact administrator to whitelist your IP",
                },
            )
        
        return await call_next(request)
    
    return app


# Create the app instance
app = create_app()

# Prometheus metrics instrumentation (must be after app creation)
# Metrics available at /metrics
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/api/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)
except ImportError:
    pass  # prometheus-fastapi-instrumentator not installed

# Import custom scientific metrics (registers them with Prometheus)
try:
    from .metrics import sync_gauges_from_database
    
    # Sync gauges on startup
    @app.on_event("startup")
    async def startup_sync_metrics():
        """Sync database gauges on startup."""
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        
        # Initial sync
        sync_gauges_from_database()
        logger.info("Initial metrics sync completed")
        
        # Background task to sync every 30 seconds
        async def periodic_sync():
            while True:
                await asyncio.sleep(30)
                try:
                    sync_gauges_from_database()
                except Exception as e:
                    logger.warning(f"Periodic metrics sync failed: {e}")
        
        asyncio.create_task(periodic_sync())
        logger.info("Periodic metrics sync task started (30s interval)")

except ImportError:
    pass  # metrics module not available


# Optional: Mount static files for production (frontend build)
# Uncomment when deploying with frontend dist
# app.mount("/ui", StaticFiles(directory="../frontend/dist", html=True), name="ui")



def ensure_port_available(port: int = 8000) -> None:
    """
    Ensure the given port is available by killing any blocking processes.
    
    Called automatically when running the app directly via `python -m ... app:app`.
    """
    import os
    import signal
    import subprocess
    import sys
    import time
    
    def get_pids_on_port(p: int) -> list[int]:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{p}"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return [int(pid) for pid in result.stdout.strip().split('\n') if pid]
        except Exception:
            pass
        return []
    
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        pids = get_pids_on_port(port)
        if not pids:
            if attempt > 1:
                print(f"[ensure-port] OK Port {port} is now available")
            return
        
        # Don't kill ourselves
        my_pid = os.getpid()
        pids = [p for p in pids if p != my_pid]
        if not pids:
            return
        
        print(f"[ensure-port] Found {len(pids)} process(es) blocking port {port}: {pids}")
        
        sig = signal.SIGKILL if attempt >= 3 else signal.SIGTERM
        for pid in pids:
            try:
                os.kill(pid, sig)
                print(f"[ensure-port] Sent {'SIGKILL' if attempt >= 3 else 'SIGTERM'} to PID {pid}")
            except (ProcessLookupError, PermissionError):
                pass
        
        time.sleep(0.5 * (2 ** (attempt - 1)))  # Exponential backoff
    
    # Final check
    if get_pids_on_port(port):
        print(f"[ensure-port] WARNING: Could not free port {port}", file=sys.stderr)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    ensure_port_available(port)
    uvicorn.run(app, host="0.0.0.0", port=port)

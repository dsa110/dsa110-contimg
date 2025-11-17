"""Status and health subrouter for the API.

Moves lightweight status, health, and streaming endpoints out of routes.py
to improve maintainability and testability.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (APIRouter, HTTPException, Request, WebSocket,
                     WebSocketDisconnect)
from fastapi.responses import HTMLResponse, StreamingResponse

from dsa110_contimg.api.data_access import (_connect, fetch_calibration_sets,
                                            fetch_queue_stats,
                                            fetch_recent_queue_groups)
from dsa110_contimg.api.models import CatalogCoverageStatus, PipelineStatus

logger = logging.getLogger(__name__)

router = APIRouter()


def get_catalog_coverage_status(
    ingest_db_path: Optional[Path] = None,
) -> Optional[CatalogCoverageStatus]:
    """Get catalog coverage status for current declination.
    
    Args:
        ingest_db_path: Path to ingest database (default: from config)
        
    Returns:
        CatalogCoverageStatus if declination is available, None otherwise
    """
    try:
        import sqlite3

        from dsa110_contimg.catalog.builders import (
          CATALOG_COVERAGE_LIMITS, check_catalog_database_exists)

        # Get current declination from pointing history
        if ingest_db_path is None:
            # Try to find ingest DB from common locations
            for path_str in [
                "/data/dsa110-contimg/state/ingest.sqlite3",
                "state/ingest.sqlite3",
            ]:
                candidate = Path(path_str)
                if candidate.exists():
                    ingest_db_path = candidate
                    break
        
        if ingest_db_path is None or not ingest_db_path.exists():
            logger.debug("Ingest database not found, skipping catalog coverage status")
            return None
        
        with sqlite3.connect(str(ingest_db_path)) as conn:
            cursor = conn.execute(
                "SELECT dec_deg FROM pointing_history ORDER BY timestamp DESC LIMIT 1"
            )
            result = cursor.fetchone()
            if not result:
                return None
            
            dec_deg = float(result[0])
        
        # Check each catalog
        coverage_status = CatalogCoverageStatus(dec_deg=dec_deg)
        
        for catalog_type in ["nvss", "first", "rax"]:
            limits = CATALOG_COVERAGE_LIMITS.get(catalog_type, {})
            dec_min = limits.get("dec_min", -90.0)
            dec_max = limits.get("dec_max", 90.0)
            
            within_coverage = dec_deg >= dec_min and dec_deg <= dec_max
            exists, db_path = check_catalog_database_exists(catalog_type, dec_deg)
            
            status_dict = {
                "exists": exists,
                "within_coverage": within_coverage,
                "db_path": str(db_path) if db_path else None,
            }
            
            if catalog_type == "nvss":
                coverage_status.nvss = status_dict
            elif catalog_type == "first":
                coverage_status.first = status_dict
            elif catalog_type == "rax":
                coverage_status.rax = status_dict
        
        return coverage_status
        
    except Exception as e:
        logger.warning(f"Failed to get catalog coverage status: {e}", exc_info=True)
        return None


@router.post("/test/streaming/broadcast")
async def test_streaming_broadcast(message: Optional[dict] = None):
    """Trigger WebSocket broadcast (disabled in production)."""
    if os.getenv("ENVIRONMENT") == "production":
        raise HTTPException(status_code=404, detail="Not available in production")

    from time import time

    from dsa110_contimg.api.websocket_manager import manager

    test_message = message or {
        "type": "streaming_status_update",
        "status": "running",
        "timestamp": time(),
        "test": True,
    }
    await manager.broadcast(test_message)
    return {"success": True, "message": "Broadcast sent", "data": test_message}


@router.get("/health")
def health(request: Request):
    """Health check endpoint for monitoring and load balancers."""
    cfg = request.app.state.cfg

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "databases": {},
        "version": "0.1.0",
    }

    # Check database accessibility
    databases = {
        "queue": cfg.queue_db,
        "products": cfg.products_db,
        "registry": cfg.registry_db,
    }

    all_healthy = True
    for db_name, db_path in databases.items():
        try:
            if db_path.exists():
                with _connect(db_path) as conn:
                    conn.execute("SELECT 1").fetchone()
                health_status["databases"][db_name] = "accessible"
            else:
                health_status["databases"][db_name] = "not_found"
                all_healthy = False
        except Exception as e:
            health_status["databases"][db_name] = f"error: {str(e)}"
            all_healthy = False

    # Check disk space (basic check)
    try:
        import shutil

        disk_usage = shutil.disk_usage(
            cfg.queue_db.parent if cfg.queue_db.parent.exists() else Path(".")
        )
        health_status["disk"] = {
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "total_gb": round(disk_usage.total / (1024**3), 2),
        }
    except (OSError, ValueError, AttributeError) as e:
        # Disk usage check failed - log but don't fail health check
        logger.debug("Disk usage check failed: %s", e)
        pass

    if not all_healthy:
        health_status["status"] = "degraded"
        # Return tuple (body, status) is allowed, but HTMLResponse used previously; keep tuple
        return health_status, 503

    return health_status


@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates."""
    from dsa110_contimg.api.websocket_manager import manager

    await websocket.accept()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except (ConnectionError, RuntimeError, ValueError) as e:
        # Handle connection errors, runtime errors, or invalid data
        logger.warning("WebSocket error: %s", e)
        await manager.disconnect(websocket)


@router.get("/sse/status")
async def sse_status():
    """Server-Sent Events endpoint for real-time status updates."""
    from dsa110_contimg.api.websocket_manager import event_generator

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status", response_model=PipelineStatus)
def status(request: Request, limit: int = 20) -> PipelineStatus:
    """Pipeline status summary for dashboard widgets."""
    cfg = request.app.state.cfg
    queue_stats = fetch_queue_stats(cfg.queue_db)
    recent_groups = fetch_recent_queue_groups(cfg.queue_db, cfg, limit=limit)
    cal_sets = fetch_calibration_sets(cfg.registry_db)
    matched_recent = sum(1 for g in recent_groups if getattr(g, "has_calibrator", False))
    
    # Get catalog coverage status
    ingest_db_path = Path(cfg.ingest_db) if hasattr(cfg, "ingest_db") else None
    catalog_coverage = get_catalog_coverage_status(ingest_db_path=ingest_db_path)
    
    return PipelineStatus(
        queue=queue_stats,
        recent_groups=recent_groups,
        calibration_sets=cal_sets,
        matched_recent=matched_recent,
        catalog_coverage=catalog_coverage,
    )

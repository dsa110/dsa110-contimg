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

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse

from dsa110_contimg.api.data_access import (
    _connect,
    fetch_calibration_sets,
    fetch_queue_stats,
    fetch_recent_queue_groups,
)
from dsa110_contimg.api.models import PipelineStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/test/streaming/broadcast")
async def test_streaming_broadcast(message: Optional[dict] = None):
    """Trigger WebSocket broadcast (disabled in production)."""
    if os.getenv("ENVIRONMENT") == "production":
        raise HTTPException(
            status_code=404, detail="Not available in production")

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
    matched_recent = sum(
        1 for g in recent_groups if getattr(g, "has_calibrator", False)
    )
    return PipelineStatus(
        queue=queue_stats,
        recent_groups=recent_groups,
        calibration_sets=cal_sets,
        matched_recent=matched_recent,
    )

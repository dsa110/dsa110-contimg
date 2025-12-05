"""
Interactive imaging routes for DSA-110 pipeline.

Provides endpoints for launching and managing InteractiveClean Bokeh sessions.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..services.bokeh_sessions import (
    DSA110_ICLEAN_DEFAULTS,
    BokehSessionManager,
    get_session_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/imaging", tags=["imaging"])


# =============================================================================
# Request/Response Models
# =============================================================================


class InteractiveCleanRequest(BaseModel):
    """Request to start an interactive clean session."""

    ms_path: str = Field(..., description="Path to Measurement Set")
    imagename: str = Field(..., description="Output image name prefix")
    imsize: List[int] = Field(
        default=[5040, 5040],
        min_length=2,
        max_length=2,
        description="Image size in pixels [width, height]",
    )
    cell: str = Field(default="2.5arcsec", description="Cell size")
    specmode: str = Field(default="mfs", description="Spectral mode (mfs, cube, etc)")
    deconvolver: str = Field(
        default="mtmfs", description="Deconvolver algorithm (mtmfs, hogbom, etc)"
    )
    weighting: str = Field(
        default="briggs", description="Weighting scheme (briggs, natural, uniform)"
    )
    robust: float = Field(
        default=0.5, ge=-2.0, le=2.0, description="Robust parameter for Briggs weighting"
    )
    niter: int = Field(default=10000, ge=0, le=1000000, description="Maximum iterations")
    threshold: str = Field(default="0.5mJy", description="Stopping threshold")

    class Config:
        json_schema_extra = {
            "example": {
                "ms_path": "/data/ms/2025-10-05T12:00:00.ms",
                "imagename": "/stage/dsa110-contimg/images/test_clean",
                "imsize": [5040, 5040],
                "cell": "2.5arcsec",
                "specmode": "mfs",
                "deconvolver": "mtmfs",
                "weighting": "briggs",
                "robust": 0.5,
                "niter": 10000,
                "threshold": "0.5mJy",
            }
        }


class InteractiveCleanResponse(BaseModel):
    """Response with session details after launching interactive clean."""

    session_id: str = Field(..., description="Unique session identifier")
    url: str = Field(..., description="URL to access the Bokeh session")
    status: str = Field(..., description="Session status (started, running, etc)")
    ms_path: str = Field(..., description="Path to the Measurement Set")
    imagename: str = Field(..., description="Output image name prefix")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "url": "http://localhost:5010/iclean",
                "status": "started",
                "ms_path": "/data/ms/2025-10-05T12:00:00.ms",
                "imagename": "/stage/dsa110-contimg/images/test_clean",
            }
        }


class SessionInfo(BaseModel):
    """Information about an active session."""

    id: str = Field(..., description="Session ID")
    port: int = Field(..., description="Bokeh server port")
    url: str = Field(..., description="Session URL")
    ms_path: str = Field(..., description="Measurement Set path")
    imagename: str = Field(..., description="Output image name")
    created_at: str = Field(..., description="Session creation time (ISO format)")
    age_hours: float = Field(..., description="Session age in hours")
    is_alive: bool = Field(..., description="Whether the Bokeh process is running")
    user_id: Optional[str] = Field(None, description="User who created the session")


class SessionListResponse(BaseModel):
    """Response containing list of active sessions."""

    sessions: List[SessionInfo] = Field(..., description="Active sessions")
    total: int = Field(..., description="Total number of active sessions")
    available_ports: int = Field(..., description="Number of available ports")


class ImagingDefaultsResponse(BaseModel):
    """Response containing DSA-110 default imaging parameters."""

    imsize: List[int] = Field(..., description="Default image size")
    cell: str = Field(..., description="Default cell size")
    specmode: str = Field(..., description="Default spectral mode")
    deconvolver: str = Field(..., description="Default deconvolver")
    weighting: str = Field(..., description="Default weighting scheme")
    robust: float = Field(..., description="Default robust parameter")
    niter: int = Field(..., description="Default max iterations")
    threshold: str = Field(..., description="Default threshold")
    nterms: int = Field(..., description="Default number of Taylor terms")
    datacolumn: str = Field(..., description="Default data column")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/interactive", response_model=InteractiveCleanResponse)
async def start_interactive_clean(
    request: InteractiveCleanRequest,
    manager: BokehSessionManager = Depends(get_session_manager),
) -> InteractiveCleanResponse:
    """
    Launch an interactive clean session.

    Opens a Bokeh server running casagui's InteractiveClean for the specified
    Measurement Set. Returns a URL that can be opened in a new browser tab
    for interactive imaging with mask drawing and deconvolution control.

    The session will be automatically cleaned up after 4 hours of inactivity
    or when explicitly stopped.

    **DSA-110 Specific Notes:**
    - Default parameters are optimized for DSA-110 continuum imaging
    - Image size of 5040x5040 with 2.5" cells covers the primary beam
    - mtmfs deconvolver with 2 Taylor terms handles spectral index
    """
    # Validate MS exists
    ms_path = Path(request.ms_path)
    if not ms_path.exists():
        raise HTTPException(status_code=404, detail=f"Measurement Set not found: {request.ms_path}")

    # Validate it looks like an MS (has MAIN table)
    if not (ms_path / "table.dat").exists():
        raise HTTPException(
            status_code=422,
            detail=f"Path does not appear to be a valid Measurement Set: {request.ms_path}",
        )

    # Build params dict
    params = {
        "imsize": request.imsize,
        "cell": request.cell,
        "specmode": request.specmode,
        "deconvolver": request.deconvolver,
        "weighting": request.weighting,
        "robust": request.robust,
        "niter": request.niter,
        "threshold": request.threshold,
    }

    try:
        session = await manager.create_session(
            ms_path=str(ms_path),
            imagename=request.imagename,
            params=params,
        )

        return InteractiveCleanResponse(
            session_id=session.id,
            url=session.url,
            status="started",
            ms_path=session.ms_path,
            imagename=session.imagename,
        )

    except RuntimeError as e:
        logger.exception(f"Failed to start interactive clean session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error starting interactive clean: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start session: {type(e).__name__}")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    manager: BokehSessionManager = Depends(get_session_manager),
) -> SessionListResponse:
    """
    List all active interactive imaging sessions.

    Returns information about all currently running InteractiveClean sessions,
    including their URLs, ages, and status.
    """
    sessions = manager.list_sessions()

    return SessionListResponse(
        sessions=[SessionInfo(**s) for s in sessions],
        total=len(sessions),
        available_ports=manager.port_pool.available_count,
    )


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    manager: BokehSessionManager = Depends(get_session_manager),
) -> SessionInfo:
    """
    Get details about a specific session.

    Returns detailed information about a single interactive imaging session.
    """
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return SessionInfo(**session.to_dict())


@router.delete("/sessions/{session_id}")
async def stop_session(
    session_id: str,
    manager: BokehSessionManager = Depends(get_session_manager),
) -> dict:
    """
    Stop and cleanup an interactive imaging session.

    Terminates the Bokeh server process and frees the allocated port.
    """
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    success = await manager.cleanup_session(session_id)

    return {
        "status": "stopped" if success else "not_found",
        "session_id": session_id,
    }


@router.post("/sessions/cleanup")
async def cleanup_stale_sessions(
    max_age_hours: float = Query(
        default=4.0, ge=0.5, le=24.0, description="Maximum session age in hours"
    ),
    manager: BokehSessionManager = Depends(get_session_manager),
) -> dict:
    """
    Manually trigger cleanup of stale sessions.

    Useful for administration purposes. Normally, cleanup happens automatically.
    """
    cleaned = await manager.cleanup_stale_sessions(max_age_hours=max_age_hours)
    dead = await manager.cleanup_dead_sessions()

    return {
        "cleaned_stale": cleaned,
        "cleaned_dead": dead,
        "remaining_sessions": len(manager.sessions),
    }


@router.get("/defaults", response_model=ImagingDefaultsResponse)
async def get_imaging_defaults() -> ImagingDefaultsResponse:
    """
    Get DSA-110 default imaging parameters.

    Returns the recommended default parameters for imaging DSA-110 data.
    These can be used to pre-populate the interactive clean request form.
    """
    return ImagingDefaultsResponse(**DSA110_ICLEAN_DEFAULTS)


@router.get("/status")
async def get_imaging_status(
    manager: BokehSessionManager = Depends(get_session_manager),
) -> dict:
    """
    Get overall status of the imaging service.

    Returns summary statistics about active sessions and available resources.
    """
    sessions = manager.list_sessions()
    alive_count = sum(1 for s in sessions if s.get("is_alive", False))

    return {
        "status": "healthy",
        "total_sessions": len(sessions),
        "alive_sessions": alive_count,
        "dead_sessions": len(sessions) - alive_count,
        "available_ports": manager.port_pool.available_count,
        "ports_in_use": manager.port_pool.in_use_count,
    }


# =============================================================================
# WebSocket Endpoint for Progress Updates
# =============================================================================


@router.websocket("/sessions/{session_id}/ws")
async def session_progress_websocket(
    websocket: WebSocket,
    session_id: str,
    manager: BokehSessionManager = Depends(get_session_manager),
) -> None:
    """
    WebSocket endpoint for real-time session progress updates.

    Clients can connect to receive progress updates from InteractiveClean sessions.
    Messages are JSON formatted with type and payload fields:

    - {"type": "status", "payload": "connected"}
    - {"type": "progress", "payload": {...}}
    - {"type": "error", "payload": "error message"}
    """
    await websocket.accept()

    # Validate session exists
    session = await manager.get_session(session_id)
    if not session:
        await websocket.send_json({"type": "error", "payload": f"Session not found: {session_id}"})
        await websocket.close(code=4004)
        return

    # Send initial status
    await websocket.send_json({"type": "status", "payload": "connected"})

    # Track this WebSocket in the session manager
    manager.register_websocket(session_id, websocket)

    try:
        # Keep connection alive and monitor session
        while True:
            # Check if session is still alive
            session = await manager.get_session(session_id)
            if not session or not session.is_alive:
                await websocket.send_json({"type": "status", "payload": "stopped"})
                break

            # Send heartbeat and wait for client messages
            try:
                # Wait for client messages (with timeout for heartbeat)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Handle client commands
                if data == "ping":
                    await websocket.send_json({"type": "pong", "payload": None})
                elif data == "status":
                    await websocket.send_json(
                        {"type": "status", "payload": "alive" if session.is_alive else "dead"}
                    )

            except asyncio.TimeoutError:
                # Send heartbeat on timeout
                await websocket.send_json(
                    {
                        "type": "heartbeat",
                        "payload": {
                            "session_id": session_id,
                            "age_hours": session.age_hours if session else 0,
                        },
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except (ConnectionError, RuntimeError, asyncio.CancelledError) as e:
        # Handle connection-related errors and task cancellation
        logger.exception(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "payload": str(e)})
        except (ConnectionError, RuntimeError):
            # Socket already closed, ignore send failure
            pass
    finally:
        # Unregister WebSocket
        manager.unregister_websocket(session_id, websocket)

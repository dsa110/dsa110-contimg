"""
CARTA (Cube Analysis and Rendering Tool for Astronomy) API routes.

Provides integration with CARTA for interactive visualization of
measurement sets and FITS images. CARTA must be running as a server
(https://cartavis.org) for these endpoints to function.

The API provides:
- Status checking to determine if CARTA is available
- Session management for multi-user access
- File opening in CARTA's embedded viewer
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/carta", tags=["carta"])

# =============================================================================
# Configuration
# =============================================================================

# CARTA server URL - defaults to local instance on standard port
CARTA_SERVER_URL = os.getenv("CARTA_SERVER_URL", "http://localhost:3002")

# Data paths that CARTA can access (for path translation)
CARTA_DATA_ROOT = os.getenv("CARTA_DATA_ROOT", "/data")

# Timeouts for CARTA requests
CARTA_TIMEOUT = httpx.Timeout(5.0, read=30.0)

# Maximum concurrent sessions (0 = unlimited)
MAX_CARTA_SESSIONS = int(os.getenv("CARTA_MAX_SESSIONS", "10"))


# =============================================================================
# Pydantic Models (matching frontend types in src/api/carta.ts)
# =============================================================================


class CARTAStatus(BaseModel):
    """CARTA server status response."""

    available: bool = Field(..., description="Whether CARTA server is reachable")
    version: Optional[str] = Field(None, description="CARTA server version")
    url: Optional[str] = Field(None, description="CARTA viewer base URL")
    sessions_active: Optional[int] = Field(None, description="Number of active sessions")
    max_sessions: Optional[int] = Field(None, description="Maximum allowed sessions")
    message: Optional[str] = Field(None, description="Status message or error")


class CARTASession(BaseModel):
    """Active CARTA session information."""

    id: str = Field(..., description="Session unique identifier")
    file_path: str = Field(..., description="Path to the file being viewed")
    file_type: str = Field(..., description="File type (ms, fits, image)")
    created_at: str = Field(..., description="ISO timestamp when session was created")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")
    user: Optional[str] = Field(None, description="Username if authenticated")


class CARTAOpenRequest(BaseModel):
    """Request to open a file in CARTA."""

    file_path: str = Field(..., description="Path to the file to open")
    file_type: Literal["ms", "fits", "image"] = Field(
        "ms", description="Type of file being opened"
    )
    new_session: bool = Field(
        False, description="Whether to create a new session or reuse existing"
    )


class CARTAOpenResponse(BaseModel):
    """Response after opening a file in CARTA."""

    success: bool = Field(..., description="Whether the file was opened successfully")
    session_id: str = Field(..., description="Session ID for the viewer")
    viewer_url: str = Field(..., description="URL to access the CARTA viewer")
    message: Optional[str] = Field(None, description="Additional information")


# =============================================================================
# In-memory session tracking (for demo/development)
# In production, this would be backed by Redis or the CARTA server API
# =============================================================================

_active_sessions: Dict[str, CARTASession] = {}


# =============================================================================
# Helper Functions
# =============================================================================


async def _check_carta_server() -> tuple[bool, Optional[str], Optional[str]]:
    """
    Check if CARTA server is running and get its version.
    
    Returns:
        Tuple of (is_available, version, error_message)
    """
    try:
        async with httpx.AsyncClient(timeout=CARTA_TIMEOUT) as client:
            # Try to reach CARTA's status endpoint
            # Note: CARTA server may expose different endpoints depending on version
            # Common patterns: /api/status, /status, or just /
            for endpoint in ["/api/status", "/status", "/"]:
                try:
                    response = await client.get(f"{CARTA_SERVER_URL}{endpoint}")
                    if response.status_code == 200:
                        # Try to parse version from response
                        try:
                            data = response.json()
                            version = data.get("version", data.get("carta_version", "unknown"))
                        except Exception:
                            # Not JSON, but server is responding
                            version = "unknown"
                        return True, version, None
                except httpx.RequestError:
                    continue
            
            # If no endpoints worked, server might be running but not responding
            return False, None, "CARTA server is not responding on expected endpoints"
            
    except httpx.TimeoutException:
        logger.warning(f"CARTA server timeout at {CARTA_SERVER_URL}")
        return False, None, "CARTA server connection timed out"
    except httpx.RequestError as e:
        logger.debug(f"CARTA server not available: {e}")
        return False, None, f"Cannot connect to CARTA server: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error checking CARTA: {e}")
        return False, None, f"Unexpected error: {str(e)}"


def _build_viewer_url(file_path: str, session_id: str) -> str:
    """Build the CARTA viewer URL for a file."""
    # CARTA URL format varies by deployment
    # Common patterns:
    # - http://host:port/?file=path
    # - http://host:port/#session_id
    # - http://host:port/api/open?file=path
    from urllib.parse import quote
    
    encoded_path = quote(file_path, safe="")
    return f"{CARTA_SERVER_URL}/?file={encoded_path}&session={session_id}"


def _validate_file_path(file_path: str) -> bool:
    """
    Validate that the file path is accessible to CARTA.
    
    Security: Prevents path traversal and access to unauthorized directories.
    """
    import os.path
    
    # Normalize the path
    normalized = os.path.normpath(file_path)
    
    # Must be absolute
    if not os.path.isabs(normalized):
        return False
    
    # Must be under allowed data roots
    allowed_roots = [
        "/data/",
        "/stage/",
        CARTA_DATA_ROOT,
    ]
    
    return any(normalized.startswith(root) for root in allowed_roots)


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/status", response_model=CARTAStatus)
async def get_carta_status():
    """
    Check CARTA server availability and status.
    
    Returns information about whether CARTA is running, its version,
    and current session usage. This is used by the frontend to determine
    whether to show CARTA integration options.
    """
    available, version, error_msg = await _check_carta_server()
    
    if not available:
        return CARTAStatus(
            available=False,
            message=error_msg or "CARTA server is not available",
        )
    
    return CARTAStatus(
        available=True,
        version=version,
        url=CARTA_SERVER_URL,
        sessions_active=len(_active_sessions),
        max_sessions=MAX_CARTA_SESSIONS if MAX_CARTA_SESSIONS > 0 else None,
        message="CARTA server is running",
    )


@router.get("/sessions", response_model=List[CARTASession])
async def list_carta_sessions():
    """
    List all active CARTA sessions.
    
    Returns information about currently open CARTA viewer sessions,
    including the files being viewed and when they were opened.
    """
    # Clean up stale sessions (older than 24 hours with no activity)
    # In production, CARTA server would manage this
    now = datetime.utcnow()
    stale_threshold = 24 * 60 * 60  # 24 hours in seconds
    
    active = []
    for session_id, session in list(_active_sessions.items()):
        try:
            created = datetime.fromisoformat(session.created_at.replace("Z", "+00:00"))
            age_seconds = (now - created.replace(tzinfo=None)).total_seconds()
            if age_seconds < stale_threshold:
                active.append(session)
            else:
                del _active_sessions[session_id]
        except Exception:
            active.append(session)  # Keep if we can't parse timestamp
    
    return active


@router.post("/open", response_model=CARTAOpenResponse)
async def open_in_carta(request: CARTAOpenRequest):
    """
    Open a file in CARTA viewer.
    
    Creates a new CARTA session (or reuses existing) for viewing the
    specified file. Returns the viewer URL that can be embedded in
    an iframe or opened in a new window.
    
    Args:
        request: File path and options for opening
        
    Returns:
        Session information and viewer URL
        
    Raises:
        HTTPException: If CARTA is unavailable or file cannot be accessed
    """
    # Check if CARTA is available
    available, _, error_msg = await _check_carta_server()
    if not available:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CARTA server is not available",
                "message": error_msg,
            },
        )
    
    # Validate file path for security
    if not _validate_file_path(request.file_path):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid file path",
                "message": "File path must be under allowed data directories",
            },
        )
    
    # Check if file exists
    import os
    if not os.path.exists(request.file_path):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "File not found",
                "message": f"The file does not exist: {request.file_path}",
            },
        )
    
    # Check session limits
    if MAX_CARTA_SESSIONS > 0 and len(_active_sessions) >= MAX_CARTA_SESSIONS:
        if request.new_session:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Session limit reached",
                    "message": f"Maximum of {MAX_CARTA_SESSIONS} concurrent sessions allowed",
                },
            )
    
    # Check for existing session with same file (if not requesting new)
    if not request.new_session:
        for session_id, session in _active_sessions.items():
            if session.file_path == request.file_path:
                return CARTAOpenResponse(
                    success=True,
                    session_id=session_id,
                    viewer_url=_build_viewer_url(request.file_path, session_id),
                    message="Reusing existing session",
                )
    
    # Create new session
    session_id = str(uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    
    session = CARTASession(
        id=session_id,
        file_path=request.file_path,
        file_type=request.file_type,
        created_at=now,
        last_activity=now,
    )
    
    _active_sessions[session_id] = session
    
    viewer_url = _build_viewer_url(request.file_path, session_id)
    
    logger.info(f"Opened CARTA session {session_id} for {request.file_path}")
    
    return CARTAOpenResponse(
        success=True,
        session_id=session_id,
        viewer_url=viewer_url,
        message="New session created",
    )


@router.delete("/sessions/{session_id}")
async def close_carta_session(
    session_id: str = Path(..., description="Session ID to close"),
):
    """
    Close a CARTA session.
    
    Terminates an active CARTA viewer session and frees up resources.
    This should be called when the user navigates away from the viewer.
    
    Args:
        session_id: The session ID to close
        
    Returns:
        Confirmation of session closure
        
    Raises:
        HTTPException: If session is not found
    """
    if session_id not in _active_sessions:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Session not found",
                "message": f"No active session with ID: {session_id}",
            },
        )
    
    session = _active_sessions.pop(session_id)
    logger.info(f"Closed CARTA session {session_id} for {session.file_path}")
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "Session closed successfully",
    }


@router.get("/sessions/{session_id}", response_model=CARTASession)
async def get_carta_session(
    session_id: str = Path(..., description="Session ID to retrieve"),
):
    """
    Get information about a specific CARTA session.
    
    Args:
        session_id: The session ID to look up
        
    Returns:
        Session details including file path and timestamps
        
    Raises:
        HTTPException: If session is not found
    """
    if session_id not in _active_sessions:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Session not found",
                "message": f"No active session with ID: {session_id}",
            },
        )
    
    # Update last activity
    session = _active_sessions[session_id]
    session.last_activity = datetime.utcnow().isoformat() + "Z"
    
    return session

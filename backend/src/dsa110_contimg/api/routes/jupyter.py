"""
Jupyter Integration API routes.

Proxy to JupyterHub for notebook management, launching, and status.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jupyter", tags=["jupyter"])

# Configuration
JUPYTERHUB_URL = os.getenv("JUPYTERHUB_URL", "http://localhost:8000")
JUPYTERHUB_TOKEN = os.getenv("JUPYTERHUB_API_TOKEN", "")
NOTEBOOK_DIR = os.getenv("JUPYTER_NOTEBOOK_DIR", "/data/dsa110-contimg/notebooks")


# ============================================================================
# Pydantic Models
# ============================================================================


class NotebookInfo(BaseModel):
    """Information about a notebook file."""

    name: str
    path: str
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None
    is_template: bool = False
    description: Optional[str] = None


class NotebookListResponse(BaseModel):
    """Response for listing notebooks."""

    notebooks: List[NotebookInfo]
    total: int


class ServerStatus(BaseModel):
    """JupyterHub server status."""

    running: bool
    url: Optional[str] = None
    last_activity: Optional[str] = None
    started_at: Optional[str] = None
    pending: Optional[str] = None  # 'spawn', 'stop', None


class LaunchRequest(BaseModel):
    """Request to launch a notebook."""

    notebook_path: Optional[str] = None
    template_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class LaunchResponse(BaseModel):
    """Response from launching a notebook."""

    success: bool
    url: str
    message: str


class TemplateInfo(BaseModel):
    """Information about a notebook template."""

    name: str
    description: str
    path: str
    parameters: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


# ============================================================================
# JupyterHub API Client
# ============================================================================


async def _hub_request(
    method: str,
    path: str,
    **kwargs,
) -> httpx.Response:
    """Make authenticated request to JupyterHub API."""
    headers = kwargs.pop("headers", {})
    if JUPYTERHUB_TOKEN:
        headers["Authorization"] = f"token {JUPYTERHUB_TOKEN}"
    
    async with httpx.AsyncClient(base_url=JUPYTERHUB_URL, timeout=30.0) as client:
        response = await client.request(method, path, headers=headers, **kwargs)
        return response


def _get_current_user() -> str:
    """Get current user. Placeholder for auth integration."""
    return os.getenv("JUPYTER_USER", "default")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/notebooks", response_model=NotebookListResponse)
async def list_notebooks(
    path: str = Query("", description="Subdirectory to list"),
    include_templates: bool = Query(True, description="Include template notebooks"),
):
    """List available notebooks in the workspace."""
    from pathlib import Path
    
    notebook_root = Path(NOTEBOOK_DIR)
    search_path = notebook_root / path if path else notebook_root
    
    if not search_path.exists():
        return NotebookListResponse(notebooks=[], total=0)
    
    notebooks = []
    
    for nb_path in search_path.rglob("*.ipynb"):
        # Skip checkpoints
        if ".ipynb_checkpoints" in str(nb_path):
            continue
        
        is_template = "template" in nb_path.name.lower() or "templates" in str(nb_path)
        
        if not include_templates and is_template:
            continue
        
        stat = nb_path.stat()
        rel_path = str(nb_path.relative_to(notebook_root))
        
        notebooks.append(NotebookInfo(
            name=nb_path.name,
            path=rel_path,
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            is_template=is_template,
        ))
    
    # Sort by modified time, newest first
    notebooks.sort(key=lambda n: n.modified_at or "", reverse=True)
    
    return NotebookListResponse(notebooks=notebooks, total=len(notebooks))


@router.get("/templates", response_model=List[TemplateInfo])
async def list_templates():
    """List available notebook templates."""
    # Predefined templates for common pipeline tasks
    templates = [
        TemplateInfo(
            name="source_analysis",
            description="Analyze a detected source with lightcurve and variability metrics",
            path="templates/source_analysis.ipynb",
            parameters=["source_id", "time_range"],
            tags=["sources", "analysis"],
        ),
        TemplateInfo(
            name="image_qa",
            description="Quality assessment for pipeline images",
            path="templates/image_qa.ipynb",
            parameters=["image_id"],
            tags=["images", "qa"],
        ),
        TemplateInfo(
            name="calibration_check",
            description="Validate calibration solutions and flag issues",
            path="templates/calibration_check.ipynb",
            parameters=["ms_path", "caltable_path"],
            tags=["calibration", "qa"],
        ),
        TemplateInfo(
            name="rfi_analysis",
            description="Analyze RFI patterns in observation data",
            path="templates/rfi_analysis.ipynb",
            parameters=["ms_path"],
            tags=["rfi", "analysis"],
        ),
        TemplateInfo(
            name="mosaic_planning",
            description="Plan and preview mosaic coverage",
            path="templates/mosaic_planning.ipynb",
            parameters=["dec_strip", "date_range"],
            tags=["mosaics", "planning"],
        ),
    ]
    
    return templates


@router.get("/status", response_model=ServerStatus)
async def get_server_status():
    """Get JupyterHub server status for current user."""
    user = _get_current_user()
    
    try:
        response = await _hub_request("GET", f"/hub/api/users/{user}")
        
        if response.status_code == 404:
            return ServerStatus(running=False)
        
        response.raise_for_status()
        data = response.json()
        
        server = data.get("servers", {}).get("", {})
        
        return ServerStatus(
            running=server.get("ready", False),
            url=server.get("url"),
            last_activity=server.get("last_activity"),
            started_at=server.get("started"),
            pending=server.get("pending"),
        )
        
    except httpx.HTTPError as e:
        logger.warning(f"JupyterHub API error: {e}")
        # Return mock status if hub unavailable
        return ServerStatus(
            running=False,
            pending=None,
        )


@router.post("/launch", response_model=LaunchResponse)
async def launch_notebook(request: LaunchRequest):
    """Launch a notebook in JupyterHub."""
    user = _get_current_user()
    
    # Ensure server is running
    try:
        status = await get_server_status()
        
        if not status.running and not status.pending:
            # Start server
            response = await _hub_request("POST", f"/hub/api/users/{user}/server")
            if response.status_code not in (201, 202):
                logger.warning(f"Failed to start server: {response.status_code}")
        
        # Build notebook URL
        base_url = f"{JUPYTERHUB_URL}/user/{user}"
        
        if request.notebook_path:
            notebook_url = f"{base_url}/notebooks/{request.notebook_path}"
        elif request.template_name:
            # Copy template to user workspace and open
            notebook_url = f"{base_url}/notebooks/templates/{request.template_name}.ipynb"
        else:
            # Just open JupyterLab
            notebook_url = f"{base_url}/lab"
        
        return LaunchResponse(
            success=True,
            url=notebook_url,
            message="Notebook launched successfully",
        )
        
    except Exception as e:
        logger.error(f"Failed to launch notebook: {e}")
        return LaunchResponse(
            success=False,
            url=f"{JUPYTERHUB_URL}/hub/login",
            message=f"Failed to launch: {e}",
        )


@router.post("/server/start", response_model=ServerStatus)
async def start_server():
    """Start JupyterHub server for current user."""
    user = _get_current_user()
    
    try:
        response = await _hub_request("POST", f"/hub/api/users/{user}/server")
        
        if response.status_code in (201, 202):
            return ServerStatus(running=False, pending="spawn")
        elif response.status_code == 400:
            # Already running
            return await get_server_status()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to start server: {response.text}",
            )
            
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"JupyterHub unavailable: {e}")


@router.post("/server/stop", response_model=ServerStatus)
async def stop_server():
    """Stop JupyterHub server for current user."""
    user = _get_current_user()
    
    try:
        response = await _hub_request("DELETE", f"/hub/api/users/{user}/server")
        
        if response.status_code in (202, 204):
            return ServerStatus(running=False, pending="stop")
        elif response.status_code == 404:
            return ServerStatus(running=False)
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to stop server: {response.text}",
            )
            
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"JupyterHub unavailable: {e}")


@router.get("/health")
async def jupyter_health():
    """Check JupyterHub availability."""
    try:
        response = await _hub_request("GET", "/hub/api/")
        
        return {
            "hub_available": response.status_code == 200,
            "hub_url": JUPYTERHUB_URL,
            "notebook_dir": NOTEBOOK_DIR,
        }
        
    except httpx.HTTPError:
        return {
            "hub_available": False,
            "hub_url": JUPYTERHUB_URL,
            "notebook_dir": NOTEBOOK_DIR,
        }

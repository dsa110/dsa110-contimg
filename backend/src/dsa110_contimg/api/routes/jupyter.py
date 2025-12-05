"""
Jupyter Integration API routes.

Direct proxy to Jupyter Server for kernel and notebook management.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jupyter", tags=["jupyter"])

# Configuration - connects to local Jupyter server
JUPYTER_SERVER_URL = os.getenv("JUPYTER_SERVER_URL", "http://localhost:8888")
JUPYTER_TOKEN = os.getenv("JUPYTER_TOKEN", "")  # Empty if no auth
NOTEBOOK_DIR = os.getenv("JUPYTER_NOTEBOOK_DIR", "/data/dsa110-contimg/notebooks")


# ============================================================================
# Pydantic Models (matching frontend expectations)
# ============================================================================


class JupyterKernel(BaseModel):
    """Kernel information matching frontend types."""

    id: str
    name: str
    display_name: str = ""
    language: str = "python"
    status: str = "idle"  # idle, busy, starting, error, dead
    last_activity: str = ""
    execution_count: int = 0
    connections: int = 0


class JupyterNotebook(BaseModel):
    """Notebook information matching frontend types."""

    id: str = ""
    name: str
    path: str
    type: str = "notebook"  # notebook, file, directory
    created: str = ""
    last_modified: str = ""
    size: Optional[int] = None
    kernel_id: Optional[str] = None
    content_type: Optional[str] = None


class JupyterSession(BaseModel):
    """Session information matching frontend types."""

    id: str
    notebook: Dict[str, str]
    kernel: JupyterKernel
    created: str = ""


class NotebookTemplate(BaseModel):
    """Notebook template for quick-start analysis."""

    id: str
    name: str
    description: str
    category: str = "custom"
    parameters: List[Dict[str, Any]] = Field(default_factory=list)


class LaunchNotebookRequest(BaseModel):
    """Request to launch a notebook from template."""

    template_id: str
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    kernel_name: str = "python3"


class JupyterStats(BaseModel):
    """Jupyter server statistics."""

    total_notebooks: int = 0
    active_kernels: int = 0
    total_sessions: int = 0
    kernel_usage: Dict[str, int] = Field(default_factory=dict)
    disk_usage_mb: float = 0
    max_disk_mb: float = 10000


# ============================================================================
# Jupyter Server Client
# ============================================================================


async def _jupyter_request(
    method: str,
    path: str,
    **kwargs,
) -> httpx.Response:
    """Make request to Jupyter server."""
    headers = kwargs.pop("headers", {})
    if JUPYTER_TOKEN:
        headers["Authorization"] = f"token {JUPYTER_TOKEN}"

    async with httpx.AsyncClient(base_url=JUPYTER_SERVER_URL, timeout=30.0) as client:
        try:
            response = await client.request(method, path, headers=headers, **kwargs)
            return response
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Jupyter server is not available. Please start it with: jupyter lab --no-browser --port=8888",
            )


# ============================================================================
# Kernel Endpoints
# ============================================================================


@router.get("/kernels", response_model=List[JupyterKernel])
async def list_kernels():
    """List all running kernels."""
    response = await _jupyter_request("GET", "/api/kernels")

    if response.status_code != 200:
        return []

    kernels_data = response.json()
    kernels = []

    for k in kernels_data:
        kernels.append(
            JupyterKernel(
                id=k.get("id", ""),
                name=k.get("name", "unknown"),
                display_name=k.get("name", "Python 3"),
                language=k.get("name", "python").replace("3", ""),  # "python3" -> "python"
                status=k.get("execution_state", "idle"),
                last_activity=k.get("last_activity", ""),
                execution_count=k.get("execution_count", 0) or 0,
                connections=k.get("connections", 0) or 0,
            )
        )

    return kernels


@router.get("/kernels/{kernel_id}", response_model=JupyterKernel)
async def get_kernel(kernel_id: str = Path(..., description="Kernel ID")):
    """Get information about a specific kernel."""
    response = await _jupyter_request("GET", f"/api/kernels/{kernel_id}")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Kernel not found")

    response.raise_for_status()
    k = response.json()

    return JupyterKernel(
        id=k.get("id", ""),
        name=k.get("name", "unknown"),
        display_name=k.get("name", "Python 3"),
        language=k.get("name", "python").replace("3", ""),
        status=k.get("execution_state", "idle"),
        last_activity=k.get("last_activity", ""),
        execution_count=k.get("execution_count", 0) or 0,
        connections=k.get("connections", 0) or 0,
    )


@router.post("/kernels", response_model=JupyterKernel)
async def start_kernel(request: Dict[str, str]):
    """Start a new kernel."""
    kernel_name = request.get("name", "python3")

    response = await _jupyter_request("POST", "/api/kernels", json={"name": kernel_name})

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code, detail=f"Failed to start kernel: {response.text}"
        )

    k = response.json()

    return JupyterKernel(
        id=k.get("id", ""),
        name=k.get("name", kernel_name),
        display_name=kernel_name,
        language="python",
        status=k.get("execution_state", "starting"),
        last_activity=k.get("last_activity", ""),
        execution_count=0,
        connections=0,
    )


@router.post("/kernels/{kernel_id}/restart")
async def restart_kernel(kernel_id: str = Path(..., description="Kernel ID")):
    """Restart a kernel."""
    response = await _jupyter_request("POST", f"/api/kernels/{kernel_id}/restart")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Kernel not found")

    response.raise_for_status()
    return {"status": "restarting"}


@router.post("/kernels/{kernel_id}/interrupt")
async def interrupt_kernel(kernel_id: str = Path(..., description="Kernel ID")):
    """Interrupt a kernel's execution."""
    response = await _jupyter_request("POST", f"/api/kernels/{kernel_id}/interrupt")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Kernel not found")

    response.raise_for_status()
    return {"status": "interrupted"}


@router.delete("/kernels/{kernel_id}")
async def shutdown_kernel(kernel_id: str = Path(..., description="Kernel ID")):
    """Shutdown a kernel."""
    response = await _jupyter_request("DELETE", f"/api/kernels/{kernel_id}")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Kernel not found")

    response.raise_for_status()
    return {"status": "shutdown"}


# ============================================================================
# Notebook Endpoints
# ============================================================================


@router.get("/notebooks", response_model=List[JupyterNotebook])
async def list_notebooks(path: str = Query("", description="Directory path")):
    """List notebooks in the workspace."""
    response = await _jupyter_request("GET", f"/api/contents/{path}")

    if response.status_code != 200:
        return []

    data = response.json()
    notebooks = []

    # Handle both single item and directory listing
    contents = data.get("content", []) if data.get("type") == "directory" else [data]

    for item in contents:
        if item.get("type") in ("notebook", "file", "directory"):
            notebooks.append(
                JupyterNotebook(
                    id=item.get("path", ""),
                    name=item.get("name", ""),
                    path=item.get("path", ""),
                    type=item.get("type", "file"),
                    created=item.get("created", ""),
                    last_modified=item.get("last_modified", ""),
                    size=item.get("size"),
                    content_type=item.get("mimetype"),
                )
            )

    # Filter to show mostly notebooks, but include directories
    notebooks = [nb for nb in notebooks if nb.type in ("notebook", "directory")]

    return notebooks


@router.get("/notebooks/{notebook_path:path}", response_model=JupyterNotebook)
async def get_notebook(notebook_path: str):
    """Get notebook metadata."""
    response = await _jupyter_request("GET", f"/api/contents/{notebook_path}")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Notebook not found")

    response.raise_for_status()
    item = response.json()

    return JupyterNotebook(
        id=item.get("path", ""),
        name=item.get("name", ""),
        path=item.get("path", ""),
        type=item.get("type", "notebook"),
        created=item.get("created", ""),
        last_modified=item.get("last_modified", ""),
        size=item.get("size"),
    )


@router.delete("/notebooks/{notebook_path:path}")
async def delete_notebook(notebook_path: str):
    """Delete a notebook."""
    response = await _jupyter_request("DELETE", f"/api/contents/{notebook_path}")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Notebook not found")

    response.raise_for_status()
    return {"status": "deleted"}


# ============================================================================
# Session Endpoints
# ============================================================================


@router.get("/sessions", response_model=List[JupyterSession])
async def list_sessions():
    """List all active sessions."""
    response = await _jupyter_request("GET", "/api/sessions")

    if response.status_code != 200:
        return []

    sessions_data = response.json()
    sessions = []

    for s in sessions_data:
        kernel_data = s.get("kernel", {})
        sessions.append(
            JupyterSession(
                id=s.get("id", ""),
                notebook={
                    "name": s.get("notebook", {}).get("name", "") or s.get("name", ""),
                    "path": s.get("notebook", {}).get("path", "") or s.get("path", ""),
                },
                kernel=JupyterKernel(
                    id=kernel_data.get("id", ""),
                    name=kernel_data.get("name", "python3"),
                    display_name=kernel_data.get("name", "Python 3"),
                    language="python",
                    status=kernel_data.get("execution_state", "idle"),
                    last_activity=kernel_data.get("last_activity", ""),
                    execution_count=kernel_data.get("execution_count", 0) or 0,
                    connections=kernel_data.get("connections", 0) or 0,
                ),
                created=s.get("started", ""),
            )
        )

    return sessions


@router.post("/sessions", response_model=JupyterSession)
async def create_session(request: Dict[str, Any]):
    """Create a new session with a notebook and kernel."""
    response = await _jupyter_request(
        "POST",
        "/api/sessions",
        json={
            "path": request.get("path", "Untitled.ipynb"),
            "name": request.get("name", "Untitled"),
            "type": "notebook",
            "kernel": {"name": request.get("kernel_name", "python3")},
        },
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code, detail=f"Failed to create session: {response.text}"
        )

    s = response.json()
    kernel_data = s.get("kernel", {})

    return JupyterSession(
        id=s.get("id", ""),
        notebook={
            "name": s.get("notebook", {}).get("name", ""),
            "path": s.get("notebook", {}).get("path", ""),
        },
        kernel=JupyterKernel(
            id=kernel_data.get("id", ""),
            name=kernel_data.get("name", "python3"),
            display_name="Python 3",
            language="python",
            status=kernel_data.get("execution_state", "starting"),
            last_activity="",
            execution_count=0,
            connections=0,
        ),
        created=s.get("started", ""),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str = Path(..., description="Session ID")):
    """Delete a session."""
    response = await _jupyter_request("DELETE", f"/api/sessions/{session_id}")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Session not found")

    response.raise_for_status()
    return {"status": "deleted"}


# ============================================================================
# Template Endpoints
# ============================================================================


@router.get("/templates", response_model=List[NotebookTemplate])
async def list_templates():
    """List available notebook templates."""
    templates = [
        NotebookTemplate(
            id="source_analysis",
            name="Source Analysis",
            description="Analyze a detected source with lightcurve and variability metrics",
            category="source_analysis",
            parameters=[
                {
                    "name": "source_id",
                    "type": "source_id",
                    "required": True,
                    "description": "ID of the source to analyze",
                },
                {
                    "name": "time_range",
                    "type": "string",
                    "required": False,
                    "description": "Time range for analysis",
                },
            ],
        ),
        NotebookTemplate(
            id="image_qa",
            name="Image QA",
            description="Quality assessment for pipeline images",
            category="image_inspection",
            parameters=[
                {
                    "name": "image_id",
                    "type": "image_id",
                    "required": True,
                    "description": "ID of the image to inspect",
                },
            ],
        ),
        NotebookTemplate(
            id="calibration_check",
            name="Calibration Check",
            description="Validate calibration solutions and flag issues",
            category="data_exploration",
            parameters=[
                {
                    "name": "ms_path",
                    "type": "string",
                    "required": True,
                    "description": "Path to measurement set",
                },
            ],
        ),
        NotebookTemplate(
            id="rfi_analysis",
            name="RFI Analysis",
            description="Analyze RFI patterns in observation data",
            category="data_exploration",
            parameters=[
                {
                    "name": "ms_path",
                    "type": "string",
                    "required": True,
                    "description": "Path to measurement set",
                },
            ],
        ),
        NotebookTemplate(
            id="custom_notebook",
            name="Custom Notebook",
            description="Start with a blank notebook",
            category="custom",
            parameters=[],
        ),
    ]
    return templates


@router.post("/launch")
async def launch_notebook(request: LaunchNotebookRequest):
    """Launch a notebook from a template."""
    # Create a new notebook with the template content
    notebook_name = f"{request.name}.ipynb"

    # Create a session with the new notebook
    session_response = await _jupyter_request(
        "POST",
        "/api/sessions",
        json={
            "path": notebook_name,
            "name": request.name,
            "type": "notebook",
            "kernel": {"name": request.kernel_name},
        },
    )

    if session_response.status_code not in (200, 201):
        raise HTTPException(
            status_code=session_response.status_code,
            detail=f"Failed to create notebook: {session_response.text}",
        )

    session_data = session_response.json()

    return {
        "success": True,
        "url": f"{JUPYTER_SERVER_URL}/notebooks/{notebook_name}",
        "session_id": session_data.get("id"),
        "kernel_id": session_data.get("kernel", {}).get("id"),
    }


# ============================================================================
# Stats & URL Endpoints
# ============================================================================


@router.get("/stats", response_model=JupyterStats)
async def get_stats():
    """Get Jupyter server statistics."""
    kernels_response = await _jupyter_request("GET", "/api/kernels")
    sessions_response = await _jupyter_request("GET", "/api/sessions")
    notebooks_response = await _jupyter_request("GET", "/api/contents")

    kernels = kernels_response.json() if kernels_response.status_code == 200 else []
    sessions = sessions_response.json() if sessions_response.status_code == 200 else []
    contents = notebooks_response.json() if notebooks_response.status_code == 200 else {}

    # Count notebooks
    notebook_count = 0
    if contents.get("type") == "directory":
        for item in contents.get("content", []):
            if item.get("type") == "notebook":
                notebook_count += 1

    # Count kernel types
    kernel_usage = {}
    for k in kernels:
        name = k.get("name", "python3")
        kernel_usage[name] = kernel_usage.get(name, 0) + 1

    return JupyterStats(
        total_notebooks=notebook_count,
        active_kernels=len(kernels),
        total_sessions=len(sessions),
        kernel_usage=kernel_usage,
        disk_usage_mb=0,  # Would need filesystem check
        max_disk_mb=10000,
    )


@router.get("/url")
async def get_jupyter_url():
    """Get the Jupyter server URL for direct access."""
    return {"url": JUPYTER_SERVER_URL}


@router.get("/health")
async def jupyter_health():
    """Check Jupyter server availability."""
    try:
        response = await _jupyter_request("GET", "/api/status")

        return {
            "available": response.status_code == 200,
            "server_url": JUPYTER_SERVER_URL,
            "notebook_dir": NOTEBOOK_DIR,
        }
    except HTTPException:
        return {
            "available": False,
            "server_url": JUPYTER_SERVER_URL,
            "notebook_dir": NOTEBOOK_DIR,
        }

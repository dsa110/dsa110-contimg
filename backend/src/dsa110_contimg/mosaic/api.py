"""
FastAPI endpoints for mosaic operations.

Two endpoints:
- POST /api/mosaic/create - Start mosaic creation
- GET /api/mosaic/status/{name} - Check status
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mosaic", tags=["mosaic"])


class MosaicRequest(BaseModel):
    """Request to create a mosaic."""

    name: str = Field(..., description="Unique name for the mosaic")
    start_time: int = Field(..., description="Start time (Unix timestamp)")
    end_time: int = Field(..., description="End time (Unix timestamp)")
    tier: str = Field(default="science", description="Mosaic tier: quicklook, science, or deep")


class MosaicResponse(BaseModel):
    """Response for mosaic creation request."""

    status: str
    execution_id: str | None = None
    message: str


class MosaicStatusResponse(BaseModel):
    """Response for mosaic status query."""

    name: str
    status: str
    tier: str
    n_images: int
    mosaic_path: str | None = None
    qa_status: str | None = None
    created_at: int | None = None


# Configuration - will be set by app startup
_config: dict[str, Any] = {}


def configure_mosaic_api(
    database_path: Path,
    mosaic_dir: Path,
    images_table: str = "images",
) -> None:
    """Configure the mosaic API with paths.

    Args:
        database_path: Path to the unified database
        mosaic_dir: Directory for output mosaics
        images_table: Name of the images table
    """
    global _config
    _config = {
        "database_path": database_path,
        "mosaic_dir": mosaic_dir,
        "images_table": images_table,
    }
    logger.info(f"Mosaic API configured: db={database_path}, dir={mosaic_dir}")


def _get_config() -> dict[str, Any]:
    """Get current configuration."""
    if not _config:
        raise HTTPException(
            status_code=500, detail="Mosaic API not configured. Call configure_mosaic_api() first."
        )
    return _config


@router.post("/create", response_model=MosaicResponse)
async def create_mosaic(request: MosaicRequest) -> MosaicResponse:
    """Create a mosaic from a time range.

    This is the ONLY mosaic creation endpoint. Simple API.

    The mosaic will be created asynchronously. Use the status endpoint
    to check progress and get the result.

    Args:
        request: Mosaic creation request with name, time range, and tier

    Returns:
        Response with execution status

    Raises:
        HTTPException: If request is invalid or creation fails
    """
    config = _get_config()

    # Validate time range
    if request.end_time <= request.start_time:
        raise HTTPException(
            status_code=400, detail="Invalid time range: end_time must be after start_time"
        )

    # Validate tier
    valid_tiers = ["quicklook", "science", "deep"]
    if request.tier.lower() not in valid_tiers:
        raise HTTPException(
            status_code=400, detail=f"Invalid tier: {request.tier}. Must be one of: {valid_tiers}"
        )

    # Check if name already exists
    try:
        conn = sqlite3.connect(str(config["database_path"]))
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("SELECT id FROM mosaic_plans WHERE name = ?", (request.name,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            raise HTTPException(
                status_code=409, detail=f"Mosaic with name '{request.name}' already exists"
            )

        conn.close()
    except sqlite3.Error as e:
        logger.warning(f"Database check failed: {e}")
        # Continue anyway - the pipeline will handle duplicates

    # Start pipeline asynchronously
    try:
        # For now, execute synchronously in background
        # In production, would spawn ABSURD task
        import asyncio

        params = {
            "database_path": str(config["database_path"]),
            "mosaic_dir": str(config["mosaic_dir"]),
            "images_table": config["images_table"],
            "name": request.name,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "tier": request.tier.lower(),
        }

        # Create background task
        asyncio.create_task(_run_mosaic_background(params))

        return MosaicResponse(
            status="accepted",
            execution_id=request.name,
            message=f"Mosaic creation started: {request.name}",
        )

    except Exception as e:
        logger.exception(f"Failed to start mosaic creation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start mosaic creation: {e}")


async def _run_mosaic_background(params: dict[str, Any]) -> None:
    """Run mosaic pipeline in background."""
    from .pipeline import execute_mosaic_pipeline_task

    try:
        result = await execute_mosaic_pipeline_task(params)
        logger.info(f"Background mosaic complete: {result}")
    except Exception as e:
        logger.exception(f"Background mosaic failed: {e}")


@router.get("/status/{name}", response_model=MosaicStatusResponse)
async def get_mosaic_status(name: str) -> MosaicStatusResponse:
    """Query mosaic build status.

    Args:
        name: Mosaic name to query

    Returns:
        Status response with current state and results

    Raises:
        HTTPException: If mosaic not found
    """
    config = _get_config()

    try:
        conn = sqlite3.connect(str(config["database_path"]))
        conn.row_factory = sqlite3.Row

        # Get plan
        cursor = conn.execute("SELECT * FROM mosaic_plans WHERE name = ?", (name,))
        plan = cursor.fetchone()

        if not plan:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Mosaic '{name}' not found")

        # Get mosaic if completed
        mosaic = None
        if plan["status"] == "completed":
            cursor = conn.execute("SELECT * FROM mosaics WHERE plan_id = ?", (plan["id"],))
            mosaic = cursor.fetchone()

        conn.close()

        return MosaicStatusResponse(
            name=name,
            status=plan["status"],
            tier=plan["tier"],
            n_images=plan["n_images"],
            mosaic_path=mosaic["path"] if mosaic else None,
            qa_status=mosaic["qa_status"] if mosaic else None,
            created_at=plan["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get mosaic status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get mosaic status: {e}")


@router.get("/list")
async def list_mosaics(
    tier: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List mosaics with optional filtering.

    Args:
        tier: Filter by tier (quicklook, science, deep)
        status: Filter by status (pending, building, completed, failed)
        limit: Maximum number of results

    Returns:
        List of mosaic records
    """
    config = _get_config()

    try:
        conn = sqlite3.connect(str(config["database_path"]))
        conn.row_factory = sqlite3.Row

        # Build query
        query = "SELECT * FROM mosaic_plans WHERE 1=1"
        params = []

        if tier:
            query += " AND tier = ?"
            params.append(tier.lower())

        if status:
            query += " AND status = ?"
            params.append(status.lower())

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        plans = cursor.fetchall()

        # Get mosaic details for completed plans
        results = []
        for plan in plans:
            record = dict(plan)

            if plan["status"] == "completed":
                cursor = conn.execute(
                    "SELECT path, qa_status FROM mosaics WHERE plan_id = ?", (plan["id"],)
                )
                mosaic = cursor.fetchone()
                if mosaic:
                    record["mosaic_path"] = mosaic["path"]
                    record["qa_status"] = mosaic["qa_status"]

            # Parse image_ids JSON
            record["image_ids"] = json.loads(record.get("image_ids", "[]"))

            results.append(record)

        conn.close()
        return results

    except Exception as e:
        logger.exception(f"Failed to list mosaics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list mosaics: {e}")


@router.delete("/{name}")
async def delete_mosaic(name: str, delete_file: bool = False) -> dict[str, str]:
    """Delete a mosaic record (and optionally the file).

    Args:
        name: Mosaic name to delete
        delete_file: Whether to also delete the FITS file

    Returns:
        Confirmation message
    """
    config = _get_config()

    try:
        conn = sqlite3.connect(str(config["database_path"]))
        conn.row_factory = sqlite3.Row

        # Get plan
        cursor = conn.execute("SELECT * FROM mosaic_plans WHERE name = ?", (name,))
        plan = cursor.fetchone()

        if not plan:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Mosaic '{name}' not found")

        plan_id = plan["id"]

        # Get mosaic record if exists
        cursor = conn.execute("SELECT * FROM mosaics WHERE plan_id = ?", (plan_id,))
        mosaic = cursor.fetchone()

        # Delete file if requested
        if delete_file and mosaic and mosaic["path"]:
            mosaic_path = Path(mosaic["path"])
            if mosaic_path.exists():
                mosaic_path.unlink()
                logger.info(f"Deleted mosaic file: {mosaic_path}")

        # Delete database records
        if mosaic:
            conn.execute("DELETE FROM mosaic_qa WHERE mosaic_id = ?", (mosaic["id"],))
            conn.execute("DELETE FROM mosaics WHERE id = ?", (mosaic["id"],))

        conn.execute("DELETE FROM mosaic_plans WHERE id = ?", (plan_id,))

        conn.commit()
        conn.close()

        return {"message": f"Deleted mosaic: {name}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete mosaic: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete mosaic: {e}")

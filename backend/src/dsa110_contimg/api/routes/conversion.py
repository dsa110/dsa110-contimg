"""
Conversion routes for HDF5 → Measurement Set conversion.

Provides endpoints for:
- Listing pending subband groups
- Triggering on-demand conversion
- Checking conversion status
- Managing the conversion queue

This enables dashboard-driven conversion alongside calibration, imaging, etc.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import require_write_access, AuthContext
from ..dependencies import get_pipeline_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversion", tags=["conversion"])


# =============================================================================
# Pydantic Models
# =============================================================================


class SubbandGroup(BaseModel):
    """A group of HDF5 subband files pending conversion."""

    group_id: str = Field(..., description="Group identifier (timestamp)")
    file_count: int = Field(..., description="Number of subband files")
    expected_subbands: int = Field(default=16, description="Expected subbands per group")
    is_complete: bool = Field(..., description="Whether all subbands are present")
    first_seen: Optional[str] = Field(None, description="When first file arrived")
    files: Optional[List[str]] = Field(None, description="List of file paths (if requested)")

    class Config:
        json_schema_extra = {
            "example": {
                "group_id": "2025-10-02T00:05:18",
                "file_count": 16,
                "expected_subbands": 16,
                "is_complete": True,
                "first_seen": "2025-10-02T00:05:20",
            }
        }


class PendingGroupsResponse(BaseModel):
    """Response listing pending subband groups."""

    groups: List[SubbandGroup]
    total: int
    complete_count: int
    incomplete_count: int


class ConversionRequest(BaseModel):
    """Request to convert specific subband groups."""

    group_ids: List[str] = Field(..., min_length=1, description="Group IDs to convert")
    output_dir: Optional[str] = Field(None, description="Custom output directory")
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")

    class Config:
        json_schema_extra = {
            "example": {
                "group_ids": ["2025-10-02T00:05:18", "2025-10-02T00:10:22"],
                "output_dir": "/data/ms",
                "priority": "normal",
            }
        }


class ConversionJobResponse(BaseModel):
    """Response after queuing conversion job."""

    job_id: str
    group_ids: List[str]
    status: str
    message: str


class ConversionStatus(BaseModel):
    """Status of a conversion job or group."""

    group_id: str
    status: str  # pending, converting, converted, failed
    ms_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ConversionStatsResponse(BaseModel):
    """Conversion pipeline statistics."""

    total_pending: int
    total_converting: int
    total_converted_today: int
    total_failed_today: int
    avg_conversion_time_s: Optional[float] = None
    oldest_pending_group: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def _get_processing_queue_db() -> str:
    """Get path to the processing queue database."""
    from dsa110_contimg.config import settings
    return str(settings.database.unified_db)


def _get_hdf5_index_db() -> str:
    """Get path to the HDF5 file index database."""
    from dsa110_contimg.config import settings
    # Default location in input_dir
    default_path = os.path.join(str(settings.paths.input_dir), "hdf5_file_index.sqlite3")
    if os.path.exists(default_path):
        return default_path
    # Fallback to /data/incoming
    fallback = "/data/incoming/hdf5_file_index.sqlite3"
    return fallback if os.path.exists(fallback) else default_path


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/pending", response_model=PendingGroupsResponse)
async def list_pending_groups(
    limit: int = Query(50, le=200, description="Maximum groups to return"),
    complete_only: bool = Query(False, description="Only return complete groups"),
    include_files: bool = Query(False, description="Include file paths in response"),
    since_hours: int = Query(24, le=168, description="Look back period in hours"),
):
    """
    List HDF5 subband groups pending conversion.

    Groups are identified by timestamp and may have 1-16 subbands.
    Complete groups (16 subbands) are ready for conversion.
    """
    db_path = _get_processing_queue_db()

    if not os.path.exists(db_path):
        return PendingGroupsResponse(
            groups=[], total=0, complete_count=0, incomplete_count=0
        )

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row

        # Query pending groups from processing_queue
        # Note: received_at is Unix timestamp, convert since_hours to seconds
        since_ts = (datetime.utcnow() - timedelta(hours=since_hours)).timestamp()

        cursor = conn.execute(
            """
            SELECT
                pq.group_id,
                COUNT(sf.path) as file_count,
                pq.received_at as first_seen,
                GROUP_CONCAT(sf.path) as file_paths
            FROM processing_queue pq
            LEFT JOIN subband_files sf ON pq.group_id = sf.group_id
            WHERE pq.state = 'pending'
              AND pq.received_at >= ?
            GROUP BY pq.group_id
            ORDER BY pq.received_at DESC
            LIMIT ?
            """,
            (since_ts, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        groups = []
        complete_count = 0
        incomplete_count = 0

        for row in rows:
            is_complete = row["file_count"] >= 16
            if complete_only and not is_complete:
                continue

            if is_complete:
                complete_count += 1
            else:
                incomplete_count += 1

            # Convert Unix timestamp to ISO format
            first_seen_str = None
            if row["first_seen"]:
                first_seen_str = datetime.fromtimestamp(row["first_seen"]).isoformat()

            group = SubbandGroup(
                group_id=row["group_id"],
                file_count=row["file_count"],
                expected_subbands=16,
                is_complete=is_complete,
                first_seen=first_seen_str,
                files=row["file_paths"].split(",") if include_files and row["file_paths"] else None,
            )
            groups.append(group)

        return PendingGroupsResponse(
            groups=groups,
            total=len(groups),
            complete_count=complete_count,
            incomplete_count=incomplete_count,
        )

    except sqlite3.Error as e:
        logger.error(f"Database error listing pending groups: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/stats", response_model=ConversionStatsResponse)
async def get_conversion_stats():
    """
    Get conversion pipeline statistics.

    Returns counts of pending, converting, converted, and failed groups.
    """
    db_path = _get_processing_queue_db()

    if not os.path.exists(db_path):
        return ConversionStatsResponse(
            total_pending=0,
            total_converting=0,
            total_converted_today=0,
            total_failed_today=0,
        )

    try:
        conn = sqlite3.connect(db_path, timeout=10)

        # Count by state
        cursor = conn.execute(
            """
            SELECT state, COUNT(*) as count
            FROM processing_queue
            GROUP BY state
            """
        )
        state_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Count completed/failed today (last_update within today)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        cursor = conn.execute(
            """
            SELECT state, COUNT(*) as count
            FROM processing_queue
            WHERE last_update >= ?
              AND state IN ('completed', 'failed')
            GROUP BY state
            """,
            (today_start,),
        )
        today_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Get oldest pending group
        cursor = conn.execute(
            """
            SELECT group_id FROM processing_queue
            WHERE state = 'pending'
            ORDER BY received_at ASC
            LIMIT 1
            """
        )
        oldest = cursor.fetchone()

        conn.close()

        return ConversionStatsResponse(
            total_pending=state_counts.get("pending", 0),
            total_converting=state_counts.get("converting", 0),
            total_converted_today=today_counts.get("converted", 0),
            total_failed_today=today_counts.get("failed", 0),
            oldest_pending_group=oldest[0] if oldest else None,
        )

    except sqlite3.Error as e:
        logger.error(f"Database error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/convert", response_model=ConversionJobResponse)
async def trigger_conversion(
    request: ConversionRequest,
    auth: AuthContext = Depends(require_write_access),
):
    """
    Trigger conversion of specified subband groups.

    Queues a background job to convert HDF5 files to Measurement Sets.
    Requires write access.
    """
    from ..job_queue import job_queue

    # Validate group_ids exist
    db_path = _get_processing_queue_db()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Processing queue database not found")

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.execute(
            """
            SELECT DISTINCT group_id FROM processing_queue
            WHERE group_id IN ({})
              AND state = 'pending'
            """.format(",".join("?" * len(request.group_ids))),
            request.group_ids,
        )
        valid_groups = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not valid_groups:
            raise HTTPException(
                status_code=400,
                detail=f"No valid pending groups found: {request.group_ids}",
            )

        # Enqueue conversion job
        job_id = job_queue.enqueue(
            _execute_conversion_job,
            group_ids=valid_groups,
            output_dir=request.output_dir,
            priority=request.priority,
            meta={
                "type": "conversion",
                "group_count": len(valid_groups),
                "requested_by": auth.user_id if hasattr(auth, "user_id") else "api",
            },
        )

        return ConversionJobResponse(
            job_id=job_id,
            group_ids=valid_groups,
            status="queued",
            message=f"Conversion queued for {len(valid_groups)} group(s)",
        )

    except sqlite3.Error as e:
        logger.error(f"Database error triggering conversion: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/status/{group_id}", response_model=ConversionStatus)
async def get_group_status(group_id: str):
    """
    Get the conversion status of a specific group.
    """
    db_path = _get_processing_queue_db()

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Processing queue database not found")

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT
                group_id,
                state,
                error,
                received_at,
                last_update
            FROM processing_queue
            WHERE group_id = ?
            """,
            (group_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")

        # Convert timestamps
        started_at = datetime.fromtimestamp(row["received_at"]).isoformat() if row["received_at"] else None
        completed_at = datetime.fromtimestamp(row["last_update"]).isoformat() if row["last_update"] else None

        return ConversionStatus(
            group_id=row["group_id"],
            status=row["state"],
            ms_path=None,  # MS path not stored in processing_queue
            error_message=row["error"],
            started_at=started_at,
            completed_at=completed_at,
        )

    except sqlite3.Error as e:
        logger.error(f"Database error getting group status: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/hdf5-index")
async def list_hdf5_groups(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    limit: int = Query(50, le=500, description="Maximum groups to return"),
):
    """
    List subband groups from the HDF5 file index.

    This queries the raw HDF5 file index, not the processing queue.
    Useful for discovering files that haven't been queued yet.
    """
    db_path = _get_hdf5_index_db()

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="HDF5 index database not found")

    try:
        conn = sqlite3.connect(db_path, timeout=10)

        # Build query
        query = """
            SELECT
                timestamp,
                COUNT(*) as file_count,
                GROUP_CONCAT(subband) as subbands
            FROM hdf5_file_index
        """
        params: List[Any] = []

        if start_time or end_time:
            conditions = []
            if start_time:
                conditions.append("timestamp_iso >= ?")
                params.append(start_time)
            if end_time:
                conditions.append("timestamp_iso <= ?")
                params.append(end_time)
            query += " WHERE " + " AND ".join(conditions)

        query += """
            GROUP BY timestamp
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        groups = []
        for row in rows:
            groups.append({
                "group_id": row[0],
                "file_count": row[1],
                "subbands": row[2].split(",") if row[2] else [],
                "is_complete": row[1] >= 16,
            })

        return {"groups": groups, "total": len(groups)}

    except sqlite3.Error as e:
        logger.error(f"Database error listing HDF5 groups: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# =============================================================================
# Background Job Function
# =============================================================================


def _execute_conversion_job(
    group_ids: List[str],
    output_dir: Optional[str] = None,
    priority: str = "normal",
) -> Dict[str, Any]:
    """
    Execute conversion for the specified groups.

    This runs in the background via the job queue.
    """
    import time
    from pathlib import Path

    from dsa110_contimg.config import settings
    from dsa110_contimg.conversion.streaming.stages.conversion import (
        ConversionConfig,
        ConversionStage,
    )
    from dsa110_contimg.conversion.streaming.queue import SubbandQueue

    results = {
        "converted": [],
        "failed": [],
        "skipped": [],
    }

    # Get output directory
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = Path(settings.paths.ms_dir)

    out_path.mkdir(parents=True, exist_ok=True)

    # Initialize queue and stage
    queue = SubbandQueue(str(settings.database.pipeline_db))

    config = ConversionConfig(
        input_dir=Path(settings.paths.incoming_dir),
        output_dir=out_path,
        scratch_dir=Path(settings.paths.scratch_dir),
        expected_subbands=16,
    )
    stage = ConversionStage(config)

    for group_id in group_ids:
        try:
            # Get file paths for this group
            group_info = queue.get_group_info(group_id)
            if not group_info:
                results["skipped"].append({"group_id": group_id, "reason": "Not found"})
                continue

            file_paths = group_info.get("file_paths", [])
            if not file_paths:
                results["skipped"].append({"group_id": group_id, "reason": "No files"})
                continue

            # Mark as converting (in_progress)
            queue.update_state(group_id, "in_progress")

            # Execute conversion
            t0 = time.time()
            result = stage.execute(group_id=group_id, file_paths=file_paths)
            elapsed = time.time() - t0

            if result.success:
                queue.update_state(group_id, "completed")
                # Record metrics if available
                queue.record_metrics(
                    group_id,
                    total_time=elapsed,
                    writer_type=result.writer_type or "fallback",
                )
                results["converted"].append({
                    "group_id": group_id,
                    "ms_path": result.ms_path,
                    "elapsed_s": round(elapsed, 1),
                })
            else:
                queue.update_state(group_id, "failed", error=result.error_message)
                results["failed"].append({
                    "group_id": group_id,
                    "error": result.error_message,
                })

        except Exception as e:
            logger.exception(f"Conversion failed for {group_id}: {e}")
            try:
                queue.update_state(group_id, "failed", error=str(e)[:500])
            except Exception:
                pass
            results["failed"].append({
                "group_id": group_id,
                "error": str(e)[:200],
            })

    return results

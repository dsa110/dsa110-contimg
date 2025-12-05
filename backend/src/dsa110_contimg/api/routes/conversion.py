"""
Conversion routes for HDF5 → Measurement Set conversion.

Provides endpoints for:
- Listing pending subband groups
- Triggering on-demand conversion
- Checking conversion status
- Managing the conversion queue

Uses ABSURD PostgreSQL for ingestion queue management.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import AuthContext, require_write_access

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


async def _get_ingestion_pool():
    """Get the ABSURD ingestion PostgreSQL pool."""
    from dsa110_contimg.absurd.ingestion_db import get_ingestion_pool

    return await get_ingestion_pool()


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
    try:
        pool = await _get_ingestion_pool()
        since_time = datetime.utcnow() - timedelta(hours=since_hours)

        async with pool.acquire() as conn:
            # Query pending groups from ABSURD ingestion tables
            rows = await conn.fetch(
                """
                SELECT
                    g.group_id,
                    COUNT(s.subband_idx) as file_count,
                    g.created_at as first_seen,
                    ARRAY_AGG(s.file_path) as file_paths
                FROM absurd.ingestion_groups g
                LEFT JOIN absurd.ingestion_subbands s ON g.group_id = s.group_id
                WHERE g.state = 'pending'
                  AND g.created_at >= $1
                GROUP BY g.group_id, g.created_at
                ORDER BY g.created_at DESC
                LIMIT $2
                """,
                since_time,
                limit,
            )

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

            first_seen_str = row["first_seen"].isoformat() if row["first_seen"] else None
            file_list = list(row["file_paths"]) if include_files and row["file_paths"] else None

            group = SubbandGroup(
                group_id=row["group_id"],
                file_count=row["file_count"],
                expected_subbands=16,
                is_complete=is_complete,
                first_seen=first_seen_str,
                files=file_list,
            )
            groups.append(group)

        return PendingGroupsResponse(
            groups=groups,
            total=len(groups),
            complete_count=complete_count,
            incomplete_count=incomplete_count,
        )

    except Exception as e:
        logger.error(f"Database error listing pending groups: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/stats", response_model=ConversionStatsResponse)
async def get_conversion_stats():
    """
    Get conversion pipeline statistics.

    Returns counts of pending, converting, converted, and failed groups.
    """
    try:
        pool = await _get_ingestion_pool()

        async with pool.acquire() as conn:
            # Count by state
            state_rows = await conn.fetch(
                """
                SELECT state, COUNT(*) as count
                FROM absurd.ingestion_groups
                GROUP BY state
                """
            )
            state_counts = {row["state"]: row["count"] for row in state_rows}

            # Count completed/failed today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_rows = await conn.fetch(
                """
                SELECT state, COUNT(*) as count
                FROM absurd.ingestion_groups
                WHERE updated_at >= $1
                  AND state IN ('completed', 'failed')
                GROUP BY state
                """,
                today_start,
            )
            today_counts = {row["state"]: row["count"] for row in today_rows}

            # Get oldest pending group
            oldest = await conn.fetchrow(
                """
                SELECT group_id FROM absurd.ingestion_groups
                WHERE state = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )

        return ConversionStatsResponse(
            total_pending=state_counts.get("pending", 0),
            total_converting=state_counts.get("in_progress", 0),
            total_converted_today=today_counts.get("completed", 0),
            total_failed_today=today_counts.get("failed", 0),
            oldest_pending_group=oldest["group_id"] if oldest else None,
        )

    except Exception as e:
        logger.error(f"Database error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/convert", response_model=ConversionJobResponse)
async def trigger_conversion(
    request: ConversionRequest,
    auth: AuthContext = Depends(require_write_access),
):
    """
    Trigger conversion of specified subband groups.

    Queues an ABSURD task to convert HDF5 files to Measurement Sets.
    Requires write access.
    """
    from dsa110_contimg.absurd.client import get_absurd_client

    try:
        pool = await _get_ingestion_pool()

        async with pool.acquire() as conn:
            # Validate group_ids exist and are pending
            placeholders = ", ".join(f"${i + 1}" for i in range(len(request.group_ids)))
            valid_rows = await conn.fetch(
                f"""
                SELECT DISTINCT group_id FROM absurd.ingestion_groups
                WHERE group_id IN ({placeholders})
                  AND state = 'pending'
                """,
                *request.group_ids,
            )
            valid_groups = [row["group_id"] for row in valid_rows]

        if not valid_groups:
            raise HTTPException(
                status_code=400,
                detail=f"No valid pending groups found: {request.group_ids}",
            )

        # Enqueue ABSURD convert-group tasks
        client = get_absurd_client()
        task_ids = []
        for group_id in valid_groups:
            task_id = await client.enqueue(
                "convert-group",
                {"group_id": group_id, "output_dir": request.output_dir},
            )
            task_ids.append(task_id)

        return ConversionJobResponse(
            job_id=task_ids[0] if len(task_ids) == 1 else f"batch:{len(task_ids)}",
            group_ids=valid_groups,
            status="queued",
            message=f"Conversion queued for {len(valid_groups)} group(s)",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error triggering conversion: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/status/{group_id}", response_model=ConversionStatus)
async def get_group_status(group_id: str):
    """
    Get the conversion status of a specific group.
    """
    try:
        pool = await _get_ingestion_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    group_id,
                    state,
                    error_message,
                    created_at,
                    updated_at,
                    ms_path
                FROM absurd.ingestion_groups
                WHERE group_id = $1
                """,
                group_id,
            )

        if not row:
            raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")

        started_at = row["created_at"].isoformat() if row["created_at"] else None
        completed_at = row["updated_at"].isoformat() if row["updated_at"] else None

        return ConversionStatus(
            group_id=row["group_id"],
            status=row["state"],
            ms_path=row["ms_path"],
            error_message=row["error_message"],
            started_at=started_at,
            completed_at=completed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
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

    This queries the ABSURD ingestion tables for recorded subbands.
    """
    import sqlite3

    # First try ABSURD PostgreSQL
    try:
        pool = await _get_ingestion_pool()

        async with pool.acquire() as conn:
            # Build query for ABSURD ingestion tables
            if start_time and end_time:
                rows = await conn.fetch(
                    """
                    SELECT
                        g.group_id,
                        COUNT(s.subband_idx) as file_count,
                        ARRAY_AGG(s.subband_idx ORDER BY s.subband_idx) as subbands
                    FROM absurd.ingestion_groups g
                    LEFT JOIN absurd.ingestion_subbands s ON g.group_id = s.group_id
                    WHERE g.group_id >= $1 AND g.group_id <= $2
                    GROUP BY g.group_id
                    ORDER BY g.group_id DESC
                    LIMIT $3
                    """,
                    start_time,
                    end_time,
                    limit,
                )
            elif start_time:
                rows = await conn.fetch(
                    """
                    SELECT
                        g.group_id,
                        COUNT(s.subband_idx) as file_count,
                        ARRAY_AGG(s.subband_idx ORDER BY s.subband_idx) as subbands
                    FROM absurd.ingestion_groups g
                    LEFT JOIN absurd.ingestion_subbands s ON g.group_id = s.group_id
                    WHERE g.group_id >= $1
                    GROUP BY g.group_id
                    ORDER BY g.group_id DESC
                    LIMIT $2
                    """,
                    start_time,
                    limit,
                )
            elif end_time:
                rows = await conn.fetch(
                    """
                    SELECT
                        g.group_id,
                        COUNT(s.subband_idx) as file_count,
                        ARRAY_AGG(s.subband_idx ORDER BY s.subband_idx) as subbands
                    FROM absurd.ingestion_groups g
                    LEFT JOIN absurd.ingestion_subbands s ON g.group_id = s.group_id
                    WHERE g.group_id <= $1
                    GROUP BY g.group_id
                    ORDER BY g.group_id DESC
                    LIMIT $2
                    """,
                    end_time,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT
                        g.group_id,
                        COUNT(s.subband_idx) as file_count,
                        ARRAY_AGG(s.subband_idx ORDER BY s.subband_idx) as subbands
                    FROM absurd.ingestion_groups g
                    LEFT JOIN absurd.ingestion_subbands s ON g.group_id = s.group_id
                    GROUP BY g.group_id
                    ORDER BY g.group_id DESC
                    LIMIT $1
                    """,
                    limit,
                )

        groups = []
        for row in rows:
            subbands = [str(sb) for sb in row["subbands"]] if row["subbands"] else []
            groups.append(
                {
                    "group_id": row["group_id"],
                    "file_count": row["file_count"],
                    "subbands": subbands,
                    "is_complete": row["file_count"] >= 16,
                }
            )

        return {"groups": groups, "total": len(groups)}

    except Exception as e:
        # Fall back to SQLite HDF5 index if ABSURD not available
        logger.warning(f"ABSURD query failed, trying SQLite fallback: {e}")

    # Fallback to SQLite HDF5 index
    db_path = _get_hdf5_index_db()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="HDF5 index database not found")

    try:
        conn = sqlite3.connect(db_path, timeout=10)

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
            groups.append(
                {
                    "group_id": row[0],
                    "file_count": row[1],
                    "subbands": row[2].split(",") if row[2] else [],
                    "is_complete": row[1] >= 16,
                }
            )

        return {"groups": groups, "total": len(groups)}

    except sqlite3.Error as e:
        logger.error(f"Database error listing HDF5 groups: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# =============================================================================
# Background Job Function (deprecated - use ABSURD tasks)
# =============================================================================


def _execute_conversion_job(
    group_ids: List[str],
    output_dir: Optional[str] = None,
    priority: str = "normal",
) -> Dict[str, Any]:
    """
    Execute conversion for the specified groups.

    DEPRECATED: Use ABSURD convert-group tasks instead.
    This function is no longer functional since the streaming converter
    was migrated to ABSURD. Use the /convert endpoint which enqueues
    ABSURD tasks instead.
    """
    return {
        "error": "DEPRECATED: Use ABSURD convert-group tasks via /convert endpoint",
        "converted": [],
        "failed": [{"group_id": gid, "error": "Migration to ABSURD required"} for gid in group_ids],
        "skipped": [],
    }

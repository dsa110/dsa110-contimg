"""
Database operations for ABSURD-based ingestion.

This module provides PostgreSQL-backed storage for subband tracking,
replacing the SQLite-based queue in streaming_converter.

Tables (in absurd schema):
    - ingestion_groups: Track subband groups and their state
    - ingestion_subbands: Track individual subband files

Benefits over SQLite:
    - Unified with ABSURD task queue
    - Better concurrency (multiple workers)
    - Integrated with Prometheus metrics
    - Transaction support across operations
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# SQL for schema creation (added to absurd/schema.sql)
INGESTION_SCHEMA = """
-- Ingestion group tracking
CREATE TABLE IF NOT EXISTS absurd.ingestion_groups (
    group_id TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'collecting',
    subband_count INTEGER NOT NULL DEFAULT 0,
    expected_subbands INTEGER NOT NULL DEFAULT 16,
    dec_deg REAL,
    ra_deg REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    ms_path TEXT,
    error TEXT,
    
    CONSTRAINT valid_state CHECK (state IN (
        'collecting', 'pending', 'normalizing', 'converting', 'completed', 'failed'
    ))
);

-- Individual subband files
CREATE TABLE IF NOT EXISTS absurd.ingestion_subbands (
    group_id TEXT NOT NULL REFERENCES absurd.ingestion_groups(group_id) ON DELETE CASCADE,
    subband_idx INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (group_id, subband_idx),
    CONSTRAINT valid_subband_idx CHECK (subband_idx >= 0 AND subband_idx < 16)
);

-- Index for finding groups by state
CREATE INDEX IF NOT EXISTS idx_ingestion_groups_state
ON absurd.ingestion_groups(state);

-- Index for finding groups by creation time
CREATE INDEX IF NOT EXISTS idx_ingestion_groups_created
ON absurd.ingestion_groups(created_at);

-- Unique constraint on file path (prevent duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ingestion_subbands_path
ON absurd.ingestion_subbands(file_path);
"""


async def get_client():
    """Get ABSURD client connection.

    Returns connected client from the global pool or creates new one.
    The client is guaranteed to have a non-None _pool after this call.
    """
    from dsa110_contimg.absurd import AbsurdClient
    from dsa110_contimg.absurd.config import AbsurdConfig

    config = AbsurdConfig.from_env()
    client = AbsurdClient(config.database_url)
    await client.connect()
    return client


async def ensure_ingestion_schema() -> None:
    """Ensure ingestion tables exist in the database."""
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(INGESTION_SCHEMA)
            logger.info("Ensured ingestion schema exists")
    finally:
        await client.close()


async def find_or_create_group(
    group_id: str,
    tolerance_s: float = 60.0,
) -> str:
    """Find an existing group within tolerance or create a new one.
    
    This implements time-based clustering: if a subband arrives with
    timestamp T, we look for existing groups within ±tolerance_s.
    If found, use that group; otherwise create a new one.
    
    Args:
        group_id: Timestamp from the subband filename
        tolerance_s: Clustering tolerance in seconds
        
    Returns:
        Canonical group_id to use (existing or new)
    """
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            # Parse incoming timestamp
            try:
                incoming_dt = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                # Invalid format - use as-is
                return group_id
            
            # Look for existing groups within tolerance
            min_time = incoming_dt - timedelta(seconds=tolerance_s)
            max_time = incoming_dt + timedelta(seconds=tolerance_s)
            
            row = await conn.fetchrow(
                """
                SELECT group_id FROM absurd.ingestion_groups
                WHERE state IN ('collecting', 'pending')
                  AND group_id >= $1
                  AND group_id <= $2
                ORDER BY created_at ASC
                LIMIT 1
                """,
                min_time.strftime("%Y-%m-%dT%H:%M:%S"),
                max_time.strftime("%Y-%m-%dT%H:%M:%S"),
            )
            
            if row:
                # Found existing group
                return row["group_id"]
            
            # Create new group
            await conn.execute(
                """
                INSERT INTO absurd.ingestion_groups (group_id, state)
                VALUES ($1, 'collecting')
                ON CONFLICT (group_id) DO NOTHING
                """,
                group_id,
            )
            return group_id
    finally:
        await client.close()


async def record_subband(
    group_id: str,
    subband_idx: int,
    file_path: str,
    dec_deg: Optional[float] = None,
) -> None:
    """Record a subband file arrival.
    
    Args:
        group_id: Canonical group ID
        subband_idx: Subband index (0-15)
        file_path: Path to the HDF5 file
        dec_deg: Declination in degrees (for metadata)
    """
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            async with conn.transaction():
                # Insert subband (ignore if already exists)
                await conn.execute(
                    """
                    INSERT INTO absurd.ingestion_subbands (group_id, subband_idx, file_path)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (file_path) DO NOTHING
                    """,
                    group_id,
                    subband_idx,
                    file_path,
                )
                
                # Update group metadata and count
                await conn.execute(
                    """
                    UPDATE absurd.ingestion_groups
                    SET subband_count = (
                            SELECT COUNT(*) FROM absurd.ingestion_subbands
                            WHERE group_id = $1
                        ),
                        dec_deg = COALESCE($2, dec_deg),
                        updated_at = NOW(),
                        state = CASE
                            WHEN (SELECT COUNT(*) FROM absurd.ingestion_subbands WHERE group_id = $1) >= expected_subbands
                            THEN 'pending'
                            ELSE state
                        END
                    WHERE group_id = $1
                    """,
                    group_id,
                    dec_deg,
                )
    finally:
        await client.close()


async def get_group_subband_count(group_id: str) -> int:
    """Get the current subband count for a group."""
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                "SELECT subband_count FROM absurd.ingestion_groups WHERE group_id = $1",
                group_id,
            )
            return row["subband_count"] if row else 0
    finally:
        await client.close()


async def get_group_files(group_id: str) -> Dict[int, str]:
    """Get all file paths for a group.

    Returns:
        Dict mapping subband_idx to file_path
    """
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT subband_idx, file_path
                FROM absurd.ingestion_subbands
                WHERE group_id = $1
                ORDER BY subband_idx
                """,
                group_id,
            )
            return {row["subband_idx"]: row["file_path"] for row in rows}
    finally:
        await client.close()


async def update_group_after_normalize(
    old_group_id: str,
    new_group_id: str,
    new_paths: Dict[int, str],
) -> None:
    """Update group and subband paths after normalization.
    
    Args:
        old_group_id: Original group ID
        new_group_id: Canonical group ID (from sb00)
        new_paths: Dict mapping subband_idx to new file path
    """
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            async with conn.transaction():
                if old_group_id != new_group_id:
                    # Check if new group already exists
                    existing = await conn.fetchrow(
                        "SELECT group_id FROM absurd.ingestion_groups WHERE group_id = $1",
                        new_group_id,
                    )
                    
                    if existing:
                        # Merge into existing group
                        # Move subbands to new group
                        await conn.execute(
                            """
                            UPDATE absurd.ingestion_subbands
                            SET group_id = $1
                            WHERE group_id = $2
                            """,
                            new_group_id,
                            old_group_id,
                        )
                        # Delete old group
                        await conn.execute(
                            "DELETE FROM absurd.ingestion_groups WHERE group_id = $1",
                            old_group_id,
                        )
                    else:
                        # Rename group
                        await conn.execute(
                            """
                            UPDATE absurd.ingestion_groups
                            SET group_id = $1, updated_at = NOW()
                            WHERE group_id = $2
                            """,
                            new_group_id,
                            old_group_id,
                        )
                        await conn.execute(
                            """
                            UPDATE absurd.ingestion_subbands
                            SET group_id = $1
                            WHERE group_id = $2
                            """,
                            new_group_id,
                            old_group_id,
                        )
                
                # Update file paths
                for subband_idx, new_path in new_paths.items():
                    await conn.execute(
                        """
                        UPDATE absurd.ingestion_subbands
                        SET file_path = $1
                        WHERE group_id = $2 AND subband_idx = $3
                        """,
                        new_path,
                        new_group_id,
                        subband_idx,
                    )
    finally:
        await client.close()


async def update_group_state(
    group_id: str,
    state: str,
    error: Optional[str] = None,
    ms_path: Optional[str] = None,
) -> None:
    """Update group state.
    
    Args:
        group_id: Group ID
        state: New state (collecting, pending, normalizing, converting, completed, failed)
        error: Error message (if state is failed)
        ms_path: Output MS path (if state is completed)
    """
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                UPDATE absurd.ingestion_groups
                SET state = $2,
                    updated_at = NOW(),
                    completed_at = CASE WHEN $2 IN ('completed', 'failed') THEN NOW() ELSE completed_at END,
                    error = $3,
                    ms_path = $4
                WHERE group_id = $1
                """,
                group_id,
                state,
                error,
                ms_path,
            )
    finally:
        await client.close()


async def get_pending_groups(limit: int = 100) -> List[Dict[str, Any]]:
    """Get groups that are ready for processing (pending state)."""
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT group_id, subband_count, dec_deg, created_at
                FROM absurd.ingestion_groups
                WHERE state = 'pending'
                ORDER BY created_at ASC
                LIMIT $1
                """,
                limit,
            )
            return [dict(row) for row in rows]
    finally:
        await client.close()


async def get_ingestion_stats() -> Dict[str, Any]:
    """Get ingestion queue statistics for monitoring."""
    client = await get_client()
    try:
        async with client._pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE state = 'collecting') as collecting,
                    COUNT(*) FILTER (WHERE state = 'pending') as pending,
                    COUNT(*) FILTER (WHERE state = 'normalizing') as normalizing,
                    COUNT(*) FILTER (WHERE state = 'converting') as converting,
                    COUNT(*) FILTER (WHERE state = 'completed') as completed,
                    COUNT(*) FILTER (WHERE state = 'failed') as failed,
                    COUNT(*) as total
                FROM absurd.ingestion_groups
                """
            )
            return dict(row) if row else {}
    finally:
        await client.close()

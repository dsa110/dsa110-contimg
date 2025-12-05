"""
Statistics service - business logic for dashboard statistics.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from ..database import DatabasePool


class StatsService:
    """Business logic for pipeline statistics."""

    def __init__(self, db_pool: DatabasePool):
        self.db_pool = db_pool

    async def get_dashboard_stats(self) -> dict:
        """
        Get comprehensive dashboard statistics.

        Returns counts and status summaries in efficient queries.
        """
        stats = {}

        async with self.db_pool.products_db() as conn:
            # MS counts by stage
            cursor = await conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN stage = 'imaged' THEN 1 ELSE 0 END) as imaged,
                    SUM(CASE WHEN stage = 'calibrated' THEN 1 ELSE 0 END) as calibrated,
                    SUM(CASE WHEN stage = 'ingested' THEN 1 ELSE 0 END) as ingested,
                    SUM(CASE WHEN stage IS NULL OR stage = '' THEN 1 ELSE 0 END) as pending
                FROM ms_index
            """)
            row = await cursor.fetchone()
            stats["ms"] = {
                "total": row["total"] or 0,
                "by_stage": {
                    "imaged": row["imaged"] or 0,
                    "calibrated": row["calibrated"] or 0,
                    "ingested": row["ingested"] or 0,
                    "pending": row["pending"] or 0,
                },
            }

            # Image count
            cursor = await conn.execute("SELECT COUNT(*) as cnt FROM images")
            row = await cursor.fetchone()
            stats["images"] = {"total": row["cnt"] or 0}

            # Photometry and source counts
            cursor = await conn.execute("""
                SELECT
                    COUNT(*) as total_photometry,
                    COUNT(DISTINCT source_id) as unique_sources
                FROM photometry
            """)
            row = await cursor.fetchone()
            stats["photometry"] = {"total": row["total_photometry"] or 0}
            stats["sources"] = {"total": row["unique_sources"] or 0}

            # Job counts by status
            cursor = await conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN status = 'pending' OR status IS NULL THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM batch_jobs
            """)
            row = await cursor.fetchone()
            stats["jobs"] = {
                "total": row["total"] or 0,
                "by_status": {
                    "completed": row["completed"] or 0,
                    "running": row["running"] or 0,
                    "pending": row["pending"] or 0,
                    "failed": row["failed"] or 0,
                },
            }

            # Recent activity
            cursor = await conn.execute("""
                SELECT path, created_at, type
                FROM images
                ORDER BY created_at DESC
                LIMIT 10
            """)
            rows = await cursor.fetchall()
            stats["recent_images"] = [
                {
                    "path": row["path"],
                    "created_at": (
                        datetime.fromtimestamp(row["created_at"]).isoformat()
                        if row["created_at"]
                        else None
                    ),
                    "type": row["type"],
                }
                for row in rows
            ]

        # Cal table count (separate database)
        try:
            if os.path.exists(self.db_pool.config.cal_registry_db_path):
                async with self.db_pool.cal_registry_db() as cal_conn:
                    cursor = await cal_conn.execute("SELECT COUNT(*) as cnt FROM caltables")
                    row = await cursor.fetchone()
                    stats["cal_tables"] = {"total": row["cnt"] or 0}
            else:
                stats["cal_tables"] = {"total": 0}
        except sqlite3.Error:
            stats["cal_tables"] = {"total": 0}

        # Metadata for caching
        stats["_meta"] = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cache_hint_seconds": 30,
        }

        return stats

"""
Mosaic stage: Create multi-observation mosaics.

This stage combines multiple individual images into larger mosaics
using the ABSURD workflow system.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants for mosaic grouping
MS_PER_MOSAIC = 12  # Number of MS files per mosaic
MS_OVERLAP = 3      # Overlap between consecutive mosaics
MS_NEW_PER_TRIGGER = MS_PER_MOSAIC - MS_OVERLAP  # 9 new MS files trigger next mosaic


@dataclass
class MosaicResult:
    """Result of mosaic operations."""
    
    success: bool
    group_id: str
    mosaic_path: Optional[str] = None
    ms_paths: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0


@dataclass  
class MosaicConfig:
    """Configuration for the mosaic stage."""
    
    output_dir: Path
    products_db: Path
    ms_per_mosaic: int = MS_PER_MOSAIC
    ms_overlap: int = MS_OVERLAP
    enable_qa: bool = True
    enable_publish: bool = False


class MosaicStage:
    """Stage for creating multi-observation mosaics.
    
    This stage:
    1. Checks if enough MS files are ready for a mosaic
    2. Groups MS files with proper overlap
    3. Triggers ABSURD mosaic workflow
    4. Optionally runs QA and publishing
    
    Example:
        >>> config = MosaicConfig(
        ...     output_dir=Path("/data/mosaics"),
        ...     products_db=Path("/data/state/db/pipeline.sqlite3"),
        ... )
        >>> stage = MosaicStage(config)
        >>> result = stage.check_and_trigger(
        ...     dec_deg=55.5,
        ...     new_ms_path="/data/ms/2025-10-02T00:12:00.ms",
        ... )
    """

    def __init__(self, config: MosaicConfig) -> None:
        """Initialize the mosaic stage.
        
        Args:
            config: Mosaic configuration
        """
        self.config = config
        self._ensure_tracking_table()

    def _ensure_tracking_table(self) -> None:
        """Ensure mosaic tracking tables exist."""
        try:
            conn = sqlite3.connect(self.config.products_db, timeout=30)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mosaic_groups (
                    group_id TEXT PRIMARY KEY,
                    ms_paths TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    mosaic_path TEXT,
                    created_at REAL NOT NULL,
                    completed_at REAL,
                    error TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mosaic_ms_membership (
                    ms_path TEXT NOT NULL,
                    mosaic_group_id TEXT NOT NULL,
                    position_in_group INTEGER NOT NULL,
                    PRIMARY KEY (ms_path, mosaic_group_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mosaic_ms_path
                ON mosaic_ms_membership(ms_path)
                """
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.warning(f"Failed to ensure mosaic tables: {e}")

    def check_ready_for_mosaic(
        self, dec_deg: float
    ) -> Tuple[bool, List[str], Optional[str]]:
        """Check if there are enough MS files for a new mosaic.
        
        Args:
            dec_deg: Declination for the mosaic strip
            
        Returns:
            Tuple of (ready, ms_paths, group_id)
        """
        try:
            conn = sqlite3.connect(self.config.products_db, timeout=30)
            conn.row_factory = sqlite3.Row
            
            # Get completed MS files not yet in a mosaic
            # Filter by declination (within 1 degree)
            cursor = conn.execute(
                """
                SELECT path FROM ms_index
                WHERE status = 'completed'
                  AND ABS(dec_deg - ?) < 1.0
                  AND path NOT IN (
                      SELECT ms_path FROM mosaic_ms_membership
                  )
                ORDER BY mid_mjd ASC
                LIMIT ?
                """,
                (dec_deg, self.config.ms_per_mosaic),
            )
            
            ms_paths = [row["path"] for row in cursor.fetchall()]
            conn.close()
            
            # Check if we have enough new files
            new_trigger = self.config.ms_per_mosaic - self.config.ms_overlap
            if len(ms_paths) >= new_trigger:
                # Generate group ID from first MS timestamp
                first_ms = Path(ms_paths[0]).stem
                group_id = f"mosaic_{first_ms}"
                return True, ms_paths[:self.config.ms_per_mosaic], group_id
            
            return False, [], None
            
        except sqlite3.Error as e:
            logger.warning(f"Failed to check mosaic readiness: {e}")
            return False, [], None

    def register_mosaic_group(
        self, group_id: str, ms_paths: List[str]
    ) -> bool:
        """Register a new mosaic group.
        
        Args:
            group_id: Mosaic group identifier
            ms_paths: List of MS paths in the group
            
        Returns:
            True if registered successfully
        """
        try:
            conn = sqlite3.connect(self.config.products_db, timeout=30)
            
            # Register the group
            conn.execute(
                """
                INSERT OR IGNORE INTO mosaic_groups 
                (group_id, ms_paths, status, created_at)
                VALUES (?, ?, 'pending', ?)
                """,
                (group_id, ",".join(ms_paths), time.time()),
            )
            
            # Record membership
            for i, ms_path in enumerate(ms_paths):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO mosaic_ms_membership
                    (ms_path, mosaic_group_id, position_in_group)
                    VALUES (?, ?, ?)
                    """,
                    (ms_path, group_id, i),
                )
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to register mosaic group: {e}")
            return False

    def trigger_mosaic_workflow(
        self, group_id: str, ms_paths: List[str]
    ) -> MosaicResult:
        """Trigger the ABSURD mosaic workflow.
        
        Args:
            group_id: Mosaic group identifier
            ms_paths: List of MS paths to mosaic
            
        Returns:
            MosaicResult with status
        """
        t0 = time.perf_counter()
        
        try:
            from dsa110_contimg.absurd import AbsurdClient

            client = AbsurdClient()
            
            # Submit mosaic task
            task_id = client.submit_task(
                "create_mosaic",
                {
                    "group_id": group_id,
                    "ms_paths": ms_paths,
                    "output_dir": str(self.config.output_dir),
                    "enable_qa": self.config.enable_qa,
                },
            )
            
            logger.info(f"Submitted mosaic task {task_id} for group {group_id}")
            
            return MosaicResult(
                success=True,
                group_id=group_id,
                ms_paths=ms_paths,
                elapsed_seconds=time.perf_counter() - t0,
            )
            
        except Exception as e:
            logger.error(f"Failed to trigger mosaic workflow: {e}")
            return MosaicResult(
                success=False,
                group_id=group_id,
                ms_paths=ms_paths,
                error_message=str(e),
                elapsed_seconds=time.perf_counter() - t0,
            )

    def check_and_trigger(
        self,
        dec_deg: float,
        new_ms_path: Optional[str] = None,
    ) -> Optional[MosaicResult]:
        """Check if mosaic is ready and trigger if so.
        
        Args:
            dec_deg: Declination for the mosaic strip
            new_ms_path: Optional path to newly completed MS
            
        Returns:
            MosaicResult if triggered, None otherwise
        """
        ready, ms_paths, group_id = self.check_ready_for_mosaic(dec_deg)
        
        if not ready or group_id is None:
            return None
            
        # Register the group
        if not self.register_mosaic_group(group_id, ms_paths):
            return MosaicResult(
                success=False,
                group_id=group_id,
                ms_paths=ms_paths,
                error_message="Failed to register mosaic group",
            )
        
        # Trigger workflow
        return self.trigger_mosaic_workflow(group_id, ms_paths)

    def update_status(
        self,
        group_id: str,
        status: str,
        mosaic_path: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update mosaic group status.
        
        Args:
            group_id: Mosaic group identifier
            status: New status (pending, processing, completed, failed)
            mosaic_path: Path to completed mosaic
            error: Error message if failed
        """
        try:
            conn = sqlite3.connect(self.config.products_db, timeout=30)
            
            if status == "completed":
                conn.execute(
                    """
                    UPDATE mosaic_groups
                    SET status = ?, mosaic_path = ?, completed_at = ?
                    WHERE group_id = ?
                    """,
                    (status, mosaic_path, time.time(), group_id),
                )
            elif status == "failed":
                conn.execute(
                    """
                    UPDATE mosaic_groups
                    SET status = ?, error = ?, completed_at = ?
                    WHERE group_id = ?
                    """,
                    (status, error, time.time(), group_id),
                )
            else:
                conn.execute(
                    "UPDATE mosaic_groups SET status = ? WHERE group_id = ?",
                    (status, group_id),
                )
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            logger.error(f"Failed to update mosaic status: {e}")

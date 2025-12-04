"""
SQLite-backed queue for tracking subband arrivals and processing state.

This module provides the SubbandQueue class which manages:
- Recording incoming subband files
- Grouping subbands by timestamp (with configurable clustering tolerance)
- Tracking processing state (collecting, pending, in_progress, completed, failed)
- Performance metrics recording
- File validation and stale path detection

The queue is persisted in SQLite with WAL mode for concurrent access safety.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Pattern for parsing subband filenames
GROUP_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<index>\d{2})\.hdf5$"
)


def parse_subband_info(path: Path) -> Optional[Tuple[str, int]]:
    """Extract (group_id, subband_idx) from a filename, or None if not matched.
    
    Args:
        path: Path to HDF5 subband file
        
    Returns:
        Tuple of (group_id, subband_index) or None if filename doesn't match pattern
        
    Example:
        >>> parse_subband_info(Path("/data/2025-10-02T00:12:00_sb05.hdf5"))
        ("2025-10-02T00:12:00", 5)
    """
    m = GROUP_PATTERN.search(path.name)
    if not m:
        return None
    gid = m.group("timestamp")
    try:
        sb = int(m.group("index"))
    except ValueError:
        return None
    return gid, sb


class SubbandQueue:
    """SQLite-backed queue tracking subband arrivals and processing state.
    
    The queue implements time-based clustering to group subbands with similar
    timestamps into the same observation group. This handles the case where
    subbands arrive with slightly different timestamps (e.g., 1 second apart).
    
    Thread Safety:
        All operations are protected by a lock and use explicit SQLite transactions.
        WAL mode is enabled for better concurrent read/write performance.
    
    Attributes:
        path: Path to the SQLite database file
        expected_subbands: Number of subbands expected per complete group (default: 16)
        chunk_duration_minutes: Duration of each observation chunk (default: 5.0)
        cluster_tolerance_s: Maximum time difference to cluster subbands (default: 60.0)
    """

    # Default clustering tolerance for grouping subbands with similar timestamps
    DEFAULT_CLUSTER_TOLERANCE_S = 60.0  # ±60 seconds

    def __init__(
        self,
        path: Path,
        expected_subbands: int = 16,
        chunk_duration_minutes: float = 5.0,
        cluster_tolerance_s: float = DEFAULT_CLUSTER_TOLERANCE_S,
    ) -> None:
        """Initialize the subband queue.
        
        Args:
            path: Path to SQLite database file (will be created if doesn't exist)
            expected_subbands: Number of subbands expected per complete group
            chunk_duration_minutes: Duration of each observation chunk in minutes
            cluster_tolerance_s: Maximum time difference (seconds) to cluster subbands
        """
        self.path = path
        self.expected_subbands = expected_subbands
        self.chunk_duration_minutes = chunk_duration_minutes
        self.cluster_tolerance_s = cluster_tolerance_s
        self._lock = threading.Lock()
        
        # CRITICAL: Use WAL mode for better concurrency and thread safety
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=30.0,
        )
        self._conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
            
        self._ensure_schema()
        self._migrate_schema()
        self._normalize_existing_groups()
        self._consolidate_fragmented_groups()

    @property
    def conn(self) -> sqlite3.Connection:
        """Access the underlying database connection (for advanced queries)."""
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            self._conn.close()

    def _ensure_schema(self) -> None:
        """Create database tables if they don't exist."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_queue (
                    group_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    received_at REAL NOT NULL,
                    last_update REAL NOT NULL,
                    expected_subbands INTEGER,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    error_message TEXT,
                    checkpoint_path TEXT,
                    processing_stage TEXT DEFAULT 'collecting',
                    chunk_minutes REAL,
                    has_calibrator INTEGER DEFAULT NULL,
                    calibrators TEXT
                )
                """
            )
            # Add indexes for performance (matches existing production schema)
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_state 
                ON processing_queue(state)
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_received 
                ON processing_queue(received_at)
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subband_files (
                    group_id TEXT NOT NULL,
                    subband_idx INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (group_id, subband_idx),
                    FOREIGN KEY (group_id) REFERENCES processing_queue(group_id)
                )
                """
            )
            # PERFORMANCE: Add UNIQUE index on path to prevent duplicates
            self._conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_subband_files_path
                ON subband_files(path)
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    group_id TEXT NOT NULL,
                    load_time REAL,
                    phase_time REAL,
                    write_time REAL,
                    total_time REAL,
                    writer_type TEXT,
                    recorded_at REAL NOT NULL,
                    PRIMARY KEY (group_id)
                )
                """
            )

    def _migrate_schema(self) -> None:
        """Ensure existing databases contain the latest columns."""
        with self._lock, self._conn:
            try:
                columns = {
                    row["name"]
                    for row in self._conn.execute("PRAGMA table_info(processing_queue)").fetchall()
                }
            except sqlite3.DatabaseError:
                return

            if "checkpoint_path" not in columns:
                self._conn.execute("ALTER TABLE processing_queue ADD COLUMN checkpoint_path TEXT")
            if "processing_stage" not in columns:
                self._conn.execute(
                    "ALTER TABLE processing_queue ADD COLUMN "
                    "processing_stage TEXT DEFAULT 'collecting'"
                )
            if "chunk_minutes" not in columns:
                self._conn.execute("ALTER TABLE processing_queue ADD COLUMN chunk_minutes REAL")
            if "expected_subbands" not in columns:
                self._conn.execute("ALTER TABLE processing_queue ADD COLUMN expected_subbands INTEGER")
            if "has_calibrator" not in columns:
                self._conn.execute(
                    "ALTER TABLE processing_queue ADD COLUMN has_calibrator INTEGER DEFAULT NULL"
                )
            if "calibrators" not in columns:
                self._conn.execute("ALTER TABLE processing_queue ADD COLUMN calibrators TEXT")
            if "error_message" not in columns:
                self._conn.execute("ALTER TABLE processing_queue ADD COLUMN error_message TEXT")

        # Migrate performance_metrics table
        with self._lock, self._conn:
            try:
                pcols = {
                    row["name"]
                    for row in self._conn.execute(
                        "PRAGMA table_info(performance_metrics)"
                    ).fetchall()
                }
            except sqlite3.DatabaseError:
                pcols = set()
            if pcols and "writer_type" not in pcols:
                try:
                    self._conn.execute(
                        "ALTER TABLE performance_metrics ADD COLUMN writer_type TEXT"
                    )
                except sqlite3.DatabaseError:
                    pass

    def _normalize_group_id(self, group_id: str) -> str:
        """Normalize group_id to 'YYYY-MM-DDTHH:MM:SS' format."""
        try:
            from dsa110_contimg.utils.naming import normalize_group_id
            return normalize_group_id(group_id)
        except (ImportError, ValueError):
            # Fallback to simple normalization
            s = group_id.strip().replace("T", " ")
            try:
                dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                return group_id.strip()

    def _normalize_existing_groups(self) -> None:
        """Normalize all existing group_ids in the database."""
        with self._lock, self._conn:
            try:
                rows = self._conn.execute("SELECT group_id FROM processing_queue").fetchall()
            except sqlite3.DatabaseError:
                return
                
            for r in rows:
                gid = r["group_id"]
                norm = self._normalize_group_id(gid)
                if norm != gid:
                    try:
                        for table in ["processing_queue", "subband_files", "performance_metrics"]:
                            self._conn.execute(
                                f"UPDATE {table} SET group_id = ? WHERE group_id = ?",
                                (norm, gid),
                            )
                    except sqlite3.DatabaseError:
                        continue

    def _consolidate_fragmented_groups(self) -> None:
        """Merge fragmented groups created before time-based clustering."""
        with self._lock, self._conn:
            try:
                rows = self._conn.execute(
                    """
                    SELECT group_id,
                           (SELECT COUNT(*) FROM subband_files 
                            WHERE subband_files.group_id = processing_queue.group_id) as subband_count
                    FROM processing_queue
                    WHERE state IN ('collecting', 'pending')
                    ORDER BY group_id
                    """
                ).fetchall()
            except sqlite3.DatabaseError:
                return

            if len(rows) < 2:
                return

            # Parse timestamps and build clusters
            groups_info: list[tuple[str, datetime, int]] = []
            for row in rows:
                gid = row["group_id"]
                count = row["subband_count"]
                try:
                    dt = datetime.strptime(gid, "%Y-%m-%dT%H:%M:%S")
                    groups_info.append((gid, dt, count))
                except ValueError:
                    continue

            if len(groups_info) < 2:
                return

            groups_info.sort(key=lambda x: x[1])

            # Build clusters
            clusters: list[list[tuple[str, datetime, int]]] = []
            current_cluster: list[tuple[str, datetime, int]] = [groups_info[0]]

            for i in range(1, len(groups_info)):
                gid, dt, count = groups_info[i]
                cluster_start = current_cluster[0][1]
                if (dt - cluster_start).total_seconds() <= self.cluster_tolerance_s:
                    current_cluster.append((gid, dt, count))
                else:
                    if len(current_cluster) > 1:
                        clusters.append(current_cluster)
                    current_cluster = [(gid, dt, count)]

            if len(current_cluster) > 1:
                clusters.append(current_cluster)

            if not clusters:
                return

            # Merge each cluster
            for cluster in clusters:
                cluster.sort(key=lambda x: x[2], reverse=True)
                target_gid = cluster[0][0]
                sources = [c[0] for c in cluster[1:]]

                for src_gid in sources:
                    try:
                        self._conn.execute(
                            "UPDATE subband_files SET group_id = ? WHERE group_id = ?",
                            (target_gid, src_gid),
                        )
                        self._conn.execute(
                            "DELETE FROM processing_queue WHERE group_id = ?",
                            (src_gid,),
                        )
                        logger.info(f"Consolidated fragmented group {src_gid} into {target_gid}")
                    except sqlite3.DatabaseError:
                        continue

    def _find_cluster_group(self, timestamp_str: str) -> Optional[str]:
        """Find an existing group_id within cluster_tolerance_s of the given timestamp."""
        try:
            incoming_dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None

        try:
            rows = self._conn.execute(
                """
                SELECT group_id FROM processing_queue
                WHERE state IN ('collecting', 'pending')
                ORDER BY received_at DESC
                LIMIT 100
                """
            ).fetchall()
        except sqlite3.DatabaseError:
            return None

        best_match = None
        best_delta = float("inf")

        for row in rows:
            existing_gid = row["group_id"]
            try:
                existing_dt = datetime.strptime(existing_gid, "%Y-%m-%dT%H:%M:%S")
                delta_s = abs((incoming_dt - existing_dt).total_seconds())

                if delta_s <= self.cluster_tolerance_s and delta_s < best_delta:
                    best_delta = delta_s
                    best_match = existing_gid
            except ValueError:
                continue

        return best_match

    def record_subband(self, group_id: str, subband_idx: int, file_path: Path) -> None:
        """Record a subband file arrival.

        Uses time-based clustering to group subbands with similar timestamps.
        All operations are atomic via explicit transactions.
        
        Args:
            group_id: Timestamp-based group identifier
            subband_idx: Subband index (0-15 for DSA-110)
            file_path: Path to the HDF5 subband file
        """
        now = time.time()
        normalized_group = self._normalize_group_id(group_id)
        
        # Register inode for stale path detection
        try:
            from dsa110_contimg.utils.fuse_lock import get_inode_tracker
            inode_tracker = get_inode_tracker()
            inode_tracker.register(str(file_path))
        except ImportError:
            pass

        with self._lock:
            try:
                clustered_group = self._find_cluster_group(normalized_group)
                target_group = clustered_group if clustered_group else normalized_group

                if clustered_group and clustered_group != normalized_group:
                    logger.debug(
                        f"Clustering subband {subband_idx} from {normalized_group} "
                        f"into existing group {clustered_group}"
                    )

                self._conn.execute("BEGIN")
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO processing_queue 
                    (group_id, state, received_at, last_update, chunk_minutes, expected_subbands)
                    VALUES (?, 'collecting', ?, ?, ?, ?)
                    """,
                    (target_group, now, now, self.chunk_duration_minutes, self.expected_subbands),
                )
                self._conn.execute(
                    """
                    INSERT INTO subband_files (group_id, subband_idx, path)
                    VALUES (?, ?, ?)
                    ON CONFLICT(path) DO NOTHING
                    """,
                    (target_group, subband_idx, str(file_path)),
                )
                self._conn.execute(
                    "UPDATE processing_queue SET last_update = ? WHERE group_id = ?",
                    (now, target_group),
                )
                
                count = self._conn.execute(
                    "SELECT COUNT(*) FROM subband_files WHERE group_id = ?",
                    (target_group,),
                ).fetchone()[0]
                
                if count >= self.expected_subbands:
                    self._conn.execute(
                        """
                        UPDATE processing_queue
                        SET state = CASE WHEN state = 'completed' THEN state ELSE 'pending' END,
                            last_update = ?
                        WHERE group_id = ?
                        """,
                        (now, target_group),
                    )
                self._conn.commit()
            except sqlite3.Error:
                self._conn.rollback()
                raise

    def bootstrap_directory(self, input_dir: Path) -> None:
        """Bootstrap queue from existing HDF5 files in directory.
        
        Args:
            input_dir: Directory containing HDF5 subband files
        """
        logger.info("Bootstrapping queue from existing files in %s", input_dir)

        new_count = 0
        skipped_count = 0
        for path in sorted(input_dir.glob("*_sb??.hdf5")):
            info = parse_subband_info(path)
            if info is None:
                continue

            group_id, subband_idx = info
            try:
                self.record_subband(group_id, subband_idx, path)
                new_count += 1
            except sqlite3.IntegrityError:
                skipped_count += 1

        logger.info(
            f"Bootstrap complete: {new_count} new files registered, "
            f"{skipped_count} already registered"
        )

    def acquire_next_pending(self) -> Optional[str]:
        """Acquire the next pending group atomically.
        
        Returns:
            Group ID of acquired group, or None if no pending groups
        """
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                row = self._conn.execute(
                    """
                    SELECT group_id FROM processing_queue
                    WHERE state = 'pending'
                    ORDER BY group_id ASC
                    LIMIT 1
                    """
                ).fetchone()
                
                if row is None:
                    self._conn.commit()
                    return None
                    
                group_id = row[0]
                now = time.time()
                self._conn.execute(
                    """
                    UPDATE processing_queue
                    SET state = 'in_progress', last_update = ?
                    WHERE group_id = ?
                    """,
                    (now, group_id),
                )
                self._conn.commit()
                return group_id
            except sqlite3.Error:
                self._conn.rollback()
                raise

    def update_state(
        self, group_id: str, state: str, error: Optional[str] = None
    ) -> None:
        """Update the state of a group.
        
        Args:
            group_id: Group identifier
            state: New state (collecting, pending, in_progress, completed, failed)
            error: Optional error message (for failed state)
        """
        normalized_group = self._normalize_group_id(group_id)
        now = time.time()
        
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                if error is not None:
                    self._conn.execute(
                        """
                        UPDATE processing_queue
                        SET state = ?, last_update = ?, error = ?
                        WHERE group_id = ?
                        """,
                        (state, now, error, normalized_group),
                    )
                else:
                    self._conn.execute(
                        """
                        UPDATE processing_queue
                        SET state = ?, last_update = ?
                        WHERE group_id = ?
                        """,
                        (state, now, normalized_group),
                    )
                self._conn.commit()
            except sqlite3.Error:
                self._conn.rollback()
                raise

    def record_metrics(self, group_id: str, **kwargs) -> None:
        """Record performance metrics for a group.
        
        Args:
            group_id: Group identifier
            **kwargs: Metric key-value pairs (load_time, phase_time, write_time, 
                     total_time, writer_type)
        """
        ALLOWED_COLUMNS = {"load_time", "phase_time", "write_time", "total_time", "writer_type"}
        
        normalized_group = self._normalize_group_id(group_id)
        now = time.time()
        
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                columns = ["group_id", "recorded_at"]
                values = [normalized_group, now]

                for key, value in kwargs.items():
                    if key in ALLOWED_COLUMNS:
                        columns.append(key)
                        values.append(value)

                if len(columns) > 2:
                    columns_str = ", ".join(columns)
                    placeholders = ", ".join(["?"] * len(columns))
                    self._conn.execute(
                        f"INSERT OR REPLACE INTO performance_metrics ({columns_str}) "
                        f"VALUES ({placeholders})",
                        values,
                    )
                self._conn.commit()
            except sqlite3.Error:
                self._conn.rollback()
                raise

    def group_files(self, group_id: str) -> List[str]:
        """Get list of file paths for a group.
        
        Args:
            group_id: Group identifier
            
        Returns:
            List of file paths ordered by subband index
        """
        normalized_group = self._normalize_group_id(group_id)
        with self._lock:
            rows = self._conn.execute(
                "SELECT path FROM subband_files WHERE group_id = ? ORDER BY subband_idx",
                (normalized_group,),
            ).fetchall()
            return [row[0] for row in rows]

    def validate_group_files(self, group_id: str) -> Tuple[List[str], List[str]]:
        """Validate that all files in a group still exist and are readable.
        
        Args:
            group_id: Group identifier
            
        Returns:
            Tuple of (valid_paths, invalid_paths)
        """
        all_paths = self.group_files(group_id)
        valid_paths = []
        invalid_paths = []

        try:
            from dsa110_contimg.utils.fuse_lock import get_inode_tracker
            inode_tracker = get_inode_tracker()
        except ImportError:
            inode_tracker = None

        for path in all_paths:
            try:
                p = Path(path)
                if not p.exists():
                    invalid_paths.append(path)
                    continue
                if not os.access(path, os.R_OK):
                    invalid_paths.append(path)
                    continue
                if p.stat().st_size == 0:
                    invalid_paths.append(path)
                    continue
                if inode_tracker is not None and not inode_tracker.is_valid(path):
                    logger.warning(f"File inode changed (may have been replaced): {path}")
                    invalid_paths.append(path)
                    continue
                valid_paths.append(path)
            except OSError:
                invalid_paths.append(path)

        return valid_paths, invalid_paths

    def remove_invalid_files(self, group_id: str, invalid_paths: List[str]) -> int:
        """Remove invalid file paths from a group.
        
        Args:
            group_id: Group identifier
            invalid_paths: List of paths to remove
            
        Returns:
            Number of paths removed
        """
        if not invalid_paths:
            return 0

        normalized_group = self._normalize_group_id(group_id)
        removed = 0
        
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                for path in invalid_paths:
                    cursor = self._conn.execute(
                        "DELETE FROM subband_files WHERE group_id = ? AND path = ?",
                        (normalized_group, path),
                    )
                    removed += cursor.rowcount
                self._conn.commit()
            except sqlite3.Error:
                self._conn.rollback()
                raise
        return removed

    def count_by_state(self) -> Dict[str, int]:
        """Count groups by state.
        
        Returns:
            Dictionary mapping state names to counts
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT state, COUNT(*) as cnt FROM processing_queue GROUP BY state"
            ).fetchall()
            return {row["state"]: row["cnt"] for row in rows}

    def get_group_info(self, group_id: str) -> Optional[Dict]:
        """Get detailed information about a group.
        
        Args:
            group_id: Group identifier
            
        Returns:
            Dictionary with group info, or None if not found
        """
        normalized_group = self._normalize_group_id(group_id)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM processing_queue WHERE group_id = ?",
                (normalized_group,),
            ).fetchone()
            if row is None:
                return None
            return dict(row)


# Backwards compatibility alias
QueueDB = SubbandQueue

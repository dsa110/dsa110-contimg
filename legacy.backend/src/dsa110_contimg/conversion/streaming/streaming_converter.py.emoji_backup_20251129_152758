#!/opt/miniforge/envs/casa6/bin/python
"""
Streaming converter service for DSA-110 UVH5 subband groups.

This daemon watches an ingest directory for new *_sb??.hdf5 files, queues
complete 16-subband groups, and invokes the existing batch converter on each
group using a scratch directory for staging.

The queue is persisted in SQLite so the service can resume after restarts.
"""

# CRITICAL: Configure h5py cache defaults BEFORE any imports that use h5py/pyuvdata
# This ensures all HDF5 file opens (including in pyuvdata) use optimized cache settings
# fmt: off
# isort: off
from dsa110_contimg.utils.hdf5_io import configure_h5py_cache_defaults  # noqa: E402

configure_h5py_cache_defaults()  # Sets 16MB cache for all h5py.File() calls
# isort: on
# fmt: on

import argparse  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Dict, Iterator, List, Optional, Tuple  # noqa: E402

from dsa110_contimg.database.registry import (  # noqa: E402
    get_active_applylist,
    register_set_from_prefix,
)
from dsa110_contimg.photometry.manager import PhotometryConfig, PhotometryManager  # noqa: E402
from dsa110_contimg.photometry.worker import PhotometryBatchWorker  # noqa: E402

try:
    from dsa110_contimg.utils.graphiti_logging import GraphitiRunLogger
except Exception:  # pragma: no cover - optional helper

    class GraphitiRunLogger:  # type: ignore
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def log_consumes(self, *a, **k):
            pass

        def log_produces(self, *a, **k):
            pass


# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

import casacore.tables as casatables  # noqa

table = casatables.table  # noqa: N816
from casatasks import concat as casa_concat  # noqa

from dsa110_contimg.calibration.applycal import apply_to_target  # noqa
from dsa110_contimg.calibration.calibration import solve_bandpass  # noqa
from dsa110_contimg.calibration.calibration import (
    solve_delay,
    solve_gains,
)
from dsa110_contimg.calibration.streaming import has_calibrator  # noqa
from dsa110_contimg.calibration.streaming import (
    solve_calibration_for_ms,
)
from dsa110_contimg.database.products import ensure_ingest_db  # noqa
from dsa110_contimg.database.products import (
    ensure_products_db,
    images_insert,
    log_pointing,
    ms_index_upsert,
)
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db  # noqa
from dsa110_contimg.imaging.cli import image_ms  # noqa
from dsa110_contimg.utils.ms_organization import create_path_mapper  # noqa
from dsa110_contimg.utils.ms_organization import (
    determine_ms_type,
    extract_date_from_filename,
    organize_ms_file,
)

try:  # Optional dependency for efficient file watching
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAVE_WATCHDOG = True
except ImportError:  # pragma: no cover - fallback path
    HAVE_WATCHDOG = False


GROUP_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<index>\d{2})\.hdf5$"
)


def parse_subband_info(path: Path) -> Optional[Tuple[str, int]]:
    """Extract (group_id, subband_idx) from a filename, or None if not matched."""
    m = GROUP_PATTERN.search(path.name)
    if not m:
        return None
    gid = m.group("timestamp")
    try:
        sb = int(m.group("index"))
    except Exception:
        return None
    return gid, sb


@contextmanager
def override_env(values: Dict[str, str]) -> Iterator[None]:
    """Temporarily override environment variables."""
    if not values:
        yield
        return

    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, val in values.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        yield
    finally:
        for key, val in previous.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class QueueDB:
    """SQLite-backed queue tracking subband arrivals and processing state."""

    # Default clustering tolerance for grouping subbands with similar timestamps
    DEFAULT_CLUSTER_TOLERANCE_S = 60.0  # ±60 seconds

    def __init__(
        self,
        path: Path,
        expected_subbands: int = 16,
        chunk_duration_minutes: float = 5.0,
        cluster_tolerance_s: float = DEFAULT_CLUSTER_TOLERANCE_S,
    ) -> None:
        self.path = path
        self.expected_subbands = expected_subbands
        self.chunk_duration_minutes = chunk_duration_minutes
        self.cluster_tolerance_s = cluster_tolerance_s
        self._lock = threading.Lock()
        # CRITICAL: Use WAL mode for better concurrency and thread safety
        # WAL (Write-Ahead Logging) allows multiple readers and one writer simultaneously
        # This is safer than check_same_thread=False with default journal mode
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=30.0,  # Wait up to 30 seconds for locks
        )
        self._conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            # If WAL mode fails (e.g., read-only filesystem), continue with default mode
            # This is a best-effort optimization
            pass
        self._ensure_schema()
        self._migrate_schema()
        self._normalize_existing_groups()
        self._consolidate_fragmented_groups()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _ensure_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingest_queue (
                    group_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    received_at REAL NOT NULL,
                    last_update REAL NOT NULL,
                    expected_subbands INTEGER,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    checkpoint_path TEXT,
                    processing_stage TEXT DEFAULT 'collecting',
                    chunk_minutes REAL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subband_files (
                    group_id TEXT NOT NULL,
                    subband_idx INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (group_id, subband_idx)
                )
                """
            )
            # PERFORMANCE: Add UNIQUE index on path to prevent memory leak
            # This allows database-enforced deduplication via ON CONFLICT,
            # eliminating the need for unbounded in-memory sets
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
                    for row in self._conn.execute("PRAGMA table_info(ingest_queue)").fetchall()
                }
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive path
                logging.error("Failed to inspect ingest_queue schema: %s", exc)
                return

            if "checkpoint_path" not in columns:
                self._conn.execute("ALTER TABLE ingest_queue ADD COLUMN checkpoint_path TEXT")
            if "processing_stage" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN processing_stage TEXT DEFAULT 'collecting'"
                )
                self._conn.execute(
                    "UPDATE ingest_queue SET processing_stage = 'collecting' WHERE processing_stage IS NULL"
                )
            if "chunk_minutes" not in columns:
                self._conn.execute("ALTER TABLE ingest_queue ADD COLUMN chunk_minutes REAL")
            if "expected_subbands" not in columns:
                self._conn.execute("ALTER TABLE ingest_queue ADD COLUMN expected_subbands INTEGER")
                try:
                    self._conn.execute(
                        "UPDATE ingest_queue SET expected_subbands = ? WHERE expected_subbands IS NULL",
                        (self.expected_subbands,),
                    )
                except sqlite3.DatabaseError:
                    pass

    def _normalize_group_id_datetime(self, group_id: str) -> str:
        """Normalize group_id to 'YYYY-MM-DDTHH:MM:SS'. Accept 'T' or space."""
        from dsa110_contimg.utils.naming import normalize_group_id

        try:
            return normalize_group_id(group_id)
        except ValueError:
            # Fallback to original behavior for backward compatibility
            s = group_id.strip()
            try:
                ts = s.replace("T", " ")
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except Exception:
                return s

    def _normalize_existing_groups(self) -> None:
        with self._lock, self._conn:
            try:
                rows = self._conn.execute("SELECT group_id FROM ingest_queue").fetchall()
            except sqlite3.DatabaseError:
                return
            for r in rows:
                gid = r["group_id"]
                norm = self._normalize_group_id_datetime(gid)
                if norm != gid:
                    try:
                        self._conn.execute(
                            "UPDATE ingest_queue SET group_id = ? WHERE group_id = ?",
                            (norm, gid),
                        )
                        self._conn.execute(
                            "UPDATE subband_files SET group_id = ? WHERE group_id = ?",
                            (norm, gid),
                        )
                        self._conn.execute(
                            "UPDATE performance_metrics SET group_id = ? WHERE group_id = ?",
                            (norm, gid),
                        )
                    except sqlite3.DatabaseError:
                        continue

            # Check which columns exist in current schema
            try:
                columns = {
                    row["name"]
                    for row in self._conn.execute("PRAGMA table_info(ingest_queue)").fetchall()
                }
            except sqlite3.DatabaseError:
                columns = set()

            altered = False
            if "has_calibrator" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN has_calibrator INTEGER DEFAULT NULL"
                )
                altered = True
            if "calibrators" not in columns:
                self._conn.execute("ALTER TABLE ingest_queue ADD COLUMN calibrators TEXT")
                altered = True

            if altered:
                logging.info("Updated ingest_queue schema with new metadata columns.")

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
                    logging.info("Updated performance_metrics schema with writer_type column.")
                except sqlite3.DatabaseError:
                    pass

    def _consolidate_fragmented_groups(self) -> None:
        """One-time migration to merge fragmented groups created before time-based clustering.

        This function detects groups that should have been clustered together (timestamps
        within cluster_tolerance_s) and merges them into a single group. This is a
        one-time fix for databases created before the clustering logic was implemented.

        The merge strategy:
        1. Find all groups in 'collecting' or 'pending' state
        2. Cluster them by timestamp similarity (within tolerance)
        3. For each cluster, merge all groups into the one with the most subbands
        4. Update subband_files foreign keys to point to the merged group
        5. Delete the now-empty original groups
        """
        with self._lock, self._conn:
            try:
                # Get all collecting/pending groups ordered by timestamp
                rows = self._conn.execute(
                    """
                    SELECT group_id, 
                           (SELECT COUNT(*) FROM subband_files WHERE subband_files.group_id = ingest_queue.group_id) as subband_count
                    FROM ingest_queue 
                    WHERE state IN ('collecting', 'pending')
                    ORDER BY group_id
                    """
                ).fetchall()
            except sqlite3.DatabaseError:
                return

            if len(rows) < 2:
                return  # Nothing to consolidate

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

            # Sort by timestamp
            groups_info.sort(key=lambda x: x[1])

            # Build clusters of groups within tolerance
            clusters: list[list[tuple[str, datetime, int]]] = []
            current_cluster: list[tuple[str, datetime, int]] = [groups_info[0]]

            for i in range(1, len(groups_info)):
                gid, dt, count = groups_info[i]
                # Check if this group is within tolerance of any in current cluster
                cluster_start = current_cluster[0][1]
                if (dt - cluster_start).total_seconds() <= self.cluster_tolerance_s:
                    current_cluster.append((gid, dt, count))
                else:
                    if len(current_cluster) > 1:
                        clusters.append(current_cluster)
                    current_cluster = [(gid, dt, count)]

            # Don't forget the last cluster
            if len(current_cluster) > 1:
                clusters.append(current_cluster)

            if not clusters:
                return  # No fragmented groups to merge

            # Merge each cluster
            merged_count = 0
            for cluster in clusters:
                # Pick the group with the most subbands as the target
                cluster.sort(key=lambda x: x[2], reverse=True)
                target_gid = cluster[0][0]
                sources = [c[0] for c in cluster[1:]]

                for src_gid in sources:
                    try:
                        # Move subbands to target group
                        self._conn.execute(
                            "UPDATE subband_files SET group_id = ? WHERE group_id = ?",
                            (target_gid, src_gid),
                        )
                        # Delete the now-empty source group
                        self._conn.execute(
                            "DELETE FROM ingest_queue WHERE group_id = ?",
                            (src_gid,),
                        )
                        merged_count += 1
                        logging.info(f"Consolidated fragmented group {src_gid} into {target_gid}")
                    except sqlite3.DatabaseError as exc:
                        logging.warning(f"Failed to merge {src_gid} into {target_gid}: {exc}")
                        continue

            if merged_count > 0:
                logging.info(f"Consolidated {merged_count} fragmented groups into their clusters")

    def _find_cluster_group(self, timestamp_str: str) -> Optional[str]:
        """Find an existing group_id within cluster_tolerance_s of the given timestamp.

        This implements time-based clustering: if a subband arrives with timestamp
        2025-11-07T23:50:19, but there's already a group 2025-11-07T23:50:18 (1 second
        apart), the subband should join that existing group rather than create a new one.

        Args:
            timestamp_str: ISO timestamp string (YYYY-MM-DDTHH:MM:SS)

        Returns:
            Existing group_id if found within tolerance, None otherwise
        """
        try:
            # Parse the incoming timestamp
            incoming_dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None

        # Query existing collecting/pending groups
        try:
            rows = self._conn.execute(
                """
                SELECT group_id FROM ingest_queue 
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

        CRITICAL: Uses time-based clustering to group subbands with similar timestamps.
        Subbands within cluster_tolerance_s (default 60s) are assigned to the same group.

        All operations within this method are atomic via explicit transactions.
        """
        now = time.time()
        normalized_group = self._normalize_group_id_datetime(group_id)
        with self._lock:
            try:
                # CRITICAL: Check for existing group within time tolerance BEFORE starting transaction
                # This implements the clustering logic per DSA-110 requirements
                clustered_group = self._find_cluster_group(normalized_group)
                target_group = clustered_group if clustered_group else normalized_group

                if clustered_group and clustered_group != normalized_group:
                    logging.debug(
                        f"Clustering subband {subband_idx} from {normalized_group} into existing group {clustered_group}"
                    )

                # CRITICAL: Use explicit transaction for atomicity
                # This ensures all operations succeed or fail together
                self._conn.execute("BEGIN")
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO ingest_queue (group_id, state, received_at, last_update, chunk_minutes, expected_subbands)
                    VALUES (?, 'collecting', ?, ?, ?, ?)
                    """,
                    (
                        target_group,
                        now,
                        now,
                        self.chunk_duration_minutes,
                        self.expected_subbands,
                    ),
                )
                # PERFORMANCE: Use INSERT OR IGNORE to leverage UNIQUE index on path
                # This prevents duplicate entries while allowing database to handle deduplication
                self._conn.execute(
                    """
                    INSERT INTO subband_files (group_id, subband_idx, path)
                    VALUES (?, ?, ?)
                    ON CONFLICT(path) DO NOTHING
                    """,
                    (target_group, subband_idx, str(file_path)),
                )
                self._conn.execute(
                    """
                    UPDATE ingest_queue
                       SET last_update = ?
                     WHERE group_id = ?
                    """,
                    (now, target_group),
                )
                count = self._conn.execute(
                    "SELECT COUNT(*) FROM subband_files WHERE group_id = ?",
                    (target_group,),
                ).fetchone()[0]
                if count >= self.expected_subbands:
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET state = CASE WHEN state = 'completed' THEN state ELSE 'pending' END,
                               last_update = ?
                         WHERE group_id = ?
                        """,
                        (now, target_group),
                    )
                # Commit transaction
                self._conn.commit()
            except Exception:
                # Rollback on any error to maintain consistency
                self._conn.rollback()
                raise

    def bootstrap_directory(self, input_dir: Path) -> None:
        """Bootstrap queue from existing HDF5 files in directory.

        PERFORMANCE: Uses database UNIQUE constraint to handle deduplication.
        No need to pre-fetch existing paths into memory.
        """
        logging.info("Bootstrapping queue from existing files in %s", input_dir)

        new_count = 0
        skipped_count = 0
        for path in sorted(input_dir.glob("*_sb??.hdf5")):
            info = parse_subband_info(path)
            if info is None:
                continue

            group_id, subband_idx = info
            try:
                # Let database handle deduplication via UNIQUE index on path
                self.record_subband(group_id, subband_idx, path)
                new_count += 1
            except sqlite3.IntegrityError:
                # File already registered - silently skip
                skipped_count += 1

        logging.info(
            f"✓ Bootstrap complete: {new_count} new files registered, "
            f"{skipped_count} already registered"
        )

    def acquire_next_pending(self) -> Optional[str]:
        """Acquire the next pending group atomically.

        CRITICAL: Uses explicit transaction to ensure SELECT and UPDATE are atomic.
        Prevents race conditions where multiple threads acquire the same group.
        """
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                row = self._conn.execute(
                    """
                    SELECT group_id FROM ingest_queue
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
                    UPDATE ingest_queue
                       SET state = 'in_progress',
                           last_update = ?
                     WHERE group_id = ?
                    """,
                    (now, group_id),
                )
                self._conn.commit()
                return group_id
            except Exception:
                self._conn.rollback()
                raise

    def update_state(self, group_id: str, state: str, error: Optional[str] = None) -> None:
        """Update the state of a group in the queue.

        CRITICAL: Uses explicit transaction for consistency.
        """
        normalized_group = self._normalize_group_id_datetime(group_id)
        now = time.time()
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                if error is not None:
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET state = ?, last_update = ?, error = ?
                         WHERE group_id = ?
                        """,
                        (state, now, error, normalized_group),
                    )
                else:
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET state = ?, last_update = ?
                         WHERE group_id = ?
                        """,
                        (state, now, normalized_group),
                    )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def record_metrics(self, group_id: str, **kwargs) -> None:
        """Record performance metrics for a group.

        CRITICAL: Column names are whitelisted to prevent SQL injection.
        Only known performance metric columns are allowed.
        """
        # CRITICAL: Whitelist allowed column names to prevent SQL injection
        ALLOWED_METRIC_COLUMNS = {
            "load_time",
            "phase_time",
            "write_time",
            "total_time",
            "writer_type",
        }

        normalized_group = self._normalize_group_id_datetime(group_id)
        now = time.time()
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                # Build column list and values dynamically, but only for whitelisted columns
                columns = ["group_id", "recorded_at"]
                values = [normalized_group, now]
                placeholders = ["?", "?"]

                for key, value in kwargs.items():
                    # Only allow whitelisted columns
                    if key in ALLOWED_METRIC_COLUMNS:
                        columns.append(key)
                        values.append(value)
                        placeholders.append("?")

                if len(columns) > 2:  # Only execute if we have metrics to record
                    # Build SQL safely: column names are whitelisted, values are parameterized
                    # Validate all column names are in whitelist (defense in depth)
                    validated_columns = [
                        col
                        for col in columns
                        if col in ALLOWED_METRIC_COLUMNS or col in ("group_id", "recorded_at")
                    ]
                    if len(validated_columns) != len(columns):
                        raise ValueError(
                            "Invalid column name detected - potential SQL injection attempt"
                        )
                    # Use parameterized query with validated column names
                    # Note: SQLite doesn't support parameterized column names, only values.
                    # Column names are validated against whitelist above, values are parameterized.
                    columns_str = ", ".join(validated_columns)
                    placeholders_str = ", ".join(["?"] * len(validated_columns))
                    # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                    # nosemgrep: python_sql_rule-hardcoded-sql-expression
                    self._conn.execute(
                        f"INSERT OR REPLACE INTO performance_metrics ({columns_str}) VALUES ({placeholders_str})",
                        values,
                    )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def group_files(self, group_id: str) -> List[str]:
        """Get list of file paths for a group."""
        normalized_group = self._normalize_group_id_datetime(group_id)
        with self._lock:
            rows = self._conn.execute(
                "SELECT path FROM subband_files WHERE group_id = ? ORDER BY subband_idx",
                (normalized_group,),
            ).fetchall()
            return [row[0] for row in rows]


class _FSHandler(FileSystemEventHandler):
    """Watchdog handler to record arriving subband files."""

    def __init__(self, queue: QueueDB) -> None:
        self.queue = queue

    def _maybe_record(self, path: str) -> None:
        p = Path(path)
        info = parse_subband_info(p)
        if info is None:
            return
        gid, sb = info

        # PRECONDITION CHECK: Validate file is readable before queuing
        # This ensures we follow "measure twice, cut once" - establish requirements upfront
        # before recording file in queue and attempting conversion.
        log = logging.getLogger("stream")

        # Check file exists
        if not p.exists():
            log.warning(f"File does not exist (may have been deleted): {path}")
            return

        # Check file is readable
        if not os.access(path, os.R_OK):
            log.warning(f"File is not readable: {path}")
            return

        # Check file size (basic sanity check)
        try:
            file_size = p.stat().st_size
            if file_size == 0:
                log.warning(f"File is empty (0 bytes): {path}")
                return
            if file_size < 1024:  # Less than 1KB is suspicious
                log.warning(f"File is suspiciously small ({file_size} bytes): {path}")
        except OSError as e:
            log.warning(f"Failed to check file size: {path}. Error: {e}")
            return

        # Quick HDF5 structure check using memory-mapped I/O for speed
        try:
            from dsa110_contimg.utils.hdf5_io import open_uvh5_mmap

            # OPTIMIZATION: Use memory-mapped I/O for fast validation
            # This avoids chunk cache overhead for simple structure checks
            with open_uvh5_mmap(path) as f:
                # Verify file has required structure (Header or Data group)
                if "Header" not in f and "Data" not in f:
                    log.warning(f"File does not appear to be valid HDF5/UVH5: {path}")
                    return
                # Quick sanity check on time_array
                if "Header/time_array" in f:
                    if f["Header/time_array"].shape[0] == 0:
                        log.warning(f"File has empty time_array: {path}")
                        return
        except Exception as e:
            log.warning(f"File is not readable HDF5: {path}. Error: {e}")
            return

        # File passed all checks, record in queue
        try:
            self.queue.record_subband(gid, sb, p)
        except Exception:
            logging.getLogger("stream").debug("record_subband failed for %s", p, exc_info=True)

    def on_created(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):  # pragma: no cover - defensive
            return
        self._maybe_record(event.src_path)

    def on_moved(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):  # pragma: no cover - defensive
            return
        self._maybe_record(event.dest_path)


# Constants for mosaic grouping
MS_PER_MOSAIC = 10  # Number of MS files per mosaic
MS_OVERLAP = 2      # Overlap between consecutive mosaics
MS_NEW_PER_TRIGGER = MS_PER_MOSAIC - MS_OVERLAP  # 8 new MS files trigger next mosaic


def _ensure_mosaic_tracking_table(conn) -> None:
    """Ensure mosaic_groups tracking table exists in products database.

    This table tracks which MS files have been included in mosaics to prevent
    duplicate processing and implement the sliding window overlap pattern.
    """
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


def get_mosaic_queue_status(products_db_path: Path) -> dict:
    """Get mosaic queue status for API reporting.

    Returns:
        Dictionary with queue statistics:
        - pending_count: Number of pending mosaic groups
        - in_progress_count: Number of in-progress mosaics
        - completed_count: Number of completed mosaics
        - failed_count: Number of failed mosaics
        - available_ms_count: MS files ready for next mosaic
        - ms_until_next_mosaic: How many more MS files needed
    """
    import sqlite3

    conn = sqlite3.connect(str(products_db_path))
    try:
        _ensure_mosaic_tracking_table(conn)

        # Count mosaic groups by status
        cursor = conn.execute(
            """
            SELECT status, COUNT(*) FROM mosaic_groups GROUP BY status
            """
        )
        status_counts = dict(cursor.fetchall())

        # Count MS files that haven't been in any mosaic yet
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM ms_index
            WHERE stage = 'imaged' AND status = 'done'
            AND path NOT IN (SELECT ms_path FROM mosaic_ms_membership)
            """
        )
        available_ms = cursor.fetchone()[0]

        return {
            "pending_count": status_counts.get("pending", 0),
            "in_progress_count": status_counts.get("in_progress", 0),
            "completed_count": status_counts.get("completed", 0),
            "failed_count": status_counts.get("failed", 0),
            "available_ms_count": available_ms,
            "ms_until_next_mosaic": max(0, MS_NEW_PER_TRIGGER - available_ms),
        }
    finally:
        conn.close()


def check_for_complete_group(
    ms_path: str,
    products_db_path: Path,
    time_window_minutes: float = 55.0,
    ms_per_mosaic: int = MS_PER_MOSAIC,
    ms_overlap: int = MS_OVERLAP,
) -> Optional[List[str]]:
    """Check if a complete group (10 MS files) exists for mosaic creation.

    Implements a sliding window pattern:
    - First mosaic: 10 completely new MS files
    - Subsequent mosaics: 8 new + 2 overlap from previous mosaic

    Args:
        ms_path: Path to MS file that was just imaged (trigger point)
        products_db_path: Path to products database
        time_window_minutes: Time window in minutes to search for MS files
        ms_per_mosaic: Number of MS files per mosaic (default: 10)
        ms_overlap: Number of MS files to overlap between mosaics (default: 2)

    Returns:
        List of MS paths in complete group, or None if group incomplete
    """
    import sqlite3

    conn = sqlite3.connect(str(products_db_path))

    try:
        _ensure_mosaic_tracking_table(conn)

        # Get mid_mjd for this MS
        cursor = conn.execute("SELECT mid_mjd FROM ms_index WHERE path = ?", (ms_path,))
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None

        mid_mjd = row[0]
        window_half_days = time_window_minutes / (2 * 24 * 60)

        # Query for MS files in time window that are imaged
        cursor = conn.execute(
            """
            SELECT path, mid_mjd FROM ms_index
            WHERE mid_mjd BETWEEN ? AND ?
            AND stage = 'imaged'
            AND status = 'done'
            ORDER BY mid_mjd
            """,
            (mid_mjd - window_half_days, mid_mjd + window_half_days),
        )

        all_ms = [(row[0], row[1]) for row in cursor.fetchall()]

        if len(all_ms) < ms_per_mosaic:
            return None  # Not enough MS files in window

        # Find MS files that haven't been in any mosaic yet
        ms_paths_only = [m[0] for m in all_ms]
        placeholders = ",".join("?" * len(ms_paths_only))
        cursor = conn.execute(
            f"""
            SELECT DISTINCT ms_path FROM mosaic_ms_membership
            WHERE ms_path IN ({placeholders})
            """,
            ms_paths_only,
        )
        already_mosaicked = {row[0] for row in cursor.fetchall()}

        # Separate new and already-mosaicked MS files
        new_ms = [(p, mjd) for p, mjd in all_ms if p not in already_mosaicked]

        # Check if we have enough new MS files for a mosaic
        # For sliding window: need at least (ms_per_mosaic - ms_overlap) new files
        ms_new_required = ms_per_mosaic - ms_overlap

        if len(new_ms) < ms_new_required:
            return None  # Not enough new MS files

        # Build the mosaic group:
        # - Take the oldest new MS files
        # - Fill remaining slots with overlap from previous mosaic

        # Sort new MS by time
        new_ms.sort(key=lambda x: x[1])

        # Take the first ms_new_required new MS files
        group_new = new_ms[:ms_new_required]
        earliest_new_mjd = group_new[0][1]

        # Find overlap candidates: mosaicked MS files just before the earliest new one
        if ms_overlap > 0 and already_mosaicked:
            cursor = conn.execute(
                """
                SELECT path, mid_mjd FROM ms_index
                WHERE path IN (SELECT ms_path FROM mosaic_ms_membership)
                AND mid_mjd < ?
                AND stage = 'imaged'
                AND status = 'done'
                ORDER BY mid_mjd DESC
                LIMIT ?
                """,
                (earliest_new_mjd, ms_overlap),
            )
            overlap_ms = [(row[0], row[1]) for row in cursor.fetchall()]
            overlap_ms.reverse()  # Put in chronological order
        else:
            overlap_ms = []

        # If we don't have enough overlap, use more new MS files
        if len(overlap_ms) < ms_overlap:
            # First mosaic case: no overlap, use all new
            needed_from_new = ms_per_mosaic
            if len(new_ms) < needed_from_new:
                return None
            group_ms = new_ms[:needed_from_new]
        else:
            # Normal case: overlap + new
            group_ms = overlap_ms + group_new

        # Verify we have exactly ms_per_mosaic files
        if len(group_ms) < ms_per_mosaic:
            return None

        # Return just the paths, sorted by time
        group_ms.sort(key=lambda x: x[1])
        return [m[0] for m in group_ms[:ms_per_mosaic]]

    finally:
        conn.close()


def register_mosaic_group(
    products_db_path: Path,
    group_id: str,
    ms_paths: List[str],
    status: str = "pending",
) -> None:
    """Register a mosaic group and its MS membership.

    Args:
        products_db_path: Path to products database
        group_id: Unique identifier for the mosaic group
        ms_paths: List of MS file paths in chronological order
        status: Initial status (default: pending)
    """
    import sqlite3
    import time

    conn = sqlite3.connect(str(products_db_path))
    try:
        _ensure_mosaic_tracking_table(conn)

        # Insert mosaic group
        conn.execute(
            """
            INSERT OR REPLACE INTO mosaic_groups
            (group_id, ms_paths, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (group_id, "|".join(ms_paths), status, time.time()),
        )

        # Insert MS membership
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
    finally:
        conn.close()


def update_mosaic_group_status(
    products_db_path: Path,
    group_id: str,
    status: str,
    mosaic_path: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Update mosaic group status after processing.

    Args:
        products_db_path: Path to products database
        group_id: Mosaic group identifier
        status: New status (in_progress, completed, failed)
        mosaic_path: Path to created mosaic (if completed)
        error: Error message (if failed)
    """
    import sqlite3
    import time

    conn = sqlite3.connect(str(products_db_path))
    try:
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
                """
                UPDATE mosaic_groups SET status = ? WHERE group_id = ?
                """,
                (status, group_id),
            )
        conn.commit()
    finally:
        conn.close()


def trigger_photometry_for_image(
    image_path: Path,
    group_id: str,
    args: argparse.Namespace,
    products_db_path: Optional[Path] = None,
    data_registry_db_path: Optional[Path] = None,
) -> Optional[int]:
    """Trigger photometry measurement for a newly imaged FITS file.

    Args:
        image_path: Path to FITS image file
        group_id: Group ID for tracking
        args: Command-line arguments with photometry configuration
        products_db_path: Path to products database (optional)
        data_registry_db_path: Path to data registry database (optional)

    Returns:
        Batch job ID if successful, None otherwise
    """
    log = logging.getLogger("stream.photometry")

    if not image_path.exists():
        log.warning(f"FITS image not found: {image_path}")
        return None

    try:
        # Get products DB path
        if products_db_path is None:
            products_db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3"))

        # Create photometry configuration from args
        config = PhotometryConfig(
            catalog=getattr(args, "photometry_catalog", "nvss"),
            radius_deg=getattr(args, "photometry_radius", 0.5),
            max_sources=getattr(args, "photometry_max_sources", None),
            method="peak",
            normalize=getattr(args, "photometry_normalize", False),
        )

        # Initialize PhotometryManager
        manager = PhotometryManager(
            products_db_path=products_db_path,
            data_registry_db_path=data_registry_db_path,
            default_config=config,
        )

        # Generate data_id from image path (stem without extension)
        image_data_id = image_path.stem

        # Use PhotometryManager to handle the workflow
        result = manager.measure_for_fits(
            fits_path=image_path,
            create_batch_job=True,
            data_id=image_data_id,
            group_id=group_id,
        )

        if result and result.batch_job_id:
            log.info(f"Created photometry batch job {result.batch_job_id} for {image_path.name}")
            return result.batch_job_id
        return None

    except Exception as e:
        log.error(f"Failed to trigger photometry for {image_path}: {e}", exc_info=True)
        return None


def trigger_group_mosaic_creation(
    group_ms_paths: List[str],
    products_db_path: Path,
    args: argparse.Namespace,
) -> Optional[str]:
    """Trigger mosaic creation for a complete group of MS files.

    Implements tracking via register_mosaic_group() and update_mosaic_group_status()
    to prevent duplicate processing and enable queue status monitoring.

    Args:
        group_ms_paths: List of MS file paths in chronological order
        products_db_path: Path to products database
        args: Command-line arguments

    Returns:
        Mosaic path if successful, None otherwise
    """
    log = logging.getLogger("stream.mosaic")

    # Generate group ID from first MS timestamp
    first_ms = Path(group_ms_paths[0])
    import re

    match = re.search(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", first_ms.name)
    if match:
        timestamp_str = match.group(1).replace(" ", "T")
        group_id = f"mosaic_{timestamp_str.replace(':', '-').replace('.', '-')}"
    else:
        # Fallback: use hash of paths (SHA256 for security, truncated for brevity)
        import hashlib

        paths_str = "|".join(sorted(group_ms_paths))
        group_id = f"mosaic_{hashlib.sha256(paths_str.encode()).hexdigest()[:8]}"

    log.info(f"Forming mosaic group {group_id} from {len(group_ms_paths)} MS files")

    # Register mosaic group in tracking table BEFORE processing
    # This prevents duplicate triggers and enables queue monitoring
    try:
        register_mosaic_group(products_db_path, group_id, group_ms_paths, status="pending")
        log.debug(f"Registered mosaic group {group_id} with {len(group_ms_paths)} MS files")
    except Exception as e:
        log.error(f"Failed to register mosaic group {group_id}: {e}")
        return None

    try:
        # Update status to in_progress
        update_mosaic_group_status(products_db_path, group_id, "in_progress")

        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        # Initialize orchestrator
        orchestrator = MosaicOrchestrator(products_db_path=products_db_path)

        # Form group
        if not orchestrator._form_group_from_ms_paths(group_ms_paths, group_id):
            log.error(f"Failed to form group {group_id}")
            update_mosaic_group_status(
                products_db_path, group_id, "failed", error="Failed to form group"
            )
            return None

        # Process group workflow (calibration → imaging → mosaic)
        mosaic_path = orchestrator._process_group_workflow(group_id)

        if mosaic_path:
            log.info(f"Mosaic created successfully: {mosaic_path}")
            update_mosaic_group_status(
                products_db_path, group_id, "completed", mosaic_path=mosaic_path
            )
            return mosaic_path
        else:
            log.error(f"Mosaic creation failed for group {group_id}")
            update_mosaic_group_status(
                products_db_path, group_id, "failed", error="Orchestrator returned None"
            )
            return None

    except Exception as e:
        log.exception(f"Failed to trigger mosaic creation: {e}")
        update_mosaic_group_status(
            products_db_path, group_id, "failed", error=str(e)
        )
        return None


def _worker_loop(args: argparse.Namespace, queue: QueueDB) -> None:
    """Poll for pending groups, convert via orchestrator, and mark complete."""
    log = logging.getLogger("stream.worker")
    while True:
        try:
            gid = queue.acquire_next_pending()
            if gid is None:
                time.sleep(float(getattr(args, "worker_poll_interval", 5.0)))
                continue
            t0 = time.perf_counter()
            # Use group timestamp for start/end
            start_time = gid.replace("T", " ")
            end_time = start_time
            writer_type = None
            ret = 0

            # Create path mapper for organized output (default to science, will be corrected if needed)
            # Extract date from group ID to determine organized path
            extract_date_from_filename(gid)
            ms_base_dir = Path(args.output_dir)  # pylint: disable=used-before-assignment
            path_mapper = create_path_mapper(ms_base_dir, is_calibrator=False, is_failed=False)

            # Initialize calibrator status (will be updated if detection enabled)
            is_calibrator = False
            is_failed = False

            try:
                if getattr(args, "use_subprocess", False):
                    # Note: Subprocess mode doesn't support path_mapper yet
                    # Files will be written to flat location and organized afterward
                    # Validate and sanitize user-controlled arguments to prevent command injection
                    # Validate paths are absolute and exist (or are valid for creation)
                    input_dir = str(Path(args.input_dir).resolve())
                    output_dir = str(Path(args.output_dir).resolve())
                    scratch_dir = str(Path(args.scratch_dir).resolve())

                    # Validate max_workers is a reasonable integer
                    max_workers = getattr(args, "max_workers", 4)
                    try:
                        max_workers_int = int(max_workers)
                        if max_workers_int < 1 or max_workers_int > 128:
                            raise ValueError(
                                f"max_workers must be between 1 and 128, got {max_workers_int}"
                            )
                    except (ValueError, TypeError) as e:
                        log.warning(
                            f"Invalid max_workers value: {max_workers}, using default 4. Error: {e}"
                        )
                        max_workers_int = 4

                    # Validate tmpfs_path if provided
                    tmpfs_path = "/dev/shm"  # default
                    if getattr(args, "stage_to_tmpfs", False):
                        tmpfs_path_attr = getattr(args, "tmpfs_path", "/dev/shm")
                        tmpfs_path = str(Path(tmpfs_path_attr).resolve())

                    # Build command with validated arguments
                    # Static command parts (safe from injection)
                    static_cmd_parts = [
                        sys.executable,
                        "-m",
                        "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
                    ]
                    # Validated dynamic arguments (all validated above)
                    validated_args = [
                        input_dir,  # Resolved absolute path
                        output_dir,  # Resolved absolute path
                        start_time,  # From gid, not user input
                        end_time,  # From gid, not user input
                        "--writer",
                        "auto",  # Literal string
                        "--scratch-dir",
                        scratch_dir,  # Resolved absolute path
                        "--max-workers",
                        str(max_workers_int),  # Validated integer 1-128
                    ]
                    cmd = static_cmd_parts + validated_args
                    if getattr(args, "stage_to_tmpfs", False):
                        cmd.extend(["--stage-to-tmpfs", "--tmpfs-path", tmpfs_path])

                    env = os.environ.copy()
                    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
                    env.setdefault("OMP_NUM_THREADS", os.getenv("OMP_NUM_THREADS", "4"))
                    env.setdefault("MKL_NUM_THREADS", os.getenv("MKL_NUM_THREADS", "4"))
                    # Safe: Using list form (not shell=True) prevents shell injection.
                    # All user inputs validated: paths resolved to absolute, max_workers bounded 1-128
                    # Using subprocess.run() (modern API) instead of subprocess.call()
                    # Note: Semgrep warning is a false positive - all inputs are validated above
                    result = subprocess.run(cmd, env=env, check=False)  # noqa: S603
                    ret = result.returncode
                    writer_type = "auto"
                else:
                    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                        convert_subband_groups_to_ms,
                    )

                    convert_subband_groups_to_ms(
                        args.input_dir,
                        args.output_dir,
                        start_time,
                        end_time,
                        scratch_dir=args.scratch_dir,
                        writer="auto",
                        writer_kwargs={
                            "max_workers": getattr(args, "max_workers", 4),
                            "stage_to_tmpfs": getattr(args, "stage_to_tmpfs", False),
                            "tmpfs_path": getattr(args, "tmpfs_path", "/dev/shm"),
                        },
                        path_mapper=path_mapper,  # Write directly to organized location
                    )
                    ret = 0
                    writer_type = "auto"
            except Exception as exc:
                log.error("Conversion failed for %s: %s", gid, exc)
                queue.update_state(gid, "failed", error=str(exc))
                continue

            total = time.perf_counter() - t0
            queue.record_metrics(gid, total_time=total, writer_type=writer_type)
            if ret != 0:
                queue.update_state(gid, "failed", error=f"orchestrator exit={ret}")
                continue

            # Derive MS path from first subband filename (already organized if path_mapper was used)
            products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")
            try:
                files = queue.group_files(gid)
                if not files:
                    raise RuntimeError("no subband files recorded for group")
                first = os.path.basename(files[0])
                base = os.path.splitext(first)[0].split("_sb")[0]

                # Extract pointing (RA/Dec) from first HDF5 file
                ra_deg = None
                dec_deg = None
                try:
                    import astropy.units as u

                    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                        _peek_uvh5_phase_and_midtime,
                    )

                    pt_ra, pt_dec, _ = _peek_uvh5_phase_and_midtime(files[0])
                    ra_deg = float(pt_ra.to(u.deg).value)  # pylint: disable=no-member
                    dec_deg = float(pt_dec.to(u.deg).value)  # pylint: disable=no-member
                    log.debug(
                        f"Extracted pointing from HDF5: RA={ra_deg:.6f} deg, Dec={dec_deg:.6f} deg"
                    )
                except Exception as e:
                    log.warning(
                        f"Could not extract pointing from HDF5 file {files[0]}: {e}",
                        exc_info=True,
                    )

                # If path_mapper was used, MS is already in organized location
                # Otherwise, compute organized path now
                if not getattr(args, "use_subprocess", False):
                    # MS was written directly to organized location via path_mapper
                    ms_path = path_mapper(base, args.output_dir)
                    # Check if this is a calibrator MS (content-based detection)
                    if getattr(args, "enable_calibration_solving", False):
                        try:
                            ms_path_obj = Path(ms_path)
                            if ms_path_obj.exists():
                                # First try path-based detection
                                is_calibrator, is_failed = determine_ms_type(ms_path_obj)
                                # If not detected, try content-based detection
                                if not is_calibrator:
                                    is_calibrator = has_calibrator(str(ms_path_obj))
                                    if is_calibrator:
                                        log.info(
                                            f"Detected calibrator in MS content: {ms_path_obj.name}"
                                        )
                        except Exception as e:
                            log.debug(
                                f"Calibrator detection failed for {ms_path}: {e}",
                                exc_info=True,
                            )
                else:
                    # Subprocess mode: compute organized path and move if needed
                    ms_path_flat = os.path.join(args.output_dir, base + ".ms")
                    ms_path_obj = Path(ms_path_flat)
                    ms_base_dir = Path(args.output_dir)

                    # Determine MS type and organize
                    try:
                        # First try path-based detection (fast)
                        is_calibrator, is_failed = determine_ms_type(ms_path_obj)

                        # If not detected as calibrator by path, try content-based detection
                        if not is_calibrator and getattr(args, "enable_calibration_solving", False):
                            try:
                                is_calibrator = has_calibrator(str(ms_path_obj))
                                if is_calibrator:
                                    log.info(
                                        f"Detected calibrator in MS content: {ms_path_obj.name}"
                                    )
                            except Exception as e:
                                log.debug(
                                    f"Calibrator detection failed for {ms_path_obj}: {e}",
                                    exc_info=True,
                                )

                        organized_path = organize_ms_file(
                            ms_path_obj,
                            ms_base_dir,
                            Path(products_db_path),
                            is_calibrator=is_calibrator,
                            is_failed=is_failed,
                            update_database=False,  # We'll register with correct path below
                        )
                        ms_path = str(organized_path)
                        if organized_path != ms_path_obj:
                            log.info(f"Organized MS file: {ms_path_flat} → {ms_path}")
                    except Exception as e:
                        log.warning(
                            f"Failed to organize MS file {ms_path_flat}: {e}. Using flat path.",
                            exc_info=True,
                        )
                        ms_path = ms_path_flat
                        is_calibrator = False
                        is_failed = False
            except Exception as exc:
                log.error("Failed to locate MS for %s: %s", gid, exc)
                queue.update_state(gid, "completed")
                continue

            # Record conversion in products DB (stage=converted) with organized path
            try:
                conn = ensure_products_db(Path(products_db_path))
                # Extract time range
                start_mjd = end_mjd = mid_mjd = None
                try:
                    from dsa110_contimg.utils.time_utils import extract_ms_time_range

                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
                except Exception:
                    pass
                ms_index_upsert(
                    conn,
                    ms_path,  # Already organized path
                    start_mjd=start_mjd,
                    end_mjd=end_mjd,
                    mid_mjd=mid_mjd,
                    processed_at=time.time(),
                    status="converted",
                    stage="converted",
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                )

                # Log pointing to pointing_history table (in ingest database)
                if mid_mjd is not None and ra_deg is not None and dec_deg is not None:
                    try:
                        queue_db_path = getattr(args, "queue_db", None)
                        if queue_db_path:
                            ingest_conn = ensure_ingest_db(Path(queue_db_path))
                            log_pointing(ingest_conn, mid_mjd, ra_deg, dec_deg)
                            ingest_conn.close()
                            log.debug(
                                f"Logged pointing to pointing_history: MJD={mid_mjd:.6f}, "
                                f"RA={ra_deg:.6f} deg, Dec={dec_deg:.6f} deg"
                            )
                    except Exception as e:
                        log.warning(
                            f"Failed to log pointing to pointing_history: {e}",
                            exc_info=True,
                        )

                conn.commit()
            except Exception:
                log.debug("ms_index conversion upsert failed", exc_info=True)

            # Solve calibration if this is a calibrator MS (before applying to science MS)
            if is_calibrator and getattr(args, "enable_calibration_solving", False):
                try:
                    log.info(f"Solving calibration for calibrator MS: {ms_path}")
                    success, error_msg = solve_calibration_for_ms(ms_path, do_k=False)
                    if success:
                        # Register calibration tables in registry
                        try:
                            # Extract calibration table prefix (MS path without .ms extension)
                            cal_prefix = Path(ms_path).with_suffix("")
                            register_set_from_prefix(
                                Path(args.registry_db),
                                set_name=f"cal_{gid}",
                                prefix=cal_prefix,
                                cal_field=None,  # Auto-detected during solve
                                refant=None,  # Auto-detected during solve
                                valid_start_mjd=mid_mjd,
                                valid_end_mjd=None,  # No end time limit
                            )
                            log.info(
                                f"Registered calibration tables for {ms_path} "
                                f"in registry (set_name=cal_{gid})"
                            )
                        except Exception as e:
                            log.warning(
                                f"Failed to register calibration tables: {e}",
                                exc_info=True,
                            )
                    else:
                        log.error(f"Calibration solve failed for {ms_path}: {error_msg}")
                except Exception as e:
                    log.warning(
                        f"Calibration solve exception for {ms_path}: {e}",
                        exc_info=True,
                    )

            # Update ingest_queue with calibrator status
            try:
                conn_queue = queue.conn
                conn_queue.execute(
                    "UPDATE ingest_queue SET has_calibrator = ? WHERE group_id = ?",
                    (1 if is_calibrator else 0, gid),
                )
                conn_queue.commit()
            except Exception as e:
                log.debug(f"Failed to update has_calibrator in ingest_queue: {e}")

            # Apply calibration from registry if available, then image (development tier)
            try:
                # Determine mid_mjd for applylist
                if mid_mjd is None:
                    # fallback: try extract_ms_time_range again (it has multiple fallbacks)
                    try:
                        from dsa110_contimg.utils.time_utils import (
                            extract_ms_time_range,
                        )

                        _, _, mid_mjd = extract_ms_time_range(ms_path)
                    except Exception:
                        pass

                applylist = []
                try:
                    applylist = get_active_applylist(
                        Path(args.registry_db),
                        (float(mid_mjd) if mid_mjd is not None else time.time() / 86400.0),
                    )
                except Exception:
                    applylist = []

                cal_applied = 0
                if applylist:
                    try:
                        apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                        cal_applied = 1
                    except Exception:
                        log.warning("applycal failed for %s", ms_path, exc_info=True)

                # Standard tier imaging (production quality)
                # Note: Data is always reordered for correct multi-SPW processing
                imgroot = os.path.join(args.output_dir, base + ".img")
                try:
                    image_ms(
                        ms_path,
                        imagename=imgroot,
                        field="",
                        quality_tier="standard",
                        skip_fits=False,
                    )

                    # Run catalog-based flux scale validation
                    try:
                        from pathlib import Path

                        from dsa110_contimg.qa.catalog_validation import (
                            validate_flux_scale,
                        )

                        # Find PB-corrected FITS image (preferred for validation)
                        pbcor_fits = f"{imgroot}.pbcor.fits"
                        fits_image = pbcor_fits if Path(pbcor_fits).exists() else f"{imgroot}.fits"

                        if Path(fits_image).exists():
                            log.info(
                                f"Running catalog-based flux scale validation (NVSS) on {fits_image}"
                            )
                            result = validate_flux_scale(
                                image_path=fits_image,
                                catalog="nvss",
                                min_snr=5.0,
                                flux_range_jy=(0.01, 10.0),
                                max_flux_ratio_error=0.2,
                            )

                            if result.n_matched > 0:
                                log.info(
                                    f"Catalog validation (NVSS): {result.n_matched} sources matched, "
                                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                                    f"scale error={result.flux_scale_error * 100:.1f}%"
                                )
                                if result.has_issues:
                                    log.warning(
                                        f"Catalog validation issues: {', '.join(result.issues)}"
                                    )
                                if result.has_warnings:
                                    log.warning(
                                        f"Catalog validation warnings: {', '.join(result.warnings)}"
                                    )
                            else:
                                log.warning("Catalog validation: No sources matched")
                        else:
                            log.debug(
                                f"Catalog validation skipped: FITS image not found ({fits_image})"
                            )
                    except Exception as e:
                        log.warning(f"Catalog validation failed (non-fatal): {e}")

                except Exception:
                    log.error("imaging failed for %s", ms_path, exc_info=True)

                # Update products DB with imaging artifacts and stage
                try:
                    products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")
                    conn = ensure_products_db(Path(products_db_path))
                    ms_index_upsert(
                        conn,
                        ms_path,
                        status="done",
                        stage="imaged",
                        cal_applied=cal_applied,
                        imagename=imgroot,
                    )
                    # Insert images
                    now_ts = time.time()
                    for suffix, pbcor in [
                        (".image", 0),
                        (".pb", 0),
                        (".pbcor", 1),
                        (".residual", 0),
                        (".model", 0),
                    ]:
                        p = f"{imgroot}{suffix}"
                        if os.path.isdir(p) or os.path.isfile(p):
                            images_insert(conn, p, ms_path, now_ts, "5min", pbcor)
                    conn.commit()

                    # Trigger photometry if enabled
                    if getattr(args, "enable_photometry", False):
                        try:
                            # Use PB-corrected FITS if available, otherwise regular FITS
                            pbcor_fits = f"{imgroot}.pbcor.fits"
                            fits_image = (
                                pbcor_fits if Path(pbcor_fits).exists() else f"{imgroot}.fits"
                            )

                            if Path(fits_image).exists():
                                log.info(f"Triggering photometry for {Path(fits_image).name}")
                                products_db_path = Path(
                                    os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")
                                )
                                photometry_job_id = trigger_photometry_for_image(
                                    image_path=Path(fits_image),
                                    group_id=gid,
                                    args=args,
                                    products_db_path=products_db_path,
                                )
                                if photometry_job_id:
                                    log.info(
                                        f"Photometry job {photometry_job_id} created for {Path(fits_image).name}"
                                    )
                                    # Link photometry job to data registry if possible
                                    try:
                                        from dsa110_contimg.database.data_registry import (
                                            ensure_data_registry_db,
                                            link_photometry_to_data,
                                        )

                                        registry_db_path = Path(
                                            os.getenv(
                                                "DATA_REGISTRY_DB",
                                                str(
                                                    products_db_path.parent
                                                    / "data_registry.sqlite3"
                                                ),
                                            )
                                        )
                                        registry_conn = ensure_data_registry_db(registry_db_path)
                                        # Generate data_id from image path (stem without extension)
                                        image_data_id = Path(fits_image).stem
                                        if link_photometry_to_data(
                                            registry_conn,
                                            image_data_id,
                                            str(photometry_job_id),
                                        ):
                                            log.debug(
                                                f"Linked photometry job {photometry_job_id} to data_id {image_data_id}"
                                            )
                                        else:
                                            log.debug(
                                                f"Could not link photometry job (data_id {image_data_id} may not exist in registry)"
                                            )
                                        registry_conn.close()
                                    except Exception as e:
                                        log.debug(
                                            f"Failed to link photometry to data registry (non-fatal): {e}"
                                        )
                                else:
                                    log.warning(
                                        f"No photometry job created for {Path(fits_image).name}"
                                    )
                            else:
                                log.debug(
                                    f"Photometry skipped: FITS image not found ({fits_image})"
                                )
                        except Exception as e:
                            log.warning(
                                f"Photometry trigger failed (non-fatal): {e}",
                                exc_info=True,
                            )

                    # Check for complete group and trigger mosaic creation if enabled
                    if getattr(args, "enable_group_imaging", False):
                        try:
                            products_db_path = os.getenv(
                                "PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3"
                            )
                            group_ms_paths = check_for_complete_group(
                                ms_path, Path(products_db_path)
                            )

                            if group_ms_paths:
                                log.info(f"Complete group detected: {len(group_ms_paths)} MS files")
                                if getattr(args, "enable_mosaic_creation", False):
                                    mosaic_path = trigger_group_mosaic_creation(
                                        group_ms_paths,
                                        Path(products_db_path),
                                        args,
                                    )
                                    if mosaic_path:
                                        # Trigger QA and publishing if enabled
                                        if getattr(args, "enable_auto_qa", False):
                                            try:
                                                from dsa110_contimg.database.data_registry import (
                                                    ensure_data_registry_db,
                                                    finalize_data,
                                                    trigger_auto_publish,
                                                )

                                                registry_conn = ensure_data_registry_db(
                                                    Path(products_db_path)
                                                )
                                                # Register mosaic in data registry
                                                mosaic_id = Path(mosaic_path).stem
                                                finalize_data(
                                                    registry_conn,
                                                    data_id=mosaic_id,
                                                    qa_status="pending",
                                                    validation_status="pending",
                                                )
                                                # Trigger auto-publish if enabled
                                                if getattr(args, "enable_auto_publish", False):
                                                    trigger_auto_publish(registry_conn, mosaic_id)
                                                registry_conn.close()
                                                log.info(
                                                    f"Mosaic {mosaic_id} registered and QA triggered"
                                                )
                                            except Exception as e:
                                                log.warning(
                                                    f"Failed to trigger QA/publishing for mosaic: {e}",
                                                    exc_info=True,
                                                )
                                else:
                                    log.debug("Group imaging enabled but mosaic creation disabled")
                        except Exception as e:
                            log.debug(
                                f"Group detection/mosaic creation check failed: {e}",
                                exc_info=True,
                            )
                except Exception:
                    log.debug("products DB update failed", exc_info=True)
            except Exception:
                log.exception("post-conversion processing failed for %s", gid)

            queue.update_state(gid, "completed")
            log.info("Completed %s in %.2fs", gid, total)
        except Exception:
            log.exception("Worker loop error")
            time.sleep(2.0)


def _start_watch(args: argparse.Namespace, queue: QueueDB) -> Optional[object]:
    log = logging.getLogger("stream.watch")
    input_dir = Path(args.input_dir)
    if HAVE_WATCHDOG:
        handler = _FSHandler(queue)
        obs = Observer()
        obs.schedule(handler, str(input_dir), recursive=False)
        obs.start()
        log.info("Watchdog monitoring %s", input_dir)
        return obs
    log.info("Watchdog not available; using polling fallback")
    return None


def _polling_loop(args: argparse.Namespace, queue: QueueDB) -> None:
    """Poll directory for new HDF5 files and record them.

    PERFORMANCE: Uses database UNIQUE constraint on path column to handle
    deduplication automatically via INSERT ... ON CONFLICT DO NOTHING.
    This eliminates the need for unbounded in-memory sets that would consume
    gigabytes of RAM for observatories ingesting millions of files.

    The database efficiently handles duplicate detection, and the polling
    interval provides natural rate limiting, making this approach both
    simpler and more scalable than manual cache management.
    """
    log = logging.getLogger("stream.poll")
    input_dir = Path(args.input_dir)
    interval = float(getattr(args, "poll_interval", 5.0))

    while True:
        try:
            new_count = 0
            for p in input_dir.glob("*_sb??.hdf5"):
                info = parse_subband_info(p)
                if info is None:
                    continue

                gid, sb = info
                try:
                    # Let database handle deduplication via UNIQUE index on path
                    queue.record_subband(gid, sb, p)
                    new_count += 1
                except sqlite3.IntegrityError:
                    # File already registered - silently skip
                    # This is expected behavior, not an error
                    pass

            if new_count > 0:
                log.debug(f"Polling: registered {new_count} new files")

            time.sleep(interval)
        except Exception:
            log.exception("Polling loop error")
            time.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DSA-110 streaming converter")
    p.add_argument("--input-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--queue-db", default="state/db/ingest.sqlite3")
    p.add_argument("--registry-db", default="state/db/cal_registry.sqlite3")
    p.add_argument("--scratch-dir", default="/stage/dsa110-contimg")
    p.add_argument("--expected-subbands", type=int, default=16)
    p.add_argument("--chunk-duration", type=float, default=5.0, help="Minutes per group")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--use-subprocess", action="store_true")
    p.add_argument("--monitoring", action="store_true")
    p.add_argument("--monitor-interval", type=float, default=60.0)
    p.add_argument("--poll-interval", type=float, default=5.0)
    p.add_argument("--worker-poll-interval", type=float, default=5.0)
    p.add_argument("--max-workers", type=int, default=4)
    p.add_argument(
        "--enable-calibration-solving",
        action="store_true",
        help="Enable automatic calibration solving for calibrator MS files",
    )
    p.add_argument(
        "--enable-group-imaging",
        action="store_true",
        help="Enable group detection and coordinated imaging after individual MS imaging",
    )
    p.add_argument(
        "--enable-mosaic-creation",
        action="store_true",
        help="Enable automatic mosaic creation when complete group detected",
    )
    p.add_argument(
        "--enable-auto-qa",
        action="store_true",
        help="Enable automatic QA validation after mosaic creation",
    )
    p.add_argument(
        "--enable-auto-publish",
        action="store_true",
        help="Enable automatic publishing after QA passes",
    )
    p.add_argument(
        "--enable-photometry",
        action="store_true",
        help="Enable automatic photometry measurement after imaging",
    )
    p.add_argument(
        "--photometry-catalog",
        default="nvss",
        choices=["nvss", "first", "rax", "vlass", "master", "atnf"],
        help="Catalog to use for source queries (default: nvss)",
    )
    p.add_argument(
        "--photometry-radius",
        type=float,
        default=0.5,
        help="Search radius in degrees for source queries (default: 0.5)",
    )
    p.add_argument(
        "--photometry-normalize",
        action="store_true",
        help="Enable photometry normalization",
    )
    p.add_argument(
        "--photometry-max-sources",
        type=int,
        default=None,
        help="Maximum number of sources to measure (default: no limit)",
    )
    p.add_argument("--stage-to-tmpfs", action="store_true")
    p.add_argument("--tmpfs-path", default="/dev/shm")
    p.set_defaults(enable_photometry=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Set CASA log directory before any CASA task calls
    from dsa110_contimg.utils.cli_helpers import setup_casa_environment

    setup_casa_environment()
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    # PRECONDITION CHECK: Validate input/output directories before proceeding
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # before starting file watching and processing.
    log = logging.getLogger("stream")

    # Validate input directory
    input_path = Path(args.input_dir)
    if not input_path.exists():
        log.error(f"Input directory does not exist: {args.input_dir}")
        return 1
    if not input_path.is_dir():
        log.error(f"Input path is not a directory: {args.input_dir}")
        return 1
    if not os.access(args.input_dir, os.R_OK):
        log.error(f"Input directory is not readable: {args.input_dir}")
        return 1

    # Validate output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not output_path.exists():
        log.error(f"Failed to create output directory: {args.output_dir}")
        return 1
    if not output_path.is_dir():
        log.error(f"Output path is not a directory: {args.output_dir}")
        return 1
    if not os.access(args.output_dir, os.W_OK):
        log.error(f"Output directory is not writable: {args.output_dir}")
        return 1

    # Validate scratch directory if provided
    if hasattr(args, "scratch_dir") and args.scratch_dir:
        scratch_path = Path(args.scratch_dir)
        scratch_path.mkdir(parents=True, exist_ok=True)
        if not scratch_path.exists():
            log.error(f"Failed to create scratch directory: {args.scratch_dir}")
            return 1
        if not os.access(args.scratch_dir, os.W_OK):
            log.error(f"Scratch directory is not writable: {args.scratch_dir}")
            return 1

    log.info("✓ Directory validation passed")

    # OPTIMIZATION: Warm up JIT-compiled functions before first observation
    # This eliminates compilation latency during time-critical processing
    try:
        from dsa110_contimg.utils.numba_accel import NUMBA_AVAILABLE, warm_up_jit
        if NUMBA_AVAILABLE:
            t0 = time.time()
            warm_up_jit()
            log.info(f"✓ JIT functions warmed up in {time.time() - t0:.2f}s")
    except ImportError:
        log.debug("Numba not available, skipping JIT warm-up")

    phot_worker = None
    if getattr(args, "enable_photometry", False):
        products_db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3"))
        phot_worker = PhotometryBatchWorker(
            products_db_path=products_db_path,
            poll_interval=float(args.worker_poll_interval),
            max_workers=getattr(args, "max_workers", None),
        )
        phot_worker.start()
        log.info("Photometry batch worker started")

    qdb = QueueDB(
        Path(args.queue_db),
        expected_subbands=int(args.expected_subbands),
        chunk_duration_minutes=float(args.chunk_duration),
    )
    try:
        qdb.bootstrap_directory(Path(args.input_dir))
    except Exception:
        logging.getLogger("stream").exception("Bootstrap failed")

    obs = _start_watch(args, qdb)

    worker = threading.Thread(target=_worker_loop, args=(args, qdb), daemon=True)
    worker.start()

    if obs is None:
        poller = threading.Thread(target=_polling_loop, args=(args, qdb), daemon=True)
        poller.start()

    if getattr(args, "monitoring", False):
        log = logging.getLogger("stream.monitor")
        while True:
            try:
                with qdb._lock:
                    cur = qdb._conn.execute(
                        "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state"
                    ).fetchall()
                stats = {r[0]: r[1] for r in cur}
                log.info("Queue stats: %s", stats)
            except Exception:
                log.debug("Monitor failed", exc_info=True)
            time.sleep(float(args.monitor_interval))
    else:
        try:
            while True:
                time.sleep(60.0)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main())

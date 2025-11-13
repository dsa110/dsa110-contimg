#!/usr/bin/env python3
"""
Streaming converter service for DSA-110 UVH5 subband groups.

This daemon watches an ingest directory for new *_sb??.hdf5 files, queues
complete 16-subband groups, and invokes the existing batch converter on each
group using a scratch directory for staging.

The queue is persisted in SQLite so the service can resume after restarts.
"""

from dsa110_contimg.database.registry import (
    get_active_applylist,
    register_set_from_prefix,
)
import argparse
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

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
from dsa110_contimg.calibration.calibration import (  # noqa
    solve_bandpass,
    solve_delay,
    solve_gains,
)
from dsa110_contimg.calibration.streaming import (  # noqa
    has_calibrator,
    solve_calibration_for_ms,
)
from dsa110_contimg.database.products import (  # noqa
    ensure_products_db,
    images_insert,
    log_pointing,
    ms_index_upsert,
)
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db  # noqa
from dsa110_contimg.imaging.cli import image_ms  # noqa
from dsa110_contimg.photometry.helpers import (  # noqa
    query_sources_for_fits,
)
from dsa110_contimg.utils.ms_organization import (  # noqa
    create_path_mapper,
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

    def __init__(
        self,
        path: Path,
        expected_subbands: int = 16,
        chunk_duration_minutes: float = 5.0,
    ) -> None:
        self.path = path
        self.expected_subbands = expected_subbands
        self.chunk_duration_minutes = chunk_duration_minutes
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
                    for row in self._conn.execute(
                        "PRAGMA table_info(ingest_queue)"
                    ).fetchall()
                }
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive path
                logging.error("Failed to inspect ingest_queue schema: %s", exc)
                return

            altered = False
            if "checkpoint_path" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN checkpoint_path TEXT"
                )
                altered = True
            if "processing_stage" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN processing_stage TEXT DEFAULT 'collecting'"
                )
                self._conn.execute(
                    "UPDATE ingest_queue SET processing_stage = 'collecting' WHERE processing_stage IS NULL"
                )
                altered = True
            if "chunk_minutes" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN chunk_minutes REAL"
                )
                altered = True
            if "expected_subbands" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN expected_subbands INTEGER"
                )
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
                rows = self._conn.execute(
                    "SELECT group_id FROM ingest_queue"
                ).fetchall()
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
                    for row in self._conn.execute(
                        "PRAGMA table_info(ingest_queue)"
                    ).fetchall()
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
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN calibrators TEXT"
                )
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
                    logging.info(
                        "Updated performance_metrics schema with writer_type column."
                    )
                except sqlite3.DatabaseError:
                    pass

    def record_subband(self, group_id: str, subband_idx: int, file_path: Path) -> None:
        """Record a subband file arrival.

        CRITICAL: Uses explicit transaction boundaries for thread safety.
        All operations within this method are atomic.
        """
        now = time.time()
        normalized_group = self._normalize_group_id_datetime(group_id)
        with self._lock:
            try:
                # CRITICAL: Use explicit transaction for atomicity
                # This ensures all operations succeed or fail together
                self._conn.execute("BEGIN")
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO ingest_queue (group_id, state, received_at, last_update, chunk_minutes, expected_subbands)
                    VALUES (?, 'collecting', ?, ?, ?, ?)
                    """,
                    (
                        normalized_group,
                        now,
                        now,
                        self.chunk_duration_minutes,
                        self.expected_subbands,
                    ),
                )
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO subband_files (group_id, subband_idx, path)
                    VALUES (?, ?, ?)
                    """,
                    (normalized_group, subband_idx, str(file_path)),
                )
                self._conn.execute(
                    """
                    UPDATE ingest_queue
                       SET last_update = ?
                     WHERE group_id = ?
                    """,
                    (now, normalized_group),
                )
                count = self._conn.execute(
                    "SELECT COUNT(*) FROM subband_files WHERE group_id = ?",
                    (normalized_group,),
                ).fetchone()[0]
                if count >= self.expected_subbands:
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET state = CASE WHEN state = 'completed' THEN state ELSE 'pending' END,
                               last_update = ?
                         WHERE group_id = ?
                        """,
                        (now, normalized_group),
                    )
                # Commit transaction
                self._conn.commit()
            except Exception:
                # Rollback on any error to maintain consistency
                self._conn.rollback()
                raise

    def bootstrap_directory(self, input_dir: Path) -> None:
        logging.info("Bootstrapping queue from existing files in %s", input_dir)

        # Pre-fetch existing registered paths to avoid redundant DB operations
        with self._lock:
            existing_paths = {
                row[0]
                for row in self._conn.execute(
                    "SELECT path FROM subband_files"
                ).fetchall()
            }

        new_count = 0
        skipped_count = 0
        for path in sorted(input_dir.glob("*_sb??.hdf5")):
            path_str = str(path)
            # Skip if already registered
            if path_str in existing_paths:
                skipped_count += 1
                continue

            info = parse_subband_info(path)
            if info is None:
                continue
            group_id, subband_idx = info
            self.record_subband(group_id, subband_idx, path)
            new_count += 1

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

    def update_state(
        self, group_id: str, state: str, error: Optional[str] = None
    ) -> None:
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
                    self._conn.execute(
                        f"""
                        INSERT OR REPLACE INTO performance_metrics ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        """,
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

        # Quick HDF5 structure check
        try:
            import h5py

            with h5py.File(path, "r") as f:
                # Verify file has required structure (Header or Data group)
                if "Header" not in f and "Data" not in f:
                    log.warning(f"File does not appear to be valid HDF5/UVH5: {path}")
                    return
        except Exception as e:
            log.warning(f"File is not readable HDF5: {path}. Error: {e}")
            return

        # File passed all checks, record in queue
        try:
            self.queue.record_subband(gid, sb, p)
        except Exception:
            logging.getLogger("stream").debug(
                "record_subband failed for %s", p, exc_info=True
            )

    def on_created(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):  # pragma: no cover - defensive
            return
        self._maybe_record(event.src_path)

    def on_moved(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):  # pragma: no cover - defensive
            return
        self._maybe_record(event.dest_path)


def check_for_complete_group(
    ms_path: str, products_db_path: Path, time_window_minutes: float = 25.0
) -> Optional[List[str]]:
    """Check if a complete group (10 MS files) exists within time window.

    Args:
        ms_path: Path to MS file that was just imaged
        products_db_path: Path to products database
        time_window_minutes: Time window in minutes (±window/2 around MS mid_mjd)

    Returns:
        List of MS paths in complete group, or None if group incomplete
    """
    import sqlite3

    conn = sqlite3.connect(str(products_db_path))

    try:
        # Get mid_mjd for this MS
        cursor = conn.execute(
            "SELECT mid_mjd FROM ms_index WHERE path = ?", (ms_path,)
        )
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None

        mid_mjd = row[0]
        window_half_days = time_window_minutes / (2 * 24 * 60)

        # Query for MS files in same time window that are imaged
        cursor = conn.execute(
            """
            SELECT path FROM ms_index
            WHERE mid_mjd BETWEEN ? AND ?
            AND stage = 'imaged'
            AND status = 'done'
            ORDER BY mid_mjd
            """,
            (mid_mjd - window_half_days, mid_mjd + window_half_days),
        )

        ms_paths = [row[0] for row in cursor.fetchall()]

        # Check if we have a complete group (10 MS files = 50 minutes)
        if len(ms_paths) >= 10:
            return ms_paths[:10]  # Return first 10 for consistent group size
        return None
    finally:
        conn.close()


def trigger_photometry_for_image(
    image_path: Path,
    group_id: str,
    args: argparse.Namespace,
    products_db_path: Optional[Path] = None,
) -> Optional[int]:
    """Trigger photometry measurement for a newly imaged FITS file.

    Args:
        image_path: Path to FITS image file
        group_id: Group ID for tracking
        args: Command-line arguments with photometry configuration
        products_db_path: Path to products database (optional)

    Returns:
        Batch job ID if successful, None otherwise
    """
    log = logging.getLogger("stream.photometry")

    if not image_path.exists():
        log.warning(f"FITS image not found: {image_path}")
        return None

    try:
        from dsa110_contimg.api.batch_jobs import create_batch_photometry_job
        from dsa110_contimg.database.products import ensure_products_db

        # Query sources for the image field
        sources = query_sources_for_fits(
            image_path,
            catalog=getattr(args, "photometry_catalog", "nvss"),
            radius_deg=getattr(args, "photometry_radius", 0.5),
            max_sources=getattr(args, "photometry_max_sources", None),
        )

        if not sources:
            log.info(f"No sources found for photometry in {image_path}")
            return None

        # Extract coordinates from sources
        coordinates = [
            {"ra_deg": float(src.get("ra", src.get("ra_deg", 0.0))), "dec_deg": float(src.get("dec", src.get("dec_deg", 0.0)))}
            for src in sources
        ]

        log.info(
            f"Found {len(coordinates)} sources for photometry in {image_path.name}"
        )

        # Prepare batch job parameters
        params = {
            "method": "peak",
            "normalize": getattr(args, "photometry_normalize", False),
        }

        # Get products DB connection
        if products_db_path is None:
            products_db_path = Path(
                os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")
            )
        conn = ensure_products_db(products_db_path)

        # Generate data_id from image path (stem without extension)
        image_data_id = image_path.stem

        # Create batch photometry job
        batch_job_id = create_batch_photometry_job(
            conn=conn,
            job_type="batch_photometry",
            fits_paths=[str(image_path)],
            coordinates=coordinates,
            params=params,
            data_id=image_data_id,
        )

        log.info(f"Created photometry batch job {batch_job_id} for {image_path.name}")
        return batch_job_id

    except Exception as e:
        log.error(
            f"Failed to trigger photometry for {image_path}: {e}", exc_info=True
        )
        return None


def trigger_group_mosaic_creation(
    group_ms_paths: List[str],
    products_db_path: Path,
    args: argparse.Namespace,
) -> Optional[str]:
    """Trigger mosaic creation for a complete group of MS files.

    Args:
        group_ms_paths: List of MS file paths in chronological order
        products_db_path: Path to products database
        args: Command-line arguments

    Returns:
        Mosaic path if successful, None otherwise
    """
    log = logging.getLogger("stream.mosaic")

    try:
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        # Initialize orchestrator
        orchestrator = MosaicOrchestrator(products_db_path=products_db_path)

        # Generate group ID from first MS timestamp
        # Extract timestamp from first MS path
        first_ms = Path(group_ms_paths[0])
        # Try to extract timestamp from filename (format: YYYY-MM-DDTHH:MM:SS)
        import re

        match = re.search(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", first_ms.name)
        if match:
            timestamp_str = match.group(1).replace(" ", "T")
            group_id = f"mosaic_{timestamp_str.replace(':', '-').replace('.', '-')}"
        else:
            # Fallback: use hash of paths
            import hashlib

            paths_str = "|".join(sorted(group_ms_paths))
            group_id = f"mosaic_{hashlib.md5(paths_str.encode()).hexdigest()[:8]}"

        log.info(f"Forming mosaic group {group_id} from {len(group_ms_paths)} MS files")

        # Form group
        if not orchestrator._form_group_from_ms_paths(group_ms_paths, group_id):
            log.error(f"Failed to form group {group_id}")
            return None

        # Process group workflow (calibration → imaging → mosaic)
        mosaic_path = orchestrator._process_group_workflow(group_id)

        if mosaic_path:
            log.info(f"Mosaic created successfully: {mosaic_path}")
            return mosaic_path
        else:
            log.error(f"Mosaic creation failed for group {group_id}")
            return None

    except Exception as e:
        log.exception(f"Failed to trigger mosaic creation: {e}")
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
            date_str = extract_date_from_filename(gid)
            ms_base_dir = Path(args.output_dir)
            path_mapper = create_path_mapper(
                ms_base_dir, is_calibrator=False, is_failed=False
            )

            # Initialize calibrator status (will be updated if detection enabled)
            is_calibrator = False
            is_failed = False
            
            try:
                if getattr(args, "use_subprocess", False):
                    # Note: Subprocess mode doesn't support path_mapper yet
                    # Files will be written to flat location and organized afterward
                    cmd = [
                        sys.executable,
                        "-m",
                        "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
                        args.input_dir,
                        args.output_dir,
                        start_time,
                        end_time,
                        "--writer",
                        "auto",
                        "--scratch-dir",
                        args.scratch_dir,
                        "--max-workers",
                        str(getattr(args, "max_workers", 4)),
                    ]
                    if getattr(args, "stage_to_tmpfs", False):
                        cmd.append("--stage-to-tmpfs")
                        cmd.extend(
                            ["--tmpfs-path", getattr(args, "tmpfs_path", "/dev/shm")]
                        )
                    env = os.environ.copy()
                    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
                    env.setdefault("OMP_NUM_THREADS", os.getenv("OMP_NUM_THREADS", "4"))
                    env.setdefault("MKL_NUM_THREADS", os.getenv("MKL_NUM_THREADS", "4"))
                    ret = subprocess.call(cmd, env=env)
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
            products_db_path = os.getenv(
                "PIPELINE_PRODUCTS_DB", "state/products.sqlite3"
            )
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
                    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                        _peek_uvh5_phase_and_midtime,
                    )
                    import astropy.units as u

                    pt_ra, pt_dec, _ = _peek_uvh5_phase_and_midtime(files[0])
                    ra_deg = float(pt_ra.to(u.deg).value)
                    dec_deg = float(pt_dec.to(u.deg).value)
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

                # Log pointing to pointing_history table
                if mid_mjd is not None and ra_deg is not None and dec_deg is not None:
                    try:
                        log_pointing(conn, mid_mjd, ra_deg, dec_deg)
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
            cal_solved = 0
            if is_calibrator and getattr(args, "enable_calibration_solving", False):
                try:
                    log.info(f"Solving calibration for calibrator MS: {ms_path}")
                    success, error_msg = solve_calibration_for_ms(ms_path, do_k=False)
                    if success:
                        cal_solved = 1
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
                        log.error(
                            f"Calibration solve failed for {ms_path}: {error_msg}"
                        )
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
                        (
                            float(mid_mjd)
                            if mid_mjd is not None
                            else time.time() / 86400.0
                        ),
                    )
                except Exception:
                    applylist = []

                cal_applied = 0
                if applylist:
                    try:
                        apply_to_target(
                            ms_path, field="", gaintables=applylist, calwt=True
                        )
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
                        fits_image = (
                            pbcor_fits
                            if Path(pbcor_fits).exists()
                            else f"{imgroot}.fits"
                        )

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
                                    f"scale error={result.flux_scale_error*100:.1f}%"
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
                    products_db_path = os.getenv(
                        "PIPELINE_PRODUCTS_DB", "state/products.sqlite3"
                    )
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
                                pbcor_fits
                                if Path(pbcor_fits).exists()
                                else f"{imgroot}.fits"
                            )

                            if Path(fits_image).exists():
                                log.info(
                                    f"Triggering photometry for {Path(fits_image).name}"
                                )
                                products_db_path = Path(
                                    os.getenv(
                                        "PIPELINE_PRODUCTS_DB", "state/products.sqlite3"
                                    )
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
                                                str(products_db_path.parent / "data_registry.sqlite3"),
                                            )
                                        )
                                        registry_conn = ensure_data_registry_db(registry_db_path)
                                        # Generate data_id from image path (stem without extension)
                                        image_data_id = Path(fits_image).stem
                                        if link_photometry_to_data(
                                            registry_conn, image_data_id, str(photometry_job_id)
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
                                f"Photometry trigger failed (non-fatal): {e}", exc_info=True
                            )

                    # Check for complete group and trigger mosaic creation if enabled
                    if getattr(args, "enable_group_imaging", False):
                        try:
                            products_db_path = os.getenv(
                                "PIPELINE_PRODUCTS_DB", "state/products.sqlite3"
                            )
                            group_ms_paths = check_for_complete_group(
                                ms_path, Path(products_db_path)
                            )

                            if group_ms_paths:
                                log.info(
                                    f"Complete group detected: {len(group_ms_paths)} MS files"
                                )
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
                                                    data_type="mosaic",
                                                    data_id=mosaic_id,
                                                    stage_path=mosaic_path,
                                                    auto_publish=getattr(
                                                        args, "enable_auto_publish", False
                                                    ),
                                                )
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
                                    log.debug(
                                        "Group imaging enabled but mosaic creation disabled"
                                    )
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
    log = logging.getLogger("stream.poll")
    input_dir = Path(args.input_dir)
    interval = float(getattr(args, "poll_interval", 5.0))

    # Pre-fetch existing registered paths from database to avoid redundant work
    # This persists across restarts, unlike an in-memory set
    with queue._lock:
        existing_paths = {
            row[0]
            for row in queue._conn.execute("SELECT path FROM subband_files").fetchall()
        }

    while True:
        try:
            new_count = 0
            skipped_count = 0
            for p in input_dir.glob("*_sb??.hdf5"):
                sp = os.fspath(p)
                # Skip if already registered in database
                if sp in existing_paths:
                    skipped_count += 1
                    continue

                info = parse_subband_info(p)
                if info is None:
                    continue
                gid, sb = info
                queue.record_subband(gid, sb, p)
                existing_paths.add(sp)  # Update in-memory set
                new_count += 1

            if new_count > 0:
                log.debug(
                    f"Polling: {new_count} new files, {skipped_count} already registered"
                )

            time.sleep(interval)
        except Exception:
            log.exception("Polling loop error")
            time.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DSA-110 streaming converter")
    p.add_argument("--input-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--queue-db", default="state/ingest.sqlite3")
    p.add_argument("--registry-db", default="state/cal_registry.sqlite3")
    p.add_argument("--scratch-dir", default="/stage/dsa110-contimg")
    p.add_argument("--expected-subbands", type=int, default=16)
    p.add_argument(
        "--chunk-duration", type=float, default=5.0, help="Minutes per group"
    )
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
        choices=["nvss", "first", "rax", "vlass", "master"],
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

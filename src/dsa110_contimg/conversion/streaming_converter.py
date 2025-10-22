#!/usr/bin/env python3
"""
Streaming converter service for DSA-110 UVH5 subband groups.

This daemon watches an ingest directory for new *_sb??.hdf5 files, queues
complete 16-subband groups, and invokes the existing batch converter on each
group using a scratch directory for staging.

The queue is persisted in SQLite so the service can resume after restarts.
"""

import argparse
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

import sys
try:
    from dsa110_contimg.utils.graphiti_logging import GraphitiRunLogger
except Exception:  # pragma: no cover - optional helper
    class GraphitiRunLogger:  # type: ignore
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def log_consumes(self, *a, **k): pass
        def log_produces(self, *a, **k): pass
from casatasks import concat as casa_concat  # noqa
from casacore.tables import table  # noqa
from dsa110_contimg.calibration.calibration import solve_delay, solve_bandpass, solve_gains  # noqa
from dsa110_contimg.calibration.applycal import apply_to_target  # noqa
from dsa110_contimg.imaging.cli import image_ms  # noqa
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db, register_set_from_prefix, get_active_applylist  # noqa
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert, images_insert  # noqa

try:  # Optional dependency for efficient file watching
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAVE_WATCHDOG = True
except ImportError:  # pragma: no cover - fallback path
    HAVE_WATCHDOG = False


GROUP_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<index>\d{2})\.hdf5$"
)


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
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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
                    for row in self._conn.execute("PRAGMA table_info(ingest_queue)").fetchall()
                }
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive path
                logging.error("Failed to inspect ingest_queue schema: %s", exc)
                return

            altered = False
            if "checkpoint_path" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN checkpoint_path TEXT")
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
                    "ALTER TABLE ingest_queue ADD COLUMN chunk_minutes REAL")
                altered = True
            if "expected_subbands" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN expected_subbands INTEGER")
                # Fill default for existing rows to current config value
                try:
                    self._conn.execute(
                        "UPDATE ingest_queue SET expected_subbands = ? WHERE expected_subbands IS NULL",
                        (self.expected_subbands,)
                    )
                except sqlite3.DatabaseError:
                    pass

            if "has_calibrator" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN has_calibrator INTEGER DEFAULT NULL")
                altered = True
            if "calibrators" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN calibrators TEXT")
                altered = True

            if altered:
                logging.info(
                    "Updated ingest_queue schema with new metadata columns.")

        # Migrate performance_metrics
        with self._lock, self._conn:
            try:
                pcols = {row["name"] for row in self._conn.execute(
                    "PRAGMA table_info(performance_metrics)").fetchall()}
            except sqlite3.DatabaseError:
                pcols = set()
            if pcols and "writer_type" not in pcols:
                try:
                    self._conn.execute(
                        "ALTER TABLE performance_metrics ADD COLUMN writer_type TEXT")
                    logging.info(
                        "Updated performance_metrics schema with writer_type column.")
                except sqlite3.DatabaseError:
                    pass

    def record_subband(
            self,
            group_id: str,
            subband_idx: int,
            file_path: Path) -> None:
        now = time.time()
        normalized_group = self._normalize_group_id_datetime(group_id)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO ingest_queue (group_id, state, received_at, last_update, chunk_minutes, expected_subbands)
                VALUES (?, 'collecting', ?, ?, ?, ?)
                """,
                (normalized_group, now, now, self.chunk_duration_minutes, self.expected_subbands),
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

    def bootstrap_directory(self, input_dir: Path) -> None:
        logging.info(
            "Bootstrapping queue from existing files in %s",
            input_dir)
        for path in sorted(input_dir.glob('*_sb??.hdf5')):
            info = parse_subband_info(path)
            if info is None:
                continue
            group_id, subband_idx = info
            self.record_subband(group_id, subband_idx, path)

    def acquire_next_pending(self) -> Optional[str]:
        with self._lock, self._conn:
            row = self._conn.execute(
                """
                SELECT group_id FROM ingest_queue
                 WHERE state = 'pending'
                 ORDER BY received_at ASC
                 LIMIT 1
                """
            ).fetchone()
            if row is None:
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
            return group_id

    def get_subband_paths(self, group_id: str) -> List[Path]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT subband_idx, path FROM subband_files
                 WHERE group_id = ?
                 ORDER BY subband_idx ASC
                """,
                (group_id,),
            ).fetchall()
        return [Path(row[1]) for row in rows]

    def mark_completed(self, group_id: str) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE ingest_queue
                   SET state = 'completed',
                       last_update = ?,
                       error = NULL
                 WHERE group_id = ?
                """,
                (now, group_id),
            )

    def mark_retry(self, group_id: str, error: str, max_retries: int) -> None:
        now = time.time()
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT retry_count FROM ingest_queue WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            if row is None:
                return
            retry_count = row[0] + 1
            next_state = 'failed' if retry_count >= max_retries else 'pending'
            self._conn.execute(
                """
                UPDATE ingest_queue
                   SET state = ?,
                       retry_count = ?,
                       last_update = ?,
                       error = ?
                 WHERE group_id = ?
                """,
                (next_state, retry_count, now, error, group_id),
            )

    def recover_stale_in_progress(
            self, timeout_seconds: Optional[float]) -> List[str]:
        if timeout_seconds is None or timeout_seconds <= 0:
            return []
        cutoff = time.time() - timeout_seconds
        with self._lock, self._conn:
            rows = self._conn.execute(
                """
                SELECT group_id, retry_count FROM ingest_queue
                 WHERE state = 'in_progress' AND last_update < ?
                """,
                (cutoff,),
            ).fetchall()
            recovered: List[str] = []
            for row in rows:
                group_id = row[0]
                retry_count = row[1] + 1
                self._conn.execute(
                    """
                    UPDATE ingest_queue
                       SET state = 'pending',
                           retry_count = ?,
                           last_update = ?,
                           error = 'Recovered from stale in_progress state'
                     WHERE group_id = ?
                    """,
                    (retry_count, time.time(), group_id),
                )
                recovered.append(group_id)
            return recovered

    def list_stale_collecting(
            self,
            timeout_seconds: Optional[float]) -> List[str]:
        if timeout_seconds is None or timeout_seconds <= 0:
            return []
        cutoff = time.time() - timeout_seconds
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT group_id FROM ingest_queue
                 WHERE state = 'collecting' AND received_at < ?
                """,
                (cutoff,),
            ).fetchall()
        return [row[0] for row in rows]

    def update_checkpoint_path(
            self,
            group_id: str,
            checkpoint_path: str) -> None:
        """Update the checkpoint path for a group."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE ingest_queue
                   SET checkpoint_path = ?, last_update = ?
                 WHERE group_id = ?
                """,
                (checkpoint_path, time.time(), group_id),
            )

    def update_processing_stage(self, group_id: str, stage: str) -> None:
        """Update the processing stage for a group."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE ingest_queue
                   SET processing_stage = ?, last_update = ?
                 WHERE group_id = ?
                """,
                (stage, time.time(), group_id),
            )

    def get_checkpoint_info(
            self, group_id: str) -> Optional[Tuple[Optional[str], str]]:
        """Get checkpoint path and processing stage for a group."""
        with self._lock:
            row = self._conn.execute(
                """
                SELECT checkpoint_path, processing_stage FROM ingest_queue
                 WHERE group_id = ?
                """,
                (group_id,),
            ).fetchone()
        if row is None:
            return None
        return row[0], row[1]

    def update_calibrator_match(
            self,
            group_id: str,
            has_cal: int,
            calibrators_json: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE ingest_queue
                   SET has_calibrator = ?, calibrators = ?, last_update = ?
                 WHERE group_id = ?
                """,
                (has_cal, calibrators_json, time.time(), group_id),
            )

    def record_performance_metrics(
            self,
            group_id: str,
            load_time: float,
            phase_time: float,
            write_time: float,
            total_time: float,
            writer_type: Optional[str] = None) -> None:
        """Record performance metrics for a group, preserving writer_type when unknown."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO performance_metrics
                (group_id, load_time, phase_time, write_time, total_time, writer_type, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(group_id) DO UPDATE SET
                  load_time=excluded.load_time,
                  phase_time=excluded.phase_time,
                  write_time=excluded.write_time,
                  total_time=excluded.total_time,
                  writer_type=COALESCE(excluded.writer_type, performance_metrics.writer_type),
                  recorded_at=excluded.recorded_at
                """,
                (group_id, load_time, phase_time, write_time, total_time, writer_type, time.time()),
            )

    def _normalize_existing_groups(self) -> None:
        """Normalize existing groups to ensure consistent chunk_duration_minutes."""
        with self._lock, self._conn:
            rows = self._conn.execute(
                """
                SELECT group_id, received_at, last_update, processing_stage
                FROM ingest_queue
                WHERE processing_stage = 'processing_fresh'
                """
            ).fetchall()

            for row in rows:
                group_id = row['group_id']
                received_at = row['received_at']
                last_update = row['last_update']
                processing_stage = row['processing_stage']

                # Calculate the chunk duration based on the received_at timestamp
                # This assumes a fixed chunk duration for all groups, which might not be ideal
                # for groups with different data durations.
                # For now, we'll use a default or the value passed to __init__.
                # A more robust solution would involve storing chunk_duration_minutes per group.
                # For simplicity, we'll use the default passed to __init__.
                # If the group was just received, set its last_update to received_at
                # to ensure it's processed correctly.
                if processing_stage == 'processing_fresh':
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET last_update = ?,
                               processing_stage = 'processing_fresh'
                         WHERE group_id = ?
                        """,
                        (received_at, group_id),
                    )

    def _normalize_group_id_datetime(self, group_id: str) -> str:
        """Return the normalized group_id using configured chunk duration."""
        try:
            ts = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return group_id

        chunk = timedelta(minutes=self.chunk_duration_minutes)
        seconds = self.chunk_duration_minutes * 60

        epoch = datetime.utcfromtimestamp(0)
        offset = (ts - epoch).total_seconds()
        base_seconds = (offset // seconds) * seconds
        base_dt = epoch + timedelta(seconds=base_seconds)
        return base_dt.strftime("%Y-%m-%dT%H:%M:%S")

    def list_collecting_groups(self, limit: int = 20) -> List[Tuple[str, int]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT group_id, COUNT(subband_idx) AS subbands
                  FROM ingest_queue iq
             LEFT JOIN subband_files sf ON iq.group_id = sf.group_id
                 WHERE iq.state = 'collecting'
              GROUP BY iq.group_id
              ORDER BY iq.received_at ASC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [(row["group_id"], row["subbands"] or 0) for row in rows]

    def get_has_calibrator(self, group_id: str) -> Optional[int]:
        """Return has_calibrator flag for a group (1/0) or None if unknown."""
        with self._lock:
            row = self._conn.execute(
                "SELECT has_calibrator FROM ingest_queue WHERE group_id = ?",
                (group_id,),
            ).fetchone()
        if row is None:
            return None
        val = row[0]
        return int(val) if val is not None else None


def parse_subband_info(path: Path) -> Optional[Tuple[str, int]]:
    match = GROUP_PATTERN.search(path.name)
    if not match:
        logging.debug("Skipping unrecognised file %s", path)
        return None
    group_id = match.group('timestamp')
    subband_idx = int(match.group('index'))
    return group_id, subband_idx


if HAVE_WATCHDOG:

    class InotifyHandler(
            FileSystemEventHandler):  # pragma: no cover - requires watchdog
        def __init__(self, queue_db: QueueDB):
            super(InotifyHandler, self).__init__()
            self.queue_db = queue_db

        def on_created(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            info = parse_subband_info(path)
            if info is None:
                return
            group_id, subband_idx = info
            logging.info(
                "Detected new subband %s (sb%02d)",
                group_id,
                subband_idx)
            self.queue_db.record_subband(group_id, subband_idx, path)

        on_moved = on_created


class DirectoryWatcher(threading.Thread):
    def __init__(
            self,
            input_dir: Path,
            queue_db: QueueDB,
            poll_interval: float = 5.0) -> None:
        super().__init__(daemon=True)
        self.input_dir = input_dir
        self.queue_db = queue_db
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._observer: Optional[Observer] = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)

    def run(self) -> None:
        if HAVE_WATCHDOG:
            logging.info("Starting watchdog observer for %s", self.input_dir)
            handler = InotifyHandler(self.queue_db)
            observer = Observer()
            observer.schedule(handler, str(self.input_dir), recursive=False)
            observer.start()
            self._observer = observer
            try:
                while not self._stop_event.is_set():
                    time.sleep(1.0)
            finally:
                observer.stop()
                observer.join(timeout=5)
        else:
            logging.info(
                "Watchdog unavailable; falling back to polling every %.1f s",
                self.poll_interval)
            seen: Set[Path] = set()
            while not self._stop_event.wait(self.poll_interval):
                for path in self.input_dir.glob('*_sb??.hdf5'):
                    if path in seen:
                        continue
                    info = parse_subband_info(path)
                    if info is None:
                        continue
                    group_id, subband_idx = info
                    logging.info(
                        "Detected new subband %s (sb%02d)",
                        group_id,
                        subband_idx)
                    self.queue_db.record_subband(group_id, subband_idx, path)
                    seen.add(path)


class WorkerConfig(object):
    def __init__(
        self,
        output_dir: Path,
        scratch_dir: Optional[Path],
        checkpoint_dir: Optional[Path],
        log_level: str,
        omp_threads: Optional[int],
        converter_path: Optional[Path],
        max_retries: int,
        cleanup_temp: bool,
        in_progress_timeout: Optional[float],
        collecting_timeout: Optional[float],
        use_subprocess: bool,
        enable_monitoring: bool = True,
        monitor_interval: float = 60.0,
        profile: bool = False,
        chunk_duration_minutes: float = 5.0,
        direct_ms: bool = False,
        stage_inputs: bool = False,
        stage_workers: int = 8,
        hdf5_noflock: bool = True,
        registry_db: Optional[Path] = None,
        # QA quicklooks (shadeMS) forwarded to converter
        qa_shadems: bool = False,
        qa_shadems_resid: bool = False,
        qa_shadems_max: int = 4,
        qa_shadems_timeout: int = 600,
        qa_state_dir: Optional[Path] = None,
        qa_shadems_cal_only: bool = False,
        # QA ragavi (HTML)
        qa_ragavi_vis: bool = False,
        qa_ragavi_timeout: int = 600,
        # Converter dask-ms flags
        converter_dask_write: bool = False,
        converter_dask_failfast: bool = False,
    ) -> None:
        self.output_dir = output_dir
        self.scratch_dir = scratch_dir
        self.checkpoint_dir = checkpoint_dir
        self.log_level = log_level
        self.omp_threads = omp_threads
        self.converter_path = converter_path
        self.max_retries = max_retries
        self.cleanup_temp = cleanup_temp
        self.in_progress_timeout = in_progress_timeout
        self.collecting_timeout = collecting_timeout
        self.use_subprocess = use_subprocess
        self.enable_monitoring = enable_monitoring
        self.monitor_interval = monitor_interval
        self.profile = profile
        self.chunk_duration_minutes = chunk_duration_minutes
        self.direct_ms = direct_ms
        self.stage_inputs = stage_inputs
        self.stage_workers = max(1, int(stage_workers))
        self.hdf5_noflock = hdf5_noflock
        self.registry_db = registry_db
        # QA quicklooks (shadeMS)
        self.qa_shadems = qa_shadems
        self.qa_shadems_resid = qa_shadems_resid
        self.qa_shadems_max = int(qa_shadems_max)
        self.qa_shadems_timeout = int(qa_shadems_timeout)
        self.qa_state_dir = qa_state_dir
        self.qa_shadems_cal_only = qa_shadems_cal_only
        self.qa_ragavi_vis = qa_ragavi_vis
        self.qa_ragavi_timeout = int(qa_ragavi_timeout)
        self.converter_dask_write = converter_dask_write
        self.converter_dask_failfast = converter_dask_failfast


class MonitoringThread(threading.Thread):
    """Monitor queue health and system resources."""

    def __init__(self, queue_db: QueueDB, config: WorkerConfig) -> None:
        super().__init__(daemon=True)
        self.queue_db = queue_db
        self.config = config
        self._stop_event = threading.Event()
        self._last_failed_count = 0

        # Try to import psutil for system metrics
        try:
            import psutil
            self._psutil = psutil
        except ImportError:
            self._psutil = None
            logging.warning(
                "psutil not available; system metrics will be limited")

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        logging.info(
            "Starting monitoring thread (interval: %.1f s)",
            self.config.monitor_interval)
        while not self._stop_event.is_set():
            try:
                self._check_queue_health()
                if self._psutil:
                    self._log_system_metrics()
            except Exception as e:
                logging.error("Error in monitoring thread: %s", e)

            self._stop_event.wait(self.config.monitor_interval)

    def _check_queue_health(self) -> None:
        """Check queue depth and processing health."""
        with self.queue_db._lock:
            # Get queue statistics
            stats = self.queue_db._conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN state = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN state = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN state = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN state = 'completed' THEN 1 ELSE 0 END) as completed
                FROM ingest_queue
                """
            ).fetchone()

            total, pending, in_progress, failed, completed = stats

            # Log queue status
            logging.info(
                "Queue status: total=%d, pending=%d, in_progress=%d, failed=%d, completed=%d",
                total,
                pending,
                in_progress,
                failed,
                completed)

            # Check for warnings
            if total > 10:
                logging.warning("High queue depth: %d groups queued", total)

            if failed > self._last_failed_count:
                logging.warning(
                    "Failed count increased: %d (was %d)",
                    failed,
                    self._last_failed_count)
            self._last_failed_count = failed

            # Check for stale in-progress groups
            stale_cutoff = time.time() - 900  # 15 minutes
            stale_count = self.queue_db._conn.execute(
                """
                SELECT COUNT(*) FROM ingest_queue
                 WHERE state = 'in_progress' AND last_update < ?
                """,
                (stale_cutoff,)
            ).fetchone()[0]

            if stale_count > 0:
                logging.warning(
                    "Found %d stale in-progress groups (>15 min)",
                    stale_count)

    def _log_system_metrics(self) -> None:
        """Log system resource usage."""
        try:
            cpu_percent = self._psutil.cpu_percent(interval=1)
            memory = self._psutil.virtual_memory()
            disk = self._psutil.disk_usage('/')

            logging.info(
                "System metrics: CPU=%.1f%%, RAM=%.1f%% (%.1fGB/%.1fGB), Disk=%.1f%% (%.1fGB/%.1fGB)",
                cpu_percent,
                memory.percent,
                memory.used / 1e9,
                memory.total / 1e9,
                disk.percent,
                disk.used / 1e9,
                disk.total / 1e9)
        except Exception as e:
            logging.debug("Failed to get system metrics: %s", e)


class StreamingWorker(threading.Thread):
    def __init__(
            self,
            queue_db: QueueDB,
            config: WorkerConfig,
            poll_interval: float = 5.0) -> None:
        super().__init__(daemon=True)
        self.queue_db = queue_db
        self.config = config
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._warned_collecting: Set[str] = set()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            recovered = self.queue_db.recover_stale_in_progress(
                self.config.in_progress_timeout)
            for group_id in recovered:
                logging.warning(
                    "Recovered stale in-progress group %s; re-queued for processing",
                    group_id)

            stale_collecting = self.queue_db.list_stale_collecting(
                self.config.collecting_timeout)
            for group_id in stale_collecting:
                if group_id in self._warned_collecting:
                    continue
                logging.warning(
                    "Group %s has been waiting for missing subbands longer than %.0f s",
                    group_id,
                    self.config.collecting_timeout,
                )
                self._warned_collecting.add(group_id)

            group_id = self.queue_db.acquire_next_pending()
            if group_id is None:
                self._stop_event.wait(self.poll_interval)
                continue
            subband_paths = self.queue_db.get_subband_paths(group_id)
            try:
                self._process_group(group_id, subband_paths)
            except Exception as exc:  # pragma: no cover - runtime path
                logging.exception("Processing failed for %s", group_id)
                self.queue_db.mark_retry(
                    group_id, str(exc), self.config.max_retries)
            else:
                logging.info("Completed group %s", group_id)
                self.queue_db.mark_completed(group_id)

    def _parse_converter_timings(self,
                                 stdout: str,
                                 stderr: str,
                                 total_time: float) -> Tuple[float,
                                                             float,
                                                             float]:
        """Parse timing information from converter subprocess output."""

        output = stdout + "\n" + stderr

        try:
            load_time = self._parse_single_timing(
                output, r"Loaded \d+ subbands in ([\d.]+) s")
            phase_time = self._parse_single_timing(
                output, r"Phasing complete in ([\d.]+) s")
            # Support both UVFITS and direct-MS writer timing lines
            write_time = (
                self._parse_single_timing(output, r"UVFITS write completed in ([\d.]+) s")
                or self._parse_single_timing(output, r"pyuvdata\.write_ms completed in ([\d.]+) s")
            )

            parsed_times = [load_time, phase_time, write_time]
            if all(value is not None for value in parsed_times):
                return load_time, phase_time, write_time

            accounted = sum(
                value for value in parsed_times if value is not None)
            remaining = max(0.0, total_time - accounted)

            ratios = {'load': 0.3, 'phase': 0.4, 'write': 0.3}
            missing = [
                name for value, name in (
                    (load_time, 'load'),
                    (phase_time, 'phase'),
                    (write_time, 'write'),
                )
                if value is None
            ]

            if missing:
                if remaining <= 0.0:
                    logging.warning(
                        "No remaining time for backfill, using estimates for missing timings")
                    return total_time * 0.3, total_time * 0.4, total_time * 0.3

                total_ratio = sum(ratios[name] for name in missing)
                remainder = remaining

                for name in missing:
                    share = remainder * (ratios[name] / total_ratio)
                    if name == 'load':
                        load_time = share
                    elif name == 'phase':
                        phase_time = share
                    else:
                        write_time = share

                logging.debug(
                    "Backfilled missing timings %s with remaining %.2f s (total_time %.2f, accounted %.2f)",
                    missing,
                    remaining,
                    total_time,
                    accounted,
                )

            load_time = 0.0 if load_time is None else load_time
            phase_time = 0.0 if phase_time is None else phase_time
            write_time = 0.0 if write_time is None else write_time

            total_timings = load_time + phase_time + write_time
            if total_timings > total_time + 1e-6:
                logging.warning(
                    "Timing sum %.2f exceeds total_time %.2f; clamping to total_time",
                    total_timings,
                    total_time,
                )
                scale = total_time / total_timings if total_timings > 0 else 0.0
                load_time *= scale
                phase_time *= scale
                write_time *= scale

            return load_time, phase_time, write_time

        except (ValueError, AttributeError) as exc:
            logging.warning("Failed to parse converter timings: %s", exc)

        logging.warning("Could not parse converter timings, using estimates")
        return total_time * 0.3, total_time * 0.4, total_time * 0.3

    @staticmethod
    def _parse_single_timing(output: str, pattern: str) -> Optional[float]:
        match = re.search(pattern, output)
        if not match:
            return None
        try:
            value = float(match.group(1))
            if value < 0:
                logging.warning(
                    "Timing %s produced negative value %.2f; ignoring",
                    pattern,
                    value)
                return None
            return value
        except ValueError:
            logging.warning(
                "Failed to parse timing value from '%s'",
                match.group(1))
            return None

    def _process_group(
            self,
            group_id: str,
            subband_paths: Sequence[Path]) -> None:
        if not subband_paths:
            raise RuntimeError(f"No subband files queued for group {group_id}")

        # Check for existing checkpoint
        checkpoint_info = self.queue_db.get_checkpoint_info(group_id)
        is_resuming = False
        if checkpoint_info:
            checkpoint_path, stage = checkpoint_info
            if checkpoint_path and os.path.exists(checkpoint_path):
                logging.info(
                    "Resuming from checkpoint for %s (stage: %s)",
                    group_id,
                    stage)
                # Update stage to indicate we're resuming
                self.queue_db.update_processing_stage(group_id, 'resuming')
                is_resuming = True

        # Only set processing stage for fresh runs
        if not is_resuming:
            self.queue_db.update_processing_stage(group_id, 'processing_fresh')

        # Calibrator match (optional): requires pointing declination and VLA
        # catalog path
        try:
            from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv, calibrator_match
            from astropy.time import Time
            vla_catalog_path = os.getenv(
                'VLA_CALIBRATOR_CSV',
                'references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv')
            pt_dec_env = os.getenv('PIPELINE_POINTING_DEC_DEG')
            if pt_dec_env and os.path.exists(vla_catalog_path):
                # mid time for this group
                start_dt = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
                mid_dt = start_dt + \
                    timedelta(minutes=self.config.chunk_duration_minutes / 2.0)
                df = read_vla_parsed_catalog_csv(vla_catalog_path)
                import astropy.units as u
                matches = calibrator_match(
                    df,
                    float(pt_dec_env) * u.deg,
                    Time(
                        mid_dt,
                        format='datetime',
                        scale='utc').mjd,
                    radius_deg=float(
                        os.getenv(
                            'CAL_MATCH_RADIUS_DEG',
                            '1.0')),
                    top_n=int(
                        os.getenv(
                            'CAL_MATCH_TOPN',
                            '3')))
                if matches:
                    self.queue_db.update_calibrator_match(
                        group_id, has_cal=1, calibrators_json=json.dumps(matches))
                    logging.info("Calibrator(s) in beam: %s", matches)
                else:
                    self.queue_db.update_calibrator_match(
                        group_id, has_cal=0, calibrators_json=json.dumps([]))
                    logging.info("No calibrators in beam for %s", group_id)
            else:
                logging.debug(
                    "Calibrator match skipped (missing PIPELINE_POINTING_DEC_DEG or catalog)")
        except Exception as e:
            logging.warning("Calibrator match failed: %s", e)

        temp_dir = Path(tempfile.mkdtemp(prefix=f"stream_{group_id}_"))
        # Graphiti lineage logging
        run_name = f"conversion-{group_id}"
        _grlog = GraphitiRunLogger(run_name)
        _grlog.__enter__()
        try:
            # Approximate dataset as common parent of subbands
            try:
                parent = os.path.commonpath([str(p.parent) for p in subband_paths])
                _grlog.log_consumes(parent)
            except Exception:
                pass
        try:
            # Stage inputs: either symlink (default) or copy concurrently for
            # faster local reads
            if self.config.stage_inputs:
                logging.info(
                    "Staging %d subbands to %s using %d workers",
                    len(subband_paths),
                    temp_dir,
                    self.config.stage_workers)
                from concurrent.futures import ThreadPoolExecutor, as_completed

                def _copy_one(src: Path, dst: Path) -> Tuple[Path, float]:
                    t0 = time.perf_counter()
                    shutil.copy2(src, dst)
                    return dst, time.perf_counter() - t0

                with ThreadPoolExecutor(max_workers=self.config.stage_workers) as ex:
                    futs = {}
                    for p in subband_paths:
                        dst = temp_dir / p.name
                        if dst.exists():
                            continue
                        futs[ex.submit(_copy_one, p, dst)] = p
                    for i, fut in enumerate(as_completed(futs), 1):
                        src_path = futs[fut]
                        try:
                            dst_path, dt = fut.result()
                            logging.info(
                                "Staged %s -> %s in %.2f s (%d/%d)",
                                src_path.name,
                                dst_path,
                                dt,
                                i,
                                len(futs))
                        except Exception as e:
                            logging.error("Failed staging %s: %s", src_path, e)
                            raise
            else:
                for path in subband_paths:
                    target = temp_dir / path.name
                    if not target.exists():
                        os.symlink(path, target)

            start_dt = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
            # Use configurable chunk duration (default: 5 minutes)
            end_dt = start_dt + \
                timedelta(minutes=self.config.chunk_duration_minutes)
            start_time = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_time = end_dt.strftime('%Y-%m-%d %H:%M:%S')

            # Track timing for performance metrics
            total_start = time.perf_counter()
            load_time = 0.0
            phase_time = 0.0
            write_time = 0.0

            writer_type: Optional[str] = None
            if self.config.use_subprocess:
                cmd = [
                    sys.executable,
                    '-m', 'dsa110_contimg.conversion.strategies.uvh5_to_ms_converter',
                    str(temp_dir),
                    str(self.config.output_dir),
                    start_time,
                    end_time,
                    '--writer', 'direct-subband',
                    '--max-workers', str(self.config.stage_workers),
                ]
                if self.config.scratch_dir is not None:
                    cmd.extend(['--scratch-dir', str(self.config.scratch_dir)])
                ll = (self.config.log_level or 'INFO').upper()
                if ll not in ('DEBUG', 'INFO', 'WARNING', 'ERROR'):
                    ll = 'INFO'
                cmd.extend(['--log-level', ll])

                logging.info(
                    "Launching converter subprocess for %s via strategy orchestrator",
                    group_id)
                env = os.environ.copy()
                if self.config.omp_threads is not None:
                    env['OMP_NUM_THREADS'] = str(self.config.omp_threads)
                    env['MKL_NUM_THREADS'] = str(self.config.omp_threads)
                else:
                    # Set default OMP threads to prevent over-subscription
                    env.setdefault('OMP_NUM_THREADS', '4')
                    env.setdefault('MKL_NUM_THREADS', '4')
                if self.config.hdf5_noflock:
                    env.setdefault('HDF5_USE_FILE_LOCKING', 'FALSE')

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Converter returned {result.returncode}: {result.stderr or result.stdout}"
                    )
                # Parse writer type marker from stdout (if present) and record
                # total time
                writer_type = None
                if result.stdout:
                    for line in (result.stdout or '').splitlines():
                        if line.startswith('WRITER_TYPE:'):
                            writer_type = line.split(':', 1)[1].strip()
                            break
                try:
                    total_time = time.perf_counter() - total_start
                    self.queue_db.record_performance_metrics(
                        group_id, 0.0, 0.0, 0.0, total_time, writer_type)
                except Exception:
                    pass
                if result.stdout:
                    logging.debug(
                        "Converter stdout for %s:\n%s",
                        group_id,
                        result.stdout)
                if result.stderr:
                    logging.debug(
                        "Converter stderr for %s:\n%s",
                        group_id,
                        result.stderr)

                # Parse timing information from subprocess output
                total_time = time.perf_counter() - total_start
                load_time, phase_time, write_time = self._parse_converter_timings(
                    result.stdout or "", result.stderr or "", total_time)
            else:
                env_overrides: Dict[str, str] = {}
                if self.config.omp_threads is not None:
                    value = str(self.config.omp_threads)
                    env_overrides['OMP_NUM_THREADS'] = value
                    env_overrides['MKL_NUM_THREADS'] = value
                else:
                    # Set default OMP threads to prevent over-subscription
                    env_overrides['OMP_NUM_THREADS'] = '4'
                    env_overrides['MKL_NUM_THREADS'] = '4'
                if self.config.hdf5_noflock:
                    env_overrides['HDF5_USE_FILE_LOCKING'] = 'FALSE'

                logging.info(
                    "Running converter in-process for %s via strategy orchestrator",
                    group_id)
                t0 = time.perf_counter()
                with override_env(env_overrides):
                    from dsa110_contimg.conversion.strategies import uvh5_to_ms_converter as _strat
                    _strat.convert_subband_groups_to_ms(
                        input_dir=str(temp_dir),
                        output_dir=str(self.config.output_dir),
                        start_time=start_time,
                        end_time=end_time,
                        writer='direct-subband',
                        writer_kwargs={
                            'max_workers': self.config.stage_workers,
                            'scratch_dir': str(self.config.scratch_dir) if self.config.scratch_dir else None,
                        },
                    )
                writer_type = 'direct-subband'
                duration = time.perf_counter() - t0
                logging.info(
                    "In-process conversion for %s completed in %.1f s",
                    group_id,
                    duration)

                # For in-process, we can't easily separate timing, so estimate
                load_time = duration * 0.3  # Estimate 30% for loading
                phase_time = duration * 0.4  # Estimate 40% for phasing
                write_time = duration * 0.3  # Estimate 30% for writing

            # After conversion, enumerate produced MS files
            group_ms_list: List[str] = []
            try:
                for p in subband_paths:
                    ms_name = (self.config.output_dir / f"{p.stem}.ms")
                    if ms_name.exists():
                        group_ms_list.append(os.fspath(ms_name))
                        try:
                            _grlog.log_produces(os.fspath(ms_name))
                        except Exception:
                            pass
            except Exception:
                group_ms_list = []

            # Decide calibrator vs target
            try:
                is_cal = self.queue_db.get_has_calibrator(group_id) == 1
            except Exception:
                is_cal = False

            # Concatenate subbands into multi-SPW MS for this group
            group_ms_path = os.fspath(
                self.config.output_dir / f"{group_id}.ms")
            try:
                if group_ms_list:
                    if os.path.isdir(group_ms_path):
                        import shutil as _sh
                        _sh.rmtree(group_ms_path, ignore_errors=True)
                    casa_concat(vis=group_ms_list, concatvis=group_ms_path)
                    _msindex_update(
                        group_ms_path,
                        stage="concatenated",
                        status="in_progress")
                    try:
                        _grlog.log_produces(group_ms_path)
                    except Exception:
                        pass
            except Exception as e:
                logging.error("concat failed for %s: %s", group_id, e)

            # Helper to get all fields selector
            def _all_fields_selector(ms: str) -> str:
                try:
                    with table(f"{ms}::FIELD") as tf:
                        n = tf.nrows()
                    return f"0~{max(0, n-1)}"
                except Exception:
                    return ""

            # Helper to get mid-MJD
            def _mid_mjd(ms: str) -> Optional[float]:
                try:
                    from casatools import msmetadata  # type: ignore
                    msmd = msmetadata()
                    msmd.open(ms)
                    tr = msmd.timerangeforobs()
                    msmd.close()
                    if tr and isinstance(tr, (list, tuple)) and len(tr) >= 2:
                        return 0.5 * (float(tr[0]) + float(tr[1]))
                except Exception:
                    return None
                return None

            def _timerange(
                    ms: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
                try:
                    from casatools import msmetadata  # type: ignore
                    msmd = msmetadata()
                    msmd.open(ms)
                    tr = msmd.timerangeforobs()
                    msmd.close()
                    if tr and isinstance(tr, (list, tuple)) and len(tr) >= 2:
                        s = float(tr[0])
                        e = float(tr[1])
                        return s, e, 0.5 * (s + e)
                except Exception:
                    pass
                return None, None, None
            def _msindex_update(
                    ms_path: str,
                    *,
                    stage: str,
                    cal_applied: int = 0,
                    imagename: Optional[str] = None,
                    status: str = "in_progress") -> None:
                db = os.getenv('PIPELINE_PRODUCTS_DB')
                if not db:
                    return
                try:
                    conn = ensure_products_db(Path(db))
                    s, e, m = _timerange(ms_path)
                    ms_index_upsert(conn, ms_path, start_mjd=s, end_mjd=e, mid_mjd=m,
                                    status=status, stage=stage, cal_applied=cal_applied,
                                    imagename=imagename)
                    conn.commit()
                    conn.close()
                except Exception as ue:
                    logging.debug("ms_index update failed: %s", ue)

            # Calibrator: solve and register
            if is_cal and os.path.isdir(group_ms_path):
                cal_field = _all_fields_selector(group_ms_path)
                # pick refant by median id present
                try:
                    with table(group_ms_path) as tb:
                        import numpy as _np
                        ants = _np.unique(_np.concatenate(
                            [tb.getcol('ANTENNA1'), tb.getcol('ANTENNA2')]))
                        refant = str(int(_np.median(ants))
                                     ) if ants.size else '0'
                except Exception:
                    refant = '0'
                prefix = os.path.splitext(group_ms_path)[0] + f"_{cal_field}"
                ktabs = solve_delay(
                    group_ms_path,
                    cal_field=cal_field,
                    refant=refant,
                    table_prefix=prefix)
                bp_minsnr = float(os.getenv('BP_MINSNR', '5.0'))
                bptabs = solve_bandpass(
                    group_ms_path,
                    cal_field=cal_field,
                    refant=refant,
                    ktable=ktabs[0],
                    table_prefix=prefix,
                    combine_fields=True,
                    minsnr=bp_minsnr)
                gtabs = solve_gains(
                    group_ms_path,
                    cal_field=cal_field,
                    refant=refant,
                    ktable=ktabs[0],
                    bptables=bptabs,
                    table_prefix=prefix,
                    t_short="60s",
                    do_fluxscale=False,
                    combine_fields=True)
                _msindex_update(
                    group_ms_path,
                    stage="calibrated",
                    status="in_progress")
                if self.config.registry_db is not None:
                    try:
                        ensure_cal_db(self.config.registry_db)
                        mid = _mid_mjd(group_ms_path)
                        win = 30.0 / 1440.0
                        register_set_from_prefix(
                            self.config.registry_db,
                            set_name=f"calset_{group_id}",
                            prefix=Path(prefix),
                            cal_field=cal_field,
                            refant=refant,
                            valid_start_mjd=None if mid is None else mid - win,
                            valid_end_mjd=None if mid is None else mid + win,
                            status="active",
                        )
                        # QA: fast_plots for MS and per-antenna BCAL plots
                        try:
                            qa_dir = os.fspath(
                                Path(
                                    os.getenv(
                                        'PIPELINE_STATE_DIR',
                                        'state')) /
                                'qa' /
                                group_id)
                            os.makedirs(qa_dir, exist_ok=True)
                            # Generate fast QA
                            from dsa110_contimg.qa.fast_plots import run_fast_plots
                            # The bandpass table is usually named with _bpcal
                            # suffix
                            bcal_guess = f"{prefix}_bpcal"
                            run_fast_plots(
                                group_ms_path,
                                output_dir=qa_dir,
                                max_uv_points=200000,
                                include_residual=False,
                                phase_per_antenna=False,
                                refant_auto=None,
                                unwrap_phase=False,
                                bcal_path=bcal_guess,
                            )
                        except Exception as qe:
                            logging.warning("QA generation failed: %s", qe)
                    except Exception as e:
                        logging.warning(
                            "Calibration registry update failed: %s", e)

            # Target: applycal + image (record artifacts to products DB if
            # available)
            if (not is_cal) and os.path.isdir(group_ms_path):
                gaintables: List[str] = []
                if self.config.registry_db is not None:
                    mid = _mid_mjd(group_ms_path)
                    if mid is not None:
                        try:
                            gaintables = get_active_applylist(
                                self.config.registry_db, mid)
                        except Exception as e:
                            logging.warning(
                                "Active applylist lookup failed: %s", e)
                if gaintables:
                    try:
                        apply_to_target(
                            group_ms_path,
                            field="",
                            gaintables=gaintables,
                            calwt=True)
                        _msindex_update(
                            group_ms_path,
                            stage="applycal_done",
                            cal_applied=1,
                            status="in_progress")
                    except Exception as e:
                        logging.warning("applycal failed: %s", e)
                        _msindex_update(
                            group_ms_path,
                            stage="applycal_failed",
                            cal_applied=0,
                            status="failed")
                try:
                    out_prefix = os.fspath(
                        self.config.output_dir / f"{group_id}.img")
                    imsize = int(os.getenv('IMG_IMSIZE', '1024'))
                    robust = float(os.getenv('IMG_ROBUST', '0.0'))
                    niter = int(os.getenv('IMG_NITER', '1000'))
                    thresh = os.getenv('IMG_THRESHOLD', '0.0Jy')
                    image_ms(
                        group_ms_path,
                        imagename=out_prefix,
                        imsize=imsize,
                        robust=robust,
                        niter=niter,
                        threshold=thresh,
                        pbcor=True)
                    _msindex_update(
                        group_ms_path,
                        stage="imaged",
                        cal_applied=1 if gaintables else 0,
                        imagename=out_prefix,
                        status="done")
                    # Record products in products_db if configured via env
                    products_db = os.getenv('PIPELINE_PRODUCTS_DB')
                    if products_db:
                        try:
                            conn = ensure_products_db(Path(products_db))
                            now = time.time()
                            for suf, pbc in [(".image", 0), (".pb", 0), (".pbcor", 1), (".residual", 0), (".model", 0)]:
                                pth = out_prefix + suf
                                if os.path.isdir(pth):
                                    images_insert(conn, pth, group_ms_path, now, "5min", pbc)
                                    try:
                                        _grlog.log_produces(pth)
                                    except Exception:
                                        pass
                            ms_index_upsert(conn, group_ms_path, status="done", stage="imaged", cal_applied=(1 if gaintables else 0), imagename=out_prefix, processed_at=now)
                            conn.commit()
                            conn.close()
                        except Exception as de:
                            logging.debug("Failed to write products DB: %s", de)
                except Exception as e:
                    logging.warning("imaging failed: %s", e)

            # Record performance metrics
            total_time = time.perf_counter() - total_start
            # Keep existing load/phase/write estimates; preserve last known
            # writer_type if any (subprocess path sets it above)
            try:
                self.queue_db.record_performance_metrics(
                    group_id, load_time, phase_time, write_time, total_time, writer_type)
            except Exception:
                pass

            # Check for performance warnings
            if total_time > 270:  # 4.5 minutes (90% of 5-min window)
                logging.warning(
                    "Group %s took %.1f s (exceeds 4.5 min threshold)",
                    group_id,
                    total_time)

            # Update processing stage
            self.queue_db.update_processing_stage(group_id, 'completed')

            # Update checkpoint path if using checkpoints
            if self.config.checkpoint_dir is not None:
                checkpoint_path = os.path.join(
                    self.config.checkpoint_dir,
                    f"{group_id}.checkpoint.uvh5")
                if os.path.exists(checkpoint_path):
                    self.queue_db.update_checkpoint_path(
                        group_id, checkpoint_path)

        finally:
            try:
                _grlog.__exit__(None, None, None)
            except Exception:
                pass
            if self.config.cleanup_temp:
                shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                logging.info(
                    "Preserved temporary staging directory %s",
                    temp_dir)


def create_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Streaming UVH5 to MS converter service")
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('/data/incoming_data/'),
        help='Directory to watch for incoming *_sb??.hdf5 files (default: /data/incoming_data/)')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Destination directory for measurement sets')
    parser.add_argument(
        '--queue-db',
        type=Path,
        default=Path('streaming_queue.sqlite3'),
        help='Path to the SQLite queue database (default: streaming_queue.sqlite3)')
    parser.add_argument(
        '--scratch-dir',
        type=Path,
        help='Scratch directory for staging UVFITS/MS during conversion')
    parser.add_argument('--checkpoint-dir', type=Path,
                        help='Directory for converter checkpoints')
    parser.add_argument(
        '--registry-db',
        type=Path,
        help='Calibration registry database path for streaming cal/apply')
    parser.add_argument(
        '--poll-interval',
        type=float,
        default=5.0,
        help='Polling interval in seconds when watchdog is unavailable (default: 5)')
    parser.add_argument(
        '--worker-poll-interval',
        type=float,
        default=5.0,
        help='Idle wait time in seconds between queue checks (default: 5)')
    parser.add_argument(
        '--expected-subbands',
        type=int,
        default=16,
        help='Expected number of subbands per group (default: 16)')
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum converter retries before marking a group failed (default: 3)')
    parser.add_argument(
        '--omp-threads',
        type=int,
        help='Set OMP_NUM_THREADS/MKL_NUM_THREADS for converter subprocess')
    parser.add_argument(
        '--use-subprocess',
        action='store_true',
        default=False,
        help='Launch the batch converter in a separate process instead of in-process')
    parser.add_argument(
        '--in-progress-timeout',
        type=float,
        default=900.0,
        help='Seconds before stale in-progress groups are re-queued (default: 900)')
    parser.add_argument(
        '--collecting-timeout',
        type=float,
        default=600.0,
        help='Warn if groups remain incomplete for more than this many seconds (default: 600)')
    parser.add_argument(
        '--monitoring',
        dest='monitoring',
        action='store_true',
        default=True,
        help='Enable queue/resource monitoring (default: enabled)')
    parser.add_argument(
        '--no-monitoring',
        dest='monitoring',
        action='store_false',
        help='Disable queue/resource monitoring for minimal footprint')
    parser.add_argument(
        '--monitor-interval',
        type=float,
        default=60.0,
        help='Monitoring check interval in seconds (default: 60)')
    parser.add_argument(
        '--profile',
        action='store_true',
        default=False,
        help='Enable detailed performance profiling and timing logs')
    parser.add_argument(
        '--chunk-duration',
        type=float,
        default=5.0,
        help='Duration of data chunks in minutes (default: 5.0)')
    parser.add_argument('--log-level', default='INFO',
                        help='Service log level (default: INFO)')
    parser.add_argument(
        '--cleanup-temp',
        action='store_true',
        default=False,
        help='Remove temporary staging directories after conversion')
    parser.add_argument(
        '--direct-ms',
        action='store_true',
        default=False,
        help='Instruct the converter to write MS directly (no UVFITS)')
    parser.add_argument(
        '--stage-inputs',
        action='store_true',
        default=False,
        help='Copy subband files to the per-group temp dir instead of symlinking')
    parser.add_argument(
        '--stage-workers',
        type=int,
        default=8,
        help='Number of concurrent workers for staging copies (default: 8)')
    parser.add_argument(
        '--hdf5-noflock',
        action='store_true',
        default=True,
        help='Set HDF5_USE_FILE_LOCKING=FALSE for converter execution (default: enabled)')
    # Converter dask-ms flags (forwarded)
    parser.add_argument(
        '--converter-dask-write',
        action='store_true',
        default=False,
        help='Instruct the converter to use dask-ms writing path (experimental)')
    parser.add_argument(
        '--converter-dask-failfast',
        action='store_true',
        default=False,
        help='Fail immediately if dask-ms write fails (no fallback)')
    # QA quicklooks (shadeMS) flags to forward to converter
    parser.add_argument(
        '--qa-shadems',
        action='store_true',
        default=False,
        help='Enable shadeMS quicklook plots after writing each MS')
    parser.add_argument(
        '--qa-shadems-resid',
        action='store_true',
        default=False,
        help='Include residual plot (CORRECTED_DATA-MODEL_DATA) if MODEL_DATA exists')
    parser.add_argument(
        '--qa-shadems-max',
        type=int,
        default=4,
        help='Maximum number of quicklook plots to produce (default: 4)')
    parser.add_argument('--qa-shadems-timeout', type=int, default=600,
                        help='Per-plot timeout in seconds (default: 600)')
    parser.add_argument(
        '--qa-state-dir',
        type=Path,
        help='Base state directory for QA artifacts (default: $PIPELINE_STATE_DIR or "state")')
    parser.add_argument(
        '--qa-shadems-cal-only',
        action='store_true',
        default=False,
        help='Only enable quicklooks for groups with a matched calibrator')
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = create_arg_parser()
    args = parser.parse_args(argv)

    setup_logging(args.log_level)

    input_dir = args.input_dir.expanduser().resolve()
    if not input_dir.exists():
        logging.info("Creating input directory %s", input_dir)
        input_dir.mkdir(parents=True, exist_ok=True)

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scratch_dir = args.scratch_dir.expanduser().resolve() if args.scratch_dir else None
    if scratch_dir is not None:
        scratch_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = args.checkpoint_dir.expanduser(
    ).resolve() if args.checkpoint_dir else None
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    queue_db = QueueDB(
        args.queue_db.expanduser().resolve(),
        expected_subbands=args.expected_subbands,
        chunk_duration_minutes=args.chunk_duration,
    )
    queue_db.bootstrap_directory(input_dir)

    converter_path = (
        Path(__file__).resolve().parent.parent /
        'uvh5_to_ms_converter_v2.py').resolve()
    config = WorkerConfig(
        output_dir=output_dir,
        scratch_dir=scratch_dir,
        checkpoint_dir=checkpoint_dir,
        log_level=args.log_level,
        omp_threads=args.omp_threads,
        converter_path=None,
        max_retries=args.max_retries,
        cleanup_temp=args.cleanup_temp,
        in_progress_timeout=args.in_progress_timeout,
        collecting_timeout=args.collecting_timeout,
        use_subprocess=args.use_subprocess,
        enable_monitoring=args.monitoring,
        monitor_interval=args.monitor_interval,
        profile=args.profile,
        chunk_duration_minutes=args.chunk_duration,
        direct_ms=args.direct_ms,
        stage_inputs=args.stage_inputs,
        stage_workers=args.stage_workers,
        hdf5_noflock=args.hdf5_noflock,
        registry_db=(
            args.registry_db.expanduser().resolve() if args.registry_db else None),
        converter_dask_write=args.converter_dask_write,
        converter_dask_failfast=args.converter_dask_failfast,
        qa_shadems=args.qa_shadems,
        qa_shadems_resid=args.qa_shadems_resid,
        qa_shadems_max=args.qa_shadems_max,
        qa_shadems_timeout=args.qa_shadems_timeout,
        qa_state_dir=args.qa_state_dir,
        qa_shadems_cal_only=args.qa_shadems_cal_only,
        qa_ragavi_vis=args.qa_ragavi_vis,
        qa_ragavi_timeout=args.qa_ragavi_timeout,
    )

    logging.info(
        "Converter execution mode: %s (chunk duration %.1f min)",
        "subprocess" if args.use_subprocess else "in-process",
        args.chunk_duration,
    )

    watcher = DirectoryWatcher(
        input_dir,
        queue_db,
        poll_interval=args.poll_interval)
    worker = StreamingWorker(
        queue_db,
        config,
        poll_interval=args.worker_poll_interval)

    # Start monitoring thread if enabled
    monitor = None
    if config.enable_monitoring:
        monitor = MonitoringThread(queue_db, config)

    try:
        watcher.start()
        worker.start()
        if monitor:
            monitor.start()
        logging.info("Streaming converter running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logging.info("Shutdown requested; stopping threads...")
    finally:
        watcher.stop()
        worker.stop()
        if monitor:
            monitor.stop()
        watcher.join(timeout=5)
        worker.join(timeout=5)
        if monitor:
            monitor.join(timeout=5)
        queue_db.close()

    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())

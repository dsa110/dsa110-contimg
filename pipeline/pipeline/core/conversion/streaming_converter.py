#!/usr/bin/env python3
"""
Streaming converter service for DSA-110 UVH5 subband groups.

This daemon watches an ingest directory for new *_sb??.hdf5 files, queues
complete 16-subband groups, and invokes the existing batch converter on each
group using a scratch directory for staging.

The queue is persisted in SQLite so the service can resume after restarts.
"""

import argparse
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvh5_to_ms_converter as converter

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
                self._conn.execute("ALTER TABLE ingest_queue ADD COLUMN checkpoint_path TEXT")
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
                self._conn.execute("ALTER TABLE ingest_queue ADD COLUMN chunk_minutes REAL")
                altered = True

            if altered:
                logging.info("Updated ingest_queue schema with new metadata columns.")

    def record_subband(self, group_id: str, subband_idx: int, file_path: Path) -> None:
        now = time.time()
        normalized_group = self._normalize_group_id_datetime(group_id)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO ingest_queue (group_id, state, received_at, last_update, chunk_minutes)
                VALUES (?, 'collecting', ?, ?, ?)
                """,
                (normalized_group, now, now, self.chunk_duration_minutes),
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
                (now, group_id),
            )
            count = self._conn.execute(
                "SELECT COUNT(*) FROM subband_files WHERE group_id = ?",
                (group_id,),
            ).fetchone()[0]
            if count >= self.expected_subbands:
                self._conn.execute(
                    """
                    UPDATE ingest_queue
                       SET state = CASE WHEN state = 'completed' THEN state ELSE 'pending' END,
                           last_update = ?
                     WHERE group_id = ?
                    """,
                    (now, group_id),
                )

    def bootstrap_directory(self, input_dir: Path) -> None:
        logging.info("Bootstrapping queue from existing files in %s", input_dir)
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

    def recover_stale_in_progress(self, timeout_seconds: Optional[float]) -> List[str]:
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

    def list_stale_collecting(self, timeout_seconds: Optional[float]) -> List[str]:
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

    def update_checkpoint_path(self, group_id: str, checkpoint_path: str) -> None:
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

    def get_checkpoint_info(self, group_id: str) -> Optional[Tuple[Optional[str], str]]:
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

    def record_performance_metrics(self, group_id: str, load_time: float, 
                                 phase_time: float, write_time: float, 
                                 total_time: float) -> None:
        """Record performance metrics for a group."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO performance_metrics
                (group_id, load_time, phase_time, write_time, total_time, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (group_id, load_time, phase_time, write_time, total_time, time.time()),
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
            start_dt = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return group_id

        chunk = timedelta(minutes=self.chunk_duration_minutes)
        seconds = chunk.total_seconds()
        epoch = start_dt.timestamp()
        snapped = epoch - (epoch % seconds)
        normalized = datetime.utcfromtimestamp(snapped)
        return normalized.strftime("%Y-%m-%dT%H:%M:%S")

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


def parse_subband_info(path: Path) -> Optional[Tuple[str, int]]:
    match = GROUP_PATTERN.search(path.name)
    if not match:
        logging.debug("Skipping unrecognised file %s", path)
        return None
    group_id = match.group('timestamp')
    subband_idx = int(match.group('index'))
    return group_id, subband_idx


if HAVE_WATCHDOG:

    class InotifyHandler(FileSystemEventHandler):  # pragma: no cover - requires watchdog
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
            logging.info("Detected new subband %s (sb%02d)", group_id, subband_idx)
            self.queue_db.record_subband(group_id, subband_idx, path)

        on_moved = on_created


class DirectoryWatcher(threading.Thread):
    def __init__(self, input_dir: Path, queue_db: QueueDB, poll_interval: float = 5.0) -> None:
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
            logging.info("Watchdog unavailable; falling back to polling every %.1f s", self.poll_interval)
            seen: Set[Path] = set()
            while not self._stop_event.wait(self.poll_interval):
                for path in self.input_dir.glob('*_sb??.hdf5'):
                    if path in seen:
                        continue
                    info = parse_subband_info(path)
                    if info is None:
                        continue
                    group_id, subband_idx = info
                    logging.info("Detected new subband %s (sb%02d)", group_id, subband_idx)
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
        converter_path: Path,
        max_retries: int,
        cleanup_temp: bool,
        in_progress_timeout: Optional[float],
        collecting_timeout: Optional[float],
        use_subprocess: bool,
        enable_monitoring: bool = True,
        monitor_interval: float = 60.0,
        profile: bool = False,
        chunk_duration_minutes: float = 5.0,
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
            logging.warning("psutil not available; system metrics will be limited")

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        logging.info("Starting monitoring thread (interval: %.1f s)", self.config.monitor_interval)
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
            logging.info("Queue status: total=%d, pending=%d, in_progress=%d, failed=%d, completed=%d", 
                       total, pending, in_progress, failed, completed)
            
            # Check for warnings
            if total > 10:
                logging.warning("High queue depth: %d groups queued", total)
            
            if failed > self._last_failed_count:
                logging.warning("Failed count increased: %d (was %d)", failed, self._last_failed_count)
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
                logging.warning("Found %d stale in-progress groups (>15 min)", stale_count)

    def _log_system_metrics(self) -> None:
        """Log system resource usage."""
        try:
            cpu_percent = self._psutil.cpu_percent(interval=1)
            memory = self._psutil.virtual_memory()
            disk = self._psutil.disk_usage('/')
            
            logging.info("System metrics: CPU=%.1f%%, RAM=%.1f%% (%.1fGB/%.1fGB), Disk=%.1f%% (%.1fGB/%.1fGB)",
                       cpu_percent, 
                       memory.percent, memory.used/1e9, memory.total/1e9,
                       disk.percent, disk.used/1e9, disk.total/1e9)
        except Exception as e:
            logging.debug("Failed to get system metrics: %s", e)


class StreamingWorker(threading.Thread):
    def __init__(self, queue_db: QueueDB, config: WorkerConfig, poll_interval: float = 5.0) -> None:
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
            recovered = self.queue_db.recover_stale_in_progress(self.config.in_progress_timeout)
            for group_id in recovered:
                logging.warning("Recovered stale in-progress group %s; re-queued for processing", group_id)

            stale_collecting = self.queue_db.list_stale_collecting(self.config.collecting_timeout)
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
                self.queue_db.mark_retry(group_id, str(exc), self.config.max_retries)
            else:
                logging.info("Completed group %s", group_id)
                self.queue_db.mark_completed(group_id)

    def _parse_converter_timings(self, stdout: str, stderr: str, total_time: float) -> Tuple[float, float, float]:
        """Parse timing information from converter subprocess output."""

        output = stdout + "\n" + stderr

        try:
            load_time = self._parse_single_timing(output, r"Loaded \d+ subbands in ([\d.]+) s")
            phase_time = self._parse_single_timing(output, r"Phasing complete in ([\d.]+) s")
            write_time = self._parse_single_timing(output, r"UVFITS write completed in ([\d.]+) s")

            parsed_times = [load_time, phase_time, write_time]
            if all(value is not None for value in parsed_times):
                return load_time, phase_time, write_time

            accounted = sum(value for value in parsed_times if value is not None)
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
                    logging.warning("No remaining time for backfill, using estimates for missing timings")
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
                logging.warning("Timing %s produced negative value %.2f; ignoring", pattern, value)
                return None
            return value
        except ValueError:
            logging.warning("Failed to parse timing value from '%s'", match.group(1))
            return None

    def _process_group(self, group_id: str, subband_paths: Sequence[Path]) -> None:
        if not subband_paths:
            raise RuntimeError(f"No subband files queued for group {group_id}")

        # Check for existing checkpoint
        checkpoint_info = self.queue_db.get_checkpoint_info(group_id)
        is_resuming = False
        if checkpoint_info:
            checkpoint_path, stage = checkpoint_info
            if checkpoint_path and os.path.exists(checkpoint_path):
                logging.info("Resuming from checkpoint for %s (stage: %s)", group_id, stage)
                # Update stage to indicate we're resuming
                self.queue_db.update_processing_stage(group_id, 'resuming')
                is_resuming = True
        
        # Only set processing stage for fresh runs
        if not is_resuming:
            self.queue_db.update_processing_stage(group_id, 'processing_fresh')

        temp_dir = Path(tempfile.mkdtemp(prefix=f"stream_{group_id}_"))
        try:
            for path in subband_paths:
                target = temp_dir / path.name
                if not target.exists():
                    os.symlink(path, target)

            start_dt = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
            # Use configurable chunk duration (default: 5 minutes)
            end_dt = start_dt + timedelta(minutes=self.config.chunk_duration_minutes)
            start_time = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_time = end_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Track timing for performance metrics
            total_start = time.perf_counter()
            load_time = 0.0
            phase_time = 0.0
            write_time = 0.0

            if self.config.use_subprocess:
                cmd = [
                    sys.executable,
                    str(self.config.converter_path),
                    str(temp_dir),
                    str(self.config.output_dir),
                    start_time,
                    end_time,
                    '--log-level',
                    self.config.log_level,
                ]
                if self.config.checkpoint_dir is not None:
                    cmd.extend(['--checkpoint-dir', str(self.config.checkpoint_dir)])
                if self.config.scratch_dir is not None:
                    cmd.extend(['--scratch-dir', str(self.config.scratch_dir)])

                logging.info("Launching converter subprocess for %s", group_id)
                env = os.environ.copy()
                if self.config.omp_threads is not None:
                    env['OMP_NUM_THREADS'] = str(self.config.omp_threads)
                    env['MKL_NUM_THREADS'] = str(self.config.omp_threads)
                else:
                    # Set default OMP threads to prevent over-subscription
                    env.setdefault('OMP_NUM_THREADS', '4')
                    env.setdefault('MKL_NUM_THREADS', '4')

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
                if result.stdout:
                    logging.debug("Converter stdout for %s:\n%s", group_id, result.stdout)
                if result.stderr:
                    logging.debug("Converter stderr for %s:\n%s", group_id, result.stderr)
                
                # Parse timing information from subprocess output
                total_time = time.perf_counter() - total_start
                load_time, phase_time, write_time = self._parse_converter_timings(
                    result.stdout or "", result.stderr or "", total_time
                )
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

                logging.info("Running converter in-process for %s", group_id)
                t0 = time.perf_counter()
                with override_env(env_overrides):
                    converter.convert_subband_groups_to_ms(
                        str(temp_dir),
                        str(self.config.output_dir),
                        start_time,
                        end_time,
                        checkpoint_dir=str(self.config.checkpoint_dir) if self.config.checkpoint_dir is not None else None,
                        scratch_dir=str(self.config.scratch_dir) if self.config.scratch_dir is not None else None,
                    )
                duration = time.perf_counter() - t0
                logging.info("In-process conversion for %s completed in %.1f s", group_id, duration)
                
                # For in-process, we can't easily separate timing, so estimate
                load_time = duration * 0.3  # Estimate 30% for loading
                phase_time = duration * 0.4  # Estimate 40% for phasing
                write_time = duration * 0.3  # Estimate 30% for writing
            
            # Record performance metrics
            total_time = time.perf_counter() - total_start
            self.queue_db.record_performance_metrics(group_id, load_time, phase_time, write_time, total_time)
            
            # Check for performance warnings
            if total_time > 270:  # 4.5 minutes (90% of 5-min window)
                logging.warning("Group %s took %.1f s (exceeds 4.5 min threshold)", group_id, total_time)
            
            # Update processing stage
            self.queue_db.update_processing_stage(group_id, 'completed')
            
            # Update checkpoint path if using checkpoints
            if self.config.checkpoint_dir is not None:
                checkpoint_path = os.path.join(self.config.checkpoint_dir, f"{group_id}.checkpoint.uvh5")
                if os.path.exists(checkpoint_path):
                    self.queue_db.update_checkpoint_path(group_id, checkpoint_path)
                    
        finally:
            if self.config.cleanup_temp:
                shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                logging.info("Preserved temporary staging directory %s", temp_dir)


def create_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Streaming UVH5 to MS converter service")
    parser.add_argument('--input-dir', type=Path, default=Path('/data/incoming_data/'),
                        help='Directory to watch for incoming *_sb??.hdf5 files (default: /data/incoming_data/)')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Destination directory for measurement sets')
    parser.add_argument('--queue-db', type=Path, default=Path('streaming_queue.sqlite3'),
                        help='Path to the SQLite queue database (default: streaming_queue.sqlite3)')
    parser.add_argument('--scratch-dir', type=Path,
                        help='Scratch directory for staging UVFITS/MS during conversion')
    parser.add_argument('--checkpoint-dir', type=Path,
                        help='Directory for converter checkpoints')
    parser.add_argument('--poll-interval', type=float, default=5.0,
                        help='Polling interval in seconds when watchdog is unavailable (default: 5)')
    parser.add_argument('--worker-poll-interval', type=float, default=5.0,
                        help='Idle wait time in seconds between queue checks (default: 5)')
    parser.add_argument('--expected-subbands', type=int, default=16,
                        help='Expected number of subbands per group (default: 16)')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Maximum converter retries before marking a group failed (default: 3)')
    parser.add_argument('--omp-threads', type=int,
                        help='Set OMP_NUM_THREADS/MKL_NUM_THREADS for converter subprocess')
    parser.add_argument('--use-subprocess', action='store_true', default=False,
                        help='Launch the batch converter in a separate process instead of in-process')
    parser.add_argument('--in-progress-timeout', type=float, default=900.0,
                        help='Seconds before stale in-progress groups are re-queued (default: 900)')
    parser.add_argument('--collecting-timeout', type=float, default=600.0,
                        help='Warn if groups remain incomplete for more than this many seconds (default: 600)')
    parser.add_argument('--monitoring', dest='monitoring', action='store_true', default=True,
                        help='Enable queue/resource monitoring (default: enabled)')
    parser.add_argument('--no-monitoring', dest='monitoring', action='store_false',
                        help='Disable queue/resource monitoring for minimal footprint')
    parser.add_argument('--monitor-interval', type=float, default=60.0,
                        help='Monitoring check interval in seconds (default: 60)')
    parser.add_argument('--profile', action='store_true', default=False,
                        help='Enable detailed performance profiling and timing logs')
    parser.add_argument('--chunk-duration', type=float, default=5.0,
                        help='Duration of data chunks in minutes (default: 5.0)')
    parser.add_argument('--log-level', default='INFO',
                        help='Service log level (default: INFO)')
    parser.add_argument('--cleanup-temp', action='store_true', default=False,
                        help='Remove temporary staging directories after conversion')
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

    checkpoint_dir = args.checkpoint_dir.expanduser().resolve() if args.checkpoint_dir else None
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    queue_db = QueueDB(
        args.queue_db.expanduser().resolve(),
        expected_subbands=args.expected_subbands,
        chunk_duration_minutes=args.chunk_duration,
    )
    queue_db.bootstrap_directory(input_dir)

    converter_path = (Path(__file__).resolve().parent.parent / 'uvh5_to_ms_converter.py').resolve()
    config = WorkerConfig(
        output_dir=output_dir,
        scratch_dir=scratch_dir,
        checkpoint_dir=checkpoint_dir,
        log_level=args.log_level,
        omp_threads=args.omp_threads,
        converter_path=converter_path,
        max_retries=args.max_retries,
        cleanup_temp=args.cleanup_temp,
        in_progress_timeout=args.in_progress_timeout,
        collecting_timeout=args.collecting_timeout,
        use_subprocess=args.use_subprocess,
        enable_monitoring=args.monitoring,
        monitor_interval=args.monitor_interval,
        profile=args.profile,
        chunk_duration_minutes=args.chunk_duration,
    )

    logging.info(
        "Converter execution mode: %s (chunk duration %.1f min)",
        "subprocess" if args.use_subprocess else "in-process",
        args.chunk_duration,
    )

    watcher = DirectoryWatcher(input_dir, queue_db, poll_interval=args.poll_interval)
    worker = StreamingWorker(queue_db, config, poll_interval=args.worker_poll_interval)
    
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


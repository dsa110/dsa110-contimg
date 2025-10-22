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
                (normalized_group, now, now,
                 self.chunk_duration_minutes, self.expected_subbands),
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
                """

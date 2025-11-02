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

    def _normalize_group_id_datetime(self, group_id: str) -> str:
        """Normalize group_id to 'YYYY-MM-DDTHH:MM:SS'. Accept 'T' or space."""
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
                        self._conn.execute("UPDATE ingest_queue SET group_id = ? WHERE group_id = ?", (norm, gid))
                        self._conn.execute("UPDATE subband_files SET group_id = ? WHERE group_id = ?", (norm, gid))
                        self._conn.execute("UPDATE performance_metrics SET group_id = ? WHERE group_id = ?", (norm, gid))
                    except sqlite3.DatabaseError:
                        continue

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
                """,
                (now, group_id),
            )
            return group_id

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
            try:
                if getattr(args, "use_subprocess", False):
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
                        cmd.extend(["--tmpfs-path", getattr(args, "tmpfs_path", "/dev/shm")])
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

            # Derive MS path from first subband filename
            try:
                files = queue.group_files(gid)
                if not files:
                    raise RuntimeError("no subband files recorded for group")
                first = os.path.basename(files[0])
                base = os.path.splitext(first)[0].split("_sb")[0]
                ms_path = os.path.join(args.output_dir, base + ".ms")
            except Exception as exc:
                log.error("Failed to locate MS for %s: %s", gid, exc)
                queue.update_state(gid, "completed")
                continue

            # Record conversion in products DB (stage=converted)
            try:
                products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")
                conn = ensure_products_db(Path(products_db_path))
                # Extract time range
                start_mjd = end_mjd = mid_mjd = None
                try:
                    from casatools import msmetadata  # type: ignore
                    msmd = msmetadata()
                    msmd.open(ms_path)
                    try:
                        tr = msmd.timerangeforobs()
                        if tr and isinstance(tr, (list, tuple)) and len(tr) >= 2:
                            start_mjd = float(tr[0])
                            end_mjd = float(tr[1])
                            mid_mjd = 0.5 * (start_mjd + end_mjd)
                    finally:
                        msmd.close()
                except Exception:
                    pass
                ms_index_upsert(
                    conn,
                    ms_path,
                    start_mjd=start_mjd,
                    end_mjd=end_mjd,
                    mid_mjd=mid_mjd,
                    processed_at=time.time(),
                    status="converted",
                    stage="converted",
                )
                conn.commit()
            except Exception:
                log.debug("ms_index conversion upsert failed", exc_info=True)

            # Apply calibration from registry if available, then quick image
            try:
                # Determine mid_mjd for applylist
                if mid_mjd is None:
                    # fallback quick mid time via casacore tables
                    try:
                        from casacore.tables import table as _tb
                        with _tb(f"{ms_path}::OBSERVATION") as _obs:
                            t0 = _obs.getcol("TIME_RANGE")[0][0] / 86400.0
                            t1 = _obs.getcol("TIME_RANGE")[0][1] / 86400.0
                            mid_mjd = 0.5 * (float(t0) + float(t1))
                    except Exception:
                        pass

                applylist = []
                try:
                    applylist = get_active_applylist(Path(args.registry_db), float(mid_mjd) if mid_mjd is not None else time.time()/86400.0)
                except Exception:
                    applylist = []

                cal_applied = 0
                if applylist:
                    try:
                        apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                        cal_applied = 1
                    except Exception:
                        log.warning("applycal failed for %s", ms_path, exc_info=True)

                # Quick image
                imgroot = os.path.join(args.output_dir, base + ".img")
                try:
                    image_ms(ms_path, imagename=imgroot, field="", quick=True, skip_fits=False)
                except Exception:
                    log.error("imaging failed for %s", ms_path, exc_info=True)

                # Update products DB with imaging artifacts and stage
                try:
                    products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")
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
                    for suffix, pbcor in [(".image", 0), (".pb", 0), (".pbcor", 1), (".residual", 0), (".model", 0)]:
                        p = f"{imgroot}{suffix}"
                        if os.path.isdir(p) or os.path.isfile(p):
                            images_insert(conn, p, ms_path, now_ts, "5min", pbcor)
                    conn.commit()
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
    seen: Set[str] = set()
    input_dir = Path(args.input_dir)
    interval = float(getattr(args, "poll_interval", 5.0))
    while True:
        try:
            for p in input_dir.glob("*_sb??.hdf5"):
                sp = os.fspath(p)
                if sp in seen:
                    continue
                seen.add(sp)
                info = parse_subband_info(p)
                if info is None:
                    continue
                gid, sb = info
                queue.record_subband(gid, sb, p)
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
    p.add_argument("--scratch-dir", default="/scratch/dsa110-contimg")
    p.add_argument("--expected-subbands", type=int, default=16)
    p.add_argument("--chunk-duration", type=float, default=5.0, help="Minutes per group")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--use-subprocess", action="store_true")
    p.add_argument("--monitoring", action="store_true")
    p.add_argument("--monitor-interval", type=float, default=60.0)
    p.add_argument("--poll-interval", type=float, default=5.0)
    p.add_argument("--worker-poll-interval", type=float, default=5.0)
    p.add_argument("--max-workers", type=int, default=4)
    p.add_argument("--stage-to-tmpfs", action="store_true")
    p.add_argument("--tmpfs-path", default="/dev/shm")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Set CASA log directory before any CASA task calls - CASA writes logs to CWD
    try:
        from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
        casa_log_dir = derive_casa_log_dir()
        os.chdir(str(casa_log_dir))
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    qdb = QueueDB(Path(args.queue_db), expected_subbands=int(args.expected_subbands), chunk_duration_minutes=float(args.chunk_duration))
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
                    cur = qdb._conn.execute("SELECT state, COUNT(*) FROM ingest_queue GROUP BY state").fetchall()
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

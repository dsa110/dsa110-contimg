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
from dsa110_contimg.utils.ms_organization import (
    organize_ms_file, determine_ms_type, create_path_mapper, extract_date_from_filename
)  # noqa

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
                # Commit transaction
                self._conn.commit()
            except Exception:
                # Rollback on any error to maintain consistency
                self._conn.rollback()
                raise

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
                     ORDER BY received_at ASC
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
            with h5py.File(path, 'r') as f:
                # Verify file has required structure (Header or Data group)
                if 'Header' not in f and 'Data' not in f:
                    log.warning(f"File does not appear to be valid HDF5/UVH5: {path}")
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
            path_mapper = create_path_mapper(ms_base_dir, is_calibrator=False, is_failed=False)
            
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
            products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")
            try:
                files = queue.group_files(gid)
                if not files:
                    raise RuntimeError("no subband files recorded for group")
                first = os.path.basename(files[0])
                base = os.path.splitext(first)[0].split("_sb")[0]
                
                # If path_mapper was used, MS is already in organized location
                # Otherwise, compute organized path now
                if not getattr(args, "use_subprocess", False):
                    # MS was written directly to organized location via path_mapper
                    ms_path = path_mapper(base, args.output_dir)
                else:
                    # Subprocess mode: compute organized path and move if needed
                    ms_path_flat = os.path.join(args.output_dir, base + ".ms")
                    ms_path_obj = Path(ms_path_flat)
                    ms_base_dir = Path(args.output_dir)
                    
                    # Determine MS type and organize
                    try:
                        is_calibrator, is_failed = determine_ms_type(ms_path_obj)
                        organized_path = organize_ms_file(
                            ms_path_obj,
                            ms_base_dir,
                            Path(products_db_path),
                            is_calibrator=is_calibrator,
                            is_failed=is_failed,
                            update_database=False  # We'll register with correct path below
                        )
                        ms_path = str(organized_path)
                        if organized_path != ms_path_obj:
                            log.info(f"Organized MS file: {ms_path_flat} → {ms_path}")
                    except Exception as e:
                        log.warning(f"Failed to organize MS file {ms_path_flat}: {e}. Using flat path.", exc_info=True)
                        ms_path = ms_path_flat
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
                )
                conn.commit()
            except Exception:
                log.debug("ms_index conversion upsert failed", exc_info=True)

            # Apply calibration from registry if available, then image (development tier)
            try:
                # Determine mid_mjd for applylist
                if mid_mjd is None:
                    # fallback: try extract_ms_time_range again (it has multiple fallbacks)
                    try:
                        from dsa110_contimg.utils.time_utils import extract_ms_time_range
                        _, _, mid_mjd = extract_ms_time_range(ms_path)
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

                # Standard tier imaging (production quality)
                # Note: Data is always reordered for correct multi-SPW processing
                imgroot = os.path.join(args.output_dir, base + ".img")
                try:
                    image_ms(ms_path, imagename=imgroot, field="", quality_tier="standard", skip_fits=False)
                    
                    # Run catalog-based flux scale validation
                    try:
                        from dsa110_contimg.qa.catalog_validation import validate_flux_scale
                        from pathlib import Path
                        
                        # Find PB-corrected FITS image (preferred for validation)
                        pbcor_fits = f"{imgroot}.pbcor.fits"
                        fits_image = pbcor_fits if Path(pbcor_fits).exists() else f"{imgroot}.fits"
                        
                        if Path(fits_image).exists():
                            log.info(f"Running catalog-based flux scale validation (NVSS) on {fits_image}")
                            result = validate_flux_scale(
                                image_path=fits_image,
                                catalog="nvss",
                                min_snr=5.0,
                                flux_range_jy=(0.01, 10.0),
                                max_flux_ratio_error=0.2
                            )
                            
                            if result.n_matched > 0:
                                log.info(
                                    f"Catalog validation (NVSS): {result.n_matched} sources matched, "
                                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                                    f"scale error={result.flux_scale_error*100:.1f}%"
                                )
                                if result.has_issues:
                                    log.warning(f"Catalog validation issues: {', '.join(result.issues)}")
                                if result.has_warnings:
                                    log.warning(f"Catalog validation warnings: {', '.join(result.warnings)}")
                            else:
                                log.warning("Catalog validation: No sources matched")
                        else:
                            log.debug(f"Catalog validation skipped: FITS image not found ({fits_image})")
                    except Exception as e:
                        log.warning(f"Catalog validation failed (non-fatal): {e}")
                        
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
    if hasattr(args, 'scratch_dir') and args.scratch_dir:
        scratch_path = Path(args.scratch_dir)
        scratch_path.mkdir(parents=True, exist_ok=True)
        if not scratch_path.exists():
            log.error(f"Failed to create scratch directory: {args.scratch_dir}")
            return 1
        if not os.access(args.scratch_dir, os.W_OK):
            log.error(f"Scratch directory is not writable: {args.scratch_dir}")
            return 1
    
    log.info("✓ Directory validation passed")

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

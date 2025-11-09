#!/usr/bin/env python3
"""
Housekeeping utility for the continuum pipeline.

Functions:
- Recover stale 'in_progress' groups back to 'pending' after a timeout
- Mark very stale 'collecting' as 'failed' for operator review
- Remove old temporary staging directories (prefix 'stream_')
"""

import argparse
import os
import shutil
import sqlite3
import time
from pathlib import Path

try:
    from dsa110_contimg.utils.cli_helpers import ensure_scratch_dirs
except ImportError:
    ensure_scratch_dirs = None


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(os.fspath(db))
    conn.row_factory = sqlite3.Row
    return conn


def recover_queue(queue_db: Path, *, in_progress_timeout: float, collecting_timeout: float) -> None:
    now = time.time()
    with _connect(queue_db) as conn:
        # Recover stale in_progress
        cutoff = now - in_progress_timeout
        rows = conn.execute(
            "SELECT group_id, retry_count FROM ingest_queue WHERE state='in_progress' AND last_update < ?",
            (cutoff,),
        ).fetchall()
        for r in rows:
            conn.execute(
                "UPDATE ingest_queue SET state='pending', retry_count=?, last_update=?, error=? WHERE group_id=?",
                (int(r["retry_count"] or 0) + 1, now, "Recovered by housekeeping", r["group_id"]),
            )
        # Mark stale collecting as failed (operator can clean or requeue later)
        cutoff_c = now - collecting_timeout
        conn.execute(
            "UPDATE ingest_queue SET state='failed', last_update=?, error=? WHERE state='collecting' AND received_at < ?",
            (now, "Collecting timeout", cutoff_c),
        )
        conn.commit()


def cleanup_tempdirs(root: Path, *, older_than: float) -> int:
    deleted = 0
    now = time.time()
    for p in root.glob('stream_*'):
        try:
            if not p.is_dir():
                continue
            age = now - p.stat().st_mtime
            if age >= older_than:
                shutil.rmtree(p, ignore_errors=True)
                deleted += 1
        except Exception:
            continue
    return deleted


def cleanup_scratch_tmp(scratch_dir: Path, *, older_than: float) -> int:
    """Clean up old files in /scratch/tmp/ directory."""
    tmp_dir = scratch_dir / 'tmp'
    if not tmp_dir.exists():
        return 0
    
    deleted = 0
    now = time.time()
    try:
        for p in tmp_dir.iterdir():
            try:
                if p.is_file():
                    age = now - p.stat().st_mtime
                    if age >= older_than:
                        p.unlink()
                        deleted += 1
                elif p.is_dir():
                    age = now - p.stat().st_mtime
                    if age >= older_than:
                        shutil.rmtree(p, ignore_errors=True)
                        deleted += 1
            except Exception:
                continue
    except Exception:
        pass
    return deleted


def cleanup_tmppointing_dirs(root_dir: Path, *, older_than: float) -> int:
    """Clean up old TMPPOINTING* directories created by CASA/casacore.
    
    These are temporary directories created by CASA for pointing table operations.
    They should be cleaned up if they're older than the specified age.
    
    Args:
        root_dir: Root directory to search for TMPPOINTING* directories
        older_than: Delete directories older than this many seconds
        
    Returns:
        Number of directories deleted
    """
    deleted = 0
    now = time.time()
    
    try:
        # Search for TMPPOINTING* directories in the root directory
        for p in root_dir.glob('TMPPOINTING*'):
            try:
                if not p.is_dir():
                    continue
                age = now - p.stat().st_mtime
                if age >= older_than:
                    shutil.rmtree(p, ignore_errors=True)
                    deleted += 1
            except Exception:
                continue
    except Exception:
        pass
    
    return deleted


def validate_scratch_structure(scratch_dir: Path) -> bool:
    """Validate that scratch directory structure exists."""
    if ensure_scratch_dirs is None:
        return False
    
    try:
        dirs = ensure_scratch_dirs()
        # Check that all expected directories exist
        required = ['ms', 'caltables', 'images', 'mosaics', 'logs', 'tmp']
        for name in required:
            if name not in dirs or not dirs[name].exists():
                print(f"Warning: Scratch directory {name} does not exist at {dirs.get(name, 'unknown')}")
                return False
        return True
    except Exception as e:
        print(f"Warning: Failed to validate scratch structure: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Pipeline housekeeping")
    ap.add_argument('--queue-db', default='state/ingest.sqlite3')
    ap.add_argument('--scratch-dir', default=None, help='Scratch directory (defaults to CONTIMG_SCRATCH_DIR or /stage/dsa110-contimg)')
    ap.add_argument('--in-progress-timeout', type=float, default=3600.0, help='Seconds to recover in-progress to pending')
    ap.add_argument('--collecting-timeout', type=float, default=86400.0, help='Seconds to mark collecting as failed')
    ap.add_argument('--temp-age', type=float, default=86400.0, help='Delete temp staging dirs older than this many seconds')
    ap.add_argument('--root-dir', default=None, help='Root directory to clean TMPPOINTING dirs from (defaults to /data/dsa110-contimg)')
    args = ap.parse_args()

    # Determine scratch directory
    scratch_dir = Path(args.scratch_dir) if args.scratch_dir else Path(
        os.getenv('CONTIMG_SCRATCH_DIR', '/stage/dsa110-contimg')
    )

    # Validate scratch structure
    if validate_scratch_structure(scratch_dir):
        print(f"✓ Scratch directory structure validated at {scratch_dir}")
    else:
        print(f"⚠ Warning: Scratch directory structure incomplete at {scratch_dir}")

    # Clean up scratch tmp directory
    n_tmp = cleanup_scratch_tmp(scratch_dir, older_than=args.temp_age)
    if n_tmp > 0:
        print(f"Removed {n_tmp} old files/dirs from {scratch_dir}/tmp")

    # Recover queue
    recover_queue(Path(args.queue_db), in_progress_timeout=args.in_progress_timeout, collecting_timeout=args.collecting_timeout)
    
    # Clean up old temp staging directories
    n = cleanup_tempdirs(scratch_dir, older_than=args.temp_age)
    if n > 0:
        print(f"Removed {n} temp staging dirs from {scratch_dir}")
    
    # Clean up TMPPOINTING* directories from root directory
    root_dir = Path(args.root_dir) if args.root_dir else Path(
        os.getenv('CONTIMG_ROOT_DIR', '/data/dsa110-contimg')
    )
    n_tmppointing = cleanup_tmppointing_dirs(root_dir, older_than=args.temp_age)
    if n_tmppointing > 0:
        print(f"Removed {n_tmppointing} old TMPPOINTING* directories from {root_dir}")
    
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


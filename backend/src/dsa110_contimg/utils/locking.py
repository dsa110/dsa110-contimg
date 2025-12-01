"""
File-based locking utilities for preventing concurrent operations.

This module provides file-based locking mechanisms to prevent race conditions
when multiple processes attempt to operate on the same resource simultaneously.
"""

import fcntl
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LockError(Exception):
    """Raised when a lock cannot be acquired."""

    pass


@contextmanager
def file_lock(lock_path: Path, timeout: float = 300.0, poll_interval: float = 1.0):
    """Acquire an exclusive file lock, blocking until available or timeout.

    This uses fcntl.flock() for advisory locking on Unix systems. The lock
    is automatically released when exiting the context manager.

    Args:
        lock_path: Path to lock file (will be created if needed)
        timeout: Maximum time to wait for lock (seconds). Default: 5 minutes
        poll_interval: How often to check if lock is available (seconds)

    Yields:
        Lock file path (for reference)

    Raises:
        LockError: If lock cannot be acquired within timeout period

    Example:
        with file_lock(Path("/tmp/my_operation.lock"), timeout=60):
            # Critical section - only one process can execute this at a time
            perform_exclusive_operation()
    """
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_file = None
    start_time = time.time()

    try:
        # Try to acquire lock with timeout
        while True:
            try:
                lock_file = open(lock_path, "w")
                # Try to acquire exclusive lock (non-blocking)
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Lock acquired successfully
                lock_file.write(f"{os.getpid()}\n")
                lock_file.flush()
                logger.debug(f"Acquired lock: {lock_path}")
                break

            except (IOError, OSError) as e:
                # Lock is held by another process
                if lock_file:
                    lock_file.close()
                    lock_file = None

                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    error_msg = (
                        f"Could not acquire lock {lock_path} within {timeout}s. "
                        f"Another process may be running. "
                        f"Check for stale lock files if no process is running."
                    )
                    logger.error(error_msg)
                    raise LockError(error_msg) from e

                logger.debug(
                    f"Lock {lock_path} is held by another process, "
                    f"waiting... ({elapsed:.1f}s elapsed)"
                )
                time.sleep(poll_interval)

        # Yield lock file path
        yield lock_path

    finally:
        # Release lock
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                logger.debug(f"Released lock: {lock_path}")
            except OSError as e:
                logger.warning(f"Error releasing lock {lock_path}: {e}")

            # Clean up lock file if empty or stale
            try:
                if lock_path.exists() and lock_path.stat().st_size == 0:
                    lock_path.unlink()
            except OSError:
                pass


def check_lock(lock_path: Path) -> tuple[bool, Optional[str]]:
    """Check if a lock file exists and is held.

    Args:
        lock_path: Path to lock file

    Returns:
        (is_locked, pid_string) tuple where pid_string is the PID holding the lock
        or None if lock is not held
    """
    lock_path = Path(lock_path)
    if not lock_path.exists():
        return False, None

    try:
        with open(lock_path, "r") as f:
            pid_str = f.read().strip()
            # Check if process is still running
            try:
                pid = int(pid_str)
                # Check if process exists (Unix-specific)
                os.kill(pid, 0)  # Signal 0 doesn't kill, just checks existence
                return True, pid_str
            except (ValueError, OSError):
                # PID invalid or process doesn't exist - stale lock
                return False, None
    except OSError:
        return False, None


def cleanup_stale_locks(lock_dir: Path, timeout_seconds: float = 3600.0) -> int:
    """Clean up stale lock files in a directory.

    A lock is considered stale if:
    - The lock file exists but the process holding it is no longer running
    - The lock file is older than timeout_seconds (default: 1 hour)

    Args:
        lock_dir: Directory containing lock files
        timeout_seconds: Maximum age of lock file before considering it stale

    Returns:
        Number of stale locks cleaned up
    """
    lock_dir = Path(lock_dir)
    if not lock_dir.exists():
        return 0

    cleaned = 0
    current_time = time.time()

    for lock_file in lock_dir.glob("*.lock"):
        try:
            # Check file age
            file_age = current_time - lock_file.stat().st_mtime
            if file_age > timeout_seconds:
                logger.warning(f"Removing stale lock file (age: {file_age:.0f}s): {lock_file}")
                lock_file.unlink()
                cleaned += 1
                continue

            # Check if process is still running
            is_locked, pid_str = check_lock(lock_file)
            if not is_locked:
                logger.warning(
                    f"Removing stale lock file (process {pid_str} not running): {lock_file}"
                )
                lock_file.unlink()
                cleaned += 1

        except Exception as e:
            logger.warning(f"Error checking lock file {lock_file}: {e}")

    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} stale lock file(s) from {lock_dir}")

    return cleaned

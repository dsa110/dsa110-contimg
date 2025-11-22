#!/opt/miniforge/envs/casa6/bin/python
"""Cleanup script to move CASA log files from workspace root to proper log directory.

This script is designed for minimal CPU usage:
- Uses efficient file operations (os.rename for atomic moves)
- Processes files in batches with small delays
- Only moves files, doesn't read/write content
- Uses pathlib for efficient path operations
"""

import os
import sys
import time
from pathlib import Path
from typing import List


# Minimal logging - only errors
def log_error(msg: str) -> None:
    """Log error to stderr."""
    print(f"ERROR: {msg}", file=sys.stderr)


def get_log_directories() -> tuple[Path, Path]:
    """Get source (workspace root) and destination (log directory) paths.

    Returns:
        (source_dir, dest_dir) tuple
    """
    # Source: workspace root where logs are currently
    source_dir = Path("/data/dsa110-contimg/src")

    # Destination: proper log directory
    state_dir = os.getenv("CONTIMG_STATE_DIR") or os.getenv("PIPELINE_STATE_DIR")
    if state_dir:
        dest_dir = Path(state_dir) / "logs"
    else:
        dest_dir = Path("/data/dsa110-contimg/state/logs")

    return source_dir, dest_dir


def find_casa_logs(source_dir: Path) -> List[Path]:
    """Find all CASA log files in source directory.

    CASA log files match pattern: casa-YYYYMMDD-HHMMSS.log
    """
    casa_logs = []
    try:
        # Use glob for efficient pattern matching
        casa_logs = list(source_dir.glob("casa-*.log"))
        # Sort by modification time (oldest first) for predictable processing
        casa_logs.sort(key=lambda p: p.stat().st_mtime)
    except (OSError, PermissionError) as e:
        log_error(f"Failed to scan for CASA logs: {e}")

    return casa_logs


def move_log_file(source: Path, dest_dir: Path) -> bool:
    """Move a single log file from source to destination directory.

    Uses os.rename for atomic move operation (very efficient).

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure destination directory exists
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Destination path
        dest = dest_dir / source.name

        # Check if destination already exists
        if dest.exists():
            # Append timestamp to avoid overwriting
            timestamp = int(time.time())
            dest = dest_dir / f"{source.stem}_{timestamp}{source.suffix}"

        # Atomic move operation (very efficient - just updates directory entries)
        os.rename(str(source), str(dest))
        return True

    except (OSError, PermissionError) as e:
        log_error(f"Failed to move {source.name}: {e}")
        return False


def main() -> int:
    """Main cleanup function.

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    source_dir, dest_dir = get_log_directories()

    # Check if source directory exists
    if not source_dir.exists():
        print(f"Source directory does not exist: {source_dir}")
        return 0  # Not an error - just nothing to do

    # Find all CASA log files
    casa_logs = find_casa_logs(source_dir)

    if not casa_logs:
        print("No CASA log files found in workspace root.")
        return 0

    print(f"Found {len(casa_logs)} CASA log file(s) to move.")
    print(f"Moving from: {source_dir}")
    print(f"Moving to: {dest_dir}")

    # Process files in small batches with minimal CPU usage
    batch_size = 10
    moved_count = 0
    failed_count = 0

    for i in range(0, len(casa_logs), batch_size):
        batch = casa_logs[i : i + batch_size]

        for log_file in batch:
            if move_log_file(log_file, dest_dir):
                moved_count += 1
            else:
                failed_count += 1

        # Small delay between batches to keep CPU usage low
        # Only if there are more files to process
        if i + batch_size < len(casa_logs):
            time.sleep(0.1)  # 100ms delay - minimal CPU impact

    # Summary
    print("\nCleanup complete:")
    print(f"  Moved: {moved_count}")
    print(f"  Failed: {failed_count}")

    if failed_count > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

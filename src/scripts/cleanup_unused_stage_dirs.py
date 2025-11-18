#!/opt/miniforge/envs/casa6/bin/python
"""Cleanup script to remove unused directories from /stage/dsa110-contimg/.

This script removes directories that are not used by the pipeline:
- logs/ - Log files (not part of data pipeline)
- tmp/ - Temporary files (can be cleaned if old)
- state/ - State files (if duplicate of /data/dsa110-contimg/state/)

WARNING: Review the analysis output before running this script!
"""

import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

STAGE_BASE = Path("/stage/dsa110-contimg")
DATA_STATE_DIR = Path("/data/dsa110-contimg/state")


def check_state_directory() -> bool:
    """Check if /stage/dsa110-contimg/state/ is a duplicate of /data/dsa110-contimg/state/."""
    stage_state = STAGE_BASE / "state"
    data_state = DATA_STATE_DIR

    if not stage_state.exists():
        return False

    if not data_state.exists():
        print(f"Warning: {data_state} does not exist. Keeping {stage_state}")
        return False

    # Check if files in stage/state are older or same as in data/state
    stage_files = {f.name: f.stat().st_mtime for f in stage_state.iterdir() if f.is_file()}
    data_files = {f.name: f.stat().st_mtime for f in data_state.iterdir() if f.is_file()}

    # If stage has same files but older, it's likely a duplicate
    if stage_files.keys() == data_files.keys():
        print("Found duplicate state directory:")
        print(f"  Stage: {stage_state}")
        print(f"  Data: {data_state}")
        print(f"  Files: {', '.join(stage_files.keys())}")
        return True

    return False


def cleanup_tmp_directory(days_old: int = 7) -> int:
    """Clean up old files in tmp directory.

    Returns:
        Number of files/directories removed
    """
    tmp_dir = STAGE_BASE / "tmp"
    if not tmp_dir.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=days_old)
    removed_count = 0

    print(f"\nCleaning tmp/ directory (removing files older than {days_old} days)...")

    for item in tmp_dir.iterdir():
        try:
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff_time:
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"  Removed directory: {item.name}")
                else:
                    item.unlink()
                    print(f"  Removed file: {item.name}")
                removed_count += 1
        except Exception as e:
            print(f"  Warning: Could not remove {item.name}: {e}")

    return removed_count


def main():
    """Main cleanup function."""
    print("=" * 80)
    print("DSA110 Continuum Imaging Pipeline - Stage Directory Cleanup")
    print("=" * 80)
    print()

    # Check what we're about to remove
    directories_to_remove = []

    # 1. logs/ - safe to remove
    logs_dir = STAGE_BASE / "logs"
    if logs_dir.exists():
        size = get_directory_size(logs_dir)
        directories_to_remove.append(("logs", logs_dir, f"Log files {size}"))

    # 2. state/ - check if duplicate
    state_dir = STAGE_BASE / "state"
    if state_dir.exists() and check_state_directory():
        size = get_directory_size(state_dir)
        directories_to_remove.append(("state", state_dir, f"Duplicate state directory {size}"))
    elif state_dir.exists():
        print(f"⚠ Keeping {state_dir} - appears to be in use or different from {DATA_STATE_DIR}")

    # 3. tmp/ - clean old files
    tmp_dir = STAGE_BASE / "tmp"
    if tmp_dir.exists():
        removed = cleanup_tmp_directory(days_old=7)
        if removed > 0:
            print(f"✓ Cleaned {removed} old items from tmp/")
        else:
            print("✓ No old files to clean in tmp/ (keeping directory)")

    if not directories_to_remove:
        print("\n✓ No unused directories to remove.")
        return 0

    # Show what will be removed
    print("\n" + "=" * 80)
    print("DIRECTORIES TO REMOVE:")
    print("=" * 80)
    for name, path, description in directories_to_remove:
        print(f"  - {name}/: {description}")

    # Ask for confirmation
    print("\n" + "=" * 80)
    response = input("Remove these directories? (yes/no): ").strip().lower()

    if response not in ["yes", "y"]:
        print("Aborted.")
        return 0

    # Remove directories
    print("\nRemoving directories...")
    for name, path, description in directories_to_remove:
        try:
            if path.is_dir():
                shutil.rmtree(path)
                print(f"✓ Removed {name}/")
            else:
                path.unlink()
                print(f"✓ Removed {name}")
        except Exception as e:
            print(f"✗ Failed to remove {name}/: {e}")
            return 1

    print("\n" + "=" * 80)
    print("Cleanup complete!")
    print("=" * 80)
    return 0


def get_directory_size(path: Path) -> str:
    """Get human-readable directory size."""
    try:
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass

        # Convert to human-readable format
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if total < 1024.0:
                return f"({total:.1f} {unit})"
            total /= 1024.0
        return f"({total:.1f} PB)"
    except Exception:
        return "(size unknown)"


if __name__ == "__main__":
    sys.exit(main())

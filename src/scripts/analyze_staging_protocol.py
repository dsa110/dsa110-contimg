#!/opt/miniforge/envs/casa6/bin/python
"""Analyze staging protocol and identify unused directories in /stage/.

This script:
1. Documents the staging protocol for the dsa110 continuum imaging pipeline
2. Identifies directories in /stage/dsa110-contimg/ that are used by the pipeline
3. Identifies directories that are NOT used and can be safely removed
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Set, Tuple

# Pipeline staging base directory
STAGE_BASE = Path("/stage/dsa110-contimg")
DATA_REGISTRY_DB = Path("/data/dsa110-contimg/state/data_registry.sqlite3")


def get_used_directories_from_code() -> Set[str]:
    """Get directories that are used by the pipeline based on code analysis.

    These are directories that appear in:
    - type_to_dir mapping in data_registry.py (for publishing)
    - Environment variable defaults
    - Hardcoded paths in the codebase
    """
    # From data_registry.py type_to_dir mapping
    # These are the directories that data gets published FROM
    used_dirs = {
        "ms",  # Measurement sets
        "images",  # Individual images
        "mosaics",  # Mosaic images
        "caltables",  # Calibration tables
        "calib_ms",  # Calibrator measurement sets
        "catalogs",  # Source catalogs
        "qa",  # Quality assurance data
        "metadata",  # Metadata files
    }
    return used_dirs


def get_directories_in_stage() -> Set[str]:
    """Get all directories currently in /stage/dsa110-contimg/."""
    if not STAGE_BASE.exists():
        return set()

    dirs = set()
    for item in STAGE_BASE.iterdir():
        if item.is_dir():
            dirs.add(item.name)
    return dirs


def check_database_references(stage_dir: str) -> Tuple[bool, int]:
    """Check if a directory is referenced in the data_registry database.

    Returns:
        (is_referenced, count): Whether directory is referenced and how many times
    """
    if not DATA_REGISTRY_DB.exists():
        return False, 0

    try:
        conn = sqlite3.connect(str(DATA_REGISTRY_DB))
        cur = conn.cursor()

        # Check stage_path column for references to this directory
        pattern = f"%/{stage_dir}/%"
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM data_registry 
            WHERE stage_path LIKE ?
            """,
            (pattern,),
        )
        count = cur.fetchone()[0]
        conn.close()

        return count > 0, count
    except Exception as e:
        print(f"Warning: Could not check database for {stage_dir}: {e}")
        return False, 0


def analyze_staging_protocol() -> Dict:
    """Analyze the staging protocol and directory usage."""
    print("=" * 80)
    print("DSA110 Continuum Imaging Pipeline - Staging Protocol Analysis")
    print("=" * 80)
    print()

    # Get directories
    used_dirs = get_used_directories_from_code()
    existing_dirs = get_directories_in_stage()

    print("STAGING PROTOCOL:")
    print("-" * 80)
    print("1. Data is saved to /stage/dsa110-contimg/ during processing (staging phase)")
    print("2. Subdirectories are organized by data type:")
    for dir_name in sorted(used_dirs):
        print(f"   - {dir_name}/")
    print()
    print("3. Publishing process:")
    print("   - When wait_for_published=False: Data stays in /stage/")
    print("   - When wait_for_published=True or auto_publish=True:")
    print("     * Data is moved from /stage/dsa110-contimg/<type>/ to")
    print("       /data/dsa110-contimg/products/<type>/")
    print("     * Status in data_registry changes: 'staging' -> 'publishing' -> 'published'")
    print()
    print("4. Data types and their staging directories:")
    type_mapping = {
        "ms": "Measurement sets (raw/converted data)",
        "calib_ms": "Calibrator measurement sets",
        "caltables": "Calibration tables",
        "images": "Individual tile images",
        "mosaics": "Mosaic images (final products)",
        "catalog": "Source catalogs",
        "qa": "Quality assurance data",
        "metadata": "Metadata files",
    }
    for dir_name, description in sorted(type_mapping.items()):
        print(f"   - {dir_name}/: {description}")
    print()

    print("DIRECTORY ANALYSIS:")
    print("-" * 80)
    print(f"Directories used by pipeline (from code): {len(used_dirs)}")
    print(f"Directories currently in /stage/: {len(existing_dirs)}")
    print()

    # Categorize directories
    definitely_used = existing_dirs & used_dirs
    potentially_unused = existing_dirs - used_dirs
    missing_but_expected = used_dirs - existing_dirs

    print("DIRECTORY STATUS:")
    print("-" * 80)

    if definitely_used:
        print(f"\n✓ USED BY PIPELINE ({len(definitely_used)} directories):")
        for dir_name in sorted(definitely_used):
            dir_path = STAGE_BASE / dir_name
            size = get_directory_size(dir_path)
            in_db, db_count = check_database_references(dir_name)
            db_info = f" ({db_count} DB refs)" if in_db else " (no DB refs)"
            print(f"   - {dir_name}/ {size}{db_info}")

    if potentially_unused:
        print(f"\n⚠ POTENTIALLY UNUSED ({len(potentially_unused)} directories):")
        for dir_name in sorted(potentially_unused):
            dir_path = STAGE_BASE / dir_name
            size = get_directory_size(dir_path)
            in_db, db_count = check_database_references(dir_name)

            # Special handling for known directories
            if dir_name == "tmp":
                print(f"   - {dir_name}/ {size} - Temporary files (may be used during processing)")
            elif dir_name == "logs":
                print(f"   - {dir_name}/ {size} - Log files (not part of data pipeline)")
            elif dir_name == "state":
                print(f"   - {dir_name}/ {size} - State files (may contain DB files)")
            else:
                db_info = f" ({db_count} DB refs)" if in_db else " (no DB refs)"
                print(f"   - {dir_name}/ {size}{db_info}")

    if missing_but_expected:
        print(f"\n? EXPECTED BUT NOT FOUND ({len(missing_but_expected)} directories):")
        for dir_name in sorted(missing_but_expected):
            print(f"   - {dir_name}/ (will be created when needed)")

    print()
    print("RECOMMENDATIONS:")
    print("-" * 80)

    safe_to_remove = []
    review_before_removing = []

    for dir_name in sorted(potentially_unused):
        in_db, db_count = check_database_references(dir_name)

        if dir_name == "tmp":
            # tmp is likely used for temporary processing files
            # Check if it's empty or contains old files
            dir_path = STAGE_BASE / dir_name
            if is_directory_old_or_empty(dir_path, days=7):
                review_before_removing.append(
                    (dir_name, "Temporary files - check if processing is complete")
                )
            else:
                review_before_removing.append((dir_name, "Temporary files - may be in active use"))
        elif dir_name == "logs":
            # Logs are not part of the data pipeline
            safe_to_remove.append((dir_name, "Log files - not part of data pipeline"))
        elif dir_name == "state":
            # State might contain database files - be careful
            review_before_removing.append((dir_name, "State files - may contain database files"))
        elif not in_db:
            # Not in database and not in code - likely safe to remove
            safe_to_remove.append((dir_name, "Not referenced in code or database"))
        else:
            review_before_removing.append((dir_name, f"Referenced in database ({db_count} times)"))

    if safe_to_remove:
        print("\n✓ SAFE TO REMOVE (not used by pipeline):")
        for dir_name, reason in safe_to_remove:
            dir_path = STAGE_BASE / dir_name
            size = get_directory_size(dir_path)
            print(f"   - {dir_name}/ {size} - {reason}")

    if review_before_removing:
        print("\n⚠ REVIEW BEFORE REMOVING:")
        for dir_name, reason in review_before_removing:
            dir_path = STAGE_BASE / dir_name
            size = get_directory_size(dir_path)
            print(f"   - {dir_name}/ {size} - {reason}")

    return {
        "used": sorted(definitely_used),
        "potentially_unused": sorted(potentially_unused),
        "safe_to_remove": [d[0] for d in safe_to_remove],
        "review_before_removing": [d[0] for d in review_before_removing],
    }


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


def is_directory_old_or_empty(path: Path, days: int = 7) -> bool:
    """Check if directory is empty or only contains files older than specified days."""
    import time

    cutoff_time = time.time() - (days * 24 * 3600)

    try:
        if not any(path.iterdir()):
            return True  # Empty

        # Check if all files are old
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    mtime = item.stat().st_mtime
                    if mtime > cutoff_time:
                        return False  # Found a recent file
                except (OSError, FileNotFoundError):
                    pass
        return True  # All files are old
    except Exception:
        return False  # Can't determine, assume not safe


if __name__ == "__main__":
    result = analyze_staging_protocol()
    print()
    print("=" * 80)
    print("Analysis complete!")
    print("=" * 80)

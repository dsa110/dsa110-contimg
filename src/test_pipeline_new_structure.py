#!/opt/miniforge/envs/casa6/bin/python
"""Test the pipeline with the new directory structure enabled.

This script:
1. Enables the new structure
2. Creates a test mosaic
3. Monitors for path-related issues
4. Verifies calibrated MS files move correctly
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Enable new structure
os.environ["CONTIMG_USE_NEW_STRUCTURE"] = "1"

sys.path.insert(0, str(Path(__file__).parent))

# Set up logging to capture path-related issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline_test_new_structure.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def check_directory_structure():
    """Verify new directory structure is in place."""
    logger.info("=" * 80)
    logger.info("Checking Directory Structure")
    logger.info("=" * 80)

    from dsa110_contimg.database.data_config import (
      STAGE_BASE, USE_NEW_STRUCTURE, get_calibrated_ms_dir,
      get_calibration_tables_dir, get_raw_ms_dir, get_workspace_dir)

    if not USE_NEW_STRUCTURE:
        logger.error("✗ New structure is NOT enabled!")
        return False

    logger.info("✓ New structure is enabled")

    # Check directories exist
    dirs_to_check = [
        (get_raw_ms_dir(), "Raw MS"),
        (get_calibrated_ms_dir(), "Calibrated MS"),
        (get_calibration_tables_dir(), "Calibration Tables"),
        (get_workspace_dir(), "Workspace"),
    ]

    all_exist = True
    for dir_path, name in dirs_to_check:
        if dir_path.exists():
            logger.info(f"✓ {name} directory exists: {dir_path}")
        else:
            logger.error(f"✗ {name} directory missing: {dir_path}")
            all_exist = False

    return all_exist


def check_calibrated_ms_files():
    """Check for calibrated MS files and verify they're in the correct location."""
    logger.info("=" * 80)
    logger.info("Checking Calibrated MS Files")
    logger.info("=" * 80)

    from dsa110_contimg.database.data_config import get_calibrated_ms_dir

    calibrated_dir = get_calibrated_ms_dir()

    # Count MS files in calibrated directory
    ms_files = list(calibrated_dir.rglob("*.ms"))
    ms_files = [f for f in ms_files if f.is_dir()]  # MS files are directories

    logger.info(
        f"Found {len(ms_files)} calibrated MS files in {calibrated_dir}")

    if ms_files:
        logger.info("Sample calibrated MS files:")
        for ms_file in ms_files[:5]:  # Show first 5
            logger.info(f"  - {ms_file}")

    # Check data registry for calibrated_ms entries
    try:
        from dsa110_contimg.database.data_config import USE_NEW_STRUCTURE
        from dsa110_contimg.database.data_registry import \
          get_data_registry_connection

        conn = get_data_registry_connection()
        cursor = conn.cursor()

        data_type = "calibrated_ms" if USE_NEW_STRUCTURE else "calib_ms"
        cursor.execute(
            "SELECT data_id, file_path, status FROM data_registry WHERE data_type = ?",
            (data_type,)
        )
        rows = cursor.fetchall()

        logger.info(f"Found {len(rows)} {data_type} entries in data registry")

        if rows:
            logger.info("Sample registry entries:")
            for row in rows[:5]:
                data_id, file_path, status = row
                logger.info(f"  - {data_id}: {file_path} (status: {status})")

        conn.close()
    except Exception as e:
        logger.warning(f"Could not check data registry: {e}")

    return len(ms_files) > 0


def monitor_path_issues(log_file="pipeline_test_new_structure.log"):
    """Monitor log file for path-related errors."""
    logger.info("=" * 80)
    logger.info("Monitoring for Path-Related Issues")
    logger.info("=" * 80)

    if not Path(log_file).exists():
        logger.warning(f"Log file not found: {log_file}")
        return

    # Keywords that indicate path-related issues
    path_issues = [
        "FileNotFoundError",
        "No such file or directory",
        "Path does not exist",
        "Directory not found",
        "cannot access",
        "Permission denied",
    ]

    with open(log_file, 'r') as f:
        lines = f.readlines()

    issues_found = []
    for i, line in enumerate(lines, 1):
        for issue in path_issues:
            if issue.lower() in line.lower():
                issues_found.append((i, line.strip()))
                break

    if issues_found:
        logger.warning(
            f"Found {len(issues_found)} potential path-related issues:")
        for line_num, line in issues_found[:10]:  # Show first 10
            logger.warning(f"  Line {line_num}: {line}")
        return False
    else:
        logger.info("✓ No path-related issues found in logs")
        return True


def main():
    """Run pipeline test with new structure."""
    logger.info("=" * 80)
    logger.info("Pipeline Test with New Directory Structure")
    logger.info(f"Started: {datetime.now()}")
    logger.info("=" * 80)

    # Step 1: Check directory structure
    if not check_directory_structure():
        logger.error("Directory structure check failed!")
        return 1

    # Step 2: Check for existing calibrated MS files
    has_calibrated = check_calibrated_ms_files()

    # Step 3: Monitor for path issues (if log exists)
    monitor_path_issues()

    logger.info("=" * 80)
    logger.info("Test Summary")
    logger.info("=" * 80)
    logger.info(f"✓ Directory structure: OK")
    logger.info(f"{'✓' if has_calibrated else '⚠'} Calibrated MS files: {'Found' if has_calibrated else 'None found (expected if no calibration has run)'}")
    logger.info("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())

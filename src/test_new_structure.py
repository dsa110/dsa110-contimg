#!/opt/miniforge/envs/casa6/bin/python
"""Test that the new structure is enabled and working correctly."""

import os
import sys
from pathlib import Path

from dsa110_contimg.database.data_config import (DATA_BASE, STAGE_BASE,
                                                 USE_NEW_STRUCTURE,
                                                 get_calibrated_ms_dir,
                                                 get_calibration_tables_dir,
                                                 get_products_dir,
                                                 get_raw_ms_dir,
                                                 get_workspace_dir)

# Set environment variable
os.environ["CONTIMG_USE_NEW_STRUCTURE"] = "1"

sys.path.insert(0, str(Path(__file__).parent))


def test_new_structure():
    """Test that new structure is enabled."""
    print("=" * 80)
    print("Testing New Directory Structure")
    print("=" * 80)
    print()

    print(f"USE_NEW_STRUCTURE: {USE_NEW_STRUCTURE}")
    print()

    if not USE_NEW_STRUCTURE:
        print("✗ New structure is NOT enabled!")
        print("  Set CONTIMG_USE_NEW_STRUCTURE=1 to enable")
        return 1

    print("✓ New structure is ENABLED")
    print()

    print("Directory Paths:")
    print(f"  Raw MS dir: {get_raw_ms_dir()}")
    print(f"  Calibrated MS dir: {get_calibrated_ms_dir()}")
    print(f"  Calibration tables dir: {get_calibration_tables_dir()}")
    print(f"  Workspace dir: {get_workspace_dir()}")
    print(f"  Products dir: {get_products_dir()}")
    print()

    # Verify paths use new structure
    expected_raw = STAGE_BASE / "raw" / "ms"
    expected_cal = STAGE_BASE / "calibrated" / "ms"

    if get_raw_ms_dir() == expected_raw:
        print("✓ Raw MS directory uses new structure")
    else:
        print(
            f"✗ Raw MS directory incorrect: {get_raw_ms_dir()} (expected {expected_raw})")
        return 1

    if get_calibrated_ms_dir() == expected_cal:
        print("✓ Calibrated MS directory uses new structure")
    else:
        print(
            f"✗ Calibrated MS directory incorrect: {get_calibrated_ms_dir()} (expected {expected_cal})")
        return 1

    print()
    print("=" * 80)
    print("✓ All tests passed! New structure is enabled and working.")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(test_new_structure())

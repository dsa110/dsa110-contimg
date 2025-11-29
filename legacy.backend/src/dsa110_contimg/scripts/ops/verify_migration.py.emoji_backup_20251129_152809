#!/opt/miniforge/envs/casa6/bin/python
"""Verify the migration and new structure are correct."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dsa110_contimg.database.data_config import (
    DATA_BASE,
    STAGE_BASE,
    get_calibrated_ms_dir,
    get_calibration_tables_dir,
    get_products_dir,
    get_raw_ms_dir,
    get_workspace_dir,
)


def verify_structure():
    """Verify the new directory structure."""
    print("=" * 80)
    print("Verifying New Directory Structure")
    print("=" * 80)
    print()

    checks = []

    # Check base directories
    print("Base Directories:")
    print(f"  Stage base: {STAGE_BASE} - {'✓' if STAGE_BASE.exists() else '✗'}")
    print(f"  Data base: {DATA_BASE} - {'✓' if DATA_BASE.exists() else '✗'}")
    checks.append(STAGE_BASE.exists())
    checks.append(DATA_BASE.exists())
    print()

    # Check raw MS directories
    print("Raw MS Directories:")
    raw_ms_dir = get_raw_ms_dir()
    raw_science = raw_ms_dir / "science"
    raw_calibrators = raw_ms_dir / "calibrators"
    print(f"  {raw_ms_dir} - {'✓' if raw_ms_dir.exists() else '✗'}")
    print(f"  {raw_science} - {'✓' if raw_science.exists() else '✗'}")
    print(f"  {raw_calibrators} - {'✓' if raw_calibrators.exists() else '✗'}")
    checks.append(raw_ms_dir.exists())
    checks.append(raw_science.exists())
    checks.append(raw_calibrators.exists())

    # Count MS files
    ms_count = len(list(raw_science.rglob("*.ms"))) if raw_science.exists() else 0
    print(f"  MS files in raw/science: {ms_count}")
    print()

    # Check calibrated MS directories
    print("Calibrated MS Directories:")
    calibrated_ms_dir = get_calibrated_ms_dir()
    cal_science = calibrated_ms_dir / "science"
    cal_calibrators = calibrated_ms_dir / "calibrators"
    print(f"  {calibrated_ms_dir} - {'✓' if calibrated_ms_dir.exists() else '✗'}")
    print(f"  {cal_science} - {'✓' if cal_science.exists() else '✗'}")
    print(f"  {cal_calibrators} - {'✓' if cal_calibrators.exists() else '✗'}")
    checks.append(calibrated_ms_dir.exists())
    checks.append(cal_science.exists())
    checks.append(cal_calibrators.exists())
    print()

    # Check calibration tables
    print("Calibration Tables Directory:")
    cal_tables_dir = get_calibration_tables_dir()
    print(f"  {cal_tables_dir} - {'✓' if cal_tables_dir.exists() else '✗'}")
    checks.append(cal_tables_dir.exists())
    print()

    # Check workspace
    print("Workspace Directories:")
    workspace_dir = get_workspace_dir()
    workspace_active = workspace_dir / "active"
    workspace_failed = workspace_dir / "failed"
    print(f"  {workspace_dir} - {'✓' if workspace_dir.exists() else '✗'}")
    print(f"  {workspace_active} - {'✓' if workspace_active.exists() else '✗'}")
    print(f"  {workspace_failed} - {'✓' if workspace_failed.exists() else '✗'}")
    checks.append(workspace_dir.exists())
    checks.append(workspace_active.exists())
    checks.append(workspace_failed.exists())
    print()

    # Check products
    print("Products Directory:")
    products_dir = get_products_dir()
    print(f"  {products_dir} - {'✓' if products_dir.exists() else '✗'}")
    checks.append(products_dir.exists())
    print()

    # Check published products
    print("Published Products Directory:")
    published_dir = DATA_BASE / "products"
    print(f"  {published_dir} - {'✓' if published_dir.exists() else '✗'}")
    checks.append(published_dir.exists())
    print()

    # Summary
    print("=" * 80)
    passed = sum(checks)
    total = len(checks)
    print(f"Verification: {passed}/{total} checks passed")

    if passed == total:
        print("✓ All checks passed! Structure is correct.")
        return 0
    else:
        print("✗ Some checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(verify_structure())

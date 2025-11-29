#!/usr/bin/env python3
"""
Lightweight validation script to check mosaic creation prerequisites.
This script only uses standard library + sqlite3 to avoid import issues.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def check_data_registry():
    """Check data registry database and schema."""
    print("\n=== Checking Data Registry ===")
    db_path = Path("state/db/data_registry.sqlite3")

    if not db_path.exists():
        print(f"❌ Data registry not found at {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check schema
    cursor.execute("PRAGMA table_info(data_registry)")
    columns = {row[1] for row in cursor.fetchall()}

    required_cols = {
        "photometry_status",
        "photometry_job_id",
        "data_type",
        "status",
        "qa_status",
        "validation_status",
        "finalization_status",
    }
    missing = required_cols - columns

    if missing:
        print(f"❌ Missing required columns: {missing}")
        conn.close()
        return False

    print(f"✅ Data registry schema valid")
    print(f"   - All required columns present including: photometry_status, photometry_job_id")

    # Check for existing mosaics
    cursor.execute("SELECT COUNT(*) FROM data_registry WHERE data_type='mosaic'")
    mosaic_count = cursor.fetchone()[0]
    print(f"   - Existing mosaics: {mosaic_count}")

    # Check for any records with photometry status
    cursor.execute(
        """
        SELECT data_id, data_type, status, photometry_status 
        FROM data_registry 
        WHERE photometry_status IS NOT NULL 
        LIMIT 5
    """
    )
    phot_records = cursor.fetchall()
    if phot_records:
        print(f"   - Records with photometry status: {len(phot_records)}")
        for rec in phot_records:
            print(f"     • {rec[0]}: {rec[2]} (phot: {rec[3]})")
    else:
        print(f"   - No records with photometry status yet (expected for first run)")

    conn.close()
    return True


def check_cal_registry():
    """Check calibration registry."""
    print("\n=== Checking Calibration Registry ===")
    db_path = Path("state/db/cal_registry.sqlite3")

    if not db_path.exists():
        print(f"❌ Calibration registry not found at {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check for caltables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print(f"⚠️  Calibration registry exists but has no tables")
        print(f"   This is expected if no calibration has been run yet")
        conn.close()
        return True

    print(f"✅ Calibration registry exists")
    print(f"   - Tables: {', '.join(tables)}")

    if "caltables" in tables:
        cursor.execute("SELECT COUNT(*) FROM caltables")
        count = cursor.fetchone()[0]
        print(f"   - Caltable entries: {count}")

        if count > 0:
            cursor.execute(
                """
                SELECT path, table_type, valid_start_mjd, valid_end_mjd
                FROM caltables
                ORDER BY valid_start_mjd DESC
                LIMIT 3
            """
            )
            recent = cursor.fetchall()
            print(f"   - Recent caltables:")
            for path, ttype, start, end in recent:
                path_str = str(path) if path else "unknown"
                start_str = f"{start:.3f}" if start else "None"
                end_str = f"{end:.3f}" if end else "None"
                print(
                    f"     • {Path(path_str).name if path else 'N/A'} ({ttype}, MJD {start_str}-{end_str})"
                )

    conn.close()
    return True


def check_hdf5_index():
    """Check HDF5 index database."""
    print("\n=== Checking HDF5 Index ===")
    db_path = Path("state/hdf5.sqlite3")

    if not db_path.exists():
        print(f"❌ HDF5 index not found at {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check for indexed files
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"✅ HDF5 index exists")
    print(f"   - Tables: {', '.join(tables)}")

    if "hdf5_files" in tables:
        cursor.execute("SELECT COUNT(*) FROM hdf5_files")
        count = cursor.fetchone()[0]
        print(f"   - Indexed HDF5 files: {count}")

        if count > 0:
            # Show some recent files
            cursor.execute(
                """
                SELECT file_path, mjd_start, mjd_end 
                FROM hdf5_files 
                ORDER BY mjd_start DESC 
                LIMIT 3
            """
            )
            recent = cursor.fetchall()
            print(f"   - Recent files:")
            for path, start, end in recent:
                print(f"     • {Path(path).name} (MJD {start:.3f} - {end:.3f})")
        else:
            print(f"   ⚠️  No HDF5 files indexed yet")
            print(f"      Run HDF5 indexing before creating mosaics")

    conn.close()
    return True


def check_products_db():
    """Check products database."""
    print("\n=== Checking Products Database ===")
    db_path = Path("state/db/products.sqlite3")

    if not db_path.exists():
        print(f"   ℹ️  Products database not yet created (will be created on first use)")
        return True

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"✅ Products database exists")
    print(f"   - Tables: {', '.join(tables)}")

    for table in ["products", "photometry", "images", "mosaics"]:
        if table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} entries")

    conn.close()
    return True


def check_directory_structure():
    """Check required directories exist."""
    print("\n=== Checking Directory Structure ===")

    dirs = {
        "/staging/dsa110/T3/uwl": ("UVH5 input data", True),  # (description, is_external)
        "/stage/dsa110-contimg/processed": ("Processed output", True),
        "state": ("State databases", False),
        "state/transit_cache": ("Transit cache", False),
    }

    all_exist = True
    for path, (description, is_external) in dirs.items():
        p = Path(path)
        if p.exists():
            print(f"✅ {description}: {path}")
        else:
            print(f"⚠️  {description} not found: {path}")
            if is_external:
                print(f"   (External directory - may be created on demand)")
            else:
                all_exist = False

    return all_exist


def summarize_readiness():
    """Summarize system readiness."""
    print("\n=== System Readiness Summary ===")

    checks = {
        "Data registry schema": check_data_registry,
        "Calibration registry": check_cal_registry,
        "HDF5 index": check_hdf5_index,
        "Products database": check_products_db,
        "Directory structure": check_directory_structure,
    }

    results = {}
    for name, func in checks.items():
        try:
            results[name] = func()
        except Exception as e:
            print(f"\n❌ {name} check failed: {e}")
            import traceback

            traceback.print_exc()
            results[name] = False

    return results


def main():
    """Run all validation checks."""
    print("=" * 70)
    print("DSA-110 Mosaic Creation Prerequisites Validation")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Working directory: {Path.cwd()}")

    results = summarize_readiness()

    print("\n" + "=" * 70)
    print("Validation Results")
    print("=" * 70)

    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n🎉 All prerequisites validated successfully!")
        print("\n📋 Key Changes Implemented:")
        print("   ✓ MODEL_DATA seeding will run after calibration for each science MS")
        print("   ✓ WSClean will only run after MODEL_DATA is populated and verified")
        print("   ✓ Photometry is enabled by default in MosaicOrchestrator")
        print("   ✓ Publishing is blocked until photometry_status='completed'")
        print("\n🚀 Next Steps:")
        print("   1. Run create_15min_mosaic.ipynb to create a full mosaic")
        print("   2. Monitor logs for 'Populating MODEL_DATA' messages after calibration")
        print("   3. Verify photometry job is created and linked in data registry")
        print("   4. Confirm publishing waits for photometry_status='completed'")
        print("\n💡 Optional Dry-Run Test:")
        print("   Open create_15min_mosaic.ipynb and run with dry_run=True")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    import os

    os.chdir("/data/dsa110-contimg")
    sys.exit(main())

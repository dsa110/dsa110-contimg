#!/usr/bin/env python3
"""Verify migration from hdf5_file_index.sqlite3 to pipeline.sqlite3."""

import sqlite3
from pathlib import Path

def verify_migration():
    """Run post-migration verification checks."""

    print("="*60)
    print("Post-Migration Verification")
    print("="*60)

    unified_db = Path('/data/dsa110-contimg/state/db/pipeline.sqlite3')
    conn = sqlite3.connect(unified_db)
    conn.row_factory = sqlite3.Row

    # 1. Check hdf5_files table exists
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hdf5_files'").fetchall()
    if not tables:
        print("✗ FAIL: hdf5_files table not found")
        return False
    print("✓ hdf5_files table exists")

    # 2. Check record count
    count = conn.execute("SELECT COUNT(*) FROM hdf5_files").fetchone()[0]
    print(f"✓ hdf5_files has {count:,} records")

    if count == 0:
        print("⚠ WARNING: hdf5_files table is empty")
        return False

    # 3. Check schema
    schema = conn.execute("PRAGMA table_info(hdf5_files)").fetchall()
    expected_columns = {
        'path', 'filename', 'group_id', 'subband_code', 'subband_num',
        'timestamp_iso', 'timestamp_mjd', 'file_size_bytes', 'stored',
        'ra_deg', 'dec_deg'
    }
    actual_columns = {col[1] for col in schema}

    missing = expected_columns - actual_columns
    if missing:
        print(f"⚠ WARNING: Missing columns: {missing}")
    else:
        print("✓ All expected columns present")

    # 4. Check data quality
    sample = conn.execute("SELECT * FROM hdf5_files LIMIT 5").fetchall()
    print(f"\n✓ Sample records ({len(sample)}):")
    for i, row in enumerate(sample, 1):
        print(f"  {i}. {row['filename']}")
        print(f"     Group: {row['group_id']}, Subband: {row['subband_num']}, MJD: {row['timestamp_mjd']}")

    # 5. Check for complete observation groups
    groups = conn.execute(
        """
        SELECT group_id, COUNT(*) as n_files, COUNT(DISTINCT subband_num) as n_subbands
        FROM hdf5_files
        WHERE subband_num IS NOT NULL
        GROUP BY group_id
        HAVING COUNT(DISTINCT subband_num) = 16
        LIMIT 10
        """,
    ).fetchall()

    print(f"\n✓ Complete 16-subband groups: {len(groups)}")
    if groups:
        for g in groups[:3]:
            print(f"  - {g['group_id']}: {g['n_files']} files, {g['n_subbands']} subbands")

    # 6. Check storage status
    stored_count = conn.execute("SELECT COUNT(*) FROM hdf5_files WHERE stored = 1").fetchone()[0]
    not_stored_count = conn.execute("SELECT COUNT(*) FROM hdf5_files WHERE stored = 0").fetchone()[0]
    print(f"\n✓ Storage status:")
    print(f"  - Stored (present on disk): {stored_count:,}")
    print(f"  - Not stored (missing): {not_stored_count:,}")

    # 7. Check legacy database status
    legacy_path = Path('/data/incoming/hdf5_file_index.sqlite3')
    if legacy_path.exists():
        print(f"\n⚠ Legacy database still exists: {legacy_path}")
        print("  Consider removing after confirming migration success")
    else:
        print("\n✓ Legacy database removed")

    # 8. Check backup exists
    backup_files = list(Path('/data/incoming/').glob('hdf5_file_index_backup_*.sqlite3'))
    if backup_files:
        print(f"\n✓ Backup files found: {len(backup_files)}")
        for backup in backup_files:
            print(f"  - {backup.name} ({backup.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print("\n⚠ WARNING: No backup files found")

    conn.close()

    print("\n" + "="*60)
    print("Verification Complete!")
    print("="*60)

    return True

if __name__ == '__main__':
    verify_migration()

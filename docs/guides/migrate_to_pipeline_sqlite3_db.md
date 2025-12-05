## **Migrating from `hdf5_file_index.sqlite3` to Unified `pipeline.sqlite3`**

---

## **Migration Strategy Overview**

The codebase has already defined the unified schema with `hdf5_files` table in `pipeline.sqlite3`. Here's how to complete the migration:

---

## **Step 1: Check Current State**

### **Identify What Databases Exist**

```bash
# Check for existing databases
ls -lh /data/dsa110-contimg/state/db/

# Expected files:
# - pipeline.sqlite3 (unified, target)
# - hdf5_file_index.sqlite3 (legacy, to migrate FROM)
# - calibrators.sqlite3 (may also exist, legacy)
# - products.sqlite3 (may also exist, legacy)
```

### **Verify Schema Status**

```python
from dsa110_contimg.database.unified import Database, get_pipeline_db_path
import sqlite3
from pathlib import Path

# Check unified database
unified_db = Database()
tables = unified_db.query("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables in pipeline.sqlite3:")
for t in tables:
    print(f"  - {t['name']}")

# Check if hdf5_files table exists
hdf5_table_exists = any(t['name'] == 'hdf5_files' for t in tables)
print(f"\nhdf5_files table exists: {hdf5_table_exists}")

# Check if legacy database exists
legacy_hdf5_db = Path('/data/dsa110-contimg/state/db/hdf5_file_index.sqlite3')
legacy_exists = legacy_hdf5_db.exists()
print(f"Legacy hdf5_file_index.sqlite3 exists: {legacy_exists}")

if legacy_exists:
    # Check how many records in legacy
    legacy_conn = sqlite3.connect(legacy_hdf5_db)
    cursor = legacy_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    legacy_tables = [row[0] for row in cursor.fetchall()]
    print(f"\nLegacy database tables: {legacy_tables}")

    for table in legacy_tables:
        count = legacy_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count:,} records")

    legacy_conn.close()
```

---

## **Step 2: Migration Script**

### **Complete Migration Script**

```python
#!/usr/bin/env python3
"""
Migrate hdf5_file_index.sqlite3 to unified pipeline.sqlite3.

This script:
1. Reads data from legacy hdf5_file_index.sqlite3
2. Transforms schema to match unified pipeline.sqlite3
3. Inserts data into pipeline.sqlite3::hdf5_files table
4. Validates migration
5. Optionally backs up and removes legacy database
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional
import shutil
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HDF5DatabaseMigrator:
    """Migrate HDF5 file index from legacy to unified database."""

    def __init__(
        self,
        legacy_db_path: str = '/data/dsa110-contimg/state/db/hdf5_file_index.sqlite3',
        unified_db_path: str = '/data/dsa110-contimg/state/db/pipeline.sqlite3'
    ):
        self.legacy_db_path = Path(legacy_db_path)
        self.unified_db_path = Path(unified_db_path)

        if not self.legacy_db_path.exists():
            raise FileNotFoundError(f"Legacy database not found: {self.legacy_db_path}")

        if not self.unified_db_path.exists():
            raise FileNotFoundError(f"Unified database not found: {self.unified_db_path}")

    def analyze_legacy_schema(self) -> Dict[str, List[str]]:
        """Analyze legacy database schema."""
        conn = sqlite3.connect(self.legacy_db_path)
        cursor = conn.cursor()

        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            schema[table] = columns

        conn.close()
        return schema

    def map_legacy_to_unified(self, legacy_row: Dict, legacy_table: str) -> Dict:
        """
        Map legacy schema fields to unified schema.

        Legacy schema (hdf5_file_index.sqlite3):
          - Various possible schemas depending on version

        Unified schema (pipeline.sqlite3::hdf5_files):
          path, filename, group_id, subband_code, subband_num,
          timestamp_iso, timestamp_mjd, file_size_bytes, modified_time,
          indexed_at, stored, ra_deg, dec_deg, obs_date, obs_time
        """
        import time

        unified_row = {}

        # Required fields
        unified_row['path'] = legacy_row.get('path') or legacy_row.get('file_path')
        unified_row['filename'] = Path(unified_row['path']).name if unified_row['path'] else None

        # Group/observation ID
        unified_row['group_id'] = (
            legacy_row.get('group_id') or
            legacy_row.get('observation_id') or
            legacy_row.get('obs_id') or
            'unknown'
        )

        # Subband information
        subband = legacy_row.get('subband') or legacy_row.get('subband_num')
        if isinstance(subband, int):
            unified_row['subband_num'] = subband
            unified_row['subband_code'] = f'sb{subband:02d}'
        elif isinstance(subband, str):
            # Extract number from 'sb00', 'sb01', etc.
            if subband.startswith('sb'):
                unified_row['subband_num'] = int(subband[2:])
                unified_row['subband_code'] = subband
            else:
                unified_row['subband_num'] = None
                unified_row['subband_code'] = subband
        else:
            unified_row['subband_num'] = None
            unified_row['subband_code'] = None

        # Timestamp fields
        unified_row['timestamp_mjd'] = (
            legacy_row.get('timestamp_mjd') or
            legacy_row.get('start_mjd') or
            legacy_row.get('mjd')
        )

        unified_row['timestamp_iso'] = (
            legacy_row.get('timestamp_iso') or
            legacy_row.get('datetime_iso') or
            legacy_row.get('obs_time')
        )

        # File metadata
        unified_row['file_size_bytes'] = (
            legacy_row.get('file_size_bytes') or
            legacy_row.get('file_size') or
            legacy_row.get('size')
        )

        unified_row['modified_time'] = (
            legacy_row.get('modified_time') or
            legacy_row.get('mtime')
        )

        # Status/stored
        status = legacy_row.get('status', 'available')
        unified_row['stored'] = 1 if status in ('available', 'present', 'active') else 0

        # Coordinates
        unified_row['ra_deg'] = legacy_row.get('ra_deg') or legacy_row.get('ra')
        unified_row['dec_deg'] = legacy_row.get('dec_deg') or legacy_row.get('dec')

        # Observation date/time
        unified_row['obs_date'] = legacy_row.get('obs_date')
        unified_row['obs_time'] = legacy_row.get('obs_time')

        # Indexed timestamp
        unified_row['indexed_at'] = legacy_row.get('indexed_at') or time.time()

        return unified_row

    def migrate_table(self, legacy_table: str, batch_size: int = 1000) -> int:
        """
        Migrate a table from legacy to unified database.

        Args:
            legacy_table: Name of table in legacy database
            batch_size: Number of records to insert at once

        Returns:
            Number of records migrated
        """
        logger.info(f"Migrating table: {legacy_table}")

        # Read from legacy
        legacy_conn = sqlite3.connect(self.legacy_db_path)
        legacy_conn.row_factory = sqlite3.Row

        unified_conn = sqlite3.connect(self.unified_db_path)

        # Get total count
        cursor = legacy_conn.execute(f"SELECT COUNT(*) FROM {legacy_table}")
        total_rows = cursor.fetchone()[0]
        logger.info(f"Total rows to migrate: {total_rows:,}")

        # Migrate in batches
        offset = 0
        migrated = 0
        skipped = 0

        while offset < total_rows:
            cursor = legacy_conn.execute(
                f"SELECT * FROM {legacy_table} LIMIT ? OFFSET ?",
                (batch_size, offset)
            )

            rows = cursor.fetchall()
            if not rows:
                break

            for legacy_row in rows:
                # Convert to dict
                legacy_dict = dict(legacy_row)

                # Map to unified schema
                try:
                    unified_dict = self.map_legacy_to_unified(legacy_dict, legacy_table)

                    # Insert into unified database
                    unified_conn.execute(
                        """
                        INSERT OR REPLACE INTO hdf5_files (
                            path, filename, group_id, subband_code, subband_num,
                            timestamp_iso, timestamp_mjd, file_size_bytes, modified_time,
                            indexed_at, stored, ra_deg, dec_deg, obs_date, obs_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            unified_dict['path'],
                            unified_dict['filename'],
                            unified_dict['group_id'],
                            unified_dict['subband_code'],
                            unified_dict['subband_num'],
                            unified_dict['timestamp_iso'],
                            unified_dict['timestamp_mjd'],
                            unified_dict['file_size_bytes'],
                            unified_dict['modified_time'],
                            unified_dict['indexed_at'],
                            unified_dict['stored'],
                            unified_dict['ra_deg'],
                            unified_dict['dec_deg'],
                            unified_dict['obs_date'],
                            unified_dict['obs_time']
                        )
                    )
                    migrated += 1

                except Exception as e:
                    logger.warning(f"Failed to migrate row: {e}")
                    logger.debug(f"Legacy row: {legacy_dict}")
                    skipped += 1

            unified_conn.commit()
            offset += batch_size

            if offset % 10000 == 0:
                logger.info(f"Progress: {offset:,}/{total_rows:,} ({100*offset/total_rows:.1f}%)")

        legacy_conn.close()
        unified_conn.close()

        logger.info(f"Migration complete: {migrated:,} migrated, {skipped:,} skipped")
        return migrated

    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        logger.info("Validating migration...")

        legacy_conn = sqlite3.connect(self.legacy_db_path)
        unified_conn = sqlite3.connect(self.unified_db_path)

        # Get counts from both databases
        legacy_tables = legacy_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

        for table_name, in legacy_tables:
            legacy_count = legacy_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            unified_count = unified_conn.execute("SELECT COUNT(*) FROM hdf5_files").fetchone()[0]

            logger.info(f"Legacy {table_name}: {legacy_count:,} records")
            logger.info(f"Unified hdf5_files: {unified_count:,} records")

            if unified_count >= legacy_count:
                logger.info("✓ Validation passed: unified has at least as many records")
            else:
                logger.warning(f"⚠ Validation issue: unified has fewer records ({unified_count} < {legacy_count})")
                return False

        # Sample check: verify some records migrated correctly
        legacy_sample = legacy_conn.execute(
            f"SELECT * FROM {legacy_tables[0][0]} LIMIT 5"
        ).fetchall()

        for legacy_row in legacy_sample:
            path = legacy_row[0]  # Assuming path is first column
            unified_row = unified_conn.execute(
                "SELECT * FROM hdf5_files WHERE path = ?", (path,)
            ).fetchone()

            if unified_row is None:
                logger.warning(f"⚠ Sample record not found in unified: {path}")
                return False

        logger.info("✓ Sample records verified")

        legacy_conn.close()
        unified_conn.close()

        return True

    def backup_legacy_database(self):
        """Create backup of legacy database before removal."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.legacy_db_path.parent / f'hdf5_file_index_backup_{timestamp}.sqlite3'

        logger.info(f"Creating backup: {backup_path}")
        shutil.copy2(self.legacy_db_path, backup_path)
        logger.info(f"✓ Backup created: {backup_path}")

        return backup_path

    def run_migration(self, backup: bool = True, remove_legacy: bool = False):
        """
        Execute complete migration.

        Args:
            backup: Create backup of legacy database (default: True)
            remove_legacy: Remove legacy database after successful migration (default: False)
        """
        logger.info("="*60)
        logger.info("HDF5 Database Migration")
        logger.info("="*60)
        logger.info(f"Legacy: {self.legacy_db_path}")
        logger.info(f"Unified: {self.unified_db_path}")

        # Analyze legacy schema
        logger.info("\n1. Analyzing legacy schema...")
        schema = self.analyze_legacy_schema()
        for table, columns in schema.items():
            logger.info(f"  Table: {table}")
            logger.info(f"    Columns: {', '.join(columns)}")

        # Migrate each table
        logger.info("\n2. Migrating data...")
        total_migrated = 0
        for table in schema.keys():
            migrated = self.migrate_table(table)
            total_migrated += migrated

        # Validate
        logger.info("\n3. Validating migration...")
        validation_passed = self.validate_migration()

        if not validation_passed:
            logger.error("✗ Validation failed - migration incomplete")
            return False

        logger.info(f"\n✓ Migration successful: {total_migrated:,} records migrated")

        # Backup
        if backup:
            logger.info("\n4. Creating backup...")
            backup_path = self.backup_legacy_database()

        # Remove legacy
        if remove_legacy:
            logger.info("\n5. Removing legacy database...")
            response = input(f"Are you sure you want to delete {self.legacy_db_path}? (yes/no): ")
            if response.lower() == 'yes':
                self.legacy_db_path.unlink()
                logger.info(f"✓ Legacy database removed")
            else:
                logger.info("Legacy database kept")

        logger.info("\n" + "="*60)
        logger.info("Migration Complete!")
        logger.info("="*60)

        return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate HDF5 file index to unified database')
    parser.add_argument('--legacy-db', default='/data/dsa110-contimg/state/db/hdf5_file_index.sqlite3',
                        help='Path to legacy hdf5_file_index.sqlite3')
    parser.add_argument('--unified-db', default='/data/dsa110-contimg/state/db/pipeline.sqlite3',
                        help='Path to unified pipeline.sqlite3')
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip creating backup of legacy database')
    parser.add_argument('--remove-legacy', action='store_true',
                        help='Remove legacy database after successful migration')
    parser.add_argument('--dry-run', action='store_true',
                        help='Analyze schema only, do not migrate')

    args = parser.parse_args()

    migrator = HDF5DatabaseMigrator(args.legacy_db, args.unified_db)

    if args.dry_run:
        logger.info("DRY RUN MODE - analyzing only")
        schema = migrator.analyze_legacy_schema()
        for table, columns in schema.items():
            print(f"\nTable: {table}")
            print(f"Columns: {', '.join(columns)}")
    else:
        success = migrator.run_migration(
            backup=not args.no_backup,
            remove_legacy=args.remove_legacy
        )

        exit(0 if success else 1)
```

---

## **Step 3: Run Migration**

### **Dry Run First (Recommended)**

```bash
# Analyze schema without migrating
python migrate_hdf5_to_unified.py --dry-run
```

### **Full Migration with Backup**

```bash
# Migrate with automatic backup (safe)
python migrate_hdf5_to_unified.py

# Or with custom paths
python migrate_hdf5_to_unified.py \
  --legacy-db /path/to/hdf5_file_index.sqlite3 \
  --unified-db /path/to/pipeline.sqlite3
```

### **Migration + Remove Legacy**

```bash
# Migrate, backup, and remove legacy (after confirming success)
python migrate_hdf5_to_unified.py --remove-legacy
```

---

## **Step 4: Update Code References**

### **Find Code Using Legacy Database**

```bash
# Search for references to hdf5_file_index.sqlite3
cd /path/to/dsa110-contimg
grep -r "hdf5_file_index" --include="*.py" backend/

# Search for HDF5_INDEX_DB environment variable
grep -r "HDF5_INDEX_DB" --include="*.py" backend/
```

### **Update Code to Use Unified Database**

**Before (Legacy)**:

```python
# OLD CODE - uses separate database
import os
HDF5_INDEX_DB = os.environ.get('HDF5_INDEX_DB', '/data/.../hdf5_file_index.sqlite3')
hdf5_conn = sqlite3.connect(HDF5_INDEX_DB)
```

**After (Unified)**:

```python
# NEW CODE - uses unified database
from dsa110_contimg.database.unified import Database

db = Database()  # Uses PIPELINE_DB automatically
files = db.query("SELECT * FROM hdf5_files WHERE timestamp_mjd BETWEEN ? AND ?", (start, end))
```

---

## **Step 5: Update Environment Variables**

### **Remove Legacy Environment Variables**

```bash
# Edit ~/.bashrc or system config
# REMOVE these lines:
# export HDF5_INDEX_DB=/data/dsa110-contimg/state/db/hdf5_file_index.sqlite3

# KEEP this (unified database):
export PIPELINE_DB=/data/dsa110-contimg/state/db/pipeline.sqlite3

# Reload
source ~/.bashrc
```

---

## **Step 6: Verify Migration Success**

### **Post-Migration Validation Script**

```python
#!/usr/bin/env python3
"""Verify migration from hdf5_file_index.sqlite3 to pipeline.sqlite3."""

from dsa110_contimg.database.unified import Database
from pathlib import Path

def verify_migration():
    """Run post-migration verification checks."""

    print("="*60)
    print("Post-Migration Verification")
    print("="*60)

    db = Database()

    # 1. Check hdf5_files table exists
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='hdf5_files'")
    if not tables:
        print("✗ FAIL: hdf5_files table not found")
        return False
    print("✓ hdf5_files table exists")

    # 2. Check record count
    count = db.query_val("SELECT COUNT(*) FROM hdf5_files")
    print(f"✓ hdf5_files has {count:,} records")

    if count == 0:
        print("⚠ WARNING: hdf5_files table is empty")

    # 3. Check schema
    schema = db.query("PRAGMA table_info(hdf5_files)")
    expected_columns = {
        'path', 'filename', 'group_id', 'subband_code', 'subband_num',
        'timestamp_iso', 'timestamp_mjd', 'file_size_bytes', 'stored',
        'ra_deg', 'dec_deg'
    }
    actual_columns = {col['name'] for col in schema}

    missing = expected_columns - actual_columns
    if missing:
        print(f"⚠ WARNING: Missing columns: {missing}")
    else:
        print("✓ All expected columns present")

    # 4. Check data quality
    sample = db.query("SELECT * FROM hdf5_files LIMIT 5")
    print(f"\n✓ Sample records ({len(sample)}):")
    for i, row in enumerate(sample, 1):
        print(f"  {i}. {row['filename']}")
        print(f"     Group: {row['group_id']}, Subband: {row['subband_num']}, MJD: {row['timestamp_mjd']}")

    # 5. Check for complete observation groups
    groups = db.query(
        """
        SELECT group_id, COUNT(*) as n_files, COUNT(DISTINCT subband_num) as n_subbands
        FROM hdf5_files
        WHERE subband_num IS NOT NULL
        GROUP BY group_id
        HAVING COUNT(DISTINCT subband_num) = 16
        LIMIT 10
        """,
        ()
    )

    print(f"\n✓ Complete 16-subband groups: {len(groups)}")
    if groups:
        for g in groups[:3]:
            print(f"  - {g['group_id']}: {g['n_files']} files, {g['n_subbands']} subbands")

    # 6. Check legacy database status
    legacy_path = Path('/data/dsa110-contimg/state/db/hdf5_file_index.sqlite3')
    if legacy_path.exists():
        print(f"\n⚠ Legacy database still exists: {legacy_path}")
        print("  Consider removing after confirming migration success")
    else:
        print("\n✓ Legacy database removed")

    print("\n" + "="*60)
    print("Verification Complete!")
    print("="*60)

    return True

if __name__ == '__main__':
    verify_migration()
```

**Run verification**:

```bash
python verify_migration.py
```

---

## **Step 7: Update Documentation & Scripts**

### **Update README/Documentation**

```markdown
## Database Architecture

The pipeline uses a **unified database** (`pipeline.sqlite3`) containing all data:

- **HDF5 files**: `hdf5_files` table
- **Calibration**: `caltables` table
- **Products**: `ms_index`, `images`, `photometry` tables
- **Jobs**: `jobs`, `batch_jobs` tables

**Legacy databases** (`hdf5_file_index.sqlite3`, `calibrators.sqlite3`, `products.sqlite3`)
have been **consolidated** into `pipeline.sqlite3`.

### Environment Variables
```

# Unified database (required)

export PIPELINE_DB=/data/dsa110-contimg/state/db/pipeline.sqlite3

# Legacy variables (DEPRECATED - no longer needed)

# export HDF5_INDEX_DB=... # REMOVE THIS

```

```

---

## **Step 8: CI/CD & Deployment Updates**

### **Update Deployment Scripts**

```bash
# deploy.sh
#!/bin/bash

# Initialize unified database
python -c "from dsa110_contimg.database.unified import init_unified_db; init_unified_db()"

# Run migration if legacy database exists
if [ -f /data/dsa110-contimg/state/db/hdf5_file_index.sqlite3 ]; then
    echo "Legacy HDF5 database found - running migration..."
    python scripts/migrate_hdf5_to_unified.py
fi

# Start services
systemctl restart dsa110-pipeline
```

---

## **Migration Checklist**

```
□ 1. Verify unified schema exists in pipeline.sqlite3
□ 2. Backup legacy hdf5_file_index.sqlite3
□ 3. Run migration script (dry-run first)
□ 4. Validate migration (compare counts, sample records)
□ 5. Update code references (search for HDF5_INDEX_DB)
□ 6. Update environment variables (remove HDF5_INDEX_DB)
□ 7. Test queries against unified database
□ 8. Update documentation
□ 9. Deploy to production
□ 10. Monitor for 1 week
□ 11. Remove legacy database (after confirming success)
```

---

## **Rollback Plan**

If migration fails:

```bash
# 1. Stop pipeline
systemctl stop dsa110-pipeline

# 2. Restore from backup
cp hdf5_file_index_backup_20251205_*.sqlite3 hdf5_file_index.sqlite3

# 3. Revert code changes
git checkout HEAD -- backend/

# 4. Restore environment variables
export HDF5_INDEX_DB=/data/dsa110-contimg/state/db/hdf5_file_index.sqlite3

# 5. Restart pipeline
systemctl start dsa110-pipeline
```

---

## **Expected Timeline**

| Phase            | Duration  | Notes                                        |
| ---------------- | --------- | -------------------------------------------- |
| **Analysis**     | 30 min    | Run dry-run, analyze schema                  |
| **Migration**    | 1-4 hours | Depends on data volume (1M records ≈ 15 min) |
| **Validation**   | 30 min    | Run verification scripts                     |
| **Code updates** | 2-4 hours | Update all references                        |
| **Testing**      | 1-2 days  | Test all functionality                       |
| **Monitoring**   | 1 week    | Watch for issues in production               |
| **Cleanup**      | 30 min    | Remove legacy database                       |

**Total**: ~2 weeks for safe migration

---

## **Bottom Line**

**To migrate from `hdf5_file_index.sqlite3` to unified `pipeline.sqlite3`:**

1. **Run migration script** (provided above) - transfers data with schema transformation
2. **Update code** - replace legacy database references with unified `Database()` class
3. **Remove environment variable** - delete `HDF5_INDEX_DB` (keep `PIPELINE_DB`)
4. **Validate thoroughly** - verify counts, sample records, and complete observation groups
5. **Monitor for 1 week** - confirm no issues before removing legacy database

The schema mapping handles differences automatically (e.g., `observation_id` → `group_id`, `subband` → `subband_num`, `status` → `stored`).

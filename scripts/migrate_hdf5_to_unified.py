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
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HDF5DatabaseMigrator:
    """Migrate HDF5 file index from legacy to unified database."""

    def __init__(
        self,
        legacy_db_path: str = '/data/incoming/hdf5_file_index.sqlite3',
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
        tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']

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
          id, timestamp, timestamp_iso, subband, path, mid_mjd

        Unified schema (pipeline.sqlite3::hdf5_files):
          path, filename, group_id, subband_code, subband_num,
          timestamp_iso, timestamp_mjd, file_size_bytes, modified_time,
          indexed_at, stored, ra_deg, dec_deg, obs_date, obs_time
        """
        import time

        unified_row = {}

        # Required fields
        unified_row['path'] = legacy_row.get('path')
        unified_row['filename'] = Path(unified_row['path']).name if unified_row['path'] else None

        # Group/observation ID - extract from timestamp
        unified_row['group_id'] = legacy_row.get('timestamp', 'unknown')

        # Subband information
        subband = legacy_row.get('subband')
        if isinstance(subband, int):
            unified_row['subband_num'] = subband
            unified_row['subband_code'] = f'sb{subband:02d}'
        elif isinstance(subband, str):
            # Extract number from 'sb00', 'sb01', etc.
            if subband.startswith('sb'):
                try:
                    unified_row['subband_num'] = int(subband[2:])
                    unified_row['subband_code'] = subband
                except ValueError:
                    unified_row['subband_num'] = None
                    unified_row['subband_code'] = subband
            else:
                unified_row['subband_num'] = None
                unified_row['subband_code'] = subband
        else:
            unified_row['subband_num'] = None
            unified_row['subband_code'] = None

        # Timestamp fields
        unified_row['timestamp_mjd'] = legacy_row.get('mid_mjd')
        unified_row['timestamp_iso'] = legacy_row.get('timestamp_iso')

        # File metadata - try to get from filesystem if file exists
        file_path = Path(unified_row['path']) if unified_row['path'] else None
        if file_path and file_path.exists():
            stat = file_path.stat()
            unified_row['file_size_bytes'] = stat.st_size
            unified_row['modified_time'] = stat.st_mtime
            unified_row['stored'] = 1
        else:
            unified_row['file_size_bytes'] = None
            unified_row['modified_time'] = None
            unified_row['stored'] = 0

        # Coordinates - not available in legacy, set to None
        unified_row['ra_deg'] = None
        unified_row['dec_deg'] = None

        # Observation date/time - not available in legacy
        unified_row['obs_date'] = None
        unified_row['obs_time'] = None

        # Indexed timestamp
        unified_row['indexed_at'] = time.time()

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

            if offset % 10000 == 0 or offset >= total_rows:
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
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
        ).fetchall()

        total_legacy_count = 0
        for table_name, in legacy_tables:
            legacy_count = legacy_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            total_legacy_count += legacy_count
            logger.info(f"Legacy {table_name}: {legacy_count:,} records")

        unified_count = unified_conn.execute("SELECT COUNT(*) FROM hdf5_files").fetchone()[0]
        logger.info(f"Unified hdf5_files: {unified_count:,} records")

        if unified_count >= total_legacy_count:
            logger.info("✓ Validation passed: unified has at least as many records")
        else:
            logger.warning(f"⚠ Validation issue: unified has fewer records ({unified_count} < {total_legacy_count})")
            legacy_conn.close()
            unified_conn.close()
            return False

        # Sample check: verify some records migrated correctly
        if legacy_tables:
            legacy_sample = legacy_conn.execute(
                f"SELECT * FROM {legacy_tables[0][0]} LIMIT 5"
            ).fetchall()

            for legacy_row in legacy_sample:
                # Path is in 'path' column (index will vary, but we can get it by name)
                legacy_dict = dict(zip([col[0] for col in legacy_conn.execute(f"PRAGMA table_info({legacy_tables[0][0]})").fetchall()], 
                                      [legacy_row[i] for i in range(len(legacy_row))]))
                
                cursor = legacy_conn.execute(f"SELECT * FROM {legacy_tables[0][0]} WHERE id = ?", (legacy_row[0],))
                cursor.row_factory = sqlite3.Row
                sample_row = cursor.fetchone()
                
                if sample_row and 'path' in sample_row.keys():
                    path = sample_row['path']
                    unified_row = unified_conn.execute(
                        "SELECT * FROM hdf5_files WHERE path = ?", (path,)
                    ).fetchone()

                    if unified_row is None:
                        logger.warning(f"⚠ Sample record not found in unified: {path}")
                        legacy_conn.close()
                        unified_conn.close()
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
    parser.add_argument('--legacy-db', default='/data/incoming/hdf5_file_index.sqlite3',
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

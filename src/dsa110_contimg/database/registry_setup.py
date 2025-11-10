"""Data registry schema setup for DSA-110 continuum pipeline.

This module sets up the data registry system by adding registry tables
and ensuring consistent table naming (keeping images, ms_index, mosaics
instead of renaming to *_all variants).
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def setup_data_registry(db_path: Path, verbose: bool = True) -> bool:
    """Set up data registry tables in products database.

    This function:
    1. Adds data_registry, data_relationships, data_tags tables
    2. Reverts any previous *_all table renames back to original names (images, ms_index, mosaics)

    NOTE: We keep original table names (images, ms_index, mosaics) instead of renaming to *_all
    for consistency with the codebase.

    Args:
        db_path: Path to products.sqlite3
        verbose: Print migration progress

    Returns:
        True if migration successful
    """
    if not db_path.exists():
        if verbose:
            logger.warning(f"Database not found: {db_path}")
        return False

    # Add timeout to prevent hanging on locked database
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        # Get list of existing tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cur.fetchall()}

        # Add data registry tables
        if verbose:
            logger.info("Adding data_registry table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS data_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT NOT NULL,
                data_id TEXT NOT NULL UNIQUE,
                base_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'staging',
                stage_path TEXT NOT NULL,
                published_path TEXT,
                created_at REAL NOT NULL,
                staged_at REAL NOT NULL,
                published_at REAL,
                publish_mode TEXT,
                metadata_json TEXT,
                qa_status TEXT,
                validation_status TEXT,
                finalization_status TEXT DEFAULT 'pending',
                auto_publish_enabled INTEGER DEFAULT 1,
                UNIQUE(data_type, data_id)
            )
            """
        )

        if verbose:
            logger.info("Adding data_relationships table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS data_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_data_id TEXT NOT NULL,
                child_data_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                FOREIGN KEY (parent_data_id) REFERENCES data_registry(data_id),
                FOREIGN KEY (child_data_id) REFERENCES data_registry(data_id),
                UNIQUE(parent_data_id, child_data_id, relationship_type)
            )
            """
        )

        if verbose:
            logger.info("Adding data_tags table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS data_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (data_id) REFERENCES data_registry(data_id),
                UNIQUE(data_id, tag)
            )
            """
        )

        # Create indexes
        indexes = [
            ("idx_data_registry_type_status", "data_registry(data_type, status)"),
            ("idx_data_registry_status", "data_registry(status)"),
            ("idx_data_registry_published_at", "data_registry(published_at)"),
            ("idx_data_registry_finalization", "data_registry(finalization_status)"),
            ("idx_data_relationships_parent", "data_relationships(parent_data_id)"),
            ("idx_data_relationships_child", "data_relationships(child_data_id)"),
            ("idx_data_tags_data_id", "data_tags(data_id)"),
        ]

        for idx_name, idx_def in indexes:
            try:
                cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
            except Exception as e:
                if verbose:
                    logger.warning(f"Failed to create index {idx_name}: {e}")

        # NOTE: We no longer rename tables to *_all suffix
        # Keep original table names (images, ms_index, mosaics) for consistency
        # If images_all exists, migrate data back to images if needed
        if "images_all" in existing_tables and "images" not in existing_tables:
            if verbose:
                logger.info(
                    "Renaming images_all -> images (reverting previous migration)..."
                )
            try:
                cur.execute("ALTER TABLE images_all RENAME TO images")
                existing_tables.remove("images_all")
                existing_tables.add("images")
            except Exception as e:
                if verbose:
                    logger.warning(f"Failed to rename images_all -> images: {e}")
        elif "images_all" in existing_tables and "images" in existing_tables:
            if verbose:
                logger.info(
                    "Both images_all and images exist. Migrating data from images_all to images..."
                )
            try:
                # Get column names from both tables to ensure compatibility
                cur.execute("PRAGMA table_info(images_all)")
                all_columns = {row[1]: row[0] for row in cur.fetchall()}
                cur.execute("PRAGMA table_info(images)")
                img_columns = {row[1]: row[0] for row in cur.fetchall()}

                # Find common columns
                common_cols = [col for col in all_columns.keys() if col in img_columns]
                if common_cols:
                    cols_str = ", ".join(common_cols)
                    cur.execute(
                        f"""
                        INSERT OR IGNORE INTO images ({cols_str})
                        SELECT {cols_str} FROM images_all
                    """
                    )
                    if verbose:
                        cur.execute("SELECT COUNT(*) FROM images_all")
                        count_all = cur.fetchone()[0]
                        cur.execute("SELECT COUNT(*) FROM images")
                        count_img = cur.fetchone()[0]
                        logger.info(
                            f"Migrated data from images_all ({count_all} rows) to images (now {count_img} rows)"
                        )
                else:
                    if verbose:
                        logger.warning(
                            "No common columns between images_all and images, skipping migration"
                        )
            except Exception as e:
                if verbose:
                    logger.warning(
                        f"Failed to migrate data from images_all to images: {e}"
                    )

        # Similar handling for ms_index/ms_all if needed
        if "ms_all" in existing_tables and "ms_index" not in existing_tables:
            if verbose:
                logger.info(
                    "Renaming ms_all -> ms_index (reverting previous migration)..."
                )
            try:
                cur.execute("ALTER TABLE ms_all RENAME TO ms_index")
                existing_tables.remove("ms_all")
                existing_tables.add("ms_index")
            except Exception as e:
                if verbose:
                    logger.warning(f"Failed to rename ms_all -> ms_index: {e}")

        # Similar handling for mosaics/mosaics_all if needed
        if "mosaics_all" in existing_tables and "mosaics" not in existing_tables:
            if verbose:
                logger.info(
                    "Renaming mosaics_all -> mosaics (reverting previous migration)..."
                )
            try:
                cur.execute("ALTER TABLE mosaics_all RENAME TO mosaics")
                existing_tables.remove("mosaics_all")
                existing_tables.add("mosaics")
            except Exception as e:
                if verbose:
                    logger.warning(f"Failed to rename mosaics_all -> mosaics: {e}")

        conn.commit()

        if verbose:
            logger.info("✓ Data registry setup completed")
        return True

    except Exception as e:
        logger.error(f"Registry setup failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

"""Database schema evolution for DSA-110 continuum pipeline.

This module provides functions to evolve database schemas by adding new tables,
columns, and indices to existing databases without disrupting operations.
These are idempotent operations that can be run multiple times safely.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional


def evolve_products_schema(db_path: Path, verbose: bool = True) -> bool:
    """Evolve products database schema by adding required tables and columns.

    Tables added:
    - variability_stats: Pre-computed variability statistics per source
    - ese_candidates: Flagged ESE candidates (auto or user-flagged)
    - mosaics: Metadata for mosaic images
    - alert_history: Log of Slack/email alerts sent
    - regions: User-defined regions on images

    Also adds missing columns to existing tables and creates indices.

    Safe to run multiple times (uses IF NOT EXISTS).

    Args:
        db_path: Path to products.sqlite3
        verbose: Print evolution progress

    Returns:
        True if schema evolution successful
    """
    if not db_path.exists():
        if verbose:
            print(f"Database not found: {db_path}")
        return False

    # Add timeout to prevent hanging on locked database
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        # Table: variability_stats
        if verbose:
            print("Adding variability_stats table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS variability_stats (
                source_id TEXT PRIMARY KEY,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                nvss_flux_mjy REAL,
                n_obs INTEGER DEFAULT 0,
                mean_flux_mjy REAL,
                std_flux_mjy REAL,
                min_flux_mjy REAL,
                max_flux_mjy REAL,
                chi2_nu REAL,
                sigma_deviation REAL,
                eta_metric REAL,
                last_measured_at REAL,
                last_mjd REAL,
                updated_at REAL NOT NULL
            )
        """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_variability_chi2 ON variability_stats(chi2_nu)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_variability_sigma ON variability_stats(sigma_deviation)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_variability_last_mjd ON variability_stats(last_mjd)"
        )

        # Table: ese_candidates
        if verbose:
            print("Adding ese_candidates table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ese_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                flagged_at REAL NOT NULL,
                flagged_by TEXT DEFAULT 'auto',
                significance REAL NOT NULL,
                flag_type TEXT NOT NULL,
                notes TEXT,
                status TEXT DEFAULT 'active',
                investigated_at REAL,
                dismissed_at REAL,
                FOREIGN KEY (source_id) REFERENCES variability_stats(source_id)
            )
        """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_ese_source ON ese_candidates(source_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_ese_status ON ese_candidates(status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_ese_flagged ON ese_candidates(flagged_at)"
        )

        # Table: mosaics
        if verbose:
            print("Adding mosaics table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mosaics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                created_at REAL NOT NULL,
                start_mjd REAL NOT NULL,
                end_mjd REAL NOT NULL,
                integration_sec REAL,
                n_images INTEGER,
                center_ra_deg REAL,
                center_dec_deg REAL,
                dec_min_deg REAL,
                dec_max_deg REAL,
                noise_jy REAL,
                beam_major_arcsec REAL,
                beam_minor_arcsec REAL,
                beam_pa_deg REAL,
                n_sources INTEGER,
                thumbnail_path TEXT
            )
        """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_mosaics_created ON mosaics(created_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_mosaics_mjd ON mosaics(start_mjd, end_mjd)"
        )

        # Table: alert_history
        if verbose:
            print("Adding alert_history table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at REAL NOT NULL,
                channel TEXT,
                success INTEGER DEFAULT 1,
                error_msg TEXT
            )
        """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_source ON alert_history(source_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_sent ON alert_history(sent_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_type ON alert_history(alert_type)"
        )

        # Table: regions
        if verbose:
            print("Adding regions table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                coordinates TEXT NOT NULL,
                image_path TEXT NOT NULL,
                created_at REAL NOT NULL,
                created_by TEXT,
                updated_at REAL,
                FOREIGN KEY (image_path) REFERENCES images(path)
            )
        """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_regions_image ON regions(image_path)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_regions_type ON regions(type)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_regions_created ON regions(created_at)"
        )

        # Table: cross_matches
        if verbose:
            print("Adding cross_matches table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cross_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                catalog_type TEXT NOT NULL,
                catalog_source_id TEXT,
                separation_arcsec REAL NOT NULL,
                dra_arcsec REAL,
                ddec_arcsec REAL,
                detected_flux_jy REAL,
                catalog_flux_jy REAL,
                flux_ratio REAL,
                match_quality TEXT,
                match_method TEXT DEFAULT 'basic',
                master_catalog_id TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY (source_id) REFERENCES variability_stats(source_id),
                UNIQUE(source_id, catalog_type)
            )
        """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_matches_source ON cross_matches(source_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_matches_catalog ON cross_matches(catalog_type)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_matches_quality ON cross_matches(match_quality)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_matches_created ON cross_matches(created_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_matches_master ON cross_matches(master_catalog_id)"
        )
        
        # Add master_catalog_id column if it doesn't exist (for existing databases)
        _add_column_if_missing(
            cur, "cross_matches", "master_catalog_id", "TEXT"
        )

        # Add missing columns to existing tables (safe schema evolution)
        if verbose:
            print("Checking for missing columns in existing tables...")

        # ms_index additions (keep original name, check for ms_all only for backwards compatibility)
        table_name = (
            "ms_index"
            if _table_exists(cur, "ms_index")
            else ("ms_all" if _table_exists(cur, "ms_all") else "ms_index")
        )
        _add_column_if_missing(cur, table_name, "field_name", "TEXT")
        _add_column_if_missing(cur, table_name, "pointing_ra_deg", "REAL")
        _add_column_if_missing(cur, table_name, "pointing_dec_deg", "REAL")

        # images additions (keep original name, check for images_all only for backwards compatibility)
        img_table = (
            "images"
            if _table_exists(cur, "images")
            else ("images_all" if _table_exists(cur, "images_all") else "images")
        )
        _add_column_if_missing(cur, img_table, "format", 'TEXT DEFAULT "fits"')
        _add_column_if_missing(cur, img_table, "beam_minor_arcsec", "REAL")
        _add_column_if_missing(cur, img_table, "beam_pa_deg", "REAL")
        _add_column_if_missing(cur, img_table, "dynamic_range", "REAL")
        _add_column_if_missing(cur, img_table, "field_name", "TEXT")
        _add_column_if_missing(cur, img_table, "center_ra_deg", "REAL")
        _add_column_if_missing(cur, img_table, "center_dec_deg", "REAL")
        _add_column_if_missing(cur, img_table, "imsize_x", "INTEGER")
        _add_column_if_missing(cur, img_table, "imsize_y", "INTEGER")
        _add_column_if_missing(cur, img_table, "cellsize_arcsec", "REAL")
        _add_column_if_missing(cur, img_table, "freq_ghz", "REAL")
        _add_column_if_missing(cur, img_table, "bandwidth_mhz", "REAL")
        _add_column_if_missing(cur, img_table, "integration_sec", "REAL")

        # photometry additions (only if table exists)
        if _table_exists(cur, "photometry"):
            _add_column_if_missing(cur, "photometry", "source_id", "TEXT")
            _add_column_if_missing(cur, "photometry", "snr", "REAL")
            _add_column_if_missing(cur, "photometry", "mjd", "REAL")
            _add_column_if_missing(
                cur, "photometry", "sep_from_center_deg", "REAL")
            _add_column_if_missing(
                cur, "photometry", "flags", "INTEGER DEFAULT 0")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_photometry_source_mjd ON photometry(source_id, mjd)"
            )

        # Add missing indices (handle renamed tables)

        # Handle table names (prefer original names, fallback to *_all for backwards compatibility)
        img_table = (
            "images"
            if _table_exists(cur, "images")
            else ("images_all" if _table_exists(cur, "images_all") else "images")
        )
        ms_table = (
            "ms_index"
            if _table_exists(cur, "ms_index")
            else ("ms_all" if _table_exists(cur, "ms_all") else "ms_index")
        )

        if _table_exists(cur, img_table):
            # Check if field_name column exists before creating index
            cur.execute(f"PRAGMA table_info({img_table})")
            img_columns = {row[1] for row in cur.fetchall()}
            if "field_name" in img_columns:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_images_field ON {img_table}(field_name)"
                )

        if _table_exists(cur, ms_table):
            # Check if columns exist before creating indices
            cur.execute(f"PRAGMA table_info({ms_table})")
            ms_columns = {row[1] for row in cur.fetchall()}
            if "field_name" in ms_columns:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_ms_index_field ON {ms_table}(field_name)"
                )
            if "mid_mjd" in ms_columns:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_ms_index_mjd ON {ms_table}(mid_mjd)"
                )

        # Run data registry setup (this will add registry tables and ensure consistent naming)
        # We do this AFTER adding columns to avoid conflicts
        from dsa110_contimg.database.registry_setup import setup_data_registry

        setup_data_registry(db_path, verbose=verbose)

        # Re-commit after data registry setup
        conn.commit()
        if verbose:
            print(f"✓ Schema evolution complete: {db_path}")
        return True

    except Exception as e:
        conn.rollback()
        if verbose:
            print(f"✗ Schema evolution failed: {e}")
        return False
    finally:
        conn.close()


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    """Check if a table exists."""
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (
                table,)
        )
        return cursor.fetchone() is not None
    except Exception:
        return False


def _add_column_if_missing(
    cursor: sqlite3.Cursor, table: str, column: str, col_type: str
):
    """Add column to table if it doesn't exist (SQLite safe schema evolution)."""
    try:
        # Check if table exists first
        if not _table_exists(cursor, table):
            return
        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in cursor.fetchall()}
        if column not in columns:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except Exception:
        pass  # Column might already exist or table doesn't exist


def evolve_ingest_schema(db_path: Path, verbose: bool = True) -> bool:
    """Evolve ingest database schema by adding missing columns.

    Safe to run multiple times.
    """
    if not db_path.exists():
        if verbose:
            print(f"Database not found: {db_path}")
        return False

    # Add timeout to prevent hanging on locked database
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        if verbose:
            print("Checking ingest_queue table...")

        _add_column_if_missing(cur, "ingest_queue",
                               "retry_count", "INTEGER DEFAULT 0")
        _add_column_if_missing(cur, "ingest_queue", "error_message", "TEXT")

        conn.commit()
        if verbose:
            print(f"✓ Schema evolution complete: {db_path}")
        return True
    except Exception as e:
        conn.rollback()
        if verbose:
            print(f"✗ Schema evolution failed: {e}")
        return False
    finally:
        conn.close()


def evolve_all_schemas(
    state_dir: Path = Path("/data/dsa110-contimg/state"), verbose: bool = True
):
    """Evolve all database schemas to latest version.

    Runs schema evolution on all standard database locations.
    """
    if verbose:
        print("=== DSA-110 Database Schema Evolution ===\n")

    results = {}

    # Products database
    products_db = state_dir / "products.sqlite3"
    if verbose:
        print(f"Evolving schema for {products_db}...")
    results["products"] = evolve_products_schema(products_db, verbose=verbose)

    # Ingest database
    ingest_db = state_dir / "ingest.sqlite3"
    if verbose:
        print(f"\nEvolving schema for {ingest_db}...")
    results["ingest"] = evolve_ingest_schema(ingest_db, verbose=verbose)

    if verbose:
        print("\n=== Schema Evolution Summary ===")
        for db_name, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {db_name}: {'Success' if success else 'Failed'}")

    return all(results.values())


# Backwards compatibility aliases
migrate_products_db = evolve_products_schema
migrate_ingest_db = evolve_ingest_schema
migrate_all = evolve_all_schemas


if __name__ == "__main__":
    import sys

    state_dir = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
            "/data/dsa110-contimg/state")
    )
    success = migrate_all(state_dir, verbose=True)
    sys.exit(0 if success else 1)

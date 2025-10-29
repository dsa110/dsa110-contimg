"""Database schema migrations for DSA-110 continuum pipeline.

This module provides migration functions to add new tables and indices to
existing databases without disrupting operations.
"""
import sqlite3
import time
from pathlib import Path
from typing import Optional


def migrate_products_db(db_path: Path, verbose: bool = True) -> bool:
    """Add frontend-required tables to products.sqlite3.
    
    Tables added:
    - variability_stats: Pre-computed variability statistics per source
    - ese_candidates: Flagged ESE candidates (auto or user-flagged)
    - mosaics: Metadata for mosaic images
    - alert_history: Log of Slack/email alerts sent
    
    Safe to run multiple times (uses IF NOT EXISTS).
    
    Args:
        db_path: Path to products.sqlite3
        verbose: Print migration progress
        
    Returns:
        True if migration successful
    """
    if not db_path.exists():
        if verbose:
            print(f"Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Table: variability_stats
        if verbose:
            print("Adding variability_stats table...")
        cur.execute("""
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
                last_measured_at REAL,
                last_mjd REAL,
                updated_at REAL NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_variability_chi2 ON variability_stats(chi2_nu)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_variability_sigma ON variability_stats(sigma_deviation)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_variability_last_mjd ON variability_stats(last_mjd)")
        
        # Table: ese_candidates
        if verbose:
            print("Adding ese_candidates table...")
        cur.execute("""
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
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ese_source ON ese_candidates(source_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ese_status ON ese_candidates(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ese_flagged ON ese_candidates(flagged_at)")
        
        # Table: mosaics
        if verbose:
            print("Adding mosaics table...")
        cur.execute("""
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
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_mosaics_created ON mosaics(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_mosaics_mjd ON mosaics(start_mjd, end_mjd)")
        
        # Table: alert_history
        if verbose:
            print("Adding alert_history table...")
        cur.execute("""
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
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_source ON alert_history(source_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_sent ON alert_history(sent_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_type ON alert_history(alert_type)")
        
        # Add missing columns to existing tables (safe migrations)
        if verbose:
            print("Checking for missing columns in existing tables...")
        
        # ms_index additions
        _add_column_if_missing(cur, 'ms_index', 'field_name', 'TEXT')
        _add_column_if_missing(cur, 'ms_index', 'pointing_ra_deg', 'REAL')
        _add_column_if_missing(cur, 'ms_index', 'pointing_dec_deg', 'REAL')
        
        # images additions
        _add_column_if_missing(cur, 'images', 'format', 'TEXT DEFAULT "fits"')
        _add_column_if_missing(cur, 'images', 'beam_minor_arcsec', 'REAL')
        _add_column_if_missing(cur, 'images', 'beam_pa_deg', 'REAL')
        _add_column_if_missing(cur, 'images', 'dynamic_range', 'REAL')
        _add_column_if_missing(cur, 'images', 'field_name', 'TEXT')
        _add_column_if_missing(cur, 'images', 'center_ra_deg', 'REAL')
        _add_column_if_missing(cur, 'images', 'center_dec_deg', 'REAL')
        _add_column_if_missing(cur, 'images', 'imsize_x', 'INTEGER')
        _add_column_if_missing(cur, 'images', 'imsize_y', 'INTEGER')
        _add_column_if_missing(cur, 'images', 'cellsize_arcsec', 'REAL')
        _add_column_if_missing(cur, 'images', 'freq_ghz', 'REAL')
        _add_column_if_missing(cur, 'images', 'bandwidth_mhz', 'REAL')
        _add_column_if_missing(cur, 'images', 'integration_sec', 'REAL')
        
        # photometry additions
        _add_column_if_missing(cur, 'photometry', 'source_id', 'TEXT')
        _add_column_if_missing(cur, 'photometry', 'snr', 'REAL')
        _add_column_if_missing(cur, 'photometry', 'mjd', 'REAL')
        _add_column_if_missing(cur, 'photometry', 'sep_from_center_deg', 'REAL')
        _add_column_if_missing(cur, 'photometry', 'flags', 'INTEGER DEFAULT 0')
        
        # Add missing indices
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photometry_source_mjd ON photometry(source_id, mjd)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_images_field ON images(field_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ms_index_field ON ms_index(field_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ms_index_mjd ON ms_index(mid_mjd)")
        
        conn.commit()
        if verbose:
            print(f"✓ Migration complete: {db_path}")
        return True
        
    except Exception as e:
        conn.rollback()
        if verbose:
            print(f"✗ Migration failed: {e}")
        return False
    finally:
        conn.close()


def _add_column_if_missing(cursor: sqlite3.Cursor, table: str, column: str, col_type: str):
    """Add column to table if it doesn't exist (SQLite safe migration)."""
    try:
        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in cursor.fetchall()}
        if column not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except Exception:
        pass  # Column might already exist or table doesn't exist


def migrate_ingest_db(db_path: Path, verbose: bool = True) -> bool:
    """Add missing columns to ingest.sqlite3.
    
    Safe to run multiple times.
    """
    if not db_path.exists():
        if verbose:
            print(f"Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        if verbose:
            print("Checking ingest_queue table...")
        
        _add_column_if_missing(cur, 'ingest_queue', 'retry_count', 'INTEGER DEFAULT 0')
        _add_column_if_missing(cur, 'ingest_queue', 'error_message', 'TEXT')
        
        conn.commit()
        if verbose:
            print(f"✓ Migration complete: {db_path}")
        return True
    except Exception as e:
        conn.rollback()
        if verbose:
            print(f"✗ Migration failed: {e}")
        return False
    finally:
        conn.close()


def migrate_all(state_dir: Path = Path("/data/dsa110-contimg/state"), verbose: bool = True):
    """Run all migrations on standard database locations."""
    if verbose:
        print("=== DSA-110 Database Migrations ===\n")
    
    results = {}
    
    # Products database
    products_db = state_dir / "products.sqlite3"
    if verbose:
        print(f"Migrating {products_db}...")
    results['products'] = migrate_products_db(products_db, verbose=verbose)
    
    # Ingest database
    ingest_db = state_dir / "ingest.sqlite3"
    if verbose:
        print(f"\nMigrating {ingest_db}...")
    results['ingest'] = migrate_ingest_db(ingest_db, verbose=verbose)
    
    if verbose:
        print("\n=== Migration Summary ===")
        for db_name, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {db_name}: {'Success' if success else 'Failed'}")
    
    return all(results.values())


if __name__ == "__main__":
    import sys
    state_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data/dsa110-contimg/state")
    success = migrate_all(state_dir, verbose=True)
    sys.exit(0 if success else 1)


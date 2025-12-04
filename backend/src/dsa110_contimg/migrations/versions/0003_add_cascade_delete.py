"""Add ON DELETE CASCADE to images and photometry foreign keys.

This migration enhances Issue #14 fix by adding CASCADE deletion policies.

When an MS file is deleted from ms_index:
- Related images are automatically deleted (ON DELETE CASCADE)
- Related photometry is automatically deleted (ON DELETE CASCADE via images)

This prevents orphaned records and simplifies cleanup operations.

Revision ID: 0003_add_cascade_delete
Revises: 0002_add_calibration_fk
Create Date: 2025-01-XX
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0003_add_cascade_delete'
down_revision = '0002_add_calibration_fk'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ON DELETE CASCADE to images and photometry foreign keys.

    SQLite doesn't support ALTER TABLE for foreign keys, so we:
    1. Create new tables with updated FK constraints
    2. Copy data
    3. Drop old tables
    4. Rename new tables
    5. Recreate indexes
    """
    # =========================================================================
    # Step 1: Update images table
    # =========================================================================
    op.execute("""
        CREATE TABLE images_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            ms_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            type TEXT NOT NULL,
            format TEXT DEFAULT 'fits',
            beam_major_arcsec REAL,
            beam_minor_arcsec REAL,
            beam_pa_deg REAL,
            noise_jy REAL,
            dynamic_range REAL,
            pbcor INTEGER DEFAULT 0,
            field_name TEXT,
            center_ra_deg REAL,
            center_dec_deg REAL,
            imsize_x INTEGER,
            imsize_y INTEGER,
            cellsize_arcsec REAL,
            freq_ghz REAL,
            bandwidth_mhz REAL,
            integration_sec REAL,
            FOREIGN KEY (ms_path) REFERENCES ms_index(path) ON DELETE CASCADE
        )
    """)

    op.execute("""
        INSERT INTO images_new
        SELECT * FROM images
    """)

    op.execute("DROP TABLE images")
    op.execute("ALTER TABLE images_new RENAME TO images")

    # Recreate indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_images_type ON images(type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at)")

    # =========================================================================
    # Step 2: Update photometry table
    # =========================================================================
    op.execute("""
        CREATE TABLE photometry_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            source_id TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL NOT NULL,
            flux_err_jy REAL,
            peak_flux_jy REAL,
            rms_jy REAL,
            snr REAL,
            major_arcsec REAL,
            minor_arcsec REAL,
            pa_deg REAL,
            measured_at REAL NOT NULL,
            quality_flag TEXT,
            FOREIGN KEY (image_path) REFERENCES images(path) ON DELETE CASCADE
        )
    """)

    op.execute("""
        INSERT INTO photometry_new
        SELECT * FROM photometry
    """)

    op.execute("DROP TABLE photometry")
    op.execute("ALTER TABLE photometry_new RENAME TO photometry")

    # Recreate indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_photometry_source ON photometry(source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_photometry_coords ON photometry(ra_deg, dec_deg)")

    # =========================================================================
    # Step 3: Update calibration_applied table
    # =========================================================================
    op.execute("""
        CREATE TABLE calibration_applied_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT NOT NULL,
            caltable_path TEXT NOT NULL,
            applied_at REAL NOT NULL,
            quality REAL,
            success INTEGER DEFAULT 1,
            error_message TEXT,
            FOREIGN KEY (ms_path) REFERENCES ms_index(path) ON DELETE CASCADE,
            FOREIGN KEY (caltable_path) REFERENCES calibration_tables(path) ON DELETE CASCADE
        )
    """)

    op.execute("""
        INSERT INTO calibration_applied_new
        SELECT * FROM calibration_applied
    """)

    op.execute("DROP TABLE calibration_applied")
    op.execute("ALTER TABLE calibration_applied_new RENAME TO calibration_applied")

    # Recreate indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_cal_applied_ms ON calibration_applied(ms_path)")


def downgrade() -> None:
    """Remove ON DELETE CASCADE (revert to original FK without CASCADE)."""
    # =========================================================================
    # Revert images table
    # =========================================================================
    op.execute("""
        CREATE TABLE images_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            ms_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            type TEXT NOT NULL,
            format TEXT DEFAULT 'fits',
            beam_major_arcsec REAL,
            beam_minor_arcsec REAL,
            beam_pa_deg REAL,
            noise_jy REAL,
            dynamic_range REAL,
            pbcor INTEGER DEFAULT 0,
            field_name TEXT,
            center_ra_deg REAL,
            center_dec_deg REAL,
            imsize_x INTEGER,
            imsize_y INTEGER,
            cellsize_arcsec REAL,
            freq_ghz REAL,
            bandwidth_mhz REAL,
            integration_sec REAL,
            FOREIGN KEY (ms_path) REFERENCES ms_index(path)
        )
    """)

    op.execute("""
        INSERT INTO images_old
        SELECT * FROM images
    """)

    op.execute("DROP TABLE images")
    op.execute("ALTER TABLE images_old RENAME TO images")
    op.execute("CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_images_type ON images(type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at)")

    # =========================================================================
    # Revert photometry table
    # =========================================================================
    op.execute("""
        CREATE TABLE photometry_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            source_id TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL NOT NULL,
            flux_err_jy REAL,
            peak_flux_jy REAL,
            rms_jy REAL,
            snr REAL,
            major_arcsec REAL,
            minor_arcsec REAL,
            pa_deg REAL,
            measured_at REAL NOT NULL,
            quality_flag TEXT,
            FOREIGN KEY (image_path) REFERENCES images(path)
        )
    """)

    op.execute("""
        INSERT INTO photometry_old
        SELECT * FROM photometry
    """)

    op.execute("DROP TABLE photometry")
    op.execute("ALTER TABLE photometry_old RENAME TO photometry")
    op.execute("CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_photometry_source ON photometry(source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_photometry_coords ON photometry(ra_deg, dec_deg)")

    # =========================================================================
    # Revert calibration_applied table
    # =========================================================================
    op.execute("""
        CREATE TABLE calibration_applied_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT NOT NULL,
            caltable_path TEXT NOT NULL,
            applied_at REAL NOT NULL,
            quality REAL,
            success INTEGER DEFAULT 1,
            error_message TEXT,
            FOREIGN KEY (ms_path) REFERENCES ms_index(path),
            FOREIGN KEY (caltable_path) REFERENCES calibration_tables(path)
        )
    """)

    op.execute("""
        INSERT INTO calibration_applied_old
        SELECT * FROM calibration_applied
    """)

    op.execute("DROP TABLE calibration_applied")
    op.execute("ALTER TABLE calibration_applied_old RENAME TO calibration_applied")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cal_applied_ms ON calibration_applied(ms_path)")

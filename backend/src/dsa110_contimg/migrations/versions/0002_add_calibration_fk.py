"""Add foreign key constraint to calibration_tables.source_ms_path.

This fixes Issue #14: Database Schema Allows Inconsistent States.

The calibration_tables.source_ms_path column previously had no foreign key
constraint to ms_index, allowing orphaned records. This migration adds the
missing constraint with ON DELETE SET NULL policy (calibration tables can
persist even if source MS is deleted).

Revision ID: 0002_add_calibration_fk
Revises: 0001_baseline
Create Date: 2025-12-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_calibration_fk'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add foreign key constraint to calibration_tables.source_ms_path.

    SQLite doesn't support ALTER TABLE ADD FOREIGN KEY, so we need to:
    1. Create new table with FK constraint
    2. Copy data from old table
    3. Drop old table
    4. Rename new table
    5. Recreate indexes
    """
    # Step 1: Create new table with FK constraint
    op.execute("""
        CREATE TABLE calibration_tables_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            table_type TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            cal_field TEXT,
            refant TEXT,
            created_at REAL NOT NULL,
            valid_start_mjd REAL,
            valid_end_mjd REAL,
            status TEXT NOT NULL DEFAULT 'active',
            source_ms_path TEXT,
            solver_command TEXT,
            solver_version TEXT,
            solver_params TEXT,
            quality_metrics TEXT,
            notes TEXT,
            FOREIGN KEY (source_ms_path) REFERENCES ms_index(path) ON DELETE SET NULL
        )
    """)

    # Step 2: Copy all data from old table to new table
    op.execute("""
        INSERT INTO calibration_tables_new (
            id, set_name, path, table_type, order_index, cal_field, refant,
            created_at, valid_start_mjd, valid_end_mjd, status, source_ms_path,
            solver_command, solver_version, solver_params, quality_metrics, notes
        )
        SELECT
            id, set_name, path, table_type, order_index, cal_field, refant,
            created_at, valid_start_mjd, valid_end_mjd, status, source_ms_path,
            solver_command, solver_version, solver_params, quality_metrics, notes
        FROM calibration_tables
    """)

    # Step 3: Drop old table
    op.execute("DROP TABLE calibration_tables")

    # Step 4: Rename new table
    op.execute("ALTER TABLE calibration_tables_new RENAME TO calibration_tables")

    # Step 5: Recreate indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_caltables_set ON calibration_tables(set_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_caltables_valid ON calibration_tables(valid_start_mjd, valid_end_mjd)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_caltables_status ON calibration_tables(status)")


def downgrade() -> None:
    """Remove foreign key constraint from calibration_tables.source_ms_path."""
    # Step 1: Create table without FK constraint (original schema)
    op.execute("""
        CREATE TABLE calibration_tables_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            table_type TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            cal_field TEXT,
            refant TEXT,
            created_at REAL NOT NULL,
            valid_start_mjd REAL,
            valid_end_mjd REAL,
            status TEXT NOT NULL DEFAULT 'active',
            source_ms_path TEXT,
            solver_command TEXT,
            solver_version TEXT,
            solver_params TEXT,
            quality_metrics TEXT,
            notes TEXT
        )
    """)

    # Step 2: Copy data back
    op.execute("""
        INSERT INTO calibration_tables_old (
            id, set_name, path, table_type, order_index, cal_field, refant,
            created_at, valid_start_mjd, valid_end_mjd, status, source_ms_path,
            solver_command, solver_version, solver_params, quality_metrics, notes
        )
        SELECT
            id, set_name, path, table_type, order_index, cal_field, refant,
            created_at, valid_start_mjd, valid_end_mjd, status, source_ms_path,
            solver_command, solver_version, solver_params, quality_metrics, notes
        FROM calibration_tables
    """)

    # Step 3: Drop new table
    op.execute("DROP TABLE calibration_tables")

    # Step 4: Rename old table
    op.execute("ALTER TABLE calibration_tables_old RENAME TO calibration_tables")

    # Step 5: Recreate indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_caltables_set ON calibration_tables(set_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_caltables_valid ON calibration_tables(valid_start_mjd, valid_end_mjd)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_caltables_status ON calibration_tables(status)")

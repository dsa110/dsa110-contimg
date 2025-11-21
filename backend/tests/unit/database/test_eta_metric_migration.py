"""
Test eta_metric column migration in variability_stats table.
"""

import sqlite3
import tempfile
from pathlib import Path

from dsa110_contimg.database.schema_evolution import evolve_products_schema


def test_eta_metric_column_added():
    """Test that eta_metric column is added to variability_stats table."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    try:
        # Create initial database with variability_stats table (without eta_metric)
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS variability_stats (
                source_id TEXT PRIMARY KEY,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                chi2_nu REAL
            )
        """
        )
        conn.commit()
        conn.close()

        # Run schema evolution
        evolve_products_schema(db_path, verbose=False)

        # Verify eta_metric column was added
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(variability_stats)").fetchall()
        }
        conn.close()

        assert "eta_metric" in columns, "eta_metric column should be added"

        # Verify index was created
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='variability_stats'"
            ).fetchall()
        }
        conn.close()

        assert "idx_variability_eta" in indexes, "eta_metric index should be created"

    finally:
        if db_path.exists():
            db_path.unlink()


def test_eta_metric_column_idempotent():
    """Test that running schema evolution multiple times is safe."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    try:
        # Run schema evolution twice
        evolve_products_schema(db_path, verbose=False)
        evolve_products_schema(db_path, verbose=False)

        # Verify eta_metric column exists
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(variability_stats)").fetchall()
        }
        conn.close()

        assert "eta_metric" in columns, "eta_metric column should exist after multiple runs"

    finally:
        if db_path.exists():
            db_path.unlink()

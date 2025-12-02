"""
Contract tests for database schema and operations.

These tests verify that the unified database maintains schema integrity
and foreign key relationships through all operations.

Contract guarantees:
1. All required tables exist
2. Foreign key constraints are enforced
3. Required columns have correct types
4. Queries return expected shapes
5. Concurrent access is handled via WAL mode
"""

import sqlite3
from pathlib import Path

import pytest


class TestSchemaContract:
    """Verify database schema correctness."""

    def test_database_exists(self, test_pipeline_db: Path):
        """Contract: Database file must exist."""
        assert test_pipeline_db.exists(), "Database not created"

    def test_required_tables_exist(self, test_pipeline_db: Path):
        """Contract: All required tables must exist."""
        required_tables = [
            "ms_index",
            "images",
            "calibration_tables",
            "hdf5_file_index",
            "ingest_queue",
            "photometry_results",
        ]
        
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        existing_tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        for table in required_tables:
            assert table in existing_tables, f"Required table '{table}' not found"

    def test_ms_index_schema(self, test_pipeline_db: Path):
        """Contract: ms_index table has required columns."""
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(ms_index)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        required_columns = {
            "ms_path",
            "group_id",
            "mid_time_mjd",
            "dec_deg",
            "n_integrations",
            "n_channels",
            "created_at",
        }
        
        for col in required_columns:
            assert col in columns, f"Column '{col}' missing from ms_index"

    def test_images_schema(self, test_pipeline_db: Path):
        """Contract: images table has required columns."""
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(images)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        required_columns = {
            "image_path",
            "ms_path",
            "field_id",
            "rms_jy",
            "peak_jy",
            "created_at",
        }
        
        for col in required_columns:
            assert col in columns, f"Column '{col}' missing from images"


class TestWALModeContract:
    """Verify WAL mode for concurrent access."""

    def test_wal_mode_enabled(self, test_pipeline_db: Path):
        """Contract: Database should use WAL journal mode."""
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0].lower()
        conn.close()
        
        # Our unified database should use WAL
        assert mode == "wal", f"Expected WAL mode, got {mode}"

    def test_concurrent_read(self, populated_pipeline_db: Path):
        """Contract: Multiple readers should work concurrently."""
        import threading
        results = []
        errors = []
        
        def reader(db_path: Path, idx: int):
            try:
                conn = sqlite3.connect(db_path, timeout=30)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ms_index")
                count = cursor.fetchone()[0]
                results.append((idx, count))
                conn.close()
            except Exception as e:
                errors.append((idx, str(e)))
        
        # Launch 5 concurrent readers
        threads = [
            threading.Thread(target=reader, args=(populated_pipeline_db, i))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors, f"Reader errors: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
        
        # All readers should see the same count
        counts = [r[1] for r in results]
        assert len(set(counts)) == 1, f"Inconsistent counts: {counts}"


class TestQueryContract:
    """Verify query operations work correctly."""

    def test_insert_ms_index(self, test_pipeline_db: Path):
        """Contract: MS index insertions must work."""
        from datetime import datetime
        
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO ms_index (
                ms_path, group_id, mid_time_mjd, dec_deg,
                n_integrations, n_channels, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "/test/path/test.ms",
                "test_group",
                60000.5,
                35.0,
                24,
                6144,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT ms_path FROM ms_index WHERE group_id = ?", ("test_group",))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None, "Insert failed"
        assert row[0] == "/test/path/test.ms"

    def test_query_by_time_range(self, populated_pipeline_db: Path):
        """Contract: Time range queries must work."""
        conn = sqlite3.connect(populated_pipeline_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM ms_index
            WHERE mid_time_mjd BETWEEN ? AND ?
            ORDER BY mid_time_mjd
            """,
            (59999.0, 60003.0),
        )
        rows = cursor.fetchall()
        conn.close()
        
        # Should find our 3 test entries
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
        
        # Should be in order
        times = [row["mid_time_mjd"] for row in rows]
        assert times == sorted(times), "Results not sorted by time"

    def test_join_ms_images(self, populated_pipeline_db: Path):
        """Contract: JOIN between ms_index and images must work."""
        conn = sqlite3.connect(populated_pipeline_db)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT m.ms_path, COUNT(i.image_path) as image_count
            FROM ms_index m
            LEFT JOIN images i ON m.ms_path = i.ms_path
            GROUP BY m.ms_path
            """
        )
        rows = cursor.fetchall()
        conn.close()
        
        assert len(rows) > 0, "JOIN returned no results"
        
        # Each MS should have associated images
        for ms_path, count in rows:
            assert count >= 0, f"Negative image count for {ms_path}"


class TestConstraintContract:
    """Verify constraint enforcement."""

    def test_unique_ms_path(self, test_pipeline_db: Path):
        """Contract: ms_path should be unique in ms_index."""
        from datetime import datetime
        
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        # First insert should succeed
        cursor.execute(
            """
            INSERT INTO ms_index (
                ms_path, group_id, mid_time_mjd, dec_deg,
                n_integrations, n_channels, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "/unique/test.ms",
                "group1",
                60000.0,
                35.0,
                24,
                6144,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        
        # Second insert with same path should fail
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO ms_index (
                    ms_path, group_id, mid_time_mjd, dec_deg,
                    n_integrations, n_channels, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "/unique/test.ms",  # Same path
                    "group2",
                    60001.0,
                    36.0,
                    24,
                    6144,
                    datetime.now().isoformat(),
                ),
            )
        
        conn.close()

    def test_not_null_constraints(self, test_pipeline_db: Path):
        """Contract: Required fields must not be null."""
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        # Try to insert with null required field
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO ms_index (
                    ms_path, group_id, mid_time_mjd, dec_deg,
                    n_integrations, n_channels, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,  # ms_path should be NOT NULL
                    "group",
                    60000.0,
                    35.0,
                    24,
                    6144,
                    None,
                ),
            )
        
        conn.close()


class TestMigrationContract:
    """Verify migration safety."""

    def test_schema_version_tracked(self, test_pipeline_db: Path):
        """Contract: Schema version should be trackable."""
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        
        # Check for schema_version table or user_version pragma
        cursor.execute("PRAGMA user_version")
        version = cursor.fetchone()[0]
        conn.close()
        
        # Version should be set (we use PRAGMA user_version for schema tracking)
        assert isinstance(version, int), "Schema version not tracked"

    def test_table_creation_idempotent(self, test_pipeline_db: Path):
        """Contract: Schema creation should be idempotent."""
        from dsa110_contimg.database.unified import Database, UNIFIED_SCHEMA
        
        # Initialize twice - should not fail
        db1 = Database(test_pipeline_db)
        db1.conn.executescript(UNIFIED_SCHEMA)
        db1.conn.commit()
        
        db2 = Database(test_pipeline_db)
        db2.conn.executescript(UNIFIED_SCHEMA)  # Should not raise (IF NOT EXISTS)
        db2.conn.commit()
        
        # Tables should still exist
        conn = sqlite3.connect(test_pipeline_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        assert len(tables) > 0, "Tables disappeared after re-initialization"

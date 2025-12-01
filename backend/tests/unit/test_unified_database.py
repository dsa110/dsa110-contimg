"""
Unit tests for the unified database module.

Tests the simplified Database class and UNIFIED_SCHEMA created as part
of the complexity reduction guide (Phase 2).
"""

import os
import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from dsa110_contimg.database.unified import (
    Database,
    init_unified_db,
    get_db,
    close_db,
    UNIFIED_SCHEMA,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_pipeline.sqlite3"


@pytest.fixture
def db(temp_db_path):
    """Create and initialize a test database."""
    database = init_unified_db(temp_db_path)
    yield database
    database.close()


# =============================================================================
# Database Class Tests
# =============================================================================

class TestDatabaseBasics:
    """Test basic Database class functionality."""
    
    def test_init_creates_connection(self, temp_db_path):
        """Database should create connection on first access."""
        db = Database(temp_db_path)
        # Connection is lazy - not created until accessed
        assert db._conn is None
        
        # Accessing conn property creates connection
        conn = db.conn
        assert conn is not None
        assert db._conn is not None
        
        db.close()
    
    def test_init_creates_parent_directory(self, tmp_path):
        """Database should create parent directory if needed."""
        nested_path = tmp_path / "nested" / "deep" / "test.sqlite3"
        db = Database(nested_path)
        
        # Access conn to trigger creation
        _ = db.conn
        
        assert nested_path.parent.exists()
        db.close()
    
    def test_default_path_from_env(self, tmp_path, monkeypatch):
        """Database should read path from PIPELINE_DB env var."""
        test_path = str(tmp_path / "from_env.sqlite3")
        monkeypatch.setenv("PIPELINE_DB", test_path)
        
        db = Database()
        assert str(db.db_path) == test_path
        db.close()
    
    def test_connection_settings(self, db):
        """Connection should have proper settings (WAL mode, row factory)."""
        # Check WAL mode
        result = db.query_val("PRAGMA journal_mode")
        assert result == "wal"
        
        # Check row factory works
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms", 60000.0, "pending", time.time())
        )
        row = db.query_one("SELECT * FROM ms_index")
        
        # Should be dict-like (sqlite3.Row)
        assert row["path"] == "/test/ms"
        assert row["status"] == "pending"
    
    def test_context_manager(self, temp_db_path):
        """Database should work as context manager."""
        with Database(temp_db_path) as db:
            db.execute_script("CREATE TABLE test (id INTEGER)")
            db.execute("INSERT INTO test VALUES (?)", (1,))
            result = db.query_val("SELECT COUNT(*) FROM test")
            assert result == 1
        
        # Connection should be closed after context
        assert db._conn is None


class TestDatabaseQueries:
    """Test query methods."""
    
    def test_query_returns_list_of_dicts(self, db):
        """query() should return list of dictionaries."""
        # Insert test data
        for i in range(3):
            db.execute(
                "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
                (f"/test/ms{i}", 60000.0 + i, "pending", time.time())
            )
        
        results = db.query("SELECT path, status FROM ms_index ORDER BY path")
        
        assert len(results) == 3
        assert isinstance(results[0], dict)
        assert results[0]["path"] == "/test/ms0"
        assert results[1]["path"] == "/test/ms1"
    
    def test_query_with_params(self, db):
        """query() should handle parameters correctly."""
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms", 60000.0, "completed", time.time())
        )
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms2", 60001.0, "pending", time.time())
        )
        
        results = db.query(
            "SELECT * FROM ms_index WHERE status = ?",
            ("completed",)
        )
        
        assert len(results) == 1
        assert results[0]["path"] == "/test/ms"
    
    def test_query_empty_result(self, db):
        """query() should return empty list for no results."""
        results = db.query("SELECT * FROM ms_index WHERE 1 = 0")
        assert results == []
    
    def test_query_one_returns_dict(self, db):
        """query_one() should return single dict."""
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms", 60000.0, "pending", time.time())
        )
        
        result = db.query_one("SELECT * FROM ms_index")
        
        assert isinstance(result, dict)
        assert result["path"] == "/test/ms"
    
    def test_query_one_returns_none_for_empty(self, db):
        """query_one() should return None for no results."""
        result = db.query_one("SELECT * FROM ms_index WHERE 1 = 0")
        assert result is None
    
    def test_query_val_returns_scalar(self, db):
        """query_val() should return single value."""
        for i in range(5):
            db.execute(
                "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
                (f"/test/ms{i}", 60000.0 + i, "pending", time.time())
            )
        
        count = db.query_val("SELECT COUNT(*) FROM ms_index")
        assert count == 5
        
        max_mjd = db.query_val("SELECT MAX(mid_mjd) FROM ms_index")
        assert max_mjd == 60004.0
    
    def test_query_val_returns_none_for_empty(self, db):
        """query_val() should return None for no results."""
        result = db.query_val("SELECT path FROM ms_index WHERE 1 = 0")
        assert result is None


class TestDatabaseWrites:
    """Test write operations."""
    
    def test_execute_returns_rowcount(self, db):
        """execute() should return affected row count."""
        # Insert
        count = db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms", 60000.0, "pending", time.time())
        )
        assert count == 1
        
        # Update multiple rows
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms2", 60001.0, "pending", time.time())
        )
        count = db.execute(
            "UPDATE ms_index SET status = ? WHERE status = ?",
            ("completed", "pending")
        )
        assert count == 2
    
    def test_execute_autocommits(self, db, temp_db_path):
        """execute() should auto-commit changes."""
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms", 60000.0, "pending", time.time())
        )
        
        # Open new connection to verify commit
        db2 = Database(temp_db_path)
        count = db2.query_val("SELECT COUNT(*) FROM ms_index")
        assert count == 1
        db2.close()
    
    def test_execute_many(self, db):
        """execute_many() should handle multiple inserts."""
        params = [
            (f"/test/ms{i}", 60000.0 + i, "pending", time.time())
            for i in range(100)
        ]
        
        count = db.execute_many(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            params
        )
        
        # Note: executemany rowcount behavior varies
        total = db.query_val("SELECT COUNT(*) FROM ms_index")
        assert total == 100
    
    def test_execute_script(self, db):
        """execute_script() should run multiple statements."""
        db.execute_script("""
            INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES ('/a', 1, 's', 0);
            INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES ('/b', 2, 's', 0);
            INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES ('/c', 3, 's', 0);
        """)
        
        count = db.query_val("SELECT COUNT(*) FROM ms_index")
        assert count == 3


class TestDatabaseTransactions:
    """Test transaction handling."""
    
    def test_transaction_commits_on_success(self, db, temp_db_path):
        """transaction() should commit on successful completion."""
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
                ("/test/ms1", 60000.0, "pending", time.time())
            )
            conn.execute(
                "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
                ("/test/ms2", 60001.0, "pending", time.time())
            )
        
        # Verify committed
        db2 = Database(temp_db_path)
        count = db2.query_val("SELECT COUNT(*) FROM ms_index")
        assert count == 2
        db2.close()
    
    def test_transaction_rollback_on_error(self, db):
        """transaction() should rollback on exception."""
        # First insert outside transaction
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/existing", 60000.0, "pending", time.time())
        )
        
        # Transaction that will fail
        with pytest.raises(sqlite3.IntegrityError):
            with db.transaction() as conn:
                conn.execute(
                    "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
                    ("/test/ms1", 60001.0, "pending", time.time())
                )
                # This should fail due to UNIQUE constraint
                conn.execute(
                    "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
                    ("/existing", 60002.0, "pending", time.time())
                )
        
        # Only the pre-existing row should remain
        count = db.query_val("SELECT COUNT(*) FROM ms_index")
        assert count == 1


# =============================================================================
# Schema Tests
# =============================================================================

class TestUnifiedSchema:
    """Test the unified database schema."""
    
    def test_schema_creates_all_tables(self, db):
        """Schema should create all expected tables."""
        expected_tables = {
            "ms_index",
            "images",
            "photometry",
            "calibration_tables",
            "calibration_applied",
            "calibrator_catalog",
            "calibrator_transits",
            "hdf5_files",
            "pointing_history",
            "processing_queue",
            "subband_files",
            "performance_metrics",
            "dead_letter_queue",
            "storage_locations",
            "alert_history",
        }
        
        result = db.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = {r["name"] for r in result}
        
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    
    def test_foreign_keys(self, db):
        """Schema should have proper foreign key relationships."""
        # Insert parent record
        db.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/test/ms", 60000.0, "completed", time.time())
        )
        
        # Insert child record
        db.execute(
            "INSERT INTO images (path, ms_path, created_at, type) VALUES (?, ?, ?, ?)",
            ("/test/image.fits", "/test/ms", time.time(), "dirty")
        )
        
        # Verify relationship
        result = db.query("""
            SELECT i.path as image_path, m.path as ms_path
            FROM images i
            JOIN ms_index m ON i.ms_path = m.path
        """)
        
        assert len(result) == 1
        assert result[0]["image_path"] == "/test/image.fits"
        assert result[0]["ms_path"] == "/test/ms"
    
    def test_indexes_exist(self, db):
        """Schema should create indexes."""
        result = db.query(
            "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
        )
        index_names = [r["name"] for r in result]
        
        # Check for some expected indexes
        assert any("ms_index" in name for name in index_names)
        assert any("images" in name for name in index_names)


# =============================================================================
# Global Instance Tests
# =============================================================================

class TestGlobalInstance:
    """Test global database instance management."""
    
    def test_get_db_returns_singleton(self, temp_db_path, monkeypatch):
        """get_db() should return same instance."""
        monkeypatch.setenv("PIPELINE_DB", str(temp_db_path))
        
        # Reset global state
        close_db()
        
        db1 = get_db()
        db2 = get_db()
        
        assert db1 is db2
        
        close_db()
    
    def test_close_db_clears_global(self, temp_db_path, monkeypatch):
        """close_db() should clear global instance."""
        monkeypatch.setenv("PIPELINE_DB", str(temp_db_path))
        
        # Reset global state
        close_db()
        
        db1 = get_db()
        close_db()
        db2 = get_db()
        
        assert db1 is not db2
        
        close_db()


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for realistic usage patterns."""
    
    def test_typical_pipeline_workflow(self, db):
        """Test a typical pipeline workflow."""
        # 1. Register HDF5 files
        for i in range(16):
            db.execute(
                """INSERT INTO hdf5_files 
                   (path, filename, group_id, subband_code, subband_num, indexed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (f"/incoming/obs_sb{i:02d}.hdf5", f"obs_sb{i:02d}.hdf5",
                 "obs_001", f"sb{i:02d}", i, time.time())
            )
        
        # 2. Create processing queue entry
        db.execute(
            """INSERT INTO processing_queue 
               (group_id, state, received_at, last_update, expected_subbands)
               VALUES (?, ?, ?, ?, ?)""",
            ("obs_001", "pending", time.time(), time.time(), 16)
        )
        
        # 3. After conversion, register MS
        db.execute(
            """INSERT INTO ms_index 
               (path, mid_mjd, status, stage, group_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("/stage/ms/obs_001.ms", 60123.5, "converted", "imaging", "obs_001", time.time())
        )
        
        # 4. Register calibration table
        db.execute(
            """INSERT INTO calibration_tables
               (set_name, path, table_type, order_index, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("cal_set_001", "/stage/cal/bandpass.tb", "bandpass", 0, time.time(), "active")
        )
        
        # 5. Register image
        db.execute(
            """INSERT INTO images
               (path, ms_path, created_at, type, noise_jy)
               VALUES (?, ?, ?, ?, ?)""",
            ("/stage/images/obs_001.fits", "/stage/ms/obs_001.ms", time.time(), "dirty", 0.001)
        )
        
        # 6. Query for pending observations with calibration
        result = db.query("""
            SELECT m.path as ms_path, m.status, c.path as cal_path
            FROM ms_index m
            LEFT JOIN calibration_tables c ON c.status = 'active'
            WHERE m.status = 'converted'
        """)
        
        assert len(result) == 1
        assert result[0]["ms_path"] == "/stage/ms/obs_001.ms"
        assert result[0]["cal_path"] == "/stage/cal/bandpass.tb"
    
    def test_concurrent_access_pattern(self, temp_db_path):
        """Test that multiple Database instances can coexist."""
        db1 = Database(temp_db_path)
        init_unified_db(temp_db_path)
        
        db2 = Database(temp_db_path)
        
        # Both should be able to write with WAL mode
        db1.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/from_db1", 60000.0, "pending", time.time())
        )
        
        db2.execute(
            "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
            ("/from_db2", 60001.0, "pending", time.time())
        )
        
        # Both should see both rows
        count1 = db1.query_val("SELECT COUNT(*) FROM ms_index")
        count2 = db2.query_val("SELECT COUNT(*) FROM ms_index")
        
        assert count1 == 2
        assert count2 == 2
        
        db1.close()
        db2.close()

"""
Contract tests for database operations.

These tests verify the ACTUAL database schema and operations work correctly
against the unified pipeline.sqlite3 database.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
import time
import re

from dsa110_contimg.database.unified import Database, UNIFIED_SCHEMA


class TestUnifiedSchemaContract:
    """Contract tests verifying the unified schema structure."""

    def test_schema_creates_all_required_tables(self, test_pipeline_db):
        """Verify UNIFIED_SCHEMA creates all expected tables."""
        db = test_pipeline_db
        
        # Query for all tables
        tables = db.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = {t['name'] for t in tables}
        
        schema_tables = {
            match.group(1)
            for match in re.finditer(
                r"CREATE TABLE IF NOT EXISTS\s+([a-zA-Z0-9_]+)", UNIFIED_SCHEMA
            )
        }
        required_tables = schema_tables
       
        missing = required_tables - table_names
        assert not missing, f"Missing tables: {missing}"

    def test_ms_index_schema(self, test_pipeline_db):
        """Verify ms_index table has correct columns."""
        db = test_pipeline_db
        
        # Get column info
        cursor = db.conn.execute("PRAGMA table_info(ms_index)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Required columns from UNIFIED_SCHEMA
        required_columns = {
            'path': 'TEXT',
            'start_mjd': 'REAL',
            'end_mjd': 'REAL', 
            'mid_mjd': 'REAL',
            'status': 'TEXT',
            'stage': 'TEXT',
            'dec_deg': 'REAL',
            'ra_deg': 'REAL',
            'group_id': 'TEXT',
            'created_at': 'REAL',
        }
        
        for col_name, col_type in required_columns.items():
            assert col_name in columns, f"Missing column: {col_name}"
            assert columns[col_name] == col_type, \
                f"Column {col_name} has type {columns[col_name]}, expected {col_type}"

    def test_images_schema(self, test_pipeline_db):
        """Verify images table has correct columns."""
        db = test_pipeline_db
        
        cursor = db.conn.execute("PRAGMA table_info(images)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Required columns from actual UNIFIED_SCHEMA
        required_columns = {
            'id': 'INTEGER',
            'path': 'TEXT',
            'ms_path': 'TEXT',
            'created_at': 'REAL',
            'type': 'TEXT',
            'format': 'TEXT',
            'beam_major_arcsec': 'REAL',
            'beam_minor_arcsec': 'REAL',
            'beam_pa_deg': 'REAL',
            'noise_jy': 'REAL',
            'dynamic_range': 'REAL',
            'pbcor': 'INTEGER',
            'field_name': 'TEXT',
            'center_ra_deg': 'REAL',
            'center_dec_deg': 'REAL',
            'imsize_x': 'INTEGER',
            'imsize_y': 'INTEGER',
            'cellsize_arcsec': 'REAL',
            'freq_ghz': 'REAL',
            'bandwidth_mhz': 'REAL',
            'integration_sec': 'REAL',
        }
        
        for col_name, col_type in required_columns.items():
            assert col_name in columns, f"Missing column: {col_name}"
            assert columns[col_name] == col_type, \
                f"Column {col_name} has type {columns[col_name]}, expected {col_type}"


class TestMSIndexOperations:
    """Contract tests for MS index CRUD operations."""

    def test_insert_and_query_ms_record(self, test_pipeline_db):
        """Verify we can insert and retrieve MS records."""
        db = test_pipeline_db
        
        # Insert a record
        ms_path = "/stage/dsa110-contimg/ms/2025-01-01T00:00:00.ms"
        now = time.time()
        
        db.execute(
            """INSERT INTO ms_index 
               (path, start_mjd, end_mjd, mid_mjd, status, stage, dec_deg, ra_deg, group_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ms_path, 60676.0, 60676.01, 60676.005, 'completed', 'imaged', 55.0, 180.0, 'grp_001', now)
        )
        
        # Query it back
        results = db.query("SELECT * FROM ms_index WHERE path = ?", (ms_path,))
        
        assert len(results) == 1
        record = results[0]
        assert record['path'] == ms_path
        assert record['mid_mjd'] == 60676.005
        assert record['status'] == 'completed'
        assert record['stage'] == 'imaged'
        assert record['dec_deg'] == 55.0

    def test_update_ms_status(self, test_pipeline_db):
        """Verify we can update MS status correctly."""
        db = test_pipeline_db
        
        ms_path = "/stage/dsa110-contimg/ms/update_test.ms"
        now = time.time()
        
        # Insert initial record
        db.execute(
            """INSERT INTO ms_index 
               (path, start_mjd, end_mjd, mid_mjd, status, stage, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ms_path, 60676.0, 60676.01, 60676.005, 'pending', 'converted', now)
        )
        
        # Update status
        rows_affected = db.execute(
            "UPDATE ms_index SET status = ?, stage = ? WHERE path = ?",
            ('completed', 'calibrated', ms_path)
        )
        
        assert rows_affected == 1
        
        # Verify update
        results = db.query("SELECT status, stage FROM ms_index WHERE path = ?", (ms_path,))
        assert results[0]['status'] == 'completed'
        assert results[0]['stage'] == 'calibrated'

    def test_unique_path_constraint(self, test_pipeline_db):
        """Verify path uniqueness is enforced."""
        db = test_pipeline_db
        
        ms_path = "/stage/dsa110-contimg/ms/unique_test.ms"
        now = time.time()
        
        # Insert first record
        db.execute(
            """INSERT INTO ms_index 
               (path, start_mjd, end_mjd, mid_mjd, status, stage, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ms_path, 60676.0, 60676.01, 60676.005, 'pending', 'converted', now)
        )
        
        # Attempt duplicate insert should fail
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO ms_index 
                   (path, start_mjd, end_mjd, mid_mjd, status, stage, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ms_path, 60677.0, 60677.01, 60677.005, 'pending', 'converted', now)
            )


class TestImagesOperations:
    """Contract tests for images table operations."""
    
    IMAGE_INSERT_COLUMNS = (
        "path",
        "ms_path",
        "created_at",
        "type",
        "format",
        "noise_jy",
        "imsize_x",
        "imsize_y",
        "cellsize_arcsec",
    )

    def test_insert_and_query_image(self, test_pipeline_db):
        """Verify we can insert and retrieve image records."""
        db = test_pipeline_db
        
        # First insert an MS record (foreign key reference)
        ms_path = "/stage/dsa110-contimg/ms/for_image.ms"
        now = time.time()
        db.execute(
            """INSERT INTO ms_index 
               (path, start_mjd, end_mjd, mid_mjd, status, stage, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ms_path, 60676.0, 60676.01, 60676.005, 'completed', 'imaged', now)
        )
        
        # Insert image record (using correct schema columns)
        img_path = "/stage/dsa110-contimg/images/for_image.fits"
        db.execute(
            f"""INSERT INTO images 
                ({', '.join(self.IMAGE_INSERT_COLUMNS)})
                VALUES ({', '.join('?' for _ in self.IMAGE_INSERT_COLUMNS)})""",
            (img_path, ms_path, now, 'dirty', 'fits', 0.001, 4096, 4096, 1.5)
        )
        
        # Query it back
        results = db.query("SELECT * FROM images WHERE path = ?", (img_path,))
        
        assert len(results) == 1
        record = results[0]
        assert record['path'] == img_path
        assert record['ms_path'] == ms_path
        assert record['type'] == 'dirty'
        assert record['noise_jy'] == 0.001

    def test_join_images_with_ms_index(self, test_pipeline_db):
        """Verify we can join images with ms_index."""
        db = test_pipeline_db
        
        # Insert MS and image
        ms_path = "/stage/dsa110-contimg/ms/join_test.ms"
        img_path = "/stage/dsa110-contimg/images/join_test.fits"
        now = time.time()
        
        db.execute(
            """INSERT INTO ms_index 
               (path, start_mjd, end_mjd, mid_mjd, status, stage, dec_deg, ra_deg, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ms_path, 60676.0, 60676.01, 60676.005, 'completed', 'imaged', 55.0, 180.0, now)
        )
        
        db.execute(
            f"""INSERT INTO images 
                ({', '.join(self.IMAGE_INSERT_COLUMNS)})
                VALUES ({', '.join('?' for _ in self.IMAGE_INSERT_COLUMNS)})""",
            (img_path, ms_path, now, 'dirty', 'FITS', 0.001, 2048, 2048, 2.0)
        )
        
        # Join query
        results = db.query(
            """SELECT i.path as img_path, i.type, i.noise_jy,
                      m.path as ms_path, m.dec_deg, m.ra_deg
               FROM images i
               JOIN ms_index m ON i.ms_path = m.path
               WHERE i.path = ?""",
            (img_path,)
        )
        
        assert len(results) == 1
        record = results[0]
        assert record['img_path'] == img_path
        assert record['ms_path'] == ms_path
        assert record['dec_deg'] == 55.0
        assert record['noise_jy'] == 0.001


class TestCalibrationOperations:
    """Contract tests for calibration table operations."""

    def test_insert_calibration_table(self, test_pipeline_db):
        """Verify we can insert calibration table records."""
        db = test_pipeline_db
        
        cal_path = "/stage/dsa110-contimg/caltables/bandpass.bcal"
        now = time.time()
        
        # Use the unified schema column list to avoid drift
        cal_columns = (
            "set_name",
            "path",
            "table_type",
            "order_index",
            "cal_field",
            "refant",
            "created_at",
            "valid_start_mjd",
            "valid_end_mjd",
            "status",
            "source_ms_path",
            "solver_command",
            "solver_version",
            "solver_params",
            "quality_metrics",
            "notes",
        )
        cal_values = (
            "cal_set_001",
            cal_path,
            "bandpass",
            0,
            "3C286",
            "ea01",
            now,
            60676.0,
            60677.0,
            "active",
            "/stage/dsa110-contimg/ms/bandpass.ms",
            "gaincal",
            "1.9.0",
            "solint=int,combine=scan",
            '{"snr": 42.0}',
            "contract test insert",
        )
        db.execute(
            f"""INSERT INTO caltables 
                ({', '.join(cal_columns)})
                VALUES ({', '.join('?' for _ in cal_columns)})""",
            cal_values,
        )
        
        results = db.query("SELECT * FROM caltables WHERE path = ?", (cal_path,))
        
        assert len(results) == 1
        record = results[0]
        assert record['table_type'] == 'bandpass'
        assert record['cal_field'] == '3C286'
        assert record['refant'] == 'ea01'
        assert record['source_ms_path'] == '/stage/dsa110-contimg/ms/bandpass.ms'
        assert record['status'] == 'active'


class TestProcessingQueueOperations:
    """Contract tests for processing queue operations."""

    def test_queue_lifecycle(self, test_pipeline_db):
        """Verify queue state transitions work correctly."""
        db = test_pipeline_db
        
        group_id = "grp_test_001"
        now = time.time()
        
        # Insert new queue entry (collecting state) with schema-accurate columns
        queue_columns = (
            "group_id",
            "state",
            "expected_subbands",
            "received_at",
            "last_update",
            "processing_stage",
        )
        queue_values = (
            group_id,
            "collecting",
            16,
            now,
            now,
            "collecting",
        )
        db.execute(
            f"""INSERT INTO processing_queue 
                ({', '.join(queue_columns)})
                VALUES ({', '.join('?' for _ in queue_columns)})""",
            queue_values,
        )
        
        # Transition to pending
        db.execute(
            "UPDATE processing_queue SET state = ?, processing_stage = ?, last_update = ? WHERE group_id = ?",
            ('pending', 'pending', now + 1, group_id)
        )
        
        # Transition to in_progress
        db.execute(
            "UPDATE processing_queue SET state = ?, processing_stage = ?, last_update = ? WHERE group_id = ?",
            ('in_progress', 'converting', now + 2, group_id)
        )
        
        # Complete
        db.execute(
            "UPDATE processing_queue SET state = ?, processing_stage = ?, last_update = ? WHERE group_id = ?",
            ('completed', 'completed', now + 10, group_id)
        )
        
        # Verify final state
        results = db.query("SELECT * FROM processing_queue WHERE group_id = ?", (group_id,))
        assert len(results) == 1
        assert results[0]['state'] == 'completed'
        assert results[0]['expected_subbands'] == 16
        assert results[0]['processing_stage'] == 'completed'


class TestPerformanceMetrics:
    """Contract tests for performance metrics tracking."""

    def test_record_performance_metrics(self, test_pipeline_db):
        """Verify we can record and query performance metrics."""
        db = test_pipeline_db
        
        group_id = "grp_perf_001"
        now = time.time()
        
        # First insert a processing_queue entry (foreign key)
        db.execute(
            """INSERT INTO processing_queue 
               (group_id, state, received_at, last_update)
               VALUES (?, ?, ?, ?)""",
            (group_id, 'completed', now, now)
        )
        
        metrics_columns = (
            "group_id",
            "load_time",
            "phase_time",
            "write_time",
            "total_time",
            "writer_type",
            "recorded_at",
        )
        metrics_values = (
            group_id,
            30.2,
            15.1,
            75.2,
            120.5,
            "direct-subband",
            now,
        )
        
        # Insert performance metrics using the real schema column names
        db.execute(
            f"""INSERT INTO performance_metrics 
                ({', '.join(metrics_columns)})
                VALUES ({', '.join('?' for _ in metrics_columns)})""",
            metrics_values,
        )
        
        select_columns = (
            "group_id",
            "total_time",
            "load_time",
            "phase_time",
            "write_time",
            "writer_type",
            "recorded_at",
        )
        results = db.query(
            f"SELECT {', '.join(select_columns)} FROM performance_metrics WHERE group_id = ?", 
            (group_id,)
        )
        
        assert len(results) == 1
        assert results[0]['total_time'] == 120.5
        assert results[0]['load_time'] == 30.2
        assert results[0]['phase_time'] == 15.1
        assert results[0]['write_time'] == 75.2
        assert results[0]['writer_type'] == 'direct-subband'


class TestDatabaseClassContract:
    """Contract tests for the Database class API."""

    def test_database_context_manager(self, tmp_path):
        """Verify Database works as context manager."""
        db_path = tmp_path / "test_context.sqlite3"
        
        with Database(db_path) as db:
            db.execute_script(UNIFIED_SCHEMA)
            db.execute(
                """INSERT INTO ms_index 
                   (path, start_mjd, end_mjd, mid_mjd, status, stage, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("/test/path.ms", 60676.0, 60676.01, 60676.005, 'pending', 'converted', time.time())
            )
            results = db.query("SELECT COUNT(*) as cnt FROM ms_index")
            assert results[0]['cnt'] == 1
        
        # Verify connection is closed after context
        # Re-opening should work fine
        with Database(db_path) as db:
            results = db.query("SELECT COUNT(*) as cnt FROM ms_index")
            assert results[0]['cnt'] == 1

    def test_query_returns_list_of_dicts(self, test_pipeline_db):
        """Verify query returns list of dictionaries."""
        db = test_pipeline_db
        
        # Insert some data
        for i in range(3):
            db.execute(
                """INSERT INTO ms_index 
                   (path, start_mjd, end_mjd, mid_mjd, status, stage, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"/test/path_{i}.ms", 60676.0 + i, 60676.01 + i, 60676.005 + i, 
                 'pending', 'converted', time.time())
            )
        
        results = db.query("SELECT path, status FROM ms_index ORDER BY path")
        
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)
        assert all('path' in r and 'status' in r for r in results)

    def test_execute_returns_rowcount(self, test_pipeline_db):
        """Verify execute returns affected row count."""
        db = test_pipeline_db
        
        # Insert records
        for i in range(5):
            db.execute(
                """INSERT INTO ms_index 
                   (path, start_mjd, end_mjd, mid_mjd, status, stage, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"/test/rowcount_{i}.ms", 60676.0, 60676.01, 60676.005, 
                 'pending', 'converted', time.time())
            )
        
        # Update multiple rows
        rows_affected = db.execute(
            "UPDATE ms_index SET status = ? WHERE status = ?",
            ('completed', 'pending')
        )
        
        assert rows_affected == 5

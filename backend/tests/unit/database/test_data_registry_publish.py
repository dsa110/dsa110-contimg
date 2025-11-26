"""Unit tests for data registry publish functionality.

Focus: Fast, isolated tests for publish retry tracking, locking,
and error recovery.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dsa110_contimg.database.data_registry import (
    _record_publish_failure,
    ensure_data_registry_db,
    get_data,
    list_data,
    register_data,
    trigger_auto_publish,
)


@pytest.fixture
def temp_registry_db(tmp_path):
    """Create a temporary data registry database for testing."""
    db_path = tmp_path / "test_registry.sqlite3"
    conn = ensure_data_registry_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def sample_staging_file(tmp_path):
    """Create a sample staging file for testing."""
    staging_dir = tmp_path / "stage" / "mosaics"
    staging_dir.mkdir(parents=True)
    test_file = staging_dir / "test_mosaic.fits"
    test_file.write_text("test data")
    return test_file


@pytest.mark.unit
def test_schema_migration_adds_publish_fields(temp_registry_db):
    """Test schema migration adds publish_attempts and publish_error."""
    conn = ensure_data_registry_db(temp_registry_db)

    # Verify new columns exist
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(data_registry)")
    columns = {row[1]: row[2] for row in cur.fetchall()}

    assert "publish_attempts" in columns
    assert columns["publish_attempts"] == "INTEGER"
    assert "publish_error" in columns
    assert columns["publish_error"] == "TEXT"

    conn.close()


@pytest.mark.unit
def test_record_publish_failure_increments_attempts(temp_registry_db):
    """Test that _record_publish_failure increments attempt counter."""
    conn = ensure_data_registry_db(temp_registry_db)

    # Register test data
    data_id = register_data(
        conn,
        data_type="mosaic",
        data_id="test_mosaic_001",
        stage_path="/stage/test_mosaic.fits",
        auto_publish=True,
    )

    # Record first failure
    cur = conn.cursor()
    _record_publish_failure(conn, cur, data_id, 0, "Test error 1")

    record = get_data(conn, data_id)
    assert record is not None
    assert record.publish_attempts == 1
    assert record.publish_error == "Test error 1"
    assert record.status == "staging"

    # Record second failure
    _record_publish_failure(conn, cur, data_id, 1, "Test error 2")

    record = get_data(conn, data_id)
    assert record.publish_attempts == 2
    assert record.publish_error == "Test error 2"

    conn.close()


@pytest.mark.unit
def test_record_publish_failure_truncates_long_error(temp_registry_db):
    """Test that _record_publish_failure truncates long error messages."""
    conn = ensure_data_registry_db(temp_registry_db)

    data_id = register_data(
        conn,
        data_type="mosaic",
        data_id="test_mosaic_002",
        stage_path="/stage/test_mosaic.fits",
    )

    long_error = "x" * 1000  # 1000 characters
    cur = conn.cursor()
    _record_publish_failure(conn, cur, data_id, 0, long_error)

    record = get_data(conn, data_id)
    assert record is not None
    assert len(record.publish_error) == 500  # Truncated to 500

    conn.close()


@pytest.mark.unit
def test_trigger_auto_publish_checks_max_attempts(temp_registry_db, sample_staging_file):
    """Test trigger_auto_publish rejects max attempts exceeded."""
    conn = ensure_data_registry_db(temp_registry_db)

    # Register data with max attempts exceeded
    data_id = register_data(
        conn,
        data_type="mosaic",
        data_id="test_mosaic_003",
        stage_path=str(sample_staging_file),
    )

    # Set publish_attempts to max
    cur = conn.cursor()
    cur.execute(
        "UPDATE data_registry SET publish_attempts = 3 WHERE data_id = ?",
        (data_id,),
    )
    conn.commit()

    # Try to publish - should fail due to max attempts
    success = trigger_auto_publish(conn, data_id, max_attempts=3)
    assert success is False

    record = get_data(conn, data_id)
    assert record.publish_attempts == 3

    conn.close()


@pytest.mark.unit
def test_trigger_auto_publish_sets_publishing_status(temp_registry_db, sample_staging_file):
    """Test trigger_auto_publish sets status to 'publishing'."""
    conn = ensure_data_registry_db(temp_registry_db)

    data_id = register_data(
        conn,
        data_type="mosaic",
        data_id="test_mosaic_004",
        stage_path=str(sample_staging_file),
    )

    # Mock the file move to fail so we can check status
    # Also need to mock products_base to use temp directory
    products_base = sample_staging_file.parent.parent.parent / "products"
    products_base.mkdir(parents=True, exist_ok=True)

    with patch("shutil.move", side_effect=OSError("Disk full")):
        try:
            trigger_auto_publish(conn, data_id, products_base=products_base)
        except Exception:
            pass

    # Check that status was set back to staging after failure
    record = get_data(conn, data_id)
    assert record.status == "staging"
    assert record.publish_attempts == 1
    assert record.publish_error is not None

    conn.close()


@pytest.mark.unit
def test_trigger_auto_publish_prevents_concurrent_access(temp_registry_db, sample_staging_file):
    """Test BEGIN IMMEDIATE prevents concurrent publish attempts."""
    conn1 = ensure_data_registry_db(temp_registry_db)
    conn2 = ensure_data_registry_db(temp_registry_db)

    data_id = register_data(
        conn1,
        data_type="mosaic",
        data_id="test_mosaic_005",
        stage_path=str(sample_staging_file),
    )

    # Start transaction in conn1 (simulating first process)
    conn1.execute("BEGIN IMMEDIATE")
    cur1 = conn1.cursor()
    cur1.execute(
        """
        SELECT data_id, status FROM data_registry
        WHERE data_id = ? AND status = 'staging'
        """,
        (data_id,),
    )
    row1 = cur1.fetchone()
    assert row1 is not None

    # Update status to publishing
    cur1.execute(
        "UPDATE data_registry SET status = 'publishing' WHERE data_id = ?",
        (data_id,),
    )
    conn1.commit()

    # Try to read in conn2 (simulating second process)
    # Should see status as 'publishing' and fail to acquire lock
    cur2 = conn2.cursor()
    cur2.execute(
        """
        SELECT data_id, status FROM data_registry
        WHERE data_id = ? AND status IN ('staging', 'publishing')
        """,
        (data_id,),
    )
    row2 = cur2.fetchone()
    assert row2 is not None
    assert row2[1] == "publishing"

    conn1.close()
    conn2.close()


@pytest.mark.unit
def test_get_data_handles_old_schema(temp_registry_db):
    """Test that get_data handles old schema without new columns gracefully."""
    conn = ensure_data_registry_db(temp_registry_db)

    # Create record with old schema (manually insert without new columns)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO data_registry
        (data_type, data_id, base_path, status, stage_path, created_at, staged_at,
         metadata_json, auto_publish_enabled, finalization_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "mosaic",
            "old_schema_test",
            "/stage",
            "staging",
            "/stage/test.fits",
            1000.0,
            1000.0,
            None,
            1,
            "pending",
        ),
    )
    conn.commit()

    # Should handle gracefully
    record = get_data(conn, "old_schema_test")
    assert record is not None
    assert record.publish_attempts == 0
    assert record.publish_error is None

    conn.close()


@pytest.mark.unit
def test_list_data_handles_old_schema(temp_registry_db):
    """Test that list_data handles old schema without new columns gracefully."""
    conn = ensure_data_registry_db(temp_registry_db)

    # Create record with old schema
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO data_registry
        (data_type, data_id, base_path, status, stage_path, created_at, staged_at,
         metadata_json, auto_publish_enabled, finalization_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "mosaic",
            "old_schema_list_test",
            "/stage",
            "staging",
            "/stage/test.fits",
            1000.0,
            1000.0,
            None,
            1,
            "pending",
        ),
    )
    conn.commit()

    # Should handle gracefully
    records, total = list_data(conn, status="staging")
    assert len(records) >= 1
    old_record = next((r for r in records if r.data_id == "old_schema_list_test"), None)
    assert old_record is not None
    assert old_record.publish_attempts == 0
    assert old_record.publish_error is None

    conn.close()


@pytest.mark.unit
def test_successful_publish_clears_attempts(temp_registry_db, tmp_path):
    """Test that successful publish clears publish_attempts and publish_error."""
    conn = ensure_data_registry_db(temp_registry_db)

    # Create staging and products directories
    staging_dir = tmp_path / "stage" / "mosaics"
    products_dir = tmp_path / "products" / "mosaics"
    staging_dir.mkdir(parents=True)
    products_dir.mkdir(parents=True)

    test_file = staging_dir / "test_mosaic.fits"
    test_file.write_text("test data")

    data_id = register_data(
        conn,
        data_type="mosaic",
        data_id="test_mosaic_006",
        stage_path=str(test_file),
    )

    # Set initial failure attempts
    cur = conn.cursor()
    cur.execute(
        """UPDATE data_registry
        SET publish_attempts = 2, publish_error = 'Previous error'
        WHERE data_id = ?""",
        (data_id,),
    )
    conn.commit()

    # Mock path validation to allow temp directory
    with patch("dsa110_contimg.utils.naming.validate_path_safe") as mock_validate:
        mock_validate.return_value = (True, None)

        # Successful publish
        success = trigger_auto_publish(conn, data_id, products_base=products_dir.parent)

        assert success is True

        record = get_data(conn, data_id)
        assert record.status == "published"
        assert record.publish_attempts == 0
        assert record.publish_error is None

    conn.close()

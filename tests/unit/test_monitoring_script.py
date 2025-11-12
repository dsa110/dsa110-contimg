"""Unit tests for monitoring script functions.

Focus: Fast, isolated tests for monitoring script core functions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Import monitoring script functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from monitor_publish_status import (  # noqa: E402
    check_alerts,
    get_failed_publishes,
    get_publish_status,
    retry_all_failed,
    retry_failed_publish,
)


@pytest.fixture
def temp_registry_db(tmp_path):
    """Create temporary data registry database."""
    db_path = tmp_path / "test_registry.sqlite3"
    from dsa110_contimg.database.data_registry import (
        ensure_data_registry_db,
        register_data,
    )

    conn = ensure_data_registry_db(db_path)

    # Register test data
    register_data(
        conn,
        data_type="mosaic",
        data_id="test_mosaic_001",
        stage_path="/stage/test_mosaic_001.fits",
    )

    # Set publish attempts
    cur = conn.cursor()
    cur.execute(
        "UPDATE data_registry SET publish_attempts = 1, publish_error = 'Test error' WHERE data_id = 'test_mosaic_001'"
    )
    conn.commit()
    conn.close()

    return db_path


@pytest.mark.unit
def test_get_publish_status(temp_registry_db):
    """Test get_publish_status function."""
    status = get_publish_status(temp_registry_db)

    assert "total_published" in status
    assert "total_staging" in status
    assert "total_publishing" in status
    assert "failed_publishes" in status
    assert "max_attempts_exceeded" in status
    assert "success_rate_percent" in status

    assert isinstance(status["total_published"], int)
    assert isinstance(status["failed_publishes"], int)
    assert 0 <= status["success_rate_percent"] <= 100


@pytest.mark.unit
def test_get_failed_publishes(temp_registry_db):
    """Test get_failed_publishes function."""
    failed = get_failed_publishes(temp_registry_db)

    assert isinstance(failed, list)
    assert len(failed) >= 1

    # Check structure
    if failed:
        record = failed[0]
        assert hasattr(record, "data_id")
        assert hasattr(record, "publish_attempts")
        assert record.publish_attempts > 0


@pytest.mark.unit
def test_get_failed_publishes_with_max_attempts_filter(temp_registry_db):
    """Test get_failed_publishes with max_attempts filter."""
    # Get all failed
    all_failed = get_failed_publishes(temp_registry_db)

    # Get only max attempts
    max_attempts_failed = get_failed_publishes(temp_registry_db, max_attempts=3)

    assert len(max_attempts_failed) <= len(all_failed)


@pytest.mark.unit
def test_check_alerts_low_success_rate():
    """Test check_alerts with low success rate."""
    status = {
        "success_rate_percent": 90.0,
        "failed_publishes": 5,
        "max_attempts_exceeded": 0,
    }

    thresholds = {"min_success_rate": 95.0, "max_failed": 10}
    alerts = check_alerts(status, thresholds)

    assert len(alerts) > 0
    assert any("success rate" in alert.lower() for alert in alerts)


@pytest.mark.unit
def test_check_alerts_high_failed_count():
    """Test check_alerts with high failed count."""
    status = {
        "success_rate_percent": 95.0,
        "failed_publishes": 15,
        "max_attempts_exceeded": 0,
    }

    thresholds = {"min_success_rate": 95.0, "max_failed": 10}
    alerts = check_alerts(status, thresholds)

    assert len(alerts) > 0
    assert any("failed" in alert.lower() for alert in alerts)


@pytest.mark.unit
def test_check_alerts_max_attempts_exceeded():
    """Test check_alerts with max attempts exceeded."""
    status = {
        "success_rate_percent": 95.0,
        "failed_publishes": 5,
        "max_attempts_exceeded": 2,
    }

    thresholds = {"min_success_rate": 95.0, "max_failed": 10}
    alerts = check_alerts(status, thresholds)

    assert len(alerts) > 0
    assert any("max attempts" in alert.lower() for alert in alerts)


@pytest.mark.unit
def test_check_alerts_no_alerts():
    """Test check_alerts with no alert conditions."""
    status = {
        "success_rate_percent": 98.0,
        "failed_publishes": 2,
        "max_attempts_exceeded": 0,
    }

    thresholds = {"min_success_rate": 95.0, "max_failed": 10}
    alerts = check_alerts(status, thresholds)

    assert len(alerts) == 0


@pytest.mark.unit
def test_retry_failed_publish_dry_run(temp_registry_db):
    """Test retry_failed_publish in dry run mode."""
    success = retry_failed_publish(temp_registry_db, "test_mosaic_001", dry_run=True)

    assert success is True

    # Verify no changes in dry run
    from dsa110_contimg.database.data_registry import (  # noqa: E402
        ensure_data_registry_db,
        get_data,
    )

    conn = ensure_data_registry_db(temp_registry_db)
    record = get_data(conn, "test_mosaic_001")
    assert record.publish_attempts == 1  # Unchanged
    conn.close()


@pytest.mark.unit
def test_retry_all_failed_dry_run(temp_registry_db):
    """Test retry_all_failed in dry run mode."""
    results = retry_all_failed(temp_registry_db, limit=10, dry_run=True)

    assert "total" in results
    assert "successful" in results
    assert "failed" in results
    assert results["successful"] == 0  # Dry run doesn't actually retry
    assert results["failed"] == 0


@pytest.mark.unit
def test_retry_all_failed_with_limit(temp_registry_db):
    """Test retry_all_failed respects limit parameter."""
    # Create more failed publishes
    from dsa110_contimg.database.data_registry import (
        ensure_data_registry_db,
        register_data,
    )

    conn = ensure_data_registry_db(temp_registry_db)
    for i in range(5):
        register_data(
            conn,
            data_type="mosaic",
            data_id=f"test_mosaic_{i+2}",
            stage_path=f"/stage/test_mosaic_{i+2}.fits",
        )
        cur = conn.cursor()
        cur.execute(
            f"UPDATE data_registry SET publish_attempts = 1 WHERE data_id = 'test_mosaic_{i+2}'"
        )
    conn.commit()
    conn.close()

    # Retry with limit
    results = retry_all_failed(temp_registry_db, limit=3, dry_run=True)
    assert results["total"] == 3  # Limited to 3

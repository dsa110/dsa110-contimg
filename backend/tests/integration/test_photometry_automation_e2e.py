"""End-to-end integration tests for photometry automation."""

import pytest

from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db,
    get_photometry_status,
    link_photometry_to_data,
    update_photometry_status,
)


class TestPhotometryAutomationE2E:
    """End-to-end tests for complete photometry automation workflows."""

    @pytest.fixture
    def temp_registry_db(self, tmp_path):
        """Create temporary data registry database."""
        db_path = tmp_path / "data_registry.sqlite3"
        conn = ensure_data_registry_db(db_path)
        # Register a test data product
        conn.execute(
            """
            INSERT INTO data_registry
            (data_type, data_id, base_path, status, stage_path, created_at, staged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "image",
                "test_image",
                str(tmp_path),
                "staging",
                str(tmp_path / "test.fits"),
                1000.0,
                1000.0,
            ),
        )
        conn.commit()
        conn.close()
        return db_path

    def test_data_registry_photometry_linking(self, temp_registry_db):
        """Test linking photometry job to data registry."""
        conn = ensure_data_registry_db(temp_registry_db)

        # Link photometry job
        success = link_photometry_to_data(conn, "test_image", "job_123")
        assert success is True

        # Verify status
        status = get_photometry_status(conn, "test_image")
        assert status is not None
        assert status["status"] == "pending"
        assert status["job_id"] == "job_123"

        conn.close()

    def test_photometry_status_updates(self, temp_registry_db):
        """Test updating photometry status through workflow."""
        conn = ensure_data_registry_db(temp_registry_db)

        # Initial state: pending
        update_photometry_status(conn, "test_image", "pending", "job_123")
        status = get_photometry_status(conn, "test_image")
        assert status["status"] == "pending"

        # Update to running
        update_photometry_status(conn, "test_image", "running", "job_123")
        status = get_photometry_status(conn, "test_image")
        assert status["status"] == "running"

        # Update to completed
        update_photometry_status(conn, "test_image", "completed", "job_123")
        status = get_photometry_status(conn, "test_image")
        assert status["status"] == "completed"

        conn.close()

    def test_photometry_status_nonexistent_data_id(self, temp_registry_db):
        """Test that updating status for nonexistent data_id returns False."""
        conn = ensure_data_registry_db(temp_registry_db)

        success = update_photometry_status(conn, "nonexistent", "pending", "job_123")
        assert success is False

        status = get_photometry_status(conn, "nonexistent")
        assert status is None

        conn.close()

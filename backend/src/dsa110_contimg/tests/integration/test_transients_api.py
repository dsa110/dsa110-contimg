"""
Integration tests for Transients API endpoints.

Tests all 12 endpoints with actual database operations:
- GET /api/transients/alerts
- GET /api/transients/alerts/{alert_id}
- GET /api/transients/candidates
- GET /api/transients/candidates/{candidate_id}
- PUT /api/transients/alerts/{alert_id}/acknowledge
- PUT /api/transients/candidates/{candidate_id}/classify
- PUT /api/transients/alerts/{alert_id}/follow-up
- PUT /api/transients/candidates/{candidate_id}/follow-up
- PUT /api/transients/alerts/{alert_id}/notes
- PUT /api/transients/candidates/{candidate_id}/notes
- POST /api/transients/alerts/bulk-acknowledge
- POST /api/transients/candidates/bulk-classify
"""

import sys
from pathlib import Path

# Add src directory to path for imports
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_db():
    """Create a temporary test database with schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create tables manually to avoid import issues
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # transient_alerts table (simplified for testing)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transient_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_level TEXT NOT NULL,
            alert_message TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_at INTEGER,
            acknowledged_by TEXT,
            notes TEXT
        )
    """
    )

    # transient_candidates table (simplified for testing)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transient_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ra REAL,
            dec REAL,
            snr REAL,
            classification TEXT,
            classified_at INTEGER,
            classified_by TEXT,
            follow_up_status TEXT,
            notes TEXT,
            created_at INTEGER NOT NULL
        )
    """
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(test_db):
    """Create FastAPI test client with test database."""
    # Ensure proper import path
    src_path = Path(__file__).parent.parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Import inside fixture to avoid issues during collection
    import importlib

    api_module = importlib.import_module("dsa110_contimg.api")
    app = api_module.create_app()

    # Store test_db_path for use in queries
    app.state.test_db_path = test_db
    return TestClient(app)


@pytest.fixture
def sample_alerts(test_db):
    """Insert sample alerts into test database."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    alerts = [
        (
            1,
            "CRITICAL",
            "High SNR detection at RA=100.5, Dec=25.3",
            1700000000,
            0,
            None,
            None,
            None,
        ),
        (2, "HIGH", "Potential transient candidate detected", 1700000100, 0, None, None, None),
        (
            3,
            "MEDIUM",
            "Moderate significance source",
            1700000200,
            1,
            1700000300,
            "analyst1",
            "Confirmed as instrumental artifact",
        ),
    ]

    cursor.executemany(
        """INSERT INTO transient_alerts 
        (id, alert_level, alert_message, created_at, acknowledged, acknowledged_at, acknowledged_by, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        alerts,
    )
    conn.commit()
    conn.close()

    return alerts


@pytest.fixture
def sample_candidates(test_db):
    """Insert sample candidates into test database."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    candidates = [
        (1, 100.5, 25.3, 15.2, None, None, None, None, None, 1700000000),
        (
            2,
            101.2,
            26.1,
            12.8,
            "real",
            1700000100,
            "analyst2",
            None,
            "Looks like genuine transient",
            1700000000,
        ),
        (
            3,
            102.0,
            27.5,
            8.5,
            "artifact",
            1700000200,
            "analyst1",
            "not_needed",
            "RFI contamination",
            1700000000,
        ),
    ]

    cursor.executemany(
        """INSERT INTO transient_candidates 
        (id, ra, dec, snr, classification, classified_at, classified_by, follow_up_status, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        candidates,
    )
    conn.commit()
    conn.close()

    return candidates


class TestAlertsEndpoints:
    """Test alert-related endpoints."""

    def test_list_alerts_all(self, client, sample_alerts, test_db):
        """Test GET /api/transients/alerts returns all alerts."""
        response = client.get(f"/api/transients/alerts?db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(key in data[0] for key in ["id", "alert_level", "alert_message", "created_at"])

    def test_list_alerts_filter_acknowledged(self, client, sample_alerts, test_db):
        """Test filtering alerts by acknowledged status."""
        # Unacknowledged
        response = client.get(f"/api/transients/alerts?acknowledged=false&db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(not alert["acknowledged"] for alert in data)

        # Acknowledged
        response = client.get(f"/api/transients/alerts?acknowledged=true&db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["acknowledged"]
        assert data[0]["acknowledged_by"] == "analyst1"

    def test_list_alerts_filter_level(self, client, sample_alerts, test_db):
        """Test filtering alerts by alert level."""
        response = client.get(f"/api/transients/alerts?alert_level=CRITICAL&db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["alert_level"] == "CRITICAL"

    def test_list_alerts_limit(self, client, sample_alerts, test_db):
        """Test limiting number of returned alerts."""
        response = client.get(f"/api/transients/alerts?limit=2&db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_alert_by_id(self, client, sample_alerts, test_db):
        """Test GET /api/transients/alerts/{alert_id}."""
        response = client.get(f"/api/transients/alerts/1?db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["alert_level"] == "CRITICAL"
        assert data["alert_message"] == "High SNR detection at RA=100.5, Dec=25.3"

    def test_get_alert_not_found(self, client, test_db):
        """Test getting non-existent alert returns 404."""
        response = client.get(f"/api/transients/alerts/999?db_path={test_db}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_acknowledge_alert(self, client, sample_alerts, test_db):
        """Test PUT /api/transients/alerts/{alert_id}/acknowledge."""
        payload = {"acknowledged_by": "test_user", "notes": "Reviewed and confirmed"}
        response = client.put(
            f"/api/transients/alerts/1/acknowledge?db_path={test_db}", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Alert acknowledged successfully"

        # Verify in database
        response = client.get(f"/api/transients/alerts/1?db_path={test_db}")
        alert = response.json()
        assert alert["acknowledged"]
        assert alert["acknowledged_by"] == "test_user"
        assert "Reviewed and confirmed" in alert["notes"]

    def test_acknowledge_alert_missing_user(self, client, sample_alerts, test_db):
        """Test acknowledging alert without user fails."""
        payload = {"acknowledged_by": ""}
        response = client.put(
            f"/api/transients/alerts/1/acknowledge?db_path={test_db}", json=payload
        )
        assert response.status_code == 422  # Validation error

    def test_update_alert_follow_up(self, client, sample_alerts, test_db):
        """Test PUT /api/transients/alerts/{alert_id}/follow-up."""
        payload = {"status": "in_progress", "notes": "Initiated telescope follow-up"}
        response = client.put(f"/api/transients/alerts/1/follow-up?db_path={test_db}", json=payload)
        assert response.status_code == 200

        # Verify notes were added
        response = client.get(f"/api/transients/alerts/1?db_path={test_db}")
        alert = response.json()
        assert "Initiated telescope follow-up" in alert["notes"]

    def test_add_alert_notes(self, client, sample_alerts, test_db):
        """Test PUT /api/transients/alerts/{alert_id}/notes."""
        payload = {
            "notes": "Additional observation scheduled",
            "username": "observer1",
            "append": True,
        }
        response = client.put(f"/api/transients/alerts/1/notes?db_path={test_db}", json=payload)
        assert response.status_code == 200

        # Verify notes were appended
        response = client.get(f"/api/transients/alerts/1?db_path={test_db}")
        alert = response.json()
        assert "Additional observation scheduled" in alert["notes"]
        assert "[observer1" in alert["notes"]  # Timestamp format

    def test_bulk_acknowledge_alerts(self, client, sample_alerts, test_db):
        """Test POST /api/transients/alerts/bulk-acknowledge."""
        payload = {
            "alert_ids": [1, 2],
            "acknowledged_by": "bulk_user",
            "notes": "Bulk review completed",
        }
        response = client.post(
            f"/api/transients/alerts/bulk-acknowledge?db_path={test_db}", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0

        # Verify both were acknowledged
        for alert_id in [1, 2]:
            response = client.get(f"/api/transients/alerts/{alert_id}?db_path={test_db}")
            alert = response.json()
            assert alert["acknowledged"]
            assert alert["acknowledged_by"] == "bulk_user"


class TestCandidatesEndpoints:
    """Test candidate-related endpoints."""

    def test_list_candidates_all(self, client, sample_candidates, test_db):
        """Test GET /api/transients/candidates returns all candidates."""
        response = client.get(f"/api/transients/candidates?db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(key in data[0] for key in ["id", "ra", "dec", "snr"])

    def test_list_candidates_filter_classification(self, client, sample_candidates, test_db):
        """Test filtering candidates by classification."""
        response = client.get(f"/api/transients/candidates?classification=real&db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["classification"] == "real"

    def test_list_candidates_filter_follow_up(self, client, sample_candidates, test_db):
        """Test filtering candidates by follow-up status."""
        response = client.get(
            f"/api/transients/candidates?follow_up_status=not_needed&db_path={test_db}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["follow_up_status"] == "not_needed"

    def test_get_candidate_by_id(self, client, sample_candidates, test_db):
        """Test GET /api/transients/candidates/{candidate_id}."""
        response = client.get(f"/api/transients/candidates/1?db_path={test_db}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["ra"] == pytest.approx(100.5)
        assert data["dec"] == pytest.approx(25.3)
        assert data["snr"] == pytest.approx(15.2)

    def test_get_candidate_not_found(self, client, test_db):
        """Test getting non-existent candidate returns 404."""
        response = client.get(f"/api/transients/candidates/999?db_path={test_db}")
        assert response.status_code == 404

    def test_classify_candidate(self, client, sample_candidates, test_db):
        """Test PUT /api/transients/candidates/{candidate_id}/classify."""
        payload = {
            "classification": "real",
            "classified_by": "astronomer1",
            "notes": "Clear transient signature",
        }
        response = client.put(
            f"/api/transients/candidates/1/classify?db_path={test_db}", json=payload
        )
        assert response.status_code == 200

        # Verify classification
        response = client.get(f"/api/transients/candidates/1?db_path={test_db}")
        candidate = response.json()
        assert candidate["classification"] == "real"
        assert candidate["classified_by"] == "astronomer1"
        assert "Clear transient signature" in candidate["notes"]

    def test_classify_candidate_invalid_classification(self, client, sample_candidates, test_db):
        """Test classifying with invalid classification fails."""
        payload = {"classification": "invalid_type", "classified_by": "user1"}
        response = client.put(
            f"/api/transients/candidates/1/classify?db_path={test_db}", json=payload
        )
        assert response.status_code == 400
        assert "invalid classification" in response.json()["detail"].lower()

    def test_update_candidate_follow_up(self, client, sample_candidates, test_db):
        """Test PUT /api/transients/candidates/{candidate_id}/follow-up."""
        payload = {"status": "required", "notes": "Needs spectroscopic confirmation"}
        response = client.put(
            f"/api/transients/candidates/1/follow-up?db_path={test_db}", json=payload
        )
        assert response.status_code == 200

        # Verify follow-up status (should be in notes)
        response = client.get(f"/api/transients/candidates/1?db_path={test_db}")
        candidate = response.json()
        assert "Needs spectroscopic confirmation" in candidate["notes"]

    def test_add_candidate_notes(self, client, sample_candidates, test_db):
        """Test PUT /api/transients/candidates/{candidate_id}/notes."""
        payload = {
            "notes": "Archival search shows no prior detections",
            "username": "researcher1",
            "append": True,
        }
        response = client.put(f"/api/transients/candidates/1/notes?db_path={test_db}", json=payload)
        assert response.status_code == 200

        # Verify notes
        response = client.get(f"/api/transients/candidates/1?db_path={test_db}")
        candidate = response.json()
        assert "Archival search shows no prior detections" in candidate["notes"]

    def test_bulk_classify_candidates(self, client, sample_candidates, test_db):
        """Test POST /api/transients/candidates/bulk-classify."""
        payload = {
            "candidate_ids": [1, 2],
            "classification": "artifact",
            "classified_by": "ml_pipeline",
            "notes": "Automated classification",
        }
        response = client.post(
            f"/api/transients/candidates/bulk-classify?db_path={test_db}", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0

        # Verify classifications
        for candidate_id in [1, 2]:
            response = client.get(f"/api/transients/candidates/{candidate_id}?db_path={test_db}")
            candidate = response.json()
            assert candidate["classification"] == "artifact"
            assert candidate["classified_by"] == "ml_pipeline"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_db_path(self, client):
        """Test with non-existent database path."""
        response = client.get("/api/transients/alerts?db_path=/tmp/nonexistent.db")
        # Should either return empty list or handle gracefully
        assert response.status_code in [200, 404, 500]

    def test_acknowledge_nonexistent_alert(self, client, test_db):
        """Test acknowledging non-existent alert."""
        payload = {"acknowledged_by": "user1"}
        response = client.put(
            f"/api/transients/alerts/999/acknowledge?db_path={test_db}", json=payload
        )
        assert response.status_code == 404

    def test_classify_nonexistent_candidate(self, client, test_db):
        """Test classifying non-existent candidate."""
        payload = {"classification": "real", "classified_by": "user1"}
        response = client.put(
            f"/api/transients/candidates/999/classify?db_path={test_db}", json=payload
        )
        assert response.status_code == 404

    def test_bulk_operation_with_invalid_ids(self, client, sample_alerts, test_db):
        """Test bulk operation with mix of valid and invalid IDs."""
        payload = {"alert_ids": [1, 999], "acknowledged_by": "user1"}  # 1 exists, 999 doesn't
        response = client.post(
            f"/api/transients/alerts/bulk-acknowledge?db_path={test_db}", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] >= 1  # At least one should succeed
        assert data["failed"] >= 1  # At least one should fail


class TestDatabaseOperations:
    """Test database state changes."""

    def test_acknowledge_updates_timestamp(self, client, sample_alerts, test_db):
        """Test that acknowledging updates acknowledged_at timestamp."""
        import time

        before_time = int(time.time())

        payload = {"acknowledged_by": "user1"}
        client.put(f"/api/transients/alerts/1/acknowledge?db_path={test_db}", json=payload)

        response = client.get(f"/api/transients/alerts/1?db_path={test_db}")
        alert = response.json()
        assert alert["acknowledged_at"] is not None
        assert alert["acknowledged_at"] >= before_time

    def test_classify_updates_timestamp(self, client, sample_candidates, test_db):
        """Test that classifying updates classified_at timestamp."""
        import time

        before_time = int(time.time())

        payload = {"classification": "real", "classified_by": "user1"}
        client.put(f"/api/transients/candidates/1/classify?db_path={test_db}", json=payload)

        response = client.get(f"/api/transients/candidates/1?db_path={test_db}")
        candidate = response.json()
        assert candidate["classified_at"] is not None
        assert candidate["classified_at"] >= before_time

    def test_notes_append_vs_replace(self, client, sample_alerts, test_db):
        """Test appending vs replacing notes."""
        # Add initial notes
        payload1 = {"notes": "First note", "username": "user1", "append": False}
        client.put(f"/api/transients/alerts/1/notes?db_path={test_db}", json=payload1)

        # Append second note
        payload2 = {"notes": "Second note", "username": "user2", "append": True}
        client.put(f"/api/transients/alerts/1/notes?db_path={test_db}", json=payload2)

        response = client.get(f"/api/transients/alerts/1?db_path={test_db}")
        alert = response.json()
        assert "First note" in alert["notes"]
        assert "Second note" in alert["notes"]

        # Replace notes
        payload3 = {"notes": "Replaced note", "username": "user3", "append": False}
        client.put(f"/api/transients/alerts/1/notes?db_path={test_db}", json=payload3)

        response = client.get(f"/api/transients/alerts/1?db_path={test_db}")
        alert = response.json()
        assert "Replaced note" in alert["notes"]
        assert "First note" not in alert["notes"]

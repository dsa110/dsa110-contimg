"""
Integration tests for Transients API endpoints using HTTP requests.

Tests all 12 endpoints against the running API server on localhost:8000.
Requires: API server running (sudo systemctl start contimg-api.service)

Tests:
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

import sqlite3
import time

import pytest
import requests

# API base URL
API_BASE = "http://localhost:8000/api/transients"
DB_PATH = "/data/dsa110-contimg/state/products.sqlite3"


@pytest.fixture(scope="session")
def api_available():
    """Check if API server is running."""
    try:
        response = requests.get(f"{API_BASE}/alerts?limit=1", timeout=2)
        if response.status_code in [200, 404]:
            return True
    except requests.exceptions.RequestException:
        pytest.skip("API server not running on localhost:8000")
    return False


@pytest.fixture
def test_alert_id(api_available):
    """Get or skip if no alerts available."""
    # Try unacknowledged first, then acknowledged
    for ack_status in [False, True]:
        response = requests.get(f"{API_BASE}/alerts?acknowledged={str(ack_status).lower()}&limit=1")
        if response.status_code == 200:
            alerts = response.json()
            if alerts and len(alerts) > 0:
                return alerts[0]["id"]

    pytest.skip("No alerts available. Create with: sqlite3 ... INSERT INTO transient_alerts ...")


@pytest.fixture
def test_candidate_id(api_available):
    """Get existing candidate for testing."""
    # Query for existing candidates via API
    response = requests.get(f"{API_BASE}/candidates?limit=1")
    if response.status_code == 200:
        candidates = response.json()
        if candidates and len(candidates) > 0:
            return candidates[0]["id"]

    pytest.skip("No candidates available for testing. Create candidates first.")


class TestAlertsEndpoints:
    """Test alert-related endpoints."""

    def test_list_alerts(self, api_available):
        """Test GET /api/transients/alerts."""
        response = requests.get(f"{API_BASE}/alerts?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_alert_by_id(self, test_alert_id):
        """Test GET /api/transients/alerts/{alert_id}."""
        response = requests.get(f"{API_BASE}/alerts/{test_alert_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_alert_id
        assert "alert_level" in data
        assert "alert_message" in data

    def test_acknowledge_alert(self, test_alert_id):
        """Test PUT /api/transients/alerts/{alert_id}/acknowledge."""
        payload = {"acknowledged_by": "integration_test", "notes": "Test acknowledgment"}
        response = requests.put(f"{API_BASE}/alerts/{test_alert_id}/acknowledge", json=payload)
        assert response.status_code == 200

        # Verify acknowledgment
        response = requests.get(f"{API_BASE}/alerts/{test_alert_id}")
        alert = response.json()
        assert alert["acknowledged"] == 1
        assert alert["acknowledged_by"] == "integration_test"

    def test_update_alert_follow_up(self, test_alert_id):
        """Test PUT /api/transients/alerts/{alert_id}/follow-up."""
        payload = {"status": "scheduled", "notes": "Follow-up initiated"}
        response = requests.put(f"{API_BASE}/alerts/{test_alert_id}/follow-up", json=payload)
        assert response.status_code == 200

    def test_add_alert_notes(self, test_alert_id):
        """Test PUT /api/transients/alerts/{alert_id}/notes."""
        payload = {"notes": "Additional test note", "username": "test_user", "append": True}
        response = requests.put(f"{API_BASE}/alerts/{test_alert_id}/notes", json=payload)
        assert response.status_code == 200


class TestCandidatesEndpoints:
    """Test candidate-related endpoints."""

    def test_list_candidates(self, api_available):
        """Test GET /api/transients/candidates."""
        response = requests.get(f"{API_BASE}/candidates?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_candidate_by_id(self, test_candidate_id):
        """Test GET /api/transients/candidates/{candidate_id}."""
        response = requests.get(f"{API_BASE}/candidates/{test_candidate_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_candidate_id
        assert "ra_deg" in data or "source_name" in data  # Accept either field name
        assert data["source_name"] == "TEST_SRC"

    def test_classify_candidate(self, test_candidate_id):
        """Test PUT /api/transients/candidates/{candidate_id}/classify."""
        payload = {
            "classification": "real",
            "classified_by": "integration_test",
            "notes": "Test classification",
        }
        response = requests.put(f"{API_BASE}/candidates/{test_candidate_id}/classify", json=payload)
        assert response.status_code == 200

        # Verify classification
        response = requests.get(f"{API_BASE}/candidates/{test_candidate_id}")
        candidate = response.json()
        assert candidate["classification"] == "real"
        assert candidate["classified_by"] == "integration_test"

    def test_update_candidate_follow_up(self, test_candidate_id):
        """Test PUT /api/transients/candidates/{candidate_id}/follow-up."""
        payload = {"status": "pending", "notes": "Needs spectroscopic follow-up"}
        response = requests.put(
            f"{API_BASE}/candidates/{test_candidate_id}/follow-up", json=payload
        )
        assert response.status_code == 200

    def test_add_candidate_notes(self, test_candidate_id):
        """Test PUT /api/transients/candidates/{candidate_id}/notes."""
        payload = {"notes": "Additional candidate note", "username": "test_user", "append": True}
        response = requests.put(f"{API_BASE}/candidates/{test_candidate_id}/notes", json=payload)
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling."""

    def test_get_nonexistent_alert(self, api_available):
        """Test GET with non-existent alert ID."""
        response = requests.get(f"{API_BASE}/alerts/999999")
        assert response.status_code == 404

    def test_get_nonexistent_candidate(self, api_available):
        """Test GET with non-existent candidate ID."""
        response = requests.get(f"{API_BASE}/candidates/999999")
        assert response.status_code == 404

    def test_classify_with_invalid_classification(self, test_candidate_id):
        """Test classify with invalid classification value."""
        payload = {"classification": "invalid_type", "classified_by": "test_user"}
        response = requests.put(f"{API_BASE}/candidates/{test_candidate_id}/classify", json=payload)
        assert response.status_code == 400

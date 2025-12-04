"""
Contract tests for Dashboard API endpoints.

Tests for saved queries, backup, triggers, jupyter, and vo_export routes.
Validates schemas and HTTP contracts.
"""

import json
import os
import pytest
from typing import Dict, Any

# Ensure test environment
os.environ.setdefault("DSA110_TEST_MODE", "1")
os.environ.setdefault("DSA110_AUTH_DISABLED", "true")
os.environ.setdefault("DSA110_ALLOWED_IPS", "127.0.0.1,::1,testclient")


# ============================================================================
# Test Client Fixture
# ============================================================================


@pytest.fixture(scope="module")
def api_client():
    """Create a FastAPI TestClient for API testing."""
    from fastapi.testclient import TestClient
    from dsa110_contimg.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_query() -> Dict[str, Any]:
    """Sample saved query payload."""
    return {
        "name": "Test Query",
        "description": "A test query for contract testing",
        "filters": json.dumps({"status": "completed", "min_snr": 10}),
        "target_type": "images",
        "visibility": "private",
    }


@pytest.fixture
def sample_trigger() -> Dict[str, Any]:
    """Sample trigger payload."""
    return {
        "name": "Test Trigger",
        "description": "Contract test trigger",
        "trigger_type": "schedule",
        "schedule": "0 */6 * * *",
        "action": "calibrate",
        "action_params": {"calibrator": "3C286"},
        "enabled": True,
    }


# ============================================================================
# Saved Queries Contract Tests
# ============================================================================


class TestSavedQueriesContracts:
    """Contract tests for /api/v1/saved-queries endpoints."""

    def test_list_queries_returns_200(self, api_client):
        """GET /api/v1/saved-queries returns 200."""
        response = api_client.get("/api/v1/saved-queries")
        assert response.status_code == 200

    def test_list_queries_response_schema(self, api_client):
        """Response has queries array and total count."""
        response = api_client.get("/api/v1/saved-queries")
        data = response.json()

        assert "queries" in data
        assert "total" in data
        assert isinstance(data["queries"], list)
        assert isinstance(data["total"], int)

    def test_create_query_returns_201(self, api_client, sample_query):
        """POST /api/v1/saved-queries returns 201 with id."""
        response = api_client.post("/api/v1/saved-queries", json=sample_query)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["name"] == sample_query["name"]

        # Cleanup
        api_client.delete(f"/api/v1/saved-queries/{data['id']}")

    def test_get_query_returns_200(self, api_client, sample_query):
        """GET /api/v1/saved-queries/{id} returns 200."""
        # Create first
        create_resp = api_client.post("/api/v1/saved-queries", json=sample_query)
        query_id = create_resp.json()["id"]

        # Get it
        response = api_client.get(f"/api/v1/saved-queries/{query_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == query_id
        assert data["name"] == sample_query["name"]

        # Cleanup
        api_client.delete(f"/api/v1/saved-queries/{query_id}")

    def test_get_nonexistent_query_returns_404(self, api_client):
        """GET /api/v1/saved-queries/{id} returns 404 for missing."""
        response = api_client.get("/api/v1/saved-queries/nonexistent-id")
        assert response.status_code == 404

    def test_update_query_returns_200(self, api_client, sample_query):
        """PUT /api/v1/saved-queries/{id} returns 200."""
        # Create first
        create_resp = api_client.post("/api/v1/saved-queries", json=sample_query)
        query_id = create_resp.json()["id"]

        # Update - full payload required
        update_data = sample_query.copy()
        update_data["name"] = "Updated Name"
        response = api_client.put(
            f"/api/v1/saved-queries/{query_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

        # Cleanup
        api_client.delete(f"/api/v1/saved-queries/{query_id}")

    def test_delete_query_returns_204(self, api_client, sample_query):
        """DELETE /api/v1/saved-queries/{id} returns 204."""
        # Create first
        create_resp = api_client.post("/api/v1/saved-queries", json=sample_query)
        query_id = create_resp.json()["id"]

        # Delete
        response = api_client.delete(f"/api/v1/saved-queries/{query_id}")
        assert response.status_code == 204

    def test_fork_query_returns_201(self, api_client, sample_query):
        """POST /api/v1/saved-queries/{id}/fork returns 201."""
        # Create original
        create_resp = api_client.post("/api/v1/saved-queries", json=sample_query)
        original_id = create_resp.json()["id"]

        # Fork it (name is optional - server generates default)
        response = api_client.post(
            f"/api/v1/saved-queries/{original_id}/fork", json={}
        )
        assert response.status_code == 201

        forked = response.json()
        assert forked["id"] != original_id
        # Server adds " (copy)" suffix by default
        assert "(copy)" in forked["name"]

        # Cleanup
        api_client.delete(f"/api/v1/saved-queries/{original_id}")
        api_client.delete(f"/api/v1/saved-queries/{forked['id']}")


# ============================================================================
# Backup Contract Tests
# ============================================================================


class TestBackupContracts:
    """Contract tests for /api/v1/backups endpoints."""

    def test_list_backups_returns_200(self, api_client):
        """GET /api/v1/backups returns 200."""
        response = api_client.get("/api/v1/backups")
        assert response.status_code == 200

    def test_list_backups_response_schema(self, api_client):
        """Response has backups array and total."""
        response = api_client.get("/api/v1/backups")
        data = response.json()

        assert "backups" in data
        assert "total" in data
        assert isinstance(data["backups"], list)

    def test_backup_status_returns_200(self, api_client):
        """GET /api/v1/backups/status returns 200 or 404."""
        response = api_client.get("/api/v1/backups/status")
        # 200 if backups exist, 404 if none
        assert response.status_code in [200, 404]

    def test_backup_status_schema(self, api_client):
        """Backup status has expected fields."""
        response = api_client.get("/api/v1/backups/status")
        if response.status_code == 200:
            data = response.json()
            # Should have at least these fields
            assert "status" in data or "id" in data

    def test_create_backup_returns_201(self, api_client):
        """POST /api/v1/backups returns 201 (created)."""
        payload = {"backup_type": "database_only"}
        response = api_client.post("/api/v1/backups", json=payload)

        # 201 Created for background task started
        assert response.status_code == 201

    def test_get_nonexistent_backup_returns_404(self, api_client):
        """GET /api/v1/backups/{id} returns 404 for missing."""
        response = api_client.get("/api/v1/backups/nonexistent-backup-id")
        assert response.status_code == 404


# ============================================================================
# Triggers Contract Tests
# ============================================================================


class TestTriggersContracts:
    """Contract tests for /api/v1/triggers endpoints."""

    def test_list_triggers_returns_200(self, api_client):
        """GET /api/v1/triggers returns 200."""
        response = api_client.get("/api/v1/triggers")
        assert response.status_code == 200

    def test_list_triggers_response_schema(self, api_client):
        """Response has triggers array and total."""
        response = api_client.get("/api/v1/triggers")
        data = response.json()

        assert "triggers" in data
        assert "total" in data
        assert isinstance(data["triggers"], list)

    def test_create_trigger_returns_201(self, api_client, sample_trigger):
        """POST /api/v1/triggers returns 201."""
        response = api_client.post("/api/v1/triggers", json=sample_trigger)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["name"] == sample_trigger["name"]

        # Cleanup
        api_client.delete(f"/api/v1/triggers/{data['id']}")

    def test_get_trigger_returns_200(self, api_client, sample_trigger):
        """GET /api/v1/triggers/{id} returns 200."""
        create_resp = api_client.post("/api/v1/triggers", json=sample_trigger)
        trigger_id = create_resp.json()["id"]

        response = api_client.get(f"/api/v1/triggers/{trigger_id}")
        assert response.status_code == 200
        assert response.json()["id"] == trigger_id

        # Cleanup
        api_client.delete(f"/api/v1/triggers/{trigger_id}")

    def test_get_nonexistent_trigger_returns_404(self, api_client):
        """GET /api/v1/triggers/{id} returns 404 for missing."""
        response = api_client.get("/api/v1/triggers/nonexistent-trigger")
        assert response.status_code == 404

    def test_delete_trigger_returns_204(self, api_client, sample_trigger):
        """DELETE /api/v1/triggers/{id} returns 204."""
        create_resp = api_client.post("/api/v1/triggers", json=sample_trigger)
        trigger_id = create_resp.json()["id"]

        response = api_client.delete(f"/api/v1/triggers/{trigger_id}")
        assert response.status_code == 204


# ============================================================================
# Jupyter Contract Tests
# ============================================================================


class TestJupyterContracts:
    """Contract tests for /api/v1/jupyter endpoints."""

    def test_jupyter_status_returns_200_or_503(self, api_client):
        """GET /api/v1/jupyter/status returns 200 or 503."""
        response = api_client.get("/api/v1/jupyter/status")
        # 200 if JupyterHub available, 503 if not
        assert response.status_code in [200, 503]

    def test_list_notebooks_returns_200_or_503(self, api_client):
        """GET /api/v1/jupyter/notebooks returns 200 or 503."""
        response = api_client.get("/api/v1/jupyter/notebooks")
        assert response.status_code in [200, 503]


# ============================================================================
# VO Export Contract Tests
# ============================================================================


class TestVOExportContracts:
    """Contract tests for /api/v1/vo/exports endpoints."""

    def test_list_export_jobs_returns_200(self, api_client):
        """GET /api/v1/vo/exports returns 200."""
        response = api_client.get("/api/v1/vo/exports")
        assert response.status_code == 200

    def test_list_export_jobs_schema(self, api_client):
        """Response has jobs array and total."""
        response = api_client.get("/api/v1/vo/exports")
        data = response.json()

        assert "jobs" in data
        assert "total" in data

    def test_create_export_job_returns_201(self, api_client):
        """POST /api/v1/vo/exports returns 201."""
        payload = {
            "export_type": "votable",
            "target_type": "images",
        }
        response = api_client.post("/api/v1/vo/exports", json=payload)
        # 201 for job creation
        assert response.status_code == 201

    def test_get_nonexistent_job_returns_404(self, api_client):
        """GET /api/v1/vo/exports/{id} returns 404 for missing."""
        response = api_client.get("/api/v1/vo/exports/nonexistent-job")
        assert response.status_code == 404


# ============================================================================
# Cross-Endpoint Validation
# ============================================================================


class TestAPIConsistency:
    """Tests for consistent API behavior across endpoints."""

    def test_all_list_endpoints_return_json(self, api_client):
        """All list endpoints return JSON content type."""
        endpoints = [
            "/api/v1/saved-queries",
            "/api/v1/backup",
            "/api/v1/triggers",
            "/api/v1/vo-export",
        ]
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.headers.get("content-type", "").startswith(
                "application/json"
            ), f"{endpoint} should return JSON"

    def test_404_responses_are_json(self, api_client):
        """404 errors return JSON with detail field."""
        endpoints = [
            "/api/v1/saved-queries/nonexistent",
            "/api/v1/backup/nonexistent",
            "/api/v1/triggers/nonexistent",
            "/api/v1/vo-export/nonexistent",
        ]
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data, f"{endpoint} 404 should have detail"

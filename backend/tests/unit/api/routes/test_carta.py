"""
Unit tests for CARTA API routes.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

import httpx


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def carta_router():
    """Import the CARTA router for testing."""
    from dsa110_contimg.api.routes.carta import router
    return router


@pytest.fixture
def client(carta_router):
    """Create a test client for the CARTA router."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.include_router(carta_router)
    return TestClient(app)


@pytest.fixture
def clear_sessions():
    """Clear active sessions before each test."""
    from dsa110_contimg.api.routes.carta import _active_sessions
    _active_sessions.clear()
    yield
    _active_sessions.clear()


# =============================================================================
# Status Endpoint Tests
# =============================================================================


class TestGetCartaStatus:
    """Tests for GET /carta/status endpoint."""

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    def test_returns_available_when_server_running(
        self, mock_check, client, clear_sessions
    ):
        """Should return available=True when CARTA server responds."""
        mock_check.return_value = (True, "4.0.0", None)
        
        response = client.get("/carta/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["version"] == "4.0.0"
        assert data["message"] == "CARTA server is running"

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    def test_returns_unavailable_when_server_down(self, mock_check, client):
        """Should return available=False when CARTA server is not responding."""
        mock_check.return_value = (False, None, "Connection refused")
        
        response = client.get("/carta/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "Connection refused" in data["message"]

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    def test_includes_session_count(self, mock_check, client, clear_sessions):
        """Should include current session count in response."""
        mock_check.return_value = (True, "4.0.0", None)
        
        # Add a mock session
        from dsa110_contimg.api.routes.carta import _active_sessions, CARTASession
        _active_sessions["test-session"] = CARTASession(
            id="test-session",
            file_path="/data/test.ms",
            file_type="ms",
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        
        response = client.get("/carta/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["sessions_active"] == 1


# =============================================================================
# Sessions Endpoint Tests
# =============================================================================


class TestListCartaSessions:
    """Tests for GET /carta/sessions endpoint."""

    def test_returns_empty_list_when_no_sessions(self, client, clear_sessions):
        """Should return empty list when no sessions exist."""
        response = client.get("/carta/sessions")
        
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_active_sessions(self, client, clear_sessions):
        """Should return list of active sessions."""
        from dsa110_contimg.api.routes.carta import _active_sessions, CARTASession
        
        now = datetime.utcnow().isoformat() + "Z"
        _active_sessions["session-1"] = CARTASession(
            id="session-1",
            file_path="/data/test1.ms",
            file_type="ms",
            created_at=now,
        )
        _active_sessions["session-2"] = CARTASession(
            id="session-2",
            file_path="/data/test2.fits",
            file_type="fits",
            created_at=now,
        )
        
        response = client.get("/carta/sessions")
        
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) == 2
        assert any(s["id"] == "session-1" for s in sessions)
        assert any(s["id"] == "session-2" for s in sessions)


# =============================================================================
# Open Endpoint Tests
# =============================================================================


class TestOpenInCarta:
    """Tests for POST /carta/open endpoint."""

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    @patch("os.path.exists")
    def test_creates_new_session(self, mock_exists, mock_check, client, clear_sessions):
        """Should create a new session when opening a file."""
        mock_check.return_value = (True, "4.0.0", None)
        mock_exists.return_value = True
        
        response = client.post(
            "/carta/open",
            json={"file_path": "/data/test.ms", "file_type": "ms"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] is not None
        assert "viewer_url" in data
        assert data["message"] == "New session created"

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    def test_returns_503_when_carta_unavailable(self, mock_check, client, clear_sessions):
        """Should return 503 when CARTA server is not available."""
        mock_check.return_value = (False, None, "Connection refused")
        
        response = client.post(
            "/carta/open",
            json={"file_path": "/data/test.ms", "file_type": "ms"},
        )
        
        assert response.status_code == 503
        assert "CARTA server is not available" in response.json()["detail"]["error"]

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    def test_returns_400_for_invalid_path(self, mock_check, client, clear_sessions):
        """Should return 400 for paths outside allowed directories."""
        mock_check.return_value = (True, "4.0.0", None)
        
        response = client.post(
            "/carta/open",
            json={"file_path": "/etc/passwd", "file_type": "ms"},
        )
        
        assert response.status_code == 400
        assert "Invalid file path" in response.json()["detail"]["error"]

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    @patch("os.path.exists")
    def test_returns_404_for_missing_file(self, mock_exists, mock_check, client, clear_sessions):
        """Should return 404 when file doesn't exist."""
        mock_check.return_value = (True, "4.0.0", None)
        mock_exists.return_value = False
        
        response = client.post(
            "/carta/open",
            json={"file_path": "/data/nonexistent.ms", "file_type": "ms"},
        )
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]["error"]

    @patch("dsa110_contimg.api.routes.carta._check_carta_server")
    @patch("os.path.exists")
    def test_reuses_existing_session(self, mock_exists, mock_check, client, clear_sessions):
        """Should reuse existing session for same file when not requesting new."""
        mock_check.return_value = (True, "4.0.0", None)
        mock_exists.return_value = True
        
        # First request creates session
        response1 = client.post(
            "/carta/open",
            json={"file_path": "/data/test.ms", "file_type": "ms"},
        )
        session_id_1 = response1.json()["session_id"]
        
        # Second request should reuse
        response2 = client.post(
            "/carta/open",
            json={"file_path": "/data/test.ms", "file_type": "ms"},
        )
        session_id_2 = response2.json()["session_id"]
        
        assert session_id_1 == session_id_2
        assert response2.json()["message"] == "Reusing existing session"


# =============================================================================
# Close Session Endpoint Tests
# =============================================================================


class TestCloseCartaSession:
    """Tests for DELETE /carta/sessions/{session_id} endpoint."""

    def test_closes_existing_session(self, client, clear_sessions):
        """Should close and remove an existing session."""
        from dsa110_contimg.api.routes.carta import _active_sessions, CARTASession
        
        _active_sessions["session-to-close"] = CARTASession(
            id="session-to-close",
            file_path="/data/test.ms",
            file_type="ms",
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        
        response = client.delete("/carta/sessions/session-to-close")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "session-to-close" not in _active_sessions

    def test_returns_404_for_unknown_session(self, client, clear_sessions):
        """Should return 404 for non-existent session."""
        response = client.delete("/carta/sessions/unknown-session")
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]["error"]


# =============================================================================
# Get Session Endpoint Tests
# =============================================================================


class TestGetCartaSession:
    """Tests for GET /carta/sessions/{session_id} endpoint."""

    def test_returns_session_details(self, client, clear_sessions):
        """Should return details of an existing session."""
        from dsa110_contimg.api.routes.carta import _active_sessions, CARTASession
        
        created = datetime.utcnow().isoformat() + "Z"
        _active_sessions["session-1"] = CARTASession(
            id="session-1",
            file_path="/data/test.ms",
            file_type="ms",
            created_at=created,
        )
        
        response = client.get("/carta/sessions/session-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "session-1"
        assert data["file_path"] == "/data/test.ms"
        assert data["file_type"] == "ms"

    def test_returns_404_for_unknown_session(self, client, clear_sessions):
        """Should return 404 for non-existent session."""
        response = client.get("/carta/sessions/unknown-session")
        
        assert response.status_code == 404


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestValidateFilePath:
    """Tests for _validate_file_path helper function."""

    def test_accepts_data_directory(self):
        """Should accept paths under /data/."""
        from dsa110_contimg.api.routes.carta import _validate_file_path
        
        assert _validate_file_path("/data/test.ms") is True
        assert _validate_file_path("/data/dsa110/ms/test.ms") is True

    def test_accepts_stage_directory(self):
        """Should accept paths under /stage/."""
        from dsa110_contimg.api.routes.carta import _validate_file_path
        
        assert _validate_file_path("/stage/test.ms") is True
        assert _validate_file_path("/stage/dsa110-contimg/ms/test.ms") is True

    def test_rejects_system_paths(self):
        """Should reject paths to system directories."""
        from dsa110_contimg.api.routes.carta import _validate_file_path
        
        assert _validate_file_path("/etc/passwd") is False
        assert _validate_file_path("/root/.ssh/id_rsa") is False
        assert _validate_file_path("/home/user/file.ms") is False

    def test_rejects_relative_paths(self):
        """Should reject relative paths."""
        from dsa110_contimg.api.routes.carta import _validate_file_path
        
        assert _validate_file_path("test.ms") is False
        assert _validate_file_path("./test.ms") is False
        assert _validate_file_path("../test.ms") is False

    def test_rejects_path_traversal(self):
        """Should reject path traversal attempts."""
        from dsa110_contimg.api.routes.carta import _validate_file_path
        
        # These normalize to paths outside allowed directories
        assert _validate_file_path("/data/../etc/passwd") is False
        assert _validate_file_path("/data/test/../../etc/passwd") is False

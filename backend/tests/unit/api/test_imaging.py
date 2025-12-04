"""
Tests for the interactive imaging API endpoints and BokehSessionManager.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.services.bokeh_sessions import (
    BokehSession,
    BokehSessionManager,
    DSA110_ICLEAN_DEFAULTS,
    PortPool,
    get_session_manager,
)


# =============================================================================
# PortPool Tests
# =============================================================================


class TestPortPool:
    """Tests for PortPool class."""

    @pytest.fixture
    def port_pool(self):
        """Create a port pool with a small range for testing."""
        return PortPool(range(5010, 5015))

    @pytest.mark.asyncio
    async def test_acquire_port_success(self, port_pool):
        """Test acquiring a port from the pool."""
        port = await port_pool.acquire("session-1")
        assert port in range(5010, 5015)
        assert port_pool.in_use_count == 1
        assert port_pool.available_count == 4

    @pytest.mark.asyncio
    async def test_acquire_multiple_ports(self, port_pool):
        """Test acquiring multiple ports."""
        ports = []
        for i in range(5):
            port = await port_pool.acquire(f"session-{i}")
            ports.append(port)

        assert len(set(ports)) == 5  # All unique
        assert port_pool.available_count == 0
        assert port_pool.in_use_count == 5

    @pytest.mark.asyncio
    async def test_acquire_no_ports_available(self, port_pool):
        """Test error when no ports available."""
        # Exhaust all ports
        for i in range(5):
            await port_pool.acquire(f"session-{i}")

        # Try to acquire one more
        with pytest.raises(RuntimeError, match="No ports available"):
            await port_pool.acquire("session-extra")

    @pytest.mark.asyncio
    async def test_release_port(self, port_pool):
        """Test releasing a port back to the pool."""
        port = await port_pool.acquire("session-1")
        assert port_pool.in_use_count == 1

        await port_pool.release("session-1")
        assert port_pool.in_use_count == 0
        assert port_pool.available_count == 5
        assert port in port_pool.available

    @pytest.mark.asyncio
    async def test_release_unknown_session(self, port_pool):
        """Test releasing a port for unknown session (no-op)."""
        await port_pool.release("unknown-session")
        assert port_pool.available_count == 5  # No change


# =============================================================================
# BokehSession Tests
# =============================================================================


class TestBokehSession:
    """Tests for BokehSession dataclass."""

    def test_session_url(self):
        """Test URL generation for session."""
        mock_process = MagicMock()
        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )

        assert session.url == "http://localhost:5010/iclean"

    def test_session_url_with_custom_host(self):
        """Test URL generation with BOKEH_HOST environment variable."""
        mock_process = MagicMock()

        with patch.dict("os.environ", {"BOKEH_HOST": "example.com"}):
            session = BokehSession(
                id="test-session",
                port=5010,
                process=mock_process,
                ms_path="/data/test.ms",
                imagename="/stage/test_clean",
            )
            assert session.url == "http://example.com:5010/iclean"

    def test_session_age(self):
        """Test session age calculation."""
        mock_process = MagicMock()
        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
            created_at=datetime.now() - timedelta(hours=2),
        )

        assert 1.9 < session.age_hours < 2.1

    def test_session_is_alive_running(self):
        """Test is_alive when process is running."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running

        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )

        assert session.is_alive() is True

    def test_session_is_alive_terminated(self):
        """Test is_alive when process has terminated."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Exited with code 0

        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )

        assert session.is_alive() is False

    def test_session_to_dict(self):
        """Test session serialization to dict."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
            user_id="user-123",
            params={"niter": 5000},
        )

        result = session.to_dict()

        assert result["id"] == "test-session"
        assert result["port"] == 5010
        assert result["ms_path"] == "/data/test.ms"
        assert result["imagename"] == "/stage/test_clean"
        assert result["is_alive"] is True
        assert result["user_id"] == "user-123"
        assert result["params"]["niter"] == 5000


# =============================================================================
# BokehSessionManager Tests
# =============================================================================


class TestBokehSessionManager:
    """Tests for BokehSessionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a session manager for testing."""
        return BokehSessionManager(port_range=range(5010, 5020))

    @pytest.mark.asyncio
    async def test_create_session_ms_not_found(self, manager):
        """Test error when MS file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="not found"):
            await manager.create_session(
                ms_path="/nonexistent/path.ms",
                imagename="/stage/output",
            )

    @pytest.mark.asyncio
    async def test_create_session_success(self, manager, tmp_path):
        """Test successful session creation."""
        # Create a mock MS directory
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running

        with patch("subprocess.Popen", return_value=mock_process):
            session = await manager.create_session(
                ms_path=str(ms_path),
                imagename="/stage/test_clean",
            )

            assert session is not None
            assert session.ms_path == str(ms_path)
            assert session.imagename == "/stage/test_clean"
            assert session.id in manager.sessions

    @pytest.mark.asyncio
    async def test_create_session_process_fails(self, manager, tmp_path):
        """Test error when Bokeh process fails to start."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Exited immediately
        mock_process.stderr = MagicMock()
        mock_process.stderr.read.return_value = b"Error: casagui not installed"

        with patch("subprocess.Popen", return_value=mock_process):
            with pytest.raises(RuntimeError, match="failed to start"):
                await manager.create_session(
                    ms_path=str(ms_path),
                    imagename="/stage/test_clean",
                )

    @pytest.mark.asyncio
    async def test_get_session(self, manager):
        """Test retrieving a session by ID."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )
        manager.sessions["test-session"] = session

        result = await manager.get_session("test-session")
        assert result == session

        result = await manager.get_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_session(self, manager):
        """Test cleaning up a session."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.return_value = None

        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )
        manager.sessions["test-session"] = session
        manager.port_pool.in_use["test-session"] = 5010
        manager.port_pool.available.discard(5010)

        success = await manager.cleanup_session("test-session")

        assert success is True
        assert "test-session" not in manager.sessions
        assert 5010 in manager.port_pool.available
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_session(self, manager):
        """Test cleaning up a session that doesn't exist."""
        success = await manager.cleanup_session("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_cleanup_stale_sessions(self, manager):
        """Test cleaning up stale sessions."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.return_value = None

        # Create an old session
        old_session = BokehSession(
            id="old-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
            created_at=datetime.now() - timedelta(hours=5),
        )

        # Create a new session
        new_session = BokehSession(
            id="new-session",
            port=5011,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
            created_at=datetime.now(),
        )

        manager.sessions["old-session"] = old_session
        manager.sessions["new-session"] = new_session
        manager.port_pool.in_use["old-session"] = 5010
        manager.port_pool.in_use["new-session"] = 5011

        cleaned = await manager.cleanup_stale_sessions(max_age_hours=4.0)

        assert cleaned == 1
        assert "old-session" not in manager.sessions
        assert "new-session" in manager.sessions

    @pytest.mark.asyncio
    async def test_cleanup_dead_sessions(self, manager):
        """Test cleaning up sessions with dead processes."""
        alive_process = MagicMock()
        alive_process.poll.return_value = None
        alive_process.wait.return_value = None

        dead_process = MagicMock()
        dead_process.poll.return_value = 1
        dead_process.wait.return_value = None

        alive_session = BokehSession(
            id="alive-session",
            port=5010,
            process=alive_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )

        dead_session = BokehSession(
            id="dead-session",
            port=5011,
            process=dead_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )

        manager.sessions["alive-session"] = alive_session
        manager.sessions["dead-session"] = dead_session
        manager.port_pool.in_use["alive-session"] = 5010
        manager.port_pool.in_use["dead-session"] = 5011

        cleaned = await manager.cleanup_dead_sessions()

        assert cleaned == 1
        assert "alive-session" in manager.sessions
        assert "dead-session" not in manager.sessions

    @pytest.mark.asyncio
    async def test_list_sessions(self, manager):
        """Test listing all sessions."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        session = BokehSession(
            id="test-session",
            port=5010,
            process=mock_process,
            ms_path="/data/test.ms",
            imagename="/stage/test_clean",
        )
        manager.sessions["test-session"] = session

        result = manager.list_sessions()

        assert len(result) == 1
        assert result[0]["id"] == "test-session"

    def test_default_params(self, manager):
        """Test DSA-110 default parameters are set."""
        assert manager.default_params["imsize"] == [5040, 5040]
        assert manager.default_params["cell"] == "2.5arcsec"
        assert manager.default_params["threshold"] == "0.5mJy"


# =============================================================================
# API Endpoint Tests
# =============================================================================


class TestImagingAPIEndpoints:
    """Tests for imaging API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client with auth disabled."""
        import os
        from unittest.mock import patch
        from dsa110_contimg.api.app import create_app

        env_patches = {
            "DSA110_AUTH_DISABLED": "true",
            "DSA110_ENV": "testing",
            "DSA110_ALLOWED_IPS": "127.0.0.1,::1,testclient",
        }
        with patch.dict(os.environ, env_patches):
            app = create_app()
            with TestClient(app) as test_client:
                yield test_client

    def test_get_imaging_defaults(self, client):
        """Test getting DSA-110 default imaging parameters."""
        response = client.get("/api/v1/imaging/defaults")

        assert response.status_code == 200
        data = response.json()
        assert data["imsize"] == [5040, 5040]
        assert data["cell"] == "2.5arcsec"
        assert data["deconvolver"] == "mtmfs"

    def test_get_imaging_status(self, client):
        """Test getting imaging service status."""
        response = client.get("/api/v1/imaging/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "total_sessions" in data
        assert "available_ports" in data

    def test_list_sessions_empty(self, client):
        """Test listing sessions when none exist."""
        response = client.get("/api/v1/imaging/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    def test_start_interactive_clean_ms_not_found(self, client):
        """Test error when MS doesn't exist."""
        response = client.post(
            "/api/v1/imaging/interactive",
            json={
                "ms_path": "/nonexistent/path.ms",
                "imagename": "/stage/test_clean",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_start_interactive_clean_invalid_ms(self, client, tmp_path):
        """Test error when path is not a valid MS."""
        # Create a regular file, not an MS directory
        fake_ms = tmp_path / "fake.ms"
        fake_ms.touch()

        response = client.post(
            "/api/v1/imaging/interactive",
            json={
                "ms_path": str(fake_ms),
                "imagename": "/stage/test_clean",
            },
        )

        assert response.status_code == 422
        assert "valid measurement set" in response.json()["detail"].lower()

    def test_get_session_not_found(self, client):
        """Test getting a session that doesn't exist."""
        response = client.get("/api/v1/imaging/sessions/nonexistent-id")

        assert response.status_code == 404

    def test_stop_session_not_found(self, client):
        """Test stopping a session that doesn't exist."""
        response = client.delete("/api/v1/imaging/sessions/nonexistent-id")

        assert response.status_code == 404


# =============================================================================
# Integration Tests
# =============================================================================


class TestImagingIntegration:
    """Integration tests for imaging workflow."""

    @pytest.fixture
    def mock_ms(self, tmp_path):
        """Create a mock MS directory structure."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        # Create table.dat to make it look like an MS
        (ms_path / "table.dat").touch()
        return ms_path

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, mock_ms):
        """Test creating, listing, and cleaning up a session."""
        manager = BokehSessionManager(port_range=range(5010, 5020))

        # Mock subprocess
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.return_value = None

        with patch("subprocess.Popen", return_value=mock_process):
            # Create session
            session = await manager.create_session(
                ms_path=str(mock_ms),
                imagename="/stage/test_clean",
            )
            assert session is not None
            assert len(manager.list_sessions()) == 1

            # Get session
            retrieved = await manager.get_session(session.id)
            assert retrieved == session

            # Cleanup
            success = await manager.cleanup_session(session.id)
            assert success is True
            assert len(manager.list_sessions()) == 0

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, tmp_path):
        """Test managing multiple concurrent sessions."""
        manager = BokehSessionManager(port_range=range(5010, 5020))

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.return_value = None

        # Create multiple MS directories
        ms_paths = []
        for i in range(3):
            ms_path = tmp_path / f"test{i}.ms"
            ms_path.mkdir()
            (ms_path / "table.dat").touch()
            ms_paths.append(ms_path)

        with patch("subprocess.Popen", return_value=mock_process):
            sessions = []
            for i, ms_path in enumerate(ms_paths):
                session = await manager.create_session(
                    ms_path=str(ms_path),
                    imagename=f"/stage/test_clean_{i}",
                )
                sessions.append(session)

            assert len(manager.list_sessions()) == 3
            assert manager.port_pool.in_use_count == 3

            # Cleanup all
            await manager.shutdown()
            assert len(manager.list_sessions()) == 0

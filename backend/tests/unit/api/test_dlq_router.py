# mypy: disable-error-code="import-not-found,import-untyped"
"""
Unit tests for Dead Letter Queue (DLQ) API router.

Tests the REST API endpoints for DLQ management.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest  # type: ignore[import-not-found]
from fastapi.testclient import TestClient  # type: ignore[import-not-found]


@pytest.fixture
def mock_dlq():
    """Create a mock DeadLetterQueue."""
    dlq = MagicMock()
    return dlq


@pytest.fixture
def mock_dlq_item():
    """Create a mock DLQ item."""
    from dsa110_contimg.pipeline.dead_letter_queue import (
        DLQStatus,  # type: ignore[import-not-found]
    )

    item = MagicMock()
    item.id = 1
    item.component = "calibration"
    item.operation = "solve"
    item.error_type = "ValidationError"
    item.error_message = "Failed to solve calibration"
    item.context = {"ms_path": "/test.ms"}
    item.created_at = 1732500000.0
    item.retry_count = 0
    item.status = DLQStatus.PENDING
    item.resolved_at = None
    item.resolution_note = None
    return item


@pytest.mark.unit
class TestDLQListEndpoint:
    """Tests for GET /api/dlq/items endpoint."""

    def test_list_items_empty(self, mock_dlq):
        """Test listing items when DLQ is empty."""
        mock_dlq.get_pending.return_value = []

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.get("/api/dlq/items")

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["total"] == 0

    def test_list_items_with_data(self, mock_dlq, mock_dlq_item):
        """Test listing items with data."""
        mock_dlq.get_pending.return_value = [mock_dlq_item]

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.get("/api/dlq/items")

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["component"] == "calibration"
            assert data["items"][0]["operation"] == "solve"

    def test_list_items_with_component_filter(self, mock_dlq, mock_dlq_item):
        """Test listing items with component filter."""
        mock_dlq.get_pending.return_value = [mock_dlq_item]

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.get("/api/dlq/items?component=calibration")

            assert response.status_code == 200
            mock_dlq.get_pending.assert_called_with(component="calibration", limit=100)


@pytest.mark.unit
class TestDLQGetItemEndpoint:
    """Tests for GET /api/dlq/items/{item_id} endpoint."""

    def test_get_item_found(self, mock_dlq, mock_dlq_item):
        """Test getting a specific item."""
        mock_dlq.get_by_id.return_value = mock_dlq_item

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.get("/api/dlq/items/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["component"] == "calibration"

    def test_get_item_not_found(self, mock_dlq):
        """Test getting a non-existent item."""
        mock_dlq.get_by_id.return_value = None

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.get("/api/dlq/items/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit
class TestDLQRetryEndpoint:
    """Tests for POST /api/dlq/items/{item_id}/retry endpoint."""

    def test_retry_item_success(self, mock_dlq):
        """Test retrying an item."""
        mock_dlq.mark_retrying.return_value = None

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.post("/api/dlq/items/1/retry")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "retrying"
            mock_dlq.mark_retrying.assert_called_once_with(1)


@pytest.mark.unit
class TestDLQResolveEndpoint:
    """Tests for POST /api/dlq/items/{item_id}/resolve endpoint."""

    def test_resolve_item_success(self, mock_dlq):
        """Test resolving an item."""
        mock_dlq.resolve.return_value = None

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.post(
                "/api/dlq/items/1/resolve",
                json={"note": "Fixed manually"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "resolved"
            mock_dlq.resolve.assert_called_once_with(1, note="Fixed manually")


@pytest.mark.unit
class TestDLQFailEndpoint:
    """Tests for POST /api/dlq/items/{item_id}/fail endpoint."""

    def test_fail_item_success(self, mock_dlq):
        """Test marking an item as failed."""
        mock_dlq.mark_failed.return_value = None

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.post(
                "/api/dlq/items/1/fail",
                json={"note": "Cannot be fixed"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            mock_dlq.mark_failed.assert_called_once_with(1, note="Cannot be fixed")


@pytest.mark.unit
class TestDLQStatsEndpoint:
    """Tests for GET /api/dlq/stats endpoint."""

    def test_get_stats(self, mock_dlq):
        """Test getting DLQ statistics."""
        mock_dlq.get_stats.return_value = {
            "pending": 5,
            "retrying": 2,
            "resolved": 10,
            "failed": 1,
            "total": 18,
            "by_component": {"calibration": 10, "imaging": 8},
            "by_error_type": {"ValidationError": 12, "IOError": 6},
        }

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.get("/api/dlq/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["pending"] == 5
            assert data["retrying"] == 2
            assert data["resolved"] == 10
            assert data["failed"] == 1
            assert data["total"] == 18
            assert data["by_component"]["calibration"] == 10
            assert data["by_error_type"]["ValidationError"] == 12


@pytest.mark.unit
class TestDLQDeleteEndpoint:
    """Tests for DELETE /api/dlq/items/{item_id} endpoint."""

    def test_delete_item_success(self, mock_dlq):
        """Test deleting an item."""
        mock_dlq.delete.return_value = None

        with patch(
            "dsa110_contimg.api.routers.dlq.get_dlq",
            return_value=mock_dlq,
        ):
            from fastapi import FastAPI

            from dsa110_contimg.api.routers.dlq import router

            app = FastAPI()
            app.include_router(router, prefix="/api/dlq")
            client = TestClient(app)

            response = client.delete("/api/dlq/items/1")

            assert response.status_code == 200
            data = response.json()
            assert "deleted" in data["message"].lower()
            mock_dlq.delete.assert_called_once_with(1)

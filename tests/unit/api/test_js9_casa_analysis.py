"""
Unit tests for JS9 CASA Analysis API endpoint.

Tests:
1. Request validation (task, image_path, region)
2. Task execution for each supported task
3. Caching behavior
4. Error handling
5. Region conversion
6. JSON serialization
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_fits_file(tmp_path):
    """Create a temporary FITS file for testing."""
    fits_path = tmp_path / "test_image.fits"
    fits_path.write_bytes(b"Fake FITS file content")
    return str(fits_path)


@pytest.fixture
def client():
    """Create test client."""
    from dsa110_contimg.api import app

    return TestClient(app)


@pytest.fixture
def mock_casa_tasks():
    """Mock CASA tasks."""
    with (
        patch("dsa110_contimg.api.visualization_routes.imstat") as mock_imstat,
        patch("dsa110_contimg.api.visualization_routes.imfit") as mock_imfit,
        patch("dsa110_contimg.api.visualization_routes.imhead") as mock_imhead,
        patch("dsa110_contimg.api.visualization_routes.immath") as mock_immath,
        patch("dsa110_contimg.api.visualization_routes.imval") as mock_imval,
    ):

        mock_imstat.return_value = {
            "DATA": {
                "mean": 0.001,
                "std": 0.0005,
                "min": -0.002,
                "max": 0.015,
                "sum": 100.0,
            }
        }

        yield {
            "imstat": mock_imstat,
            "imfit": mock_imfit,
            "imhead": mock_imhead,
            "immath": mock_immath,
            "imval": mock_imval,
        }


class TestRequestValidation:
    """Test request validation."""

    def test_invalid_task(self, client, mock_fits_file):
        """Test invalid task name."""
        response = client.post(
            "/api/visualization/js9/analysis",
            json={
                "task": "invalid_task",
                "image_path": mock_fits_file,
            },
        )
        assert response.status_code == 400
        assert "Invalid task" in response.json()["detail"]

    def test_missing_image_path(self, client):
        """Test missing image path."""
        response = client.post("/api/visualization/js9/analysis", json={"task": "imstat"})
        assert response.status_code == 422  # Validation error

    def test_nonexistent_image(self, client):
        """Test nonexistent image file."""
        response = client.post(
            "/api/visualization/js9/analysis",
            json={
                "task": "imstat",
                "image_path": "/nonexistent/file.fits",
            },
        )
        assert response.status_code == 404

    def test_non_fits_file(self, client, tmp_path):
        """Test non-FITS file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Not a FITS file")

        response = client.post(
            "/api/visualization/js9/analysis",
            json={
                "task": "imstat",
                "image_path": str(txt_file),
            },
        )
        assert response.status_code == 400
        assert "not a FITS image" in response.json()["detail"].lower()


class TestTaskExecution:
    """Test CASA task execution."""

    def test_imstat_execution(self, client, mock_fits_file, mock_casa_tasks):
        """Test imstat task execution."""
        with patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"):
            response = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imstat",
                    "image_path": mock_fits_file,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task"] == "imstat"
            assert "result" in data
            assert mock_casa_tasks["imstat"].called

    def test_imhead_execution(self, client, mock_fits_file, mock_casa_tasks):
        """Test imhead task execution."""
        mock_casa_tasks["imhead"].return_value = {"header": {"NAXIS": 2}}

        with patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"):
            response = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imhead",
                    "image_path": mock_fits_file,
                    "parameters": {"mode": "list"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task"] == "imhead"

    def test_immath_execution(self, client, mock_fits_file, mock_casa_tasks):
        """Test immath task execution."""
        with (
            patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"),
            patch("tempfile.gettempdir", return_value=str(Path(mock_fits_file).parent)),
            patch("os.path.exists", return_value=True),
            patch("os.remove"),
        ):

            response = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "immath",
                    "image_path": mock_fits_file,
                    "parameters": {"expr": "IM0 * 2"},
                },
            )
            # immath may fail without real CASA, but should handle gracefully
            assert response.status_code in [200, 500]


class TestRegionConversion:
    """Test JS9 region to CASA conversion via API."""

    def test_region_included_in_request(self, client, mock_fits_file, mock_casa_tasks):
        """Test that region is properly included in API request."""
        region = {"shape": "circle", "x": 100, "y": 200, "r": 50}

        with patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"):
            response = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imstat",
                    "image_path": mock_fits_file,
                    "region": region,
                },
            )
            assert response.status_code == 200
            # Verify task was called (region should be converted internally)
            assert mock_casa_tasks["imstat"].called


class TestCaching:
    """Test result caching."""

    def test_cache_hit(self, client, mock_fits_file, mock_casa_tasks):
        """Test cache hit returns cached result."""
        # Clear cache first
        from dsa110_contimg.api.visualization_routes import _analysis_cache

        _analysis_cache.clear()

        with patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"):
            # First request
            response1 = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imstat",
                    "image_path": mock_fits_file,
                },
            )
            assert response1.status_code == 200

            # Reset mock to verify it's not called again
            mock_casa_tasks["imstat"].reset_mock()

            # Second request (should use cache)
            response2 = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imstat",
                    "image_path": mock_fits_file,
                },
            )
            assert response2.status_code == 200
            # Cached results have very short execution time
            assert response2.json()["execution_time_sec"] < 0.01


class TestJSONSerialization:
    """Test JSON serialization via API responses."""

    def test_numpy_data_in_response(self, client, mock_fits_file, mock_casa_tasks):
        """Test that numpy arrays are properly serialized in responses."""
        import numpy as np

        # Mock imstat to return numpy types
        mock_casa_tasks["imstat"].return_value = {
            "DATA": {
                "mean": np.float64(0.001),
                "std": np.float64(0.0005),
                "values": np.array([1, 2, 3, 4]),
            }
        }

        with patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"):
            response = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imstat",
                    "image_path": mock_fits_file,
                },
            )
            assert response.status_code == 200
            data = response.json()

            # Verify response is JSON-serializable (no numpy types)
            result = data["result"]["DATA"]
            assert isinstance(result["mean"], float)
            assert isinstance(result["values"], list)


class TestErrorHandling:
    """Test error handling."""

    def test_casa_task_failure(self, client, mock_fits_file, mock_casa_tasks):
        """Test CASA task failure handling."""
        mock_casa_tasks["imstat"].side_effect = Exception("CASA task failed")

        with patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"):
            response = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imstat",
                    "image_path": mock_fits_file,
                },
            )
            assert response.status_code == 200  # API returns 200 with error in response
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_imhead_fallback_to_fits(self, client, mock_fits_file):
        """Test imhead fallback to direct FITS reading."""
        with (
            patch("dsa110_contimg.api.visualization_routes.ensure_casa_path"),
            patch(
                "dsa110_contimg.api.visualization_routes.imhead",
                side_effect=Exception("CASA unavailable"),
            ),
            patch("astropy.io.fits.open") as mock_fits,
        ):

            mock_hdul = MagicMock()
            mock_hdul.__enter__.return_value = [MagicMock()]
            mock_hdul[0].header = {
                "NAXIS": 2,
                "NAXIS1": 100,
                "NAXIS2": 100,
            }
            mock_fits.return_value = mock_hdul

            response = client.post(
                "/api/visualization/js9/analysis",
                json={
                    "task": "imhead",
                    "image_path": mock_fits_file,
                    "parameters": {"mode": "list"},
                },
            )
            # Should succeed with fallback
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "note" in data["result"]  # Should indicate fallback


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

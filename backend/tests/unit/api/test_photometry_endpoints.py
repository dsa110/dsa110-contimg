"""Unit tests for photometry API endpoints.

Focus: Fast tests for photometry measurement endpoints with mocked dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestPhotometryMeasureEndpoint:
    """Test POST /api/photometry/measure endpoint."""

    @patch("dsa110_contimg.api.routers.photometry.measure_forced_peak")
    def test_measure_photometry_peak(self, mock_measure, client):
        """Test single photometry measurement with peak method."""
        # Mock result
        mock_result = MagicMock()
        mock_result.ra_deg = 123.456
        mock_result.dec_deg = -45.678
        mock_result.peak_jyb = 1.23
        mock_result.peak_err_jyb = 0.05
        mock_result.integrated_flux_jy = 1.25
        mock_result.err_integrated_flux_jy = 0.06
        mock_result.local_rms_jy = 0.02
        mock_result.success = True
        mock_result.error_message = None
        mock_measure.return_value = mock_result

        request_body = {
            "fits_path": "/path/to/image.fits",
            "ra_deg": 123.456,
            "dec_deg": -45.678,
            "use_aegean": False,
        }

        response = client.post("/api/photometry/measure", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["ra_deg"] == 123.456
        assert data["result"]["peak_jyb"] == 1.23
        assert data["result"]["success"] is True
        assert data["result"]["method"] == "peak"

        mock_measure.assert_called_once()

    @patch("dsa110_contimg.api.routers.photometry.measure_with_aegean")
    def test_measure_photometry_aegean(self, mock_measure, client):
        """Test single photometry measurement with Aegean method."""
        # Mock result
        mock_result = MagicMock()
        mock_result.ra_deg = 123.456
        mock_result.dec_deg = -45.678
        mock_result.peak_flux_jy = 1.23
        mock_result.err_peak_flux_jy = 0.05
        mock_result.integrated_flux_jy = 1.25
        mock_result.err_integrated_flux_jy = 0.06
        mock_result.local_rms_jy = 0.02
        mock_result.success = True
        mock_result.error_message = None
        mock_measure.return_value = mock_result

        request_body = {
            "fits_path": "/path/to/image.fits",
            "ra_deg": 123.456,
            "dec_deg": -45.678,
            "use_aegean": True,
            "aegean_prioritized": True,
        }

        response = client.post("/api/photometry/measure", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["method"] == "aegean"
        assert data["result"]["success"] is True

        mock_measure.assert_called_once()

    @patch("dsa110_contimg.api.routers.photometry.measure_forced_peak")
    def test_measure_photometry_error(self, mock_measure, client):
        """Test photometry measurement error handling."""
        mock_measure.side_effect = Exception("File not found")

        request_body = {
            "fits_path": "/path/to/nonexistent.fits",
            "ra_deg": 123.456,
            "dec_deg": -45.678,
        }

        response = client.post("/api/photometry/measure", json=request_body)
        assert response.status_code == 500


class TestPhotometryMeasureBatchEndpoint:
    """Test POST /api/photometry/measure-batch endpoint."""

    @patch("dsa110_contimg.api.routers.photometry.measure_many")
    def test_measure_photometry_batch(self, mock_measure, client):
        """Test batch photometry measurement."""
        # Mock results
        mock_result1 = MagicMock()
        mock_result1.ra_deg = 123.456
        mock_result1.dec_deg = -45.678
        mock_result1.peak_jyb = 1.23
        mock_result1.peak_err_jyb = 0.05
        mock_result1.integrated_flux_jy = 1.25
        mock_result1.err_integrated_flux_jy = 0.06
        mock_result1.local_rms_jy = 0.02
        mock_result1.success = True
        mock_result1.error_message = None

        mock_result2 = MagicMock()
        mock_result2.ra_deg = 124.456
        mock_result2.dec_deg = -46.678
        mock_result2.peak_jyb = 2.34
        mock_result2.peak_err_jyb = 0.08
        mock_result2.integrated_flux_jy = 2.40
        mock_result2.err_integrated_flux_jy = 0.09
        mock_result2.local_rms_jy = 0.03
        mock_result2.success = True
        mock_result2.error_message = None

        mock_measure.return_value = [mock_result1, mock_result2]

        request_body = {
            "fits_path": "/path/to/image.fits",
            "coordinates": [
                {"ra_deg": 123.456, "dec_deg": -45.678},
                {"ra_deg": 124.456, "dec_deg": -46.678},
            ],
        }

        response = client.post("/api/photometry/measure-batch", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["ra_deg"] == 123.456
        assert data["results"][1]["ra_deg"] == 124.456

        mock_measure.assert_called_once()

    @patch("dsa110_contimg.api.routers.photometry.measure_many")
    def test_measure_photometry_batch_error(self, mock_measure, client):
        """Test batch photometry measurement error handling."""
        mock_measure.side_effect = Exception("File not found")

        request_body = {
            "fits_path": "/path/to/nonexistent.fits",
            "coordinates": [{"ra_deg": 123.456, "dec_deg": -45.678}],
        }

        response = client.post("/api/photometry/measure-batch", json=request_body)
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0
        assert data["error"] is not None


class TestLightCurveEndpoint:
    """Test GET /api/photometry/sources/{source_id}/lightcurve endpoint."""

    @patch("dsa110_contimg.api.routers.photometry.Source")
    def test_get_lightcurve_success(self, mock_source_class, client):
        """Test successful lightcurve retrieval."""
        import pandas as pd

        # Mock Source instance
        mock_source = MagicMock()
        mock_source.ra_deg = 123.456
        mock_source.dec_deg = -45.678
        mock_source.measurements = pd.DataFrame({
            "mjd": [60100.5, 60101.5, 60102.5],
            "peak_jyb": [1.0, 1.2, 0.9],
            "peak_err_jyb": [0.05, 0.06, 0.04],
            "image_path": ["/img1.fits", "/img2.fits", "/img3.fits"],
        })
        mock_source_class.return_value = mock_source

        response = client.get("/api/photometry/sources/SRC001/lightcurve")

        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "SRC001"
        assert data["ra_deg"] == 123.456
        assert data["dec_deg"] == -45.678
        assert len(data["flux_points"]) == 3
        assert data["flux_points"][0]["flux_jy"] == 1.0
        assert data["flux_points"][0]["flux_err_jy"] == 0.05

    @patch("dsa110_contimg.api.routers.photometry.Source")
    def test_get_lightcurve_with_normalized(self, mock_source_class, client):
        """Test lightcurve with normalized flux points."""
        import pandas as pd

        mock_source = MagicMock()
        mock_source.ra_deg = 123.456
        mock_source.dec_deg = -45.678
        mock_source.measurements = pd.DataFrame({
            "mjd": [60100.5, 60101.5],
            "peak_jyb": [1.0, 1.2],
            "peak_err_jyb": [0.05, 0.06],
            "normalized_flux_jy": [1.0, 1.1],
            "normalized_flux_err_jy": [0.04, 0.05],
            "image_path": ["/img1.fits", "/img2.fits"],
        })
        mock_source_class.return_value = mock_source

        response = client.get("/api/photometry/sources/SRC002/lightcurve")

        assert response.status_code == 200
        data = response.json()
        assert data["normalized_flux_points"] is not None
        assert len(data["normalized_flux_points"]) == 2
        assert data["normalized_flux_points"][0]["flux_jy"] == 1.0

    @patch("dsa110_contimg.api.routers.photometry.Source")
    def test_get_lightcurve_no_measurements(self, mock_source_class, client):
        """Test lightcurve for source with no measurements."""
        import pandas as pd

        mock_source = MagicMock()
        mock_source.measurements = pd.DataFrame()
        mock_source_class.return_value = mock_source

        response = client.get("/api/photometry/sources/SRC_EMPTY/lightcurve")

        assert response.status_code == 404
        assert "No measurements found" in response.json()["detail"]

    @patch("dsa110_contimg.api.routers.photometry.Source")
    def test_get_lightcurve_source_not_found(self, mock_source_class, client):
        """Test lightcurve for non-existent source."""
        mock_source_class.side_effect = Exception("Source not found")

        response = client.get("/api/photometry/sources/NONEXISTENT/lightcurve")

        assert response.status_code == 404


class TestSourceMetricsEndpoint:
    """Test GET /api/photometry/sources/{source_id}/metrics endpoint."""

    @patch("dsa110_contimg.api.routers.photometry.Source")
    def test_get_source_metrics_success(self, mock_source_class, client):
        """Test successful metrics retrieval."""
        import pandas as pd

        mock_source = MagicMock()
        mock_source.ra_deg = 123.456
        mock_source.dec_deg = -45.678
        mock_source.measurements = pd.DataFrame({
            "peak_jyb": [1.0, 1.2, 0.9, 1.1],
            "peak_err_jyb": [0.05, 0.06, 0.04, 0.05],
        })
        mock_source_class.return_value = mock_source

        response = client.get("/api/photometry/sources/SRC001/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "SRC001"
        assert data["ra_deg"] == 123.456
        assert "mean_flux_jy" in data
        assert "variability_index" in data
        assert data["n_measurements"] == 4

    @patch("dsa110_contimg.api.routers.photometry.Source")
    def test_get_source_metrics_not_found(self, mock_source_class, client):
        """Test metrics for non-existent source."""
        mock_source_class.side_effect = Exception("Source not found")

        response = client.get("/api/photometry/sources/NONEXISTENT/metrics")

        assert response.status_code == 404

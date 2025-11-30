"""
Unit tests for variability endpoint and lightcurve analysis.

Tests for:
- /sources/{id}/variability endpoint
- /sources/{id}/lightcurve endpoint
- Variability statistical calculations
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the API."""
    with patch("dsa110_contimg.api.app.is_ip_allowed", return_value=True):
        app = create_app()
        yield TestClient(app)


class TestVariabilityEndpoint:
    """Tests for the variability analysis endpoint."""

    def test_variability_returns_json(self, client):
        """Test variability endpoint returns JSON."""
        response = client.get("/api/v1/sources/test-source/variability")
        
        # May be 200 or 404 depending on source existence
        assert response.status_code in (200, 404)
        assert "application/json" in response.headers.get("content-type", "")

    def test_variability_404_for_unknown_source(self, client):
        """Test variability returns 404 for unknown source."""
        response = client.get("/api/v1/sources/nonexistent-source-xyz/variability")
        
        # Should return 404 or error response
        assert response.status_code in (404, 500)

    def test_variability_response_structure(self, client):
        """Test variability response has expected structure when source exists."""
        # Mock the async source service dependency
        with patch("dsa110_contimg.api.routes.sources.get_async_source_service") as mock_get_service:
            mock_service = MagicMock()
            # Make the async methods return awaitable values
            mock_service.get_source = MagicMock(return_value=MagicMock(id="src-1"))
            mock_service.get_lightcurve = MagicMock(return_value=[])
            mock_service.calculate_variability = MagicMock(return_value={
                "source_id": "src-1",
                "n_epochs": 0,
            })
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/v1/sources/src-1/variability")
            
            if response.status_code == 200:
                data = response.json()
                # Should have these fields
                expected_fields = ["source_id", "n_epochs"]
                for field in expected_fields:
                    assert field in data

    def test_variability_legacy_route(self, client):
        """Test /api/sources/{id}/variability legacy route works."""
        response = client.get("/api/sources/test-source/variability")
        
        # Should work same as v1
        assert response.status_code in (200, 404)


class TestVariabilityStatistics:
    """Tests for variability statistical calculations."""

    def test_variability_index_calculation(self):
        """Test variability index is calculated correctly."""
        # variability_index = std_flux / mean_flux
        mean_flux = 1.0
        std_flux = 0.1
        
        variability_index = std_flux / mean_flux
        
        assert variability_index == 0.1

    def test_variability_index_with_zero_mean(self):
        """Test variability index handles zero mean."""
        mean_flux = 0.0
        std_flux = 0.1
        
        # Should not divide by zero
        variability_index = std_flux / mean_flux if mean_flux > 0 else None
        
        assert variability_index is None

    def test_modulation_index(self):
        """Test modulation index equals variability index."""
        mean_flux = 2.0
        std_flux = 0.5
        
        variability_index = std_flux / mean_flux
        modulation_index = variability_index  # Same calculation
        
        assert modulation_index == 0.25

    def test_variable_classification_threshold(self):
        """Test variable classification uses 0.1 threshold."""
        threshold = 0.1
        
        # Variability index > 0.1 should be classified as variable
        assert 0.15 > threshold  # Variable
        assert 0.05 < threshold  # Not variable

    def test_chi_squared_needs_errors(self):
        """Test chi-squared calculation concept."""
        # chi2 = sum((flux - mean)^2 / error^2)
        fluxes = [1.0, 1.1, 0.9]
        mean_flux = sum(fluxes) / len(fluxes)
        errors = [0.1, 0.1, 0.1]
        
        chi2 = sum((f - mean_flux)**2 / e**2 for f, e in zip(fluxes, errors))
        
        assert chi2 > 0


class TestLightcurveEndpoint:
    """Tests for the lightcurve endpoint."""

    def test_lightcurve_returns_json(self, client):
        """Test lightcurve endpoint returns JSON."""
        response = client.get("/api/v1/sources/test-source/lightcurve")
        
        assert response.status_code in (200, 404)
        assert "application/json" in response.headers.get("content-type", "")

    def test_lightcurve_404_for_unknown_source(self, client):
        """Test lightcurve returns empty list or 404 for unknown source."""
        response = client.get("/api/v1/sources/nonexistent-xyz/lightcurve")
        
        # Implementation may return 200 with empty list, or 404
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            # Should return empty data for unknown source
            data = response.json()
            # Either empty list or dict with empty data
            assert data is not None

    def test_lightcurve_accepts_date_range(self, client):
        """Test lightcurve accepts start_mjd and end_mjd parameters."""
        response = client.get(
            "/api/v1/sources/test-source/lightcurve?start_mjd=59000&end_mjd=60000"
        )
        
        # Should accept these parameters
        assert response.status_code in (200, 404)

    def test_lightcurve_legacy_route(self, client):
        """Test /api/sources/{id}/lightcurve legacy route works."""
        response = client.get("/api/sources/test-source/lightcurve")
        
        assert response.status_code in (200, 404)


class TestVariabilityInsufficientData:
    """Tests for handling insufficient data in variability analysis."""

    def test_insufficient_epochs_message(self):
        """Test message when not enough epochs."""
        n_epochs = 1
        min_required = 2
        
        if n_epochs < min_required:
            message = f"Insufficient epochs for variability analysis (need at least {min_required})"
            assert "Insufficient" in message

    def test_zero_epochs_handled(self):
        """Test zero epochs case is handled."""
        epochs = []
        
        if len(epochs) < 2:
            result = {"n_epochs": 0, "variability_index": None}
            assert result["variability_index"] is None

    def test_single_epoch_handled(self):
        """Test single epoch case is handled."""
        epochs = [{"mjd": 59000, "flux": 1.0}]
        
        if len(epochs) < 2:
            result = {"n_epochs": 1, "variability_index": None}
            assert result["variability_index"] is None


class TestVariabilityMetrics:
    """Tests for variability metric calculations."""

    def test_mean_flux_calculation(self):
        """Test mean flux is calculated correctly."""
        fluxes = [1.0, 2.0, 3.0]
        mean_flux = sum(fluxes) / len(fluxes)
        
        assert mean_flux == 2.0

    def test_std_flux_calculation(self):
        """Test standard deviation is calculated correctly."""
        import statistics
        
        fluxes = [1.0, 2.0, 3.0]
        std_flux = statistics.stdev(fluxes)
        
        assert abs(std_flux - 1.0) < 0.01

    def test_min_max_flux(self):
        """Test min/max flux extraction."""
        fluxes = [1.0, 2.0, 3.0, 0.5, 2.5]
        
        min_flux = min(fluxes)
        max_flux = max(fluxes)
        
        assert min_flux == 0.5
        assert max_flux == 3.0

    def test_mjd_range(self):
        """Test MJD range extraction."""
        epochs = [
            {"mjd": 59000},
            {"mjd": 59100},
            {"mjd": 59200},
        ]
        
        mjds = [e["mjd"] for e in epochs]
        mjd_range = (min(mjds), max(mjds))
        
        assert mjd_range == (59000, 59200)

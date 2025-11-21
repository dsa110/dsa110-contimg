"""Unit tests for photometry normalization API endpoint.

Tests the normalize endpoint with focus on:
- Fast execution (mocked normalization functions)
- Accurate targeting of normalization logic
- Error handling and edge cases
"""

from unittest.mock import MagicMock, patch

from dsa110_contimg.api.models import (
    PhotometryNormalizeRequest,
    PhotometryNormalizeResponse,
)

# Rebuild models to resolve forward references
PhotometryNormalizeRequest.model_rebuild()


class TestPhotometryNormalizeEndpoint:
    """Test photometry normalization endpoint."""

    @patch("dsa110_contimg.photometry.normalize.query_reference_sources")
    @patch("dsa110_contimg.photometry.normalize.compute_ensemble_correction")
    @patch("dsa110_contimg.photometry.normalize.normalize_measurement")
    def test_normalize_success(self, mock_normalize, mock_compute, mock_query, tmp_path):
        """Test successful normalization."""
        from dsa110_contimg.api.routers.photometry import normalize_photometry
        from dsa110_contimg.photometry.normalize import (
            CorrectionResult,
            ReferenceSource,
        )

        # Mock request
        request = MagicMock()
        request.app.state.cfg.products_db = tmp_path / "products.sqlite3"

        # Mock reference sources
        ref_sources = [
            ReferenceSource(
                source_id=1,
                ra_deg=100.0,
                dec_deg=50.0,
                nvss_name="NVSS J100000+500000",
                nvss_flux_mjy=100.0,
                snr_nvss=100.0,
            )
        ]
        mock_query.return_value = ref_sources

        # Mock correction result
        correction = CorrectionResult(
            correction_factor=1.05,
            correction_rms=0.02,
            n_references=1,
            reference_measurements=[1.05],
            valid_references=[1],
        )
        mock_compute.return_value = correction

        # Mock normalized measurement
        mock_normalize.return_value = (0.952, 0.019)  # normalized flux, error

        # Create request body
        request_body = PhotometryNormalizeRequest(
            fits_path=str(tmp_path / "test.fits"),
            ra_deg=100.0,
            dec_deg=50.0,
            raw_flux_jy=1.0,
            raw_error_jy=0.02,
            ra_center=100.0,
            dec_center=50.0,
        )

        result = normalize_photometry(request, request_body)

        assert result.success is True
        assert result.normalized_flux_jy == 0.952
        assert result.normalized_error_jy == 0.019
        assert result.correction_factor == 1.05
        assert result.correction_rms == 0.02
        assert result.n_references == 1
        mock_query.assert_called_once()
        mock_compute.assert_called_once()
        mock_normalize.assert_called_once()

    @patch("dsa110_contimg.photometry.normalize.query_reference_sources")
    def test_normalize_no_reference_sources(self, mock_query, tmp_path):
        """Test normalization when no reference sources found."""
        from dsa110_contimg.api.routers.photometry import normalize_photometry

        request = MagicMock()
        request.app.state.cfg.products_db = tmp_path / "products.sqlite3"

        mock_query.return_value = []

        request_body = PhotometryNormalizeRequest(
            fits_path=str(tmp_path / "test.fits"),
            ra_deg=100.0,
            dec_deg=50.0,
            raw_flux_jy=1.0,
            raw_error_jy=0.02,
        )

        result = normalize_photometry(request, request_body)

        assert result.success is False
        assert result.normalized_flux_jy == 1.0  # Returns raw flux
        assert result.normalized_error_jy == 0.02
        assert result.correction_factor == 1.0
        assert result.n_references == 0
        assert "No reference sources found" in result.error_message

    @patch("dsa110_contimg.photometry.normalize.query_reference_sources")
    @patch("dsa110_contimg.photometry.normalize.compute_ensemble_correction")
    def test_normalize_exception_handling(self, mock_compute, mock_query, tmp_path):
        """Test exception handling in normalization."""
        from dsa110_contimg.api.routers.photometry import normalize_photometry

        request = MagicMock()
        request.app.state.cfg.products_db = tmp_path / "products.sqlite3"

        mock_query.side_effect = Exception("Database error")

        request_body = PhotometryNormalizeRequest(
            fits_path=str(tmp_path / "test.fits"),
            ra_deg=100.0,
            dec_deg=50.0,
            raw_flux_jy=1.0,
            raw_error_jy=0.02,
        )

        result = normalize_photometry(request, request_body)

        assert result.success is False
        assert result.normalized_flux_jy == 1.0  # Returns raw flux on error
        assert "Normalization failed" in result.error_message

    def test_normalize_request_model_validation(self):
        """Test PhotometryNormalizeRequest model validation."""
        # Valid request
        request = PhotometryNormalizeRequest(
            fits_path="/path/to/image.fits",
            ra_deg=100.0,
            dec_deg=50.0,
            raw_flux_jy=1.0,
            raw_error_jy=0.02,
        )
        assert request.fits_path == "/path/to/image.fits"
        assert request.ra_deg == 100.0
        assert request.dec_deg == 50.0

        # Test defaults
        assert request.fov_radius_deg == 1.5
        assert request.min_snr == 50.0
        assert request.max_sources == 20

    def test_normalize_response_model(self):
        """Test PhotometryNormalizeResponse model."""
        response = PhotometryNormalizeResponse(
            normalized_flux_jy=0.95,
            normalized_error_jy=0.019,
            correction_factor=1.05,
            correction_rms=0.02,
            n_references=5,
            success=True,
            error_message=None,
        )

        assert response.normalized_flux_jy == 0.95
        assert response.success is True
        assert response.error_message is None

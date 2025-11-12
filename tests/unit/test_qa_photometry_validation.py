"""
Unit tests for photometry validation module.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from dsa110_contimg.qa.photometry_validation import (
    PhotometryValidationResult,
    validate_forced_photometry,
    validate_photometry_consistency,
)
from dsa110_contimg.qa.base import ValidationInputError
from dsa110_contimg.qa.config import PhotometryConfig, get_default_config


class TestPhotometryValidationResult:
    """Test PhotometryValidationResult dataclass."""

    def test_initialization(self):
        """Test result initialization."""
        result = PhotometryValidationResult(
            passed=True,
            message="Test",
            details={},
            n_sources_validated=10,
            n_sources_passed=8,
            n_sources_failed=2,
        )
        assert result.passed is True
        assert result.n_sources_validated == 10
        assert result.n_sources_passed == 8
        assert result.n_sources_failed == 2

    def test_calculate_pass_rate(self):
        """Test pass rate calculation."""
        result = PhotometryValidationResult(
            passed=True,
            message="Test",
            details={},
            n_sources_validated=10,
            n_sources_passed=8,
        )
        assert result.calculate_pass_rate() == 0.8

    def test_calculate_pass_rate_zero(self):
        """Test pass rate with zero sources."""
        result = PhotometryValidationResult(
            passed=False,
            message="Test",
            details={},
            n_sources_validated=0,
        )
        assert result.calculate_pass_rate() == 0.0


class TestValidateForcedPhotometry:
    """Test validate_forced_photometry function."""

    def test_missing_image_file(self, tmp_path):
        """Test error when image file doesn't exist."""
        image_path = tmp_path / "nonexistent.fits"
        
        with pytest.raises(ValidationInputError):
            validate_forced_photometry(
                image_path=str(image_path),
                catalog_sources=[],
                photometry_results=[],
            )

    def test_missing_catalog_and_sources(self, tmp_path):
        """Test error when neither catalog_path nor catalog_sources provided."""
        image_path = tmp_path / "test.fits"
        image_path.touch()
        
        with pytest.raises(ValidationInputError):
            validate_forced_photometry(
                image_path=str(image_path),
                photometry_results=[],
            )

    def test_missing_photometry_results(self, tmp_path):
        """Test error when photometry_results not provided."""
        image_path = tmp_path / "test.fits"
        image_path.touch()
        
        with pytest.raises(ValidationInputError):
            validate_forced_photometry(
                image_path=str(image_path),
                catalog_sources=[],
            )

    def test_no_matches(self, tmp_path):
        """Test validation when no sources match."""
        image_path = tmp_path / "test.fits"
        image_path.touch()
        
        catalog_sources = [
            {"ra": 0.0, "dec": 0.0, "flux": 1.0, "source_id": "cat1"},
        ]
        photometry_results = [
            {"ra": 10.0, "dec": 10.0, "flux": 1.0},  # Far from catalog source
        ]
        
        result = validate_forced_photometry(
            image_path=str(image_path),
            catalog_sources=catalog_sources,
            photometry_results=photometry_results,
        )
        
        assert result.passed is False
        assert "No sources matched" in result.message

    @patch("dsa110_contimg.qa.photometry_validation.fits.open")
    def test_successful_validation(self, mock_fits, tmp_path):
        """Test successful validation with matching sources."""
        image_path = tmp_path / "test.fits"
        image_path.touch()
        
        # Mock FITS header
        mock_header = Mock()
        mock_header.__getitem__ = Mock(side_effect=lambda k: {"CRVAL1": 0.0, "CRVAL2": 0.0}.get(k, 0))
        mock_hdul = [Mock(header=mock_header)]
        mock_fits.return_value.__enter__ = Mock(return_value=mock_hdul)
        mock_fits.return_value.__exit__ = Mock(return_value=None)
        
        catalog_sources = [
            {"ra": 0.0, "dec": 0.0, "flux": 1.0, "source_id": "cat1"},
        ]
        photometry_results = [
            {"ra": 0.0, "dec": 0.0, "flux": 0.95, "flux_err": 0.05},  # Close match
        ]
        
        config = PhotometryConfig(max_flux_error_fraction=0.1, max_position_offset_arcsec=1.0)
        
        result = validate_forced_photometry(
            image_path=str(image_path),
            catalog_sources=catalog_sources,
            photometry_results=photometry_results,
            config=config,
        )
        
        # Should pass if flux error is within threshold
        assert result.n_sources_validated > 0


class TestValidatePhotometryConsistency:
    """Test validate_photometry_consistency function."""

    def test_consistency_validation(self):
        """Test consistency validation across images."""
        # Same sources measured consistently
        photometry_results_list = [
            [{"source_id": "src1", "flux": 1.0}, {"source_id": "src2", "flux": 2.0}],
            [{"source_id": "src1", "flux": 1.05}, {"source_id": "src2", "flux": 2.1}],
            [{"source_id": "src1", "flux": 0.98}, {"source_id": "src2", "flux": 1.95}],
        ]
        
        result = validate_photometry_consistency(photometry_results_list)
        
        assert isinstance(result, PhotometryValidationResult)
        assert result.flux_consistency_rms is not None


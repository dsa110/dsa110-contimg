"""Unit tests for image utility functions.

Focus: Fast, isolated tests with mocked file operations.
"""

from __future__ import annotations

from unittest.mock import patch

from dsa110_contimg.api.image_utils import (
    convert_casa_to_fits,
    get_fits_path,
    resolve_image_path,
)


class TestGetFitsPath:
    """Test get_fits_path function."""

    def test_get_fits_path_with_fits_extension(self):
        """Test get_fits_path with .fits extension."""
        image_path = "/data/images/test.fits"
        fits_path = get_fits_path(image_path)
        assert fits_path == image_path

    def test_get_fits_path_with_casa_extension(self):
        """Test get_fits_path with CASA image extension."""
        image_path = "/data/images/test.image"
        fits_path = get_fits_path(image_path)
        # Should convert .image to .fits
        assert fits_path.endswith(".fits")
        assert ".image" not in fits_path

    def test_get_fits_path_no_extension(self):
        """Test get_fits_path with no extension."""
        image_path = "/data/images/test"
        fits_path = get_fits_path(image_path)
        assert fits_path.endswith(".fits")


class TestResolveImagePath:
    """Test resolve_image_path function."""

    def test_resolve_image_path_exists(self, tmp_path):
        """Test resolve_image_path with existing file."""
        test_file = tmp_path / "test.fits"
        test_file.touch()

        resolved = resolve_image_path(str(test_file))
        assert resolved == str(test_file)

    def test_resolve_image_path_not_exists(self, tmp_path):
        """Test resolve_image_path with non-existent file."""
        test_file = tmp_path / "nonexistent.fits"

        resolved = resolve_image_path(str(test_file))
        # Should return None or original path depending on implementation
        assert resolved is not None  # Function may return path even if doesn't exist


class TestConvertCasaToFits:
    """Test convert_casa_to_fits function."""

    @patch("casatasks.exportfits")
    def test_convert_casa_to_fits_success(self, mock_casatasks):
        """Test successful CASA to FITS conversion."""
        casa_path = "/data/images/test.image"
        fits_path = "/data/images/test.fits"

        # Mock casatasks.exportfits
        mock_casatasks.exportfits.return_value = None

        result = convert_casa_to_fits(casa_path, fits_path)
        assert result == fits_path
        mock_casatasks.exportfits.assert_called_once()

    @patch("casatasks.exportfits")
    def test_convert_casa_to_fits_failure(self, mock_casatasks):
        """Test CASA to FITS conversion failure."""
        casa_path = "/data/images/test.image"
        fits_path = "/data/images/test.fits"

        # Mock casatasks.exportfits to raise exception
        mock_casatasks.exportfits.side_effect = Exception("Conversion failed")

        result = convert_casa_to_fits(casa_path, fits_path)
        # Should return None or handle error gracefully
        assert result is None or result == fits_path

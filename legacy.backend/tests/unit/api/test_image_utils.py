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

    def test_get_fits_path_with_fits_extension(self, tmp_path):
        """Test get_fits_path with .fits extension that exists."""
        # Create a real file that exists
        test_file = tmp_path / "test.fits"
        test_file.touch()
        fits_path = get_fits_path(str(test_file))
        assert fits_path is not None
        assert fits_path.endswith(".fits")

    def test_get_fits_path_with_casa_extension(self, tmp_path):
        """Test get_fits_path with CASA image extension."""
        image_path = str(tmp_path / "test.image")
        fits_path = get_fits_path(image_path)
        # Returns None if path doesn't exist and no FITS file found
        assert fits_path is None

    def test_get_fits_path_no_extension(self, tmp_path):
        """Test get_fits_path with no extension."""
        image_path = str(tmp_path / "test")
        fits_path = get_fits_path(image_path)
        # Returns None if path doesn't exist
        assert fits_path is None


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
        import pytest
        from fastapi import HTTPException

        test_file = tmp_path / "nonexistent.fits"

        # Should raise HTTPException for missing file
        with pytest.raises(HTTPException) as exc_info:
            resolve_image_path(str(test_file))
        assert exc_info.value.status_code == 404


class TestConvertCasaToFits:
    """Test convert_casa_to_fits function."""

    @patch("casatasks.exportfits")
    def test_convert_casa_to_fits_success(self, mock_casatasks, tmp_path):
        """Test successful CASA to FITS conversion."""
        # Create a directory to simulate a CASA image
        casa_dir = tmp_path / "test.image"
        casa_dir.mkdir()
        fits_path = str(tmp_path / "test.fits")

        # Mock casatasks.exportfits
        mock_casatasks.return_value = None

        result = convert_casa_to_fits(str(casa_dir), fits_path)
        # Returns True on success
        assert result is True

    @patch("casatasks.exportfits")
    def test_convert_casa_to_fits_failure(self, mock_casatasks, tmp_path):
        """Test CASA to FITS conversion failure."""
        # Non-existent path (not a directory)
        casa_path = str(tmp_path / "nonexistent.image")
        fits_path = str(tmp_path / "test.fits")

        result = convert_casa_to_fits(casa_path, fits_path)
        # Returns False if not a directory
        assert result is False

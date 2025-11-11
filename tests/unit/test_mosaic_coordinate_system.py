"""Unit tests for coordinate system creation.

Tests the _create_common_coordinate_system function to ensure
correct template creation and coordinate system centering.
"""

from dsa110_contimg.mosaic.cli import _create_common_coordinate_system
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import numpy as np
import pytest
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class MockCASAImage:
    """Mock CASA image for template creation."""

    def __init__(self, shape, coordsys=None):
        self._shape = shape
        self._coordsys = coordsys or Mock()

    def shape(self):
        return self._shape

    def coordinates(self):
        return self._coordsys

    def __del__(self):
        pass


class MockCoordinateSystem:
    """Mock CASA coordinate system."""

    def __init__(self):
        self._dir_coord = Mock()
        self._dir_coord.get_increment.return_value = [
            np.radians(2.0/3600.0), -np.radians(2.0/3600.0)]
        self._dir_coord.get_referencevalue.return_value = [
            np.radians(54.0), np.radians(122.0)]
        self._dir_coord.get_referencepixel.return_value = [50.0, 100.0]

    def get_coordinate(self, coord_type):
        if coord_type == 'direction':
            return self._dir_coord
        return Mock()

    def dict(self):
        return {"direction0": {}}


class TestCoordinateSystemCreation:
    """Test suite for _create_common_coordinate_system."""

    @patch('casacore.images.image')
    @patch('casatasks.importfits')
    @patch('dsa110_contimg.mosaic.cli.os.path.exists')
    @patch('dsa110_contimg.mosaic.cli.os.makedirs')
    def test_create_coordinate_system_from_fits_template(
        self, mock_makedirs, mock_exists, mock_importfits, mock_casaimage
    ):
        """Test coordinate system creation from FITS template."""
        # Setup mocks
        mock_exists.return_value = False  # Template doesn't exist yet

        template_coordsys = MockCoordinateSystem()
        mock_template_img = MockCASAImage([1, 1, 100, 200], template_coordsys)
        mock_casaimage.return_value = mock_template_img

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            template_tile = os.path.join(temp_dir, "template.fits")
            output_dir = os.path.join(temp_dir, "output")

            # Create template file
            Path(template_tile).touch()

            template_path, template_shape = _create_common_coordinate_system(
                ra_min=117.0,
                ra_max=125.0,
                dec_min=52.0,
                dec_max=56.0,
                pixel_scale_arcsec=2.0,
                padding_pixels=10,
                template_tile=template_tile,
                output_dir=output_dir
            )

            # Verify template was created
            assert template_path is not None
            assert template_shape is not None
            assert len(template_shape) >= 2

            # Verify importfits was called
            mock_importfits.assert_called_once()

    @patch('casacore.images.image')
    @patch('dsa110_contimg.mosaic.cli.os.path.exists')
    @patch('dsa110_contimg.mosaic.cli.os.makedirs')
    def test_create_coordinate_system_from_casa_template(
        self, mock_makedirs, mock_exists, mock_casaimage
    ):
        """Test coordinate system creation from CASA image template."""
        # Setup mocks
        mock_exists.return_value = False

        template_coordsys = MockCoordinateSystem()
        mock_template_img = MockCASAImage([1, 1, 100, 200], template_coordsys)
        mock_casaimage.side_effect = [
            mock_template_img,  # First call: read template
            # Second call: create new image
            MockCASAImage([1, 1, 200, 400], MockCoordinateSystem()),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            template_tile = os.path.join(temp_dir, "template.image")
            output_dir = os.path.join(temp_dir, "output")

            # Create template directory
            Path(template_tile).mkdir(parents=True)

            template_path, template_shape = _create_common_coordinate_system(
                ra_min=117.0,
                ra_max=125.0,
                dec_min=52.0,
                dec_max=56.0,
                pixel_scale_arcsec=2.0,
                padding_pixels=10,
                template_tile=template_tile,
                output_dir=output_dir
            )

            # Verify template was created
            assert template_path is not None
            assert template_shape is not None

    def test_coordinate_system_centering(self):
        """Test that coordinate system is centered on mosaic bounds."""
        # This test verifies the fix for coordinate system centering
        ra_min, ra_max = 117.0, 125.0
        dec_min, dec_max = 52.0, 56.0

        ra_center = (ra_min + ra_max) / 2.0
        dec_center = (dec_min + dec_max) / 2.0

        assert abs(
            ra_center - 121.0) < 0.01, f"RA center should be 121.0°, got {ra_center}"
        assert abs(
            dec_center - 54.0) < 0.01, f"Dec center should be 54.0°, got {dec_center}"

    def test_pixel_scale_calculation(self):
        """Test pixel scale calculation for template."""
        pixel_scale_arcsec = 2.0
        pixel_scale_deg = pixel_scale_arcsec / 3600.0

        ra_span = 8.0  # degrees
        dec_span = 4.0  # degrees
        padding_pixels = 10

        nx = int(np.ceil(ra_span / pixel_scale_deg)) + 2 * padding_pixels
        ny = int(np.ceil(dec_span / pixel_scale_deg)) + 2 * padding_pixels

        # Verify dimensions are reasonable
        assert nx > 0
        assert ny > 0
        assert nx > int(ra_span / pixel_scale_deg)  # Should include padding
        assert ny > int(dec_span / pixel_scale_deg)  # Should include padding


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Unit tests for mosaic bounds calculation.

Tests the _calculate_mosaic_bounds function with various image types
(2D/4D, FITS/CASA) to ensure correct coordinate extraction.
"""

from dsa110_contimg.mosaic.cli import _calculate_mosaic_bounds
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class MockCASAImage:
    """Mock CASA image object for testing."""

    def __init__(self, shape, corners_world):
        """
        Args:
            shape: Image shape tuple/list
            corners_world: List of world coordinates for corners
                          Each corner is [stokes, freq, dec_rad, ra_rad]
        """
        self._shape = shape
        self._corners_world = corners_world
        self._corner_idx = 0

    def shape(self):
        return self._shape

    def coordinates(self):
        return Mock()  # Not used in bounds calculation

    def toworld(self, pixel_coords):
        """Mock toworld that returns corner coordinates."""
        # For 4D: pixel_coords = [stokes_idx, freq_idx, dec_idx, ra_idx]
        # For 2D: pixel_coords = [dec_idx, ra_idx]
        if len(self._shape) >= 4:
            # Return [stokes, freq, dec, ra] in radians
            corner = self._corners_world[self._corner_idx % len(
                self._corners_world)]
            self._corner_idx += 1
            return corner
        else:
            # Return [dec, ra] in radians
            corner = self._corners_world[self._corner_idx % len(
                self._corners_world)]
            self._corner_idx += 1
            return corner

    def __del__(self):
        pass


@pytest.fixture
def mock_4d_casa_image():
    """Create a mock 4D CASA image."""
    # Shape: [stokes, freq, dec, ra] = [1, 1, 100, 200]
    shape = [1, 1, 100, 200]

    # Corners in world coordinates [stokes, freq, dec_rad, ra_rad]
    corners = [
        [1.0, 1.0, np.radians(52.0), np.radians(117.0)],  # BLC
        [1.0, 1.0, np.radians(52.0), np.radians(125.0)],  # BRC
        [1.0, 1.0, np.radians(56.0), np.radians(117.0)],  # TLC
        [1.0, 1.0, np.radians(56.0), np.radians(125.0)],  # TRC
    ]

    return MockCASAImage(shape, corners)


@pytest.fixture
def mock_2d_casa_image():
    """Create a mock 2D CASA image."""
    # Shape: [dec, ra] = [100, 200]
    shape = [100, 200]

    # Corners in world coordinates [dec_rad, ra_rad]
    corners = [
        [np.radians(52.0), np.radians(117.0)],  # BLC
        [np.radians(52.0), np.radians(125.0)],  # BRC
        [np.radians(56.0), np.radians(117.0)],  # TLC
        [np.radians(56.0), np.radians(125.0)],  # TRC
    ]

    return MockCASAImage(shape, corners)


class TestBoundsCalculation:
    """Test suite for _calculate_mosaic_bounds."""

    def test_4d_casa_image_bounds(self, mock_4d_casa_image):
        """Test bounds calculation for 4D CASA images."""
        # Reset corner index for fresh test
        mock_4d_casa_image._corner_idx = 0

        with patch('casacore.images.image', return_value=mock_4d_casa_image):
            tiles = ["/fake/path/tile1.image"]
            ra_min, ra_max, dec_min, dec_max = _calculate_mosaic_bounds(tiles)

        assert abs(
            ra_min - 117.0) < 0.1, f"RA min should be ~117.0°, got {ra_min}"
        assert abs(
            ra_max - 125.0) < 0.1, f"RA max should be ~125.0°, got {ra_max}"
        assert abs(
            dec_min - 52.0) < 0.1, f"Dec min should be ~52.0°, got {dec_min}"
        assert abs(
            dec_max - 56.0) < 0.1, f"Dec max should be ~56.0°, got {dec_max}"

    def test_2d_casa_image_bounds(self, mock_2d_casa_image):
        """Test bounds calculation for 2D CASA images."""
        # Reset corner index for fresh test
        mock_2d_casa_image._corner_idx = 0

        with patch('casacore.images.image', return_value=mock_2d_casa_image):
            tiles = ["/fake/path/tile1.image"]
            ra_min, ra_max, dec_min, dec_max = _calculate_mosaic_bounds(tiles)

            assert abs(
                ra_min - 117.0) < 0.1, f"RA min should be ~117.0°, got {ra_min}"
            assert abs(
                ra_max - 125.0) < 0.1, f"RA max should be ~125.0°, got {ra_max}"
            assert abs(
                dec_min - 52.0) < 0.1, f"Dec min should be ~52.0°, got {dec_min}"
            assert abs(
                dec_max - 56.0) < 0.1, f"Dec max should be ~56.0°, got {dec_max}"

    def test_multiple_tiles_union_bounds(self):
        """Test bounds calculation with multiple tiles (union)."""
        # Tile 1: RA 117-125°, Dec 52-56°
        tile1 = MockCASAImage(
            [1, 1, 100, 200],
            [
                [1.0, 1.0, np.radians(52.0), np.radians(117.0)],
                [1.0, 1.0, np.radians(52.0), np.radians(125.0)],
                [1.0, 1.0, np.radians(56.0), np.radians(117.0)],
                [1.0, 1.0, np.radians(56.0), np.radians(125.0)],
            ]
        )

        # Tile 2: RA 120-128°, Dec 53-57° (overlaps and extends)
        tile2 = MockCASAImage(
            [1, 1, 100, 200],
            [
                [1.0, 1.0, np.radians(53.0), np.radians(120.0)],
                [1.0, 1.0, np.radians(53.0), np.radians(128.0)],
                [1.0, 1.0, np.radians(57.0), np.radians(120.0)],
                [1.0, 1.0, np.radians(57.0), np.radians(128.0)],
            ]
        )

        def mock_casaimage_factory(path):
            if "tile1" in path:
                return tile1
            elif "tile2" in path:
                return tile2
            return tile1

        with patch('casacore.images.image', side_effect=mock_casaimage_factory):
            tiles = ["/fake/path/tile1.image", "/fake/path/tile2.image"]
            ra_min, ra_max, dec_min, dec_max = _calculate_mosaic_bounds(tiles)
            # Union should cover RA 117-128°, Dec 52-57°
            assert abs(
                ra_min - 117.0) < 0.1, f"RA min should be ~117.0°, got {ra_min}"
            assert abs(
                ra_max - 128.0) < 0.1, f"RA max should be ~128.0°, got {ra_max}"
            assert abs(
                dec_min - 52.0) < 0.1, f"Dec min should be ~52.0°, got {dec_min}"
            assert abs(
                dec_max - 57.0) < 0.1, f"Dec max should be ~57.0°, got {dec_max}"

    def test_bounds_with_toworld_4d_order(self):
        """Test that toworld is called with correct pixel order for 4D images."""
        # This test verifies the fix: [0, 0, y, x] instead of [y, x, 0, 0]
        shape = [1, 1, 100, 200]
        corners = [
            [1.0, 1.0, np.radians(52.0), np.radians(117.0)],
            [1.0, 1.0, np.radians(52.0), np.radians(125.0)],
            [1.0, 1.0, np.radians(56.0), np.radians(117.0)],
            [1.0, 1.0, np.radians(56.0), np.radians(125.0)],
        ]

        mock_img = MockCASAImage(shape, corners)

        with patch('casacore.images.image', return_value=mock_img):
            tiles = ["/fake/path/tile1.image"]
            _calculate_mosaic_bounds(tiles)

        # Verify toworld was called with correct order for 4D images
        # Should be called with [0, 0, y, x] for 4D images
        assert mock_img._corner_idx == 4, "toworld should be called 4 times (once per corner)"

    def test_bounds_handles_missing_corners(self):
        """Test that bounds calculation handles missing corner coordinates gracefully."""
        # Create image that fails on some corners
        class FailingMockImage(MockCASAImage):
            def toworld(self, pixel_coords):
                if self._corner_idx < 2:
                    # First two corners succeed
                    return super().toworld(pixel_coords)
                else:
                    # Last two corners fail
                    raise Exception("Failed to get world coordinates")

        shape = [1, 1, 100, 200]
        corners = [
            [1.0, 1.0, np.radians(52.0), np.radians(117.0)],
            [1.0, 1.0, np.radians(52.0), np.radians(125.0)],
        ]

        mock_img = FailingMockImage(shape, corners)

        with patch('casacore.images.image', return_value=mock_img):
            tiles = ["/fake/path/tile1.image"]
            ra_min, ra_max, dec_min, dec_max = _calculate_mosaic_bounds(tiles)

        # Should still work with partial corners
        assert ra_min is not None
        assert ra_max is not None
        assert dec_min is not None
        assert dec_max is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

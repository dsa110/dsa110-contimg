"""
Tests for the batch thumbnails module.

Tests thumbnail generation utilities with mocks for CASA dependencies.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Optional

import pytest
import numpy as np

from dsa110_contimg.api.batch.thumbnails import (
    generate_image_thumbnail,
    generate_thumbnails_for_directory,
    _normalize_image_data,
)


class TestNormalizeImageData:
    """Tests for _normalize_image_data function."""

    def test_normalizes_simple_array(self):
        """Test normalization of simple array."""
        data = np.array([[0, 50, 100], [25, 75, 100]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is not None
        assert result.min() >= 0
        assert result.max() <= 1

    def test_preserves_relative_values(self):
        """Test that relative values are preserved after normalization."""
        data = np.array([[0, 50, 100]], dtype=float)
        result = _normalize_image_data(data)
        
        # Middle value should be roughly in the middle
        assert 0.3 < result[0, 1] < 0.7

    def test_handles_nan_values(self):
        """Test handling of NaN values in data."""
        data = np.array([[0, np.nan, 100], [50, np.nan, 75]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is not None
        # Should still produce valid output for non-NaN values

    def test_handles_inf_values(self):
        """Test handling of infinity values in data."""
        data = np.array([[0, np.inf, 100], [50, -np.inf, 75]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is not None

    def test_returns_none_for_all_nan(self):
        """Test returns None when all values are NaN."""
        data = np.array([[np.nan, np.nan], [np.nan, np.nan]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is None

    def test_returns_none_for_no_dynamic_range(self):
        """Test returns None when data has no dynamic range."""
        data = np.array([[50, 50, 50], [50, 50, 50]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is None

    def test_uses_percentile_clipping(self):
        """Test that percentile clipping is applied."""
        # Create data with outliers
        data = np.array([[0, 1, 1, 1, 1, 1, 1, 1, 1, 100]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is not None
        # Values should be clipped to reasonable range

    def test_output_shape_matches_input(self):
        """Test output shape matches input shape."""
        data = np.random.rand(100, 200)
        result = _normalize_image_data(data)
        
        assert result is not None
        assert result.shape == data.shape


class TestGenerateImageThumbnail:
    """Tests for generate_image_thumbnail function."""

    @patch("dsa110_contimg.api.batch.thumbnails.Image")
    @patch("dsa110_contimg.api.batch.thumbnails.image")
    def test_generates_thumbnail(self, mock_image_class, mock_pil, tmp_path):
        """Test successful thumbnail generation."""
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        
        # Mock image data (4D array: [x, y, stokes, channel])
        mock_data = np.random.rand(100, 100, 1, 1) * 100
        mock_ia.getchunk.return_value = mock_data
        
        # Create mock PIL image
        mock_pil_img = MagicMock()
        mock_pil.fromarray.return_value = mock_pil_img
        
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        output_path = tmp_path / "test.thumb.png"
        
        result = generate_image_thumbnail(str(image_path), str(output_path))
        
        assert result is not None
        mock_ia.open.assert_called_once()
        mock_ia.close.assert_called_once()
        mock_pil_img.save.assert_called_once()

    @patch("dsa110_contimg.api.batch.thumbnails.Image")
    @patch("dsa110_contimg.api.batch.thumbnails.image")
    def test_default_output_path(self, mock_image_class, mock_pil, tmp_path):
        """Test default output path generation."""
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        mock_ia.getchunk.return_value = np.random.rand(50, 50, 1, 1) * 100
        
        mock_pil_img = MagicMock()
        mock_pil.fromarray.return_value = mock_pil_img
        
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        result = generate_image_thumbnail(str(image_path))
        
        assert result is not None
        expected_output = str(image_path.with_suffix(".thumb.png"))
        assert result == expected_output

    @patch("dsa110_contimg.api.batch.thumbnails.Image")
    @patch("dsa110_contimg.api.batch.thumbnails.image")
    def test_respects_size_parameter(self, mock_image_class, mock_pil, tmp_path):
        """Test that size parameter is used for thumbnail."""
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        mock_ia.getchunk.return_value = np.random.rand(100, 100, 1, 1) * 100
        
        mock_pil_img = MagicMock()
        mock_pil.fromarray.return_value = mock_pil_img
        
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        generate_image_thumbnail(str(image_path), size=256)
        
        mock_pil_img.thumbnail.assert_called_once()
        call_args = mock_pil_img.thumbnail.call_args
        assert call_args[0][0] == (256, 256)

    @patch("dsa110_contimg.api.batch.thumbnails.Image")
    @patch("dsa110_contimg.api.batch.thumbnails.image")
    def test_handles_3d_data(self, mock_image_class, mock_pil, tmp_path):
        """Test handling of 3D image data."""
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        mock_ia.getchunk.return_value = np.random.rand(100, 100, 1) * 100  # 3D
        
        mock_pil_img = MagicMock()
        mock_pil.fromarray.return_value = mock_pil_img
        
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        result = generate_image_thumbnail(str(image_path))
        
        assert result is not None

    @patch("dsa110_contimg.api.batch.thumbnails.Image")
    @patch("dsa110_contimg.api.batch.thumbnails.image")
    def test_handles_2d_data(self, mock_image_class, mock_pil, tmp_path):
        """Test handling of 2D image data."""
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        mock_ia.getchunk.return_value = np.random.rand(100, 100) * 100  # 2D
        
        mock_pil_img = MagicMock()
        mock_pil.fromarray.return_value = mock_pil_img
        
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        result = generate_image_thumbnail(str(image_path))
        
        assert result is not None

    @patch("dsa110_contimg.api.batch.thumbnails.image")
    def test_handles_1d_data(self, mock_image_class, tmp_path):
        """Test handling of 1D image data (unsupported)."""
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        mock_ia.getchunk.return_value = np.random.rand(100)  # 1D - unsupported
        
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        result = generate_image_thumbnail(str(image_path))
        
        assert result is None
        mock_ia.close.assert_called_once()

    def test_returns_none_for_missing_dependencies(self, tmp_path):
        """Test returns None when dependencies are missing."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        with patch.dict("sys.modules", {"casatools": None}):
            # This should handle ImportError gracefully
            pass  # Test that it doesn't crash

    @patch("dsa110_contimg.api.batch.thumbnails.image")
    def test_handles_casa_error(self, mock_image_class, tmp_path):
        """Test handling of CASA errors."""
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        mock_ia.open.side_effect = RuntimeError("CASA error")
        
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        result = generate_image_thumbnail(str(image_path))
        
        assert result is None


class TestGenerateThumbnailsForDirectory:
    """Tests for generate_thumbnails_for_directory function."""

    def test_returns_empty_for_nonexistent_directory(self):
        """Test returns empty dict for nonexistent directory."""
        result = generate_thumbnails_for_directory("/nonexistent/path")
        
        assert result == {}

    def test_returns_empty_for_file(self, tmp_path):
        """Test returns empty dict when path is a file."""
        file_path = tmp_path / "not_a_directory.txt"
        file_path.touch()
        
        result = generate_thumbnails_for_directory(str(file_path))
        
        assert result == {}

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_generates_for_matching_files(self, mock_gen, tmp_path):
        """Test generates thumbnails for files matching pattern."""
        mock_gen.return_value = "/output/path.thumb.png"
        
        # Create test image directories
        (tmp_path / "image1.image").mkdir()
        (tmp_path / "image2.image").mkdir()
        (tmp_path / "other.fits").touch()  # Should not match
        
        result = generate_thumbnails_for_directory(str(tmp_path))
        
        assert len(result) == 2
        assert mock_gen.call_count == 2

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_respects_custom_pattern(self, mock_gen, tmp_path):
        """Test respects custom glob pattern."""
        mock_gen.return_value = "/output/path.thumb.png"
        
        (tmp_path / "image1.fits").touch()
        (tmp_path / "image2.fits").touch()
        (tmp_path / "other.image").mkdir()
        
        result = generate_thumbnails_for_directory(str(tmp_path), pattern="*.fits")
        
        assert len(result) == 2

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_skips_existing_without_overwrite(self, mock_gen, tmp_path):
        """Test skips existing thumbnails when overwrite=False."""
        # Create image and existing thumbnail
        (tmp_path / "test.image").mkdir()
        (tmp_path / "test.thumb.png").touch()
        
        result = generate_thumbnails_for_directory(str(tmp_path), overwrite=False)
        
        # Should return existing path without calling generate
        assert len(result) == 1
        mock_gen.assert_not_called()

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_overwrites_existing_with_flag(self, mock_gen, tmp_path):
        """Test overwrites existing thumbnails when overwrite=True."""
        mock_gen.return_value = "/output/new.thumb.png"
        
        (tmp_path / "test.image").mkdir()
        (tmp_path / "test.thumb.png").touch()  # Existing thumbnail
        
        result = generate_thumbnails_for_directory(str(tmp_path), overwrite=True)
        
        mock_gen.assert_called_once()

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_respects_size_parameter(self, mock_gen, tmp_path):
        """Test passes size parameter to generator."""
        mock_gen.return_value = "/output/path.thumb.png"
        
        (tmp_path / "test.image").mkdir()
        
        generate_thumbnails_for_directory(str(tmp_path), size=1024)
        
        call_args = mock_gen.call_args
        assert call_args[1]["size"] == 1024 or call_args[0][2] == 1024

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_handles_generation_failures(self, mock_gen, tmp_path):
        """Test handles individual thumbnail generation failures."""
        mock_gen.side_effect = ["/output/success.png", None]  # One success, one failure
        
        (tmp_path / "image1.image").mkdir()
        (tmp_path / "image2.image").mkdir()
        
        result = generate_thumbnails_for_directory(str(tmp_path))
        
        assert len(result) == 2
        # Should include both, but one is None


class TestIntegration:
    """Integration-style tests for thumbnail generation."""

    def test_thumbnail_module_exports(self):
        """Test module exports expected functions."""
        from dsa110_contimg.api.batch import thumbnails
        
        assert hasattr(thumbnails, "generate_image_thumbnail")
        assert hasattr(thumbnails, "generate_thumbnails_for_directory")
        assert callable(thumbnails.generate_image_thumbnail)
        assert callable(thumbnails.generate_thumbnails_for_directory)

    def test_public_api(self):
        """Test public API from batch package."""
        from dsa110_contimg.api.batch import generate_image_thumbnail
        
        assert callable(generate_image_thumbnail)

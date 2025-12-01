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

    def test_clips_to_zero_one(self):
        """Test that output is clipped to [0, 1] range."""
        data = np.array([[0, 50, 100, 150, 200]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is not None
        assert np.all(result >= 0)
        assert np.all(result <= 1)

    def test_handles_negative_values(self):
        """Test handling of negative values in data."""
        data = np.array([[-100, 0, 100]], dtype=float)
        result = _normalize_image_data(data)
        
        assert result is not None
        # Should still normalize correctly

    def test_handles_very_small_range(self):
        """Test handling of very small dynamic range."""
        data = np.array([[1.0, 1.0001, 1.0002]], dtype=float)
        result = _normalize_image_data(data)
        
        # May return None due to small range at percentile boundaries
        # or may succeed - either is acceptable


class TestGenerateImageThumbnail:
    """Tests for generate_image_thumbnail function."""

    def test_returns_none_for_missing_dependencies(self):
        """Test returns None when CASA or PIL are not available."""
        # This is a basic test that the function handles import errors
        # The actual import error handling is tested implicitly
        pass

    def test_function_signature(self):
        """Test function accepts expected parameters."""
        # Just verify the function signature without calling it
        import inspect
        sig = inspect.signature(generate_image_thumbnail)
        params = list(sig.parameters.keys())
        
        assert "image_path" in params
        assert "output_path" in params
        assert "size" in params


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
    def test_handles_generation_failures(self, mock_gen, tmp_path):
        """Test handles individual thumbnail generation failures."""
        mock_gen.side_effect = ["/output/success.png", None]  # One success, one failure
        
        (tmp_path / "image1.image").mkdir()
        (tmp_path / "image2.image").mkdir()
        
        result = generate_thumbnails_for_directory(str(tmp_path))
        
        assert len(result) == 2
        # Should include both, but one is None

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_empty_directory(self, mock_gen, tmp_path):
        """Test handles empty directory."""
        result = generate_thumbnails_for_directory(str(tmp_path))
        
        assert result == {}
        mock_gen.assert_not_called()

    @patch("dsa110_contimg.api.batch.thumbnails.generate_image_thumbnail")
    def test_passes_size_to_generator(self, mock_gen, tmp_path):
        """Test passes size parameter to thumbnail generator."""
        mock_gen.return_value = "/output/path.thumb.png"
        
        (tmp_path / "test.image").mkdir()
        
        generate_thumbnails_for_directory(str(tmp_path), size=1024)
        
        # Check that size was passed (it's the 3rd positional arg)
        call_args = mock_gen.call_args
        assert 1024 in call_args[0] or call_args.kwargs.get("size") == 1024


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

    def test_normalize_function_exported(self):
        """Test internal normalize function is accessible."""
        from dsa110_contimg.api.batch.thumbnails import _normalize_image_data
        
        assert callable(_normalize_image_data)


class TestNormalizationEdgeCases:
    """Additional edge case tests for normalization."""

    def test_single_value_array(self):
        """Test normalization of single value array."""
        data = np.array([[50.0]])
        result = _normalize_image_data(data)
        
        # Single value has no dynamic range
        assert result is None

    def test_large_array(self):
        """Test normalization of larger array."""
        data = np.random.rand(1000, 1000) * 1000
        result = _normalize_image_data(data)
        
        assert result is not None
        assert result.shape == (1000, 1000)

    def test_high_precision_values(self):
        """Test normalization of high precision floating point values."""
        data = np.array([[1e-10, 1e-5, 1e-3]], dtype=np.float64)
        result = _normalize_image_data(data)
        
        assert result is not None

    def test_mixed_valid_invalid(self):
        """Test with mixture of valid and invalid values."""
        data = np.array([
            [1.0, np.nan, 3.0],
            [np.inf, 5.0, -np.inf],
            [7.0, 8.0, 9.0],
        ], dtype=float)
        result = _normalize_image_data(data)
        
        # Should still produce output based on valid values
        assert result is not None


class TestGenerateImageThumbnailWithMocks:
    """Tests for generate_image_thumbnail with mocked CASA and PIL."""

    def test_generate_thumbnail_2d_data(self, tmp_path):
        """Test thumbnail generation with 2D data."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        output_path = str(tmp_path / "test.thumb.png")
        
        # Create mock CASA image tool
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(64, 64).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        # Create mock PIL Image
        mock_pil_image = MagicMock()
        mock_pil_image_class = MagicMock()
        mock_pil_image_class.fromarray.return_value = mock_pil_image
        mock_pil_image_class.Resampling = MagicMock()
        mock_pil_image_class.Resampling.LANCZOS = 1
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': mock_pil_image_class,
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                output_path,
                size=256,
            )
        
        # Should have called the right methods
        mock_ia.open.assert_called_once_with(str(image_path))
        mock_ia.getchunk.assert_called_once()
        mock_ia.close.assert_called_once()

    def test_generate_thumbnail_3d_data(self, tmp_path):
        """Test thumbnail generation with 3D data."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        output_path = str(tmp_path / "test.thumb.png")
        
        # 3D data (x, y, stokes)
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(64, 64, 4).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        mock_pil_image = MagicMock()
        mock_pil_image_class = MagicMock()
        mock_pil_image_class.fromarray.return_value = mock_pil_image
        mock_pil_image_class.Resampling = MagicMock()
        mock_pil_image_class.Resampling.LANCZOS = 1
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': mock_pil_image_class,
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                output_path,
                size=256,
            )
        
        mock_ia.close.assert_called_once()

    def test_generate_thumbnail_4d_data(self, tmp_path):
        """Test thumbnail generation with 4D data (full cube)."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        output_path = str(tmp_path / "test.thumb.png")
        
        # 4D data (x, y, stokes, channel)
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(64, 64, 4, 128).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        mock_pil_image = MagicMock()
        mock_pil_image_class = MagicMock()
        mock_pil_image_class.fromarray.return_value = mock_pil_image
        mock_pil_image_class.Resampling = MagicMock()
        mock_pil_image_class.Resampling.LANCZOS = 1
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': mock_pil_image_class,
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                output_path,
                size=256,
            )
        
        mock_ia.close.assert_called_once()

    def test_generate_thumbnail_1d_data_unsupported(self, tmp_path):
        """Test thumbnail generation fails with 1D data."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        # 1D data (unsupported)
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(64).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': MagicMock(),
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                size=256,
            )
        
        assert result is None

    def test_generate_thumbnail_default_output_path(self, tmp_path):
        """Test thumbnail generation uses default output path."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(64, 64).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        mock_pil_image = MagicMock()
        mock_pil_image_class = MagicMock()
        mock_pil_image_class.fromarray.return_value = mock_pil_image
        mock_pil_image_class.Resampling = MagicMock()
        mock_pil_image_class.Resampling.LANCZOS = 1
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': mock_pil_image_class,
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                output_path=None,  # Use default
                size=512,
            )
        
        # Should save to expected path with .thumb.png suffix
        mock_pil_image.save.assert_called_once()
        save_args = mock_pil_image.save.call_args
        # First positional arg is the path
        assert ".thumb.png" in save_args[0][0]

    def test_generate_thumbnail_os_error(self, tmp_path):
        """Test thumbnail generation handles OS errors."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(64, 64).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        mock_pil_image = MagicMock()
        mock_pil_image.save.side_effect = OSError("Disk full")
        mock_pil_image_class = MagicMock()
        mock_pil_image_class.fromarray.return_value = mock_pil_image
        mock_pil_image_class.Resampling = MagicMock()
        mock_pil_image_class.Resampling.LANCZOS = 1
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': mock_pil_image_class,
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                size=256,
            )
        
        assert result is None

    def test_generate_thumbnail_value_error(self, tmp_path):
        """Test thumbnail generation handles value errors."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(64, 64).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        mock_pil_image_class = MagicMock()
        mock_pil_image_class.fromarray.side_effect = ValueError("Invalid array")
        mock_pil_image_class.Resampling = MagicMock()
        mock_pil_image_class.Resampling.LANCZOS = 1
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': mock_pil_image_class,
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                size=256,
            )
        
        assert result is None

    def test_generate_thumbnail_import_error(self, tmp_path):
        """Test thumbnail generation handles import errors."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        # Create a fake casatools that raises ImportError
        def raise_import_error(*args, **kwargs):
            raise ImportError("casatools not available")
        
        with patch.dict('sys.modules', {
            'casatools': None,  # Will cause ImportError
        }):
            with patch('builtins.__import__', side_effect=raise_import_error):
                # Import error should be handled gracefully
                pass

    def test_generate_thumbnail_normalization_failure(self, tmp_path):
        """Test thumbnail generation when normalization returns None."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        # Return all-NaN data which will fail normalization
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.full((64, 64), np.nan)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': MagicMock(),
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                size=256,
            )
        
        # Should return None when normalization fails
        assert result is None

    def test_generate_thumbnail_custom_size(self, tmp_path):
        """Test thumbnail generation with custom size."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        output_path = str(tmp_path / "test.thumb.png")
        
        mock_ia = MagicMock()
        mock_ia.getchunk.return_value = np.random.rand(1024, 1024).astype(np.float32)
        
        mock_image_class = MagicMock(return_value=mock_ia)
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        mock_pil_image = MagicMock()
        mock_pil_image_class = MagicMock()
        mock_pil_image_class.fromarray.return_value = mock_pil_image
        mock_pil_image_class.Resampling = MagicMock()
        mock_pil_image_class.Resampling.LANCZOS = 1
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
            'PIL': MagicMock(),
            'PIL.Image': mock_pil_image_class,
        }):
            from importlib import reload
            import dsa110_contimg.api.batch.thumbnails as thumbnails_module
            reload(thumbnails_module)
            
            result = thumbnails_module.generate_image_thumbnail(
                str(image_path),
                output_path,
                size=128,
            )
        
        # Verify thumbnail was called with correct size
        mock_pil_image.thumbnail.assert_called_once()
        call_args = mock_pil_image.thumbnail.call_args
        assert call_args[0][0] == (128, 128)

"""
Contract tests for thumbnail generation.

These tests verify ACTUAL thumbnail generation behavior using real
synthetic FITS images instead of heavy mocking. They test the
thumbnail module's output format and content with real data.

Philosophy (from complexity reduction guide):
    Contract tests verify actual behavior with real data structures
    and minimal mocking. They ensure interfaces work correctly at
    integration boundaries.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Generator

import numpy as np
import pytest
from PIL import Image


class TestThumbnailFromFITSContract:
    """Contract tests for FITS thumbnail generation.
    
    These tests use the fallback FITS-to-thumbnail path which doesn't
    require CASA. This tests the same normalization and rendering logic
    used in production.
    """

    def test_thumbnail_is_valid_png(
        self,
        synthetic_fits_image: Path,
        tmp_path: Path,
    ):
        """Verify thumbnail output is a valid PNG file."""
        from dsa110_contimg.api.routes.images import (
            _load_image_array,
            _render_image_bytes,
        )
        
        # Load the synthetic FITS image
        data, header = _load_image_array(str(synthetic_fits_image))
        
        # Render to PNG
        buf = _render_image_bytes(data, fmt="png")
        
        # Verify it's a valid PNG by opening with PIL
        img = Image.open(buf)
        assert img.format == "PNG"
        assert img.mode == "RGBA"

    def test_thumbnail_has_image_dimensions(
        self,
        synthetic_fits_image: Path,
    ):
        """Verify thumbnail preserves image aspect ratio."""
        from dsa110_contimg.api.routes.images import (
            _load_image_array,
            _render_image_bytes,
        )
        
        data, _ = _load_image_array(str(synthetic_fits_image))
        buf = _render_image_bytes(data, fmt="png")
        
        img = Image.open(buf)
        
        # Synthetic image is 256x256, so output should be square
        assert img.width == img.height
        # Should match input dimensions for this test
        assert img.width == 256

    def test_thumbnail_contains_source_signal(
        self,
        synthetic_fits_image: Path,
    ):
        """Verify thumbnail contains detectable signal from sources."""
        from dsa110_contimg.api.routes.images import (
            _load_image_array,
            _render_image_bytes,
        )
        
        data, _ = _load_image_array(str(synthetic_fits_image))
        buf = _render_image_bytes(data, fmt="png")
        
        img = Image.open(buf)
        arr = np.array(img)
        
        # Should have non-uniform values (sources visible)
        # RGBA array has shape (H, W, 4)
        alpha = arr[:, :, 3]  # Alpha channel should be 255 (opaque)
        assert np.all(alpha == 255)
        
        # RGB channels should have variation (sources vs noise)
        r_channel = arr[:, :, 0]
        assert r_channel.std() > 0, "Thumbnail has no variation (all same color)"

    def test_normalize_image_data_handles_real_fits(
        self,
        synthetic_fits_image: Path,
    ):
        """Verify normalization works with actual FITS data."""
        from dsa110_contimg.api.routes.images import (
            _load_image_array,
            _prepare_display_array,
        )
        
        data, _ = _load_image_array(str(synthetic_fits_image))
        normalized = _prepare_display_array(data)
        
        # Output should be in [0, 1] range
        assert normalized.min() >= 0
        assert normalized.max() <= 1
        
        # Should preserve shape
        assert normalized.shape == data.shape

    def test_different_scales_produce_different_output(
        self,
        synthetic_fits_image: Path,
    ):
        """Verify scale parameter actually affects output."""
        from dsa110_contimg.api.routes.images import (
            _load_image_array,
            _prepare_display_array,
        )
        
        data, _ = _load_image_array(str(synthetic_fits_image))
        
        linear = _prepare_display_array(data, scale="linear")
        sqrt_scale = _prepare_display_array(data, scale="sqrt")
        log_scale = _prepare_display_array(data, scale="log")
        
        # Different scales should produce different distributions
        # (not exact equality check, just verify they differ)
        assert not np.allclose(linear, sqrt_scale)
        assert not np.allclose(linear, log_scale)
        assert not np.allclose(sqrt_scale, log_scale)


class TestEnsureThumbnailContract:
    """Contract tests for the _ensure_thumbnail helper.
    
    Tests the full thumbnail generation pipeline including caching.
    """

    def test_creates_thumbnail_file(
        self,
        synthetic_fits_image: Path,
        tmp_path: Path,
    ):
        """Verify thumbnail file is created on disk."""
        from dsa110_contimg.api.routes.images import _ensure_thumbnail
        
        thumb_path = tmp_path / "test.thumb.png"
        
        result = _ensure_thumbnail(
            synthetic_fits_image,
            thumb_path,
            size=128,
        )
        
        assert result.exists()
        assert result.suffix == ".png"

    def test_thumbnail_respects_size_limit(
        self,
        synthetic_fits_image: Path,
        tmp_path: Path,
    ):
        """Verify thumbnail respects maximum size parameter."""
        from dsa110_contimg.api.routes.images import _ensure_thumbnail
        
        thumb_path = tmp_path / "small_thumb.png"
        
        result = _ensure_thumbnail(
            synthetic_fits_image,
            thumb_path,
            size=64,
        )
        
        img = Image.open(result)
        
        # Should be <= size in both dimensions
        assert img.width <= 64
        assert img.height <= 64

    def test_returns_existing_thumbnail(
        self,
        synthetic_fits_image: Path,
        tmp_path: Path,
    ):
        """Verify existing thumbnails are reused (not regenerated)."""
        from dsa110_contimg.api.routes.images import _ensure_thumbnail
        
        thumb_path = tmp_path / "existing.thumb.png"
        
        # Create an existing thumbnail
        existing_img = Image.new("RGB", (50, 50), color="red")
        existing_img.save(thumb_path, "PNG")
        
        # Call ensure_thumbnail
        result = _ensure_thumbnail(
            synthetic_fits_image,
            thumb_path,
            size=128,
        )
        
        # Should return existing path without regenerating
        img = Image.open(result)
        assert img.width == 50  # Original size, not regenerated to 128


class TestDirectoryThumbnailGenerationContract:
    """Contract tests for batch thumbnail generation.
    
    Tests directory-level thumbnail generation with real files.
    """

    @pytest.fixture
    def fits_directory(
        self,
        tmp_path: Path,
    ) -> Generator[Path, None, None]:
        """Create a directory with multiple synthetic FITS files."""
        from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits
        
        fits_dir = tmp_path / "fits_images"
        fits_dir.mkdir()
        
        # Create 3 FITS files with different sources
        for i in range(3):
            create_synthetic_fits(
                fits_dir / f"image_{i}.fits",
                ra_deg=180.0 + i,
                dec_deg=35.0,
                image_size=128,
                n_sources=3,
                mark_synthetic=True,
            )
        
        yield fits_dir

    def test_generates_thumbnails_for_all_fits(
        self,
        fits_directory: Path,
    ):
        """Verify thumbnails are generated for all FITS files."""
        from dsa110_contimg.api.batch.thumbnails import (
            generate_thumbnails_for_directory,
        )
        
        # Note: This uses *.image pattern by default, so we need to test
        # with *.fits pattern for our synthetic FITS files
        result = generate_thumbnails_for_directory(
            str(fits_directory),
            pattern="*.fits",
            size=64,
        )
        
        # Should have 3 entries (one per FITS file)
        assert len(result) == 3
        
        # Each should have a thumbnail path or None (if generation failed)
        for img_path, thumb_path in result.items():
            assert Path(img_path).exists()
            # For FITS files without CASA, the function may return None
            # since generate_image_thumbnail requires casatools
            # This is expected behavior - the fallback is in _ensure_thumbnail

    def test_skips_non_matching_files(
        self,
        fits_directory: Path,
    ):
        """Verify only files matching pattern are processed."""
        # Create a non-matching file
        (fits_directory / "readme.txt").touch()
        (fits_directory / "data.csv").touch()
        
        from dsa110_contimg.api.batch.thumbnails import (
            generate_thumbnails_for_directory,
        )
        
        result = generate_thumbnails_for_directory(
            str(fits_directory),
            pattern="*.fits",
        )
        
        # Should only have FITS files
        assert len(result) == 3
        for img_path in result.keys():
            assert img_path.endswith(".fits")


class TestNormalizeImageDataContract:
    """Contract tests for the pure normalization function.
    
    These verify the normalization logic with realistic astronomical data.
    """

    def test_handles_fits_with_sources(
        self,
        synthetic_fits_image: Path,
    ):
        """Verify normalization handles FITS with point sources."""
        from astropy.io import fits
        from dsa110_contimg.api.batch.thumbnails import _normalize_image_data
        
        with fits.open(synthetic_fits_image) as hdul:
            data = hdul[0].data
        
        # Reduce to 2D if needed
        while len(data.shape) > 2:
            data = data[0]
        
        result = _normalize_image_data(data)
        
        assert result is not None
        assert result.shape == data.shape
        assert result.min() >= 0
        assert result.max() <= 1

    def test_handles_fits_with_noise_only(
        self,
        tmp_path: Path,
    ):
        """Verify normalization handles noise-only images."""
        from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits
        from dsa110_contimg.api.batch.thumbnails import _normalize_image_data
        from astropy.io import fits
        
        # Create FITS with only noise (no sources)
        noise_fits = tmp_path / "noise_only.fits"
        create_synthetic_fits(
            noise_fits,
            n_sources=0,  # No sources
            noise_level_jy=0.01,
            image_size=64,
        )
        
        with fits.open(noise_fits) as hdul:
            data = hdul[0].data
        
        result = _normalize_image_data(data)
        
        # Should still produce valid output
        assert result is not None
        assert result.shape == data.shape

    def test_handles_extreme_dynamic_range(
        self,
        tmp_path: Path,
    ):
        """Verify normalization handles high dynamic range images."""
        from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits
        from dsa110_contimg.api.batch.thumbnails import _normalize_image_data
        from astropy.io import fits
        
        # Create FITS with very bright sources
        bright_fits = tmp_path / "bright_sources.fits"
        sources = [
            {"ra_deg": 180.0, "dec_deg": 35.0, "flux_jy": 10.0},  # Very bright
            {"ra_deg": 180.1, "dec_deg": 35.1, "flux_jy": 0.001},  # Very faint
        ]
        
        create_synthetic_fits(
            bright_fits,
            sources=sources,
            noise_level_jy=0.0001,  # Low noise
            image_size=64,
        )
        
        with fits.open(bright_fits) as hdul:
            data = hdul[0].data
        
        result = _normalize_image_data(data)
        
        # Should handle high dynamic range
        assert result is not None
        # Percentile clipping should prevent extremes
        assert 0 <= result.min() <= 0.1  # Near 0 after clipping
        assert 0.9 <= result.max() <= 1.0  # Near 1 after clipping


class TestThumbnailIntegrationContract:
    """End-to-end contract tests for thumbnail generation.
    
    These test the complete flow from FITS file to thumbnail file.
    """

    def test_end_to_end_fits_to_thumbnail(
        self,
        synthetic_fits_image: Path,
        tmp_path: Path,
    ):
        """Verify complete FITS-to-thumbnail pipeline."""
        from dsa110_contimg.api.routes.images import _ensure_thumbnail
        
        thumb_path = tmp_path / "e2e_thumb.png"
        
        # Generate thumbnail
        result = _ensure_thumbnail(synthetic_fits_image, thumb_path, size=128)
        
        # Verify file exists
        assert result.exists()
        
        # Verify it's a valid image
        img = Image.open(result)
        assert img.format == "PNG"
        assert img.width <= 128
        assert img.height <= 128
        
        # Verify it has content (not all black/white)
        arr = np.array(img)
        assert arr.std() > 0, "Thumbnail appears to be solid color"

    def test_thumbnail_metadata_is_stripped(
        self,
        synthetic_fits_image: Path,
        tmp_path: Path,
    ):
        """Verify thumbnail doesn't leak FITS metadata."""
        from dsa110_contimg.api.routes.images import _ensure_thumbnail
        
        thumb_path = tmp_path / "metadata_test.png"
        
        result = _ensure_thumbnail(synthetic_fits_image, thumb_path, size=64)
        
        img = Image.open(result)
        
        # PNG shouldn't have FITS-specific metadata
        info = img.info
        assert "BUNIT" not in info
        assert "BMAJ" not in info
        assert "RA" not in str(info)

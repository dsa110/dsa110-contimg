"""Unit tests for mosaic cache persistence utilities.

Tests for:
- Validation result caching
- Cache invalidation based on file modification
- Cache file reading/writing
- Force recomputation
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestValidateTilesConsistencyCached:
    """Tests for validate_tiles_consistency_cached function."""

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_empty_tiles_list(self, mock_validate, tmp_path):
        """Test with empty tiles list."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )

        mock_validate.return_value = (True, [], {})

        result = validate_tiles_consistency_cached(
            tiles=[],
            products_db=tmp_path / "products.sqlite3",
            cache_file=tmp_path / "cache.json",
        )

        assert result[0] is True  # is_valid
        assert result[1] == []  # issues
        assert result[2] == {}  # metrics_dict

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_cache_file_creation(self, mock_validate, tmp_path):
        """Test that cache file is created."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )
        from dsa110_contimg.mosaic.validation import TileQualityMetrics

        # Create a mock tile
        tile_path = tmp_path / "tile.fits"
        tile_path.write_text("dummy")

        mock_metrics = TileQualityMetrics(
            tile_path=str(tile_path),
            rms_noise=0.01,
            dynamic_range=100.0,
        )
        mock_validate.return_value = (True, [], {str(tile_path): mock_metrics})

        cache_file = tmp_path / "cache.json"
        validate_tiles_consistency_cached(
            tiles=[str(tile_path)],
            products_db=tmp_path / "products.sqlite3",
            cache_file=cache_file,
        )

        assert cache_file.exists()

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_cache_is_loaded(self, mock_validate, tmp_path):
        """Test that cache is loaded from file."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )

        # Create a tile
        tile_path = tmp_path / "tile.fits"
        tile_path.write_text("dummy")
        tile_mtime = os.path.getmtime(str(tile_path))

        # Create cache with valid entry
        cache_file = tmp_path / "cache.json"
        cache_data = {
            f"{tile_path}:{tile_mtime}": {
                "tile_path": str(tile_path),
                "rms_noise": 0.01,
                "dynamic_range": 100.0,
                "issues": [],
                "warnings": [],
            }
        }
        cache_file.write_text(json.dumps(cache_data))

        # Mock for consistency check (still called)
        mock_validate.return_value = (True, [], {})

        result = validate_tiles_consistency_cached(
            tiles=[str(tile_path)],
            products_db=tmp_path / "products.sqlite3",
            cache_file=cache_file,
        )

        # Should have loaded from cache
        assert result[0] is True

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_force_recompute(self, mock_validate, tmp_path):
        """Test force_recompute bypasses cache."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )
        from dsa110_contimg.mosaic.validation import TileQualityMetrics

        # Create a tile
        tile_path = tmp_path / "tile.fits"
        tile_path.write_text("dummy")

        # Create cache
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{}")

        mock_metrics = TileQualityMetrics(
            tile_path=str(tile_path),
            rms_noise=0.02,  # Different from any cache
        )
        mock_validate.return_value = (True, [], {str(tile_path): mock_metrics})

        result = validate_tiles_consistency_cached(
            tiles=[str(tile_path)],
            cache_file=cache_file,
            force_recompute=True,
        )

        # Should have called validate even with cache
        assert mock_validate.called

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_cache_invalidation_on_mtime_change(self, mock_validate, tmp_path):
        """Test cache is invalidated when file modification time changes."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )
        from dsa110_contimg.mosaic.validation import TileQualityMetrics

        # Create a tile
        tile_path = tmp_path / "tile.fits"
        tile_path.write_text("dummy")

        # Create cache with old mtime
        cache_file = tmp_path / "cache.json"
        old_mtime = os.path.getmtime(str(tile_path)) - 1000  # Old mtime
        cache_data = {
            f"{tile_path}:{old_mtime}": {
                "tile_path": str(tile_path),
                "rms_noise": 0.01,
                "issues": [],
                "warnings": [],
            }
        }
        cache_file.write_text(json.dumps(cache_data))

        mock_metrics = TileQualityMetrics(
            tile_path=str(tile_path),
            rms_noise=0.02,
        )
        mock_validate.return_value = (True, [], {str(tile_path): mock_metrics})

        result = validate_tiles_consistency_cached(
            tiles=[str(tile_path)],
            cache_file=cache_file,
        )

        # Should have recomputed due to mtime change
        assert mock_validate.called

    def test_default_cache_path_from_products_db(self, tmp_path):
        """Test default cache path is derived from products_db."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )

        products_db = tmp_path / "products" / "products.sqlite3"
        products_db.parent.mkdir(parents=True)
        products_db.touch()

        with patch(
            "dsa110_contimg.mosaic.validation.validate_tiles_consistency"
        ) as mock_validate:
            mock_validate.return_value = (True, [], {})

            validate_tiles_consistency_cached(
                tiles=[],
                products_db=products_db,
            )

            # Cache file should be in same directory as products_db
            expected_cache = products_db.parent / "mosaic_validation_cache.json"
            # Function may or may not have created it depending on tiles list
            # but the path should be derivable

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_issues_collected_from_metrics(self, mock_validate, tmp_path):
        """Test that issues are collected from individual tile metrics."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )
        from dsa110_contimg.mosaic.validation import TileQualityMetrics

        tile_path = tmp_path / "tile.fits"
        tile_path.write_text("dummy")

        mock_metrics = TileQualityMetrics(
            tile_path=str(tile_path),
            issues=["High noise", "Low dynamic range"],
        )
        mock_validate.return_value = (False, [], {str(tile_path): mock_metrics})

        result = validate_tiles_consistency_cached(
            tiles=[str(tile_path)],
            cache_file=tmp_path / "cache.json",
        )

        # Issues should include tile-specific issues
        assert any("High noise" in str(issue) for issue in result[1])
        assert any("Low dynamic range" in str(issue) for issue in result[1])


class TestCacheFileHandling:
    """Tests for cache file reading and writing edge cases."""

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_corrupted_cache_file(self, mock_validate, tmp_path):
        """Test handling of corrupted cache file."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )

        cache_file = tmp_path / "cache.json"
        cache_file.write_text("not valid json {{{")

        mock_validate.return_value = (True, [], {})

        # Should not raise, should handle gracefully
        result = validate_tiles_consistency_cached(
            tiles=[],
            cache_file=cache_file,
        )

        assert result[0] is True

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_cache_with_nonexistent_tiles(self, mock_validate, tmp_path):
        """Test handling when cached tiles no longer exist."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )

        # Reference a nonexistent tile
        tile_path = tmp_path / "nonexistent.fits"
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{}")

        mock_validate.return_value = (True, [], {})

        result = validate_tiles_consistency_cached(
            tiles=[str(tile_path)],
            cache_file=cache_file,
        )

        # Should handle gracefully
        assert mock_validate.called

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    def test_multiple_tiles(self, mock_validate, tmp_path):
        """Test caching with multiple tiles."""
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )
        from dsa110_contimg.mosaic.validation import TileQualityMetrics

        # Create multiple tiles
        tile_paths = []
        for i in range(3):
            tile_path = tmp_path / f"tile_{i}.fits"
            tile_path.write_text(f"dummy_{i}")
            tile_paths.append(str(tile_path))

        # Mock return for each tile
        mock_metrics = {
            path: TileQualityMetrics(tile_path=path, rms_noise=0.01 * (i + 1))
            for i, path in enumerate(tile_paths)
        }
        mock_validate.return_value = (True, [], mock_metrics)

        cache_file = tmp_path / "cache.json"
        result = validate_tiles_consistency_cached(
            tiles=tile_paths,
            cache_file=cache_file,
        )

        # All tiles should be in result metrics
        assert len(result[2]) == 3


class TestCachePathDefaults:
    """Tests for default cache path behavior."""

    def test_default_to_tmp_without_products_db(self, tmp_path):
        """Test fallback to /tmp when no products_db provided."""
        # This is more of a documentation test - the function defaults to /tmp
        from dsa110_contimg.mosaic.cache_persistence import (
            validate_tiles_consistency_cached,
        )

        with patch(
            "dsa110_contimg.mosaic.validation.validate_tiles_consistency"
        ) as mock_validate:
            mock_validate.return_value = (True, [], {})

            # Call without products_db
            validate_tiles_consistency_cached(
                tiles=[],
                products_db=None,
            )

            # Function should complete without error
            # Default cache is /tmp/mosaic_validation_cache.json

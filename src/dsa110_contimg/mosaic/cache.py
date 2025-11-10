"""
Unified caching module for mosaicking pipeline.

Provides centralized caching for expensive operations:
- Tile headers
- PB paths
- Coordinate systems
- Image statistics
- PB statistics
- Catalog queries
- Validation results
- Regridding results
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache
import time
import sqlite3
import os
import logging
import json
import hashlib
import warnings

# Use SHA256 instead of MD5 for cache keys (non-cryptographic use, but better practice)
# Suppress warning about MD5 usage since this is for cache keys, not security
warnings.filterwarnings("ignore", category=DeprecationWarning, module="hashlib")


logger = logging.getLogger(__name__)

try:
    from casacore.images import image as casaimage
    from casatasks import imhead

    HAVE_CASACORE = True
except ImportError:
    HAVE_CASACORE = False


class MosaicCache:
    """
    Unified cache manager for mosaicking operations.

    Provides in-memory and on-disk caching with automatic invalidation.
    """

    def __init__(
        self, cache_dir: Optional[Path] = None, enable_disk_cache: bool = True
    ):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for persistent cache files (None = no disk cache)
            enable_disk_cache: Whether to enable disk-based caching
        """
        self.cache_dir = cache_dir
        self.enable_disk_cache = enable_disk_cache and cache_dir is not None

        if self.enable_disk_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._headers: Dict[str, Dict[str, Any]] = {}
        self._pb_paths: Dict[str, Optional[str]] = {}
        self._coordsys: Dict[str, Any] = {}
        self._wcs_metadata: Dict[str, Dict[str, Any]] = {}
        self._image_stats: Dict[str, Dict[str, float]] = {}
        self._pb_stats: Dict[str, Dict[str, float]] = {}
        self._catalog_queries: Dict[str, List[Dict]] = {}
        self._file_metadata: Dict[str, Dict[str, Any]] = {}
        self._grid_consistency: Dict[Tuple, Dict[str, Any]] = {}

    def _get_cache_key(self, file_path: str, include_mtime: bool = True) -> str:
        """Generate cache key with optional mtime."""
        if include_mtime:
            try:
                mtime = os.path.getmtime(file_path)
                return f"{file_path}:{mtime}"
            except OSError:
                return f"{file_path}:0"
        return file_path

    def _get_disk_cache_path(self, cache_type: str, key: str) -> Path:
        """Get disk cache file path."""
        if not self.enable_disk_cache:
            return None

        # Create hash of key for filename (non-cryptographic, but use SHA256)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{cache_type}_{key_hash}.cache"

    def _load_disk_cache(self, cache_path: Path) -> Optional[Any]:
        """Load data from disk cache."""
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cache_data = json.load(f)
                # Check if cache is expired (7 days default)
                if cache_data.get("expires", float("inf")) < time.time():
                    cache_path.unlink()
                    return None
                return cache_data.get("data")
        except Exception as e:
            logger.debug(f"Failed to load cache {cache_path}: {e}")
            return None

    def _save_disk_cache(self, cache_path: Path, data: Any, expire_days: int = 7):
        """Save data to disk cache."""
        if not self.enable_disk_cache:
            return

        try:
            cache_data = {
                "data": data,
                "created": time.time(),
                "expires": time.time() + (expire_days * 24 * 3600),
            }
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, default=str)
        except Exception as e:
            logger.debug(f"Failed to save cache {cache_path}: {e}")

    # Header caching
    def get_tile_header(self, tile_path: str) -> Optional[Dict[str, Any]]:
        """Get and cache tile header."""
        cache_key = self._get_cache_key(tile_path)

        if cache_key in self._headers:
            return self._headers[cache_key]

        # Check disk cache
        if self.enable_disk_cache:
            cache_path = self._get_disk_cache_path("header", cache_key)
            cached = self._load_disk_cache(cache_path)
            if cached is not None:
                self._headers[cache_key] = cached
                return cached

        # Compute
        if not HAVE_CASACORE:
            return None

        try:
            from .error_handling import safe_imhead

            header = safe_imhead(imagename=tile_path, mode="list")
            self._headers[cache_key] = header

            # Save to disk
            if self.enable_disk_cache:
                self._save_disk_cache(cache_path, header)

            return header
        except Exception as e:
            logger.debug(f"Failed to get header for {tile_path}: {e}")
            return None

    # PB path caching
    def get_pb_path(self, tile_path: str, find_func) -> Optional[str]:
        """Get and cache PB path."""
        cache_key = self._get_cache_key(tile_path, include_mtime=False)

        if cache_key in self._pb_paths:
            return self._pb_paths[cache_key]

        # Check disk cache
        if self.enable_disk_cache:
            cache_path = self._get_disk_cache_path("pb_path", cache_key)
            cached = self._load_disk_cache(cache_path)
            if cached is not None:
                self._pb_paths[cache_key] = cached
                return cached

        # Compute
        pb_path = find_func(tile_path)
        self._pb_paths[cache_key] = pb_path

        # Save to disk
        if self.enable_disk_cache:
            self._save_disk_cache(cache_path, pb_path)

        return pb_path

    # Coordinate system caching
    def get_tile_coordsys(self, tile_path: str) -> Optional[Any]:
        """Get and cache tile coordinate system."""
        cache_key = self._get_cache_key(tile_path)

        if cache_key in self._coordsys:
            return self._coordsys[cache_key]

        if not HAVE_CASACORE:
            return None

        try:
            img = casaimage(tile_path)
            # Try coordsys() first (for CASA image directories)
            try:
                coordsys = img.coordsys()
            except AttributeError:
                # Fallback to coordinates() for FITS files
                coordsys = img.coordinates()
            # Try to close image (may not exist for FITS files)
            try:
                img.close()
            except AttributeError:
                pass  # FITS files don't have close() method
            self._coordsys[cache_key] = coordsys
            return coordsys
        except Exception as e:
            logger.debug(f"Failed to get coordsys for {tile_path}: {e}")
            return None

    def get_tile_wcs_metadata(self, tile_path: str) -> Dict[str, Any]:
        """Get cached WCS metadata (center, increment, shape)."""
        cache_key = self._get_cache_key(tile_path)

        if cache_key in self._wcs_metadata:
            return self._wcs_metadata[cache_key]

        # Check disk cache
        if self.enable_disk_cache:
            cache_path = self._get_disk_cache_path("wcs_metadata", cache_key)
            cached = self._load_disk_cache(cache_path)
            if cached is not None:
                self._wcs_metadata[cache_key] = cached
                return cached

        # Compute
        coordsys = self.get_tile_coordsys(tile_path)
        if not coordsys:
            return {}

        try:
            # Try direct methods first (for coordsys() objects from CASA image directories)
            try:
                ref_val = coordsys.referencevalue()
                incr = coordsys.increment()
            except AttributeError:
                # Fallback to get_* methods (for coordinates() objects from FITS files)
                ref_val = coordsys.get_referencevalue()
                incr = coordsys.get_increment()

            # Extract scalar values, handling both scalars and arrays
            def to_scalar(val):
                """Convert value to scalar float, handling numpy arrays."""
                if isinstance(val, np.ndarray):
                    return float(val[0] if val.size > 0 else 0.0)
                return float(val)

            header = self.get_tile_header(tile_path)
            shape = header.get("shape") if header else None

            # Extract RA/Dec values, handling arrays
            ra_val = ref_val[0] if len(ref_val) >= 1 else None
            dec_val = ref_val[1] if len(ref_val) >= 2 else None
            ra_incr = incr[0] if len(incr) >= 1 else None
            dec_incr = incr[1] if len(incr) >= 2 else None

            metadata = {
                "ra_center": to_scalar(ra_val) if ra_val is not None else None,
                "dec_center": to_scalar(dec_val) if dec_val is not None else None,
                "cdelt_ra": (
                    to_scalar(ra_incr) * 180.0 / np.pi if ra_incr is not None else None
                ),
                "cdelt_dec": (
                    to_scalar(dec_incr) * 180.0 / np.pi
                    if dec_incr is not None
                    else None
                ),
                "shape": shape,
            }

            self._wcs_metadata[cache_key] = metadata

            # Save to disk
            if self.enable_disk_cache:
                self._save_disk_cache(cache_path, metadata)

            return metadata
        except Exception as e:
            logger.debug(f"Failed to get WCS metadata for {tile_path}: {e}")
            return {}

    def get_tile_shape(self, tile_path: str) -> Optional[Tuple[int, ...]]:
        """Get tile shape from cached header."""
        header = self.get_tile_header(tile_path)
        if header:
            shape = header.get("shape")
            if shape:
                return tuple(shape) if isinstance(shape, (list, tuple)) else shape
        return None

    # Image statistics caching
    def get_tile_statistics(
        self, tile_path: str, force_recompute: bool = False
    ) -> Dict[str, float]:
        """Get cached tile statistics (RMS, dynamic range, etc.)."""
        cache_key = self._get_cache_key(tile_path)

        if cache_key in self._image_stats and not force_recompute:
            return self._image_stats[cache_key]

        # Check disk cache
        if self.enable_disk_cache and not force_recompute:
            cache_path = self._get_disk_cache_path("image_stats", cache_key)
            cached = self._load_disk_cache(cache_path)
            if cached is not None:
                self._image_stats[cache_key] = cached
                return cached

        # Compute
        if not HAVE_CASACORE:
            return {}

        try:
            img = casaimage(tile_path)
            data = img.getdata()
            valid_pixels = data[np.isfinite(data)]
            img.close()

            if len(valid_pixels) > 0:
                rms_noise = float(np.std(valid_pixels))
                peak_value = float(np.abs(valid_pixels).max())
                dynamic_range = peak_value / rms_noise if rms_noise > 0 else 0.0

                stats = {
                    "rms_noise": rms_noise,
                    "peak_flux": peak_value,
                    "dynamic_range": dynamic_range,
                    "num_pixels": len(valid_pixels),
                }

                self._image_stats[cache_key] = stats

                # Save to disk
                if self.enable_disk_cache:
                    self._save_disk_cache(cache_path, stats)

                return stats
        except Exception as e:
            logger.debug(f"Failed to get statistics for {tile_path}: {e}")

        return {}

    # PB statistics caching
    def get_pb_statistics(self, pb_path: str) -> Dict[str, float]:
        """Get cached PB response statistics."""
        cache_key = self._get_cache_key(pb_path)

        if cache_key in self._pb_stats:
            return self._pb_stats[cache_key]

        # Check disk cache
        if self.enable_disk_cache:
            cache_path = self._get_disk_cache_path("pb_stats", cache_key)
            cached = self._load_disk_cache(cache_path)
            if cached is not None:
                self._pb_stats[cache_key] = cached
                return cached

        # Compute
        if not HAVE_CASACORE:
            return {}

        try:
            pb_img = casaimage(pb_path)
            pb_data = pb_img.getdata()
            valid_pb = pb_data[np.isfinite(pb_data) & (pb_data > 0)]
            pb_img.close()

            if len(valid_pb) > 0:
                stats = {
                    "pb_response_min": float(valid_pb.min()),
                    "pb_response_max": float(valid_pb.max()),
                    "pb_response_mean": float(valid_pb.mean()),
                    "pb_response_median": float(np.median(valid_pb)),
                }

                self._pb_stats[cache_key] = stats

                # Save to disk
                if self.enable_disk_cache:
                    self._save_disk_cache(cache_path, stats)

                return stats
        except Exception as e:
            logger.debug(f"Failed to get PB statistics for {pb_path}: {e}")

        return {}

    # Catalog query caching
    def query_catalog_cached(
        self,
        ra_deg: float,
        dec_deg: float,
        radius_deg: float,
        catalog_name: str,
        query_func,
    ) -> List[Dict]:
        """Query catalog with caching based on sky region."""
        # Use SHA256 for cache keys (non-cryptographic, but better practice)
        cache_key = hashlib.sha256(
            f"{catalog_name}:{ra_deg:.6f}:{dec_deg:.6f}:{radius_deg:.6f}".encode()
        ).hexdigest()

        if cache_key in self._catalog_queries:
            return self._catalog_queries[cache_key]

        # Check disk cache
        if self.enable_disk_cache:
            cache_path = self._get_disk_cache_path("catalog_query", cache_key)
            cached = self._load_disk_cache(cache_path)
            if cached is not None:
                self._catalog_queries[cache_key] = cached
                return cached

        # Query
        sources = query_func(ra_deg, dec_deg, radius_deg, catalog_name)
        self._catalog_queries[cache_key] = sources

        # Save to disk
        if self.enable_disk_cache:
            # Longer expiry for catalog
            self._save_disk_cache(cache_path, sources, expire_days=30)

        return sources

    # File metadata caching
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get cached file metadata."""
        if file_path in self._file_metadata:
            return self._file_metadata[file_path]

        path = Path(file_path)
        metadata = {
            "exists": path.exists(),
            "mtime": path.stat().st_mtime if path.exists() else None,
            "size": path.stat().st_size if path.exists() else None,
            "isdir": path.is_dir() if path.exists() else False,
        }

        self._file_metadata[file_path] = metadata
        return metadata

    # Grid consistency caching
    def get_reference_grid(self, tiles: List[str]) -> Optional[Dict[str, Any]]:
        """Get cached reference grid for tile set."""
        cache_key = tuple(sorted(tiles))

        if cache_key in self._grid_consistency:
            return self._grid_consistency[cache_key]

        if not tiles:
            return None

        # Compute reference grid from first tile
        header = self.get_tile_header(tiles[0])
        if header:
            grid_info = {
                "shape": header.get("shape"),
                "cdelt1": header.get("cdelt1"),
                "cdelt2": header.get("cdelt2"),
                "ref_tile": tiles[0],
            }
            self._grid_consistency[cache_key] = grid_info
            return grid_info

        return None

    # Cache management
    def clear(self, cache_type: Optional[str] = None):
        """Clear caches."""
        if cache_type is None:
            # Clear all
            self._headers.clear()
            self._pb_paths.clear()
            self._coordsys.clear()
            self._wcs_metadata.clear()
            self._image_stats.clear()
            self._pb_stats.clear()
            self._catalog_queries.clear()
            self._file_metadata.clear()
            self._grid_consistency.clear()

            # Clear disk cache
            if self.enable_disk_cache:
                for f in self.cache_dir.glob("*.cache"):
                    f.unlink()
        else:
            # Clear specific cache type
            if cache_type == "headers":
                self._headers.clear()
            elif cache_type == "pb_paths":
                self._pb_paths.clear()
            # ... etc

    def cleanup_disk_cache(self, max_age_days: int = 7):
        """Clean up old disk cache files."""
        if not self.enable_disk_cache:
            return

        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        cleaned = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    cleaned += 1
            except Exception:
                pass

        logger.info(f"Cleaned up {cleaned} old cache files")

    # Regridding results caching
    def get_regridded_image(
        self, source_path: str, template_path: str, regrid_func, output_suffix: str = ""
    ) -> Optional[str]:
        """
        Get cached regridded image or create if needed.

        Args:
            source_path: Source image path
            template_path: Template image path for regridding
            regrid_func: Function to perform regridding (imregrid wrapper)
            output_suffix: Optional suffix for output filename

        Returns:
            Path to regridded image (cached or newly created)
        """
        if not self.enable_disk_cache:
            # No disk cache, can't cache regridded images
            return None

        try:
            source_mtime = os.path.getmtime(source_path)
            template_mtime = os.path.getmtime(template_path)

            # Use SHA256 for cache keys (non-cryptographic, but better practice)
            cache_key = hashlib.sha256(
                f"{source_path}:{source_mtime}:{template_path}:{template_mtime}{output_suffix}".encode()
            ).hexdigest()

            cached_path = self.cache_dir / f"regrid_{cache_key}.image"

            if cached_path.exists():
                return str(cached_path)

            # Regrid and cache
            try:
                regrid_func(
                    imagename=source_path,
                    template=template_path,
                    output=str(cached_path),
                    overwrite=True,
                )
                return str(cached_path)
            except Exception as e:
                logger.debug(f"Failed to regrid and cache {source_path}: {e}")
                return None
        except Exception:
            return None


# Global cache instance
_global_cache: Optional[MosaicCache] = None


def get_cache(
    cache_dir: Optional[Path] = None, enable_disk_cache: bool = True
) -> MosaicCache:
    """Get or create global cache instance."""
    global _global_cache

    if _global_cache is None:
        if cache_dir is None:
            # Default cache directory
            cache_dir = Path(os.getenv("MOSAIC_CACHE_DIR", "/tmp/mosaic_cache"))

        _global_cache = MosaicCache(
            cache_dir=cache_dir, enable_disk_cache=enable_disk_cache
        )

    return _global_cache


def clear_cache(cache_type: Optional[str] = None):
    """Clear global cache."""
    if _global_cache:
        _global_cache.clear(cache_type)

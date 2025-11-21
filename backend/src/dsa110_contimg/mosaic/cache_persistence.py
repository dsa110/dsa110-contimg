"""
Validation results persistence for mosaicking pipeline.

Provides persistent caching of validation results to avoid recomputation.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from .validation import TileQualityMetrics

logger = logging.getLogger(__name__)


def validate_tiles_consistency_cached(
    tiles: List[str],
    products_db: Optional[Path] = None,
    cache_file: Optional[Path] = None,
    force_recompute: bool = False,
) -> tuple:
    """
    Validate tiles with persistent caching.

    Caches validation results to disk to avoid recomputation on repeated runs.
    Cache is invalidated based on file modification times.

    Args:
        tiles: List of tile paths
        products_db: Optional products database
        cache_file: Optional cache file path (defaults to products_db parent)
        force_recompute: Force recomputation even if cache exists

    Returns:
        (is_valid, issues, metrics_dict) as per validate_tiles_consistency
    """
    from .validation import validate_tiles_consistency

    # Determine cache file path
    if cache_file is None:
        if products_db:
            cache_file = products_db.parent / "mosaic_validation_cache.json"
        else:
            cache_file = Path("/tmp/mosaic_validation_cache.json")

    cache_file = Path(cache_file)

    # Load cache
    cache_data = {}
    if cache_file.exists() and not force_recompute:
        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load validation cache: {e}")

    # Validate each tile with cache lookup
    metrics_dict = {}
    all_issues = []
    tiles_to_recompute = []

    for tile in tiles:
        # Check cache validity
        tile_mtime = os.path.getmtime(tile) if os.path.exists(tile) else 0
        cache_key = f"{tile}:{tile_mtime}"

        if cache_key in cache_data and not force_recompute:
            # Load from cache
            try:
                cached_metrics = cache_data[cache_key]
                metrics = TileQualityMetrics(
                    tile_path=cached_metrics.get("tile_path", tile),
                    pbcor_path=cached_metrics.get("pbcor_path"),
                    pb_path=cached_metrics.get("pb_path"),
                    rms_noise=cached_metrics.get("rms_noise"),
                    dynamic_range=cached_metrics.get("dynamic_range"),
                    has_artifacts=cached_metrics.get("has_artifacts", False),
                    pbcor_applied=cached_metrics.get("pbcor_applied", False),
                    pb_response_min=cached_metrics.get("pb_response_min"),
                    pb_response_max=cached_metrics.get("pb_response_max"),
                    ms_path=cached_metrics.get("ms_path"),
                    calibration_applied=cached_metrics.get("calibration_applied", False),
                    ra_center=cached_metrics.get("ra_center"),
                    dec_center=cached_metrics.get("dec_center"),
                    issues=cached_metrics.get("issues", []),
                    warnings=cached_metrics.get("warnings", []),
                )
                metrics_dict[tile] = metrics
            except Exception as e:
                logger.debug(f"Failed to load cached metrics for {tile}: {e}")
                tiles_to_recompute.append(tile)
        else:
            tiles_to_recompute.append(tile)

    # Recompute for tiles not in cache
    if tiles_to_recompute:
        logger.info(f"Recomputing validation for {len(tiles_to_recompute)} tiles")
        _, _, recomputed_metrics = validate_tiles_consistency(tiles_to_recompute, products_db)

        # Update cache and metrics dict
        for tile in tiles_to_recompute:
            if tile in recomputed_metrics:
                metrics = recomputed_metrics[tile]
                tile_mtime = os.path.getmtime(tile) if os.path.exists(tile) else 0
                cache_key = f"{tile}:{tile_mtime}"

                # Store in cache (convert to dict for JSON serialization)
                cache_data[cache_key] = {
                    "tile_path": metrics.tile_path,
                    "pbcor_path": metrics.pbcor_path,
                    "pb_path": metrics.pb_path,
                    "rms_noise": metrics.rms_noise,
                    "dynamic_range": metrics.dynamic_range,
                    "has_artifacts": metrics.has_artifacts,
                    "pbcor_applied": metrics.pbcor_applied,
                    "pb_response_min": metrics.pb_response_min,
                    "pb_response_max": metrics.pb_response_max,
                    "ms_path": metrics.ms_path,
                    "calibration_applied": metrics.calibration_applied,
                    "ra_center": metrics.ra_center,
                    "dec_center": metrics.dec_center,
                    "issues": metrics.issues,
                    "warnings": metrics.warnings,
                }

                metrics_dict[tile] = metrics

    # Save cache
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(cache_data, f, indent=2, default=str)
    except Exception as e:
        logger.debug(f"Failed to save validation cache: {e}")

    # Collect issues
    for tile, metrics in metrics_dict.items():
        if metrics.issues:
            all_issues.extend([f"{tile}: {issue}" for issue in metrics.issues])

    # Continue with consistency checks (grid, noise, beam, etc.)
    # This part still needs to be done fresh
    from .validation import validate_tiles_consistency

    _, consistency_issues, _ = validate_tiles_consistency(tiles, products_db=None)
    all_issues.extend(consistency_issues)

    return len(all_issues) == 0, all_issues, metrics_dict

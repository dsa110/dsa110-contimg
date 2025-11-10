"""
Pre-flight validation functions for mosaic building.

Validates all pre-conditions before expensive operations,
adhering to "measure twice, cut once" philosophy.
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional

from .validation import TileQualityMetrics, _find_pb_path
from .error_handling import check_disk_space

logger = logging.getLogger(__name__)


def validate_preflight_conditions(
    tiles: List[str],
    output_path: str,
    metrics_dict: Optional[Dict[str, TileQualityMetrics]] = None,
    require_pb: bool = True,
    check_disk_space_flag: bool = True,
) -> Tuple[bool, List[str], Dict[str, any]]:
    """
    Validate all pre-conditions before expensive operations.

    Performs fast checks that should pass before starting:
    - All tile files exist
    - All PB images exist (if required)
    - Output directory exists/is writable
    - Output path doesn't conflict (or warn if overwriting)
    - Disk space available
    - Write permissions

    Args:
        tiles: List of tile paths
        output_path: Output mosaic path
        metrics_dict: Optional pre-computed TileQualityMetrics dict
        require_pb: Require PB images for all tiles
        check_disk_space_flag: Whether to check disk space

    Returns:
        (is_valid, issues, info_dict) where info_dict contains validation info
    """
    issues = []
    info = {
        "tiles_exist": 0,
        "tiles_missing": 0,
        "pb_images_exist": 0,
        "pb_images_missing": 0,
        "output_dir_writable": False,
        "output_exists": False,
        "disk_space_ok": False,
    }

    # Check all tiles exist
    logger.info(f"Pre-flight check: Verifying {len(tiles)} tiles exist...")
    missing_tiles = []
    for tile in tiles:
        if os.path.exists(tile):
            info["tiles_exist"] += 1
        else:
            info["tiles_missing"] += 1
            missing_tiles.append(tile)

    if missing_tiles:
        issues.append(
            f"{len(missing_tiles)} tiles not found: {missing_tiles[:5]}"
            + (
                f" ... and {len(missing_tiles)-5} more"
                if len(missing_tiles) > 5
                else ""
            )
        )

    # Check PB images exist (if required)
    if require_pb:
        logger.info("Pre-flight check: Verifying PB images exist...")
        missing_pb = []
        for tile in tiles:
            pb_path = None
            if metrics_dict and tile in metrics_dict:
                pb_path = metrics_dict[tile].pb_path

            if not pb_path:
                pb_path = _find_pb_path(tile)

            if pb_path and os.path.exists(pb_path):
                info["pb_images_exist"] += 1
            else:
                info["pb_images_missing"] += 1
                missing_pb.append(tile)

        if missing_pb:
            issues.append(
                f"{len(missing_pb)} tiles missing PB images: {missing_pb[:5]}"
                + (f" ... and {len(missing_pb)-5} more" if len(missing_pb) > 5 else "")
            )

    # Check output directory
    output_path_obj = Path(output_path)
    output_dir = output_path_obj.parent if output_path_obj.suffix else output_path_obj

    logger.info(f"Pre-flight check: Verifying output directory '{output_dir}'...")

    # Check if output directory exists or can be created
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        info["output_dir_writable"] = True

        # Check write permissions
        test_file = output_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            issues.append(f"Output directory not writable: {output_dir} ({e})")
            info["output_dir_writable"] = False
    except Exception as e:
        issues.append(f"Cannot create output directory: {output_dir} ({e})")

    # Check if output already exists
    if (
        output_path_obj.exists()
        or (output_path_obj.parent / f"{output_path_obj.name}.fits").exists()
    ):
        info["output_exists"] = True
        # Don't fail, but warn - overwrite is allowed

    # Check disk space
    if check_disk_space_flag:
        logger.info("Pre-flight check: Verifying disk space...")
        try:
            # Estimate: ~300MB per tile for regridding + output
            estimated_gb = len(tiles) * 0.3
            has_space, space_msg = check_disk_space(
                str(output_path), required_gb=estimated_gb, operation="preflight_check"
            )
            info["disk_space_ok"] = has_space
            if not has_space:
                issues.append(space_msg)
            else:
                logger.debug(space_msg)
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            # Don't fail on disk space check errors

    # Summary
    if issues:
        logger.warning(f"Pre-flight validation found {len(issues)} issues")
    else:
        logger.info("✓ Pre-flight validation passed")

    return len(issues) == 0, issues, info


def estimate_resources(
    tiles: List[str],
    output_path: str,
) -> Dict[str, any]:
    """
    Estimate resource requirements for mosaic building.

    Args:
        tiles: List of tile paths
        output_path: Output mosaic path

    Returns:
        Dictionary with resource estimates
    """
    estimates = {
        "num_tiles": len(tiles),
        "estimated_disk_gb": len(tiles) * 0.3,  # ~300MB per tile
        "estimated_operations": len(tiles) * 2,  # PB regrid + tile regrid per tile
        "estimated_time_minutes": len(tiles) * 2,  # Rough estimate: 2 min per tile
    }

    # More accurate disk space estimate if we can check tile sizes
    try:
        total_size_mb = 0
        for tile in tiles[:10]:  # Sample first 10 tiles
            if os.path.exists(tile):
                if os.path.isdir(tile):
                    # CASA image directory
                    import shutil

                    try:
                        size = sum(
                            f.stat().st_size
                            for f in Path(tile).rglob("*")
                            if f.is_file()
                        )
                        total_size_mb += size / (1024**2)
                    except Exception:
                        pass
                else:
                    # FITS file
                    try:
                        total_size_mb += os.path.getsize(tile) / (1024**2)
                    except Exception:
                        pass

        if total_size_mb > 0:
            avg_size_mb = total_size_mb / min(10, len(tiles))
            # Estimate: 3x tile size (regridding + output)
            estimates["estimated_disk_gb"] = (avg_size_mb * len(tiles) * 3) / 1024
            estimates["estimated_disk_gb"] = max(
                estimates["estimated_disk_gb"], 0.1
            )  # Minimum 100MB
    except Exception:
        pass  # Keep default estimate

    return estimates

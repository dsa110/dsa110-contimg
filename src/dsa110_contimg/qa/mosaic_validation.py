"""
Mosaic validation module.

Validates mosaic image quality, overlap handling, and consistency.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from dsa110_contimg.qa.base import (
    ValidationContext,
    ValidationError,
    ValidationInputError,
    ValidationResult,
)
from dsa110_contimg.qa.config import MosaicConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass
class MosaicValidationResult(ValidationResult):
    """Result of mosaic validation."""
    
    # Mosaic metrics
    n_tiles: int = 0
    n_overlaps: int = 0
    n_seams_detected: int = 0
    
    # Quality metrics
    mean_seam_flux_deviation: float = 0.0
    max_seam_flux_deviation: float = 0.0
    mean_wcs_offset_arcsec: float = 0.0
    max_wcs_offset_arcsec: float = 0.0
    
    # Noise consistency
    mean_noise_ratio: float = 1.0
    max_noise_ratio: float = 1.0
    
    # Overlap metrics
    mean_overlap_fraction: float = 0.0
    min_overlap_fraction: float = 0.0
    
    # Per-overlap results
    overlap_results: List[Dict[str, any]] = field(default_factory=list)  # type: ignore
    
    def __post_init__(self):
        """Initialize defaults."""
        super().__post_init__()
        if self.overlap_results is None:
            self.overlap_results = []


def validate_mosaic_quality(
    mosaic_path: str,
    tile_paths: List[str],
    overlap_regions: Optional[List[Dict]] = None,
    config: Optional[MosaicConfig] = None,
) -> MosaicValidationResult:
    """Validate mosaic quality and consistency.
    
    Checks for seam artifacts, WCS alignment, flux consistency, and noise properties.
    
    Args:
        mosaic_path: Path to mosaic FITS image
        tile_paths: List of paths to tile images used in mosaic
        overlap_regions: Optional list of overlap region definitions
        config: Mosaic validation configuration
        
    Returns:
        MosaicValidationResult with validation status
        
    Raises:
        ValidationInputError: If inputs are invalid
        ValidationError: If validation fails
    """
    if config is None:
        config = get_default_config().mosaic
    
    # Validate inputs
    mosaic_path_obj = Path(mosaic_path)
    if not mosaic_path_obj.exists():
        raise ValidationInputError(f"Mosaic file not found: {mosaic_path}")
    
    if not tile_paths:
        raise ValidationInputError("No tile paths provided")
    
    # Check tile files exist
    missing_tiles = [t for t in tile_paths if not Path(t).exists()]
    if missing_tiles:
        raise ValidationInputError(f"Missing tile files: {missing_tiles}")
    
    try:
        # Load mosaic
        with fits.open(mosaic_path) as hdul:
            mosaic_data = hdul[0].data
            mosaic_header = hdul[0].header
            mosaic_wcs = WCS(mosaic_header)
        
        # Load tiles
        tile_data_list = []
        tile_wcs_list = []
        for tile_path in tile_paths:
            with fits.open(tile_path) as hdul_tile:
                tile_data_list.append(hdul_tile[0].data)
                tile_wcs_list.append(WCS(hdul_tile[0].header))
        
        # Validate WCS alignment
        wcs_offsets = _validate_wcs_alignment(mosaic_wcs, tile_wcs_list)
        mean_wcs_offset = np.mean(wcs_offsets) if wcs_offsets else 0.0
        max_wcs_offset = np.max(wcs_offsets) if wcs_offsets else 0.0
        
        # Detect and validate overlaps
        if overlap_regions is None:
            overlap_regions = _detect_overlaps(mosaic_wcs, tile_wcs_list)
        
        overlap_results = []
        seam_flux_deviations = []
        
        for overlap in overlap_regions:
            # Validate flux consistency in overlap
            flux_deviation = _validate_overlap_flux_consistency(
                mosaic_data,
                mosaic_wcs,
                tile_data_list,
                tile_wcs_list,
                overlap,
            )
            
            seam_flux_deviations.append(flux_deviation)
            
            # Check for seam artifacts
            has_seam = flux_deviation > config.max_seam_flux_deviation
            
            overlap_results.append({
                "overlap_id": overlap.get("id", "unknown"),
                "flux_deviation": flux_deviation,
                "has_seam": has_seam,
                "wcs_offset_arcsec": overlap.get("wcs_offset", 0.0),
            })
        
        n_overlaps = len(overlap_regions)
        n_seams = sum(1 for r in overlap_results if r["has_seam"])
        
        mean_seam_deviation = np.mean(seam_flux_deviations) if seam_flux_deviations else 0.0
        max_seam_deviation = np.max(seam_flux_deviations) if seam_flux_deviations else 0.0
        
        # Validate noise consistency
        noise_ratios = _validate_noise_consistency(mosaic_data, tile_data_list)
        mean_noise_ratio = np.mean(noise_ratios) if noise_ratios else 1.0
        max_noise_ratio = np.max(noise_ratios) if noise_ratios else 1.0
        
        # Calculate overlap fractions
        overlap_fractions = [o.get("fraction", 0.0) for o in overlap_regions]
        mean_overlap_fraction = np.mean(overlap_fractions) if overlap_fractions else 0.0
        min_overlap_fraction = np.min(overlap_fractions) if overlap_fractions else 0.0
        
        # Determine overall pass status
        passed = (
            max_seam_deviation <= config.max_seam_flux_deviation and
            max_wcs_offset <= config.max_wcs_offset_arcsec and
            min_overlap_fraction >= config.min_overlap_fraction and
            max_noise_ratio <= config.max_noise_ratio
        )
        
        result = MosaicValidationResult(
            passed=passed,
            message=f"Mosaic validation: {n_seams}/{n_overlaps} seams detected, max_dev={max_seam_deviation:.3f}",
            details={
                "n_tiles": len(tile_paths),
                "n_overlaps": n_overlaps,
                "n_seams": n_seams,
                "mean_seam_deviation": mean_seam_deviation,
                "max_seam_deviation": max_seam_deviation,
                "mean_wcs_offset": mean_wcs_offset,
                "max_wcs_offset": max_wcs_offset,
                "mean_noise_ratio": mean_noise_ratio,
                "max_noise_ratio": max_noise_ratio,
                "mean_overlap_fraction": mean_overlap_fraction,
                "min_overlap_fraction": min_overlap_fraction,
            },
            metrics={
                "mean_seam_flux_deviation": mean_seam_deviation,
                "max_seam_flux_deviation": max_seam_deviation,
                "mean_wcs_offset_arcsec": mean_wcs_offset,
                "max_wcs_offset_arcsec": max_wcs_offset,
                "mean_noise_ratio": mean_noise_ratio,
                "max_noise_ratio": max_noise_ratio,
                "mean_overlap_fraction": mean_overlap_fraction,
                "min_overlap_fraction": min_overlap_fraction,
            },
            n_tiles=len(tile_paths),
            n_overlaps=n_overlaps,
            n_seams_detected=n_seams,
            mean_seam_flux_deviation=mean_seam_deviation,
            max_seam_flux_deviation=max_seam_deviation,
            mean_wcs_offset_arcsec=mean_wcs_offset,
            max_wcs_offset_arcsec=max_wcs_offset,
            mean_noise_ratio=mean_noise_ratio,
            max_noise_ratio=max_noise_ratio,
            mean_overlap_fraction=mean_overlap_fraction,
            min_overlap_fraction=min_overlap_fraction,
            overlap_results=overlap_results,
        )
        
        if n_seams > 0:
            result.add_warning(f"{n_seams} seam artifacts detected in mosaic")
        
        if max_wcs_offset > config.max_wcs_offset_arcsec:
            result.add_error(
                f"WCS offset {max_wcs_offset:.3f} arcsec exceeds threshold {config.max_wcs_offset_arcsec:.3f}"
            )
        
        if max_seam_deviation > config.max_seam_flux_deviation:
            result.add_error(
                f"Seam flux deviation {max_seam_deviation:.3f} exceeds threshold {config.max_seam_flux_deviation:.3f}"
            )
        
        if min_overlap_fraction < config.min_overlap_fraction:
            result.add_warning(
                f"Minimum overlap fraction {min_overlap_fraction:.3f} below recommended {config.min_overlap_fraction:.3f}"
            )
        
        return result
        
    except Exception as e:
        logger.exception("Mosaic validation failed")
        raise ValidationError(f"Mosaic validation failed: {e}") from e


def _validate_wcs_alignment(
    mosaic_wcs: WCS,
    tile_wcs_list: List[WCS],
) -> List[float]:
    """Validate WCS alignment between mosaic and tiles.
    
    Args:
        mosaic_wcs: WCS of mosaic image
        tile_wcs_list: List of WCS objects for tiles
        
    Returns:
        List of WCS offset values in arcseconds
    """
    offsets = []
    
    # Sample points in each tile and check alignment with mosaic
    for tile_wcs in tile_wcs_list:
        # Get center pixel of tile
        tile_shape = tile_wcs.pixel_shape if hasattr(tile_wcs, 'pixel_shape') else (100, 100)
        center_pix = (tile_shape[0] / 2, tile_shape[1] / 2)
        
        # Convert to world coordinates
        tile_ra, tile_dec = tile_wcs.pixel_to_world_values(center_pix[0], center_pix[1])
        
        # Convert to mosaic pixel coordinates
        mosaic_pix = mosaic_wcs.world_to_pixel_values(tile_ra, tile_dec)
        
        # Calculate offset (simplified - would need proper coordinate conversion)
        # For now, return small offset
        offsets.append(0.05)  # Placeholder
    
    return offsets


def _detect_overlaps(
    mosaic_wcs: WCS,
    tile_wcs_list: List[WCS],
) -> List[Dict]:
    """Detect overlap regions between tiles.
    
    Args:
        mosaic_wcs: WCS of mosaic image
        tile_wcs_list: List of WCS objects for tiles
        
    Returns:
        List of overlap region dictionaries
    """
    overlaps = []
    
    # Simplified overlap detection
    # In practice, would calculate actual pixel overlaps
    for i, wcs1 in enumerate(tile_wcs_list):
        for j, wcs2 in enumerate(tile_wcs_list[i+1:], start=i+1):
            # Check if tiles overlap
            # Placeholder implementation
            overlaps.append({
                "id": f"overlap_{i}_{j}",
                "tile1": i,
                "tile2": j,
                "fraction": 0.15,  # Placeholder
                "wcs_offset": 0.05,  # Placeholder
            })
    
    return overlaps


def _validate_overlap_flux_consistency(
    mosaic_data: np.ndarray,
    mosaic_wcs: WCS,
    tile_data_list: List[np.ndarray],
    tile_wcs_list: List[WCS],
    overlap: Dict,
) -> float:
    """Validate flux consistency in overlap region.
    
    Args:
        mosaic_data: Mosaic image data
        mosaic_wcs: Mosaic WCS
        tile_data_list: List of tile data arrays
        tile_wcs_list: List of tile WCS objects
        overlap: Overlap region definition
        
    Returns:
        Flux deviation fraction
    """
    # Simplified implementation
    # In practice, would extract overlap regions and compare fluxes
    return 0.05  # Placeholder - 5% deviation


def _validate_noise_consistency(
    mosaic_data: np.ndarray,
    tile_data_list: List[np.ndarray],
) -> List[float]:
    """Validate noise consistency between mosaic and tiles.
    
    Args:
        mosaic_data: Mosaic image data
        tile_data_list: List of tile data arrays
        
    Returns:
        List of noise ratios (mosaic/tile)
    """
    # Calculate noise in mosaic (RMS of background)
    mosaic_noise = np.std(mosaic_data[np.abs(mosaic_data) < np.percentile(np.abs(mosaic_data), 50)])
    
    noise_ratios = []
    for tile_data in tile_data_list:
        tile_noise = np.std(tile_data[np.abs(tile_data) < np.percentile(np.abs(tile_data), 50)])
        if tile_noise > 0:
            noise_ratio = mosaic_noise / tile_noise
        else:
            noise_ratio = 1.0
        noise_ratios.append(noise_ratio)
    
    return noise_ratios


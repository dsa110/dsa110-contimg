"""
Photometry stage: Measure source fluxes in images.

This stage performs forced photometry at known source positions
using catalog cross-matching.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PhotometryResult:
    """Result of photometry operations."""
    
    success: bool
    image_path: str
    sources_measured: int = 0
    catalog_used: str = ""
    measurements: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0


@dataclass
class PhotometryConfig:
    """Configuration for the photometry stage."""

    catalog: str = "nvss"  # nvss, first, rax, vlass, master, atnf
    search_radius_arcsec: float = 30.0
    search_radius_deg: float = 0.5  # Alternative to search_radius_arcsec
    snr_threshold: float = 5.0
    batch_size: int = 100
    products_db: Optional[Path] = None  # Optional database for recording


class PhotometryStage:
    """Stage for measuring source fluxes in images.
    
    This stage:
    1. Queries the specified catalog for sources in the image FOV
    2. Performs forced photometry at each source position
    3. Records measurements for variability analysis
    
    Example:
        >>> config = PhotometryConfig(catalog="nvss")
        >>> stage = PhotometryStage(config)
        >>> result = stage.execute("/data/images/2025-10-02T00:12:00-image.fits")
        >>> print(f"Measured {result.sources_measured} sources")
    """

    def __init__(self, config: PhotometryConfig) -> None:
        """Initialize the photometry stage.
        
        Args:
            config: Photometry configuration
        """
        self.config = config
        self._worker_available = False
        
        # Check if photometry worker is available
        try:
            from dsa110_contimg.photometry.worker import PhotometryBatchWorker
            if PhotometryBatchWorker is not None:
                self._worker_available = True
        except ImportError:
            pass

    def validate(self, image_path: str) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for photometry.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not Path(image_path).exists():
            return False, f"Image not found: {image_path}"

        if not self._worker_available:
            return False, "Photometry worker not available"

        return True, None

    def execute(
        self,
        image_path: str,
        ra_deg: Optional[float] = None,
        dec_deg: Optional[float] = None,
    ) -> PhotometryResult:
        """Execute the photometry stage.
        
        Args:
            image_path: Path to the image file
            ra_deg: Optional RA center for catalog query
            dec_deg: Optional Dec center for catalog query
            
        Returns:
            PhotometryResult with measurements
        """
        t0 = time.perf_counter()
        
        # Validate
        is_valid, error = self.validate(image_path)
        if not is_valid:
            return PhotometryResult(
                success=False,
                image_path=image_path,
                error_message=error,
            )

        try:
            from dsa110_contimg.photometry.worker import PhotometryBatchWorker

            # Get image center if not provided
            if ra_deg is None or dec_deg is None:
                ra_deg, dec_deg = self._get_image_center(image_path)

            if ra_deg is None or dec_deg is None:
                return PhotometryResult(
                    success=False,
                    image_path=image_path,
                    error_message="Could not determine image center",
                )

            # Initialize worker
            worker = PhotometryBatchWorker(
                catalog=self.config.catalog,
                search_radius_arcsec=self.config.search_radius_arcsec,
            )

            # Run photometry
            measurements = worker.measure_sources(
                image_path,
                ra_deg,
                dec_deg,
                snr_threshold=self.config.snr_threshold,
            )

            return PhotometryResult(
                success=True,
                image_path=image_path,
                sources_measured=len(measurements),
                catalog_used=self.config.catalog,
                measurements=measurements,
                elapsed_seconds=time.perf_counter() - t0,
            )

        except Exception as e:
            logger.error(f"Photometry failed for {image_path}: {e}", exc_info=True)
            return PhotometryResult(
                success=False,
                image_path=image_path,
                error_message=str(e),
                elapsed_seconds=time.perf_counter() - t0,
            )

    def _get_image_center(
        self, image_path: str
    ) -> Tuple[Optional[float], Optional[float]]:
        """Extract image center coordinates from FITS header.
        
        Args:
            image_path: Path to FITS image
            
        Returns:
            Tuple of (ra_deg, dec_deg) or (None, None)
        """
        try:
            from astropy.io import fits
            from astropy.wcs import WCS

            with fits.open(image_path) as hdul:
                wcs = WCS(hdul[0].header).celestial
                # Get center pixel
                ny, nx = hdul[0].data.shape[-2:]
                ra, dec = wcs.pixel_to_world_values(nx / 2, ny / 2)
                return float(ra), float(dec)

        except Exception as e:
            logger.debug(f"Failed to get image center: {e}")
            return None, None

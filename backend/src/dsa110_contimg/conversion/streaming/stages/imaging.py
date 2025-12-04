"""
Imaging stage: Generate images from Measurement Sets.

This stage handles image generation using WSClean or CASA tclean,
with support for various weighting schemes and cleaning parameters.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ImagingResult:
    """Result of imaging operations."""
    
    success: bool
    ms_path: str
    image_path: Optional[str] = None
    fits_path: Optional[str] = None
    rms_jy: Optional[float] = None
    peak_jy: Optional[float] = None
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImagingConfig:
    """Configuration for the imaging stage."""

    output_dir: Path
    products_db: Optional[Path] = None  # Optional database for recording
    imsize: int = 4096
    cell_arcsec: float = 1.0
    weighting: str = "briggs"
    robust: float = 0.0
    niter: int = 10000
    threshold_jy: float = 1e-4
    use_wsclean: bool = True
    fits_output: bool = True
    quality_tier: str = "standard"
    enable_catalog_validation: bool = True
    validation_catalog: str = "nvss"


class ImagingStage:
    """Stage for generating images from Measurement Sets.
    
    This stage:
    1. Reorders MS data for multi-SPW processing
    2. Runs imaging (WSClean or CASA tclean)
    3. Exports to FITS format
    4. Calculates image statistics
    
    Example:
        >>> config = ImagingConfig(
        ...     output_dir=Path("/data/images"),
        ...     imsize=4096,
        ...     cell_arcsec=1.0,
        ... )
        >>> stage = ImagingStage(config)
        >>> result = stage.execute("/data/ms/2025-10-02T00:12:00.ms")
        >>> if result.success:
        ...     print(f"Created image: {result.image_path}")
        ...     print(f"RMS: {result.rms_jy*1e6:.1f} µJy")
    """

    def __init__(self, config: ImagingConfig) -> None:
        """Initialize the imaging stage.
        
        Args:
            config: Imaging configuration
        """
        self.config = config

    def validate(self, ms_path: str) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for imaging.
        
        Args:
            ms_path: Path to the Measurement Set
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.exists(ms_path):
            return False, f"MS not found: {ms_path}"

        if not self.config.output_dir.exists():
            try:
                self.config.output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return False, f"Cannot create output directory: {e}"

        return True, None

    def execute(self, ms_path: str) -> ImagingResult:
        """Execute the imaging stage.
        
        Args:
            ms_path: Path to the Measurement Set
            
        Returns:
            ImagingResult with status and output paths
        """
        t0 = time.perf_counter()
        
        # Validate
        is_valid, error = self.validate(ms_path)
        if not is_valid:
            return ImagingResult(
                success=False,
                ms_path=ms_path,
                error_message=error,
            )

        try:
            from dsa110_contimg.imaging import image_ms

            # Derive output name from MS
            ms_name = Path(ms_path).stem
            image_root = str(self.config.output_dir / ms_name)

            # Run imaging
            image_ms(
                ms_path,
                imgroot=image_root,
                imsize=self.config.imsize,
                cell=f"{self.config.cell_arcsec}arcsec",
                weighting=self.config.weighting,
                robust=self.config.robust,
                niter=self.config.niter,
                threshold=f"{self.config.threshold_jy}Jy",
            )

            # Determine output paths
            image_path = f"{image_root}-image.fits"
            if not os.path.exists(image_path):
                image_path = f"{image_root}.image"

            # Calculate image statistics
            rms_jy, peak_jy = self._calculate_stats(image_path)

            return ImagingResult(
                success=True,
                ms_path=ms_path,
                image_path=image_path,
                fits_path=image_path if image_path.endswith(".fits") else None,
                rms_jy=rms_jy,
                peak_jy=peak_jy,
                elapsed_seconds=time.perf_counter() - t0,
            )

        except Exception as e:
            logger.error(f"Imaging failed for {ms_path}: {e}", exc_info=True)
            return ImagingResult(
                success=False,
                ms_path=ms_path,
                error_message=str(e),
                elapsed_seconds=time.perf_counter() - t0,
            )

    def _calculate_stats(
        self, image_path: str
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate image statistics (RMS, peak).
        
        Args:
            image_path: Path to the image
            
        Returns:
            Tuple of (rms_jy, peak_jy)
        """
        try:
            from astropy.io import fits
            import numpy as np

            with fits.open(image_path) as hdul:
                data = hdul[0].data
                # Handle 4D cubes (Stokes, Freq, RA, Dec)
                if data.ndim == 4:
                    data = data[0, 0, :, :]
                elif data.ndim == 3:
                    data = data[0, :, :]

                # Robust RMS from median absolute deviation
                valid = data[np.isfinite(data)]
                if len(valid) == 0:
                    return None, None
                    
                rms = 1.4826 * np.median(np.abs(valid - np.median(valid)))
                peak = np.nanmax(np.abs(valid))
                
                return float(rms), float(peak)

        except Exception as e:
            logger.debug(f"Failed to calculate image stats: {e}")
            return None, None

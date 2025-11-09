"""
Adaptive binning photometry integration for DSA-110 pipeline.

This module integrates adaptive channel binning with the photometry workflow,
allowing automatic detection of weak sources by combining multiple subbands.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np

from dsa110_contimg.photometry.adaptive_binning import (
    AdaptiveBinningConfig,
    Detection,
    adaptive_bin_channels,
    create_measure_fn_from_images,
)
from dsa110_contimg.photometry.forced import measure_forced_peak
from dsa110_contimg.imaging.spw_imaging import get_spw_info, image_all_spws

LOG = logging.getLogger(__name__)


@dataclass
class AdaptivePhotometryResult:
    """Result from adaptive binning photometry."""
    ra_deg: float
    dec_deg: float
    detections: List[Detection]
    n_spws: int
    spw_info: List  # List of SPWInfo objects
    success: bool
    error_message: Optional[str] = None


def measure_with_adaptive_binning(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    output_dir: Path,
    config: Optional[AdaptiveBinningConfig] = None,
    photometry_fn: Optional[Callable[[
        str, float, float], Tuple[float, float]]] = None,
    max_spws: Optional[int] = None,
    **imaging_kwargs,
) -> AdaptivePhotometryResult:
    """Measure photometry using adaptive channel binning.

    This function:
    1. Images all SPWs individually
    2. Measures photometry on each SPW image
    3. Applies adaptive binning algorithm to find optimal combinations
    4. Returns detections with optimal binning

    Args:
        ms_path: Path to Measurement Set
        ra_deg: Right ascension (degrees)
        dec_deg: Declination (degrees)
        output_dir: Directory for SPW images and results
        config: Adaptive binning configuration (uses defaults if None)
        photometry_fn: Optional custom photometry function. If None, uses
                      measure_forced_peak(). Should take (image_path, ra, dec)
                      and return (flux_jy, rms_jy).
        **imaging_kwargs: Additional arguments passed to image_ms()

    Returns:
        AdaptivePhotometryResult with detections

    Example:
        >>> from pathlib import Path
        >>> result = measure_with_adaptive_binning(
        ...     ms_path="data.ms",
        ...     ra_deg=128.725,
        ...     dec_deg=55.573,
        ...     output_dir=Path("adaptive_results/"),
        ...     imsize=1024,
        ...     quality_tier="standard",
        ... )
        >>> print(f"Found {len(result.detections)} detections")
        >>> for det in result.detections:
        ...     print(f"SPWs {det.channels}: SNR={det.snr:.2f}, Flux={det.flux_jy:.6f} Jy")
    """
    try:
        # Get SPW information
        spw_info_list = get_spw_info(ms_path)
        n_spws = len(spw_info_list)

        if n_spws == 0:
            return AdaptivePhotometryResult(
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                detections=[],
                n_spws=0,
                spw_info=[],
                success=False,
                error_message="No SPWs found in Measurement Set",
            )

        LOG.info(f"Found {n_spws} SPW(s) in {ms_path}")

        # Limit SPWs if requested
        if max_spws is not None and max_spws < n_spws:
            LOG.info(f"Limiting to first {max_spws} SPW(s) (out of {n_spws})")
            spw_ids_to_image = [info.spw_id for info in spw_info_list[:max_spws]]
            n_spws_used = max_spws
        else:
            spw_ids_to_image = None
            n_spws_used = n_spws

        # Image SPWs
        output_dir.mkdir(parents=True, exist_ok=True)
        spw_images_dir = output_dir / "spw_images"

        LOG.info(f"Imaging {n_spws_used} SPW(s)...")
        # Extract parallel imaging parameters if provided
        parallel = imaging_kwargs.pop('parallel', False)
        max_workers = imaging_kwargs.pop('max_workers', None)
        
        spw_image_paths = image_all_spws(
            ms_path=ms_path,
            output_dir=spw_images_dir,
            base_name="spw",
            spw_ids=spw_ids_to_image,
            parallel=parallel,
            max_workers=max_workers,
            **imaging_kwargs,
        )

        # Sort by SPW ID and extract paths
        spw_image_paths_sorted = sorted(spw_image_paths, key=lambda x: x[0])
        image_paths = [str(path) for _, path in spw_image_paths_sorted]

        if len(image_paths) != n_spws:
            LOG.warning(
                f"Expected {n_spws} images but got {len(image_paths)}. "
                "Some SPWs may have failed to image."
            )

        # Create photometry function if not provided
        if photometry_fn is None:
            def photometry_fn(image_path: str, ra: float, dec: float) -> Tuple[float, float]:
                """Default photometry using measure_forced_peak."""
                result = measure_forced_peak(
                    image_path,
                    ra,
                    dec,
                    box_size_pix=5,
                    annulus_pix=(12, 20),
                )
                # Convert from Jy/beam to Jy (approximate)
                flux_jy = result.peak_jyb
                rms_jy = result.peak_err_jyb if result.peak_err_jyb is not None else result.local_rms_jy
                if rms_jy is None or not np.isfinite(rms_jy):
                    rms_jy = 0.001  # Default RMS if not available
                return flux_jy, rms_jy

        # Create measure function for adaptive binning
        measure_fn = create_measure_fn_from_images(
            image_paths=image_paths,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            photometry_fn=photometry_fn,
        )

        # Get channel frequencies for center frequency calculation
        # Use only the SPWs that were actually imaged
        spw_ids_imaged = [spw_id for spw_id, _ in spw_image_paths]
        spw_info_used = [info for info in spw_info_list if info.spw_id in spw_ids_imaged]
        channel_freqs_mhz = [info.center_freq_mhz for info in spw_info_used]

        # Run adaptive binning
        LOG.info("Running adaptive binning algorithm...")
        detections = adaptive_bin_channels(
            n_channels=len(spw_info_used),
            measure_fn=measure_fn,
            config=config,
            channel_freqs_mhz=channel_freqs_mhz,
        )

        LOG.info(f"Found {len(detections)} detection(s) with adaptive binning")

        return AdaptivePhotometryResult(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            detections=detections,
            n_spws=len(spw_info_used),
            spw_info=spw_info_used,
            success=True,
        )

    except Exception as e:
        LOG.error(f"Adaptive binning photometry failed: {e}", exc_info=True)
        return AdaptivePhotometryResult(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            detections=[],
            n_spws=0,
            spw_info=[],
            success=False,
            error_message=str(e),
        )

"""
Self-calibration module for iterative imaging and calibration.

Self-calibration (selfcal) iteratively improves calibration by using the
current best image as a model for the next round of calibration:

    Initial Imaging → Phase Self-cal → Amplitude+Phase Self-cal → Final Image

This module provides:
- SelfCalConfig: Configuration for self-calibration parameters
- SelfCalResult: Results from a self-calibration run
- selfcal_iteration: Run a single self-cal iteration
- selfcal_ms: Run full self-calibration loop on a Measurement Set

Self-calibration workflow:
1. Create initial image (dirty or cleaned)
2. Predict model visibilities to MODEL_DATA
3. Solve gaincal (phase-only initially, then amp+phase)
4. Apply calibration
5. Re-image with improved calibration
6. Measure SNR improvement
7. Repeat until convergence or max iterations

Backend support:
- WSClean: Uses `-predict` for model prediction (recommended)
- CASA tclean: Uses internal ft() for model prediction
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class SelfCalMode(str, Enum):
    """Self-calibration mode."""
    
    PHASE = "phase"  # Phase-only calibration
    AMPLITUDE_PHASE = "ap"  # Amplitude + phase calibration


class SelfCalStatus(str, Enum):
    """Status of self-calibration."""
    
    SUCCESS = "success"
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    DIVERGED = "diverged"
    FAILED = "failed"
    NO_IMPROVEMENT = "no_improvement"


# Default solution intervals for progressive selfcal
DEFAULT_PHASE_SOLINTS = ["60s", "30s", "inf"]  # Start coarse, refine
DEFAULT_AMP_SOLINT = "inf"  # Amplitude solint (typically longer)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class SelfCalConfig:
    """Configuration for self-calibration.
    
    Attributes:
        max_iterations: Maximum number of self-cal iterations
        min_snr_improvement: Minimum fractional SNR improvement to continue (e.g., 1.05 = 5%)
        stop_on_divergence: Stop if SNR decreases
        
        phase_solints: Solution intervals for phase-only iterations
        phase_minsnr: Minimum SNR for phase solutions
        phase_combine: Combine parameter for gaincal (e.g., "scan", "spw")
        
        do_amplitude: Whether to do amplitude self-cal after phase
        amp_solint: Solution interval for amplitude+phase iteration
        amp_minsnr: Minimum SNR for amplitude solutions
        amp_combine: Combine parameter for amplitude gaincal
        
        imsize: Image size in pixels
        cell_arcsec: Cell size in arcseconds (None = auto-calculate)
        niter: Clean iterations per imaging cycle
        threshold: Clean threshold (e.g., "0.1mJy")
        robust: Briggs robust weighting parameter
        backend: Imaging backend ("wsclean" or "tclean")
        
        min_initial_snr: Minimum initial SNR required to start selfcal
        max_flagged_fraction: Maximum flagged fraction allowed
        
        refant: Reference antenna (None = auto-select)
        uvrange: UV range selection (e.g., ">1klambda")
        spw: Spectral window selection
        field: Field selection
        
        use_nvss_seeding: Seed initial model from NVSS catalog
        nvss_min_mjy: Minimum flux for NVSS sources
        calib_ra_deg: Calibrator RA for initial model seeding
        calib_dec_deg: Calibrator Dec for initial model seeding
        calib_flux_jy: Calibrator flux for initial model seeding
    """
    
    # Iteration control
    max_iterations: int = 5
    min_snr_improvement: float = 1.05  # 5% improvement threshold
    stop_on_divergence: bool = True
    
    # Phase-only calibration parameters
    phase_solints: List[str] = field(default_factory=lambda: DEFAULT_PHASE_SOLINTS.copy())
    phase_minsnr: float = 3.0
    phase_combine: str = ""
    
    # Amplitude+phase calibration parameters
    do_amplitude: bool = True
    amp_solint: str = DEFAULT_AMP_SOLINT
    amp_minsnr: float = 5.0
    amp_combine: str = "scan"
    
    # Imaging parameters
    imsize: int = 1024
    cell_arcsec: Optional[float] = None  # Auto-calculate if None
    niter: int = 10000
    threshold: str = "0.1mJy"
    robust: float = 0.0
    backend: str = "wsclean"
    
    # Quality control
    min_initial_snr: float = 5.0
    max_flagged_fraction: float = 0.5
    
    # Data selection
    refant: Optional[str] = None
    uvrange: str = ""
    spw: str = ""
    field: str = "0"
    
    # Model seeding
    use_nvss_seeding: bool = False
    nvss_min_mjy: float = 10.0
    calib_ra_deg: Optional[float] = None
    calib_dec_deg: Optional[float] = None
    calib_flux_jy: Optional[float] = None


# =============================================================================
# Results
# =============================================================================


@dataclass
class SelfCalIterationResult:
    """Result from a single self-calibration iteration.
    
    Attributes:
        iteration: Iteration number (0-indexed)
        mode: Calibration mode (phase or ap)
        solint: Solution interval used
        success: Whether iteration succeeded
        snr: Peak SNR after this iteration
        rms: RMS noise after this iteration
        peak_flux: Peak flux after this iteration
        gaintable: Path to calibration table produced
        image_path: Path to image produced
        message: Status message
    """
    
    iteration: int
    mode: SelfCalMode
    solint: str
    success: bool
    snr: float = 0.0
    rms: float = 0.0
    peak_flux: float = 0.0
    gaintable: Optional[str] = None
    image_path: Optional[str] = None
    message: str = ""


@dataclass
class SelfCalResult:
    """Result from a full self-calibration run.
    
    Attributes:
        status: Final status of self-calibration
        iterations_completed: Number of iterations completed
        initial_snr: Initial SNR before self-calibration
        best_snr: Best SNR achieved
        final_snr: Final SNR (may be worse than best if diverged)
        improvement_factor: Final/Initial SNR ratio
        iterations: List of iteration results
        best_iteration: Index of best iteration
        final_image: Path to final image
        final_gaintables: List of final calibration tables to apply
        message: Status message
    """
    
    status: SelfCalStatus
    iterations_completed: int = 0
    initial_snr: float = 0.0
    best_snr: float = 0.0
    final_snr: float = 0.0
    improvement_factor: float = 1.0
    iterations: List[SelfCalIterationResult] = field(default_factory=list)
    best_iteration: int = -1
    final_image: Optional[str] = None
    final_gaintables: List[str] = field(default_factory=list)
    message: str = ""


# =============================================================================
# Helper Functions
# =============================================================================


def _measure_image_stats(image_path: str) -> Tuple[float, float, float]:
    """Measure image statistics (peak, rms, snr).
    
    Args:
        image_path: Path to FITS or CASA image
        
    Returns:
        Tuple of (peak_flux, rms, snr)
    """
    try:
        # Try FITS first
        if image_path.endswith(".fits"):
            from astropy.io import fits
            with fits.open(image_path) as hdul:
                data = hdul[0].data
                # Handle multi-dimensional data (freq, pol axes)
                while data.ndim > 2:
                    data = data[0]
                
                # Measure peak and RMS
                peak = np.nanmax(np.abs(data))
                # RMS from outer regions (avoid central source)
                ny, nx = data.shape
                edge_data = np.concatenate([
                    data[:ny//4, :].flatten(),
                    data[3*ny//4:, :].flatten(),
                    data[:, :nx//4].flatten(),
                    data[:, 3*nx//4:].flatten(),
                ])
                rms = np.nanstd(edge_data)
                snr = peak / rms if rms > 0 else 0.0
                return peak, rms, snr
        else:
            # Try CASA image
            try:
                from casacore.images import image as casa_image
                with casa_image(image_path) as img:
                    data = img.getdata()
                    # Handle multi-dimensional data
                    while data.ndim > 2:
                        data = data[..., 0]
                    
                    peak = np.nanmax(np.abs(data))
                    ny, nx = data.shape
                    edge_data = np.concatenate([
                        data[:ny//4, :].flatten(),
                        data[3*ny//4:, :].flatten(),
                        data[:, :nx//4].flatten(),
                        data[:, 3*nx//4:].flatten(),
                    ])
                    rms = np.nanstd(edge_data)
                    snr = peak / rms if rms > 0 else 0.0
                    return peak, rms, snr
            except ImportError:
                logger.warning("casacore.images not available")
                return 0.0, 0.0, 0.0
    except Exception as e:
        logger.warning(f"Failed to measure image stats for {image_path}: {e}")
        return 0.0, 0.0, 0.0


def _get_flagged_fraction(ms_path: str) -> float:
    """Get fraction of flagged data in MS.
    
    Args:
        ms_path: Path to Measurement Set
        
    Returns:
        Flagged fraction (0-1)
    """
    try:
        import casacore.tables as tb
        with tb.table(ms_path, readonly=True) as t:
            flags = t.getcol("FLAG")
            return np.mean(flags)
    except Exception as e:
        logger.warning(f"Failed to get flagged fraction: {e}")
        return 0.0


def _predict_model_wsclean(
    ms_path: str,
    model_prefix: str,
    wsclean_path: Optional[str] = None,
) -> bool:
    """Predict model visibilities using WSClean -predict.
    
    This writes to the MODEL_DATA column from a model image.
    
    Args:
        ms_path: Path to Measurement Set
        model_prefix: Prefix of model image (e.g., "image" for "image-model.fits")
        wsclean_path: Optional path to WSClean executable
        
    Returns:
        True if successful
    """
    # Find WSClean executable
    wsclean_exec = wsclean_path or shutil.which("wsclean")
    
    use_docker = False
    if not wsclean_exec:
        if shutil.which("docker"):
            use_docker = True
        else:
            logger.error("WSClean not found for model prediction")
            return False
    
    try:
        if use_docker:
            # Use Docker WSClean
            from dsa110_contimg.imaging.docker_utils import (
                convert_host_path_to_container,
                get_wsclean_container,
            )
            
            container = get_wsclean_container()
            ms_container = convert_host_path_to_container(ms_path)
            model_prefix_container = convert_host_path_to_container(model_prefix)
            
            container.wsclean(
                [
                    "-predict",
                    "-reorder",
                    "-name", model_prefix_container,
                    ms_container,
                ],
                timeout=600,
            )
        else:
            # Native WSClean
            cmd = [
                wsclean_exec,
                "-predict",
                "-reorder",
                "-name", model_prefix,
                ms_path,
            ]
            logger.info(f"Running WSClean predict: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, timeout=600, capture_output=True)
        
        logger.info("Model prediction successful")
        return True
        
    except Exception as e:
        logger.error(f"WSClean predict failed: {e}")
        return False


def _predict_model_casa(
    ms_path: str,
    model_image: str,
    field: str = "0",
) -> bool:
    """Predict model visibilities using CASA ft().
    
    Args:
        ms_path: Path to Measurement Set
        model_image: Path to model image
        field: Field selection
        
    Returns:
        True if successful
    """
    try:
        from dsa110_contimg.utils.casa_init import ensure_casa_path
        ensure_casa_path()
        
        from dsa110_contimg.utils.tempdirs import casa_log_environment
        with casa_log_environment():
            from casatasks import ft as casa_ft
        
        casa_ft(
            vis=ms_path,
            model=model_image,
            field=field,
            usescratch=True,
        )
        
        logger.info("CASA ft() model prediction successful")
        return True
        
    except Exception as e:
        logger.error(f"CASA ft() failed: {e}")
        return False


def _run_gaincal(
    ms_path: str,
    caltable: str,
    field: str,
    solint: str,
    calmode: str,
    refant: Optional[str],
    minsnr: float,
    combine: str,
    gaintable: Optional[List[str]] = None,
    uvrange: str = "",
    spw: str = "",
) -> bool:
    """Run CASA gaincal.
    
    Args:
        ms_path: Path to Measurement Set
        caltable: Output calibration table path
        field: Field selection
        solint: Solution interval
        calmode: Calibration mode ('p' for phase, 'ap' for amp+phase)
        refant: Reference antenna
        minsnr: Minimum SNR for solutions
        combine: Combine parameter
        gaintable: Previous calibration tables to apply
        uvrange: UV range selection
        spw: Spectral window selection
        
    Returns:
        True if successful
    """
    try:
        from dsa110_contimg.utils.casa_init import ensure_casa_path
        ensure_casa_path()
        
        from dsa110_contimg.utils.tempdirs import casa_log_environment
        with casa_log_environment():
            from casatasks import gaincal
        
        kwargs: Dict[str, Any] = {
            "vis": ms_path,
            "caltable": caltable,
            "field": field,
            "solint": solint,
            "gaintype": "G",
            "calmode": calmode,
            "minsnr": minsnr,
        }
        
        if refant:
            kwargs["refant"] = refant
        if combine:
            kwargs["combine"] = combine
        if gaintable:
            kwargs["gaintable"] = gaintable
        if uvrange:
            kwargs["uvrange"] = uvrange
        if spw:
            kwargs["spw"] = spw
        
        logger.info(f"Running gaincal: solint={solint}, calmode={calmode}")
        gaincal(**kwargs)
        
        # Verify table was created
        if Path(caltable).exists():
            logger.info(f"Calibration table created: {caltable}")
            return True
        else:
            logger.error(f"Calibration table not created: {caltable}")
            return False
            
    except Exception as e:
        logger.error(f"gaincal failed: {e}")
        return False


def _apply_calibration(
    ms_path: str,
    gaintables: List[str],
    field: str = "",
) -> bool:
    """Apply calibration tables to MS.
    
    Args:
        ms_path: Path to Measurement Set
        gaintables: List of calibration tables to apply
        field: Field selection
        
    Returns:
        True if successful
    """
    try:
        from dsa110_contimg.calibration.applycal import apply_to_target
        
        apply_to_target(
            ms_path,
            field=field,
            gaintables=gaintables,
            calwt=True,
        )
        
        logger.info(f"Applied {len(gaintables)} calibration tables")
        return True
        
    except Exception as e:
        logger.error(f"applycal failed: {e}")
        return False


def _run_imaging(
    ms_path: str,
    imagename: str,
    config: SelfCalConfig,
) -> Optional[str]:
    """Run imaging with configured parameters.
    
    Args:
        ms_path: Path to Measurement Set
        imagename: Output image name prefix
        config: Self-calibration configuration
        
    Returns:
        Path to output image, or None if failed
    """
    try:
        if config.backend == "wsclean":
            from dsa110_contimg.imaging.cli_imaging import image_ms
            
            image_ms(
                ms_path,
                imagename=imagename,
                field=config.field,
                imsize=config.imsize,
                cell_arcsec=config.cell_arcsec,
                niter=config.niter,
                threshold=config.threshold,
                robust=config.robust,
                backend="wsclean",
            )
            
            # Find output image
            for suffix in [".image.fits", "-image.fits", ".image"]:
                img_path = f"{imagename}{suffix}"
                if Path(img_path).exists():
                    return img_path
                    
            # WSClean naming convention
            img_path = f"{imagename}-MFS-image.fits"
            if Path(img_path).exists():
                return img_path
                
            logger.warning(f"Could not find output image for {imagename}")
            return None
            
        else:
            # CASA tclean
            from dsa110_contimg.utils.casa_init import ensure_casa_path
            ensure_casa_path()
            
            from dsa110_contimg.utils.tempdirs import casa_log_environment
            with casa_log_environment():
                from casatasks import tclean
            
            tclean(
                vis=ms_path,
                imagename=imagename,
                field=config.field,
                imsize=[config.imsize, config.imsize],
                cell=f"{config.cell_arcsec or 1.0}arcsec",
                niter=config.niter,
                threshold=config.threshold,
                weighting="briggs",
                robust=config.robust,
                datacolumn="corrected",
                savemodel="modelcolumn",  # Save model to MODEL_DATA
            )
            
            img_path = f"{imagename}.image"
            if Path(img_path).exists():
                return img_path
            
            return None
            
    except Exception as e:
        logger.error(f"Imaging failed: {e}")
        return None


# =============================================================================
# Main Self-Calibration Functions
# =============================================================================


def selfcal_iteration(
    ms_path: str,
    output_dir: str,
    iteration: int,
    mode: SelfCalMode,
    solint: str,
    config: SelfCalConfig,
    previous_gaintables: Optional[List[str]] = None,
) -> SelfCalIterationResult:
    """Run a single self-calibration iteration.
    
    One iteration consists of:
    1. Image the current data
    2. Predict model visibilities
    3. Solve gaincal
    4. Apply calibration
    
    Args:
        ms_path: Path to Measurement Set
        output_dir: Output directory for products
        iteration: Iteration number (0-indexed)
        mode: Calibration mode (phase or ap)
        solint: Solution interval
        config: Self-calibration configuration
        previous_gaintables: Previous calibration tables to apply
        
    Returns:
        SelfCalIterationResult with iteration details
    """
    result = SelfCalIterationResult(
        iteration=iteration,
        mode=mode,
        solint=solint,
        success=False,
    )
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Image prefix for this iteration
    iter_prefix = f"selfcal_iter{iteration}_{mode.value}_{solint.replace(' ', '')}"
    imagename = str(output_path / iter_prefix)
    caltable = str(output_path / f"{iter_prefix}.cal")
    
    try:
        # Step 1: Image
        logger.info(f"Iteration {iteration}: Imaging ({mode.value}, solint={solint})")
        image_path = _run_imaging(ms_path, imagename, config)
        
        if not image_path:
            result.message = "Imaging failed"
            return result
        
        result.image_path = image_path
        
        # Measure image stats
        peak, rms, snr = _measure_image_stats(image_path)
        result.peak_flux = peak
        result.rms = rms
        result.snr = snr
        
        logger.info(f"Iteration {iteration}: SNR={snr:.1f}, Peak={peak*1e3:.3f}mJy, RMS={rms*1e6:.1f}µJy")
        
        # Step 2: Predict model
        logger.info(f"Iteration {iteration}: Predicting model")
        
        if config.backend == "wsclean":
            # WSClean uses prefix for model files
            model_prefix = imagename
            if not _predict_model_wsclean(ms_path, model_prefix, wsclean_path=None):
                result.message = "Model prediction failed"
                return result
        else:
            # CASA tclean already saved model if savemodel="modelcolumn"
            pass
        
        # Step 3: Gaincal
        logger.info(f"Iteration {iteration}: Running gaincal")
        calmode = "p" if mode == SelfCalMode.PHASE else "ap"
        minsnr = config.phase_minsnr if mode == SelfCalMode.PHASE else config.amp_minsnr
        combine = config.phase_combine if mode == SelfCalMode.PHASE else config.amp_combine
        
        if not _run_gaincal(
            ms_path=ms_path,
            caltable=caltable,
            field=config.field,
            solint=solint,
            calmode=calmode,
            refant=config.refant,
            minsnr=minsnr,
            combine=combine,
            gaintable=previous_gaintables,
            uvrange=config.uvrange,
            spw=config.spw,
        ):
            result.message = "Gaincal failed"
            return result
        
        result.gaintable = caltable
        
        # Step 4: Apply calibration
        logger.info(f"Iteration {iteration}: Applying calibration")
        all_gaintables = (previous_gaintables or []) + [caltable]
        
        if not _apply_calibration(ms_path, all_gaintables, field=config.field):
            result.message = "Applycal failed"
            return result
        
        result.success = True
        result.message = f"Completed: SNR={snr:.1f}"
        
        return result
        
    except Exception as e:
        logger.error(f"Iteration {iteration} failed: {e}")
        result.message = str(e)
        return result


def selfcal_ms(
    ms_path: str,
    output_dir: str,
    config: Optional[SelfCalConfig] = None,
    initial_caltables: Optional[List[str]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """Run full self-calibration loop on a Measurement Set.
    
    This orchestrates multiple self-calibration iterations:
    1. Phase-only iterations with progressive solution intervals
    2. Optional amplitude+phase iteration
    
    Args:
        ms_path: Path to Measurement Set
        output_dir: Output directory for all products
        config: Self-calibration configuration (default: SelfCalConfig())
        initial_caltables: Initial calibration tables to apply first
        
    Returns:
        Tuple of (success, summary_dict)
    """
    if config is None:
        config = SelfCalConfig()
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    result = SelfCalResult(status=SelfCalStatus.FAILED)
    
    logger.info("=" * 60)
    logger.info("Starting self-calibration")
    logger.info(f"MS: {ms_path}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Max iterations: {config.max_iterations}")
    logger.info(f"Phase solints: {config.phase_solints}")
    logger.info(f"Do amplitude: {config.do_amplitude}")
    logger.info("=" * 60)
    
    # Check flagged fraction
    flagged_frac = _get_flagged_fraction(ms_path)
    if flagged_frac > config.max_flagged_fraction:
        result.message = f"Too much data flagged: {flagged_frac*100:.1f}% > {config.max_flagged_fraction*100:.1f}%"
        logger.error(result.message)
        return False, _result_to_dict(result)
    
    # Apply initial calibration if provided
    current_gaintables: List[str] = []
    if initial_caltables:
        logger.info(f"Applying {len(initial_caltables)} initial calibration tables")
        if not _apply_calibration(ms_path, initial_caltables, field=config.field):
            result.message = "Failed to apply initial calibration"
            return False, _result_to_dict(result)
        current_gaintables = list(initial_caltables)
    
    # Create initial image to measure starting SNR
    logger.info("Creating initial image to measure baseline SNR")
    initial_imagename = str(output_path / "selfcal_initial")
    initial_image = _run_imaging(ms_path, initial_imagename, config)
    
    if not initial_image:
        result.message = "Failed to create initial image"
        return False, _result_to_dict(result)
    
    initial_peak, initial_rms, initial_snr = _measure_image_stats(initial_image)
    result.initial_snr = initial_snr
    
    logger.info(f"Initial image: SNR={initial_snr:.1f}, Peak={initial_peak*1e3:.3f}mJy, RMS={initial_rms*1e6:.1f}µJy")
    
    if initial_snr < config.min_initial_snr:
        result.message = f"Initial SNR too low: {initial_snr:.1f} < {config.min_initial_snr:.1f}"
        result.status = SelfCalStatus.FAILED
        logger.warning(result.message)
        return False, _result_to_dict(result)
    
    best_snr = initial_snr
    best_iteration = -1
    iteration = 0
    
    # Phase-only iterations
    for solint in config.phase_solints:
        if iteration >= config.max_iterations:
            logger.info("Reached maximum iterations")
            break
        
        iter_result = selfcal_iteration(
            ms_path=ms_path,
            output_dir=output_dir,
            iteration=iteration,
            mode=SelfCalMode.PHASE,
            solint=solint,
            config=config,
            previous_gaintables=current_gaintables,
        )
        
        result.iterations.append(iter_result)
        
        if not iter_result.success:
            logger.warning(f"Phase iteration {iteration} failed: {iter_result.message}")
            # Continue to next iteration, don't abort entire selfcal
            iteration += 1
            continue
        
        # Check for improvement
        if iter_result.snr > best_snr * config.min_snr_improvement:
            logger.info(f"SNR improved: {best_snr:.1f} -> {iter_result.snr:.1f}")
            best_snr = iter_result.snr
            best_iteration = iteration
            if iter_result.gaintable:
                current_gaintables.append(iter_result.gaintable)
        elif iter_result.snr < best_snr and config.stop_on_divergence:
            logger.warning(f"SNR decreased: {best_snr:.1f} -> {iter_result.snr:.1f}, stopping")
            result.status = SelfCalStatus.DIVERGED
            break
        else:
            logger.info(f"SNR not significantly improved: {best_snr:.1f} -> {iter_result.snr:.1f}")
        
        iteration += 1
    
    # Amplitude+phase iteration
    if config.do_amplitude and iteration < config.max_iterations:
        logger.info("Running amplitude+phase self-calibration")
        
        iter_result = selfcal_iteration(
            ms_path=ms_path,
            output_dir=output_dir,
            iteration=iteration,
            mode=SelfCalMode.AMPLITUDE_PHASE,
            solint=config.amp_solint,
            config=config,
            previous_gaintables=current_gaintables,
        )
        
        result.iterations.append(iter_result)
        
        if iter_result.success:
            if iter_result.snr > best_snr:
                logger.info(f"Amplitude SNR improved: {best_snr:.1f} -> {iter_result.snr:.1f}")
                best_snr = iter_result.snr
                best_iteration = iteration
                if iter_result.gaintable:
                    current_gaintables.append(iter_result.gaintable)
            elif iter_result.snr < best_snr and config.stop_on_divergence:
                logger.warning(f"Amplitude SNR decreased: {best_snr:.1f} -> {iter_result.snr:.1f}")
                result.status = SelfCalStatus.DIVERGED
        
        iteration += 1
    
    # Final results
    result.iterations_completed = iteration
    result.best_snr = best_snr
    result.best_iteration = best_iteration
    result.final_snr = result.iterations[-1].snr if result.iterations else initial_snr
    result.improvement_factor = best_snr / initial_snr if initial_snr > 0 else 1.0
    result.final_gaintables = current_gaintables
    
    # Find final image
    if result.iterations and result.iterations[-1].image_path:
        result.final_image = result.iterations[-1].image_path
    
    # Determine final status
    if result.status == SelfCalStatus.FAILED:
        if result.improvement_factor >= config.min_snr_improvement:
            result.status = SelfCalStatus.SUCCESS
        elif iteration >= config.max_iterations:
            result.status = SelfCalStatus.MAX_ITERATIONS
        else:
            result.status = SelfCalStatus.NO_IMPROVEMENT
    
    success = result.status in (SelfCalStatus.SUCCESS, SelfCalStatus.CONVERGED, SelfCalStatus.MAX_ITERATIONS)
    
    logger.info("=" * 60)
    logger.info("Self-calibration complete")
    logger.info(f"Status: {result.status.value}")
    logger.info(f"Iterations: {result.iterations_completed}")
    logger.info(f"Initial SNR: {result.initial_snr:.1f}")
    logger.info(f"Best SNR: {result.best_snr:.1f}")
    logger.info(f"Improvement: {result.improvement_factor:.2f}x")
    logger.info("=" * 60)
    
    result.message = f"{result.status.value}: {result.improvement_factor:.2f}x improvement in {result.iterations_completed} iterations"
    
    return success, _result_to_dict(result)


def _result_to_dict(result: SelfCalResult) -> Dict[str, Any]:
    """Convert SelfCalResult to dictionary for serialization."""
    return {
        "status": result.status.value,
        "iterations_completed": result.iterations_completed,
        "initial_snr": result.initial_snr,
        "best_snr": result.best_snr,
        "final_snr": result.final_snr,
        "improvement_factor": result.improvement_factor,
        "best_iteration": result.best_iteration,
        "final_image": result.final_image,
        "final_gaintables": result.final_gaintables,
        "message": result.message,
        "iterations": [
            {
                "iteration": ir.iteration,
                "mode": ir.mode.value,
                "solint": ir.solint,
                "success": ir.success,
                "snr": ir.snr,
                "rms": ir.rms,
                "peak_flux": ir.peak_flux,
                "gaintable": ir.gaintable,
                "image_path": ir.image_path,
                "message": ir.message,
            }
            for ir in result.iterations
        ],
    }


__all__ = [
    "SelfCalMode",
    "SelfCalStatus",
    "SelfCalConfig",
    "SelfCalIterationResult",
    "SelfCalResult",
    "selfcal_iteration",
    "selfcal_ms",
]

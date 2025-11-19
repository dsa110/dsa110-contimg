#!/usr/bin/env python3
"""Self-calibration iterative imaging and calibration module.

This module implements self-calibration (self-cal) for radio interferometric data.
Self-calibration iteratively improves calibration solutions by using the observed
data itself to refine the sky model, then using that improved model to derive
better calibration solutions.

Key Concepts:
    - Phase-only self-cal: Corrects phase errors, preserves flux scale
    - Amplitude+phase self-cal: Corrects both phase and amplitude, higher risk
    - Iterative refinement: Each cycle improves the model and calibration
    - Dynamic range improvement: Self-cal dramatically improves image quality

Typical Workflow:
    1. Initial imaging with external calibration (BP, GP from calibrator)
    2. Phase-only self-cal (short solint)
    3. Image with phase solutions applied
    4. Phase-only self-cal (longer solint)
    5. Amplitude+phase self-cal (long solint, final iteration)
    6. Final imaging

Author: DSA-110 Continuum Imaging Team
"""

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from astropy.io import fits

try:
    from casatasks import applycal, gaincal

    CASATASKS_AVAILABLE = True
except ImportError:
    CASATASKS_AVAILABLE = False
    gaincal = None
    applycal = None

from dsa110_contimg.imaging.cli_imaging import image_ms
from dsa110_contimg.qa.calibration_quality import validate_caltable_quality

logger = logging.getLogger(__name__)


def _fix_ms_permissions(ms_path: Path, user: Optional[str] = None) -> bool:
    """Fix MS permissions to ensure current user can read/write.

    This is needed because CASA tasks may create MS files owned by root,
    causing permission errors for non-root users.

    Args:
        ms_path: Path to Measurement Set
        user: Target user (defaults to current user)

    Returns:
        True if successful, False otherwise
    """
    if user is None:
        user = os.getenv("USER", "ubuntu")

    try:
        logger.debug(f"Fixing MS permissions for {ms_path} (user={user})")

        # Change ownership
        subprocess.run(
            ["sudo", "chown", "-R", f"{user}:{user}", str(ms_path)],
            check=True,
            capture_output=True,
            text=True,
        )

        # Set permissions (u+rw, g+r, o+r)
        subprocess.run(
            ["sudo", "chmod", "-R", "u+rw,g+r,o+r", str(ms_path)],
            check=True,
            capture_output=True,
            text=True,
        )

        # Make directories executable
        subprocess.run(
            ["sudo", "find", str(ms_path), "-type", "d", "-exec", "chmod", "u+x", "{}", "+"],
            check=True,
            capture_output=True,
            text=True,
        )

        logger.debug(f"✓ MS permissions fixed for {ms_path}")
        return True

    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to fix MS permissions: {e}")
        logger.warning(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error fixing MS permissions: {e}")
        return False


@dataclass
class SelfCalIteration:
    """Results from a single self-calibration iteration."""

    iteration: int
    calmode: str  # 'p' (phase-only) or 'ap' (amplitude+phase)
    solint: str  # Solution interval (e.g., '30s', '60s', 'inf')
    caltable: str
    model_image: str
    residual_image: str
    peak_flux_jy: float
    rms_noise_jy: float
    snr: float
    dynamic_range: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfCalConfig:
    """Configuration for self-calibration iterations."""

    # Iteration control
    max_iterations: int = 5
    min_snr_improvement: float = 1.05  # Minimum 5% SNR improvement to continue
    stop_on_divergence: bool = True

    # Phase-only iterations
    phase_solints: List[str] = field(default_factory=lambda: ["30s", "60s", "inf"])
    phase_minsnr: float = 3.0
    phase_combine: str = ""  # Can be "spw", "scan", ""

    # Amplitude+phase iteration (final)
    do_amplitude: bool = True
    amp_solint: str = "inf"
    amp_minsnr: float = 5.0
    amp_combine: str = "scan"

    # Imaging parameters
    imsize: int = 1024
    cell_arcsec: Optional[float] = None
    niter: int = 10000
    threshold: str = "0.0005Jy"  # 0.5 mJy
    robust: float = 0.0
    backend: str = "wsclean"

    # Quality control
    min_initial_snr: float = 10.0  # Don't self-cal if initial SNR too low
    max_flagged_fraction: float = 0.5  # Stop if too much data flagged

    # Advanced
    refant: Optional[str] = None
    uvrange: str = ""
    spw: str = ""
    field: str = ""

    # Model seeding
    use_nvss_seeding: bool = False
    nvss_min_mjy: Optional[float] = 10.0
    calib_ra_deg: Optional[float] = None
    calib_dec_deg: Optional[float] = None
    calib_flux_jy: Optional[float] = None


class SelfCalibrator:
    """Iterative self-calibration for radio interferometric data."""

    def __init__(
        self,
        ms_path: str,
        output_dir: str,
        config: Optional[SelfCalConfig] = None,
        initial_caltables: Optional[List[str]] = None,
    ):
        """Initialize self-calibrator.

        Args:
            ms_path: Path to Measurement Set (must have CORRECTED_DATA or DATA)
            output_dir: Directory for self-cal products (images, caltables)
            config: Self-calibration configuration (uses defaults if None)
            initial_caltables: Existing calibration tables to apply first (e.g., BP, GP)
        """
        self.ms_path = Path(ms_path)
        self.output_dir = Path(output_dir)
        self.config = config or SelfCalConfig()
        self.initial_caltables = initial_caltables or []

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.iterations: List[SelfCalIteration] = []
        self.best_iteration: Optional[SelfCalIteration] = None

        # Fix MS permissions to ensure we can read/write
        # (CASA tasks may create MS files owned by root)
        logger.info(f"Initialized SelfCalibrator for {self.ms_path}")
        _fix_ms_permissions(self.ms_path)

        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Max iterations: {self.config.max_iterations}")

    def run(self) -> Tuple[bool, str]:
        """Run full self-calibration pipeline.

        Returns:
            (success, message): Success status and summary message
        """
        logger.info("=" * 80)
        logger.info("STARTING SELF-CALIBRATION PIPELINE")
        logger.info("=" * 80)

        start_time = time.time()

        # Step 0: Initial imaging to get baseline metrics
        logger.info("[0/N] Running initial imaging to establish baseline...")
        initial_result = self._run_initial_imaging()
        if not initial_result:
            return False, "Initial imaging failed"

        initial_snr = initial_result.snr
        logger.info(f"Initial SNR: {initial_snr:.1f}")

        if initial_snr < self.config.min_initial_snr:
            msg = f"Initial SNR ({initial_snr:.1f}) below minimum ({self.config.min_initial_snr})"
            logger.warning(msg)
            logger.warning("Self-calibration unlikely to improve results. Consider:")
            logger.warning("  1. Check calibration quality (BP, GP tables)")
            logger.warning("  2. Increase integration time")
            logger.warning("  3. Use stronger calibrator source")
            return False, msg

        # Phase-only iterations
        phase_iter_count = 0
        for phase_iter, solint in enumerate(self.config.phase_solints, start=1):
            logger.info("=" * 80)
            logger.info(
                f"[{phase_iter}/{len(self.config.phase_solints) + (1 if self.config.do_amplitude else 0)}] "
                f"Phase-only self-cal (solint={solint})"
            )
            logger.info("=" * 80)

            success = self._run_selfcal_iteration(
                iteration=phase_iter,
                calmode="p",
                solint=solint,
                minsnr=self.config.phase_minsnr,
                combine=self.config.phase_combine,
            )

            if not success:
                logger.warning(f"Phase iteration {phase_iter} failed, stopping")
                break

            # Check for convergence
            if not self._check_continue():
                logger.info("Self-cal converged or diverging, stopping phase iterations")
                break

            phase_iter_count = phase_iter

        # Amplitude+phase iteration (final)
        if self.config.do_amplitude and phase_iter_count > 0:
            amp_iter = phase_iter_count + 1
            logger.info("=" * 80)
            logger.info(
                f"[{amp_iter}/{len(self.config.phase_solints) + 1}] "
                f"Amplitude+phase self-cal (solint={self.config.amp_solint})"
            )
            logger.info("=" * 80)

            success = self._run_selfcal_iteration(
                iteration=amp_iter,
                calmode="ap",
                solint=self.config.amp_solint,
                minsnr=self.config.amp_minsnr,
                combine=self.config.amp_combine,
            )

            if not success:
                logger.warning("Amplitude+phase iteration failed")

        elapsed = time.time() - start_time

        # Summary
        logger.info("=" * 80)
        logger.info("SELF-CALIBRATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        logger.info(f"Iterations completed: {len(self.iterations)}")

        if self.best_iteration:
            logger.info(f"Best iteration: {self.best_iteration.iteration}")
            logger.info(f"Best SNR: {self.best_iteration.snr:.1f}")
            logger.info(f"Best dynamic range: {self.best_iteration.dynamic_range:.1f}")
            logger.info(f"SNR improvement: {self.best_iteration.snr / initial_snr:.2f}x")

            return (
                True,
                f"Self-cal successful: SNR {initial_snr:.1f} → {self.best_iteration.snr:.1f}",
            )
        else:
            return False, "Self-calibration did not improve results"

    def _run_initial_imaging(self) -> Optional[SelfCalIteration]:
        """Run initial imaging to establish baseline metrics."""
        imagename = str(self.output_dir / "selfcal_iter0")

        try:
            # Apply initial calibration tables if provided
            if self.initial_caltables:
                logger.info(f"Applying initial calibration tables: {self.initial_caltables}")
                if not CASATASKS_AVAILABLE:
                    raise RuntimeError("casatasks not available - required for self-calibration")

                applycal(
                    vis=str(self.ms_path),
                    gaintable=self.initial_caltables,
                    interp="linear",
                    calwt=False,
                    flagbackup=False,
                )

                # Fix permissions after applycal (CASA may change ownership)
                _fix_ms_permissions(self.ms_path)

            # Run imaging
            image_ms(
                ms_path=str(self.ms_path),
                imagename=imagename,
                imsize=self.config.imsize,
                cell_arcsec=self.config.cell_arcsec,
                niter=self.config.niter,
                threshold=self.config.threshold,
                robust=self.config.robust,
                backend=self.config.backend,
                field=self.config.field,
                spw=self.config.spw,
                uvrange=self.config.uvrange,
                use_nvss_mask=self.config.use_nvss_seeding,
                nvss_min_mjy=self.config.nvss_min_mjy,
                calib_ra_deg=self.config.calib_ra_deg,
                calib_dec_deg=self.config.calib_dec_deg,
                calib_flux_jy=self.config.calib_flux_jy,
                export_model_image=True,
            )

            # Fix permissions after imaging (WSClean/CASA may change ownership)
            _fix_ms_permissions(self.ms_path)

            # Update MODEL_DATA with cleaned model for next iteration
            # This is critical: each iteration must use the cleaned model from previous iteration
            self._update_model_data_from_image(imagename)

            # Extract metrics
            metrics = self._extract_image_metrics(imagename)
            if not metrics:
                return None

            peak_flux, rms_noise, snr, dynamic_range = metrics

            result = SelfCalIteration(
                iteration=0,
                calmode="initial",
                solint="N/A",
                caltable="N/A",
                model_image=f"{imagename}-model.fits",
                residual_image=f"{imagename}-residual.fits",
                peak_flux_jy=peak_flux,
                rms_noise_jy=rms_noise,
                snr=snr,
                dynamic_range=dynamic_range,
                success=True,
            )

            self.iterations.append(result)
            self.best_iteration = result

            logger.info(
                f"✓ Initial imaging: SNR={snr:.1f}, Peak={peak_flux*1000:.1f} mJy, "
                f"RMS={rms_noise*1000:.3f} mJy"
            )

            return result

        except Exception as e:
            logger.error(f"Initial imaging failed: {e}", exc_info=True)
            return None

    def _run_selfcal_iteration(
        self,
        iteration: int,
        calmode: str,
        solint: str,
        minsnr: float,
        combine: str,
    ) -> bool:
        """Run a single self-calibration iteration.

        Args:
            iteration: Iteration number
            calmode: 'p' (phase) or 'ap' (amplitude+phase)
            solint: Solution interval
            minsnr: Minimum SNR for solutions
            combine: Combine parameter for gaincal

        Returns:
            Success status
        """
        caltable = str(self.output_dir / f"selfcal_iter{iteration}_{calmode}.gcal")
        imagename = str(self.output_dir / f"selfcal_iter{iteration}")

        try:
            # Step 1: Solve for gains using current model
            logger.info(f"  [1/3] Solving for {calmode} gains (solint={solint}, minsnr={minsnr})")

            if not CASATASKS_AVAILABLE:
                raise RuntimeError("casatasks not available - required for self-calibration")

            # Fix permissions before gaincal
            _fix_ms_permissions(self.ms_path)

            gaincal(
                vis=str(self.ms_path),
                caltable=caltable,
                field=self.config.field,
                spw=self.config.spw,
                solint=solint,
                gaintype="G",
                calmode=calmode,
                minsnr=minsnr,
                refant=self.config.refant if self.config.refant else "",
                combine=combine,
                uvrange=self.config.uvrange,
                gaintable=self.initial_caltables,  # Include initial calibration
                append=False,
            )

            # Step 2: Validate calibration quality
            logger.info("  [2/3] Validating calibration quality")
            cal_result = validate_caltable_quality(caltable)

            if cal_result.has_issues:
                logger.warning(f"Calibration has issues: {cal_result.issues}")
                if "flagged" in str(cal_result.fraction_flagged):
                    frac = float(cal_result.fraction_flagged.replace("%", "")) / 100
                    if frac > self.config.max_flagged_fraction:
                        logger.error(f"Too much data flagged ({frac:.1%}), stopping")
                        return False

            # Step 3: Apply calibration and image
            logger.info("  [3/3] Applying calibration and imaging")

            # Combine all calibration tables (initial + this iteration)
            all_caltables = self.initial_caltables + [caltable]

            applycal(
                vis=str(self.ms_path),
                gaintable=all_caltables,
                interp="linear",
                calwt=False,
                flagbackup=False,
            )

            # Fix permissions after applycal (CASA may change ownership)
            _fix_ms_permissions(self.ms_path)

            # Image with new calibration
            image_ms(
                ms_path=str(self.ms_path),
                imagename=imagename,
                imsize=self.config.imsize,
                cell_arcsec=self.config.cell_arcsec,
                niter=self.config.niter,
                threshold=self.config.threshold,
                robust=self.config.robust,
                backend=self.config.backend,
                field=self.config.field,
                spw=self.config.spw,
                uvrange=self.config.uvrange,
                use_nvss_mask=self.config.use_nvss_seeding,
                nvss_min_mjy=self.config.nvss_min_mjy,
                calib_ra_deg=self.config.calib_ra_deg,
                calib_dec_deg=self.config.calib_dec_deg,
                calib_flux_jy=self.config.calib_flux_jy,
                export_model_image=True,
            )

            # Fix permissions after imaging
            _fix_ms_permissions(self.ms_path)

            # Update MODEL_DATA with cleaned model for next iteration
            # This is critical: each iteration must use the cleaned model from previous iteration
            self._update_model_data_from_image(imagename)

            # Extract metrics
            metrics = self._extract_image_metrics(imagename)
            if not metrics:
                logger.error("Failed to extract image metrics")
                return False

            peak_flux, rms_noise, snr, dynamic_range = metrics

            result = SelfCalIteration(
                iteration=iteration,
                calmode=calmode,
                solint=solint,
                caltable=caltable,
                model_image=f"{imagename}-model.fits",
                residual_image=f"{imagename}-residual.fits",
                peak_flux_jy=peak_flux,
                rms_noise_jy=rms_noise,
                snr=snr,
                dynamic_range=dynamic_range,
                success=True,
                metadata={
                    "minsnr": minsnr,
                    "combine": combine,
                    "cal_flagged_fraction": cal_result.fraction_flagged,
                },
            )

            self.iterations.append(result)

            # Update best iteration
            if not self.best_iteration or result.snr > self.best_iteration.snr:
                self.best_iteration = result
                logger.info(
                    f"  ✓ NEW BEST: SNR={snr:.1f}, Peak={peak_flux*1000:.1f} mJy, "
                    f"RMS={rms_noise*1000:.3f} mJy"
                )
            else:
                logger.info(
                    f"  ✓ SNR={snr:.1f}, Peak={peak_flux*1000:.1f} mJy, "
                    f"RMS={rms_noise*1000:.3f} mJy"
                )

            return True

        except Exception as e:
            logger.error(f"Self-cal iteration {iteration} failed: {e}", exc_info=True)

            result = SelfCalIteration(
                iteration=iteration,
                calmode=calmode,
                solint=solint,
                caltable=caltable,
                model_image="",
                residual_image="",
                peak_flux_jy=0.0,
                rms_noise_jy=0.0,
                snr=0.0,
                dynamic_range=0.0,
                success=False,
                error_message=str(e),
            )
            self.iterations.append(result)

            return False

    def _update_model_data_from_image(self, imagename: str) -> bool:
        """Update MODEL_DATA column with cleaned model image from previous iteration.

        This is critical for self-calibration: each iteration must use the cleaned
        model from the previous iteration, not the original seeded model.

        Args:
            imagename: Base image name (will look for {imagename}-model.fits)

        Returns:
            True if successful, False otherwise
        """
        model_fits = f"{imagename}-model.fits"
        if not os.path.exists(model_fits):
            logger.warning(f"Model image not found: {model_fits}, skipping MODEL_DATA update")
            return False

        try:
            if self.config.backend == "wsclean":
                # Use WSClean -predict (faster, multi-threaded, avoids CASA phase center bugs)
                logger.info(
                    f"  [4/4] Updating MODEL_DATA with cleaned model using WSClean -predict"
                )

                # Find WSClean executable
                import shutil

                wsclean_exec = shutil.which("wsclean")
                if not wsclean_exec:
                    # Try Docker fallback
                    logger.info("WSClean not found, trying Docker...")
                    ms_dir = str(self.ms_path.parent)
                    ms_name = self.ms_path.name
                    model_dir = str(Path(model_fits).parent)
                    model_name = Path(model_fits).name
                    model_prefix = imagename

                    cmd_predict = [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        f"{ms_dir}:/data_ms",
                        "-v",
                        f"{model_dir}:/data_model",
                        "wsclean-everybeam-0.7.4",
                        "wsclean",
                        "-predict",
                        "-reorder",  # Required for multi-SPW MS
                        "-name",
                        f"/data_model/{Path(imagename).name}",
                        f"/data_ms/{ms_name}",
                    ]
                    logger.info(f"Running: {' '.join(cmd_predict)}")
                    subprocess.run(cmd_predict, check=True)
                else:
                    # Native WSClean
                    cmd_predict = [
                        wsclean_exec,
                        "-predict",
                        "-reorder",  # Required for multi-SPW MS
                        "-name",
                        imagename,
                        str(self.ms_path),
                    ]
                    logger.info(f"Running: {' '.join(cmd_predict)}")
                    subprocess.run(cmd_predict, check=True)

                logger.info("✓ MODEL_DATA updated with cleaned model")
                return True

            else:
                # CASA backend: use ft() (slower, but works)
                logger.info(f"  [4/4] Updating MODEL_DATA with cleaned model using CASA ft()")
                # Convert FITS to CASA image format if needed
                # WSClean outputs FITS, but ft() expects CASA image format
                # We need to import the FITS into CASA first
                import tempfile

                from dsa110_contimg.calibration.model import write_image_model_with_ft

                casa_image = f"{imagename}.casa_model"

                from casatasks import importfits

                importfits(fitsimage=model_fits, imagename=casa_image, overwrite=True)

                try:
                    write_image_model_with_ft(str(self.ms_path), casa_image)
                    logger.info("✓ MODEL_DATA updated with cleaned model")
                    return True
                finally:
                    # Clean up temporary CASA image
                    if os.path.exists(casa_image):
                        import shutil

                        shutil.rmtree(casa_image)

        except Exception as e:
            logger.warning(f"Failed to update MODEL_DATA from {model_fits}: {e}")
            logger.debug("Traceback:", exc_info=True)
            return False

    def _extract_image_metrics(self, imagename: str) -> Optional[Tuple[float, float, float, float]]:
        """Extract peak flux, RMS noise, SNR, and dynamic range from image.

        Args:
            imagename: Base image name (will look for -image.fits and -residual.fits)

        Returns:
            (peak_flux_jy, rms_noise_jy, snr, dynamic_range) or None if failed
        """
        image_fits = f"{imagename}-image.fits"
        residual_fits = f"{imagename}-residual.fits"

        try:
            # Read image
            with fits.open(image_fits) as hdul:
                image_data = np.asarray(hdul[0].data).squeeze()
                if image_data.ndim > 2:
                    image_data = image_data[0] if image_data.ndim == 3 else image_data[0, 0]

            # Read residual
            with fits.open(residual_fits) as hdul:
                residual_data = np.asarray(hdul[0].data).squeeze()
                if residual_data.ndim > 2:
                    residual_data = (
                        residual_data[0] if residual_data.ndim == 3 else residual_data[0, 0]
                    )

            # Calculate metrics
            peak_flux = float(np.nanmax(np.abs(image_data)))

            # RMS from residual (robust estimate)
            valid_residual = residual_data[~np.isnan(residual_data)]
            rms_noise = float(np.std(valid_residual))

            snr = peak_flux / rms_noise if rms_noise > 0 else 0.0
            dynamic_range = peak_flux / rms_noise if rms_noise > 0 else 0.0

            return peak_flux, rms_noise, snr, dynamic_range

        except Exception as e:
            logger.error(f"Failed to extract metrics from {imagename}: {e}")
            return None

    def _check_continue(self) -> bool:
        """Check if self-calibration should continue.

        Returns:
            True if should continue, False if should stop
        """
        if len(self.iterations) < 2:
            return True

        current = self.iterations[-1]
        previous = self.iterations[-2]

        if not current.success:
            logger.warning("Current iteration failed")
            return False

        # Check for SNR improvement
        snr_ratio = current.snr / previous.snr

        if snr_ratio < 1.0 and self.config.stop_on_divergence:
            logger.warning(f"SNR decreased ({snr_ratio:.3f}x), stopping to prevent divergence")
            return False

        if snr_ratio < self.config.min_snr_improvement:
            logger.info(
                f"SNR improvement ({snr_ratio:.3f}x) below threshold "
                f"({self.config.min_snr_improvement}), converged"
            )
            return False

        logger.info(f"SNR improved {snr_ratio:.3f}x, continuing")
        return True

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of self-calibration results.

        Returns:
            Dictionary with summary statistics
        """
        if not self.iterations:
            return {"status": "not_run"}

        initial = self.iterations[0]
        final = self.iterations[-1]

        return {
            "status": "success" if any(it.success for it in self.iterations) else "failed",
            "iterations_completed": len(self.iterations),
            "initial_snr": initial.snr,
            "final_snr": final.snr,
            "best_snr": self.best_iteration.snr if self.best_iteration else 0.0,
            "snr_improvement": final.snr / initial.snr if initial.snr > 0 else 0.0,
            "best_iteration": self.best_iteration.iteration if self.best_iteration else None,
            "iterations": [
                {
                    "iteration": it.iteration,
                    "calmode": it.calmode,
                    "solint": it.solint,
                    "snr": it.snr,
                    "peak_flux_mjy": it.peak_flux_jy * 1000,
                    "rms_noise_mjy": it.rms_noise_jy * 1000,
                    "success": it.success,
                }
                for it in self.iterations
            ],
        }


def selfcal_ms(
    ms_path: str,
    output_dir: str,
    config: Optional[SelfCalConfig] = None,
    initial_caltables: Optional[List[str]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """Convenience function to run self-calibration on an MS.

    Args:
        ms_path: Path to Measurement Set
        output_dir: Output directory for self-cal products
        config: Self-calibration configuration
        initial_caltables: Initial calibration tables (BP, GP)

    Returns:
        (success, summary_dict): Success status and summary dictionary
    """
    selfcal = SelfCalibrator(
        ms_path=ms_path,
        output_dir=output_dir,
        config=config,
        initial_caltables=initial_caltables,
    )

    success, message = selfcal.run()
    summary = selfcal.get_summary()
    summary["message"] = message

    return success, summary

"""
Self-calibration stage: Iteratively refine calibration using image model.

This stage wraps the core calibration.selfcal module to provide a
SubbandGroup-aware interface for the streaming pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import SubbandGroup

logger = logging.getLogger(__name__)


@dataclass
class SelfCalResult:
    """Result of self-calibration operations."""

    success: bool
    group: SubbandGroup
    ms_path: Optional[str] = None
    improvement_factor: float = 1.0
    iterations_completed: int = 0
    final_snr: Optional[float] = None
    initial_snr: Optional[float] = None
    gaintables: List[str] = field(default_factory=list)
    final_image: Optional[str] = None
    status: str = "unknown"  # converged, max_iterations, diverged, failed, no_improvement
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "group_id": self.group.group_id,
            "ms_path": self.ms_path,
            "improvement_factor": self.improvement_factor,
            "iterations_completed": self.iterations_completed,
            "final_snr": self.final_snr,
            "initial_snr": self.initial_snr,
            "gaintables": self.gaintables,
            "final_image": self.final_image,
            "status": self.status,
            "error_message": self.error_message,
            "elapsed_seconds": self.elapsed_seconds,
            "metrics": self.metrics,
        }


@dataclass
class SelfCalConfig:
    """Configuration for the self-calibration stage.

    Attributes:
        output_dir: Base directory for self-cal products
        max_iterations: Maximum number of self-cal iterations
        min_snr_improvement: Minimum fractional SNR improvement to continue
        stop_on_divergence: Stop if SNR decreases
        phase_solints: Solution intervals for phase-only iterations
        phase_minsnr: Minimum SNR for phase solutions
        do_amplitude: Whether to do amplitude self-cal after phase
        amp_solint: Solution interval for amplitude+phase
        amp_minsnr: Minimum SNR for amplitude solutions
        imsize: Image size in pixels
        niter: Clean iterations per imaging cycle
        threshold: Clean threshold (e.g., "0.1mJy")
        robust: Briggs robust weighting parameter
        backend: Imaging backend ("wsclean" or "tclean")
        min_initial_snr: Minimum initial SNR required to start
        skip_for_calibrators: Skip selfcal for calibrator observations
    """

    output_dir: Path = field(default_factory=lambda: Path("/data/state/selfcal"))
    max_iterations: int = 5
    min_snr_improvement: float = 1.05
    stop_on_divergence: bool = True
    phase_solints: List[str] = field(default_factory=lambda: ["60s", "30s", "inf"])
    phase_minsnr: float = 3.0
    do_amplitude: bool = True
    amp_solint: str = "inf"
    amp_minsnr: float = 5.0
    imsize: int = 1024
    niter: int = 10000
    threshold: str = "0.1mJy"
    robust: float = 0.0
    backend: str = "wsclean"
    min_initial_snr: float = 5.0
    skip_for_calibrators: bool = True


class SelfCalStage:
    """Stage for self-calibration of Measurement Sets.

    This stage takes a SubbandGroup that has already been converted and
    calibrated, then runs iterative self-calibration to improve dynamic range.

    Self-calibration workflow:
    1. Create initial image from calibrated data
    2. Predict model visibilities to MODEL_DATA
    3. Solve gaincal (phase-only, then amplitude+phase)
    4. Apply new calibration
    5. Re-image with improved calibration
    6. Repeat until convergence or max iterations

    Example:
        >>> config = SelfCalConfig(
        ...     output_dir=Path("/data/selfcal"),
        ...     max_iterations=5,
        ... )
        >>> stage = SelfCalStage(config)
        >>> result = stage.execute(group)
        >>> if result.success:
        ...     print(f"Improved by {result.improvement_factor:.2f}x")
    """

    def __init__(self, config: SelfCalConfig) -> None:
        """Initialize the self-calibration stage.

        Args:
            config: Self-calibration configuration
        """
        self.config = config

    def validate(self, group: SubbandGroup) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for self-calibration.

        Args:
            group: SubbandGroup with completed conversion and calibration

        Returns:
            Tuple of (is_valid, error_message)
        """
        if group.ms_path is None:
            return False, "No MS path in group - conversion required first"

        if not Path(group.ms_path).exists():
            return False, f"MS not found: {group.ms_path}"

        # Skip calibrator observations if configured
        if self.config.skip_for_calibrators and group.has_calibrator:
            return False, "Skipping self-cal for calibrator observation"

        # Ensure output directory exists
        try:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"Cannot create output directory: {e}"

        # Verify CORRECTED_DATA exists
        try:
            import casacore.tables as casatables

            with casatables.table(str(group.ms_path), readonly=True) as tb:
                if "CORRECTED_DATA" not in tb.colnames():
                    return False, "CORRECTED_DATA not found - initial calibration required"
        except ImportError:
            logger.warning("casacore not available, skipping CORRECTED_DATA check")
        except Exception as e:
            return False, f"Cannot validate MS structure: {e}"

        return True, None

    def execute(self, group: SubbandGroup) -> SelfCalResult:
        """Execute self-calibration on a SubbandGroup.

        Args:
            group: SubbandGroup with MS path from prior conversion/calibration

        Returns:
            SelfCalResult with status and improvements
        """
        t0 = time.perf_counter()
        ms_path = str(group.ms_path)

        # Validate prerequisites
        is_valid, error = self.validate(group)
        if not is_valid:
            # Special case: skipping for calibrator is not a failure
            if error and "Skipping self-cal for calibrator" in error:
                return SelfCalResult(
                    success=True,
                    group=group,
                    ms_path=ms_path,
                    status="skipped",
                    error_message=error,
                    elapsed_seconds=time.perf_counter() - t0,
                )
            return SelfCalResult(
                success=False,
                group=group,
                ms_path=ms_path,
                status="failed",
                error_message=error,
                elapsed_seconds=time.perf_counter() - t0,
            )

        try:
            return self._run_selfcal(group, t0)
        except Exception as e:
            logger.error(f"Self-calibration failed for {group.group_id}: {e}", exc_info=True)
            return SelfCalResult(
                success=False,
                group=group,
                ms_path=ms_path,
                status="failed",
                error_message=str(e),
                elapsed_seconds=time.perf_counter() - t0,
            )

    def _run_selfcal(self, group: SubbandGroup, t0: float) -> SelfCalResult:
        """Run the actual self-calibration loop.

        Args:
            group: SubbandGroup to process
            t0: Start time for elapsed calculation

        Returns:
            SelfCalResult with outcomes
        """
        from dsa110_contimg.calibration.selfcal import (
            SelfCalConfig as CoreSelfCalConfig,
            selfcal_ms,
        )

        ms_path = str(group.ms_path)

        # Create output directory for this group
        output_dir = self.config.output_dir / group.group_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build core config from our config
        core_config = CoreSelfCalConfig(
            max_iterations=self.config.max_iterations,
            min_snr_improvement=self.config.min_snr_improvement,
            stop_on_divergence=self.config.stop_on_divergence,
            phase_solints=self.config.phase_solints.copy(),
            phase_minsnr=self.config.phase_minsnr,
            do_amplitude=self.config.do_amplitude,
            amp_solint=self.config.amp_solint,
            amp_minsnr=self.config.amp_minsnr,
            imsize=self.config.imsize,
            niter=self.config.niter,
            threshold=self.config.threshold,
            robust=self.config.robust,
            backend=self.config.backend,
            min_initial_snr=self.config.min_initial_snr,
        )

        logger.info(
            f"Starting self-calibration for {group.group_id} "
            f"(max {self.config.max_iterations} iterations)"
        )

        # Run self-calibration
        success, summary = selfcal_ms(
            ms_path=ms_path,
            output_dir=str(output_dir),
            config=core_config,
        )

        elapsed = time.perf_counter() - t0

        # Map the core result to our result model
        status = summary.get("status", "unknown")
        if isinstance(status, object) and hasattr(status, "value"):
            status = status.value  # Handle enum

        result = SelfCalResult(
            success=success,
            group=group,
            ms_path=ms_path,
            improvement_factor=summary.get("improvement_factor", 1.0),
            iterations_completed=summary.get("iterations_completed", 0),
            final_snr=summary.get("final_snr"),
            initial_snr=summary.get("initial_snr"),
            gaintables=summary.get("final_gaintables", []),
            final_image=summary.get("final_image"),
            status=status,
            elapsed_seconds=elapsed,
            metrics={
                "output_dir": str(output_dir),
                "phase_solints": self.config.phase_solints,
                "do_amplitude": self.config.do_amplitude,
            },
        )

        if success:
            logger.info(
                f"Self-cal complete for {group.group_id}: "
                f"{result.improvement_factor:.2f}x improvement in "
                f"{result.iterations_completed} iterations"
            )
        else:
            logger.warning(
                f"Self-cal did not improve {group.group_id}: {status}"
            )

        return result

"""
Adaptive RFI flagging with calibration-aware strategy selection.

This module implements an adaptive flagging approach that:
1. Attempts flagging with a default (less aggressive) strategy
2. Tests if calibration succeeds after flagging
3. Falls back to more aggressive strategies if calibration fails
4. Optionally uses GPU-accelerated RFI detection

The goal is to flag enough RFI to allow successful calibration without
over-flagging good data.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)


class CalibrationFailure(Exception):
    """Exception raised when calibration fails during adaptive flagging.

    This exception is used to signal that the current flagging strategy
    is insufficient and a more aggressive approach should be tried.
    """


class AdaptiveFlaggingResult(TypedDict):
    """Result from adaptive flagging operation."""

    success: bool
    strategy: str
    attempts: int
    flagged_fraction: float
    calibration_error: Optional[str]
    processing_time_s: float


@dataclass
class FlaggingStrategy:
    """Configuration for a flagging strategy."""

    name: str
    backend: str  # "aoflagger" or "casa"
    strategy_file: Optional[str] = None  # For AOFlagger Lua strategies
    aggressive: bool = False
    threshold_scale: float = 1.0  # Multiplier for detection thresholds
    use_gpu: bool = False  # Whether to use GPU RFI detection


# Default strategy chain: try in order until calibration succeeds
DEFAULT_STRATEGY_CHAIN: List[FlaggingStrategy] = [
    FlaggingStrategy(
        name="default",
        backend="aoflagger",
        strategy_file=None,  # Uses dsa110-default.lua
        aggressive=False,
    ),
    FlaggingStrategy(
        name="aggressive",
        backend="aoflagger",
        strategy_file="/data/dsa110-contimg/config/dsa110-aggressive.lua",
        aggressive=True,
    ),
    FlaggingStrategy(
        name="casa_tfcrop",
        backend="casa",
        aggressive=True,
        threshold_scale=0.8,  # Tighter thresholds
    ),
]


def _get_flag_fraction(ms_path: str) -> float:
    """Get the fraction of flagged data in a measurement set."""
    try:
        import casacore.tables as casatables
        import numpy as np

        with casatables.table(ms_path, readonly=True) as tb:
            flags = tb.getcol("FLAG")
            if flags.size == 0:
                return 0.0
            return float(np.sum(flags) / flags.size)
    except (OSError, RuntimeError, KeyError) as e:
        logger.warning("Failed to get flag fraction: %s", e)
        return 0.0


def _apply_gpu_flagging(
    ms_path: str,
    strategy: FlaggingStrategy,
    datacolumn: str,
) -> bool:
    """Apply GPU-accelerated RFI flagging.

    Returns:
        True if GPU flagging succeeded, False if fallback needed.
    """
    try:
        from dsa110_contimg.rfi import RFIDetectionConfig, gpu_rfi_detection

        config = RFIDetectionConfig(
            threshold=5.0 / strategy.threshold_scale,
            apply_flags=True,
        )
        result = gpu_rfi_detection(ms_path, config=config)

        if result.success:
            return True
        logger.warning("GPU RFI detection failed: %s", result.error)
        return False
    except ImportError:
        logger.warning("GPU RFI detection not available, using standard flagging")
        return False


def _apply_flagging_strategy(
    ms_path: str,
    strategy: FlaggingStrategy,
    datacolumn: str = "data",
) -> float:
    """Apply a flagging strategy and return the new flagged fraction.

    Args:
        ms_path: Path to measurement set
        strategy: Flagging strategy to apply
        datacolumn: Data column to flag

    Returns:
        Flagged fraction after applying strategy
    """
    from dsa110_contimg.calibration.flagging import flag_rfi, flag_zeros, reset_flags

    logger.info("Applying flagging strategy: %s (backend=%s)", strategy.name, strategy.backend)

    # Reset flags before applying new strategy
    reset_flags(ms_path)
    flag_zeros(ms_path, datacolumn=datacolumn)

    initial_fraction = _get_flag_fraction(ms_path)

    # Try GPU if requested, fall back to standard if it fails
    gpu_succeeded = False
    if strategy.use_gpu:
        gpu_succeeded = _apply_gpu_flagging(ms_path, strategy, datacolumn)

    # Use standard flagging if GPU not requested or failed
    if not strategy.use_gpu or not gpu_succeeded:
        flag_rfi(
            ms_path,
            datacolumn=datacolumn,
            backend=strategy.backend,
            strategy=strategy.strategy_file,
        )

    final_fraction = _get_flag_fraction(ms_path)
    logger.info(
        "Strategy '%s': flagged fraction %.2f%% -> %.2f%%",
        strategy.name,
        initial_fraction * 100,
        final_fraction * 100,
    )

    return final_fraction


def flag_rfi_adaptive(
    ms_path: str,
    refant: str,
    calibrate_fn: Callable[[str, str], None],
    calibrate_kwargs: Optional[Dict[str, Any]] = None,
    aggressive_strategy: Optional[str] = None,
    backend: str = "aoflagger",
    datacolumn: str = "data",
    max_attempts: int = 3,
    strategy_chain: Optional[List[FlaggingStrategy]] = None,
    use_gpu_rfi: bool = False,
) -> AdaptiveFlaggingResult:
    """
    Perform adaptive RFI flagging with calibration-aware strategy selection.

    This function implements an iterative approach:
    1. Apply a flagging strategy
    2. Attempt calibration
    3. If calibration fails, try a more aggressive strategy
    4. Repeat until calibration succeeds or all strategies exhausted

    Args:
        ms_path: Path to measurement set
        refant: Reference antenna for calibration
        calibrate_fn: Calibration function to call. Should accept (ms_path, refant, **kwargs)
                     and raise CalibrationFailure if calibration fails.
        calibrate_kwargs: Additional kwargs to pass to calibrate_fn
        aggressive_strategy: Path to aggressive AOFlagger strategy file (for backward compat)
        backend: Default flagging backend ("aoflagger" or "casa")
        datacolumn: Data column to flag
        max_attempts: Maximum number of flagging attempts
        strategy_chain: Custom strategy chain to use (default: DEFAULT_STRATEGY_CHAIN)
        use_gpu_rfi: Whether to try GPU RFI detection first

    Returns:
        AdaptiveFlaggingResult with success status, strategy used, and statistics
    """
    start_time = time.time()
    calibrate_kwargs = calibrate_kwargs or {}

    # Build strategy chain
    if strategy_chain is None:
        strategy_chain = list(DEFAULT_STRATEGY_CHAIN)  # Copy to avoid mutation

        # Override aggressive strategy if provided
        if aggressive_strategy:
            for s in strategy_chain:
                if s.name == "aggressive":
                    s.strategy_file = aggressive_strategy

    # Optionally prepend GPU strategy
    if use_gpu_rfi:
        gpu_strategy = FlaggingStrategy(
            name="gpu_default",
            backend="aoflagger",
            use_gpu=True,
            aggressive=False,
        )
        strategy_chain.insert(0, gpu_strategy)

    # Limit to max_attempts
    strategy_chain = strategy_chain[:max_attempts]

    last_error: Optional[str] = None
    final_flagged_fraction = 0.0

    for attempt, strategy in enumerate(strategy_chain, 1):
        logger.info(
            "Adaptive flagging attempt %d/%d: %s", attempt, len(strategy_chain), strategy.name
        )

        try:
            # Apply flagging strategy
            final_flagged_fraction = _apply_flagging_strategy(
                ms_path, strategy, datacolumn=datacolumn
            )

            # Attempt calibration
            logger.info("Testing calibration after %s flagging...", strategy.name)
            calibrate_fn(ms_path, refant, **calibrate_kwargs)

            # Calibration succeeded!
            logger.info("Calibration succeeded with strategy: %s", strategy.name)
            return AdaptiveFlaggingResult(
                success=True,
                strategy=strategy.name,
                attempts=attempt,
                flagged_fraction=final_flagged_fraction,
                calibration_error=None,
                processing_time_s=time.time() - start_time,
            )

        except CalibrationFailure as e:
            last_error = str(e)
            logger.warning("Calibration failed with strategy '%s': %s", strategy.name, e)
            if attempt < len(strategy_chain):
                logger.info("Trying more aggressive flagging strategy...")
            continue

        except (OSError, RuntimeError, ValueError) as e:
            # Unexpected error - log but continue trying
            last_error = str(e)
            logger.error(
                "Unexpected error during adaptive flagging attempt %d: %s",
                attempt,
                e,
                exc_info=True,
            )
            if attempt < len(strategy_chain):
                logger.info("Trying next flagging strategy...")
            continue

    # All strategies exhausted
    logger.error(
        "Adaptive flagging failed: all %d strategies exhausted. Last error: %s",
        len(strategy_chain),
        last_error,
    )

    return AdaptiveFlaggingResult(
        success=False,
        strategy=strategy_chain[-1].name if strategy_chain else "none",
        attempts=len(strategy_chain),
        flagged_fraction=final_flagged_fraction,
        calibration_error=last_error,
        processing_time_s=time.time() - start_time,
    )


def flag_rfi_with_gpu_fallback(
    ms_path: str,
    *,
    threshold: float = 5.0,
    backend: str = "aoflagger",
    strategy: Optional[str] = None,
    prefer_gpu: bool = True,
) -> Dict[str, Any]:
    """
    Flag RFI with automatic GPU/CPU fallback.

    Attempts GPU-accelerated flagging first (if available and preferred),
    falling back to standard AOFlagger/CASA flagging if GPU fails.

    Args:
        ms_path: Path to measurement set
        threshold: Detection threshold in MAD units (for GPU)
        backend: Fallback backend ("aoflagger" or "casa")
        strategy: AOFlagger strategy file path
        prefer_gpu: Whether to try GPU first

    Returns:
        Dict with flagging results and method used
    """
    from dsa110_contimg.calibration.flagging import flag_rfi

    result: Dict[str, Any] = {
        "method": "unknown",
        "success": False,
        "flagged_fraction": 0.0,
        "error": None,
    }

    # Try GPU first if preferred
    if prefer_gpu:
        gpu_result = _try_gpu_flagging(ms_path, threshold, result)
        if gpu_result is not None:
            return gpu_result

    # Fall back to standard flagging
    logger.info("Using standard RFI flagging (backend=%s)", backend)
    try:
        initial_fraction = _get_flag_fraction(ms_path)
        flag_rfi(ms_path, backend=backend, strategy=strategy)
        final_fraction = _get_flag_fraction(ms_path)

        result["method"] = backend
        result["success"] = True
        result["flagged_fraction"] = final_fraction
        result["rfi_flagged"] = final_fraction - initial_fraction

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        result["error"] = str(e)
        logger.error("Standard RFI flagging failed: %s", e)

    return result


def _try_gpu_flagging(
    ms_path: str,
    threshold: float,
    result: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Try GPU-accelerated flagging.

    Returns:
        Updated result dict if GPU succeeded, None if fallback needed.
    """
    try:
        from dsa110_contimg.rfi import RFIDetectionConfig, gpu_rfi_detection
        from dsa110_contimg.rfi.gpu_detection import CUPY_AVAILABLE

        if not CUPY_AVAILABLE:
            logger.debug("CuPy not available, skipping GPU RFI detection")
            return None

        logger.info("Attempting GPU-accelerated RFI flagging...")
        config = RFIDetectionConfig(
            threshold=threshold,
            apply_flags=True,
        )
        gpu_result = gpu_rfi_detection(ms_path, config=config)

        if gpu_result.success:
            result["method"] = "gpu"
            result["success"] = True
            result["flagged_fraction"] = gpu_result.flag_percent / 100.0
            result["processing_time_s"] = gpu_result.processing_time_s
            logger.info(
                "GPU RFI flagging complete: %.2f%% flagged in %.2fs",
                gpu_result.flag_percent,
                gpu_result.processing_time_s,
            )
            return result

        logger.warning("GPU RFI flagging failed: %s", gpu_result.error)
        return None

    except ImportError:
        logger.debug("GPU RFI module not available")
        return None
    except (OSError, RuntimeError) as e:
        logger.warning("GPU RFI flagging failed: %s", e)
        return None

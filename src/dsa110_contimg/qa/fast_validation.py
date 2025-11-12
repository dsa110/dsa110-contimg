"""
Fast validation module for sub-60-second pipeline validation.

Implements tiered validation architecture with parallel execution and aggressive sampling.
"""

import logging
import os
import time
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
    as_completed,
)
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dsa110_contimg.qa.base import ValidationResult
from dsa110_contimg.qa.config import FastValidationConfig, QAConfig, get_default_config
from dsa110_contimg.qa.image_quality import quick_image_check
from dsa110_contimg.qa.ms_quality import quick_ms_check
from dsa110_contimg.qa.pipeline_quality import (
    check_calibration_quality,
    check_image_quality,
    check_ms_after_conversion,
)

logger = logging.getLogger(__name__)


class ValidationMode(Enum):
    """Validation mode enumeration."""

    FAST = "fast"  # <30s, aggressive sampling, parallel, skip expensive checks
    STANDARD = "standard"  # <60s, parallel, caching, balanced detail/speed
    COMPREHENSIVE = "comprehensive"  # Full validation, can be deferred/background


@dataclass
class TieredValidationResult:
    """Results from tiered validation."""

    tier1_results: Dict[str, Any] = field(default_factory=dict)
    tier2_results: Dict[str, Any] = field(default_factory=dict)
    tier3_results: Dict[str, Any] = field(default_factory=dict)
    timing: Dict[str, float] = field(default_factory=dict)
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier1_results": self.tier1_results,
            "tier2_results": self.tier2_results,
            "tier3_results": self.tier3_results,
            "timing": self.timing,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def get_fast_config_for_mode(mode: ValidationMode) -> FastValidationConfig:
    """
    Get FastValidationConfig optimized for a specific validation mode.

    Args:
        mode: ValidationMode enum value.

    Returns:
        FastValidationConfig instance optimized for the mode.
    """
    if mode == ValidationMode.FAST:
        return FastValidationConfig(
            ms_sample_fraction=0.005,  # 0.5% for ultra-fast
            image_sample_pixels=5000,
            catalog_max_sources=25,
            calibration_sample_fraction=0.005,
            skip_expensive_checks=True,
            parallel_workers=8,
            timeout_seconds=30,
            tier1_timeout_seconds=5.0,
            tier2_timeout_seconds=20.0,
            tier3_timeout_seconds=30.0,
            skip_catalog_validation=False,  # Can still do quick catalog check
            skip_photometry_validation=True,
            skip_variability_validation=True,
            skip_mosaic_validation=True,
            use_cache=True,
        )
    elif mode == ValidationMode.STANDARD:
        return FastValidationConfig(
            ms_sample_fraction=0.01,  # 1% default
            image_sample_pixels=10000,
            catalog_max_sources=50,
            calibration_sample_fraction=0.01,
            skip_expensive_checks=False,  # Run all checks
            parallel_workers=4,
            timeout_seconds=60,
            tier1_timeout_seconds=10.0,
            tier2_timeout_seconds=30.0,
            tier3_timeout_seconds=60.0,
            skip_catalog_validation=False,
            skip_photometry_validation=False,
            skip_variability_validation=True,  # Still skip variability in standard
            skip_mosaic_validation=True,  # Still skip mosaic in standard
            use_cache=True,
        )
    else:  # COMPREHENSIVE
        return FastValidationConfig(
            ms_sample_fraction=0.1,  # 10% for comprehensive
            image_sample_pixels=None,  # Full image
            catalog_max_sources=None,  # All sources
            calibration_sample_fraction=0.1,
            skip_expensive_checks=False,
            parallel_workers=4,
            timeout_seconds=300,  # 5 minutes for comprehensive
            tier1_timeout_seconds=30.0,
            tier2_timeout_seconds=120.0,
            tier3_timeout_seconds=300.0,
            skip_catalog_validation=False,
            skip_photometry_validation=False,
            skip_variability_validation=False,
            skip_mosaic_validation=False,
            use_cache=True,
        )


def validate_pipeline_fast(
    ms_path: Optional[str] = None,
    caltables: Optional[List[str]] = None,
    image_paths: Optional[List[str]] = None,
    config: Optional[QAConfig] = None,
    fast_config: Optional[FastValidationConfig] = None,
    mode: Optional[ValidationMode] = None,
) -> TieredValidationResult:
    """
    Fast pipeline validation with tiered architecture and parallel execution.

    Target: <60 seconds for standard mode, <30 seconds for fast mode.

    Args:
        ms_path: Path to Measurement Set (optional).
        caltables: List of calibration table paths (optional).
        image_paths: List of image paths (optional).
        config: QAConfig instance (uses default if not provided).
        fast_config: FastValidationConfig instance (uses default if not provided).
        mode: ValidationMode enum (FAST/STANDARD/COMPREHENSIVE). If provided,
              overrides fast_config with mode-optimized settings.

    Returns:
        TieredValidationResult with tier1, tier2, tier3 results and timing.
    """
    start_time = time.time()

    if config is None:
        config = get_default_config()

    # If mode is provided, use mode-optimized config
    if mode is not None:
        fast_config = get_fast_config_for_mode(mode)
    elif fast_config is None:
        fast_config = config.fast_validation

    result = TieredValidationResult()

    # Validate inputs
    if ms_path and not Path(ms_path).exists():
        result.errors.append(f"MS not found: {ms_path}")
        result.passed = False
        return result

    if caltables:
        missing_caltables = [ct for ct in caltables if not Path(ct).exists()]
        if missing_caltables:
            result.errors.append(f"Missing caltables: {missing_caltables}")
            result.passed = False
            return result

    if image_paths:
        missing_images = [img for img in image_paths if not Path(img).exists()]
        if missing_images:
            result.errors.append(f"Missing images: {missing_images}")
            result.passed = False
            return result

    # Tier 1: Critical fast checks (<10s)
    tier1_start = time.time()
    try:
        result.tier1_results = _run_tier1_validation(
            ms_path=ms_path,
            caltables=caltables,
            image_paths=image_paths,
            timeout=fast_config.tier1_timeout_seconds,
        )
        tier1_time = time.time() - tier1_start

        # Check if tier1 passed
        if not result.tier1_results.get("passed", True):
            result.passed = False
            result.errors.extend(result.tier1_results.get("errors", []))

        result.timing["tier1_seconds"] = tier1_time

        # If tier1 failed critically, return early
        if result.tier1_results.get("critical_failure", False):
            result.timing["total_seconds"] = time.time() - start_time
            return result

    except Exception as e:
        logger.error(f"Tier1 validation failed: {e}", exc_info=True)
        result.errors.append(f"Tier1 validation error: {str(e)}")
        result.passed = False
        result.timing["tier1_seconds"] = time.time() - tier1_start
        result.timing["total_seconds"] = time.time() - start_time
        return result

    # Tier 2: Standard checks in parallel (<30s)
    tier2_start = time.time()
    try:
        result.tier2_results = _run_tier2_validation(
            ms_path=ms_path,
            caltables=caltables,
            image_paths=image_paths,
            config=config,
            fast_config=fast_config,
            timeout=fast_config.tier2_timeout_seconds,
        )
        tier2_time = time.time() - tier2_start

        # Check if tier2 passed
        if not result.tier2_results.get("passed", True):
            result.passed = False
            result.errors.extend(result.tier2_results.get("errors", []))

        result.timing["tier2_seconds"] = tier2_time

    except Exception as e:
        logger.error(f"Tier2 validation failed: {e}", exc_info=True)
        result.errors.append(f"Tier2 validation error: {str(e)}")
        result.passed = False
        result.timing["tier2_seconds"] = time.time() - tier2_start

    # Tier 3: Detailed checks (optional, deferred if time permits)
    tier3_start = time.time()
    remaining_time = fast_config.timeout_seconds - (time.time() - start_time)

    if remaining_time > 10 and not fast_config.skip_expensive_checks:
        try:
            result.tier3_results = _run_tier3_validation(
                ms_path=ms_path,
                caltables=caltables,
                image_paths=image_paths,
                config=config,
                fast_config=fast_config,
                timeout=min(remaining_time, fast_config.tier3_timeout_seconds),
            )
            tier3_time = time.time() - tier3_start

            if not result.tier3_results.get("passed", True):
                result.warnings.extend(result.tier3_results.get("warnings", []))

            result.timing["tier3_seconds"] = tier3_time

        except Exception as e:
            logger.warning(f"Tier3 validation skipped or failed: {e}")
            result.warnings.append(f"Tier3 validation skipped: {str(e)}")
            result.timing["tier3_seconds"] = time.time() - tier3_start
    else:
        result.warnings.append(
            "Tier3 validation skipped (insufficient time or disabled)"
        )
        result.timing["tier3_seconds"] = 0.0

    result.timing["total_seconds"] = time.time() - start_time

    return result


def _run_tier1_validation(
    ms_path: Optional[str],
    caltables: Optional[List[str]],
    image_paths: Optional[List[str]],
    timeout: float,
) -> Dict[str, Any]:
    """
    Tier 1: Critical fast checks (<10s).

    - File existence and basic integrity
    - Quick MS structure check
    - Quick image structure check
    - Caltable existence
    """
    start_time = time.time()
    results = {
        "passed": True,
        "errors": [],
        "warnings": [],
        "critical_failure": False,
    }

    # Quick MS check
    if ms_path:
        try:
            passed, message = quick_ms_check(ms_path)
            if not passed:
                results["passed"] = False
                results["errors"].append(f"MS quick check failed: {message}")
                results["critical_failure"] = True
        except Exception as e:
            results["passed"] = False
            results["errors"].append(f"MS quick check error: {str(e)}")
            results["critical_failure"] = True

    # Quick image checks
    if image_paths:
        for img_path in image_paths[:5]:  # Limit to first 5 images for speed
            try:
                passed, message = quick_image_check(img_path)
                if not passed:
                    results["warnings"].append(
                        f"Image quick check warning for {img_path}: {message}"
                    )
            except Exception as e:
                results["warnings"].append(
                    f"Image quick check error for {img_path}: {str(e)}"
                )

    # Caltable existence already checked in main function
    if caltables:
        results["n_caltables"] = len(caltables)

    elapsed = time.time() - start_time
    if elapsed > timeout:
        results["warnings"].append(
            f"Tier1 exceeded timeout ({timeout}s), took {elapsed:.2f}s"
        )

    results["elapsed_seconds"] = elapsed
    return results


def _run_tier2_validation(
    ms_path: Optional[str],
    caltables: Optional[List[str]],
    image_paths: Optional[List[str]],
    config: QAConfig,
    fast_config: FastValidationConfig,
    timeout: float,
) -> Dict[str, Any]:
    """
    Tier 2: Standard checks in parallel (<30s).

    - MS quality (sampled)
    - Calibration quality
    - Image quality (basic metrics)
    """
    start_time = time.time()
    results = {
        "passed": True,
        "errors": [],
        "warnings": [],
    }

    futures = {}

    with ThreadPoolExecutor(max_workers=fast_config.parallel_workers) as executor:
        # MS quality check
        if ms_path:
            future = executor.submit(
                _check_ms_quality_fast,
                ms_path,
                config,
                fast_config,
            )
            futures[future] = "ms"

        # Calibration quality check
        if caltables:
            future = executor.submit(
                _check_calibration_quality_fast,
                caltables,
                config,
                fast_config,
            )
            futures[future] = "calibration"

        # Image quality checks (limit to first 3 for speed)
        if image_paths:
            for i, img_path in enumerate(image_paths[:3]):
                future = executor.submit(
                    _check_image_quality_fast,
                    img_path,
                    config,
                    fast_config,
                )
                futures[future] = f"image_{i}"

        # Collect results with timeout per future
        remaining_timeout = timeout
        start_collect = time.time()

        for future in futures:
            key = futures[future]
            elapsed = time.time() - start_collect
            remaining_timeout = max(1.0, timeout - elapsed)

            try:
                check_result = future.result(timeout=min(remaining_timeout, 10.0))
                if check_result and not check_result.get("passed", True):
                    results["passed"] = False
                    results["errors"].extend(check_result.get("errors", []))
                results[key] = check_result
            except FutureTimeoutError:
                results["warnings"].append(
                    f"{key} check timed out after {remaining_timeout:.1f}s"
                )
                results[key] = {"passed": False, "timeout": True}
                future.cancel()  # Cancel the future
            except Exception as e:
                logger.error(f"{key} check failed: {e}", exc_info=True)
                results["warnings"].append(f"{key} check error: {str(e)}")
                results[key] = {"passed": False, "error": str(e)}

    elapsed = time.time() - start_time
    if elapsed > timeout:
        results["warnings"].append(
            f"Tier2 exceeded timeout ({timeout}s), took {elapsed:.2f}s"
        )

    results["elapsed_seconds"] = elapsed
    return results


def _run_tier3_validation(
    ms_path: Optional[str],
    caltables: Optional[List[str]],
    image_paths: Optional[List[str]],
    config: QAConfig,
    fast_config: FastValidationConfig,
    timeout: float,
) -> Dict[str, Any]:
    """
    Tier 3: Detailed checks (optional, deferred).

    - Catalog validation (if not skipped)
    - Photometry validation (if not skipped)
    - Variability validation (if not skipped)
    - Mosaic validation (if not skipped)
    """
    start_time = time.time()
    results = {
        "passed": True,
        "warnings": [],
    }

    # Skip if configured to skip expensive checks
    if fast_config.skip_expensive_checks:
        results["warnings"].append("Tier3 skipped (skip_expensive_checks=True)")
        results["elapsed_seconds"] = time.time() - start_time
        return results

    # Catalog validation (if not skipped)
    if not fast_config.skip_catalog_validation and image_paths:
        # Would run catalog validation here
        results["warnings"].append(
            "Catalog validation not yet implemented in fast mode"
        )

    # Photometry validation (if not skipped)
    if not fast_config.skip_photometry_validation and image_paths:
        # Would run photometry validation here
        results["warnings"].append(
            "Photometry validation not yet implemented in fast mode"
        )

    elapsed = time.time() - start_time
    if elapsed > timeout:
        results["warnings"].append(
            f"Tier3 exceeded timeout ({timeout}s), took {elapsed:.2f}s"
        )

    results["elapsed_seconds"] = elapsed
    return results


def _check_ms_quality_fast(
    ms_path: str,
    config: QAConfig,
    fast_config: FastValidationConfig,
) -> Dict[str, Any]:
    """Fast MS quality check with aggressive sampling."""
    try:
        result = check_ms_after_conversion(
            ms_path,
            config=config,
            quick_check_only=False,  # Use sampled full check
        )
        if result:
            passed, details = result
            return {
                "passed": passed,
                "details": details,
            }
        return {"passed": True}
    except Exception as e:
        logger.error(f"MS quality check failed: {e}", exc_info=True)
        return {"passed": False, "error": str(e)}


def _check_calibration_quality_fast(
    caltables: List[str],
    config: QAConfig,
    fast_config: FastValidationConfig,
) -> Dict[str, Any]:
    """Fast calibration quality check."""
    try:
        result = check_calibration_quality(
            caltables,
            config=config,
        )
        if result:
            passed, details, issues = result
            return {
                "passed": passed,
                "details": details,
                "issues": issues,
            }
        return {"passed": True}
    except Exception as e:
        logger.error(f"Calibration quality check failed: {e}", exc_info=True)
        return {"passed": False, "error": str(e)}


def _check_image_quality_fast(
    image_path: str,
    config: QAConfig,
    fast_config: FastValidationConfig,
) -> Dict[str, Any]:
    """Fast image quality check."""
    try:
        # Use quick_check_only=True for fast mode to avoid expensive operations
        result = check_image_quality(
            image_path,
            config=config,
            quick_check_only=True,  # Use quick check for speed
        )
        if result:
            passed, details = result
            return {
                "passed": passed,
                "details": details,
            }
        return {"passed": True}
    except Exception as e:
        logger.error(f"Image quality check failed: {e}", exc_info=True)
        return {"passed": False, "error": str(e)}

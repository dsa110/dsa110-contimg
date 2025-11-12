"""
Variability and ESE (Extreme Scattering Event) validation module.

Validates variability detection, ESE identification, and variability statistics.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from dsa110_contimg.qa.base import (
    ValidationContext,
    ValidationError,
    ValidationInputError,
    ValidationResult,
)
from dsa110_contimg.qa.config import VariabilityConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass
class VariabilityValidationResult(ValidationResult):
    """Result of variability validation."""
    
    # Variability metrics
    n_sources_validated: int = 0
    n_ese_candidates: int = 0
    n_false_positives: int = 0
    
    # Statistics validation
    mean_chi_squared: float = 0.0
    median_chi_squared: float = 0.0
    max_chi_squared: float = 0.0
    
    # Variability fraction
    mean_variability_fraction: float = 0.0
    
    # False positive rate
    false_positive_rate: float = 0.0
    
    # Per-source results
    source_results: List[Dict[str, any]] = field(default_factory=list)  # type: ignore
    
    def __post_init__(self):
        """Initialize defaults."""
        super().__post_init__()
        if self.source_results is None:
            self.source_results = []


def validate_variability_detection(
    source_id: str,
    photometry_history: List[Dict],
    variability_stats: Optional[Dict] = None,
    config: Optional[VariabilityConfig] = None,
) -> VariabilityValidationResult:
    """Validate variability detection for a single source.
    
    Args:
        source_id: Source identifier
        photometry_history: List of photometry measurements with 'flux', 'flux_err', 'mjd' keys
        variability_stats: Optional pre-calculated variability statistics
        config: Variability validation configuration
        
    Returns:
        VariabilityValidationResult with validation status
    """
    if config is None:
        config = get_default_config().variability
    
    # Validate inputs
    if len(photometry_history) < config.min_observations:
        return VariabilityValidationResult(
            passed=False,
            message=f"Insufficient observations: {len(photometry_history)} < {config.min_observations}",
            details={"n_observations": len(photometry_history), "min_required": config.min_observations},
            errors=[f"Need at least {config.min_observations} observations for variability validation"],
        )
    
    try:
        # Calculate variability statistics if not provided
        if variability_stats is None:
            variability_stats = _calculate_variability_stats(photometry_history)
        
        chi_squared = variability_stats.get("chi_squared", 0.0)
        variability_fraction = variability_stats.get("variability_fraction", 0.0)
        is_ese_candidate = variability_stats.get("is_ese_candidate", False)
        
        # Validate chi-squared calculation
        expected_chi_squared = _calculate_expected_chi_squared(photometry_history)
        chi_squared_error = abs(chi_squared - expected_chi_squared) / expected_chi_squared if expected_chi_squared > 0 else 0.0
        
        # Determine if variability is real (not systematic error)
        is_real_variability = (
            chi_squared >= config.min_chi_squared and
            variability_fraction >= config.min_variability_fraction and
            chi_squared_error < 0.1  # Chi-squared calculated correctly
        )
        
        # Check if ESE candidate is valid
        ese_valid = False
        if is_ese_candidate:
            ese_valid = (
                chi_squared >= config.min_chi_squared and
                variability_fraction >= config.min_variability_fraction
            )
        
        passed = is_real_variability or (is_ese_candidate and ese_valid)
        
        result = VariabilityValidationResult(
            passed=passed,
            message=f"Variability validation for {source_id}: chi²={chi_squared:.2f}, var_frac={variability_fraction:.3f}",
            details={
                "source_id": source_id,
                "chi_squared": chi_squared,
                "variability_fraction": variability_fraction,
                "is_ese_candidate": is_ese_candidate,
                "ese_valid": ese_valid,
                "is_real_variability": is_real_variability,
            },
            metrics={
                "chi_squared": chi_squared,
                "variability_fraction": variability_fraction,
                "chi_squared_error": chi_squared_error,
            },
            n_sources_validated=1,
            n_ese_candidates=1 if is_ese_candidate else 0,
            mean_chi_squared=chi_squared,
            max_chi_squared=chi_squared,
            mean_variability_fraction=variability_fraction,
            source_results=[{
                "source_id": source_id,
                "chi_squared": chi_squared,
                "variability_fraction": variability_fraction,
                "is_ese_candidate": is_ese_candidate,
                "passed": passed,
            }],
        )
        
        if not passed:
            result.add_warning(f"Variability detection may be spurious for {source_id}")
        
        return result
        
    except Exception as e:
        logger.exception(f"Variability validation failed for {source_id}")
        raise ValidationError(f"Variability validation failed: {e}") from e


def validate_ese_detection(
    ese_candidates: List[Dict],
    photometry_histories: Dict[str, List[Dict]],
    config: Optional[VariabilityConfig] = None,
) -> VariabilityValidationResult:
    """Validate ESE (Extreme Scattering Event) detection.
    
    Validates that ESE candidates are correctly identified and not false positives.
    
    Args:
        ese_candidates: List of ESE candidate dictionaries with 'source_id', 'chi_squared', etc.
        photometry_histories: Dictionary mapping source_id to photometry history
        config: Variability validation configuration
        
    Returns:
        VariabilityValidationResult with ESE validation status
    """
    if config is None:
        config = get_default_config().variability
    
    validated_candidates = []
    false_positives = []
    
    for candidate in ese_candidates:
        source_id = candidate.get("source_id")
        if source_id not in photometry_histories:
            false_positives.append(candidate)
            continue
        
        # Validate this candidate
        result = validate_variability_detection(
            source_id=source_id,
            photometry_history=photometry_histories[source_id],
            variability_stats=candidate,
            config=config,
        )
        
        if result.passed:
            validated_candidates.append(candidate)
        else:
            false_positives.append(candidate)
    
    n_validated = len(ese_candidates)
    n_valid = len(validated_candidates)
    n_false_positives = len(false_positives)
    
    false_positive_rate = n_false_positives / n_validated if n_validated > 0 else 0.0
    
    # Calculate aggregate statistics
    chi_squared_values = [c.get("chi_squared", 0.0) for c in ese_candidates]
    variability_fractions = [c.get("variability_fraction", 0.0) for c in ese_candidates]
    
    mean_chi_squared = np.mean(chi_squared_values) if chi_squared_values else 0.0
    median_chi_squared = np.median(chi_squared_values) if chi_squared_values else 0.0
    max_chi_squared = np.max(chi_squared_values) if chi_squared_values else 0.0
    mean_variability_fraction = np.mean(variability_fractions) if variability_fractions else 0.0
    
    # Determine overall pass status
    passed = false_positive_rate <= config.max_false_positive_rate
    
    result = VariabilityValidationResult(
        passed=passed,
        message=f"ESE validation: {n_valid}/{n_validated} valid, FPR={false_positive_rate:.3f}",
        details={
            "n_validated": n_validated,
            "n_valid": n_valid,
            "n_false_positives": n_false_positives,
            "false_positive_rate": false_positive_rate,
        },
        metrics={
            "mean_chi_squared": mean_chi_squared,
            "median_chi_squared": median_chi_squared,
            "max_chi_squared": max_chi_squared,
            "mean_variability_fraction": mean_variability_fraction,
            "false_positive_rate": false_positive_rate,
        },
        n_sources_validated=n_validated,
        n_ese_candidates=n_valid,
        n_false_positives=n_false_positives,
        mean_chi_squared=mean_chi_squared,
        median_chi_squared=median_chi_squared,
        max_chi_squared=max_chi_squared,
        mean_variability_fraction=mean_variability_fraction,
        false_positive_rate=false_positive_rate,
        source_results=[
            {
                "source_id": c.get("source_id"),
                "chi_squared": c.get("chi_squared", 0.0),
                "variability_fraction": c.get("variability_fraction", 0.0),
                "is_valid": c in validated_candidates,
            }
            for c in ese_candidates
        ],
    )
    
    if false_positive_rate > config.max_false_positive_rate:
        result.add_error(
            f"False positive rate {false_positive_rate:.3f} exceeds threshold {config.max_false_positive_rate:.3f}"
        )
    
    if n_false_positives > 0:
        result.add_warning(f"{n_false_positives} false positive ESE detections")
    
    return result


def validate_variability_statistics(
    variability_stats_list: List[Dict],
    config: Optional[VariabilityConfig] = None,
) -> VariabilityValidationResult:
    """Validate variability statistics are calculated correctly.
    
    Args:
        variability_stats_list: List of variability statistics dictionaries
        config: Variability validation configuration
        
    Returns:
        VariabilityValidationResult with statistics validation status
    """
    if config is None:
        config = get_default_config().variability
    
    # Check that all required fields are present
    required_fields = ["chi_squared", "variability_fraction"]
    missing_fields = []
    
    for stats in variability_stats_list:
        for field in required_fields:
            if field not in stats:
                missing_fields.append(field)
    
    if missing_fields:
        return VariabilityValidationResult(
            passed=False,
            message=f"Missing required fields: {set(missing_fields)}",
            details={"missing_fields": list(set(missing_fields))},
            errors=[f"Statistics missing required fields: {set(missing_fields)}"],
        )
    
    # Validate statistics are reasonable
    chi_squared_values = [s.get("chi_squared", 0.0) for s in variability_stats_list]
    variability_fractions = [s.get("variability_fraction", 0.0) for s in variability_stats_list]
    
    # Check for negative or invalid values
    invalid_chi_squared = [v for v in chi_squared_values if v < 0]
    invalid_variability = [v for v in variability_fractions if v < 0 or v > 1]
    
    passed = len(invalid_chi_squared) == 0 and len(invalid_variability) == 0
    
    result = VariabilityValidationResult(
        passed=passed,
        message=f"Variability statistics validation: {len(variability_stats_list)} sources checked",
        details={
            "n_sources": len(variability_stats_list),
            "n_invalid_chi_squared": len(invalid_chi_squared),
            "n_invalid_variability": len(invalid_variability),
        },
        n_sources_validated=len(variability_stats_list),
    )
    
    if invalid_chi_squared:
        result.add_error(f"Found {len(invalid_chi_squared)} invalid chi-squared values")
    
    if invalid_variability:
        result.add_error(f"Found {len(invalid_variability)} invalid variability fractions")
    
    return result


def _calculate_variability_stats(photometry_history: List[Dict]) -> Dict:
    """Calculate variability statistics from photometry history.
    
    Args:
        photometry_history: List of photometry measurements
        
    Returns:
        Dictionary with 'chi_squared', 'variability_fraction', 'is_ese_candidate'
    """
    fluxes = np.array([m["flux"] for m in photometry_history])
    flux_errors = np.array([m.get("flux_err", 0.0) for m in photometry_history])
    
    # Calculate mean flux
    mean_flux = np.mean(fluxes)
    
    # Calculate chi-squared
    if np.any(flux_errors > 0):
        chi_squared = np.sum(((fluxes - mean_flux) / flux_errors) ** 2)
    else:
        # If no errors, use standard deviation
        chi_squared = len(fluxes) * (np.std(fluxes) / mean_flux) ** 2 if mean_flux > 0 else 0.0
    
    # Calculate variability fraction
    if mean_flux > 0:
        variability_fraction = np.std(fluxes) / mean_flux
    else:
        variability_fraction = 0.0
    
    # Determine if ESE candidate (5-sigma threshold)
    is_ese_candidate = chi_squared >= 25.0  # 5-sigma
    
    return {
        "chi_squared": chi_squared,
        "variability_fraction": variability_fraction,
        "is_ese_candidate": is_ese_candidate,
        "mean_flux": mean_flux,
        "std_flux": np.std(fluxes),
    }


def _calculate_expected_chi_squared(photometry_history: List[Dict]) -> float:
    """Calculate expected chi-squared value.
    
    This is used to validate that chi-squared is calculated correctly.
    
    Args:
        photometry_history: List of photometry measurements
        
    Returns:
        Expected chi-squared value
    """
    fluxes = np.array([m["flux"] for m in photometry_history])
    flux_errors = np.array([m.get("flux_err", 0.0) for m in photometry_history])
    
    mean_flux = np.mean(fluxes)
    
    if np.any(flux_errors > 0):
        return np.sum(((fluxes - mean_flux) / flux_errors) ** 2)
    else:
        return len(fluxes) * (np.std(fluxes) / mean_flux) ** 2 if mean_flux > 0 else 0.0


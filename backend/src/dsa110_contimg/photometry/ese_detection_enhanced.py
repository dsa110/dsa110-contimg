"""Enhanced ESE detection with observability, resilience, and caching.

This module demonstrates integration of all cost-free improvements
into the ESE detection component.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

# Import original function
from dsa110_contimg.photometry.ese_detection import detect_ese_candidates as _detect_ese_candidates
from dsa110_contimg.pipeline.caching import (
    get_cached_variability_stats,
)
from dsa110_contimg.pipeline.circuit_breaker import ese_detection_circuit_breaker
from dsa110_contimg.pipeline.dead_letter_queue import get_dlq
from dsa110_contimg.pipeline.event_bus import publish_ese_candidate
from dsa110_contimg.pipeline.metrics import record_ese_detection
from dsa110_contimg.pipeline.retry_enhanced import retry_ese_detection
from dsa110_contimg.pipeline.structured_logging import (
    get_logger,
    log_ese_detection,
    set_correlation_id,
)

logger = get_logger(__name__)


@retry_ese_detection
def detect_ese_candidates_enhanced(
    products_db: Path,
    min_sigma: float = 5.0,
    source_id: Optional[str] = None,
    recompute: bool = False,
    correlation_id: Optional[str] = None,
) -> List[dict]:
    """Enhanced ESE detection with observability and resilience.

    Features:
    - Circuit breaker protection
    - Retry logic
    - Metrics recording
    - Structured logging
    - Event publishing
    - Caching
    - Dead letter queue for failures

    Args:
        products_db: Path to products database
        min_sigma: Minimum sigma threshold
        source_id: Optional specific source ID
        recompute: Recompute variability stats
        correlation_id: Correlation ID for tracing

    Returns:
        List of ESE candidate dictionaries
    """
    # Set correlation ID for tracing
    if correlation_id:
        set_correlation_id(correlation_id)

    start_time = time.time()

    try:
        # Use circuit breaker to protect against cascading failures
        def _detect():
            return _detect_ese_candidates(
                products_db=products_db,
                min_sigma=min_sigma,
                source_id=source_id,
                recompute=recompute,
            )

        # Execute with circuit breaker
        candidates = ese_detection_circuit_breaker.call(_detect)

        duration = time.time() - start_time

        # Record metrics
        record_ese_detection(
            duration=duration,
            candidates=len(candidates),
            source=source_id or "all",
            min_sigma=min_sigma,
        )

        # Structured logging
        log_ese_detection(
            logger=logger,
            source_id=source_id,
            candidates_found=len(candidates),
            duration_seconds=duration,
            min_sigma=min_sigma,
        )

        # Publish events for high-significance candidates
        for candidate in candidates:
            significance = candidate.get("significance", 0.0)
            if significance >= min_sigma:
                publish_ese_candidate(
                    source_id=candidate.get("source_id", "unknown"),
                    significance=significance,
                    sigma_deviation=candidate.get("sigma_deviation", 0.0),
                    n_observations=candidate.get("n_obs", 0),
                    correlation_id=correlation_id,
                )

        return candidates

    except Exception as e:
        duration = time.time() - start_time

        # Record failure metrics
        record_ese_detection(
            duration=duration,
            candidates=0,
            source=source_id or "all",
            min_sigma=min_sigma,
        )

        # Log error
        logger.error(
            "ese_detection_failed",
            component="ese_detection",
            error_type=type(e).__name__,
            error_message=str(e),
            source_id=source_id,
            min_sigma=min_sigma,
        )

        # Add to dead letter queue
        dlq = get_dlq()
        dlq.add(
            component="ese_detection",
            operation="detect_candidates",
            error=e,
            context={
                "products_db": str(products_db),
                "min_sigma": min_sigma,
                "source_id": source_id,
                "recompute": recompute,
            },
        )

        raise


def detect_ese_with_caching(
    products_db: Path, source_id: str, min_sigma: float = 5.0
) -> Optional[dict]:
    """Detect ESE for a source with caching.

    Uses cached variability stats if available and recent.

    Args:
        products_db: Path to products database
        source_id: Source ID to check
        min_sigma: Minimum sigma threshold

    Returns:
        ESE candidate dict if detected, None otherwise
    """
    # Try to get cached variability stats
    cached_stats = get_cached_variability_stats(source_id)

    if cached_stats:
        # Use cached stats if sigma deviation meets threshold
        sigma_dev = cached_stats.get("sigma_deviation", 0.0)
        if sigma_dev >= min_sigma:
            return {
                "source_id": source_id,
                "significance": sigma_dev,
                "sigma_deviation": sigma_dev,
                "cached": True,
            }

    # Fall back to full detection
    candidates = detect_ese_candidates_enhanced(
        products_db=products_db,
        min_sigma=min_sigma,
        source_id=source_id,
        recompute=False,
    )

    if candidates:
        candidate = candidates[0]
        # Cache the variability stats for future use
        # (This would need to fetch from database)
        return candidate

    return None

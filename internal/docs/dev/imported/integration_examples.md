# Integration Examples: Cost-Free Improvements

This document provides examples of how to integrate the cost-free improvements
into existing pipeline components.

## Table of Contents

1. [ESE Detection Integration](#ese-detection-integration)
2. [Photometry Integration](#photometry-integration)
3. [Calibration Integration](#calibration-integration)
4. [API Integration](#api-integration)
5. [Event Handlers](#event-handlers)

---

## ESE Detection Integration

### Basic Integration

```python
from dsa110_contimg.pipeline.metrics import record_ese_detection
from dsa110_contimg.pipeline.structured_logging import get_logger, log_ese_detection
from dsa110_contimg.pipeline.circuit_breaker import ese_detection_circuit_breaker
from dsa110_contimg.pipeline.retry_enhanced import retry_ese_detection
from dsa110_contimg.pipeline.event_bus import publish_ese_candidate

logger = get_logger(__name__)

@retry_ese_detection
def detect_ese_candidates(products_db, min_sigma=5.0):
    """ESE detection with all improvements."""
    start_time = time.time()

    try:
        # Use circuit breaker
        candidates = ese_detection_circuit_breaker.call(
            lambda: _detect_ese_candidates(products_db, min_sigma)
        )

        duration = time.time() - start_time

        # Record metrics
        record_ese_detection(duration, len(candidates), min_sigma=min_sigma)

        # Structured logging
        log_ese_detection(logger, None, len(candidates), duration, min_sigma)

        # Publish events
        for candidate in candidates:
            publish_ese_candidate(
                source_id=candidate['source_id'],
                significance=candidate['significance'],
                sigma_deviation=candidate['sigma_deviation'],
                n_observations=candidate['n_obs']
            )

        return candidates
    except Exception as e:
        # Error handling with DLQ
        dlq = get_dlq()
        dlq.add("ese_detection", "detect_candidates", e, {
            "min_sigma": min_sigma
        })
        raise
```

---

## Photometry Integration

### Measurement with Observability

```python
from dsa110_contimg.pipeline.metrics import record_photometry_measurement
from dsa110_contimg.pipeline.structured_logging import log_photometry_measurement
from dsa110_contimg.pipeline.event_bus import publish_photometry_measurement
from dsa110_contimg.pipeline.caching import cache_reference_sources_for_field

def measure_photometry_with_observability(fits_path, ra_deg, dec_deg, method="forced"):
    """Photometry measurement with full observability."""
    start_time = time.time()

    try:
        # Check cache for reference sources
        cached_refs = get_cached_reference_sources(ra_deg, dec_deg)

        # Perform measurement
        result = measure_forced_peak(fits_path, ra_deg, dec_deg)

        duration = time.time() - start_time

        # Record metrics
        record_photometry_measurement(duration, method, "success")

        # Structured logging
        log_photometry_measurement(
            logger, method, fits_path, ra_deg, dec_deg, duration, "success"
        )

        # Publish event
        publish_photometry_measurement(
            fits_path=fits_path,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            flux_jy=result.peak_jyb,
            method=method
        )

        return result
    except Exception as e:
        duration = time.time() - start_time
        record_photometry_measurement(duration, method, "failure")
        raise
```

---

## Calibration Integration

### Calibration Solve with Resilience

```python
from dsa110_contimg.pipeline.metrics import record_calibration_solve
from dsa110_contimg.pipeline.circuit_breaker import calibration_solve_circuit_breaker
from dsa110_contimg.pipeline.retry_enhanced import retry_calibration_solve
from dsa110_contimg.pipeline.event_bus import publish_calibration_solved

@retry_calibration_solve
def solve_calibration_with_resilience(ms_path, calibrator_name):
    """Calibration solve with resilience patterns."""
    start_time = time.time()

    try:
        # Use circuit breaker
        def _solve():
            return solve_calibration_for_ms(ms_path, do_k=False)

        success, error_msg = calibration_solve_circuit_breaker.call(_solve)

        duration = time.time() - start_time
        status = "success" if success else "failure"

        # Record metrics
        record_calibration_solve(
            duration, calibrator_name, "BP", status
        )

        if success:
            # Publish event
            publish_calibration_solved(
                ms_path=ms_path,
                calibrator_name=calibrator_name,
                calibration_type="BP"
            )

        return success, error_msg
    except Exception as e:
        # Add to DLQ
        dlq = get_dlq()
        dlq.add("calibration", "solve", e, {
            "ms_path": ms_path,
            "calibrator_name": calibrator_name
        })
        raise
```

---

## API Integration

### FastAPI Route with Health Checks

```python
from fastapi import APIRouter, Request
from dsa110_contimg.api.health import router as health_router
from dsa110_contimg.pipeline.structured_logging import set_correlation_id, get_logger

router = APIRouter()
router.include_router(health_router)

logger = get_logger(__name__)

@router.post("/api/jobs/ese-detect")
def create_ese_detect_job(request: ESEDetectJobCreateRequest):
    """ESE detection job with observability."""
    # Set correlation ID
    correlation_id = set_correlation_id()

    logger.info(
        "ese_detection_job_created",
        job_type="ese-detect",
        min_sigma=request.params.min_sigma,
        correlation_id=correlation_id
    )

    # Create job with correlation ID
    # ... job creation logic ...

    return {"job_id": job_id, "correlation_id": correlation_id}
```

---

## Event Handlers

### Subscribe to Events

```python
from dsa110_contimg.pipeline.event_bus import (
    get_event_bus,
    EventType,
    PipelineEvent
)

def handle_ese_candidate(event: PipelineEvent):
    """Handle ESE candidate detected event."""
    if event.event_type == EventType.ESE_CANDIDATE_DETECTED:
        # Send alert, update dashboard, etc.
        print(f"ESE candidate detected: {event.source_id}")

# Subscribe to events
event_bus = get_event_bus()
event_bus.subscribe(EventType.ESE_CANDIDATE_DETECTED, handle_ese_candidate)
```

---

## Metrics Endpoint

### Expose Prometheus Metrics

```python
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

## Configuration

### Environment Variables

```bash
# Redis (optional)
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Correlation ID (auto-generated if not set)
export CORRELATION_ID=optional-uuid

# Logging
export LOG_LEVEL=INFO
export STRUCTURED_LOGGING=true
```

---

## Next Steps

1. Integrate metrics into all components
2. Add structured logging throughout
3. Implement circuit breakers for critical paths
4. Set up event handlers for notifications
5. Configure Prometheus scraping
6. Set up Grafana dashboards

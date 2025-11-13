"""Pipeline orchestration and infrastructure modules."""

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.orchestrator import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.resilience import RetryPolicy, RetryStrategy
from dsa110_contimg.pipeline.stages import PipelineStage, StageStatus
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

# New observability and resilience modules
from dsa110_contimg.pipeline.metrics import (
    record_ese_detection,
    record_calibration_solve,
    record_photometry_measurement,
    record_pipeline_stage,
)
from dsa110_contimg.pipeline.structured_logging import (
    get_logger,
    configure_structured_logging,
    set_correlation_id,
    get_correlation_id,
    log_ese_detection,
    log_calibration_solve,
    log_photometry_measurement,
    log_pipeline_stage,
    log_error,
)
from dsa110_contimg.pipeline.circuit_breaker import (
    circuit_breaker,
    SimpleCircuitBreaker,
    CircuitBreakerOpenError,
    ese_detection_circuit_breaker,
    calibration_solve_circuit_breaker,
    photometry_circuit_breaker,
)
from dsa110_contimg.pipeline.retry_enhanced import (
    retry_with_backoff,
    retry_on_transient_error,
    retry_on_database_error,
    retry_ese_detection,
    retry_calibration_solve,
    retry_photometry,
    retry_database,
)
from dsa110_contimg.pipeline.caching import (
    get_cache_backend,
    cached_with_ttl,
    cache_variability_stats,
    cache_reference_sources,
    cache_calibration_tables,
    cache_catalog_queries,
    cache_variability_stats_for_source,
    get_cached_variability_stats,
    cache_reference_sources_for_field,
    get_cached_reference_sources,
)
from dsa110_contimg.pipeline.event_bus import (
    EventBus,
    EventType,
    PipelineEvent,
    get_event_bus,
    publish_photometry_measurement,
    publish_ese_candidate,
    publish_calibration_solved,
)
from dsa110_contimg.pipeline.dead_letter_queue import (
    DeadLetterQueue,
    DeadLetterQueueItem,
    DLQStatus,
    get_dlq,
)

__all__ = [
    # Core pipeline
    "PipelineConfig",
    "PipelineContext",
    "PipelineOrchestrator",
    "StageDefinition",
    "RetryPolicy",
    "RetryStrategy",
    "PipelineStage",
    "StageStatus",
    "standard_imaging_workflow",
    # Metrics
    "record_ese_detection",
    "record_calibration_solve",
    "record_photometry_measurement",
    "record_pipeline_stage",
    # Structured logging
    "get_logger",
    "configure_structured_logging",
    "set_correlation_id",
    "get_correlation_id",
    "log_ese_detection",
    "log_calibration_solve",
    "log_photometry_measurement",
    "log_pipeline_stage",
    "log_error",
    # Circuit breakers
    "circuit_breaker",
    "SimpleCircuitBreaker",
    "CircuitBreakerOpenError",
    "ese_detection_circuit_breaker",
    "calibration_solve_circuit_breaker",
    "photometry_circuit_breaker",
    # Retry logic
    "retry_with_backoff",
    "retry_on_transient_error",
    "retry_on_database_error",
    "retry_ese_detection",
    "retry_calibration_solve",
    "retry_photometry",
    "retry_database",
    # Caching
    "get_cache_backend",
    "cached_with_ttl",
    "cache_variability_stats",
    "cache_reference_sources",
    "cache_calibration_tables",
    "cache_catalog_queries",
    "cache_variability_stats_for_source",
    "get_cached_variability_stats",
    "cache_reference_sources_for_field",
    "get_cached_reference_sources",
    # Event bus
    "EventBus",
    "EventType",
    "PipelineEvent",
    "get_event_bus",
    "publish_photometry_measurement",
    "publish_ese_candidate",
    "publish_calibration_solved",
    # Dead letter queue
    "DeadLetterQueue",
    "DeadLetterQueueItem",
    "DLQStatus",
    "get_dlq",
]

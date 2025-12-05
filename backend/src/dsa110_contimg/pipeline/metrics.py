"""Prometheus metrics for pipeline observability.

This module provides Prometheus metrics for all pipeline components.
All metrics are cost-free (using prometheus-client, open-source).
"""

from __future__ import annotations

from typing import Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, Info

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Fallback to simple metrics if Prometheus not available
    from collections import defaultdict
    from typing import Dict, List

# ============================================================================
# ESE Detection Metrics
# ============================================================================

if PROMETHEUS_AVAILABLE:
    ese_detection_requests = Counter(
        "ese_detection_requests_total",
        "Total ESE detection requests",
        ["source", "min_sigma"],
    )

    ese_detection_duration = Histogram(
        "ese_detection_duration_seconds",
        "ESE detection execution time",
        ["source"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    )

    ese_candidates_detected = Gauge(
        "ese_candidates_current",
        "Current number of ESE candidates",
        ["significance_tier"],  # 'high' (>7σ), 'medium' (5-7σ), 'low' (<5σ)
    )

    variability_stats_computation_time = Histogram(
        "variability_stats_computation_seconds",
        "Time to compute variability statistics",
        ["source_count"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    )

    # ============================================================================
    # Calibration Metrics
    # ============================================================================

    calibration_solve_attempts = Counter(
        "calibration_solve_attempts_total",
        "Total calibration solve attempts",
        ["calibrator_name", "status"],  # 'success', 'failure', 'skipped'
    )

    calibration_solve_duration = Histogram(
        "calibration_solve_duration_seconds",
        "Calibration solve execution time",
        ["calibrator_name", "calibration_type"],  # 'BP', 'GP', 'K'
        buckets=[10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0],
    )

    calibration_table_age_hours = Gauge(
        "calibration_table_age_hours",
        "Age of calibration tables in hours",
        ["calibrator_name", "table_type"],
    )

    calibration_quality_score = Gauge(
        "calibration_quality_score",
        "Quality score of calibration solution",
        ["calibrator_name", "table_type"],
    )

    # ============================================================================
    # Photometry Metrics
    # ============================================================================

    photometry_measurements_total = Counter(
        "photometry_measurements_total",
        "Total photometry measurements",
        ["method", "status"],  # 'forced', 'aegean', 'adaptive', 'success', 'failure'
    )

    photometry_measurement_duration = Histogram(
        "photometry_measurement_duration_seconds",
        "Photometry measurement execution time",
        ["method"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    )

    photometry_normalization_requests = Counter(
        "photometry_normalization_requests_total",
        "Total normalization requests",
        ["status"],  # 'success', 'no_references', 'error'
    )

    normalization_correction_factor = Histogram(
        "normalization_correction_factor",
        "Distribution of correction factors",
        buckets=[0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2],
    )

    normalization_reference_count = Histogram(
        "normalization_reference_count",
        "Number of reference sources used",
        buckets=[1, 5, 10, 15, 20],
    )

    # ============================================================================
    # Pipeline Stage Metrics
    # ============================================================================

    pipeline_stage_duration = Histogram(
        "pipeline_stage_duration_seconds",
        "Duration of pipeline stages",
        ["stage_name", "status"],  # 'success', 'failure'
        buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0],
    )

    pipeline_stage_attempts = Counter(
        "pipeline_stage_attempts_total",
        "Total pipeline stage attempts",
        ["stage_name", "status"],
    )

    pipeline_throughput = Gauge(
        "pipeline_throughput_items_per_hour", "Pipeline throughput", ["stage_name"]
    )

    # ============================================================================
    # System Metrics
    # ============================================================================

    pipeline_info = Info("pipeline_info", "Pipeline version and configuration information")

else:
    # Fallback simple metrics if Prometheus not available
    class SimpleCounter:
        def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
            self.name = name
            self.description = description
            self.labels = labels or []
            self._counts: Dict[str, int] = defaultdict(int)

        def inc(self, labels: Optional[Dict[str, str]] = None):
            key = str(sorted((labels or {}).items()))
            self._counts[key] += 1

        def get_value(self, labels: Optional[Dict[str, str]] = None) -> int:
            key = str(sorted((labels or {}).items()))
            return self._counts.get(key, 0)

    class SimpleHistogram:
        def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
            self.name = name
            self.description = description
            self.labels = labels or []
            self._values: Dict[str, List[float]] = defaultdict(list)

        def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
            key = str(sorted((labels or {}).items()))
            self._values[key].append(value)

        def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
            key = str(sorted((labels or {}).items()))
            return len(self._values.get(key, []))

    class SimpleGauge:
        def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
            self.name = name
            self.description = description
            self.labels = labels or []
            self._values: Dict[str, float] = {}

        def set(self, value: float, labels: Optional[Dict[str, str]] = None):
            key = str(sorted((labels or {}).items()))
            self._values[key] = value

        def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
            key = str(sorted((labels or {}).items()))
            return self._values.get(key, 0.0)

    # Create fallback metrics
    ese_detection_requests = SimpleCounter(
        "ese_detection_requests_total", "Total ESE detection requests"
    )
    ese_detection_duration = SimpleHistogram(
        "ese_detection_duration_seconds", "ESE detection execution time"
    )
    ese_candidates_detected = SimpleGauge(
        "ese_candidates_current", "Current number of ESE candidates"
    )
    variability_stats_computation_time = SimpleHistogram(
        "variability_stats_computation_seconds",
        "Time to compute variability statistics",
    )
    calibration_solve_attempts = SimpleCounter(
        "calibration_solve_attempts_total", "Total calibration solve attempts"
    )
    calibration_solve_duration = SimpleHistogram(
        "calibration_solve_duration_seconds", "Calibration solve execution time"
    )
    calibration_table_age_hours = SimpleGauge(
        "calibration_table_age_hours", "Age of calibration tables in hours"
    )
    calibration_quality_score = SimpleGauge(
        "calibration_quality_score", "Quality score of calibration solution"
    )
    photometry_measurements_total = SimpleCounter(
        "photometry_measurements_total", "Total photometry measurements"
    )
    photometry_measurement_duration = SimpleHistogram(
        "photometry_measurement_duration_seconds",
        "Photometry measurement execution time",
    )
    photometry_normalization_requests = SimpleCounter(
        "photometry_normalization_requests_total", "Total normalization requests"
    )
    normalization_correction_factor = SimpleHistogram(
        "normalization_correction_factor", "Distribution of correction factors"
    )
    normalization_reference_count = SimpleHistogram(
        "normalization_reference_count", "Number of reference sources used"
    )
    pipeline_stage_duration = SimpleHistogram(
        "pipeline_stage_duration_seconds", "Duration of pipeline stages"
    )
    pipeline_stage_attempts = SimpleCounter(
        "pipeline_stage_attempts_total", "Total pipeline stage attempts"
    )
    pipeline_throughput = SimpleGauge("pipeline_throughput_items_per_hour", "Pipeline throughput")
    pipeline_info = type("Info", (), {"info": lambda self, labels: None})()


def record_ese_detection(
    duration: float, candidates: int, source: str = "all", min_sigma: float = 5.0
):
    """Record ESE detection metrics."""
    if PROMETHEUS_AVAILABLE:
        ese_detection_requests.labels(source=source, min_sigma=str(min_sigma)).inc()
        ese_detection_duration.labels(source=source).observe(duration)

        # Categorize candidates by significance
        if candidates > 0:
            # This would need actual candidate data to categorize properly
            # For now, just record total
            ese_candidates_detected.labels(significance_tier="total").set(candidates)
    else:
        ese_detection_requests.inc({"source": source, "min_sigma": str(min_sigma)})
        ese_detection_duration.observe(duration, {"source": source})
        ese_candidates_detected.set(candidates, {"significance_tier": "total"})


def record_calibration_solve(
    duration: float, calibrator_name: str, calibration_type: str, status: str
):
    """Record calibration solve metrics."""
    if PROMETHEUS_AVAILABLE:
        calibration_solve_attempts.labels(calibrator_name=calibrator_name, status=status).inc()
        if status == "success":
            calibration_solve_duration.labels(
                calibrator_name=calibrator_name, calibration_type=calibration_type
            ).observe(duration)
    else:
        calibration_solve_attempts.inc({"calibrator_name": calibrator_name, "status": status})
        if status == "success":
            calibration_solve_duration.observe(
                duration,
                {
                    "calibrator_name": calibrator_name,
                    "calibration_type": calibration_type,
                },
            )


def record_photometry_measurement(duration: float, method: str, status: str):
    """Record photometry measurement metrics."""
    if PROMETHEUS_AVAILABLE:
        photometry_measurements_total.labels(method=method, status=status).inc()
        if status == "success":
            photometry_measurement_duration.labels(method=method).observe(duration)
    else:
        photometry_measurements_total.inc({"method": method, "status": status})
        if status == "success":
            photometry_measurement_duration.observe(duration, {"method": method})


def record_pipeline_stage(duration: float, stage_name: str, status: str):
    """Record pipeline stage metrics."""
    if PROMETHEUS_AVAILABLE:
        pipeline_stage_duration.labels(stage_name=stage_name, status=status).observe(duration)
        pipeline_stage_attempts.labels(stage_name=stage_name, status=status).inc()
    else:
        pipeline_stage_duration.observe(duration, {"stage_name": stage_name, "status": status})
        pipeline_stage_attempts.inc({"stage_name": stage_name, "status": status})

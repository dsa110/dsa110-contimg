"""
Monitoring module for DSA-110 Continuum Imaging Pipeline.

Provides:
- Service health checking (Docker, systemd, HTTP endpoints)
- Prometheus metrics export
- Alerting with notification support
- Monitoring tasks for ABSURD workflow manager
"""

from .alerting import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertState,
    create_default_alert_rules,
)
from .pipeline_metrics import (
    GPUUtilizationMetrics,
    JobMetrics,
    MemoryMetrics,
    PipelineMetricsCollector,
    PipelineStage,
    ProcessingMode,
    StageContext,
    StageTimingMetrics,
    ThroughputMetrics,
    close_metrics_collector,
    get_metrics_collector,
    record_memory_sample,
    record_stage_timing,
)
from .prometheus_metrics import (
    MetricValue,
    PrometheusExporter,
    collect_all_metrics,
)
from .service_health import (
    DEFAULT_DOCKER_CONTAINERS,
    DEFAULT_HTTP_ENDPOINTS,
    DEFAULT_SYSTEMD_SERVICES,
    ServiceHealthResult,
    ServiceStatus,
    SystemHealthReport,
    check_docker_container,
    check_http_endpoint,
    check_system_health,
    check_systemd_service,
)
from .tasks import (
    DEFAULT_MONITORING_SCHEDULES,
    TASK_FLUX_MONITORING_CHECK,
    TASK_HEALTH_CHECK,
    TASK_SEND_ALERT,
    TASK_VALIDITY_WINDOW_CHECK,
    execute_monitoring_task,
    register_monitoring_tasks,
    setup_monitoring_schedules,
)

__all__ = [
    # Service health
    "ServiceStatus",
    "ServiceHealthResult",
    "SystemHealthReport",
    "check_docker_container",
    "check_systemd_service",
    "check_http_endpoint",
    "check_system_health",
    "DEFAULT_DOCKER_CONTAINERS",
    "DEFAULT_SYSTEMD_SERVICES",
    "DEFAULT_HTTP_ENDPOINTS",
    # Prometheus
    "PrometheusExporter",
    "MetricValue",
    "collect_all_metrics",
    # Alerting
    "AlertSeverity",
    "AlertState",
    "AlertRule",
    "Alert",
    "AlertManager",
    "create_default_alert_rules",
    # Tasks
    "TASK_FLUX_MONITORING_CHECK",
    "TASK_HEALTH_CHECK",
    "TASK_VALIDITY_WINDOW_CHECK",
    "TASK_SEND_ALERT",
    "execute_monitoring_task",
    "register_monitoring_tasks",
    "setup_monitoring_schedules",
    "DEFAULT_MONITORING_SCHEDULES",
    # Pipeline Metrics
    "GPUUtilizationMetrics",
    "JobMetrics",
    "MemoryMetrics",
    "PipelineMetricsCollector",
    "PipelineStage",
    "ProcessingMode",
    "StageContext",
    "StageTimingMetrics",
    "ThroughputMetrics",
    "close_metrics_collector",
    "get_metrics_collector",
    "record_memory_sample",
    "record_stage_timing",
]

"""
Monitoring module for DSA-110 Continuum Imaging Pipeline.

Provides:
- Service health checking (Docker, systemd, HTTP endpoints)
- Prometheus metrics export
- Alerting with notification support
- Monitoring tasks for ABSURD workflow manager
"""

from .service_health import (
    ServiceStatus,
    ServiceHealthResult,
    SystemHealthReport,
    check_docker_container,
    check_systemd_service,
    check_http_endpoint,
    check_system_health,
    DEFAULT_DOCKER_CONTAINERS,
    DEFAULT_SYSTEMD_SERVICES,
    DEFAULT_HTTP_ENDPOINTS,
)

from .prometheus_metrics import (
    PrometheusExporter,
    MetricValue,
    collect_all_metrics,
)

from .alerting import (
    AlertSeverity,
    AlertState,
    AlertRule,
    Alert,
    AlertManager,
    create_default_alert_rules,
)

from .tasks import (
    TASK_FLUX_MONITORING_CHECK,
    TASK_HEALTH_CHECK,
    TASK_VALIDITY_WINDOW_CHECK,
    TASK_SEND_ALERT,
    execute_monitoring_task,
    register_monitoring_tasks,
    setup_monitoring_schedules,
    DEFAULT_MONITORING_SCHEDULES,
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
]

"""
Routes package for DSA-110 Continuum Imaging Pipeline API.

This package contains modular route definitions organized by resource type.
"""

from .absurd import router as absurd_router
from .alert_policies import router as alert_policies_router
from .auth import router as auth_router
from .backup import router as backup_router
from .cache import router as cache_router
from .cal import router as cal_router
from .calibrator_imaging import router as calibrator_imaging_router
from .carta import router as carta_router
from .comments import router as comments_router
from .conversion import router as conversion_router
from .external import router as external_router
from .health import router as health_router
from .images import router as images_router
from .imaging import router as imaging_router
from .jobs import router as jobs_router
from .jupyter import router as jupyter_router
from .logs import router as logs_router
from .metrics_dashboard import router as metrics_dashboard_router
from .ms import router as ms_router
from .performance import router as performance_router
from .pipeline import router as pipeline_router
from .qa import router as qa_router
from .queue import router as queue_router
from .ratings import router as ratings_router
from .retention import router as retention_router
from .saved_queries import router as queries_router
from .services import router as services_router
from .sources import router as sources_router
from .stats import router as stats_router
from .triggers import router as triggers_router
from .vo_export import router as vo_export_router

__all__ = [
    "auth_router",
    "carta_router",
    "conversion_router",
    "images_router",
    "ms_router",
    "sources_router",
    "jobs_router",
    "queue_router",
    "qa_router",
    "cal_router",
    "logs_router",
    "metrics_dashboard_router",
    "stats_router",
    "cache_router",
    "services_router",
    "imaging_router",
    "absurd_router",
    "calibrator_imaging_router",
    "health_router",
    "alert_policies_router",
    "retention_router",
    "performance_router",
    "queries_router",
    "backup_router",
    "triggers_router",
    "jupyter_router",
    "vo_export_router",
    "pipeline_router",
    "ratings_router",
    "comments_router",
    "external_router",
]

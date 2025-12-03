"""
Routes package for DSA-110 Continuum Imaging Pipeline API.

This package contains modular route definitions organized by resource type.
"""

from .auth import router as auth_router
from .images import router as images_router
from .ms import router as ms_router
from .sources import router as sources_router
from .jobs import router as jobs_router
from .queue import router as queue_router
from .qa import router as qa_router
from .cal import router as cal_router
from .logs import router as logs_router
from .stats import router as stats_router
from .cache import router as cache_router
from .services import router as services_router
from .imaging import router as imaging_router
from .absurd import router as absurd_router
from .calibrator_imaging import router as calibrator_imaging_router
from .health import router as health_router
from .performance import router as performance_router

__all__ = [
    "auth_router",
    "images_router",
    "ms_router",
    "sources_router",
    "jobs_router",
    "queue_router",
    "qa_router",
    "cal_router",
    "logs_router",
    "stats_router",
    "cache_router",
    "services_router",
    "imaging_router",
    "absurd_router",
    "calibrator_imaging_router",
    "health_router",
    "performance_router",
]

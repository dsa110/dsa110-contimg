"""
Services package for DSA-110 Continuum Imaging Pipeline API.

Contains business logic separated from route handlers and data access.
"""

from .async_services import (
    AsyncImageService,
    AsyncJobService,
    AsyncMSService,
    AsyncSourceService,
)
from .fits_service import FITSMetadata, FITSParsingService
from .qa_service import QAService
from .stats_service import StatsService

# Aliases for backward compatibility - point sync names to async implementations
ImageService = AsyncImageService
SourceService = AsyncSourceService
JobService = AsyncJobService
MSService = AsyncMSService

__all__ = [
    "ImageService",
    "SourceService",
    "JobService",
    "MSService",
    "StatsService",
    "QAService",
    "FITSParsingService",
    "FITSMetadata",
    "AsyncImageService",
    "AsyncMSService",
    "AsyncSourceService",
    "AsyncJobService",
]

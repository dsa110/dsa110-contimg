"""
Services package for DSA-110 Continuum Imaging Pipeline API.

Contains business logic separated from route handlers and data access.
"""

from .stats_service import StatsService
from .qa_service import QAService
from .fits_service import FITSParsingService, FITSMetadata
from .async_services import (
    AsyncImageService,
    AsyncMSService,
    AsyncSourceService,
    AsyncJobService,
)

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

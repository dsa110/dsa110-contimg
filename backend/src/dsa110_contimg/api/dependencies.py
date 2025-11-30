"""
Dependency injection for FastAPI.

Provides factory functions for injecting repositories and services
into route handlers using FastAPI's Depends() system.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Depends

from .database import get_db_pool, DatabasePool
from .repositories import (
    ImageRepository,
    MSRepository,
    SourceRepository,
    JobRepository,
)
from .async_repositories import (
    AsyncImageRepository,
    AsyncMSRepository,
    AsyncSourceRepository,
    AsyncJobRepository,
)
from .services import (
    ImageService,
    SourceService,
    JobService,
    MSService,
    StatsService,
    QAService,
)


# Repository dependencies

def get_image_repository() -> ImageRepository:
    """Get image repository instance."""
    return ImageRepository()


def get_ms_repository() -> MSRepository:
    """Get MS repository instance."""
    return MSRepository()


def get_source_repository() -> SourceRepository:
    """Get source repository instance."""
    return SourceRepository()


def get_job_repository() -> JobRepository:
    """Get job repository instance."""
    return JobRepository()


# Service dependencies

def get_image_service(
    repo: ImageRepository = Depends(get_image_repository)
) -> ImageService:
    """Get image service with injected repository."""
    return ImageService(repo)


def get_source_service(
    repo: SourceRepository = Depends(get_source_repository)
) -> SourceService:
    """Get source service with injected repository."""
    return SourceService(repo)


def get_job_service(
    repo: JobRepository = Depends(get_job_repository)
) -> JobService:
    """Get job service with injected repository."""
    return JobService(repo)


def get_ms_service(
    repo: MSRepository = Depends(get_ms_repository)
) -> MSService:
    """Get MS service with injected repository."""
    return MSService(repo)


def get_stats_service(
    db_pool: DatabasePool = Depends(get_db_pool)
) -> StatsService:
    """Get stats service with injected database pool."""
    return StatsService(db_pool)


def get_qa_service() -> QAService:
    """Get QA service instance."""
    return QAService()


# Async repository dependencies

def get_async_image_repository() -> AsyncImageRepository:
    """Get async image repository instance."""
    return AsyncImageRepository()


def get_async_ms_repository() -> AsyncMSRepository:
    """Get async MS repository instance."""
    return AsyncMSRepository()


def get_async_source_repository() -> AsyncSourceRepository:
    """Get async source repository instance."""
    return AsyncSourceRepository()


def get_async_job_repository() -> AsyncJobRepository:
    """Get async job repository instance."""
    return AsyncJobRepository()


# Async service dependencies

def get_async_image_service(
    repo: AsyncImageRepository = Depends(get_async_image_repository)
) -> "AsyncImageService":
    """Get async image service with injected repository."""
    from .services.async_services import AsyncImageService
    return AsyncImageService(repo)


def get_async_source_service(
    repo: AsyncSourceRepository = Depends(get_async_source_repository)
) -> "AsyncSourceService":
    """Get async source service with injected repository."""
    from .services.async_services import AsyncSourceService
    return AsyncSourceService(repo)


def get_async_job_service(
    repo: AsyncJobRepository = Depends(get_async_job_repository)
) -> "AsyncJobService":
    """Get async job service with injected repository."""
    from .services.async_services import AsyncJobService
    return AsyncJobService(repo)


def get_async_ms_service(
    repo: AsyncMSRepository = Depends(get_async_ms_repository)
) -> "AsyncMSService":
    """Get async MS service with injected repository."""
    from .services.async_services import AsyncMSService
    return AsyncMSService(repo)

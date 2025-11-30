"""
Dependency injection for FastAPI.

Provides factory functions for injecting repositories and services
into route handlers using FastAPI's Depends() system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from .database import get_db_pool, DatabasePool
from .repositories import (
    AsyncImageRepository,
    AsyncMSRepository,
    AsyncSourceRepository,
    AsyncJobRepository,
)
from .services import (
    StatsService,
    QAService,
)

if TYPE_CHECKING:
    from .services.async_services import (
        AsyncImageService,
        AsyncMSService,
        AsyncSourceService,
        AsyncJobService,
    )


# Repository dependencies

def get_image_repository() -> AsyncImageRepository:
    """Get image repository instance."""
    return AsyncImageRepository()


def get_ms_repository() -> AsyncMSRepository:
    """Get MS repository instance."""
    return AsyncMSRepository()


def get_source_repository() -> AsyncSourceRepository:
    """Get source repository instance."""
    return AsyncSourceRepository()


def get_job_repository() -> AsyncJobRepository:
    """Get job repository instance."""
    return AsyncJobRepository()


# Async aliases for backward compatibility
get_async_image_repository = get_image_repository
get_async_ms_repository = get_ms_repository
get_async_source_repository = get_source_repository
get_async_job_repository = get_job_repository


# Service dependencies

def get_image_service(
    repo: AsyncImageRepository = Depends(get_image_repository)
) -> "AsyncImageService":
    """Get image service with injected repository."""
    from .services.async_services import AsyncImageService
    return AsyncImageService(repo)


def get_source_service(
    repo: AsyncSourceRepository = Depends(get_source_repository)
) -> "AsyncSourceService":
    """Get source service with injected repository."""
    from .services.async_services import AsyncSourceService
    return AsyncSourceService(repo)


def get_job_service(
    repo: AsyncJobRepository = Depends(get_job_repository)
) -> "AsyncJobService":
    """Get job service with injected repository."""
    from .services.async_services import AsyncJobService
    return AsyncJobService(repo)


def get_ms_service(
    repo: AsyncMSRepository = Depends(get_ms_repository)
) -> "AsyncMSService":
    """Get MS service with injected repository."""
    from .services.async_services import AsyncMSService
    return AsyncMSService(repo)


# Async aliases for backward compatibility
get_async_image_service = get_image_service
get_async_source_service = get_source_service
get_async_job_service = get_job_service
get_async_ms_service = get_ms_service


# Other service dependencies

def get_stats_service(
    db_pool: DatabasePool = Depends(get_db_pool)
) -> StatsService:
    """Get stats service with injected database pool."""
    return StatsService(db_pool)


def get_qa_service() -> QAService:
    """Get QA service instance."""
    return QAService()

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


# Async repository dependencies (for future async routes)

def get_async_image_repository(
    db_pool: DatabasePool = Depends(get_db_pool)
) -> AsyncImageRepository:
    """Get async image repository instance."""
    return AsyncImageRepository(db_pool)


def get_async_source_repository(
    db_pool: DatabasePool = Depends(get_db_pool)
) -> AsyncSourceRepository:
    """Get async source repository instance."""
    return AsyncSourceRepository(db_pool)


def get_async_job_repository(
    db_pool: DatabasePool = Depends(get_db_pool)
) -> AsyncJobRepository:
    """Get async job repository instance."""
    return AsyncJobRepository(db_pool)

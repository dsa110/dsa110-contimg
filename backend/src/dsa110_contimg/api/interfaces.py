"""
Repository interfaces using Protocol for structural subtyping.

Defines the contracts that repository implementations must fulfill.
Using Protocol allows for duck-typing and better type checking without
requiring explicit inheritance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Protocol

if TYPE_CHECKING:
    from .repositories import ImageRecord, JobRecord, MSRecord, SourceRecord


# =============================================================================
# Synchronous Repository Protocols
# =============================================================================


class ImageRepositoryProtocol(Protocol):
    """Protocol for synchronous image data access."""

    def get_by_id(self, image_id: str) -> Optional["ImageRecord"]:
        """Get image by ID."""
        ...

    def list_all(self, limit: int = 100, offset: int = 0) -> List["ImageRecord"]:
        """List all images with pagination."""
        ...

    def get_many(self, image_ids: List[str]) -> List["ImageRecord"]:
        """Get multiple images by IDs in a single batch query.

        Args:
            image_ids: List of image IDs to fetch

        Returns:
            List of ImageRecords (may be fewer than requested if some not found)
        """
        ...


class MSRepositoryProtocol(Protocol):
    """Protocol for synchronous measurement set data access."""

    def get_metadata(self, ms_path: str) -> Optional["MSRecord"]:
        """Get metadata for a measurement set."""
        ...

    def get_many(self, ms_paths: List[str]) -> Dict[str, "MSRecord"]:
        """Get multiple MS records by paths in a single batch query.

        Args:
            ms_paths: List of MS paths to fetch

        Returns:
            Dict mapping path to MSRecord
        """
        ...


class SourceRepositoryProtocol(Protocol):
    """Protocol for synchronous source data access."""

    def get_by_id(self, source_id: str) -> Optional["SourceRecord"]:
        """Get source by ID."""
        ...

    def list_all(self, limit: int = 100, offset: int = 0) -> List["SourceRecord"]:
        """List all sources with pagination."""
        ...

    def get_lightcurve(
        self, source_id: str, start_mjd: Optional[float] = None, end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data for a source."""
        ...

    def get_many(self, source_ids: List[str]) -> List["SourceRecord"]:
        """Get multiple sources by IDs in a single batch query.

        Args:
            source_ids: List of source IDs to fetch

        Returns:
            List of SourceRecords
        """
        ...


class JobRepositoryProtocol(Protocol):
    """Protocol for synchronous job data access."""

    def get_by_run_id(self, run_id: str) -> Optional["JobRecord"]:
        """Get job by run ID."""
        ...

    def list_all(self, limit: int = 100, offset: int = 0) -> List["JobRecord"]:
        """List all jobs with pagination."""
        ...

    def get_many(self, run_ids: List[str]) -> List["JobRecord"]:
        """Get multiple jobs by run IDs in a single batch query.

        Args:
            run_ids: List of run IDs to fetch

        Returns:
            List of JobRecords
        """
        ...


# =============================================================================
# Asynchronous Repository Protocols
# =============================================================================


class AsyncImageRepositoryProtocol(Protocol):
    """Protocol for asynchronous image data access."""

    async def get_by_id(self, image_id: str) -> Optional["ImageRecord"]:
        """Get image by ID."""
        ...

    async def list_all(self, limit: int = 100, offset: int = 0) -> List["ImageRecord"]:
        """List all images with pagination."""
        ...

    async def get_many(self, image_ids: List[str]) -> List["ImageRecord"]:
        """Get multiple images by IDs in a single batch query.

        Args:
            image_ids: List of image IDs to fetch

        Returns:
            List of ImageRecords (may be fewer than requested if some not found)
        """
        ...


class AsyncMSRepositoryProtocol(Protocol):
    """Protocol for asynchronous measurement set data access."""

    async def get_metadata(self, ms_path: str) -> Optional["MSRecord"]:
        """Get metadata for a measurement set."""
        ...

    async def get_many(self, ms_paths: List[str]) -> Dict[str, "MSRecord"]:
        """Get multiple MS records by paths in a single batch query.

        Args:
            ms_paths: List of MS paths to fetch

        Returns:
            Dict mapping path to MSRecord
        """
        ...


class AsyncSourceRepositoryProtocol(Protocol):
    """Protocol for asynchronous source data access."""

    async def get_by_id(self, source_id: str) -> Optional["SourceRecord"]:
        """Get source by ID."""
        ...

    async def list_all(self, limit: int = 100, offset: int = 0) -> List["SourceRecord"]:
        """List all sources with pagination."""
        ...

    async def get_lightcurve(
        self, source_id: str, start_mjd: Optional[float] = None, end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data for a source."""
        ...

    async def get_many(self, source_ids: List[str]) -> List["SourceRecord"]:
        """Get multiple sources by IDs in a single batch query.

        Args:
            source_ids: List of source IDs to fetch

        Returns:
            List of SourceRecords
        """
        ...


class AsyncJobRepositoryProtocol(Protocol):
    """Protocol for asynchronous job data access."""

    async def get_by_run_id(self, run_id: str) -> Optional["JobRecord"]:
        """Get job by run ID."""
        ...

    async def list_all(self, limit: int = 100, offset: int = 0) -> List["JobRecord"]:
        """List all jobs with pagination."""
        ...

    async def get_many(self, run_ids: List[str]) -> List["JobRecord"]:
        """Get multiple jobs by run IDs in a single batch query.

        Args:
            run_ids: List of run IDs to fetch

        Returns:
            List of JobRecords
        """
        ...

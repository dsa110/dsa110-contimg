"""
Repository interfaces using Protocol for structural subtyping.

Defines the contracts that repository implementations must fulfill.
Using Protocol allows for duck-typing and better type checking without
requiring explicit inheritance.
"""

from __future__ import annotations

from typing import Optional, List, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .repositories import ImageRecord, MSRecord, SourceRecord, JobRecord


# =============================================================================
# Synchronous Repository Protocols
# =============================================================================

class ImageRepositoryProtocol(Protocol):
    """Protocol for synchronous image data access."""
    
    def get_by_id(self, image_id: str) -> Optional["ImageRecord"]:
        """Get image by ID."""
        ...
    
    def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["ImageRecord"]:
        """List all images with pagination."""
        ...


class MSRepositoryProtocol(Protocol):
    """Protocol for synchronous measurement set data access."""
    
    def get_metadata(self, ms_path: str) -> Optional["MSRecord"]:
        """Get metadata for a measurement set."""
        ...


class SourceRepositoryProtocol(Protocol):
    """Protocol for synchronous source data access."""
    
    def get_by_id(self, source_id: str) -> Optional["SourceRecord"]:
        """Get source by ID."""
        ...
    
    def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["SourceRecord"]:
        """List all sources with pagination."""
        ...
    
    def get_lightcurve(
        self,
        source_id: str,
        start_mjd: Optional[float] = None,
        end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data for a source."""
        ...


class JobRepositoryProtocol(Protocol):
    """Protocol for synchronous job data access."""
    
    def get_by_run_id(self, run_id: str) -> Optional["JobRecord"]:
        """Get job by run ID."""
        ...
    
    def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["JobRecord"]:
        """List all jobs with pagination."""
        ...


# =============================================================================
# Asynchronous Repository Protocols
# =============================================================================

class AsyncImageRepositoryProtocol(Protocol):
    """Protocol for asynchronous image data access."""
    
    async def get_by_id(self, image_id: str) -> Optional["ImageRecord"]:
        """Get image by ID."""
        ...
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["ImageRecord"]:
        """List all images with pagination."""
        ...


class AsyncMSRepositoryProtocol(Protocol):
    """Protocol for asynchronous measurement set data access."""
    
    async def get_metadata(self, ms_path: str) -> Optional["MSRecord"]:
        """Get metadata for a measurement set."""
        ...


class AsyncSourceRepositoryProtocol(Protocol):
    """Protocol for asynchronous source data access."""
    
    async def get_by_id(self, source_id: str) -> Optional["SourceRecord"]:
        """Get source by ID."""
        ...
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["SourceRecord"]:
        """List all sources with pagination."""
        ...
    
    async def get_lightcurve(
        self,
        source_id: str,
        start_mjd: Optional[float] = None,
        end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data for a source."""
        ...


class AsyncJobRepositoryProtocol(Protocol):
    """Protocol for asynchronous job data access."""
    
    async def get_by_run_id(self, run_id: str) -> Optional["JobRecord"]:
        """Get job by run ID."""
        ...
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["JobRecord"]:
        """List all jobs with pagination."""
        ...


# Backwards compatibility aliases (deprecated)
ImageRepositoryInterface = AsyncImageRepositoryProtocol
MSRepositoryInterface = AsyncMSRepositoryProtocol
SourceRepositoryInterface = AsyncSourceRepositoryProtocol
JobRepositoryInterface = AsyncJobRepositoryProtocol

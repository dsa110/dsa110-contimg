"""
Repository interfaces (abstract base classes).

Defines the contracts that repository implementations must fulfill.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .repositories import ImageRecord, MSRecord, SourceRecord, JobRecord


class ImageRepositoryInterface(ABC):
    """Interface for image data access."""
    
    @abstractmethod
    async def get_by_id(self, image_id: str) -> Optional["ImageRecord"]:
        """Get image by ID."""
        ...
    
    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["ImageRecord"]:
        """List all images with pagination."""
        ...
    
    @abstractmethod
    async def get_for_source(self, source_id: str) -> List["ImageRecord"]:
        """Get images containing a source."""
        ...


class MSRepositoryInterface(ABC):
    """Interface for measurement set data access."""
    
    @abstractmethod
    async def get_metadata(self, ms_path: str) -> Optional["MSRecord"]:
        """Get metadata for a measurement set."""
        ...


class SourceRepositoryInterface(ABC):
    """Interface for source data access."""
    
    @abstractmethod
    async def get_by_id(self, source_id: str) -> Optional["SourceRecord"]:
        """Get source by ID."""
        ...
    
    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["SourceRecord"]:
        """List all sources with pagination."""
        ...
    
    @abstractmethod
    async def get_lightcurve(
        self,
        source_id: str,
        start_mjd: Optional[float] = None,
        end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data for a source."""
        ...


class JobRepositoryInterface(ABC):
    """Interface for job data access."""
    
    @abstractmethod
    async def get_by_run_id(self, run_id: str) -> Optional["JobRecord"]:
        """Get job by run ID."""
        ...
    
    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["JobRecord"]:
        """List all jobs with pagination."""
        ...

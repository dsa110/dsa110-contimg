"""
Request validation utilities for the DSA-110 API.

Provides custom validators, path/query parameter validation,
and reusable validation patterns for API endpoints.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generic, List, Optional, TypeVar, Union

from fastapi import HTTPException, Query, Path
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)


# ============================================================================
# Common Validation Patterns
# ============================================================================

# Valid image ID pattern: alphanumeric with underscores/dashes
IMAGE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")

# Valid source name pattern: allows alphanumeric, spaces, underscores, dashes, plus/minus
SOURCE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9\s_+\-\.]{1,200}$")

# Valid MS path pattern: filesystem path
MS_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_/\-\.]{1,500}$")

# ISO 8601 datetime pattern
ISO_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?)?$"
)

# UUID pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationError(HTTPException):
    """Raised when request validation fails."""
    
    def __init__(
        self,
        field: str,
        message: str,
        value: Any = None,
    ):
        detail = {
            "error": "validation_error",
            "field": field,
            "message": message,
        }
        if value is not None:
            detail["value"] = str(value)[:100]  # Truncate long values
        
        super().__init__(status_code=422, detail=detail)


# ============================================================================
# Pagination Models
# ============================================================================

class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    model_config = ConfigDict(extra="forbid")
    
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of items to return",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip",
    )
    
    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v > 1000:
            raise ValueError("limit cannot exceed 1000")
        return v


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters."""
    
    model_config = ConfigDict(extra="forbid")
    
    cursor: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Pagination cursor for next page",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of items to return",
    )


# ============================================================================
# Sort/Filter Models
# ============================================================================

class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    """Standard sort parameters."""
    
    model_config = ConfigDict(extra="forbid")
    
    sort_by: Optional[str] = Field(
        default=None,
        max_length=50,
        pattern=r"^[a-z_]+$",
        description="Field to sort by",
    )
    order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort order",
    )


class DateRangeParams(BaseModel):
    """Date range filter parameters."""
    
    model_config = ConfigDict(extra="forbid")
    
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start of date range (ISO 8601)",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End of date range (ISO 8601)",
    )
    
    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeParams":
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before end_date")
        return self


# ============================================================================
# Entity Validation Models
# ============================================================================

class ImageQueryParams(BaseModel):
    """Query parameters for image listing."""
    
    model_config = ConfigDict(extra="forbid")
    
    source: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Filter by source name",
    )
    field_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter by field name",
    )
    min_flux: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum flux in Jy",
    )
    max_flux: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum flux in Jy",
    )
    
    @model_validator(mode="after")
    def validate_flux_range(self) -> "ImageQueryParams":
        if self.min_flux is not None and self.max_flux is not None:
            if self.min_flux > self.max_flux:
                raise ValueError("min_flux must be less than max_flux")
        return self


class SourceQueryParams(BaseModel):
    """Query parameters for source listing."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Filter by source name (partial match)",
    )
    ra_min: Optional[float] = Field(
        default=None,
        ge=0,
        le=360,
        description="Minimum RA in degrees",
    )
    ra_max: Optional[float] = Field(
        default=None,
        ge=0,
        le=360,
        description="Maximum RA in degrees",
    )
    dec_min: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90,
        description="Minimum Dec in degrees",
    )
    dec_max: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90,
        description="Maximum Dec in degrees",
    )


class JobQueryParams(BaseModel):
    """Query parameters for job listing."""
    
    model_config = ConfigDict(extra="forbid")
    
    status: Optional[str] = Field(
        default=None,
        pattern=r"^(pending|running|completed|failed|cancelled)$",
        description="Filter by job status",
    )
    pipeline: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter by pipeline name",
    )


# ============================================================================
# Path Parameter Validators
# ============================================================================

def validate_image_id(image_id: str) -> str:
    """Validate image ID path parameter."""
    if not IMAGE_ID_PATTERN.match(image_id):
        raise ValidationError(
            field="image_id",
            message="Invalid image ID format. Must be alphanumeric with underscores/dashes.",
            value=image_id,
        )
    return image_id


def validate_source_id(source_id: str) -> str:
    """Validate source ID path parameter."""
    # Sources can use name or numeric ID
    if not (source_id.isdigit() or SOURCE_NAME_PATTERN.match(source_id)):
        raise ValidationError(
            field="source_id",
            message="Invalid source ID format.",
            value=source_id,
        )
    return source_id


def validate_job_id(job_id: str) -> str:
    """Validate job ID path parameter (UUID)."""
    if not UUID_PATTERN.match(job_id):
        raise ValidationError(
            field="job_id",
            message="Invalid job ID format. Must be a valid UUID.",
            value=job_id,
        )
    return job_id


def validate_ms_path(ms_path: str) -> str:
    """Validate MS path parameter."""
    # Decode URL-encoded paths
    import urllib.parse
    decoded_path = urllib.parse.unquote(ms_path)
    
    # Check for path traversal attempts
    if ".." in decoded_path or decoded_path.startswith("/"):
        raise ValidationError(
            field="ms_path",
            message="Invalid MS path. Path traversal not allowed.",
            value=ms_path,
        )
    
    return decoded_path


# ============================================================================
# FastAPI Dependency Helpers
# ============================================================================

def ImageIdPath(
    description: str = "Image identifier"
) -> str:
    """Path parameter for image ID with validation."""
    return Path(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description=description,
        examples=["image_2024_01_15_001"],
    )


def SourceIdPath(
    description: str = "Source identifier or name"
) -> str:
    """Path parameter for source ID with validation."""
    return Path(
        ...,
        min_length=1,
        max_length=200,
        description=description,
        examples=["1", "J1234+5678"],
    )


def JobIdPath(
    description: str = "Job UUID"
) -> str:
    """Path parameter for job ID with validation."""
    return Path(
        ...,
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        description=description,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


def LimitQuery(
    default: int = 50,
    max_value: int = 1000,
    description: str = "Maximum number of items to return",
) -> int:
    """Query parameter for pagination limit."""
    return Query(
        default=default,
        ge=1,
        le=max_value,
        description=description,
    )


def OffsetQuery(
    description: str = "Number of items to skip",
) -> int:
    """Query parameter for pagination offset."""
    return Query(
        default=0,
        ge=0,
        description=description,
    )


# ============================================================================
# Request Body Validation
# ============================================================================

class JobCreateRequest(BaseModel):
    """Request body for creating a new job."""
    
    model_config = ConfigDict(extra="forbid")
    
    pipeline: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Pipeline name",
    )
    parameters: dict = Field(
        default_factory=dict,
        description="Pipeline parameters",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Job priority (1=highest, 10=lowest)",
    )


class CacheInvalidateRequest(BaseModel):
    """Request body for cache invalidation."""
    
    model_config = ConfigDict(extra="forbid")
    
    keys: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Cache keys to invalidate",
    )
    
    @field_validator("keys")
    @classmethod
    def validate_keys(cls, v: List[str]) -> List[str]:
        for key in v:
            if len(key) > 500:
                raise ValueError("Cache key too long")
            if not re.match(r"^[a-zA-Z0-9_:/-]+$", key):
                raise ValueError(f"Invalid cache key format: {key}")
        return v


# ============================================================================
# Content Validation
# ============================================================================

def validate_json_content_type(content_type: Optional[str]) -> bool:
    """Validate that content type is JSON."""
    if content_type is None:
        return False
    return content_type.startswith("application/json")


def validate_file_extension(filename: str, allowed: List[str]) -> bool:
    """Validate file has allowed extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in [e.lower().lstrip(".") for e in allowed]


# ============================================================================
# Coordinate Validation
# ============================================================================

def validate_ra(ra: float) -> float:
    """Validate Right Ascension (0-360 degrees)."""
    if not 0 <= ra <= 360:
        raise ValidationError(
            field="ra",
            message="RA must be between 0 and 360 degrees",
            value=ra,
        )
    return ra


def validate_dec(dec: float) -> float:
    """Validate Declination (-90 to +90 degrees)."""
    if not -90 <= dec <= 90:
        raise ValidationError(
            field="dec",
            message="Dec must be between -90 and +90 degrees",
            value=dec,
        )
    return dec


def validate_search_radius(radius: float, max_radius: float = 10.0) -> float:
    """Validate search radius in degrees."""
    if radius <= 0:
        raise ValidationError(
            field="radius",
            message="Radius must be positive",
            value=radius,
        )
    if radius > max_radius:
        raise ValidationError(
            field="radius",
            message=f"Radius cannot exceed {max_radius} degrees",
            value=radius,
        )
    return radius

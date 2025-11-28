"""
Standardized error envelope for the DSA-110 Continuum Imaging Pipeline API.

This module provides a consistent error response format across all API endpoints.
Error codes are aligned with the frontend ERROR_CODES table for seamless UI integration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """
    Standardized error codes aligned with frontend errorMappings.
    Use UPPER_SNAKE_CASE, keep stable across releases.
    """
    # Calibration errors
    CAL_TABLE_MISSING = "CAL_TABLE_MISSING"
    CAL_APPLY_FAILED = "CAL_APPLY_FAILED"
    
    # Imaging errors
    IMAGE_CLEAN_FAILED = "IMAGE_CLEAN_FAILED"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    
    # Photometry errors
    PHOTOMETRY_BAD_COORDS = "PHOTOMETRY_BAD_COORDS"
    
    # Data errors
    MS_NOT_FOUND = "MS_NOT_FOUND"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    PRODUCTS_DB_UNAVAILABLE = "PRODUCTS_DB_UNAVAILABLE"
    
    # Service errors
    STREAMING_STALE_STATUS = "STREAMING_STALE_STATUS"
    ABSURD_DISABLED = "ABSURD_DISABLED"
    
    # Request errors
    RATE_LIMITED = "RATE_LIMITED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    
    # Generic errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"


# Mapping from error codes to documentation anchors
DOC_ANCHORS: dict[str, str] = {
    ErrorCode.CAL_TABLE_MISSING: "calibration_missing_table",
    ErrorCode.CAL_APPLY_FAILED: "calibration_apply_failed",
    ErrorCode.IMAGE_CLEAN_FAILED: "imaging_tclean_failed",
    ErrorCode.IMAGE_NOT_FOUND: "image_not_found",
    ErrorCode.PHOTOMETRY_BAD_COORDS: "photometry_bad_coords",
    ErrorCode.MS_NOT_FOUND: "ms_not_found",
    ErrorCode.SOURCE_NOT_FOUND: "source_not_found",
    ErrorCode.PRODUCTS_DB_UNAVAILABLE: "db_unavailable",
    ErrorCode.STREAMING_STALE_STATUS: "streaming_stale",
    ErrorCode.VALIDATION_FAILED: "validation_failed",
}


@dataclass
class ErrorEnvelope:
    """
    Standardized error response envelope.
    
    Attributes:
        code: Machine-readable error code (UPPER_SNAKE_CASE)
        http_status: HTTP status code
        user_message: Human-readable message for display
        action: Suggested remediation action
        ref_id: Job/run ID for log correlation (if available)
        details: Additional structured context
        trace_id: Request trace ID for debugging
        doc_anchor: Documentation anchor for troubleshooting link
    """
    code: str
    http_status: int
    user_message: str
    action: str
    ref_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    doc_anchor: Optional[str] = None
    
    def __post_init__(self):
        # Auto-populate doc_anchor if not provided
        if self.doc_anchor is None and self.code in DOC_ANCHORS:
            self.doc_anchor = DOC_ANCHORS[self.code]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = asdict(self)
        # Remove None values for cleaner JSON
        return {k: v for k, v in result.items() if v is not None}


def make_error(
    code: str | ErrorCode,
    http_status: int,
    user_message: str,
    action: str,
    ref_id: str = "",
    details: Optional[dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    doc_anchor: Optional[str] = None,
) -> ErrorEnvelope:
    """
    Factory function to create an error envelope.
    
    Args:
        code: Error code (use ErrorCode enum values)
        http_status: HTTP status code
        user_message: User-friendly error message
        action: Suggested action for the user
        ref_id: Optional job/run ID for correlation
        details: Optional additional context
        trace_id: Optional trace ID (auto-generated if not provided)
        doc_anchor: Optional documentation anchor
    
    Returns:
        ErrorEnvelope ready for serialization
    """
    if isinstance(code, ErrorCode):
        code = code.value
    
    return ErrorEnvelope(
        code=code,
        http_status=http_status,
        user_message=user_message,
        action=action,
        ref_id=ref_id,
        details=details or {},
        trace_id=trace_id or uuid.uuid4().hex[:12],
        doc_anchor=doc_anchor,
    )


# Pre-defined error factory functions for common cases

def cal_table_missing(ms_path: str, ref_id: str = "") -> ErrorEnvelope:
    """Create error for missing calibration table."""
    return make_error(
        code=ErrorCode.CAL_TABLE_MISSING,
        http_status=400,
        user_message=f"Calibration table not found for MS {ms_path}",
        action="Re-run calibration or select an existing table",
        ref_id=ref_id,
        details={"ms_path": ms_path},
    )


def cal_apply_failed(ms_path: str, reason: str, ref_id: str = "") -> ErrorEnvelope:
    """Create error for failed calibration apply."""
    return make_error(
        code=ErrorCode.CAL_APPLY_FAILED,
        http_status=500,
        user_message="Calibration apply failed",
        action="Inspect cal logs; retry apply",
        ref_id=ref_id,
        details={"ms_path": ms_path, "reason": reason},
    )


def image_not_found(image_id: str) -> ErrorEnvelope:
    """Create error for image not found."""
    return make_error(
        code=ErrorCode.IMAGE_NOT_FOUND,
        http_status=404,
        user_message=f"Image {image_id} not found",
        action="Verify the image ID or check if the image has been processed",
        details={"image_id": image_id},
    )


def ms_not_found(ms_path: str) -> ErrorEnvelope:
    """Create error for MS not found."""
    return make_error(
        code=ErrorCode.MS_NOT_FOUND,
        http_status=404,
        user_message=f"Measurement Set not found: {ms_path}",
        action="Confirm path exists; rescan MS directory",
        details={"ms_path": ms_path},
    )


def source_not_found(source_id: str) -> ErrorEnvelope:
    """Create error for source not found."""
    return make_error(
        code=ErrorCode.SOURCE_NOT_FOUND,
        http_status=404,
        user_message=f"Source {source_id} not found",
        action="Verify the source ID or check the source catalog",
        details={"source_id": source_id},
    )


def validation_failed(errors: list[dict[str, Any]]) -> ErrorEnvelope:
    """Create error for validation failures (e.g., Pydantic)."""
    return make_error(
        code=ErrorCode.VALIDATION_FAILED,
        http_status=400,
        user_message="Input validation failed",
        action="Fix highlighted fields and retry",
        details={"validation_errors": errors},
    )


def db_unavailable(db_name: str = "products") -> ErrorEnvelope:
    """Create error for database unavailability."""
    return make_error(
        code=ErrorCode.PRODUCTS_DB_UNAVAILABLE,
        http_status=503,
        user_message=f"{db_name.capitalize()} database unavailable",
        action="Check DB path/permissions; retry",
        details={"database": db_name},
    )


def internal_error(message: str = "An unexpected error occurred", trace_id: Optional[str] = None) -> ErrorEnvelope:
    """Create error for internal server errors."""
    return make_error(
        code=ErrorCode.INTERNAL_ERROR,
        http_status=500,
        user_message=message,
        action="Please try again later or contact support",
        trace_id=trace_id,
    )

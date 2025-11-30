"""
Custom exception types for the DSA-110 API.

This module provides a hierarchy of exceptions for specific error scenarios,
enabling more precise error handling and better error messages for API consumers.

Exception Hierarchy:
    DSA110APIError (base)
    ├── DatabaseError
    │   ├── ConnectionError
    │   ├── QueryError
    │   └── TransactionError
    ├── RepositoryError
    │   ├── RecordNotFoundError
    │   ├── RecordAlreadyExistsError
    │   └── InvalidRecordError
    ├── ServiceError
    │   ├── ValidationError
    │   ├── ProcessingError
    │   └── ExternalServiceError
    ├── FileSystemError
    │   ├── FileNotFoundError
    │   ├── FileAccessError
    │   └── InvalidPathError
    └── QAError
        ├── ExtractionError
        └── CalculationError
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class DSA110APIError(Exception):
    """Base exception for all DSA-110 API errors.
    
    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Optional additional error details
    """
    
    default_code = "API_ERROR"
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code or self.default_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# Database Exceptions
# =============================================================================

class DatabaseError(DSA110APIError):
    """Base class for database-related errors."""
    default_code = "DATABASE_ERROR"


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    default_code = "DATABASE_CONNECTION_ERROR"
    
    def __init__(self, database: str, cause: Optional[str] = None):
        message = f"Failed to connect to database: {database}"
        if cause:
            message += f" ({cause})"
        super().__init__(message, details={"database": database})


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""
    default_code = "DATABASE_QUERY_ERROR"
    
    def __init__(self, query: str, cause: Optional[str] = None):
        message = f"Database query failed"
        if cause:
            message += f": {cause}"
        super().__init__(message, details={"query_type": query})


class DatabaseTransactionError(DatabaseError):
    """Raised when a database transaction fails."""
    default_code = "DATABASE_TRANSACTION_ERROR"


# =============================================================================
# Repository Exceptions
# =============================================================================

class RepositoryError(DSA110APIError):
    """Base class for repository-related errors."""
    default_code = "REPOSITORY_ERROR"


class RecordNotFoundError(RepositoryError):
    """Raised when a requested record is not found."""
    default_code = "RECORD_NOT_FOUND"
    
    def __init__(self, entity_type: str, identifier: Any):
        message = f"{entity_type} not found: {identifier}"
        super().__init__(
            message,
            details={"entity_type": entity_type, "identifier": str(identifier)},
        )


class RecordAlreadyExistsError(RepositoryError):
    """Raised when trying to create a record that already exists."""
    default_code = "RECORD_ALREADY_EXISTS"
    
    def __init__(self, entity_type: str, identifier: Any):
        message = f"{entity_type} already exists: {identifier}"
        super().__init__(
            message,
            details={"entity_type": entity_type, "identifier": str(identifier)},
        )


class InvalidRecordError(RepositoryError):
    """Raised when a record fails validation."""
    default_code = "INVALID_RECORD"


# =============================================================================
# Service Exceptions
# =============================================================================

class ServiceError(DSA110APIError):
    """Base class for service-layer errors."""
    default_code = "SERVICE_ERROR"


class ValidationError(ServiceError):
    """Raised when input validation fails."""
    default_code = "VALIDATION_ERROR"
    
    def __init__(self, field: str, message: str, value: Any = None):
        full_message = f"Validation failed for '{field}': {message}"
        details = {"field": field}
        if value is not None:
            details["value"] = str(value)
        super().__init__(full_message, details=details)


class ProcessingError(ServiceError):
    """Raised when processing an operation fails."""
    default_code = "PROCESSING_ERROR"


class ExternalServiceError(ServiceError):
    """Raised when an external service call fails."""
    default_code = "EXTERNAL_SERVICE_ERROR"
    
    def __init__(self, service: str, message: str):
        super().__init__(
            f"External service error ({service}): {message}",
            details={"service": service},
        )


# =============================================================================
# File System Exceptions
# =============================================================================

class FileSystemError(DSA110APIError):
    """Base class for file system errors."""
    default_code = "FILE_SYSTEM_ERROR"


class FileNotAccessibleError(FileSystemError):
    """Raised when a file cannot be accessed."""
    default_code = "FILE_NOT_ACCESSIBLE"
    
    def __init__(self, path: str, operation: str = "access"):
        message = f"Cannot {operation} file: {path}"
        super().__init__(message, details={"path": path, "operation": operation})


class InvalidPathError(FileSystemError):
    """Raised when a path is invalid or unsafe."""
    default_code = "INVALID_PATH"
    
    def __init__(self, path: str, reason: str = "invalid"):
        message = f"Invalid path ({reason}): {path}"
        super().__init__(message, details={"path": path, "reason": reason})


class FITSParsingError(FileSystemError):
    """Raised when FITS file parsing fails."""
    default_code = "FITS_PARSING_ERROR"
    
    def __init__(self, path: str, cause: Optional[str] = None):
        message = f"Failed to parse FITS file: {path}"
        if cause:
            message += f" ({cause})"
        super().__init__(message, details={"path": path})


class MSParsingError(FileSystemError):
    """Raised when Measurement Set parsing fails."""
    default_code = "MS_PARSING_ERROR"
    
    def __init__(self, path: str, cause: Optional[str] = None):
        message = f"Failed to parse Measurement Set: {path}"
        if cause:
            message += f" ({cause})"
        super().__init__(message, details={"path": path})


# =============================================================================
# QA Exceptions
# =============================================================================

class QAError(DSA110APIError):
    """Base class for QA-related errors."""
    default_code = "QA_ERROR"


class QAExtractionError(QAError):
    """Raised when QA extraction fails."""
    default_code = "QA_EXTRACTION_ERROR"
    
    def __init__(self, source: str, qa_type: str, cause: Optional[str] = None):
        message = f"Failed to extract {qa_type} QA from {source}"
        if cause:
            message += f": {cause}"
        super().__init__(message, details={"source": source, "qa_type": qa_type})


class QACalculationError(QAError):
    """Raised when QA calculation fails."""
    default_code = "QA_CALCULATION_ERROR"


# =============================================================================
# Batch Job Exceptions
# =============================================================================

class BatchJobError(DSA110APIError):
    """Base class for batch job errors."""
    default_code = "BATCH_JOB_ERROR"


class BatchJobNotFoundError(BatchJobError):
    """Raised when a batch job is not found."""
    default_code = "BATCH_JOB_NOT_FOUND"
    
    def __init__(self, job_id: int):
        super().__init__(
            f"Batch job not found: {job_id}",
            details={"job_id": job_id},
        )


class BatchJobInvalidStateError(BatchJobError):
    """Raised when a batch job is in an invalid state for the operation."""
    default_code = "BATCH_JOB_INVALID_STATE"
    
    def __init__(self, job_id: int, current_state: str, expected_states: list):
        super().__init__(
            f"Batch job {job_id} is in state '{current_state}', "
            f"expected one of: {expected_states}",
            details={
                "job_id": job_id,
                "current_state": current_state,
                "expected_states": expected_states,
            },
        )


# =============================================================================
# Utility Functions
# =============================================================================

def map_exception_to_http_status(exc: DSA110APIError) -> int:
    """Map an exception to an appropriate HTTP status code.
    
    Args:
        exc: The exception to map
        
    Returns:
        HTTP status code
    """
    status_map = {
        RecordNotFoundError: 404,
        RecordAlreadyExistsError: 409,
        ValidationError: 400,
        InvalidPathError: 400,
        InvalidRecordError: 400,
        DatabaseConnectionError: 503,
        ExternalServiceError: 502,
        FileNotAccessibleError: 404,
        BatchJobNotFoundError: 404,
        BatchJobInvalidStateError: 409,
    }
    
    for exc_type, status in status_map.items():
        if isinstance(exc, exc_type):
            return status
    
    return 500  # Default to internal server error

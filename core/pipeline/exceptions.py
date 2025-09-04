# core/pipeline/exceptions.py
"""
Custom exception hierarchy for DSA-110 pipeline.

This module defines a comprehensive exception hierarchy that provides
clear error categorization and better error handling throughout the pipeline.
"""


class PipelineError(Exception):
    """Base exception for all pipeline-related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(PipelineError):
    """Raised when there are configuration-related errors."""
    pass


class DataError(PipelineError):
    """Raised when there are data-related errors (missing files, corrupt data, etc.)."""
    pass


class StageError(PipelineError):
    """Base exception for pipeline stage errors."""
    pass


class CalibrationError(StageError):
    """Raised when calibration operations fail."""
    pass


class ImagingError(StageError):
    """Raised when imaging operations fail."""
    pass


class MosaickingError(StageError):
    """Raised when mosaicking operations fail."""
    pass


class PhotometryError(StageError):
    """Raised when photometry operations fail."""
    pass


class ServiceError(PipelineError):
    """Raised when service-related operations fail."""
    pass


class MessageQueueError(ServiceError):
    """Raised when message queue operations fail."""
    pass


class StateManagementError(ServiceError):
    """Raised when state management operations fail."""
    pass


class ValidationError(PipelineError):
    """Raised when data validation fails."""
    pass


class DependencyError(PipelineError):
    """Raised when required dependencies are missing or incompatible."""
    pass

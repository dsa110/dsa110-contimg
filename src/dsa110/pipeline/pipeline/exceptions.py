# core/pipeline/exceptions.py
"""
Custom exception hierarchy for DSA-110 pipeline.

This module defines a comprehensive exception hierarchy that provides
clear error categorization and better error handling throughout the pipeline.
"""

# Import base exceptions from utils to avoid circular imports
from ..utils.exceptions import (
    PipelineError, DataError, ConfigurationError, StageError,
    CalibrationError, ImagingError, MosaickingError, PhotometryError
)


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

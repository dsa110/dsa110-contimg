# core/pipeline/__init__.py
"""
Pipeline orchestration and processing stages.

This package contains the main pipeline orchestrator and individual
processing stages for calibration, imaging, mosaicking, and photometry.
"""

from .orchestrator import PipelineOrchestrator, ProcessingBlock, ProcessingResult
from .enhanced_orchestrator import EnhancedPipelineOrchestrator
from .exceptions import (
    PipelineError, ConfigurationError, DataError, StageError,
    CalibrationError, ImagingError, MosaickingError, PhotometryError,
    ServiceError, MessageQueueError, StateManagementError,
    ValidationError, DependencyError
)

__all__ = [
    'PipelineOrchestrator', 'EnhancedPipelineOrchestrator', 'ProcessingBlock', 'ProcessingResult',
    'PipelineError', 'ConfigurationError', 'DataError', 'StageError',
    'CalibrationError', 'ImagingError', 'MosaickingError', 'PhotometryError',
    'ServiceError', 'MessageQueueError', 'StateManagementError',
    'ValidationError', 'DependencyError'
]

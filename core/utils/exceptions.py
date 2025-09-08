# core/utils/exceptions.py
"""
Basic exceptions for the DSA-110 pipeline.

This module contains basic exceptions that can be used across
the pipeline without creating circular import dependencies.
"""


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class DataError(PipelineError):
    """Exception raised for data-related errors."""
    pass


class ConfigurationError(PipelineError):
    """Exception raised for configuration-related errors."""
    pass


class StageError(PipelineError):
    """Exception raised for stage-related errors."""
    pass


class CalibrationError(StageError):
    """Exception raised for calibration-related errors."""
    pass


class ImagingError(StageError):
    """Exception raised for imaging-related errors."""
    pass


class MosaickingError(StageError):
    """Exception raised for mosaicking-related errors."""
    pass


class PhotometryError(StageError):
    """Exception raised for photometry-related errors."""
    pass

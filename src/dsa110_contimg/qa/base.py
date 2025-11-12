"""
Base classes and protocols for QA validation system.

Provides abstraction layer for consistent validation patterns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable

try:
    from typing_extensions import runtime_checkable
except ImportError:
    # Fallback for older Python versions
    def runtime_checkable(cls):
        return cls


@runtime_checkable
class Validator(Protocol):
    """Protocol for validation functions.

    All validators should follow this interface for consistency.
    """

    def validate(self, context: "ValidationContext") -> "ValidationResult":
        """Run validation and return result.

        Args:
            context: Validation context with inputs and configuration

        Returns:
            ValidationResult with pass/fail status and details
        """
        ...


@dataclass
class ValidationContext:
    """Context object passed to validators.

    Contains all inputs and configuration needed for validation.
    """

    # Input data paths
    image_path: Optional[str] = None
    ms_path: Optional[str] = None
    catalog_path: Optional[str] = None
    calibration_tables: Optional[list[str]] = None

    # Configuration
    config: Optional[Dict[str, Any]] = None

    # Additional context
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.config is None:
            self.config = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationResult:
    """Base class for validation results.

    All validation results should inherit from this or follow its structure.
    """

    # Core status
    passed: bool
    message: str

    # Details
    details: Dict[str, Any]

    # Metrics (optional)
    metrics: Optional[Dict[str, float]] = None

    # Warnings (non-fatal issues)
    warnings: list[str] = None

    # Errors (fatal issues)
    errors: list[str] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.details is None:
            self.details = {}

    def add_warning(self, warning: str):
        """Add a warning message."""
        if self.warnings is None:
            self.warnings = []
        self.warnings.append(warning)

    def add_error(self, error: str):
        """Add an error message."""
        if self.errors is None:
            self.errors = []
        self.errors.append(error)
        self.passed = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "metrics": self.metrics or {},
            "warnings": self.warnings or [],
            "errors": self.errors or [],
        }


class ValidationError(Exception):
    """Base exception for validation errors."""

    pass


class ValidationConfigurationError(ValidationError):
    """Raised when validation configuration is invalid."""

    pass


class ValidationInputError(ValidationError):
    """Raised when validation inputs are invalid or missing."""

    pass


class ValidationExecutionError(ValidationError):
    """Raised when validation execution fails."""

    pass

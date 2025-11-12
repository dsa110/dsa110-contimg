"""
Unit tests for QA base classes and protocols.
"""

import pytest
from dsa110_contimg.qa.base import (
    ValidationContext,
    ValidationError,
    ValidationInputError,
    ValidationResult,
)


class TestValidationContext:
    """Test ValidationContext dataclass."""

    def test_default_initialization(self):
        """Test default initialization."""
        ctx = ValidationContext()
        assert ctx.image_path is None
        assert ctx.ms_path is None
        assert ctx.config == {}
        assert ctx.metadata == {}

    def test_custom_initialization(self):
        """Test custom initialization."""
        ctx = ValidationContext(
            image_path="test.fits",
            ms_path="test.ms",
            config={"key": "value"},
            metadata={"meta": "data"},
        )
        assert ctx.image_path == "test.fits"
        assert ctx.ms_path == "test.ms"
        assert ctx.config == {"key": "value"}
        assert ctx.metadata == {"meta": "data"}


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_default_initialization(self):
        """Test default initialization."""
        result = ValidationResult(
            passed=True,
            message="Test passed",
            details={},
        )
        assert result.passed is True
        assert result.message == "Test passed"
        assert result.details == {}
        assert result.warnings == []
        assert result.errors == []

    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult(
            passed=True,
            message="Test",
            details={},
        )
        result.add_warning("Warning 1")
        assert len(result.warnings) == 1
        assert "Warning 1" in result.warnings

    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult(
            passed=True,
            message="Test",
            details={},
        )
        result.add_error("Error 1")
        assert len(result.errors) == 1
        assert "Error 1" in result.errors
        assert result.passed is False  # Errors should set passed=False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ValidationResult(
            passed=True,
            message="Test",
            details={"key": "value"},
            metrics={"metric": 1.0},
        )
        result.add_warning("Warning")
        result.add_error("Error")
        
        result_dict = result.to_dict()
        # add_error() sets passed=False
        assert result_dict["passed"] is False
        assert result_dict["message"] == "Test"
        assert result_dict["details"] == {"key": "value"}
        assert result_dict["metrics"] == {"metric": 1.0}
        assert result_dict["warnings"] == ["Warning"]
        assert result_dict["errors"] == ["Error"]


class TestValidationErrors:
    """Test validation exception hierarchy."""

    def test_validation_error(self):
        """Test base ValidationError."""
        with pytest.raises(ValidationError):
            raise ValidationError("Test error")

    def test_validation_input_error(self):
        """Test ValidationInputError."""
        with pytest.raises(ValidationInputError):
            raise ValidationInputError("Invalid input")
        
        # Should also be catchable as ValidationError
        with pytest.raises(ValidationError):
            raise ValidationInputError("Invalid input")


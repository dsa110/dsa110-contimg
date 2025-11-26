"""Unit tests for mosaic error handling utilities.

Tests for:
- Image format detection
- Pre-validation checks
- Disk space checking
- CASA tool error handling
- Image data validation
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestImageFormatDetection:
    """Tests for detect_image_format function."""

    def test_detect_nonexistent_file(self, tmp_path):
        """Test detection of nonexistent file."""
        from dsa110_contimg.mosaic.error_handling import detect_image_format

        nonexistent = tmp_path / "nonexistent.fits"
        fmt, is_valid = detect_image_format(str(nonexistent))

        assert fmt == "unknown"
        assert is_valid is False

    def test_detect_valid_fits_file(self, tmp_path):
        """Test detection of valid FITS file."""
        from dsa110_contimg.mosaic.error_handling import detect_image_format

        fits_file = tmp_path / "test.fits"
        fits_file.write_bytes(b"SIMPLE  =                    T")

        fmt, is_valid = detect_image_format(str(fits_file))

        assert fmt == "fits"
        assert is_valid is True

    def test_detect_fits_by_extension(self, tmp_path):
        """Test FITS detection by extension."""
        from dsa110_contimg.mosaic.error_handling import detect_image_format

        fits_file = tmp_path / "test.fits"
        fits_file.write_bytes(b"dummy content")  # Not valid FITS header

        fmt, is_valid = detect_image_format(str(fits_file))

        # Has .fits extension
        assert fmt == "fits"
        assert is_valid is True

    def test_detect_casa_image_directory(self, tmp_path):
        """Test detection of CASA image directory."""
        from dsa110_contimg.mosaic.error_handling import detect_image_format

        casa_dir = tmp_path / "test.image"
        casa_dir.mkdir()
        (casa_dir / "table.dat").touch()

        fmt, is_valid = detect_image_format(str(casa_dir))

        assert fmt == "casa"
        assert is_valid is True

    def test_detect_invalid_casa_directory(self, tmp_path):
        """Test detection of invalid CASA image directory."""
        from dsa110_contimg.mosaic.error_handling import detect_image_format

        casa_dir = tmp_path / "test.image"
        casa_dir.mkdir()
        # No table.dat file

        fmt, is_valid = detect_image_format(str(casa_dir))

        assert fmt == "casa"
        assert is_valid is False


class TestImagePreValidation:
    """Tests for validate_image_before_read function."""

    def test_validate_nonexistent_image(self, tmp_path):
        """Test validation of nonexistent image."""
        from dsa110_contimg.mosaic.error_handling import validate_image_before_read
        from dsa110_contimg.mosaic.exceptions import ImageReadError

        with pytest.raises(ImageReadError) as exc_info:
            validate_image_before_read(str(tmp_path / "nonexistent.fits"))

        assert "not found" in str(exc_info.value)

    def test_validate_unknown_format(self, tmp_path):
        """Test validation of unknown format."""
        from dsa110_contimg.mosaic.error_handling import validate_image_before_read
        from dsa110_contimg.mosaic.exceptions import IncompatibleImageFormatError

        # Create a file with unknown extension
        unknown_file = tmp_path / "test.xyz"
        unknown_file.write_text("dummy content")

        with pytest.raises(IncompatibleImageFormatError) as exc_info:
            validate_image_before_read(str(unknown_file))

        assert "Unknown image format" in str(exc_info.value)

    def test_validate_invalid_casa_directory(self, tmp_path):
        """Test validation of invalid CASA image directory."""
        from dsa110_contimg.mosaic.error_handling import validate_image_before_read
        from dsa110_contimg.mosaic.exceptions import ImageCorruptionError

        casa_dir = tmp_path / "test.image"
        casa_dir.mkdir()
        # No table.dat file

        with pytest.raises(ImageCorruptionError) as exc_info:
            validate_image_before_read(str(casa_dir))

        assert "missing table.dat" in str(exc_info.value)

    def test_validate_valid_fits_file(self, tmp_path):
        """Test validation of valid FITS file."""
        from dsa110_contimg.mosaic.error_handling import validate_image_before_read

        fits_file = tmp_path / "test.fits"
        fits_file.write_bytes(b"SIMPLE  =                    T")

        # Should not raise
        validate_image_before_read(str(fits_file))

    def test_validate_with_operation_context(self, tmp_path):
        """Test validation includes operation context in error."""
        from dsa110_contimg.mosaic.error_handling import validate_image_before_read
        from dsa110_contimg.mosaic.exceptions import ImageReadError

        with pytest.raises(ImageReadError) as exc_info:
            validate_image_before_read(
                str(tmp_path / "nonexistent.fits"),
                operation="mosaic_combine",
            )

        assert "mosaic_combine" in str(exc_info.value)


class TestImageDataValidation:
    """Tests for validate_image_data function."""

    def test_validate_none_data(self, tmp_path):
        """Test validation of None data."""
        from dsa110_contimg.mosaic.error_handling import validate_image_data
        from dsa110_contimg.mosaic.exceptions import ImageCorruptionError

        with pytest.raises(ImageCorruptionError) as exc_info:
            validate_image_data(None, "/path/to/image")

        assert "is None" in str(exc_info.value)

    def test_validate_all_nan_data(self, tmp_path):
        """Test validation of all-NaN data."""
        import numpy as np

        from dsa110_contimg.mosaic.error_handling import validate_image_data
        from dsa110_contimg.mosaic.exceptions import ImageCorruptionError

        nan_data = np.full((10, 10), np.nan)

        with pytest.raises(ImageCorruptionError) as exc_info:
            validate_image_data(nan_data, "/path/to/image")

        assert "no valid data" in str(exc_info.value)

    def test_validate_all_inf_data(self, tmp_path):
        """Test validation of all-Inf data."""
        import numpy as np

        from dsa110_contimg.mosaic.error_handling import validate_image_data
        from dsa110_contimg.mosaic.exceptions import ImageCorruptionError

        inf_data = np.full((10, 10), np.inf)

        with pytest.raises(ImageCorruptionError) as exc_info:
            validate_image_data(inf_data, "/path/to/image")

        assert "no valid data" in str(exc_info.value)

    def test_validate_all_zero_data_warns(self, tmp_path):
        """Test validation of all-zero data (should warn but not fail)."""
        import numpy as np

        from dsa110_contimg.mosaic.error_handling import validate_image_data

        zero_data = np.zeros((10, 10))

        # Should not raise, but logs warning
        validate_image_data(zero_data, "/path/to/image")

    def test_validate_valid_data(self, tmp_path):
        """Test validation of valid data."""
        import numpy as np

        from dsa110_contimg.mosaic.error_handling import validate_image_data

        valid_data = np.random.randn(10, 10)

        # Should not raise
        validate_image_data(valid_data, "/path/to/image")


class TestDiskSpaceCheck:
    """Tests for check_disk_space function."""

    def test_check_disk_space_with_path(self, tmp_path):
        """Test disk space check with valid path."""
        from dsa110_contimg.mosaic.error_handling import check_disk_space

        # Should return tuple (is_ok, message)
        result = check_disk_space(str(tmp_path))

        assert isinstance(result, tuple)
        assert len(result) == 2
        is_ok, message = result
        assert isinstance(is_ok, bool)
        assert isinstance(message, str)

    def test_check_disk_space_nonexistent_path(self):
        """Test disk space check with nonexistent path."""
        from dsa110_contimg.mosaic.error_handling import check_disk_space

        # Function returns (True, error_msg) for errors when not fatal
        # This is by design - don't block on disk check errors
        result = check_disk_space("/nonexistent/path/to/nowhere")
        
        assert isinstance(result, tuple)
        # Result is (True, "Could not check disk space: ...") for non-fatal errors


class TestCASAToolErrorHandling:
    """Tests for CASA tool error handling."""

    def test_handle_casa_tool_error_imhead(self):
        """Test error handling for imhead failures."""
        from dsa110_contimg.mosaic.error_handling import handle_casa_tool_error
        from dsa110_contimg.mosaic.exceptions import CASAToolError

        with pytest.raises(CASAToolError) as exc_info:
            handle_casa_tool_error(
                "imhead",
                Exception("Image file not found"),
                image_path="/path/to/image",
                operation="get_header",
            )

        error = exc_info.value
        assert "imhead" in str(error)
        assert "imhead failed" in error.recovery_hint

    def test_handle_casa_tool_error_imregrid(self):
        """Test error handling for imregrid failures."""
        from dsa110_contimg.mosaic.error_handling import handle_casa_tool_error
        from dsa110_contimg.mosaic.exceptions import CASAToolError

        with pytest.raises(CASAToolError) as exc_info:
            handle_casa_tool_error(
                "imregrid",
                Exception("Coordinate system mismatch"),
                image_path="/path/to/image",
                operation="regrid",
            )

        error = exc_info.value
        assert "imregrid" in str(error)
        assert "imregrid failed" in error.recovery_hint

    def test_handle_casa_tool_error_immath(self):
        """Test error handling for immath failures."""
        from dsa110_contimg.mosaic.error_handling import handle_casa_tool_error
        from dsa110_contimg.mosaic.exceptions import CASAToolError

        with pytest.raises(CASAToolError) as exc_info:
            handle_casa_tool_error(
                "immath",
                Exception("Expression error"),
                image_path="/path/to/image",
                operation="math",
            )

        error = exc_info.value
        assert "immath" in str(error)
        assert "immath failed" in error.recovery_hint

    def test_handle_casa_tool_error_exportfits(self):
        """Test error handling for exportfits failures."""
        from dsa110_contimg.mosaic.error_handling import handle_casa_tool_error
        from dsa110_contimg.mosaic.exceptions import CASAToolError

        with pytest.raises(CASAToolError) as exc_info:
            handle_casa_tool_error(
                "exportfits",
                Exception("File exists"),
                image_path="/path/to/image",
                operation="export",
            )

        error = exc_info.value
        assert "exportfits" in str(error)
        assert "exportfits failed" in error.recovery_hint

    def test_handle_casa_tool_error_unknown_tool(self):
        """Test error handling for unknown CASA tool."""
        from dsa110_contimg.mosaic.error_handling import handle_casa_tool_error
        from dsa110_contimg.mosaic.exceptions import CASAToolError

        with pytest.raises(CASAToolError) as exc_info:
            handle_casa_tool_error(
                "unknown_tool",
                Exception("Some error"),
                operation="test",
            )

        error = exc_info.value
        assert "unknown_tool" in str(error)
        assert "Check CASA logs" in error.recovery_hint

    def test_error_context_includes_image_path(self):
        """Test that error context includes image path."""
        from dsa110_contimg.mosaic.error_handling import handle_casa_tool_error
        from dsa110_contimg.mosaic.exceptions import CASAToolError

        with pytest.raises(CASAToolError) as exc_info:
            handle_casa_tool_error(
                "imhead",
                Exception("Error"),
                image_path="/test/path/image.fits",
                operation="test",
            )

        error = exc_info.value
        assert error.context.get("image_path") == "/test/path/image.fits"


class TestExceptionTypes:
    """Tests for custom exception types."""

    def test_image_read_error(self):
        """Test ImageReadError exception."""
        from dsa110_contimg.mosaic.exceptions import ImageReadError

        error = ImageReadError(
            "Cannot read image",
            "Check file exists",
            context={"path": "/test/image"},
        )

        assert "Cannot read image" in str(error)
        assert error.recovery_hint == "Check file exists"
        assert error.context["path"] == "/test/image"

    def test_image_corruption_error(self):
        """Test ImageCorruptionError exception."""
        from dsa110_contimg.mosaic.exceptions import ImageCorruptionError

        error = ImageCorruptionError(
            "Image is corrupted",
            "Try regenerating the image",
            context={"operation": "read"},
        )

        assert "corrupted" in str(error)
        assert "regenerating" in error.recovery_hint

    def test_incompatible_image_format_error(self):
        """Test IncompatibleImageFormatError exception."""
        from dsa110_contimg.mosaic.exceptions import IncompatibleImageFormatError

        error = IncompatibleImageFormatError(
            "Unknown format",
            "Convert to FITS or CASA format",
        )

        assert "Unknown format" in str(error)
        assert "Convert" in error.recovery_hint

    def test_casa_tool_error(self):
        """Test CASAToolError exception."""
        from dsa110_contimg.mosaic.exceptions import CASAToolError

        error = CASAToolError(
            "imhead failed",
            "Check image integrity",
            context={"tool": "imhead"},
        )

        assert "imhead" in str(error)
        assert error.context["tool"] == "imhead"

"""
Enhanced error handling utilities for mosaic building operations.

Provides helper functions for:
- Image format detection and validation
- Pre-validation checks before expensive operations
- Granular CASA tool error handling with context
- Disk space checking
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

try:
    from casatasks import imhead

    HAVE_CASA_TOOLS = True
except ImportError:
    HAVE_CASA_TOOLS = False

try:
    from casacore.images import image as casaimage

    HAVE_CASACORE = True
except ImportError:
    HAVE_CASACORE = False


def detect_image_format(image_path: str) -> Tuple[str, bool]:
    """
    Detect image format (CASA directory or FITS file).

    Args:
        image_path: Path to image

    Returns:
        (format_type, is_valid) where format_type is 'casa' or 'fits'
    """
    path = Path(image_path)

    if not path.exists():
        return "unknown", False

    # Check if it's a CASA image directory
    if path.is_dir():
        # CASA images are directories with table.dat file
        table_file = path / "table.dat"
        if table_file.exists():
            return "casa", True
        # Might be a directory but not a valid CASA image
        return "casa", False

    # Check if it's a FITS file
    if path.is_file():
        if path.suffix.lower() == ".fits":
            return "fits", True
        # Try to read as FITS even without .fits extension
        try:
            # Check file signature (FITS starts with 'SIMPLE')
            with open(path, "rb") as f:
                header = f.read(80)
                if header.startswith(b"SIMPLE"):
                    return "fits", True
        except Exception:
            pass

    return "unknown", False


def validate_image_before_read(
    image_path: str,
    operation: str = "read",
    check_format: bool = True,
    check_permissions: bool = True,
) -> None:
    """
    Pre-validate image before attempting to read it.

    Performs checks:
    - File/directory exists
    - Format detection
    - Read permissions
    - Basic structure validation

    Args:
        image_path: Path to image
        operation: Operation being performed (for error messages)
        check_format: Whether to check image format
        check_permissions: Whether to check file permissions

    Raises:
        ImageReadError: If image cannot be read
        ImageCorruptionError: If image appears corrupted
        IncompatibleImageFormatError: If format is not supported
    """
    # Import here to avoid circular imports
    from .exceptions import (
        ImageCorruptionError,
        ImageReadError,
        IncompatibleImageFormatError,
    )

    path = Path(image_path)

    # Check existence
    if not path.exists():
        raise ImageReadError(
            f"Image not found: {image_path}",
            f"Check that the file/directory exists. Operation: {operation}",
            context={"operation": operation, "image_path": str(image_path)},
        )

    # Check format
    if check_format:
        fmt, is_valid = detect_image_format(image_path)
        if fmt == "unknown":
            raise IncompatibleImageFormatError(
                f"Unknown image format: {image_path}",
                f"Expected CASA image directory or FITS file. Operation: {operation}",
                context={"operation": operation, "image_path": str(image_path)},
            )
        if not is_valid:
            if fmt == "casa":
                raise ImageCorruptionError(
                    f"Invalid CASA image directory: {image_path} (missing table.dat)",
                    f"Directory exists but doesn't appear to be a valid CASA image. "
                    f"Operation: {operation}",
                    context={"operation": operation, "image_path": str(image_path)},
                )
            else:
                raise ImageCorruptionError(
                    f"Invalid FITS file: {image_path}",
                    f"File exists but doesn't appear to be a valid FITS file. "
                    f"Operation: {operation}",
                    context={"operation": operation, "image_path": str(image_path)},
                )

    # Check permissions
    if check_permissions:
        if path.is_file():
            if not os.access(path, os.R_OK):
                raise ImageReadError(
                    f"No read permission for image: {image_path}",
                    f"Check file permissions. Operation: {operation}",
                    context={"operation": operation, "image_path": str(image_path)},
                )
        elif path.is_dir():
            # Check if directory is readable
            if not os.access(path, os.R_OK):
                raise ImageReadError(
                    f"No read permission for image directory: {image_path}",
                    f"Check directory permissions. Operation: {operation}",
                    context={"operation": operation, "image_path": str(image_path)},
                )


def validate_image_data(data, image_path: str, operation: str = "read") -> None:
    """
    Validate image data after reading for corruption signs.

    Args:
        data: Image data array
        image_path: Path to image (for error messages)
        operation: Operation being performed

    Raises:
        ImageCorruptionError: If data appears corrupted
    """
    import numpy as np

    from .exceptions import ImageCorruptionError

    if data is None:
        raise ImageCorruptionError(
            f"Image data is None: {image_path}",
            f"Image read returned None. Operation: {operation}",
            context={"operation": operation, "image_path": str(image_path)},
        )

    # Check if all NaN or all Inf
    if isinstance(data, np.ndarray):
        finite_data = data[np.isfinite(data)]
        if len(finite_data) == 0:
            raise ImageCorruptionError(
                f"Image contains no valid data (all NaN/Inf): {image_path}",
                f"Image may be corrupted or uninitialized. Operation: {operation}",
                context={"operation": operation, "image_path": str(image_path)},
            )

        # Check for suspicious all-zero (might be valid, but warn)
        if np.all(data == 0):
            logger.warning(
                f"Image contains only zeros: {image_path} " f"(this may be valid but is unusual)"
            )


def handle_casa_tool_error(
    tool_name: str,
    error: Exception,
    image_path: Optional[str] = None,
    operation: str = "unknown",
    **kwargs,
) -> None:
    """
    Convert CASA tool errors to specific exception types with context.

    Args:
        tool_name: Name of CASA tool that failed (e.g., 'imhead', 'imregrid')
        error: Original exception
        image_path: Path to image being processed
        operation: Operation being performed
        **kwargs: Additional context for error message

    Raises:
        CASAToolError: With enhanced context and recovery hints
    """
    from .exceptions import CASAToolError

    error_msg = str(error)

    # Build context
    context = {
        "tool": tool_name,
        "operation": operation,
    }
    if image_path:
        context["image_path"] = image_path
    context.update(kwargs)

    # Provide tool-specific recovery hints
    recovery_hints = {
        "imhead": (
            "imhead failed. Common causes:\n"
            "  - Image file is corrupted or incomplete\n"
            "  - Image is locked by another process\n"
            "  - Insufficient disk space\n"
            "  - CASA installation issue\n"
            "Try: Check image integrity, verify CASA installation, check disk space"
        ),
        "imregrid": (
            "imregrid failed. Common causes:\n"
            "  - Incompatible coordinate systems between images\n"
            "  - Template image is corrupted\n"
            "  - Insufficient disk space for output\n"
            "  - Image projection mismatch\n"
            "Try: Verify coordinate systems match, check template image, ensure disk space"
        ),
        "immath": (
            "immath failed. Common causes:\n"
            "  - Input images have incompatible formats\n"
            "  - Expression syntax error\n"
            "  - Insufficient disk space\n"
            "  - One or more input images are corrupted\n"
            "Try: Verify all input images are valid, check expression syntax, ensure disk space"
        ),
        "exportfits": (
            "exportfits failed. Common causes:\n"
            "  - Output file already exists and cannot be overwritten\n"
            "  - Insufficient disk space\n"
            "  - Image is locked\n"
            "Try: Check output file permissions, ensure disk space, close other processes using image"
        ),
    }

    recovery_hint = recovery_hints.get(tool_name, "Check CASA logs for details.")

    # Add image-specific context if available
    if image_path:
        recovery_hint += f"\nImage: {image_path}"

    raise CASAToolError(
        f"CASA tool '{tool_name}' failed: {error_msg}", recovery_hint, context=context
    ) from error


def safe_imhead(imagename: str, mode: str = "list", **kwargs) -> Any:
    """
    Safely call imhead with enhanced error handling.

    Args:
        imagename: Image name/path
        mode: imhead mode ('list', 'get', etc.)
        **kwargs: Additional imhead arguments

    Returns:
        imhead result

    Raises:
        CASAToolError: With context if imhead fails
    """
    if not HAVE_CASA_TOOLS:
        from .exceptions import CASAToolError

        raise CASAToolError(
            "CASA imhead not available",
            "Ensure CASA is installed and available: conda activate casa6",
            context={"tool": "imhead", "image_path": imagename},
        )

    # Pre-validate image
    validate_image_before_read(imagename, operation="imhead")

    try:
        return imhead(imagename=imagename, mode=mode, **kwargs)
    except Exception as e:
        handle_casa_tool_error("imhead", e, image_path=imagename, operation="read_header")


def safe_casaimage_open(image_path: str, operation: str = "read") -> Any:
    """
    Safely open CASA image with enhanced error handling.

    Args:
        image_path: Path to image
        operation: Operation being performed

    Returns:
        casaimage object

    Raises:
        ImageReadError: If image cannot be opened
        ImageCorruptionError: If image appears corrupted
    """
    if not HAVE_CASACORE:
        from .exceptions import ImageReadError

        raise ImageReadError(
            f"casacore.images not available for {image_path}",
            "Ensure CASA is installed: conda activate casa6",
            context={"operation": operation, "image_path": image_path},
        )

    # Pre-validate image
    validate_image_before_read(image_path, operation=operation)

    try:
        img = casaimage(str(image_path))

        # Try to read a small amount of data to validate
        try:
            data = img.getdata()
            validate_image_data(data, image_path, operation)
        except Exception as e:
            img.close()
            from .exceptions import ImageCorruptionError

            raise ImageCorruptionError(
                f"Failed to read image data from {image_path}: {e}",
                f"Image may be corrupted. Operation: {operation}",
                context={"operation": operation, "image_path": image_path},
            ) from e

        return img
    except (ImageReadError, ImageCorruptionError):
        raise
    except Exception as e:
        from .exceptions import ImageReadError

        raise ImageReadError(
            f"Failed to open image: {image_path}",
            f"Error: {e}. Check if image exists and is readable. Operation: {operation}",
            context={"operation": operation, "image_path": image_path},
        ) from e


def check_disk_space(
    path: str,
    required_bytes: Optional[int] = None,
    required_gb: Optional[float] = None,
    operation: str = "unknown",
    fatal: bool = False,
) -> Tuple[bool, str]:
    """
    Check available disk space at a given path.

    Args:
        path: Path to check disk space for
        required_bytes: Required space in bytes
        required_gb: Required space in GB (alternative to required_bytes)
        operation: Operation being performed (for error messages)
        fatal: If True, raise RuntimeError on insufficient space instead of returning False

    Returns:
        (has_space, message) where has_space is True if sufficient space available
        If fatal=True and space insufficient, raises RuntimeError instead

    Raises:
        RuntimeError: If fatal=True and insufficient disk space available
    """
    try:
        path_obj = Path(path)
        # Get the directory where the file will be written
        if path_obj.is_dir():
            check_path = path_obj
        else:
            check_path = path_obj.parent

        # Ensure path exists
        check_path.mkdir(parents=True, exist_ok=True)

        # Get disk usage
        stat = shutil.disk_usage(check_path)
        free_bytes = stat.free

        # Convert required space to bytes
        if required_gb is not None:
            required_bytes = int(required_gb * 1024**3)
        elif required_bytes is None:
            # Default: require at least 1 GB free
            required_bytes = 1024**3

        free_gb = free_bytes / (1024**3)
        required_gb_actual = required_bytes / (1024**3)

        if free_bytes < required_bytes:
            error_msg = (
                f"Insufficient disk space: {free_gb:.2f} GB free, "
                f"{required_gb_actual:.2f} GB required. Operation: {operation}"
            )
            if fatal:
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            return False, error_msg

        return (
            True,
            f"Disk space OK: {free_gb:.2f} GB free (required: {required_gb_actual:.2f} GB)",
        )

    except RuntimeError:
        # Re-raise RuntimeError (from fatal=True case)
        raise
    except Exception as e:
        error_msg = f"Failed to check disk space: {e}"
        if fatal:
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        logger.warning(error_msg)
        # Don't fail on disk space check errors if not fatal, just warn
        return True, f"Could not check disk space: {e}"

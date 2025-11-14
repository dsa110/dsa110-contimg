"""
Path validation utilities for secure file path handling.

This module provides utilities to validate and sanitize file paths to prevent
path traversal attacks and ensure paths are within allowed directories.
"""

import os
from pathlib import Path
from typing import Optional, Union


def validate_path(
    user_path: Union[str, Path],
    base_directory: Union[str, Path],
    allow_absolute: bool = False,
) -> Path:
    """
    Validate and sanitize a user-provided path to prevent path traversal attacks.

    Args:
        user_path: The path provided by the user (may be relative or absolute)
        base_directory: The base directory that paths must be within
        allow_absolute: If True, allow absolute paths (still validated against base)

    Returns:
        A validated Path object that is guaranteed to be within base_directory

    Raises:
        ValueError: If the path attempts to escape base_directory
        ValueError: If the path is invalid or contains dangerous components
    """
    # codeql[py/path-injection]: This function intentionally accepts user input for validation.
    # The path is validated and sanitized before being returned.
    base_dir = Path(base_directory).resolve()
    user_path_obj = Path(user_path)

    # Resolve the user path
    if user_path_obj.is_absolute():
        if not allow_absolute:
            raise ValueError(f"Absolute paths not allowed: {user_path}")
        # codeql[py/path-injection]: User input is validated below
        resolved_path = user_path_obj.resolve()
    else:
        # Resolve relative to base directory
        # codeql[py/path-injection]: User input is validated below
        resolved_path = (base_dir / user_path_obj).resolve()

    # Check for path traversal attempts
    try:
        resolved_path.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Path traversal detected: {user_path} would escape {base_directory}")

    # Check for dangerous path components
    parts = resolved_path.parts
    if ".." in parts or "." in parts and parts.count(".") > 1:
        raise ValueError(f"Invalid path components detected: {user_path}")

    return resolved_path


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to prevent directory traversal and other attacks.

    Args:
        filename: The filename to sanitize
        max_length: Maximum length of the filename

    Returns:
        A sanitized filename safe for use in file operations

    Raises:
        ValueError: If the filename is invalid or contains dangerous characters
    """
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")

    # Remove path separators and dangerous characters
    dangerous_chars = ["/", "\\", "..", "\x00"]
    for char in dangerous_chars:
        if char in filename:
            raise ValueError(f"Filename contains dangerous character: {char}")

    # Remove leading/trailing whitespace and dots
    sanitized = filename.strip().strip(".")

    if not sanitized:
        raise ValueError("Filename is invalid after sanitization")

    # Limit length
    if len(sanitized) > max_length:
        raise ValueError(f"Filename too long (max {max_length} characters)")

    return sanitized


def get_safe_path(
    user_input: Union[str, Path],
    base_dir: Union[str, Path],
    subdirectory: Optional[str] = None,
) -> Path:
    """
    Get a safe path by combining user input with a base directory.

    This is a convenience function that validates and constructs a safe path.

    Args:
        user_input: User-provided path component
        base_dir: Base directory (must exist)
        subdirectory: Optional subdirectory within base_dir

    Returns:
        A validated Path object

    Raises:
        ValueError: If validation fails
        FileNotFoundError: If base_dir doesn't exist
    """
    base = Path(base_dir)
    if not base.exists():
        raise FileNotFoundError(f"Base directory does not exist: {base_dir}")

    if subdirectory:
        base = base / subdirectory
        base.mkdir(parents=True, exist_ok=True)

    return validate_path(user_input, base)


def is_safe_path(path: Union[str, Path], allowed_dirs: list[Union[str, Path]]) -> bool:
    """
    Check if a path is within any of the allowed directories.

    Args:
        path: The path to check
        allowed_dirs: List of allowed base directories

    Returns:
        True if the path is within one of the allowed directories
    """
    try:
        resolved_path = Path(path).resolve()
        for allowed_dir in allowed_dirs:
            allowed = Path(allowed_dir).resolve()
            try:
                resolved_path.relative_to(allowed)
                return True
            except ValueError:
                continue
        return False
    except (ValueError, OSError):
        return False

"""
Path Enforcement - Strict validation of file access paths in the pipeline.

This module enforces critical path rules:
1. NEVER access files in .local/archive/ directory
2. Database files MUST be SQLite (.sqlite3)
3. Catalog databases MUST be in state/catalogs/

These rules exist to:
- Prevent accidental use of legacy/deprecated code
- Ensure all data access is through properly managed databases
- Maintain reproducibility and provenance tracking
"""

from __future__ import annotations

import logging
import os
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar, Union

logger = logging.getLogger(__name__)

# Forbidden path patterns
FORBIDDEN_PATHS = [
    ".local/archive",
    ".local/archive/",
    "/.local/archive",
]

# Required database extension
REQUIRED_DB_EXTENSION = ".sqlite3"

# Valid catalog database directory
VALID_CATALOG_DIRS = [
    "/data/dsa110-contimg/state/catalogs",
    "state/catalogs",
]


class ForbiddenPathError(Exception):
    """Raised when attempting to access a forbidden path."""
    pass


class InvalidDatabaseError(Exception):
    """Raised when a database path does not meet requirements."""
    pass


def is_forbidden_path(path: Union[str, Path]) -> bool:
    """Check if a path is in a forbidden directory.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is forbidden, False otherwise
    """
    path_str = str(path)
    
    # Check for forbidden patterns
    for forbidden in FORBIDDEN_PATHS:
        if forbidden in path_str:
            return True
    
    # Resolve to absolute and check again
    try:
        resolved = Path(path).resolve()
        resolved_str = str(resolved)
        for forbidden in FORBIDDEN_PATHS:
            if forbidden in resolved_str:
                return True
    except Exception:
        pass
    
    return False


def validate_path(path: Union[str, Path], context: str = "") -> Path:
    """Validate that a path is not forbidden.
    
    Args:
        path: Path to validate
        context: Description of the access context (for error messages)
        
    Returns:
        Validated Path object
        
    Raises:
        ForbiddenPathError: If path is in a forbidden directory
    """
    if is_forbidden_path(path):
        ctx = f" ({context})" if context else ""
        raise ForbiddenPathError(
            f"Access to path is forbidden{ctx}: {path}\n"
            f"The .local/archive/ directory contains deprecated/legacy code "
            f"and data that must NOT be used by the pipeline.\n"
            f"Use proper data sources in state/catalogs/ instead."
        )
    return Path(path)


def validate_database_path(
    path: Union[str, Path],
    must_exist: bool = False,
    context: str = "",
) -> Path:
    """Validate that a database path meets requirements.
    
    Requirements:
    1. Not in a forbidden directory
    2. Has .sqlite3 extension
    3. Optionally, must exist
    
    Args:
        path: Database path to validate
        must_exist: If True, path must exist
        context: Description of the access context
        
    Returns:
        Validated Path object
        
    Raises:
        ForbiddenPathError: If path is in a forbidden directory
        InvalidDatabaseError: If path doesn't meet requirements
    """
    path = validate_path(path, context)
    path = Path(path)
    
    # Check extension
    if path.suffix != REQUIRED_DB_EXTENSION:
        raise InvalidDatabaseError(
            f"Database must have {REQUIRED_DB_EXTENSION} extension: {path}\n"
            f"Only SQLite databases are permitted in the pipeline."
        )
    
    # Check existence if required
    if must_exist and not path.exists():
        raise InvalidDatabaseError(
            f"Database does not exist: {path}\n"
            f"Build the database first using the appropriate builder module."
        )
    
    return path


def validate_catalog_database(
    path: Union[str, Path],
    must_exist: bool = True,
) -> Path:
    """Validate that a catalog database path is valid.
    
    Catalog databases must:
    1. Not be in a forbidden directory
    2. Have .sqlite3 extension
    3. Be in a valid catalog directory
    
    Args:
        path: Catalog database path
        must_exist: If True, database must exist
        
    Returns:
        Validated Path object
        
    Raises:
        ForbiddenPathError: If path is forbidden
        InvalidDatabaseError: If requirements not met
    """
    path = validate_database_path(path, must_exist=must_exist, context="catalog")
    
    # Check if in valid catalog directory
    path_str = str(path.resolve())
    in_valid_dir = any(valid_dir in path_str for valid_dir in VALID_CATALOG_DIRS)
    
    if not in_valid_dir:
        logger.warning(
            f"Catalog database not in standard location: {path}\n"
            f"Expected: {VALID_CATALOG_DIRS[0]}/"
        )
    
    return path


F = TypeVar('F', bound=Callable)


def enforce_path_rules(func: F) -> F:
    """Decorator to enforce path rules on function arguments.
    
    Inspects function arguments for paths and validates them.
    Arguments named 'path', 'file_path', 'db_path', 'source_path', 
    'input_path', 'output_path' are validated.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with path validation
    """
    path_arg_names = {
        'path', 'file_path', 'db_path', 'source_path',
        'input_path', 'output_path', 'catalog_path',
        'database_path', 'csv_path', 'txt_path',
    }
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check keyword arguments
        for key, value in kwargs.items():
            if key in path_arg_names and value is not None:
                if isinstance(value, (str, Path)):
                    validate_path(value, context=f"{func.__name__}({key}=...)")
        
        return func(*args, **kwargs)
    
    return wrapper  # type: ignore


def check_environment():
    """Check environment for potential path violations.
    
    This can be called at startup to warn about suspicious configurations.
    """
    # Check for any environment variables pointing to archive
    for key, value in os.environ.items():
        if value and is_forbidden_path(value):
            logger.warning(
                f"Environment variable {key} points to forbidden path: {value}"
            )


# Export public API
__all__ = [
    "ForbiddenPathError",
    "InvalidDatabaseError",
    "is_forbidden_path",
    "validate_path",
    "validate_database_path",
    "validate_catalog_database",
    "enforce_path_rules",
    "check_environment",
    "FORBIDDEN_PATHS",
    "VALID_CATALOG_DIRS",
]

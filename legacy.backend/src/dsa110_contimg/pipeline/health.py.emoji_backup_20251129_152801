"""
Health check utilities for pipeline execution.

Provides pre-flight health checks before starting expensive operations.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    """Raised when health check fails."""

    pass


def check_disk_space(path: Path, required_gb: float) -> Tuple[bool, str]:
    """Check if sufficient disk space is available.

    Args:
        path: Path to check disk space for
        required_gb: Required space in GB

    Returns:
        (has_space, message) tuple
    """
    try:
        free_bytes = shutil.disk_usage(path).free
        free_gb = free_bytes / (1024**3)
        has_space = free_gb >= required_gb

        if has_space:
            return (
                True,
                f"Sufficient disk space: {free_gb:.1f}GB available (need {required_gb:.1f}GB)",
            )
        else:
            return (
                False,
                f"Insufficient disk space: {free_gb:.1f}GB available (need {required_gb:.1f}GB)",
            )
    except Exception as e:
        return False, f"Cannot check disk space: {e}"


def check_directory_writable(path: Path) -> Tuple[bool, str]:
    """Check if directory is writable.

    Args:
        path: Path to check

    Returns:
        (is_writable, message) tuple
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".health_check_test"
        test_file.write_text("test")
        test_file.unlink()
        return True, f"Directory is writable: {path}"
    except Exception as e:
        return False, f"Directory not writable: {path} ({e})"


def check_database_accessible(db_path: Path) -> Tuple[bool, str]:
    """Check if database is accessible.

    Args:
        db_path: Path to database

    Returns:
        (is_accessible, message) tuple
    """
    try:
        import sqlite3

        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.execute("SELECT 1")
        conn.close()
        return True, f"Database accessible: {db_path}"
    except Exception as e:
        return False, f"Database not accessible: {db_path} ({e})"


def check_system_resources(
    min_memory_gb: float = 4.0,
    min_disk_gb: float = 10.0,
    check_paths: List[Path] = None,
) -> Tuple[bool, List[str]]:
    """Perform comprehensive system health check.

    Args:
        min_memory_gb: Minimum required memory in GB
        min_disk_gb: Minimum required disk space in GB
        check_paths: Optional list of paths to check disk space for

    Returns:
        (is_healthy, issues) tuple where issues is a list of problem descriptions
    """
    issues = []

    # Check memory
    try:
        import psutil

        mem = psutil.virtual_memory()
        mem_gb = mem.total / (1024**3)
        if mem_gb < min_memory_gb:
            issues.append(
                f"Insufficient memory: {mem_gb:.1f}GB available (need {min_memory_gb:.1f}GB)"
            )
    except ImportError:
        logger.warning("psutil not available, skipping memory check")
    except Exception as e:
        issues.append(f"Cannot check memory: {e}")

    # Check disk space for root and specified paths
    paths_to_check = [Path("/")]
    if check_paths:
        paths_to_check.extend(check_paths)

    for path in paths_to_check:
        has_space, msg = check_disk_space(path, min_disk_gb)
        if not has_space:
            issues.append(msg)

    return len(issues) == 0, issues


def validate_pipeline_health(
    config,
    required_disk_gb: float = 50.0,
) -> None:
    """Validate pipeline health before execution.

    Performs comprehensive health checks:
    - Disk space availability
    - Directory writability
    - Database accessibility
    - System resources

    Args:
        config: PipelineConfig instance
        required_disk_gb: Required disk space in GB

    Raises:
        HealthCheckError: If health check fails
    """
    issues = []

    # Check input directory exists and is readable
    if not config.paths.input_dir.exists():
        issues.append(f"Input directory does not exist: {config.paths.input_dir}")
    elif not os.access(config.paths.input_dir, os.R_OK):
        issues.append(f"Input directory not readable: {config.paths.input_dir}")

    # Check output directory is writable
    is_writable, msg = check_directory_writable(config.paths.output_dir.parent)
    if not is_writable:
        issues.append(msg)

    # Check scratch directory if specified
    if config.paths.scratch_dir:
        is_writable, msg = check_directory_writable(config.paths.scratch_dir)
        if not is_writable:
            issues.append(msg)

    # Check state directory and databases
    state_dir = config.paths.state_dir
    state_dir.mkdir(parents=True, exist_ok=True)

    products_db = config.paths.products_db
    is_accessible, msg = check_database_accessible(products_db)
    if not is_accessible:
        issues.append(msg)

    registry_db = config.paths.registry_db
    is_accessible, msg = check_database_accessible(registry_db)
    if not is_accessible:
        issues.append(msg)

    # Check system resources
    check_paths = [config.paths.output_dir.parent]
    if config.paths.scratch_dir:
        check_paths.append(config.paths.scratch_dir)

    is_healthy, resource_issues = check_system_resources(
        min_disk_gb=required_disk_gb,
        check_paths=check_paths,
    )
    issues.extend(resource_issues)

    if issues:
        error_msg = "Pipeline health check failed:\n" + "\n".join(
            f"  - {issue}" for issue in issues
        )
        logger.error(error_msg)
        raise HealthCheckError(error_msg)

    logger.info("✓ Pipeline health check passed")

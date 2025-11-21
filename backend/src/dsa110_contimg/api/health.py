"""Health checks and readiness probes for API endpoints.

Provides health check endpoints for Kubernetes readiness/liveness probes
and general system health monitoring.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter

router = APIRouter()


def _check_database(db_path: Path, timeout: float = 1.0) -> tuple[bool, Optional[str]]:
    """Check database connectivity."""
    try:
        conn = sqlite3.connect(str(db_path), timeout=timeout)
        # Try a simple query
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


def _check_disk_space(path: Path, min_free_gb: float = 1.0) -> tuple[bool, Optional[str]]:
    """Check disk space availability."""
    try:
        import shutil

        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024**3)
        if free_gb < min_free_gb:
            return (
                False,
                f"Insufficient disk space: {free_gb:.2f} GB free (need {min_free_gb} GB)",
            )
        return True, None
    except Exception as e:
        return False, f"Cannot check disk space: {e}"


def _check_calibration_registry() -> tuple[bool, Optional[str]]:
    """Check calibration registry accessibility."""
    registry_path = Path(os.getenv("CAL_REGISTRY_DB", "state/cal_registry.sqlite3"))
    if not registry_path.exists():
        return False, f"Calibration registry not found: {registry_path}"
    return _check_database(registry_path)


def _check_products_database() -> tuple[bool, Optional[str]]:
    """Check products database accessibility."""
    products_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
    return _check_database(products_path)


def _check_master_sources_database() -> tuple[bool, Optional[str]]:
    """Check master sources database accessibility."""
    products_db = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
    master_sources_path = products_db.parent / "master_sources.sqlite3"
    if not master_sources_path.exists():
        return False, f"Master sources database not found: {master_sources_path}"
    return _check_database(master_sources_path)


def _check_casa_wrapper_config() -> tuple[bool, Optional[str], Optional[Dict[str, str]]]:
    """Check if casa_wrapper.sh location matches expected path from environment.

    The CASA wrapper script ensures CASA logs are written to state/logs/ instead of
    the current working directory. This prevents log pollution in execution contexts
    and enables centralized log management.

    Reads from environment variable or falls back to reading contimg.env file.

    Returns:
        Tuple of (healthy, error_message, details_dict)
    """
    # Try environment variable first
    expected_path = os.getenv("CONTIMG_CASA_WRAPPER")

    # If not in environment, try reading from contimg.env file
    if not expected_path:
        env_file = Path("/data/dsa110-contimg/ops/systemd/contimg.env")
        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("CONTIMG_CASA_WRAPPER=") and not line.startswith("#"):
                            expected_path = line.split("=", 1)[1].strip()
                            # Remove quotes if present
                            expected_path = expected_path.strip("\"'")
                            break
            except Exception as e:
                return (
                    False,
                    f"Error reading contimg.env: {e}",
                    {"error_type": "file_read"},
                )

    if not expected_path:
        return True, None, {"note": "CONTIMG_CASA_WRAPPER not configured"}

    expected = Path(expected_path)
    if not expected.exists():
        return (
            False,
            f"Expected casa_wrapper.sh not found: {expected_path}",
            {"expected": str(expected_path), "exists": False},
        )

    if not os.access(expected, os.X_OK):
        return (
            False,
            f"casa_wrapper.sh is not executable: {expected_path}",
            {"expected": str(expected_path), "executable": False},
        )

    return (
        True,
        None,
        {"expected": str(expected_path), "exists": True, "executable": True},
    )


@router.get("/health/liveness")
def liveness_check():
    """Liveness probe - indicates service is running."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health/readiness")
def readiness_check():
    """Readiness probe - indicates service is ready to accept requests."""
    checks: Dict[str, Dict[str, any]] = {}
    all_healthy = True

    # Check products database
    healthy, error = _check_products_database()
    checks["products_database"] = {"healthy": healthy, "error": error}
    if not healthy:
        all_healthy = False

    # Check calibration registry
    healthy, error = _check_calibration_registry()
    checks["calibration_registry"] = {"healthy": healthy, "error": error}
    if not healthy:
        all_healthy = False

    # Check disk space
    data_dir = Path(os.getenv("PIPELINE_DATA_DIR", "/stage/dsa110-contimg"))
    healthy, error = _check_disk_space(data_dir)
    checks["disk_space"] = {"healthy": healthy, "error": error}
    if not healthy:
        all_healthy = False

    # System configuration check (casa_wrapper path)
    healthy, error, details = _check_casa_wrapper_config()
    checks["system_config"] = {"healthy": healthy, "error": error, **details}
    if not healthy:
        all_healthy = False

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": time.time(),
    }


@router.get("/health/startup")
def startup_check():
    """Startup probe - indicates service has finished starting."""
    # Same as readiness for now
    return readiness_check()


@router.get("/health/detailed")
def detailed_health_check():
    """Detailed health check with all components."""
    checks: Dict[str, Dict[str, any]] = {}
    all_healthy = True

    # Database checks
    healthy, error = _check_products_database()
    checks["products_database"] = {
        "healthy": healthy,
        "error": error,
        "type": "database",
    }

    healthy, error = _check_calibration_registry()
    checks["calibration_registry"] = {
        "healthy": healthy,
        "error": error,
        "type": "database",
    }

    healthy, error = _check_master_sources_database()
    checks["master_sources_database"] = {
        "healthy": healthy,
        "error": error,
        "type": "database",
    }

    # Disk space check
    data_dir = Path(os.getenv("PIPELINE_DATA_DIR", "/stage/dsa110-contimg"))
    healthy, error = _check_disk_space(data_dir)
    checks["disk_space"] = {"healthy": healthy, "error": error, "type": "resource"}

    # System configuration check (casa_wrapper path)
    healthy, error, details = _check_casa_wrapper_config()
    checks["system_config"] = {
        "healthy": healthy,
        "error": error,
        "type": "configuration",
        **details,
    }
    if not healthy:
        all_healthy = False

    # Memory check (if psutil available)
    try:
        import psutil

        process = psutil.Process()
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()
        checks["memory"] = {
            "healthy": mem_percent < 90.0,
            "memory_mb": mem_info.rss / (1024**2),
            "memory_percent": mem_percent,
            "type": "resource",
        }
    except ImportError:
        checks["memory"] = {
            "healthy": True,
            "error": "psutil not available",
            "type": "resource",
        }

    all_healthy = all(c["healthy"] for c in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": time.time(),
    }


@router.get("/health/ese-detection")
def ese_detection_health():
    """Health check specifically for ESE detection system."""
    checks: Dict[str, Dict[str, any]] = {}

    # Check products database
    healthy, error = _check_products_database()
    checks["database_accessible"] = {"healthy": healthy, "error": error}

    # Check if tables exist
    products_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
    if products_path.exists():
        try:
            conn = sqlite3.connect(str(products_path), timeout=1.0)
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('variability_stats', 'ese_candidates', 'photometry')
            """
            )
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            checks["variability_stats_table"] = {
                "healthy": "variability_stats" in tables,
                "exists": "variability_stats" in tables,
            }
            checks["ese_candidates_table"] = {
                "healthy": "ese_candidates" in tables,
                "exists": "ese_candidates" in tables,
            }
            checks["photometry_table"] = {
                "healthy": "photometry" in tables,
                "exists": "photometry" in tables,
            }
        except Exception as e:
            checks["table_check"] = {"healthy": False, "error": str(e)}
    else:
        checks["table_check"] = {
            "healthy": False,
            "error": "Products database not found",
        }

    all_healthy = all(c.get("healthy", False) for c in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": time.time(),
    }


@router.get("/api/health/summary")
def health_summary():
    """Get a summary of all health checks for dashboard display."""
    from dsa110_contimg.pipeline.circuit_breaker import (
        calibration_solve_circuit_breaker,
        ese_detection_circuit_breaker,
        photometry_circuit_breaker,
    )
    from dsa110_contimg.pipeline.dead_letter_queue import get_dlq

    # Get detailed health
    detailed = detailed_health_check()

    # Get DLQ stats
    dlq = get_dlq()
    dlq_stats = dlq.get_stats()

    # Get circuit breaker states
    circuit_breakers = [
        {
            "name": "ese_detection",
            "state": ese_detection_circuit_breaker.state.value,
            "failure_count": ese_detection_circuit_breaker.failure_count,
        },
        {
            "name": "calibration_solve",
            "state": calibration_solve_circuit_breaker.state.value,
            "failure_count": calibration_solve_circuit_breaker.failure_count,
        },
        {
            "name": "photometry",
            "state": photometry_circuit_breaker.state.value,
            "failure_count": photometry_circuit_breaker.failure_count,
        },
    ]

    # Determine overall status
    all_checks_healthy = all(c.get("healthy", False) for c in detailed["checks"].values())
    has_open_circuits = any(cb["state"] == "open" for cb in circuit_breakers)
    has_pending_dlq = dlq_stats["pending"] > 0

    overall_status = "healthy"
    if not all_checks_healthy or has_open_circuits or has_pending_dlq:
        overall_status = "degraded"
    if has_open_circuits and has_pending_dlq:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "checks": detailed["checks"],
        "circuit_breakers": circuit_breakers,
        "dlq_stats": {
            "total": dlq_stats["total"],
            "pending": dlq_stats["pending"],
            "retrying": dlq_stats["retrying"],
            "resolved": dlq_stats["resolved"],
            "failed": dlq_stats["failed"],
        },
    }

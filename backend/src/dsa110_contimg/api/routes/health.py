"""
Unified Health Dashboard API routes.

Provides comprehensive health monitoring for:
- Docker containers
- Systemd services
- HTTP endpoints
- Database connectivity
- Pipeline-specific services
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


# ============================================================================
# Pydantic Models
# ============================================================================


class ServiceHealthStatus(BaseModel):
    """Health status of a single service."""

    name: str
    status: str  # running, stopped, degraded, error, unknown
    message: str = ""
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: str = ""


class HealthSummary(BaseModel):
    """Summary of all health checks."""

    total: int
    running: int
    stopped: int
    degraded: int
    error: int


class SystemHealthReport(BaseModel):
    """Complete system health report."""

    overall_status: str
    services: List[ServiceHealthStatus]
    docker_available: bool = False
    systemd_available: bool = False
    summary: HealthSummary
    checked_at: str
    check_duration_ms: float


class ValidityWindowInfo(BaseModel):
    """Information about a calibration validity window."""

    set_name: str
    table_type: str
    path: str
    valid_start_mjd: Optional[float]
    valid_end_mjd: Optional[float]
    cal_field: Optional[str]
    refant: Optional[str]
    status: str
    created_at: float


class ActiveValidityWindows(BaseModel):
    """Active validity windows response."""

    query_mjd: float
    query_iso: str
    active_sets: List[Dict[str, Any]]
    total_active_tables: int
    overlapping_sets: int


class FluxMonitoringStatus(BaseModel):
    """Flux monitoring status for a calibrator."""

    calibrator_name: str
    n_measurements: int
    latest_mjd: Optional[float]
    latest_flux_ratio: Optional[float]
    mean_flux_ratio: Optional[float]
    flux_ratio_std: Optional[float]
    is_stable: bool
    alerts_count: int


# ============================================================================
# Default Service Configurations
# ============================================================================

DEFAULT_DOCKER_CONTAINERS = [
    "dsa110-api",
    "dsa110-redis",
    "contimg-stream",
    "ragflow-ragflow-1",
    "ragflow-elasticsearch01-1",
    "ragflow-redis-1",
]

DEFAULT_SYSTEMD_SERVICES = [
    "contimg-api.service",
    "contimg-stream.service",
    "absurd-worker.service",
    "absurd-scheduler.service",
    "contimg-pointing.service",
]

DEFAULT_HTTP_ENDPOINTS = {
    "api": "http://localhost:8000/api/status",
    "grafana": "http://localhost:3030/api/health",
    "frontend": "http://localhost:3000/",
}


# ============================================================================
# Health Check Endpoints
# ============================================================================


@router.get("/system", response_model=SystemHealthReport)
async def get_system_health(
    include_docker: bool = Query(True, description="Check Docker containers"),
    include_systemd: bool = Query(True, description="Check systemd services"),
    include_http: bool = Query(True, description="Check HTTP endpoints"),
    docker_containers: Optional[str] = Query(
        None, description="Comma-separated container names"
    ),
    systemd_services: Optional[str] = Query(
        None, description="Comma-separated service names"
    ),
) -> SystemHealthReport:
    """
    Get comprehensive system health status.

    Checks all infrastructure components and returns aggregated health report.
    """
    from dsa110_contimg.monitoring.service_health import (
        check_system_health,
        ServiceStatus,
    )

    # Parse custom lists or use defaults
    containers = (
        docker_containers.split(",") if docker_containers else DEFAULT_DOCKER_CONTAINERS
    )
    services = (
        systemd_services.split(",") if systemd_services else DEFAULT_SYSTEMD_SERVICES
    )

    report = await check_system_health(
        docker_containers=containers if include_docker else None,
        systemd_services=services if include_systemd else None,
        http_endpoints=DEFAULT_HTTP_ENDPOINTS if include_http else None,
    )

    # Convert to Pydantic models
    service_list = [
        ServiceHealthStatus(
            name=s.name,
            status=s.status.value,
            message=s.message,
            response_time_ms=s.response_time_ms,
            details=s.details,
            checked_at=s.checked_at,
        )
        for s in report.services
    ]

    summary = HealthSummary(
        total=len(report.services),
        running=sum(1 for s in report.services if s.status == ServiceStatus.RUNNING),
        stopped=sum(1 for s in report.services if s.status == ServiceStatus.STOPPED),
        degraded=sum(1 for s in report.services if s.status == ServiceStatus.DEGRADED),
        error=sum(1 for s in report.services if s.status == ServiceStatus.ERROR),
    )

    return SystemHealthReport(
        overall_status=report.overall_status.value,
        services=service_list,
        docker_available=report.docker_available,
        systemd_available=report.systemd_available,
        summary=summary,
        checked_at=report.checked_at,
        check_duration_ms=report.check_duration_ms,
    )


@router.get("/docker/{container_name}")
async def check_docker_container(container_name: str) -> ServiceHealthStatus:
    """Check health of a specific Docker container."""
    from dsa110_contimg.monitoring.service_health import check_docker_container as check

    result = check(container_name)
    return ServiceHealthStatus(
        name=result.name,
        status=result.status.value,
        message=result.message,
        response_time_ms=result.response_time_ms,
        details=result.details,
        checked_at=result.checked_at,
    )


@router.get("/systemd/{service_name}")
async def check_systemd_service(service_name: str) -> ServiceHealthStatus:
    """Check health of a specific systemd service."""
    from dsa110_contimg.monitoring.service_health import (
        check_systemd_service as check,
    )

    result = check(service_name)
    return ServiceHealthStatus(
        name=result.name,
        status=result.status.value,
        message=result.message,
        response_time_ms=result.response_time_ms,
        details=result.details,
        checked_at=result.checked_at,
    )


@router.get("/databases")
async def check_database_health() -> Dict[str, Any]:
    """Check health of all pipeline databases.

    Note: All domains are now unified in pipeline.sqlite3.
    Legacy database names are shown for backward compatibility monitoring.
    """
    import os
    import sqlite3
    import time
    from pathlib import Path

    # Unified database path (Phase 2 consolidation)
    unified_db = os.environ.get(
        "PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3"
    )

    # Check unified database with domain labels for clarity
    databases = {
        "pipeline": unified_db,
        # Legacy aliases (all point to same unified database)
        "products": unified_db,
        "cal_registry": unified_db,
        "hdf5_index": unified_db,
        "ingest": unified_db,
    }

    results = []
    for name, path in databases.items():
        start = time.time()
        try:
            if not os.path.exists(path):
                results.append(
                    {
                        "name": name,
                        "path": path,
                        "status": "missing",
                        "message": "Database file not found",
                    }
                )
                continue

            conn = sqlite3.connect(path, timeout=5.0)
            conn.execute("SELECT 1")
            response_ms = (time.time() - start) * 1000

            # Get file size
            size_mb = os.path.getsize(path) / (1024 * 1024)

            conn.close()
            results.append(
                {
                    "name": name,
                    "path": path,
                    "status": "healthy",
                    "response_time_ms": round(response_ms, 2),
                    "size_mb": round(size_mb, 2),
                }
            )
        except Exception as e:
            results.append(
                {
                    "name": name,
                    "path": path,
                    "status": "error",
                    "message": str(e),
                }
            )

    healthy_count = sum(1 for r in results if r["status"] == "healthy")
    return {
        "databases": results,
        "summary": {
            "total": len(results),
            "healthy": healthy_count,
            "unhealthy": len(results) - healthy_count,
        },
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }


# ============================================================================
# Validity Window Endpoints
# ============================================================================


@router.get("/validity-windows", response_model=ActiveValidityWindows)
async def get_active_validity_windows(
    mjd: Optional[float] = Query(None, description="Query MJD (default: now)"),
) -> ActiveValidityWindows:
    """
    Get active calibration validity windows for a given time.

    Returns all calibration sets whose validity windows include the query time.
    """
    import sqlite3
    from pathlib import Path

    from astropy.time import Time

    if mjd is None:
        mjd = Time.now().mjd

    query_time = Time(mjd, format="mjd")
    # Unified database path (Phase 2 consolidation)
    registry_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    if not registry_path.exists():
        return ActiveValidityWindows(
            query_mjd=mjd,
            query_iso=query_time.isot,
            active_sets=[],
            total_active_tables=0,
            overlapping_sets=0,
        )

    conn = sqlite3.connect(str(registry_path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Get all active tables with validity windows covering the query time
    rows = conn.execute(
        """
        SELECT set_name, path, table_type, order_index, cal_field, refant,
               valid_start_mjd, valid_end_mjd, status, created_at
        FROM caltables
        WHERE status = 'active'
          AND (valid_start_mjd IS NULL OR valid_start_mjd <= ?)
          AND (valid_end_mjd IS NULL OR valid_end_mjd >= ?)
        ORDER BY set_name, order_index
        """,
        (mjd, mjd),
    ).fetchall()

    conn.close()

    # Group by set_name
    sets_dict: Dict[str, List[Dict]] = {}
    for row in rows:
        set_name = row["set_name"]
        if set_name not in sets_dict:
            sets_dict[set_name] = []
        sets_dict[set_name].append(
            {
                "path": row["path"],
                "table_type": row["table_type"],
                "order_index": row["order_index"],
                "cal_field": row["cal_field"],
                "refant": row["refant"],
                "valid_start_mjd": row["valid_start_mjd"],
                "valid_end_mjd": row["valid_end_mjd"],
                "valid_start_iso": (
                    Time(row["valid_start_mjd"], format="mjd").isot
                    if row["valid_start_mjd"]
                    else None
                ),
                "valid_end_iso": (
                    Time(row["valid_end_mjd"], format="mjd").isot
                    if row["valid_end_mjd"]
                    else None
                ),
            }
        )

    active_sets = [
        {
            "set_name": name,
            "tables": tables,
            "table_count": len(tables),
        }
        for name, tables in sets_dict.items()
    ]

    return ActiveValidityWindows(
        query_mjd=mjd,
        query_iso=query_time.isot,
        active_sets=active_sets,
        total_active_tables=len(rows),
        overlapping_sets=len(sets_dict),
    )


@router.get("/validity-windows/timeline")
async def get_validity_window_timeline(
    days_back: int = Query(7, description="Days to look back"),
    days_forward: int = Query(1, description="Days to look forward"),
) -> Dict[str, Any]:
    """
    Get timeline of validity windows for visualization.

    Returns validity windows suitable for Gantt-chart style visualization.
    """
    import sqlite3
    from pathlib import Path

    from astropy.time import Time

    now = Time.now()
    start_mjd = now.mjd - days_back
    end_mjd = now.mjd + days_forward

    # Unified database path (Phase 2 consolidation)
    registry_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    if not registry_path.exists():
        return {
            "timeline_start": Time(start_mjd, format="mjd").isot,
            "timeline_end": Time(end_mjd, format="mjd").isot,
            "current_time": now.isot,
            "windows": [],
        }

    conn = sqlite3.connect(str(registry_path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Ensure the consolidated caltables exist before querying
    table_exists = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='caltables'
        """
    ).fetchone()

    if not table_exists:
        conn.close()
        return {
            "timeline_start": Time(start_mjd, format="mjd").isot,
            "timeline_end": Time(end_mjd, format="mjd").isot,
            "current_time": now.isot,
            "current_mjd": now.mjd,
            "windows": [],
            "message": "caltables table not initialized",
        }

    # Get all windows that overlap with timeline
    rows = conn.execute(
        """
        SELECT set_name, table_type, cal_field, refant,
               valid_start_mjd, valid_end_mjd, created_at
        FROM caltables
        WHERE status = 'active'
          AND valid_start_mjd IS NOT NULL
          AND valid_end_mjd IS NOT NULL
          AND valid_end_mjd >= ?
          AND valid_start_mjd <= ?
        ORDER BY valid_start_mjd
        """,
        (start_mjd, end_mjd),
    ).fetchall()

    conn.close()

    windows = []
    for row in rows:
        windows.append(
            {
                "set_name": row["set_name"],
                "table_type": row["table_type"],
                "cal_field": row["cal_field"],
                "refant": row["refant"],
                "start_mjd": row["valid_start_mjd"],
                "end_mjd": row["valid_end_mjd"],
                "start_iso": Time(row["valid_start_mjd"], format="mjd").isot,
                "end_iso": Time(row["valid_end_mjd"], format="mjd").isot,
                "duration_hours": (row["valid_end_mjd"] - row["valid_start_mjd"]) * 24,
                "is_current": start_mjd <= now.mjd <= end_mjd,
            }
        )

    return {
        "timeline_start": Time(start_mjd, format="mjd").isot,
        "timeline_end": Time(end_mjd, format="mjd").isot,
        "current_time": now.isot,
        "current_mjd": now.mjd,
        "windows": windows,
        "total_windows": len(windows),
    }


# ============================================================================
# Flux Monitoring Endpoints
# ============================================================================


@router.get("/flux-monitoring")
async def get_flux_monitoring_status(
    calibrator: Optional[str] = Query(None, description="Filter by calibrator name"),
    days_back: int = Query(7, description="Days to look back"),
) -> Dict[str, Any]:
    """
    Get flux monitoring status for calibrators.

    Returns stability metrics and recent measurements.
    """
    import sqlite3
    from pathlib import Path

    from astropy.time import Time

    # Unified database path (Phase 2 consolidation)
    products_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    if not products_path.exists():
        return {
            "calibrators": [],
            "message": "Pipeline database not found",
        }

    conn = sqlite3.connect(str(products_path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Check if calibration_monitoring table exists
    table_exists = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='calibration_monitoring'
        """
    ).fetchone()

    if not table_exists:
        conn.close()
        return {
            "calibrators": [],
            "message": "Flux monitoring table not initialized. Run create_flux_monitoring_tables() to initialize.",
        }

    now_mjd = Time.now().mjd
    start_mjd = now_mjd - days_back

    # Build query
    if calibrator:
        rows = conn.execute(
            """
            SELECT calibrator_name,
                   COUNT(*) as n_measurements,
                   MAX(mjd) as latest_mjd,
                   AVG(flux_ratio) as mean_flux_ratio,
                   MIN(flux_ratio) as min_flux_ratio,
                   MAX(flux_ratio) as max_flux_ratio
            FROM calibration_monitoring
            WHERE calibrator_name = ? AND mjd >= ?
            GROUP BY calibrator_name
            """,
            (calibrator, start_mjd),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT calibrator_name,
                   COUNT(*) as n_measurements,
                   MAX(mjd) as latest_mjd,
                   AVG(flux_ratio) as mean_flux_ratio,
                   MIN(flux_ratio) as min_flux_ratio,
                   MAX(flux_ratio) as max_flux_ratio
            FROM calibration_monitoring
            WHERE mjd >= ?
            GROUP BY calibrator_name
            ORDER BY n_measurements DESC
            """,
            (start_mjd,),
        ).fetchall()

    # Get alert counts
    alert_counts = {}
    alert_rows = conn.execute(
        """
        SELECT calibrator_name, COUNT(*) as count
        FROM flux_monitoring_alerts
        WHERE calibrator_name IS NOT NULL
        GROUP BY calibrator_name
        """
    ).fetchall()
    for row in alert_rows:
        alert_counts[row["calibrator_name"]] = row["count"]

    conn.close()

    calibrators = []
    for row in rows:
        name = row["calibrator_name"]
        mean_ratio = row["mean_flux_ratio"]
        min_ratio = row["min_flux_ratio"]
        max_ratio = row["max_flux_ratio"]

        # Stability check: ratio within 10% of 1.0
        is_stable = (
            mean_ratio is not None
            and 0.9 <= mean_ratio <= 1.1
            and (max_ratio - min_ratio) < 0.2
        )

        calibrators.append(
            {
                "calibrator_name": name,
                "n_measurements": row["n_measurements"],
                "latest_mjd": row["latest_mjd"],
                "latest_iso": (
                    Time(row["latest_mjd"], format="mjd").isot
                    if row["latest_mjd"]
                    else None
                ),
                "mean_flux_ratio": round(mean_ratio, 4) if mean_ratio else None,
                "flux_ratio_range": (
                    [round(min_ratio, 4), round(max_ratio, 4)]
                    if min_ratio and max_ratio
                    else None
                ),
                "is_stable": is_stable,
                "alerts_count": alert_counts.get(name, 0),
            }
        )

    return {
        "calibrators": calibrators,
        "query_period_days": days_back,
        "query_start_mjd": start_mjd,
        "query_start_iso": Time(start_mjd, format="mjd").isot,
        "total_calibrators": len(calibrators),
    }


@router.get("/flux-monitoring/{calibrator_name}/history")
async def get_flux_history(
    calibrator_name: str,
    days_back: int = Query(30, description="Days to look back"),
    limit: int = Query(100, description="Maximum records to return"),
) -> Dict[str, Any]:
    """
    Get detailed flux monitoring history for a specific calibrator.

    Returns time-series data for plotting.
    """
    import sqlite3
    from pathlib import Path

    from astropy.time import Time

    # Unified database path (Phase 2 consolidation)
    products_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    if not products_path.exists():
        return {"error": "Pipeline database not found"}

    conn = sqlite3.connect(str(products_path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    now_mjd = Time.now().mjd
    start_mjd = now_mjd - days_back

    rows = conn.execute(
        """
        SELECT mjd, observed_flux_jy, catalog_flux_jy, flux_ratio,
               phase_rms_deg, amp_rms, flagged_fraction, ms_path
        FROM calibration_monitoring
        WHERE calibrator_name = ? AND mjd >= ?
        ORDER BY mjd DESC
        LIMIT ?
        """,
        (calibrator_name, start_mjd, limit),
    ).fetchall()

    conn.close()

    history = []
    for row in rows:
        history.append(
            {
                "mjd": row["mjd"],
                "iso": Time(row["mjd"], format="mjd").isot,
                "observed_flux_jy": row["observed_flux_jy"],
                "catalog_flux_jy": row["catalog_flux_jy"],
                "flux_ratio": row["flux_ratio"],
                "phase_rms_deg": row["phase_rms_deg"],
                "amp_rms": row["amp_rms"],
                "flagged_fraction": row["flagged_fraction"],
                "ms_path": row["ms_path"],
            }
        )

    return {
        "calibrator_name": calibrator_name,
        "period_days": days_back,
        "measurements": history,
        "total_measurements": len(history),
    }


@router.get("/alerts")
async def get_monitoring_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    days_back: int = Query(7, description="Days to look back"),
    limit: int = Query(50, description="Maximum alerts to return"),
) -> Dict[str, Any]:
    """
    Get recent monitoring alerts from flux monitoring system.
    """
    import sqlite3
    from pathlib import Path

    from astropy.time import Time

    # Unified database path (Phase 2 consolidation)
    products_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    if not products_path.exists():
        return {"alerts": [], "message": "Pipeline database not found"}

    conn = sqlite3.connect(str(products_path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Check if table exists
    table_exists = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='flux_monitoring_alerts'
        """
    ).fetchone()

    if not table_exists:
        conn.close()
        return {"alerts": [], "message": "Alerts table not initialized"}

    now_mjd = Time.now().mjd
    cutoff_time = (now_mjd - days_back) * 86400  # Convert to unix timestamp approx

    if severity:
        rows = conn.execute(
            """
            SELECT * FROM flux_monitoring_alerts
            WHERE severity = ? AND triggered_at >= ?
            ORDER BY triggered_at DESC
            LIMIT ?
            """,
            (severity, cutoff_time, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM flux_monitoring_alerts
            WHERE triggered_at >= ?
            ORDER BY triggered_at DESC
            LIMIT ?
            """,
            (cutoff_time, limit),
        ).fetchall()

    conn.close()

    alerts = []
    for row in rows:
        alerts.append(dict(row))

    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "period_days": days_back,
        "severity_filter": severity,
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: Optional[str] = Query(None, description="Username acknowledging the alert"),
) -> Dict[str, Any]:
    """
    Acknowledge a monitoring alert.

    Marks the alert as acknowledged with a timestamp and optional username.
    Acknowledged alerts are typically hidden from active alert views.

    Args:
        alert_id: ID of the alert to acknowledge
        acknowledged_by: Optional username of the person acknowledging
    """
    import sqlite3
    from pathlib import Path

    products_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    if not products_path.exists():
        return {"success": False, "error": "Pipeline database not found"}

    conn = sqlite3.connect(str(products_path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Check if table exists
    table_exists = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='flux_monitoring_alerts'
        """
    ).fetchone()

    if not table_exists:
        conn.close()
        return {"success": False, "error": "Alerts table not initialized"}

    # Check if alert exists
    alert = conn.execute(
        "SELECT id, acknowledged_at FROM flux_monitoring_alerts WHERE id = ?",
        (alert_id,),
    ).fetchone()

    if not alert:
        conn.close()
        return {"success": False, "error": f"Alert {alert_id} not found"}

    if alert["acknowledged_at"] is not None:
        conn.close()
        return {
            "success": False,
            "error": f"Alert {alert_id} is already acknowledged",
            "acknowledged_at": alert["acknowledged_at"],
        }

    # Update the alert
    acknowledged_at = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        """
        UPDATE flux_monitoring_alerts
        SET acknowledged_at = ?, acknowledged_by = ?
        WHERE id = ?
        """,
        (acknowledged_at, acknowledged_by, alert_id),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "alert_id": alert_id,
        "acknowledged_at": acknowledged_at,
        "acknowledged_by": acknowledged_by,
    }


@router.post("/flux-monitoring/check")
async def trigger_flux_monitoring_check(
    calibrator: Optional[str] = Query(None, description="Specific calibrator to check"),
    create_alerts: bool = Query(True, description="Create alerts if issues found"),
) -> Dict[str, Any]:
    """
    Trigger a flux monitoring check manually.

    This runs the same check that would be run by the scheduler.
    """
    try:
        from dsa110_contimg.catalog.flux_monitoring import run_flux_monitoring_check

        result = run_flux_monitoring_check(
            calibrator_name=calibrator,
            create_alerts=create_alerts,
        )
        return {
            "success": True,
            "result": result,
            "triggered_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.exception("Flux monitoring check failed")
        return {
            "success": False,
            "error": str(e),
            "triggered_at": datetime.utcnow().isoformat() + "Z",
        }


# ============================================================================
# Calibration Health Endpoints
# ============================================================================


class CalibrationHealthStatus(BaseModel):
    """Calibration health status."""

    status: str  # healthy, warning, critical
    message: str
    nearest_cal_hours: Optional[float] = None
    active_sets: int = 0
    stale_sets: int = 0
    missing_types: List[str] = Field(default_factory=list)
    query_mjd: float
    query_iso: str
    checked_at: str


class CalibrationCandidate(BaseModel):
    """A calibration candidate."""

    set_name: str
    mjd: float
    time_diff_hours: float
    tables: Dict[str, Optional[str]]
    source_ms_path: Optional[str] = None
    staleness_level: str = "fresh"


class CalibrationTimelineEntry(BaseModel):
    """Entry in calibration timeline."""

    set_name: str
    start_mjd: Optional[float]
    end_mjd: Optional[float]
    start_iso: Optional[str]
    end_iso: Optional[str]
    table_types: List[str]
    table_count: int


@router.get("/calibration", response_model=CalibrationHealthStatus)
async def get_calibration_health(
    mjd: Optional[float] = Query(None, description="Query MJD (default: now)"),
    warning_hours: float = Query(12.0, description="Hours until warning status"),
    critical_hours: float = Query(24.0, description="Hours until critical status"),
) -> CalibrationHealthStatus:
    """
    Get calibration health status for a given time.

    Evaluates the freshness of available calibrations and returns
    health status with recommendations. Useful for monitoring
    calibration coverage and detecting gaps.

    Args:
        mjd: Query MJD (default: current time)
        warning_hours: Hours until warning status (default: 12)
        critical_hours: Hours until critical status (default: 24)
    """
    from astropy.time import Time

    from dsa110_contimg.calibration.caltables import check_calibration_staleness

    if mjd is None:
        mjd = Time.now().mjd

    query_time = Time(mjd, format="mjd")
    checked_at = datetime.utcnow().isoformat() + "Z"

    health = check_calibration_staleness(
        mjd,
        warning_threshold_hours=warning_hours,
        critical_threshold_hours=critical_hours,
    )

    return CalibrationHealthStatus(
        status=health.status,
        message=health.message,
        nearest_cal_hours=health.nearest_cal_hours,
        active_sets=health.active_sets,
        stale_sets=health.stale_sets,
        missing_types=health.missing_types,
        query_mjd=mjd,
        query_iso=query_time.isot,
        checked_at=checked_at,
    )


@router.get("/calibration/nearest")
async def get_nearest_calibration(
    mjd: Optional[float] = Query(None, description="Query MJD (default: now)"),
    search_hours: float = Query(24.0, description="Search window in hours"),
) -> Dict[str, Any]:
    """
    Find the nearest calibration to a given time.

    Performs bidirectional time-based search to find the closest
    valid calibration tables within the search window.

    Args:
        mjd: Query MJD (default: current time)
        search_hours: Maximum search window in hours (default: 24)
    """
    from astropy.time import Time

    from dsa110_contimg.calibration.caltables import find_nearest_calibration

    if mjd is None:
        mjd = Time.now().mjd

    query_time = Time(mjd, format="mjd")
    checked_at = datetime.utcnow().isoformat() + "Z"

    result = find_nearest_calibration(mjd, search_window_hours=search_hours)

    if result is None:
        return {
            "found": False,
            "query_mjd": mjd,
            "query_iso": query_time.isot,
            "search_hours": search_hours,
            "message": f"No calibrations within ±{search_hours}h",
            "checked_at": checked_at,
        }

    return {
        "found": True,
        "query_mjd": mjd,
        "query_iso": query_time.isot,
        "search_hours": search_hours,
        "calibration": {
            "set_name": result.set_name,
            "mjd": result.mjd,
            "iso": Time(result.mjd, format="mjd").isot,
            "time_diff_hours": result.time_diff_hours,
            "staleness_level": result.staleness_level,
            "tables": result.tables,
            "source_ms_path": result.source_ms_path,
        },
        "checked_at": checked_at,
    }


@router.get("/calibration/timeline")
async def get_calibration_coverage_timeline(
    start_mjd: Optional[float] = Query(None, description="Start MJD"),
    end_mjd: Optional[float] = Query(None, description="End MJD"),
    hours: float = Query(48.0, description="Hours to show if start/end not specified"),
) -> Dict[str, Any]:
    """
    Get timeline of calibration coverage.

    Returns all calibration sets and their validity windows within
    the specified time range. Useful for visualizing calibration
    coverage and identifying gaps.

    Args:
        start_mjd: Start of time range
        end_mjd: End of time range
        hours: Hours to show (default: 48, centered on now)
    """
    from astropy.time import Time

    from dsa110_contimg.calibration.caltables import get_calibration_timeline

    now = Time.now()

    if start_mjd is None:
        start_mjd = now.mjd - (hours / 48.0)
    if end_mjd is None:
        end_mjd = now.mjd + (hours / 48.0)

    timeline = get_calibration_timeline(start_mjd, end_mjd)

    # Calculate coverage statistics
    total_duration = (end_mjd - start_mjd) * 24  # hours
    covered_hours = 0
    gaps = []
    prev_end = start_mjd

    # Sort by start time
    sorted_timeline = sorted(
        timeline,
        key=lambda x: x.get("start_mjd") or start_mjd,
    )

    for entry in sorted_timeline:
        entry_start = entry.get("start_mjd") or start_mjd
        entry_end = entry.get("end_mjd") or end_mjd

        # Check for gap before this entry
        if entry_start > prev_end:
            gap_hours = (entry_start - prev_end) * 24
            gaps.append({
                "start_mjd": prev_end,
                "end_mjd": entry_start,
                "start_iso": Time(prev_end, format="mjd").isot,
                "end_iso": Time(entry_start, format="mjd").isot,
                "duration_hours": gap_hours,
            })

        # Update coverage
        if entry_end > prev_end:
            covered_hours += (min(entry_end, end_mjd) - max(entry_start, prev_end)) * 24
            prev_end = max(prev_end, entry_end)

    # Check for final gap
    if prev_end < end_mjd:
        gap_hours = (end_mjd - prev_end) * 24
        gaps.append({
            "start_mjd": prev_end,
            "end_mjd": end_mjd,
            "start_iso": Time(prev_end, format="mjd").isot,
            "end_iso": Time(end_mjd, format="mjd").isot,
            "duration_hours": gap_hours,
        })

    coverage_pct = (covered_hours / total_duration * 100) if total_duration > 0 else 0

    return {
        "timeline_start_mjd": start_mjd,
        "timeline_end_mjd": end_mjd,
        "timeline_start_iso": Time(start_mjd, format="mjd").isot,
        "timeline_end_iso": Time(end_mjd, format="mjd").isot,
        "current_mjd": now.mjd,
        "current_iso": now.isot,
        "entries": timeline,
        "total_entries": len(timeline),
        "statistics": {
            "total_duration_hours": total_duration,
            "covered_hours": covered_hours,
            "coverage_percent": round(coverage_pct, 1),
            "gaps": gaps,
            "gap_count": len(gaps),
        },
    }


@router.get("/calibration/applylist")
async def get_calibration_applylist(
    mjd: Optional[float] = Query(None, description="Query MJD (default: now)"),
    search_hours: float = Query(24.0, description="Search window in hours"),
) -> Dict[str, Any]:
    """
    Get ordered list of calibration tables to apply.

    Returns the calibration tables in the correct application order
    (delay, bandpass, gain) for the nearest calibration to the
    specified time.

    Args:
        mjd: Query MJD (default: current time)
        search_hours: Maximum search window in hours (default: 24)
    """
    from astropy.time import Time

    from dsa110_contimg.calibration.caltables import (
        find_nearest_calibration,
        get_applylist_for_mjd,
    )

    if mjd is None:
        mjd = Time.now().mjd

    query_time = Time(mjd, format="mjd")
    checked_at = datetime.utcnow().isoformat() + "Z"

    # Get apply list
    tables = get_applylist_for_mjd(mjd, search_window_hours=search_hours)

    # Get more info about the source
    result = find_nearest_calibration(mjd, search_window_hours=search_hours)

    return {
        "query_mjd": mjd,
        "query_iso": query_time.isot,
        "applylist": tables,
        "table_count": len(tables),
        "source_info": {
            "set_name": result.set_name if result else None,
            "mjd": result.mjd if result else None,
            "time_diff_hours": result.time_diff_hours if result else None,
            "staleness_level": result.staleness_level if result else None,
        }
        if result
        else None,
        "checked_at": checked_at,
    }


# ============================================================================
# Calibration QA Endpoints
# ============================================================================


class CalibrationQAMetrics(BaseModel):
    """Metrics from a single calibration table."""

    caltable_path: str
    cal_type: str
    n_solutions: int
    n_flagged: int
    flag_fraction: float
    mean_amplitude: float
    std_amplitude: float
    median_snr: Optional[float] = None
    extraction_error: Optional[str] = None


class CalibrationQAIssue(BaseModel):
    """A QA issue found during assessment."""

    severity: str
    cal_type: str
    metric: str
    value: float
    threshold: float
    message: str


class CalibrationQAResponse(BaseModel):
    """Calibration QA assessment response."""

    ms_path: str
    passed: bool
    severity: str
    overall_grade: str
    issues: List[CalibrationQAIssue] = Field(default_factory=list)
    metrics: List[CalibrationQAMetrics] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    assessment_time_s: float
    timestamp: float


class CalibrationQASummaryStats(BaseModel):
    """Summary statistics for QA results."""

    by_grade: Dict[str, int]
    passed: int
    failed: int
    total: int
    avg_flagging: Optional[float]
    avg_assessment_time_s: Optional[float]


@router.get("/calibration/qa/recent")
async def get_recent_calibration_qa(
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    passed_only: bool = Query(False, description="Only return passed results"),
    failed_only: bool = Query(False, description="Only return failed results"),
    min_grade: Optional[str] = Query(
        None,
        description="Minimum grade ('excellent', 'good', 'marginal', 'poor')",
    ),
) -> Dict[str, Any]:
    """
    Get recent calibration QA results.

    Returns a list of recent QA assessments with filtering options.
    Results are ordered by timestamp (most recent first).

    Args:
        limit: Maximum number of results to return
        passed_only: Only return passed assessments
        failed_only: Only return failed assessments
        min_grade: Minimum acceptable grade
    """
    from dsa110_contimg.calibration.qa import get_qa_store

    store = get_qa_store()

    results = store.list_recent(
        limit=limit,
        passed_only=passed_only,
        failed_only=failed_only,
        min_grade=min_grade,
    )

    checked_at = datetime.utcnow().isoformat() + "Z"

    return {
        "results": [r.to_dict() for r in results],
        "count": len(results),
        "checked_at": checked_at,
    }


@router.get("/calibration/qa/stats")
async def get_calibration_qa_stats(
    since_hours: Optional[float] = Query(
        None, description="Only include results from last N hours"
    ),
) -> CalibrationQASummaryStats:
    """
    Get summary statistics for calibration QA results.

    Returns aggregate statistics including pass/fail counts,
    grade distribution, and average metrics.

    Args:
        since_hours: Only include results from the last N hours
    """
    import time

    from dsa110_contimg.calibration.qa import get_qa_store

    store = get_qa_store()

    since_timestamp = None
    if since_hours:
        since_timestamp = time.time() - (since_hours * 3600)

    stats = store.get_summary_stats(since_timestamp=since_timestamp)

    return CalibrationQASummaryStats(
        by_grade=stats.get("by_grade", {}),
        passed=stats.get("passed", 0),
        failed=stats.get("failed", 0),
        total=stats.get("total", 0),
        avg_flagging=stats.get("avg_flagging"),
        avg_assessment_time_s=stats.get("avg_assessment_time_s"),
    )


@router.get("/calibration/qa/{ms_path:path}")
async def get_calibration_qa_for_ms(
    ms_path: str,
    run_assessment: bool = Query(
        False, description="Run new assessment if not found"
    ),
    save_result: bool = Query(True, description="Save result to database"),
) -> Dict[str, Any]:
    """
    Get calibration QA for a specific Measurement Set.

    Returns the most recent QA assessment for the specified MS.
    Optionally runs a new assessment if none exists.

    Args:
        ms_path: Path to the Measurement Set
        run_assessment: Run new assessment if not found in database
        save_result: Save new assessment result to database
    """
    from pathlib import Path

    from dsa110_contimg.calibration.qa import (
        assess_calibration_quality,
        get_qa_store,
    )

    store = get_qa_store()
    checked_at = datetime.utcnow().isoformat() + "Z"

    # Try to get existing result
    result = store.get_result(ms_path)

    if result is None and run_assessment:
        # Check if MS exists
        if not Path(ms_path).exists():
            return {
                "ms_path": ms_path,
                "error": f"Measurement Set not found: {ms_path}",
                "checked_at": checked_at,
            }

        # Run assessment
        result = assess_calibration_quality(ms_path)

        if save_result:
            store.save_result(result)

    if result is None:
        return {
            "ms_path": ms_path,
            "error": "No QA result found. Set run_assessment=true to assess.",
            "checked_at": checked_at,
        }

    return {
        "result": result.to_dict(),
        "checked_at": checked_at,
    }


# ============================================================================
# GPU Health Endpoints
# ============================================================================


class GPUHealthInfo(BaseModel):
    """GPU health information."""

    id: int
    name: str
    health_status: str  # healthy, warning, critical, unavailable
    memory_total_gb: float
    memory_used_gb: Optional[float] = None
    memory_utilization_pct: Optional[float] = None
    gpu_utilization_pct: Optional[float] = None
    temperature_c: Optional[float] = None
    power_draw_w: Optional[float] = None
    driver_version: Optional[str] = None
    compute_capability: Optional[str] = None


class GPUHealthResponse(BaseModel):
    """GPU health status response."""

    available: bool
    gpu_count: int
    overall_status: str  # healthy, warning, critical, unavailable
    monitoring_backend: str  # pynvml, cupy, none
    gpus: List[GPUHealthInfo]
    recent_alerts: List[Dict[str, Any]] = []
    thresholds: Dict[str, float] = {}
    checked_at: str


@router.get("/gpus", response_model=GPUHealthResponse)
async def get_gpu_health() -> GPUHealthResponse:
    """
    Get comprehensive GPU health status.

    Returns health status, utilization, temperature, and recent alerts
    for all available GPUs. Used by the Health Dashboard for GPU monitoring.
    """
    checked_at = datetime.utcnow().isoformat() + "Z"

    try:
        from dsa110_contimg.monitoring.gpu import get_gpu_monitor

        monitor = get_gpu_monitor()
        summary = monitor.get_all_summaries()

        # Determine overall status
        statuses = [d.get("health_status", "unavailable") for d in summary["devices"]]
        if "critical" in statuses:
            overall_status = "critical"
        elif "warning" in statuses:
            overall_status = "warning"
        elif "healthy" in statuses:
            overall_status = "healthy"
        else:
            overall_status = "unavailable"

        gpus = []
        for device in summary["devices"]:
            metrics = device.get("current_metrics") or {}
            gpus.append(
                GPUHealthInfo(
                    id=device["id"],
                    name=device["name"],
                    health_status=device.get("health_status", "unavailable"),
                    memory_total_gb=device["memory_total_gb"],
                    memory_used_gb=metrics.get("memory_used_gb"),
                    memory_utilization_pct=metrics.get("memory_utilization_pct"),
                    gpu_utilization_pct=metrics.get("gpu_utilization_pct"),
                    temperature_c=metrics.get("temperature_c"),
                    power_draw_w=metrics.get("power_draw_w"),
                    driver_version=device.get("driver_version"),
                    compute_capability=device.get("compute_capability"),
                )
            )

        return GPUHealthResponse(
            available=summary["available"],
            gpu_count=summary["gpu_count"],
            overall_status=overall_status,
            monitoring_backend=summary["monitoring_backend"],
            gpus=gpus,
            recent_alerts=monitor.get_recent_alerts(10),
            thresholds=summary["thresholds"],
            checked_at=checked_at,
        )

    except ImportError:
        return GPUHealthResponse(
            available=False,
            gpu_count=0,
            overall_status="unavailable",
            monitoring_backend="none",
            gpus=[],
            recent_alerts=[],
            thresholds={},
            checked_at=checked_at,
        )


@router.get("/gpus/{gpu_id}", response_model=GPUHealthInfo)
async def get_gpu_health_by_id(gpu_id: int) -> GPUHealthInfo:
    """
    Get health status for a specific GPU.

    Args:
        gpu_id: GPU index (0-based)
    """
    try:
        from dsa110_contimg.monitoring.gpu import get_gpu_monitor

        monitor = get_gpu_monitor()
        summary = monitor.get_device_summary(gpu_id)

        if not summary:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"GPU {gpu_id} not found")

        metrics = summary.get("current_metrics") or {}
        return GPUHealthInfo(
            id=summary["id"],
            name=summary["name"],
            health_status=summary.get("health_status", "unavailable"),
            memory_total_gb=summary["memory_total_gb"],
            memory_used_gb=metrics.get("memory_used_gb"),
            memory_utilization_pct=metrics.get("memory_utilization_pct"),
            gpu_utilization_pct=metrics.get("gpu_utilization_pct"),
            temperature_c=metrics.get("temperature_c"),
            power_draw_w=metrics.get("power_draw_w"),
            driver_version=summary.get("driver_version"),
            compute_capability=summary.get("compute_capability"),
        )

    except ImportError:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="GPU monitoring not available")


@router.get("/gpus/{gpu_id}/history")
async def get_gpu_history(
    gpu_id: int,
    minutes: int = Query(60, ge=1, le=1440, description="Minutes of history"),
) -> Dict[str, Any]:
    """
    Get historical metrics for a GPU.

    Returns time series data for memory, utilization, temperature.
    Useful for rendering charts in the dashboard.

    Args:
        gpu_id: GPU index (0-based)
        minutes: Number of minutes of history (1-1440, default 60)
    """
    try:
        from dsa110_contimg.monitoring.gpu import get_gpu_monitor

        monitor = get_gpu_monitor()
        history = monitor.get_history(gpu_id, minutes)

        if not history:
            return {
                "gpu_id": gpu_id,
                "minutes": minutes,
                "data_points": 0,
                "history": [],
            }

        return {
            "gpu_id": gpu_id,
            "minutes": minutes,
            "data_points": len(history),
            "history": history,
        }

    except ImportError:
        return {
            "gpu_id": gpu_id,
            "minutes": minutes,
            "data_points": 0,
            "history": [],
            "error": "GPU monitoring not available",
        }


@router.get("/gpus/alerts/recent")
async def get_gpu_alerts(
    limit: int = Query(100, ge=1, le=1000, description="Maximum alerts to return"),
    gpu_id: Optional[int] = Query(None, description="Filter by GPU ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
) -> Dict[str, Any]:
    """
    Get recent GPU alerts.

    Args:
        limit: Maximum number of alerts to return
        gpu_id: Optional filter by GPU ID
        severity: Optional filter by severity (warning, critical)
    """
    try:
        from dsa110_contimg.monitoring.gpu import get_gpu_monitor

        monitor = get_gpu_monitor()
        alerts = monitor.get_recent_alerts(limit)

        # Apply filters
        if gpu_id is not None:
            alerts = [a for a in alerts if a["gpu_id"] == gpu_id]
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]

        return {
            "alerts": alerts,
            "total": len(alerts),
            "filters": {
                "gpu_id": gpu_id,
                "severity": severity,
            },
        }

    except ImportError:
        return {
            "alerts": [],
            "total": 0,
            "error": "GPU monitoring not available",
        }


# ============================================================================
# Pointing Status Endpoint
# ============================================================================


class TransitPrediction(BaseModel):
    """Transit prediction for a calibrator."""

    calibrator: str
    ra_deg: float
    dec_deg: float
    transit_utc: str
    time_to_transit_sec: float
    lst_at_transit: float
    elevation_at_transit: float
    status: str  # "in_progress", "upcoming", "scheduled"


class PointingStatusResponse(BaseModel):
    """Current pointing status and upcoming transits."""

    current_lst: float
    current_lst_deg: float
    active_calibrator: Optional[str] = None
    upcoming_transits: List[TransitPrediction]
    timestamp: str


@router.get("/pointing", response_model=PointingStatusResponse)
async def get_pointing_status() -> PointingStatusResponse:
    """
    Get current pointing status including LST and upcoming calibrator transits.

    This endpoint aggregates data from the pointing tracker and transit
    prediction systems to provide a unified view for the health dashboard.
    """
    from astropy.time import Time
    from astropy.coordinates import Longitude
    import astropy.units as u

    try:
        # Get current LST
        now = Time.now()

        # DSA-110 location
        dsa_longitude = -118.2819  # degrees West
        lst = now.sidereal_time('apparent', longitude=dsa_longitude * u.deg)
        current_lst_hours = lst.hour
        current_lst_deg = lst.deg

        # Try to get upcoming transits
        upcoming_transits = []
        active_calibrator = None

        try:
            from dsa110_contimg.pointing.monitor import get_all_upcoming_transits
            from dsa110_contimg.pipeline.precompute import get_pointing_tracker

            # Get current pointing
            tracker = get_pointing_tracker()
            current_dec = tracker.current_dec if tracker else None

            # Get upcoming transits
            transits_data = get_all_upcoming_transits(
                target_dec_deg=current_dec,
                hours_ahead=24,
                max_transits=10,
            )

            for t in transits_data.get("transits", []):
                time_to_transit = t.get("time_to_transit_sec", t.get("seconds_until_transit", 0))

                # Determine status based on time to transit
                if time_to_transit < 0:
                    status = "in_progress"
                    if not active_calibrator:
                        active_calibrator = t.get("calibrator", t.get("name"))
                elif time_to_transit < 1800:  # 30 minutes
                    status = "upcoming"
                else:
                    status = "scheduled"

                upcoming_transits.append(TransitPrediction(
                    calibrator=t.get("calibrator", t.get("name", "Unknown")),
                    ra_deg=t.get("ra_deg", 0),
                    dec_deg=t.get("dec_deg", 0),
                    transit_utc=t.get("transit_utc", t.get("transit_time", now.iso)),
                    time_to_transit_sec=time_to_transit,
                    lst_at_transit=t.get("lst_at_transit", t.get("transit_lst_hours", 0)),
                    elevation_at_transit=t.get("elevation_at_transit", t.get("max_elevation", 90)),
                    status=status,
                ))
        except ImportError:
            logger.warning("Pointing monitor not available, returning empty transits")
        except Exception as e:
            logger.warning(f"Failed to get transit data: {e}")

        return PointingStatusResponse(
            current_lst=current_lst_hours,
            current_lst_deg=current_lst_deg,
            active_calibrator=active_calibrator,
            upcoming_transits=upcoming_transits,
            timestamp=now.iso,
        )

    except Exception as e:
        logger.exception("Failed to get pointing status")
        # Return minimal valid response
        return PointingStatusResponse(
            current_lst=0.0,
            current_lst_deg=0.0,
            active_calibrator=None,
            upcoming_transits=[],
            timestamp=datetime.utcnow().isoformat() + "Z",
        )


# ============================================================================
# Storage Monitoring Endpoints
# ============================================================================


class DirectoryUsage(BaseModel):
    """Disk usage for a directory."""

    path: str
    name: str
    size_bytes: int
    size_formatted: str
    file_count: int
    last_modified: Optional[str] = None
    category: str  # hdf5, ms, images, calibration, logs, other


class DiskPartition(BaseModel):
    """Disk partition information."""

    mount_point: str
    device: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float
    total_formatted: str
    used_formatted: str
    free_formatted: str


class StorageAlert(BaseModel):
    """Storage-related alert."""

    severity: str  # info, warning, critical
    message: str
    path: Optional[str] = None
    threshold_percent: Optional[float] = None
    current_percent: Optional[float] = None


class StorageSummary(BaseModel):
    """Complete storage summary."""

    partitions: List[DiskPartition]
    directories: List[DirectoryUsage]
    alerts: List[StorageAlert]
    total_pipeline_data_bytes: int
    total_pipeline_data_formatted: str
    checked_at: str
    check_duration_ms: Optional[float] = None


class CleanupCandidate(BaseModel):
    """A file recommended for cleanup."""

    path: str
    size_bytes: int
    size_formatted: str
    age_days: float
    last_accessed: Optional[str] = None
    reason: str
    category: str  # old_ms, old_images, old_logs, temp, orphaned
    safe_to_delete: bool


class CleanupRecommendations(BaseModel):
    """Cleanup recommendations response."""

    candidates: List[CleanupCandidate]
    total_reclaimable_bytes: int
    total_reclaimable_formatted: str
    generated_at: str


class StorageTrendPoint(BaseModel):
    """A point in storage trend history."""

    timestamp: str
    used_bytes: int
    usage_percent: float


class StorageTrend(BaseModel):
    """Storage trend data for a partition."""

    mount_point: str
    data_points: List[StorageTrendPoint]
    growth_rate_bytes_per_day: float
    days_until_full: Optional[float] = None
    period_start: str
    period_end: str


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"


@router.get("/storage/summary", response_model=StorageSummary)
async def get_storage_summary() -> StorageSummary:
    """
    Get comprehensive storage summary including disk usage and directory breakdown.
    """
    import shutil
    import time
    from pathlib import Path

    start_time = time.time()
    checked_at = datetime.utcnow().isoformat() + "Z"

    partitions: List[DiskPartition] = []
    directories: List[DirectoryUsage] = []
    alerts: List[StorageAlert] = []
    total_pipeline_data = 0

    # Check main data partitions
    partition_paths = [
        ("/data/dsa110-contimg", "data"),
        ("/stage/dsa110-contimg", "ssd"),
        ("/", "root"),
    ]

    for mount_path, name in partition_paths:
        path = Path(mount_path)
        if path.exists():
            try:
                usage = shutil.disk_usage(path)
                partition = DiskPartition(
                    mount_point=mount_path,
                    device=name,
                    filesystem="ext4",  # Simplified
                    total_bytes=usage.total,
                    used_bytes=usage.used,
                    free_bytes=usage.free,
                    usage_percent=round((usage.used / usage.total) * 100, 1),
                    total_formatted=format_bytes(usage.total),
                    used_formatted=format_bytes(usage.used),
                    free_formatted=format_bytes(usage.free),
                )
                partitions.append(partition)

                # Generate alerts for high usage
                usage_pct = (usage.used / usage.total) * 100
                if usage_pct >= 95:
                    alerts.append(StorageAlert(
                        severity="critical",
                        message=f"Disk {mount_path} is critically full ({usage_pct:.1f}%)",
                        path=mount_path,
                        threshold_percent=95,
                        current_percent=usage_pct,
                    ))
                elif usage_pct >= 85:
                    alerts.append(StorageAlert(
                        severity="warning",
                        message=f"Disk {mount_path} is filling up ({usage_pct:.1f}%)",
                        path=mount_path,
                        threshold_percent=85,
                        current_percent=usage_pct,
                    ))
            except OSError as e:
                logger.warning(f"Could not check partition {mount_path}: {e}")

    # Check pipeline data directories
    data_dirs = [
        ("/data/dsa110-contimg/state/hdf5", "HDF5 Data", "hdf5"),
        ("/data/dsa110-contimg/state/ms", "Measurement Sets", "ms"),
        ("/data/dsa110-contimg/state/images", "FITS Images", "images"),
        ("/data/dsa110-contimg/state/cal", "Calibration Tables", "calibration"),
        ("/data/dsa110-contimg/state/logs", "Log Files", "logs"),
        ("/stage/dsa110-contimg/tmp", "Temporary Files", "other"),
    ]

    for dir_path, name, category in data_dirs:
        path = Path(dir_path)
        if path.exists():
            try:
                total_size = 0
                file_count = 0
                latest_mtime = 0

                for f in path.rglob("*"):
                    if f.is_file():
                        try:
                            stat = f.stat()
                            total_size += stat.st_size
                            file_count += 1
                            if stat.st_mtime > latest_mtime:
                                latest_mtime = stat.st_mtime
                        except OSError:
                            pass

                directories.append(DirectoryUsage(
                    path=dir_path,
                    name=name,
                    size_bytes=total_size,
                    size_formatted=format_bytes(total_size),
                    file_count=file_count,
                    last_modified=(
                        datetime.fromtimestamp(latest_mtime).isoformat() + "Z"
                        if latest_mtime > 0 else None
                    ),
                    category=category,
                ))
                total_pipeline_data += total_size
            except OSError as e:
                logger.warning(f"Could not check directory {dir_path}: {e}")

    check_duration = (time.time() - start_time) * 1000

    return StorageSummary(
        partitions=partitions,
        directories=directories,
        alerts=alerts,
        total_pipeline_data_bytes=total_pipeline_data,
        total_pipeline_data_formatted=format_bytes(total_pipeline_data),
        checked_at=checked_at,
        check_duration_ms=round(check_duration, 2),
    )


@router.get("/storage/cleanup-recommendations", response_model=CleanupRecommendations)
async def get_cleanup_recommendations() -> CleanupRecommendations:
    """
    Get recommendations for files that can be safely cleaned up.
    """
    from pathlib import Path
    import time

    generated_at = datetime.utcnow().isoformat() + "Z"
    candidates: List[CleanupCandidate] = []
    total_reclaimable = 0

    now = time.time()

    # Check for old temporary files
    temp_dirs = [
        "/stage/dsa110-contimg/tmp",
        "/data/dsa110-contimg/state/tmp",
    ]

    for temp_dir in temp_dirs:
        path = Path(temp_dir)
        if path.exists():
            try:
                for f in path.rglob("*"):
                    if f.is_file():
                        try:
                            stat = f.stat()
                            age_days = (now - stat.st_mtime) / 86400
                            if age_days > 1:  # Temp files older than 1 day
                                candidates.append(CleanupCandidate(
                                    path=str(f),
                                    size_bytes=stat.st_size,
                                    size_formatted=format_bytes(stat.st_size),
                                    age_days=round(age_days, 1),
                                    last_accessed=(
                                        datetime.fromtimestamp(stat.st_atime).isoformat() + "Z"
                                    ),
                                    reason="Temporary file older than 1 day",
                                    category="temp",
                                    safe_to_delete=True,
                                ))
                                total_reclaimable += stat.st_size
                        except OSError:
                            pass
            except OSError:
                pass

    # Check for old log files (> 30 days)
    log_dir = Path("/data/dsa110-contimg/state/logs")
    if log_dir.exists():
        try:
            for f in log_dir.rglob("*.log*"):
                if f.is_file():
                    try:
                        stat = f.stat()
                        age_days = (now - stat.st_mtime) / 86400
                        if age_days > 30:
                            candidates.append(CleanupCandidate(
                                path=str(f),
                                size_bytes=stat.st_size,
                                size_formatted=format_bytes(stat.st_size),
                                age_days=round(age_days, 1),
                                reason="Log file older than 30 days",
                                category="old_logs",
                                safe_to_delete=True,
                            ))
                            total_reclaimable += stat.st_size
                    except OSError:
                        pass
        except OSError:
            pass

    # Sort by size descending and limit
    candidates.sort(key=lambda c: c.size_bytes, reverse=True)
    candidates = candidates[:100]

    return CleanupRecommendations(
        candidates=candidates,
        total_reclaimable_bytes=total_reclaimable,
        total_reclaimable_formatted=format_bytes(total_reclaimable),
        generated_at=generated_at,
    )


@router.get("/storage/trends", response_model=List[StorageTrend])
async def get_storage_trends(
    days: int = Query(30, ge=1, le=365, description="Days of history"),
) -> List[StorageTrend]:
    """
    Get storage usage trends over time.

    Returns historical disk usage data for trend analysis and capacity planning.
    """
    import sqlite3
    from pathlib import Path

    now = datetime.utcnow()
    period_end = now.isoformat() + "Z"
    period_start = (now - __import__("datetime").timedelta(days=days)).isoformat() + "Z"

    trends: List[StorageTrend] = []

    # Check if we have historical data in the database
    db_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row

            # Check if storage_history table exists
            table_check = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='storage_history'"
            ).fetchone()

            if table_check:
                # Get historical data
                rows = conn.execute(
                    """
                    SELECT mount_point, timestamp, used_bytes, usage_percent
                    FROM storage_history
                    WHERE timestamp >= datetime('now', ?)
                    ORDER BY mount_point, timestamp
                    """,
                    (f"-{days} days",),
                ).fetchall()

                # Group by mount point
                mount_data: Dict[str, List[StorageTrendPoint]] = {}
                for row in rows:
                    mp = row["mount_point"]
                    if mp not in mount_data:
                        mount_data[mp] = []
                    mount_data[mp].append(StorageTrendPoint(
                        timestamp=row["timestamp"],
                        used_bytes=row["used_bytes"],
                        usage_percent=row["usage_percent"],
                    ))

                for mount_point, data_points in mount_data.items():
                    if len(data_points) >= 2:
                        # Calculate growth rate
                        first = data_points[0]
                        last = data_points[-1]
                        days_span = days  # Approximate
                        growth = (last.used_bytes - first.used_bytes) / max(days_span, 1)

                        # Estimate days until full
                        days_until_full = None
                        if growth > 0:
                            # Get total capacity (would need to store this)
                            # For now, estimate based on 100% usage
                            remaining = (100 - last.usage_percent) / 100 * last.used_bytes / (last.usage_percent / 100)
                            if remaining > 0:
                                days_until_full = remaining / growth

                        trends.append(StorageTrend(
                            mount_point=mount_point,
                            data_points=data_points,
                            growth_rate_bytes_per_day=growth,
                            days_until_full=days_until_full,
                            period_start=period_start,
                            period_end=period_end,
                        ))

            conn.close()
        except Exception as e:
            logger.warning(f"Could not get storage trends: {e}")

    # If no historical data, return current snapshot as single point
    if not trends:
        import shutil

        for mount_path in ["/data/dsa110-contimg", "/stage/dsa110-contimg"]:
            path = Path(mount_path)
            if path.exists():
                try:
                    usage = shutil.disk_usage(path)
                    usage_pct = (usage.used / usage.total) * 100

                    trends.append(StorageTrend(
                        mount_point=mount_path,
                        data_points=[StorageTrendPoint(
                            timestamp=period_end,
                            used_bytes=usage.used,
                            usage_percent=round(usage_pct, 1),
                        )],
                        growth_rate_bytes_per_day=0,
                        days_until_full=None,
                        period_start=period_start,
                        period_end=period_end,
                    ))
                except OSError:
                    pass

    return trends

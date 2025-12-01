"""
Monitoring Tasks for ABSURD Workflow Manager.

This module defines ABSURD tasks for:
- Flux monitoring checks
- Health monitoring checks
- Validity window checks
- Alerting
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Task name constants for use with ABSURD
TASK_FLUX_MONITORING_CHECK = "monitoring.flux_check"
TASK_HEALTH_CHECK = "monitoring.health_check"
TASK_VALIDITY_WINDOW_CHECK = "monitoring.validity_check"
TASK_SEND_ALERT = "monitoring.send_alert"


async def execute_monitoring_task(task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a monitoring task.

    This is the entry point for ABSURD worker to execute monitoring tasks.

    Args:
        task_name: Name of the task to execute
        params: Task parameters

    Returns:
        Task result dict
    """
    handlers = {
        TASK_FLUX_MONITORING_CHECK: _execute_flux_monitoring_check,
        TASK_HEALTH_CHECK: _execute_health_check,
        TASK_VALIDITY_WINDOW_CHECK: _execute_validity_window_check,
        TASK_SEND_ALERT: _execute_send_alert,
    }

    handler = handlers.get(task_name)
    if handler is None:
        raise ValueError(f"Unknown monitoring task: {task_name}")

    return await handler(params)


async def _execute_flux_monitoring_check(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute flux monitoring check task.

    Params:
        calibrator: Optional calibrator name to check
        create_alerts: Whether to create alerts (default True)
        products_db: Path to products database
    """
    from dsa110_contimg.catalog.flux_monitoring import run_flux_monitoring_check

    calibrator = params.get("calibrator")
    create_alerts = params.get("create_alerts", True)
    products_db = params.get("products_db", "/data/dsa110-contimg/state/db/products.sqlite3")

    logger.info(f"Running flux monitoring check: calibrator={calibrator}")

    try:
        result = run_flux_monitoring_check(
            calibrator_name=calibrator,
            create_alerts=create_alerts,
            db_path=products_db,
        )
        return {
            "success": True,
            "result": result,
            "executed_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.exception("Flux monitoring check failed")
        return {
            "success": False,
            "error": str(e),
            "executed_at": datetime.utcnow().isoformat() + "Z",
        }


async def _execute_health_check(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute system health check task.

    Params:
        include_docker: Check Docker containers
        include_systemd: Check systemd services
        include_http: Check HTTP endpoints
    """
    from dsa110_contimg.monitoring.service_health import check_system_health

    include_docker = params.get("include_docker", True)
    include_systemd = params.get("include_systemd", True)
    include_http = params.get("include_http", True)

    docker_containers = (
        params.get("docker_containers") or [
            "dsa110-api",
            "dsa110-redis",
            "contimg-stream",
        ]
    )

    systemd_services = (
        params.get("systemd_services") or [
            "contimg-api.service",
            "contimg-stream.service",
        ]
    )

    http_endpoints = (
        params.get("http_endpoints") or {
            "api": "http://localhost:8000/api/status",
        }
    )

    logger.info("Running system health check")

    report = await check_system_health(
        docker_containers=docker_containers if include_docker else None,
        systemd_services=systemd_services if include_systemd else None,
        http_endpoints=http_endpoints if include_http else None,
    )

    return {
        "success": True,
        "overall_status": report.overall_status.value,
        "summary": report.to_dict()["summary"],
        "services": [s.to_dict() for s in report.services],
        "executed_at": datetime.utcnow().isoformat() + "Z",
    }


async def _execute_validity_window_check(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check for expiring validity windows and create alerts.

    Params:
        warning_hours: Hours before expiry to warn (default 2)
        registry_db: Path to calibration registry
    """
    import sqlite3
    from pathlib import Path

    from astropy.time import Time

    warning_hours = params.get("warning_hours", 2)
    registry_db = params.get(
        "registry_db", "/data/dsa110-contimg/state/db/cal_registry.sqlite3"
    )

    logger.info(f"Checking validity windows (warning threshold: {warning_hours}h)")

    if not Path(registry_db).exists():
        return {
            "success": False,
            "error": "Registry database not found",
            "executed_at": datetime.utcnow().isoformat() + "Z",
        }

    now_mjd = Time.now().mjd
    warning_threshold_mjd = now_mjd + (warning_hours / 24.0)

    conn = sqlite3.connect(registry_db, timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Find windows expiring soon
    expiring = conn.execute(
        """
        SELECT DISTINCT set_name, MIN(valid_end_mjd) as earliest_expiry
        FROM caltables
        WHERE status = 'active'
          AND valid_end_mjd IS NOT NULL
          AND valid_end_mjd <= ?
          AND valid_end_mjd >= ?
        GROUP BY set_name
        ORDER BY earliest_expiry
        """,
        (warning_threshold_mjd, now_mjd),
    ).fetchall()

    # Find already expired windows
    expired = conn.execute(
        """
        SELECT DISTINCT set_name, MAX(valid_end_mjd) as latest_expiry
        FROM caltables
        WHERE status = 'active'
          AND valid_end_mjd IS NOT NULL
          AND valid_end_mjd < ?
        GROUP BY set_name
        ORDER BY latest_expiry DESC
        """,
        (now_mjd,),
    ).fetchall()

    conn.close()

    expiring_sets = [
        {
            "set_name": row["set_name"],
            "expires_mjd": row["earliest_expiry"],
            "expires_iso": Time(row["earliest_expiry"], format="mjd").isot,
            "hours_remaining": (row["earliest_expiry"] - now_mjd) * 24,
        }
        for row in expiring
    ]

    expired_sets = [
        {
            "set_name": row["set_name"],
            "expired_mjd": row["latest_expiry"],
            "expired_iso": Time(row["latest_expiry"], format="mjd").isot,
            "hours_ago": (now_mjd - row["latest_expiry"]) * 24,
        }
        for row in expired
    ]

    return {
        "success": True,
        "expiring_soon": expiring_sets,
        "already_expired": expired_sets,
        "expiring_count": len(expiring_sets),
        "expired_count": len(expired_sets),
        "warning_hours": warning_hours,
        "executed_at": datetime.utcnow().isoformat() + "Z",
    }


async def _execute_send_alert(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send an alert via configured notification channels.

    Params:
        severity: Alert severity (info, warning, critical)
        title: Alert title
        message: Alert message body
        channels: List of channels to send to (webhook, email, slack)
        webhook_url: Webhook URL for webhook channel
        email_to: Email recipient for email channel
    """
    severity = params.get("severity", "info")
    title = params.get("title", "DSA-110 Pipeline Alert")
    message = params.get("message", "")
    channels = params.get("channels", ["webhook"])

    logger.info(f"Sending alert: {severity} - {title}")

    results = {}

    if "webhook" in channels:
        webhook_url = params.get("webhook_url")
        if webhook_url:
            result = await _send_webhook_alert(webhook_url, severity, title, message)
            results["webhook"] = result
        else:
            results["webhook"] = {"sent": False, "error": "No webhook URL configured"}

    if "email" in channels:
        email_to = params.get("email_to")
        if email_to:
            result = await _send_email_alert(email_to, severity, title, message)
            results["email"] = result
        else:
            results["email"] = {"sent": False, "error": "No email recipient configured"}

    if "slack" in channels:
        slack_webhook = params.get("slack_webhook")
        if slack_webhook:
            result = await _send_slack_alert(slack_webhook, severity, title, message)
            results["slack"] = result
        else:
            results["slack"] = {"sent": False, "error": "No Slack webhook configured"}

    return {
        "success": any(r.get("sent", False) for r in results.values()),
        "channels": results,
        "executed_at": datetime.utcnow().isoformat() + "Z",
    }


async def _send_webhook_alert(
    url: str, severity: str, title: str, message: str
) -> Dict[str, Any]:
    """Send alert via webhook."""
    import httpx

    payload = {
        "severity": severity,
        "title": title,
        "message": message,
        "source": "dsa110-contimg",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            return {
                "sent": response.status_code < 400,
                "status_code": response.status_code,
            }
    except Exception as e:
        return {"sent": False, "error": str(e)}


async def _send_email_alert(
    to: str, severity: str, title: str, message: str
) -> Dict[str, Any]:
    """Send alert via email (placeholder - requires SMTP config)."""
    # TODO: Implement email sending with smtplib
    logger.warning("Email alerting not implemented - skipping")
    return {"sent": False, "error": "Email alerting not implemented"}


async def _send_slack_alert(
    webhook_url: str, severity: str, title: str, message: str
) -> Dict[str, Any]:
    """Send alert via Slack webhook."""
    import httpx

    # Color based on severity
    colors = {
        "info": "#36a64f",  # green
        "warning": "#ff9900",  # orange
        "critical": "#ff0000",  # red
    }

    payload = {
        "attachments": [
            {
                "color": colors.get(severity, "#808080"),
                "title": title,
                "text": message,
                "footer": "DSA-110 Continuum Imaging Pipeline",
                "ts": int(datetime.utcnow().timestamp()),
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            return {
                "sent": response.status_code == 200,
                "status_code": response.status_code,
            }
    except Exception as e:
        return {"sent": False, "error": str(e)}


# ============================================================================
# Task Registration for ABSURD Worker
# ============================================================================


def register_monitoring_tasks(worker) -> None:
    """
    Register monitoring tasks with ABSURD worker.

    Call this from worker initialization to enable monitoring task execution.
    """
    # Register task handlers
    worker.register_handler(TASK_FLUX_MONITORING_CHECK, _execute_flux_monitoring_check)
    worker.register_handler(TASK_HEALTH_CHECK, _execute_health_check)
    worker.register_handler(TASK_VALIDITY_WINDOW_CHECK, _execute_validity_window_check)
    worker.register_handler(TASK_SEND_ALERT, _execute_send_alert)

    logger.info("Registered monitoring tasks with ABSURD worker")


# ============================================================================
# Schedule Definitions
# ============================================================================

# Default schedules for monitoring tasks
DEFAULT_MONITORING_SCHEDULES = [
    {
        "name": "flux-monitoring-hourly",
        "task_name": TASK_FLUX_MONITORING_CHECK,
        "cron_expression": "0 * * * *",  # Every hour at :00
        "params": {"create_alerts": True},
        "description": "Hourly flux monitoring check",
    },
    {
        "name": "health-check-5min",
        "task_name": TASK_HEALTH_CHECK,
        "cron_expression": "*/5 * * * *",  # Every 5 minutes
        "params": {"include_docker": True, "include_systemd": True},
        "description": "System health check every 5 minutes",
    },
    {
        "name": "validity-window-check-hourly",
        "task_name": TASK_VALIDITY_WINDOW_CHECK,
        "cron_expression": "30 * * * *",  # Every hour at :30
        "params": {"warning_hours": 2},
        "description": "Check for expiring validity windows",
    },
]


async def setup_monitoring_schedules(scheduler) -> None:
    """
    Set up default monitoring schedules.

    Args:
        scheduler: TaskScheduler instance
    """
    for schedule in DEFAULT_MONITORING_SCHEDULES:
        try:
            await scheduler.create_schedule(
                name=schedule["name"],
                queue_name="dsa110-monitoring",
                task_name=schedule["task_name"],
                cron_expression=schedule["cron_expression"],
                params=schedule["params"],
                description=schedule.get("description"),
            )
            logger.info(f"Created schedule: {schedule['name']}")
        except Exception as e:
            # Schedule might already exist
            logger.debug(f"Could not create schedule {schedule['name']}: {e}")

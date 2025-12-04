"""
Alerting Module for DSA-110 Continuum Imaging Pipeline.

This module provides:
1. Alert rule definitions
2. Alert evaluation
3. Notification dispatch (webhook, email, Slack)
4. Alert history tracking
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """Alert states."""
    FIRING = "firing"
    RESOLVED = "resolved"
    PENDING = "pending"


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[], bool]  # Returns True when alert should fire
    message_template: str
    cooldown_seconds: int = 300  # Minimum time between alerts
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """An alert instance."""
    rule_name: str
    severity: AlertSeverity
    state: AlertState
    message: str
    fired_at: float
    resolved_at: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "state": self.state.value,
            "message": self.message,
            "fired_at": datetime.fromtimestamp(self.fired_at).isoformat(),
            "resolved_at": datetime.fromtimestamp(self.resolved_at).isoformat() if self.resolved_at else None,
            "labels": self.labels,
            "annotations": self.annotations,
        }


class AlertManager:
    """Manages alert rules and notifications."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        webhook_url: Optional[str] = None,
        slack_webhook: Optional[str] = None,
    ):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.last_fired: Dict[str, float] = {}  # For cooldown tracking

        self.db_path = db_path
        self.webhook_url = webhook_url
        self.slack_webhook = slack_webhook

        if db_path:
            self._init_db()

    def _init_db(self):
        """Initialize alert history database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                state TEXT NOT NULL,
                message TEXT,
                fired_at REAL NOT NULL,
                resolved_at REAL,
                labels_json TEXT,
                created_at REAL DEFAULT (unixepoch())
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_rule ON alert_history(rule_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_fired ON alert_history(fired_at)
        """)
        conn.commit()
        conn.close()

    def register_rule(self, rule: AlertRule):
        """Register an alert rule."""
        self.rules[rule.name] = rule
        logger.info(f"Registered alert rule: {rule.name}")

    def evaluate_rules(self) -> List[Alert]:
        """Evaluate all rules and return new/changed alerts."""
        alerts = []
        current_time = time.time()

        for name, rule in self.rules.items():
            try:
                condition_met = rule.condition()
            except Exception as e:
                logger.error(f"Error evaluating rule {name}: {e}")
                continue

            # Check if alert should fire
            if condition_met:
                if name not in self.active_alerts:
                    # Check cooldown
                    last = self.last_fired.get(name, 0)
                    if current_time - last < rule.cooldown_seconds:
                        continue

                    # Create new alert
                    alert = Alert(
                        rule_name=name,
                        severity=rule.severity,
                        state=AlertState.FIRING,
                        message=rule.message_template,
                        fired_at=current_time,
                        labels=rule.labels.copy(),
                    )
                    self.active_alerts[name] = alert
                    self.last_fired[name] = current_time
                    alerts.append(alert)

                    logger.warning(f"Alert firing: {name} - {rule.message_template}")
                    self._save_alert(alert)
            else:
                # Check if alert should resolve
                if name in self.active_alerts:
                    alert = self.active_alerts[name]
                    alert.state = AlertState.RESOLVED
                    alert.resolved_at = current_time
                    alerts.append(alert)

                    del self.active_alerts[name]
                    logger.info(f"Alert resolved: {name}")
                    self._update_alert_resolved(alert)

        return alerts

    def _save_alert(self, alert: Alert):
        """Save alert to history database."""
        if not self.db_path:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO alert_history (rule_name, severity, state, message, fired_at, labels_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert.rule_name,
                alert.severity.value,
                alert.state.value,
                alert.message,
                alert.fired_at,
                json.dumps(alert.labels),
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")

    def _update_alert_resolved(self, alert: Alert):
        """Update alert as resolved in database."""
        if not self.db_path:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                UPDATE alert_history
                SET state = ?, resolved_at = ?
                WHERE rule_name = ? AND resolved_at IS NULL
            """, (
                AlertState.RESOLVED.value,
                alert.resolved_at,
                alert.rule_name,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update alert: {e}")

    async def send_notifications(self, alerts: List[Alert]):
        """Send notifications for alerts."""
        import httpx

        for alert in alerts:
            # Webhook notification
            if self.webhook_url:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            self.webhook_url,
                            json=alert.to_dict(),
                            timeout=10,
                        )
                except Exception as e:
                    logger.error(f"Failed to send webhook: {e}")

            # Slack notification
            if self.slack_webhook:
                try:
                    color = {
                        AlertSeverity.INFO: "#36a64f",
                        AlertSeverity.WARNING: "#ff9800",
                        AlertSeverity.CRITICAL: "#f44336",
                    }.get(alert.severity, "#808080")

                    state_emoji = "🔥" if alert.state == AlertState.FIRING else "✅"

                    payload = {
                        "attachments": [{
                            "color": color,
                            "title": f"{state_emoji} {alert.rule_name}",
                            "text": alert.message,
                            "fields": [
                                {"title": "Severity", "value": alert.severity.value, "short": True},
                                {"title": "State", "value": alert.state.value, "short": True},
                            ],
                            "ts": int(alert.fired_at),
                        }]
                    }

                    async with httpx.AsyncClient() as client:
                        await client.post(
                            self.slack_webhook,
                            json=payload,
                            timeout=10,
                        )
                except Exception as e:
                    logger.error(f"Failed to send Slack notification: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts."""
        return list(self.active_alerts.values())

    def get_alert_history(
        self,
        limit: int = 100,
        rule_name: Optional[str] = None,
    ) -> List[dict]:
        """Get alert history from database."""
        if not self.db_path:
            return []

        try:
            conn = sqlite3.connect(self.db_path)

            if rule_name:
                cursor = conn.execute("""
                    SELECT rule_name, severity, state, message, fired_at, resolved_at, labels_json
                    FROM alert_history
                    WHERE rule_name = ?
                    ORDER BY fired_at DESC
                    LIMIT ?
                """, (rule_name, limit))
            else:
                cursor = conn.execute("""
                    SELECT rule_name, severity, state, message, fired_at, resolved_at, labels_json
                    FROM alert_history
                    ORDER BY fired_at DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "rule_name": r[0],
                    "severity": r[1],
                    "state": r[2],
                    "message": r[3],
                    "fired_at": datetime.fromtimestamp(r[4]).isoformat(),
                    "resolved_at": datetime.fromtimestamp(r[5]).isoformat() if r[5] else None,
                    "labels": json.loads(r[6]) if r[6] else {},
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            return []


def create_default_alert_rules(
    hdf5_db_path: str,
    incoming_dir: str,
    sync_threshold: float = 95.0,
) -> List[AlertRule]:
    """
    Create default alert rules for the pipeline.

    Args:
        hdf5_db_path: Path to HDF5 index database
        incoming_dir: Path to HDF5 storage directory
        sync_threshold: Alert when sync percentage drops below this

    Returns:
        List of AlertRule instances
    """
    from dsa110_contimg.database.storage_validator import get_storage_metrics
    from dsa110_contimg.monitoring.service_health import (
        ServiceStatus,
        check_docker_container,
        check_systemd_service,
    )

    rules = []

    # Storage sync alert
    def check_storage_sync():
        try:
            metrics = get_storage_metrics(hdf5_db_path, incoming_dir)
            if metrics["files_on_disk"] == 0:
                return False
            sync_pct = (metrics["files_in_db_stored"] / metrics["files_on_disk"]) * 100
            return sync_pct < sync_threshold
        except Exception:
            return False

    rules.append(AlertRule(
        name="storage_sync_low",
        description="Storage synchronization percentage is below threshold",
        severity=AlertSeverity.WARNING,
        condition=check_storage_sync,
        message_template=f"Storage sync percentage below {sync_threshold}%",
        cooldown_seconds=3600,  # 1 hour cooldown
        labels={"component": "storage"},
    ))

    # API service alert
    def check_api_service():
        result = check_systemd_service("contimg-api")
        return result.status != ServiceStatus.RUNNING

    rules.append(AlertRule(
        name="api_service_down",
        description="Contimg API service is not running",
        severity=AlertSeverity.CRITICAL,
        condition=check_api_service,
        message_template="contimg-api systemd service is not running",
        cooldown_seconds=60,
        labels={"component": "api", "service": "contimg-api"},
    ))

    # Stream service alert
    def check_stream_service():
        result = check_systemd_service("contimg-stream")
        return result.status != ServiceStatus.RUNNING

    rules.append(AlertRule(
        name="stream_service_down",
        description="Contimg streaming service is not running",
        severity=AlertSeverity.CRITICAL,
        condition=check_stream_service,
        message_template="contimg-stream systemd service is not running",
        cooldown_seconds=60,
        labels={"component": "streaming", "service": "contimg-stream"},
    ))

    # RAGFlow container alert
    def check_ragflow_container():
        result = check_docker_container("ragflow-ragflow-1")
        return result.status != ServiceStatus.RUNNING and result.status != ServiceStatus.STOPPED

    rules.append(AlertRule(
        name="ragflow_container_error",
        description="RAGFlow container is in error state",
        severity=AlertSeverity.WARNING,
        condition=check_ragflow_container,
        message_template="RAGFlow container is not healthy",
        cooldown_seconds=300,
        labels={"component": "ragflow", "container": "ragflow-ragflow-1"},
    ))

    return rules


def create_throughput_alert_rules(
    metrics_collector: "PipelineMetricsCollector",  # noqa: F821
    backlog_threshold: int = 10,
    rate_threshold: float = 0.8,
) -> List[AlertRule]:
    """
    Create alert rules for pipeline throughput monitoring.

    These rules address Issue #12: Inadequate Observability by alerting
    when the pipeline is falling behind incoming data.

    Args:
        metrics_collector: The PipelineMetricsCollector instance
        backlog_threshold: Alert when backlog exceeds this many groups
        rate_threshold: Alert when processing rate / arrival rate < this

    Returns:
        List of AlertRule instances for throughput monitoring
    """

    rules = []

    # Backlog growing alert
    def check_backlog_growing():
        try:
            metrics = metrics_collector.get_ingest_rate(hours=1.0)
            return metrics.backlog_groups > backlog_threshold and metrics.backlog_growing
        except Exception:
            return False

    rules.append(AlertRule(
        name="pipeline_backlog_growing",
        description="Pipeline processing backlog is growing",
        severity=AlertSeverity.WARNING,
        condition=check_backlog_growing,
        message_template=f"Pipeline backlog exceeds {backlog_threshold} groups and is growing",
        cooldown_seconds=600,  # 10 minute cooldown
        labels={"component": "pipeline", "metric": "backlog"},
    ))

    # Processing rate too slow
    def check_processing_rate():
        try:
            metrics = metrics_collector.get_ingest_rate(hours=1.0)
            return (
                metrics.groups_arrived > 0
                and metrics.rate_ratio < rate_threshold
            )
        except Exception:
            return False

    rules.append(AlertRule(
        name="pipeline_processing_slow",
        description="Pipeline processing rate is below arrival rate",
        severity=AlertSeverity.WARNING,
        condition=check_processing_rate,
        message_template=f"Processing rate is below {rate_threshold*100:.0f}% of arrival rate",
        cooldown_seconds=1800,  # 30 minute cooldown
        labels={"component": "pipeline", "metric": "rate"},
    ))

    # Critical backlog (large backup)
    def check_critical_backlog():
        try:
            metrics = metrics_collector.get_ingest_rate(hours=1.0)
            return metrics.backlog_groups > backlog_threshold * 3  # 3x normal threshold
        except Exception:
            return False

    rules.append(AlertRule(
        name="pipeline_backlog_critical",
        description="Pipeline backlog has reached critical levels",
        severity=AlertSeverity.CRITICAL,
        condition=check_critical_backlog,
        message_template=f"Pipeline backlog exceeds {backlog_threshold * 3} groups - intervention needed",
        cooldown_seconds=300,  # 5 minute cooldown for critical
        labels={"component": "pipeline", "metric": "backlog"},
    ))

    return rules

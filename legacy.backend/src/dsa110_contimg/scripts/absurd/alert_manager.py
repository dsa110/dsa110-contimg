#!/usr/bin/env python
"""
Absurd Pipeline Alert Manager

Monitors system health and sends alerts when thresholds are exceeded.
Supports multiple notification channels: log file, email, Slack.

Environment Variables for SMTP:
    ABSURD_SMTP_HOST: SMTP server hostname (default: localhost)
    ABSURD_SMTP_PORT: SMTP server port (default: 587 for TLS, 25 for unencrypted)
    ABSURD_SMTP_USER: SMTP username (optional, for authenticated SMTP)
    ABSURD_SMTP_PASSWORD: SMTP password (optional, for authenticated SMTP)
    ABSURD_SMTP_USE_TLS: Use STARTTLS (default: true if port is 587)
    ABSURD_SMTP_FROM: From address (default: absurd-alerts@dsa110)
    ABSURD_ALERT_EMAIL_TO: Comma-separated list of email recipients

Environment Variables for Slack:
    ABSURD_SLACK_WEBHOOK_URL: Slack incoming webhook URL
    ABSURD_SLACK_CHANNEL: Slack channel to post to (optional, uses webhook default)
"""

import asyncio
import json
import logging
import os
import smtplib
import ssl
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class SMTPConfig:
    """SMTP server configuration."""

    host: str = "localhost"
    port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    from_address: str = "absurd-alerts@dsa110"

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """Load SMTP configuration from environment variables."""
        port = int(os.environ.get("ABSURD_SMTP_PORT", "587"))
        # Default TLS to True if using standard TLS port
        default_tls = port in (587, 465)

        return cls(
            host=os.environ.get("ABSURD_SMTP_HOST", "localhost"),
            port=port,
            username=os.environ.get("ABSURD_SMTP_USER"),
            password=os.environ.get("ABSURD_SMTP_PASSWORD"),
            use_tls=os.environ.get("ABSURD_SMTP_USE_TLS", str(default_tls)).lower()
            in ("true", "1", "yes"),
            from_address=os.environ.get("ABSURD_SMTP_FROM", "absurd-alerts@dsa110"),
        )

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured for use."""
        # At minimum, we need a host that's not the default localhost
        # OR we have authentication credentials (indicating intentional config)
        return self.host != "localhost" or self.username is not None


@dataclass
class SlackConfig:
    """Slack notification configuration."""

    webhook_url: Optional[str] = None
    channel: Optional[str] = None
    username: str = "DSA-110 Absurd Monitor"
    icon_emoji: str = ":robot_face:"

    @classmethod
    def from_env(cls) -> "SlackConfig":
        """Load Slack configuration from environment variables."""
        return cls(
            webhook_url=os.environ.get("ABSURD_SLACK_WEBHOOK_URL"),
            channel=os.environ.get("ABSURD_SLACK_CHANNEL"),
            username=os.environ.get("ABSURD_SLACK_USERNAME", "DSA-110 Absurd Monitor"),
            icon_emoji=os.environ.get("ABSURD_SLACK_ICON", ":robot_face:"),
        )

    def is_configured(self) -> bool:
        """Check if Slack is properly configured for use."""
        return self.webhook_url is not None


@dataclass
class AlertThresholds:
    """Alert threshold configuration."""

    queue_depth_warning: int = 50
    queue_depth_critical: int = 100
    failure_rate_warning: float = 0.10  # 10%
    failure_rate_critical: float = 0.25  # 25%
    disk_usage_warning: int = 85  # percent
    disk_usage_critical: int = 95  # percent
    worker_min_count: int = 1
    task_timeout_hours: int = 2


@dataclass
class Alert:
    """Alert data structure."""

    level: str  # INFO, WARNING, CRITICAL
    category: str  # queue, workers, disk, etc.
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class AlertManager:
    """Manages monitoring and alerting for Absurd pipeline."""

    def __init__(
        self,
        database_url: str,
        queue_name: str,
        thresholds: Optional[AlertThresholds] = None,
        alert_log: str = "/var/log/absurd_alerts.log",
        email_enabled: bool = False,
        email_to: Optional[List[str]] = None,
        smtp_config: Optional[SMTPConfig] = None,
        slack_config: Optional[SlackConfig] = None,
        slack_enabled: bool = False,
    ):
        self.database_url = database_url
        self.queue_name = queue_name
        self.thresholds = thresholds or AlertThresholds()
        self.alert_log = Path(alert_log)

        # Email configuration
        self.email_enabled = email_enabled
        self.email_to = email_to or self._parse_email_recipients()
        self.smtp_config = smtp_config or SMTPConfig.from_env()

        # Slack configuration
        self.slack_enabled = slack_enabled
        self.slack_config = slack_config or SlackConfig.from_env()

        # Auto-enable based on configuration
        if not email_enabled and self.smtp_config.is_configured() and self.email_to:
            self.email_enabled = True
        if not slack_enabled and self.slack_config.is_configured():
            self.slack_enabled = True

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(self.alert_log), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

        self._pool: Optional[asyncpg.Pool] = None
        self.alert_history: List[Alert] = []

        # Log enabled notification channels
        channels = ["log"]
        if self.email_enabled:
            channels.append(f"email ({len(self.email_to)} recipients)")
        if self.slack_enabled:
            channels.append("slack")
        self.logger.info(f"Alert channels enabled: {', '.join(channels)}")

    def _parse_email_recipients(self) -> List[str]:
        """Parse email recipients from environment variable."""
        recipients_str = os.environ.get("ABSURD_ALERT_EMAIL_TO", "")
        if not recipients_str:
            return []
        return [r.strip() for r in recipients_str.split(",") if r.strip()]

    async def connect(self):
        """Connect to database."""
        self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=3)
        self.logger.info("Alert manager connected to database")

    async def close(self):
        """Close database connection."""
        if self._pool:
            await self._pool.close()

    async def check_queue_depth(self) -> Optional[Alert]:
        """Check if queue depth exceeds thresholds."""
        async with self._pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT COUNT(*) as depth
                FROM absurd.t_tasks
                WHERE queue_name = $1 AND status = 'pending'
                """,
                self.queue_name,
            )
            depth = result["depth"]

        if depth >= self.thresholds.queue_depth_critical:
            return Alert(
                level="CRITICAL",
                category="queue",
                message=f"Queue depth critical: {depth} pending tasks",
                timestamp=datetime.now(),
                details={"depth": depth},
            )
        elif depth >= self.thresholds.queue_depth_warning:
            return Alert(
                level="WARNING",
                category="queue",
                message=f"Queue depth high: {depth} pending tasks",
                timestamp=datetime.now(),
                details={"depth": depth},
            )
        return None

    async def check_failure_rate(self) -> Optional[Alert]:
        """Check task failure rate."""
        async with self._pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM absurd.t_tasks
                WHERE queue_name = $1 
                  AND created_at > NOW() - INTERVAL '1 hour'
                """,
                self.queue_name,
            )

            total = result["total"] or 0
            failed = result["failed"] or 0

        if total == 0:
            return None

        failure_rate = failed / total

        if failure_rate >= self.thresholds.failure_rate_critical:
            return Alert(
                level="CRITICAL",
                category="failures",
                message=f"High failure rate: {failure_rate*100:.1f}% " f"({failed}/{total} tasks)",
                timestamp=datetime.now(),
                details={"rate": failure_rate, "failed": failed, "total": total},
            )
        elif failure_rate >= self.thresholds.failure_rate_warning:
            return Alert(
                level="WARNING",
                category="failures",
                message=f"Elevated failure rate: {failure_rate*100:.1f}% "
                f"({failed}/{total} tasks)",
                timestamp=datetime.now(),
                details={"rate": failure_rate, "failed": failed, "total": total},
            )
        return None

    def check_disk_usage(self) -> Optional[Alert]:
        """Check disk usage for key paths."""
        paths_to_check = ["/data", "/stage"]
        alerts = []

        for path in paths_to_check:
            try:
                result = subprocess.run(["df", path], capture_output=True, text=True, check=True)
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    fields = lines[1].split()
                    usage_percent = int(fields[4].rstrip("%"))

                    if usage_percent >= self.thresholds.disk_usage_critical:
                        alerts.append(
                            Alert(
                                level="CRITICAL",
                                category="disk",
                                message=f"Disk {path} critically full: {usage_percent}%",
                                timestamp=datetime.now(),
                                details={"path": path, "usage": usage_percent},
                            )
                        )
                    elif usage_percent >= self.thresholds.disk_usage_warning:
                        alerts.append(
                            Alert(
                                level="WARNING",
                                category="disk",
                                message=f"Disk {path} running low: {usage_percent}%",
                                timestamp=datetime.now(),
                                details={"path": path, "usage": usage_percent},
                            )
                        )
            except Exception as e:
                self.logger.error(f"Error checking disk {path}: {e}")

        return alerts[0] if alerts else None

    def check_worker_count(self) -> Optional[Alert]:
        """Check if sufficient workers are running."""
        try:
            result = subprocess.run(
                ["systemctl", "list-units", "--state=active", "dsa110-absurd-worker@*"],
                capture_output=True,
                text=True,
                check=True,
            )
            worker_count = result.stdout.count("dsa110-absurd-worker")

            if worker_count < self.thresholds.worker_min_count:
                return Alert(
                    level="CRITICAL",
                    category="workers",
                    message=f"Insufficient workers: {worker_count} active "
                    f"(min: {self.thresholds.worker_min_count})",
                    timestamp=datetime.now(),
                    details={"count": worker_count},
                )
        except Exception as e:
            self.logger.error(f"Error checking worker count: {e}")
            return Alert(
                level="CRITICAL",
                category="workers",
                message="Unable to check worker status",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )
        return None

    async def check_stale_tasks(self) -> Optional[Alert]:
        """Check for tasks stuck in claimed state too long."""
        async with self._pool.acquire() as conn:
            result = await conn.fetch(
                """
                SELECT task_id, task_name, claimed_at, worker_id
                FROM absurd.t_tasks
                WHERE queue_name = $1 
                  AND status = 'claimed'
                  AND claimed_at < NOW() - INTERVAL '%s hours'
                """,
                self.queue_name,
                self.thresholds.task_timeout_hours,
            )

        if result:
            task_count = len(result)
            task_list = ", ".join([r["task_name"] for r in result[:5]])
            return Alert(
                level="WARNING",
                category="stale_tasks",
                message=f"{task_count} tasks stuck in claimed state: {task_list}...",
                timestamp=datetime.now(),
                details={"count": task_count, "tasks": [dict(r) for r in result]},
            )
        return None

    async def run_checks(self) -> List[Alert]:
        """Run all health checks."""
        alerts = []

        # Async checks
        alert = await self.check_queue_depth()
        if alert:
            alerts.append(alert)

        alert = await self.check_failure_rate()
        if alert:
            alerts.append(alert)

        alert = await self.check_stale_tasks()
        if alert:
            alerts.append(alert)

        # Sync checks
        alert = self.check_disk_usage()
        if alert:
            alerts.append(alert)

        alert = self.check_worker_count()
        if alert:
            alerts.append(alert)

        return alerts

    def send_alert(self, alert: Alert):
        """Send alert through configured channels."""
        # Log to file
        log_method = {
            "INFO": self.logger.info,
            "WARNING": self.logger.warning,
            "CRITICAL": self.logger.critical,
        }.get(alert.level, self.logger.info)

        log_method(f"[{alert.category}] {alert.message}")

        # Add to history
        self.alert_history.append(alert)

        # Email notification (if enabled and critical)
        if self.email_enabled and alert.level == "CRITICAL":
            self.send_email_alert(alert)

    def send_email_alert(self, alert: Alert):
        """Send email notification."""
        if not self.email_to:
            return

        subject = f"[DSA-110 Absurd] {alert.level}: {alert.category}"
        body = f"""
Absurd Pipeline Alert

Level: {alert.level}
Category: {alert.category}
Time: {alert.timestamp}

Message:
{alert.message}

Details:
{alert.details}

---
This is an automated alert from the DSA-110 Absurd pipeline monitor.
        """

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.smtp_config.from_address
            msg["To"] = ", ".join(self.email_to)

            # Connect to SMTP server and send
            if self.smtp_config.port == 465:
                # Direct SSL connection
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_config.host,
                    self.smtp_config.port,
                    context=context,
                ) as smtp:
                    if self.smtp_config.username and self.smtp_config.password:
                        smtp.login(self.smtp_config.username, self.smtp_config.password)
                    smtp.send_message(msg)
            else:
                # Standard connection with optional STARTTLS
                with smtplib.SMTP(self.smtp_config.host, self.smtp_config.port) as smtp:
                    if self.smtp_config.use_tls:
                        context = ssl.create_default_context()
                        smtp.starttls(context=context)
                    if self.smtp_config.username and self.smtp_config.password:
                        smtp.login(self.smtp_config.username, self.smtp_config.password)
                    smtp.send_message(msg)

            self.logger.info(f"Email alert sent to {self.email_to}")
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP authentication failed: {e}")
        except smtplib.SMTPConnectError as e:
            self.logger.error(f"Failed to connect to SMTP server: {e}")
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error sending alert: {e}")
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    async def send_slack_alert(self, alert: Alert):
        """Send Slack notification via webhook.

        Requires the 'httpx' package for async HTTP requests.
        Falls back to synchronous requests.urlopen if httpx is not available.
        """
        if not self.slack_config.webhook_url:
            return

        # Determine emoji based on alert level
        level_emoji = {
            "INFO": ":information_source:",
            "WARNING": ":warning:",
            "CRITICAL": ":rotating_light:",
        }.get(alert.level, ":bell:")

        # Build Slack message payload
        payload: Dict[str, Any] = {
            "username": self.slack_config.username,
            "icon_emoji": self.slack_config.icon_emoji,
            "attachments": [
                {
                    "color": {"INFO": "#36a64f", "WARNING": "#ff9500", "CRITICAL": "#ff0000"}.get(
                        alert.level, "#808080"
                    ),
                    "title": f"{level_emoji} {alert.level}: {alert.category}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Category", "value": alert.category, "short": True},
                        {"title": "Level", "value": alert.level, "short": True},
                        {"title": "Time", "value": alert.timestamp.isoformat(), "short": True},
                    ],
                    "footer": "DSA-110 Absurd Pipeline Monitor",
                    "ts": int(alert.timestamp.timestamp()),
                }
            ],
        }

        # Add details as fields if present
        if alert.details:
            for key, value in alert.details.items():
                payload["attachments"][0]["fields"].append(
                    {
                        "title": key,
                        "value": str(value),
                        "short": True,
                    }
                )

        # Override channel if specified
        if self.slack_config.channel:
            payload["channel"] = self.slack_config.channel

        try:
            if HTTPX_AVAILABLE:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.slack_config.webhook_url,
                        json=payload,
                        timeout=10.0,
                    )
                    response.raise_for_status()
            else:
                # Fallback to synchronous request
                import urllib.error
                import urllib.request

                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    self.slack_config.webhook_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status != 200:
                        raise Exception(f"Slack webhook returned status {response.status}")

            self.logger.info("Slack alert sent successfully")
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    async def monitor_loop(self, interval_sec: int = 60):
        """Main monitoring loop."""
        self.logger.info(f"Starting alert manager (check interval: {interval_sec}s)")

        while True:
            try:
                alerts = await self.run_checks()

                for alert in alerts:
                    await self.send_alert_async(alert)

                if not alerts:
                    self.logger.debug("All checks passed")

            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}", exc_info=True)

            await asyncio.sleep(interval_sec)

    async def send_alert_async(self, alert: Alert):
        """Send alert through all configured channels (async version)."""
        # Log to file (sync - fast)
        log_method = {
            "INFO": self.logger.info,
            "WARNING": self.logger.warning,
            "CRITICAL": self.logger.critical,
        }.get(alert.level, self.logger.info)

        log_method(f"[{alert.category}] {alert.message}")

        # Add to history
        self.alert_history.append(alert)

        # Email notification (if enabled and critical)
        if self.email_enabled and alert.level == "CRITICAL":
            self.send_email_alert(alert)

        # Slack notification (if enabled)
        if self.slack_enabled and alert.level in ("WARNING", "CRITICAL"):
            await self.send_slack_alert(alert)


async def main():
    """Main entry point."""
    database_url = os.environ.get(
        "ABSURD_DATABASE_URL", "postgresql://user:password@localhost/dsa110_absurd"
    )
    queue_name = os.environ.get("ABSURD_QUEUE_NAME", "dsa110-pipeline")
    alert_log = os.environ.get("ABSURD_ALERT_LOG", "/var/log/absurd_alerts.log")

    # Create alert manager - configuration is loaded from environment
    manager = AlertManager(
        database_url=database_url,
        queue_name=queue_name,
        alert_log=alert_log,
        # email_enabled and slack_enabled will auto-enable if configured via env
    )

    await manager.connect()

    try:
        await manager.monitor_loop(interval_sec=60)
    except KeyboardInterrupt:
        print("\nStopping alert manager...")
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())

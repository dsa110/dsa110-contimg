"""
Alerting module for DSA-110 continuum imaging pipeline.

Supports multiple alert channels (Slack, email, etc.) with severity-based routing.
Designed for lights-out operation with minimal human intervention.
"""

import json
import logging
import os
import smtplib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib import request
from urllib.error import URLError

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


@dataclass
class Alert:
    """Represents a single alert."""
    severity: AlertSeverity
    message: str
    category: str
    timestamp: float = field(default_factory=time.time)
    context: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary."""
        return {
            "severity": self.severity.name,
            "message": self.message,
            "category": self.category,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "context": self.context or {},
        }


class AlertChannel:
    """Base class for alert channels."""
    
    def __init__(self, name: str, min_severity: AlertSeverity = AlertSeverity.WARNING):
        self.name = name
        self.min_severity = min_severity
        self.enabled = True
    
    def enabled_for_severity(self, severity: AlertSeverity) -> bool:
        """Check if this channel should handle this severity."""
        return self.enabled and severity.value >= self.min_severity.value
    
    def send(self, alert: Alert) -> bool:
        """Send alert through this channel. Returns success status."""
        raise NotImplementedError


class SlackChannel(AlertChannel):
    """Slack webhook alert channel."""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        min_severity: AlertSeverity = AlertSeverity.WARNING,
        username: str = "DSA-110 Pipeline",
        icon_emoji: str = ":telescope:",
    ):
        super().__init__("slack", min_severity)
        self.webhook_url = webhook_url or os.getenv("CONTIMG_SLACK_WEBHOOK_URL")
        self.username = username
        self.icon_emoji = icon_emoji
        
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured, disabling Slack alerts")
            self.enabled = False
    
    def _format_message(self, alert: Alert) -> Dict:
        """Format alert as Slack message."""
        # Color coding by severity
        color_map = {
            AlertSeverity.DEBUG: "#808080",
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.ERROR: "#ff0000",
            AlertSeverity.CRITICAL: "#8B0000",
        }
        
        # Emoji by severity
        emoji_map = {
            AlertSeverity.DEBUG: ":mag:",
            AlertSeverity.INFO: ":information_source:",
            AlertSeverity.WARNING: ":warning:",
            AlertSeverity.ERROR: ":x:",
            AlertSeverity.CRITICAL: ":rotating_light:",
        }
        
        fields = []
        if alert.context:
            for key, value in alert.context.items():
                fields.append({
                    "title": key.replace("_", " ").title(),
                    "value": str(value),
                    "short": len(str(value)) < 40
                })
        
        attachment = {
            "color": color_map.get(alert.severity, "#808080"),
            "title": f"{emoji_map.get(alert.severity, '')} {alert.severity.name}: {alert.category}",
            "text": alert.message,
            "fields": fields,
            "footer": "DSA-110 Continuum Imaging Pipeline",
            "ts": int(alert.timestamp),
        }
        
        return {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [attachment],
        }
    
    def send(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        if not self.enabled:
            return False
        
        try:
            payload = self._format_message(alert)
            data = json.dumps(payload).encode('utf-8')
            
            req = request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.debug(f"Sent {alert.severity.name} alert to Slack: {alert.message}")
                    return True
                else:
                    logger.error(f"Slack webhook returned status {response.status}")
                    return False
        
        except URLError as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack alert: {e}")
            return False


class EmailChannel(AlertChannel):
    """Email alert channel."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_addr: Optional[str] = None,
        to_addrs: Optional[List[str]] = None,
        min_severity: AlertSeverity = AlertSeverity.ERROR,
    ):
        super().__init__("email", min_severity)
        self.smtp_host = smtp_host or os.getenv("CONTIMG_SMTP_HOST")
        self.smtp_port = int(os.getenv("CONTIMG_SMTP_PORT", str(smtp_port)))
        self.smtp_user = smtp_user or os.getenv("CONTIMG_SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("CONTIMG_SMTP_PASSWORD")
        self.from_addr = from_addr or os.getenv("CONTIMG_ALERT_FROM_EMAIL", "dsa110-pipeline@example.com")
        
        to_addrs_env = os.getenv("CONTIMG_ALERT_TO_EMAILS")
        if to_addrs_env:
            self.to_addrs = [addr.strip() for addr in to_addrs_env.split(",")]
        else:
            self.to_addrs = to_addrs or []
        
        if not all([self.smtp_host, self.to_addrs]):
            logger.warning("Email configuration incomplete, disabling email alerts")
            self.enabled = False
    
    def send(self, alert: Alert) -> bool:
        """Send alert via email."""
        if not self.enabled:
            return False
        
        try:
            subject = f"[{alert.severity.name}] DSA-110: {alert.category}"
            
            body_lines = [
                f"Severity: {alert.severity.name}",
                f"Category: {alert.category}",
                f"Time: {datetime.fromtimestamp(alert.timestamp).isoformat()}",
                "",
                "Message:",
                alert.message,
            ]
            
            if alert.context:
                body_lines.extend(["", "Context:"])
                for key, value in alert.context.items():
                    body_lines.append(f"  {key}: {value}")
            
            body = "\n".join(body_lines)
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.from_addr
            msg['To'] = ", ".join(self.to_addrs)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.debug(f"Sent {alert.severity.name} alert via email: {alert.message}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False


class LogChannel(AlertChannel):
    """Logging channel (always enabled as fallback)."""
    
    def __init__(self, min_severity: AlertSeverity = AlertSeverity.DEBUG):
        super().__init__("log", min_severity)
        self.enabled = True
    
    def send(self, alert: Alert) -> bool:
        """Log alert."""
        log_level_map = {
            AlertSeverity.DEBUG: logging.DEBUG,
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }
        
        level = log_level_map.get(alert.severity, logging.INFO)
        extra_info = f" [{alert.category}]"
        if alert.context:
            extra_info += f" {alert.context}"
        
        logger.log(level, f"{alert.message}{extra_info}")
        return True


class AlertManager:
    """
    Central alert manager for the pipeline.
    
    Manages multiple alert channels and implements rate limiting to prevent spam.
    """
    
    def __init__(
        self,
        channels: Optional[List[AlertChannel]] = None,
        rate_limit_window: int = 300,  # 5 minutes
        rate_limit_count: int = 10,
    ):
        self.channels = channels or []
        self.rate_limit_window = rate_limit_window
        self.rate_limit_count = rate_limit_count
        
        # Rate limiting tracking
        self._alert_history: List[Alert] = []
        self._suppressed_count: Dict[str, int] = {}
    
    def add_channel(self, channel: AlertChannel) -> None:
        """Add an alert channel."""
        self.channels.append(channel)
    
    def _check_rate_limit(self, alert: Alert) -> bool:
        """Check if alert should be rate limited."""
        now = time.time()
        cutoff = now - self.rate_limit_window
        
        # Remove old alerts
        self._alert_history = [
            a for a in self._alert_history
            if a.timestamp > cutoff
        ]
        
        # Count recent alerts of same category
        recent_count = sum(
            1 for a in self._alert_history
            if a.category == alert.category and a.severity == alert.severity
        )
        
        if recent_count >= self.rate_limit_count:
            key = f"{alert.category}:{alert.severity.name}"
            self._suppressed_count[key] = self._suppressed_count.get(key, 0) + 1
            return True
        
        return False
    
    def send_alert(
        self,
        severity: AlertSeverity,
        category: str,
        message: str,
        context: Optional[Dict] = None,
    ) -> bool:
        """
        Send an alert through all enabled channels.
        
        Args:
            severity: Alert severity level
            category: Alert category (e.g., "conversion", "calibration", "disk_space")
            message: Human-readable alert message
            context: Optional context dictionary with additional details
        
        Returns:
            True if at least one channel successfully sent the alert
        """
        alert = Alert(
            severity=severity,
            message=message,
            category=category,
            context=context,
        )
        
        # Check rate limiting
        if self._check_rate_limit(alert):
            logger.debug(f"Rate limited alert: {category} {severity.name}")
            return False
        
        # Add to history
        self._alert_history.append(alert)
        
        # Send through all enabled channels
        success_count = 0
        for channel in self.channels:
            if channel.enabled_for_severity(severity):
                if channel.send(alert):
                    success_count += 1
        
        return success_count > 0
    
    def flush_suppressed_alerts(self) -> None:
        """Send summary of suppressed alerts."""
        if not self._suppressed_count:
            return
        
        summary_lines = ["Suppressed alerts in last window:"]
        for key, count in self._suppressed_count.items():
            summary_lines.append(f"  {key}: {count} alerts")
        
        self.send_alert(
            AlertSeverity.INFO,
            "rate_limiting",
            "\n".join(summary_lines),
        )
        
        self._suppressed_count.clear()
    
    def get_recent_alerts(self, minutes: int = 60) -> List[Alert]:
        """Get recent alerts within time window."""
        cutoff = time.time() - (minutes * 60)
        return [a for a in self._alert_history if a.timestamp > cutoff]


# Global alert manager instance
_global_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create global alert manager instance."""
    global _global_alert_manager
    
    if _global_alert_manager is None:
        # Create with default channels
        channels = [LogChannel()]  # Always log
        
        # Add Slack if configured
        slack_webhook = os.getenv("CONTIMG_SLACK_WEBHOOK_URL")
        if slack_webhook:
            slack_channel = SlackChannel(
                webhook_url=slack_webhook,
                min_severity=AlertSeverity.WARNING,
            )
            channels.append(slack_channel)
        
        # Add email if configured
        if os.getenv("CONTIMG_SMTP_HOST"):
            email_channel = EmailChannel(min_severity=AlertSeverity.ERROR)
            channels.append(email_channel)
        
        _global_alert_manager = AlertManager(channels=channels)
    
    return _global_alert_manager


def alert(
    severity: AlertSeverity,
    category: str,
    message: str,
    context: Optional[Dict] = None,
) -> bool:
    """Convenience function to send an alert."""
    manager = get_alert_manager()
    return manager.send_alert(severity, category, message, context)


# Convenience functions for each severity level
def debug(category: str, message: str, context: Optional[Dict] = None) -> bool:
    """Send debug alert."""
    return alert(AlertSeverity.DEBUG, category, message, context)


def info(category: str, message: str, context: Optional[Dict] = None) -> bool:
    """Send info alert."""
    return alert(AlertSeverity.INFO, category, message, context)


def warning(category: str, message: str, context: Optional[Dict] = None) -> bool:
    """Send warning alert."""
    return alert(AlertSeverity.WARNING, category, message, context)


def error(category: str, message: str, context: Optional[Dict] = None) -> bool:
    """Send error alert."""
    return alert(AlertSeverity.ERROR, category, message, context)


def critical(category: str, message: str, context: Optional[Dict] = None) -> bool:
    """Send critical alert."""
    return alert(AlertSeverity.CRITICAL, category, message, context)


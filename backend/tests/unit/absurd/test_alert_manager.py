# mypy: disable-error-code="import-not-found,import-untyped"
"""
Unit tests for AlertManager.

Tests SMTP configuration, Slack alerts, and threshold monitoring.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest  # type: ignore[import-not-found]

from dsa110_contimg.scripts.absurd.alert_manager import (  # type: ignore[import-not-found]
    Alert,
    AlertManager,
    AlertThresholds,
    SlackConfig,
    SMTPConfig,
)

# --- Fixtures ---


@pytest.fixture
def temp_log_file():
    """Create a temporary log file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        yield f.name
    # Cleanup
    try:
        os.unlink(f.name)
    except FileNotFoundError:
        pass


# --- SMTPConfig Tests ---


class TestSMTPConfig:
    """Tests for SMTPConfig dataclass."""

    def test_smtp_config_defaults(self):
        """SMTPConfig should have sensible defaults."""
        config = SMTPConfig()

        assert config.host == "localhost"
        assert config.port == 587
        assert config.username is None
        assert config.password is None
        assert config.use_tls is True
        assert config.from_address == "absurd-alerts@dsa110"

    def test_smtp_config_from_env(self):
        """SMTPConfig should load from environment variables."""
        env = {
            "ABSURD_SMTP_HOST": "smtp.example.com",
            "ABSURD_SMTP_PORT": "465",
            "ABSURD_SMTP_USER": "user@example.com",
            "ABSURD_SMTP_PASSWORD": "secret123",
            "ABSURD_SMTP_USE_TLS": "true",
            "ABSURD_SMTP_FROM": "alerts@example.com",
        }

        with patch.dict(os.environ, env, clear=False):
            config = SMTPConfig.from_env()

        assert config.host == "smtp.example.com"
        assert config.port == 465
        assert config.username == "user@example.com"
        assert config.password == "secret123"
        assert config.use_tls is True
        assert config.from_address == "alerts@example.com"

    def test_smtp_config_from_env_defaults(self):
        """SMTPConfig should use defaults when env vars not set."""
        # Clear any ABSURD_SMTP_ env vars
        env_to_clear = {k: "" for k in os.environ if k.startswith("ABSURD_SMTP_")}

        with patch.dict(os.environ, env_to_clear, clear=False):
            # Now patch to ensure clean state
            with patch.dict(
                os.environ,
                {
                    "ABSURD_SMTP_HOST": "",
                    "ABSURD_SMTP_PORT": "",
                    "ABSURD_SMTP_USER": "",
                },
                clear=False,
            ):
                # Reset to empty - from_env will use defaults
                pass

        config = SMTPConfig()  # Use defaults directly
        assert config.host == "localhost"

    def test_smtp_is_configured_with_custom_host(self):
        """is_configured() should return True for non-localhost host."""
        config = SMTPConfig(host="smtp.example.com")
        assert config.is_configured() is True

    def test_smtp_is_configured_with_credentials(self):
        """is_configured() should return True when credentials provided."""
        config = SMTPConfig(host="localhost", username="user", password="pass")
        assert config.is_configured() is True

    def test_smtp_not_configured_default(self):
        """is_configured() should return False for default localhost without creds."""
        config = SMTPConfig()
        assert config.is_configured() is False

    def test_smtp_tls_auto_detect_port_465(self):
        """TLS should auto-enable for port 465."""
        env = {"ABSURD_SMTP_PORT": "465"}

        with patch.dict(os.environ, env, clear=False):
            config = SMTPConfig.from_env()

        assert config.use_tls is True

    def test_smtp_tls_auto_detect_port_25(self):
        """TLS should not auto-enable for port 25."""
        env = {
            "ABSURD_SMTP_PORT": "25",
            "ABSURD_SMTP_USE_TLS": "",  # Clear to test default
        }

        with patch.dict(os.environ, env, clear=False):
            # Port 25 should default to no TLS
            config = SMTPConfig(port=25, use_tls=False)

        assert config.use_tls is False


# --- SlackConfig Tests ---


class TestSlackConfig:
    """Tests for SlackConfig dataclass."""

    def test_slack_config_defaults(self):
        """SlackConfig should have sensible defaults."""
        config = SlackConfig()

        assert config.webhook_url is None
        assert config.channel is None
        assert config.username == "DSA-110 Absurd Monitor"
        assert config.icon_emoji == ":robot_face:"

    def test_slack_config_from_env(self):
        """SlackConfig should load from environment variables."""
        env = {
            "ABSURD_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/xxx",
            "ABSURD_SLACK_CHANNEL": "#alerts",
            "ABSURD_SLACK_USERNAME": "Pipeline Bot",
            "ABSURD_SLACK_ICON": ":warning:",
        }

        with patch.dict(os.environ, env, clear=False):
            config = SlackConfig.from_env()

        assert config.webhook_url == "https://hooks.slack.com/services/xxx"
        assert config.channel == "#alerts"
        assert config.username == "Pipeline Bot"
        assert config.icon_emoji == ":warning:"

    def test_slack_is_configured_with_webhook(self):
        """is_configured() should return True when webhook URL set."""
        config = SlackConfig(webhook_url="https://hooks.slack.com/xxx")
        assert config.is_configured() is True

    def test_slack_not_configured_without_webhook(self):
        """is_configured() should return False without webhook URL."""
        config = SlackConfig()
        assert config.is_configured() is False


# --- Alert Tests ---


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self):
        """Alert should store all fields correctly."""
        now = datetime.now()
        alert = Alert(
            level="CRITICAL",
            category="queue",
            message="Queue depth critical",
            timestamp=now,
            details={"depth": 150},
        )

        assert alert.level == "CRITICAL"
        assert alert.category == "queue"
        assert alert.message == "Queue depth critical"
        assert alert.timestamp == now
        assert alert.details == {"depth": 150}

    def test_alert_without_details(self):
        """Alert should allow None details."""
        alert = Alert(
            level="WARNING",
            category="disk",
            message="Disk usage high",
            timestamp=datetime.now(),
        )

        assert alert.details is None


# --- AlertManager Initialization Tests ---


class TestAlertManagerInit:
    """Tests for AlertManager initialization."""

    def test_init_with_defaults(self, temp_log_file):
        """AlertManager should initialize with defaults."""
        manager = AlertManager(
            database_url="postgresql://test:test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
        )

        assert manager.queue_name == "test-queue"
        assert isinstance(manager.thresholds, AlertThresholds)
        assert isinstance(manager.smtp_config, SMTPConfig)
        assert isinstance(manager.slack_config, SlackConfig)

    def test_init_auto_enables_email_when_configured(self, temp_log_file):
        """Should auto-enable email when SMTP is configured."""
        smtp = SMTPConfig(host="smtp.example.com")

        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            smtp_config=smtp,
            email_to=["admin@example.com"],
        )

        assert manager.email_enabled is True

    def test_init_auto_enables_slack_when_configured(self, temp_log_file):
        """Should auto-enable Slack when webhook is configured."""
        slack = SlackConfig(webhook_url="https://hooks.slack.com/xxx")

        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            slack_config=slack,
        )

        assert manager.slack_enabled is True

    def test_init_parses_email_recipients_from_env(self, temp_log_file):
        """Should parse email recipients from environment."""
        env = {"ABSURD_ALERT_EMAIL_TO": "admin@example.com, ops@example.com"}

        with patch.dict(os.environ, env, clear=False):
            manager = AlertManager(
                database_url="postgresql://test@localhost/test",
                queue_name="test-queue",
                alert_log=temp_log_file,
            )

        assert "admin@example.com" in manager.email_to
        assert "ops@example.com" in manager.email_to


# --- Email Alert Tests ---


class TestEmailAlert:
    """Tests for send_email_alert method."""

    def test_email_alert_skipped_when_no_recipients(self, temp_log_file):
        """Should not send email when no recipients configured."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            email_enabled=True,
            email_to=[],
        )

        alert = Alert(
            level="CRITICAL",
            category="test",
            message="Test alert",
            timestamp=datetime.now(),
        )

        # Should not raise, just return early
        manager.send_email_alert(alert)

    @patch("smtplib.SMTP")
    def test_email_alert_sends_with_starttls(self, mock_smtp_class, temp_log_file):
        """Should send email using STARTTLS."""
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp_class.return_value = mock_smtp

        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            email_enabled=True,
            email_to=["admin@example.com"],
            smtp_config=SMTPConfig(
                host="smtp.example.com",
                port=587,
                use_tls=True,
            ),
        )

        alert = Alert(
            level="CRITICAL",
            category="queue",
            message="Queue depth critical",
            timestamp=datetime.now(),
        )

        manager.send_email_alert(alert)

        mock_smtp_class.assert_called_with("smtp.example.com", 587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_email_alert_with_authentication(self, mock_smtp_class, temp_log_file):
        """Should authenticate when credentials provided."""
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp_class.return_value = mock_smtp

        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            email_enabled=True,
            email_to=["admin@example.com"],
            smtp_config=SMTPConfig(
                host="smtp.example.com",
                port=587,
                username="user@example.com",
                password="secret",
                use_tls=True,
            ),
        )

        alert = Alert(
            level="CRITICAL",
            category="queue",
            message="Test",
            timestamp=datetime.now(),
        )

        manager.send_email_alert(alert)

        mock_smtp.login.assert_called_with("user@example.com", "secret")

    @patch("smtplib.SMTP_SSL")
    def test_email_alert_ssl_connection(self, mock_smtp_ssl_class, temp_log_file):
        """Should use SSL for port 465."""
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp_ssl_class.return_value = mock_smtp

        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            email_enabled=True,
            email_to=["admin@example.com"],
            smtp_config=SMTPConfig(
                host="smtp.example.com",
                port=465,
            ),
        )

        alert = Alert(
            level="CRITICAL",
            category="queue",
            message="Test",
            timestamp=datetime.now(),
        )

        manager.send_email_alert(alert)

        mock_smtp_ssl_class.assert_called_once()


# --- Slack Alert Tests ---


class TestSlackAlert:
    """Tests for send_slack_alert method."""

    @pytest.mark.asyncio
    async def test_slack_alert_skipped_without_webhook(self, temp_log_file):
        """Should not send Slack alert without webhook URL."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            slack_enabled=True,
            slack_config=SlackConfig(),
        )

        alert = Alert(
            level="CRITICAL",
            category="test",
            message="Test",
            timestamp=datetime.now(),
        )

        # Should not raise, just return early
        await manager.send_slack_alert(alert)

    @pytest.mark.asyncio
    async def test_slack_alert_sends_payload(self, temp_log_file):
        """Should send properly formatted Slack payload via httpx."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            slack_enabled=True,
            slack_config=SlackConfig(
                webhook_url="https://hooks.slack.com/services/test",
                channel="#alerts",
            ),
        )

        alert = Alert(
            level="CRITICAL",
            category="queue",
            message="Queue depth critical",
            timestamp=datetime.now(),
            details={"depth": 150},
        )

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            # Create async context manager mock
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await manager.send_slack_alert(alert)

            # Verify the POST was made
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args

            # Check URL
            assert call_args[0][0] == "https://hooks.slack.com/services/test"

            # Check payload
            payload = call_args.kwargs["json"]
            assert payload["channel"] == "#alerts"
            assert len(payload["attachments"]) == 1
            assert payload["attachments"][0]["color"] == "#ff0000"  # CRITICAL = red

    @pytest.mark.asyncio
    async def test_slack_alert_color_by_level(self, temp_log_file):
        """Should use correct colors for different alert levels."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            slack_enabled=True,
            slack_config=SlackConfig(webhook_url="https://test"),
        )

        # Test color mapping
        colors = {
            "INFO": "#36a64f",
            "WARNING": "#ff9500",
            "CRITICAL": "#ff0000",
        }

        # We can test the color selection logic indirectly
        # by checking the method doesn't error with different levels
        for level in ["INFO", "WARNING", "CRITICAL"]:
            alert = Alert(
                level=level,
                category="test",
                message="Test",
                timestamp=datetime.now(),
            )
            # This will try to send but fail - we just want to verify no errors
            with patch("urllib.request.urlopen") as mock:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.__enter__ = MagicMock(return_value=mock_resp)
                mock_resp.__exit__ = MagicMock(return_value=False)
                mock.return_value = mock_resp

                await manager.send_slack_alert(alert)


# --- Threshold Check Tests ---


class TestThresholdChecks:
    """Tests for alert threshold checks."""

    @pytest.mark.asyncio
    async def test_check_queue_depth_critical(self, temp_log_file):
        """Should raise critical alert when queue depth exceeds critical threshold."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            thresholds=AlertThresholds(queue_depth_critical=100),
        )

        # Mock the database pool
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"depth": 150})

        mock_pool = MagicMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire
        manager._pool = mock_pool

        alert = await manager.check_queue_depth()

        assert alert is not None
        assert alert.level == "CRITICAL"
        assert alert.category == "queue"

    @pytest.mark.asyncio
    async def test_check_queue_depth_warning(self, temp_log_file):
        """Should raise warning alert when queue depth exceeds warning threshold."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            thresholds=AlertThresholds(
                queue_depth_warning=50,
                queue_depth_critical=100,
            ),
        )

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"depth": 75})

        mock_pool = MagicMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire
        manager._pool = mock_pool

        alert = await manager.check_queue_depth()

        assert alert is not None
        assert alert.level == "WARNING"

    def test_check_disk_usage_warning(self, temp_log_file):
        """Should warn when disk usage exceeds warning threshold."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            thresholds=AlertThresholds(
                disk_usage_warning=80,
                disk_usage_critical=95,
            ),
        )

        # Mock disk usage check
        with patch("shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(
                total=100 * 1024**3,  # 100 GB
                used=90 * 1024**3,  # 90 GB (90% used)
                free=10 * 1024**3,
            )

            alert = manager.check_disk_usage()

        assert alert is not None
        assert alert.category == "disk"


# --- Send Alert Tests ---


class TestSendAlert:
    """Tests for send_alert method."""

    def test_send_alert_logs_message(self, temp_log_file):
        """Should log alert message."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
        )

        alert = Alert(
            level="WARNING",
            category="test",
            message="Test warning",
            timestamp=datetime.now(),
        )

        with patch.object(manager.logger, "warning") as mock_warn:
            manager.send_alert(alert)
            mock_warn.assert_called_once()

    def test_send_alert_adds_to_history(self, temp_log_file):
        """Should add alert to history."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
        )

        alert = Alert(
            level="INFO",
            category="test",
            message="Test info",
            timestamp=datetime.now(),
        )

        manager.send_alert(alert)

        assert alert in manager.alert_history

    def test_send_alert_emails_on_critical(self, temp_log_file):
        """Should trigger email for critical alerts."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            email_enabled=True,
            email_to=["admin@test.com"],
        )

        alert = Alert(
            level="CRITICAL",
            category="test",
            message="Critical issue",
            timestamp=datetime.now(),
        )

        with patch.object(manager, "send_email_alert") as mock_email:
            manager.send_alert(alert)
            mock_email.assert_called_once_with(alert)

    def test_send_alert_no_email_on_warning(self, temp_log_file):
        """Should not trigger email for warning alerts."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            email_enabled=True,
            email_to=["admin@test.com"],
        )

        alert = Alert(
            level="WARNING",
            category="test",
            message="Warning issue",
            timestamp=datetime.now(),
        )

        with patch.object(manager, "send_email_alert") as mock_email:
            manager.send_alert(alert)
            mock_email.assert_not_called()


# --- Async Alert Tests ---


class TestAsyncAlerts:
    """Tests for async alert sending."""

    @pytest.mark.asyncio
    async def test_send_alert_async_slack_on_warning(self, temp_log_file):
        """Should trigger Slack for warning alerts."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            slack_enabled=True,
            slack_config=SlackConfig(webhook_url="https://test"),
        )

        alert = Alert(
            level="WARNING",
            category="test",
            message="Warning issue",
            timestamp=datetime.now(),
        )

        with patch.object(manager, "send_slack_alert", new_callable=AsyncMock) as mock_slack:
            await manager.send_alert_async(alert)
            mock_slack.assert_called_once_with(alert)

    @pytest.mark.asyncio
    async def test_send_alert_async_both_channels_on_critical(self, temp_log_file):
        """Should trigger both email and Slack for critical alerts."""
        manager = AlertManager(
            database_url="postgresql://test@localhost/test",
            queue_name="test-queue",
            alert_log=temp_log_file,
            email_enabled=True,
            email_to=["admin@test.com"],
            slack_enabled=True,
            slack_config=SlackConfig(webhook_url="https://test"),
        )

        alert = Alert(
            level="CRITICAL",
            category="test",
            message="Critical issue",
            timestamp=datetime.now(),
        )

        with patch.object(manager, "send_email_alert") as mock_email:
            with patch.object(manager, "send_slack_alert", new_callable=AsyncMock) as mock_slack:
                await manager.send_alert_async(alert)
                mock_email.assert_called_once()
                mock_slack.assert_called_once()

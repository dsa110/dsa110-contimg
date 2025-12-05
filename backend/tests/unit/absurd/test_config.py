"""
Unit tests for ABSURD configuration.

Tests the AbsurdConfig class and environment variable handling.
"""

import os
import pytest
from unittest.mock import patch

from dsa110_contimg.absurd.config import AbsurdConfig


class TestAbsurdConfigDefaults:
    """Tests for AbsurdConfig default values."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AbsurdConfig()

        assert config.enabled is False
        assert config.queue_name == "dsa110-pipeline"
        assert config.worker_concurrency == 4
        assert config.worker_poll_interval_sec == 1.0
        assert config.task_timeout_sec == 3600
        assert config.max_retries == 3
        assert config.dead_letter_enabled is True
        assert config.dead_letter_queue_name == "dsa110-pipeline-dlq"
        assert config.api_base_url == ""
        assert config.api_heartbeat_interval_sec == 10.0

    def test_default_database_url(self):
        """Test default database URL."""
        config = AbsurdConfig()
        assert "postgresql://" in config.database_url
        assert "localhost" in config.database_url


class TestAbsurdConfigFromEnv:
    """Tests for AbsurdConfig.from_env() method."""

    def test_from_env_defaults(self):
        """Test from_env with no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            # Need to ensure ABSURD vars are not set
            for key in list(os.environ.keys()):
                if key.startswith("ABSURD_"):
                    del os.environ[key]

            config = AbsurdConfig.from_env()
            assert config.enabled is False
            assert config.queue_name == "dsa110-pipeline"

    def test_from_env_enabled_true(self):
        """Test enabling ABSURD via environment."""
        with patch.dict(os.environ, {"ABSURD_ENABLED": "true"}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.enabled is True

    def test_from_env_enabled_variations(self):
        """Test various truthy values for ABSURD_ENABLED."""
        for value in ["true", "1", "yes", "TRUE", "True", "YES"]:
            with patch.dict(os.environ, {"ABSURD_ENABLED": value}, clear=False):
                config = AbsurdConfig.from_env()
                assert config.enabled is True, f"Failed for value: {value}"

    def test_from_env_enabled_false(self):
        """Test disabling ABSURD via environment."""
        for value in ["false", "0", "no", "anything_else"]:
            with patch.dict(os.environ, {"ABSURD_ENABLED": value}, clear=False):
                config = AbsurdConfig.from_env()
                assert config.enabled is False, f"Failed for value: {value}"

    def test_from_env_custom_database_url(self):
        """Test custom database URL from environment."""
        custom_url = "postgresql://user:pass@host:5432/mydb"
        with patch.dict(os.environ, {"ABSURD_DATABASE_URL": custom_url}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.database_url == custom_url

    def test_from_env_custom_queue_name(self):
        """Test custom queue name from environment."""
        with patch.dict(os.environ, {"ABSURD_QUEUE_NAME": "my-custom-queue"}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.queue_name == "my-custom-queue"
            # DLQ should also use the custom name
            assert config.dead_letter_queue_name == "my-custom-queue-dlq"

    def test_from_env_worker_concurrency(self):
        """Test worker concurrency from environment."""
        with patch.dict(os.environ, {"ABSURD_WORKER_CONCURRENCY": "8"}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.worker_concurrency == 8

    def test_from_env_poll_interval(self):
        """Test poll interval from environment."""
        with patch.dict(os.environ, {"ABSURD_WORKER_POLL_INTERVAL": "2.5"}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.worker_poll_interval_sec == 2.5

    def test_from_env_task_timeout(self):
        """Test task timeout from environment."""
        with patch.dict(os.environ, {"ABSURD_TASK_TIMEOUT": "7200"}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.task_timeout_sec == 7200

    def test_from_env_max_retries(self):
        """Test max retries from environment."""
        with patch.dict(os.environ, {"ABSURD_MAX_RETRIES": "5"}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.max_retries == 5

    def test_from_env_dlq_disabled(self):
        """Test disabling dead letter queue."""
        with patch.dict(os.environ, {"ABSURD_DLQ_ENABLED": "false"}, clear=False):
            config = AbsurdConfig.from_env()
            assert config.dead_letter_enabled is False

    def test_from_env_custom_dlq_name(self):
        """Test custom DLQ name from environment."""
        with patch.dict(
            os.environ,
            {
                "ABSURD_QUEUE_NAME": "my-queue",
                "ABSURD_DLQ_QUEUE_NAME": "my-custom-dlq",
            },
            clear=False,
        ):
            config = AbsurdConfig.from_env()
            assert config.dead_letter_queue_name == "my-custom-dlq"

    def test_from_env_api_settings(self):
        """Test API heartbeat settings from environment."""
        with patch.dict(
            os.environ,
            {
                "ABSURD_API_BASE_URL": "http://localhost:8000/api/v1",
                "ABSURD_API_HEARTBEAT_INTERVAL": "30.0",
            },
            clear=False,
        ):
            config = AbsurdConfig.from_env()
            assert config.api_base_url == "http://localhost:8000/api/v1"
            assert config.api_heartbeat_interval_sec == 30.0


class TestAbsurdConfigDataclass:
    """Tests for AbsurdConfig dataclass behavior."""

    def test_config_is_dataclass(self):
        """Test that AbsurdConfig is a proper dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(AbsurdConfig)

    def test_config_equality(self):
        """Test that configs with same values are equal."""
        config1 = AbsurdConfig(queue_name="test")
        config2 = AbsurdConfig(queue_name="test")
        assert config1 == config2

    def test_config_inequality(self):
        """Test that configs with different values are not equal."""
        config1 = AbsurdConfig(queue_name="queue1")
        config2 = AbsurdConfig(queue_name="queue2")
        assert config1 != config2

    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = AbsurdConfig(
            enabled=True,
            database_url="postgresql://custom:5432/db",
            queue_name="custom-queue",
            worker_concurrency=16,
            max_retries=10,
        )

        assert config.enabled is True
        assert config.database_url == "postgresql://custom:5432/db"
        assert config.queue_name == "custom-queue"
        assert config.worker_concurrency == 16
        assert config.max_retries == 10

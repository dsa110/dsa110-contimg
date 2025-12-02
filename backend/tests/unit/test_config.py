"""
Unit tests for config.py - Configuration and secrets management.

Tests for:
- Environment enum
- DatabaseConfig
- RedisConfig
- AuthConfig
- RateLimitConfig
- CORSConfig
- Settings class
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from dsa110_contimg.api.config import (
    Environment,
    ConfigError,
    DatabaseConfig,
    RedisConfig,
    AuthConfig,
    RateLimitConfig,
    CORSConfig,
)


class TestEnvironment:
    """Tests for Environment enum."""

    def test_development_value(self):
        """Test development environment value."""
        assert Environment.DEVELOPMENT.value == "development"

    def test_testing_value(self):
        """Test testing environment value."""
        assert Environment.TESTING.value == "testing"

    def test_staging_value(self):
        """Test staging environment value."""
        assert Environment.STAGING.value == "staging"

    def test_production_value(self):
        """Test production environment value."""
        assert Environment.PRODUCTION.value == "production"

    def test_is_string_enum(self):
        """Test Environment is a string enum."""
        assert isinstance(Environment.DEVELOPMENT, str)
        assert Environment.DEVELOPMENT == "development"


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass - unified database design."""

    def test_default_unified_path(self):
        """Test default unified database path is set."""
        config = DatabaseConfig()
        
        # All paths now point to unified pipeline.sqlite3
        assert config.unified_path.name == "pipeline.sqlite3"
        
    def test_legacy_properties_return_unified_path(self):
        """Test legacy path properties all return unified path for backwards compat."""
        config = DatabaseConfig()
        
        # Legacy properties should all return the unified path
        assert config.products_path == config.unified_path
        assert config.cal_registry_path == config.unified_path
        assert config.hdf5_path == config.unified_path
        assert config.ingest_path == config.unified_path
        assert config.data_registry_path == config.unified_path

    def test_default_timeout(self):
        """Test default connection timeout."""
        config = DatabaseConfig()
        
        assert config.connection_timeout == 30.0

    def test_custom_unified_path(self):
        """Test custom unified database path."""
        config = DatabaseConfig(
            unified_path=Path("/custom/pipeline.sqlite3"),
        )
        
        assert config.unified_path == Path("/custom/pipeline.sqlite3")
        # Legacy properties should also reflect the custom unified path
        assert config.products_path == Path("/custom/pipeline.sqlite3")
        assert config.cal_registry_path == Path("/custom/pipeline.sqlite3")



class TestRedisConfig:
    """Tests for RedisConfig dataclass."""

    def test_default_values(self):
        """Test default Redis configuration."""
        config = RedisConfig()
        
        assert config.url == "redis://localhost:6379"
        assert config.queue_name == "dsa110-pipeline"
        assert config.max_connections == 10
        assert config.socket_timeout == 5.0

    def test_from_env_defaults(self):
        """Test from_env uses defaults when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = RedisConfig.from_env()
        
        assert config.url == "redis://localhost:6379"

    def test_from_env_custom_values(self):
        """Test from_env reads from environment variables."""
        env = {
            "DSA110_REDIS_URL": "redis://custom:6380",
            "DSA110_QUEUE_NAME": "custom-queue",
            "DSA110_REDIS_MAX_CONNECTIONS": "20",
            "DSA110_REDIS_TIMEOUT": "10.0",
        }
        with patch.dict(os.environ, env, clear=True):
            config = RedisConfig.from_env()
        
        assert config.url == "redis://custom:6380"
        assert config.queue_name == "custom-queue"
        assert config.max_connections == 20
        assert config.socket_timeout == 10.0


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_default_values(self):
        """Test default authentication configuration."""
        config = AuthConfig()
        
        assert config.enabled is True
        assert config.api_keys == set()
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_expiry_hours == 24

    def test_from_env_with_api_keys(self):
        """Test from_env parses API keys correctly."""
        env = {
            "DSA110_API_KEYS": "key1,key2,key3",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AuthConfig.from_env()
        
        assert "key1" in config.api_keys
        assert "key2" in config.api_keys
        assert "key3" in config.api_keys

    def test_from_env_disabled_auth(self):
        """Test from_env respects auth disabled flag."""
        env = {
            "DSA110_AUTH_DISABLED": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AuthConfig.from_env()
        
        assert config.enabled is False

    def test_from_env_generates_jwt_secret(self):
        """Test from_env generates JWT secret if not provided."""
        with patch.dict(os.environ, {}, clear=True):
            config = AuthConfig.from_env()
        
        assert len(config.jwt_secret) >= 32

    def test_validate_production_auth_disabled(self):
        """Test validation fails if auth disabled in production."""
        config = AuthConfig(enabled=False)
        errors = config.validate(Environment.PRODUCTION)
        
        assert any("cannot be disabled" in e.lower() for e in errors)

    def test_validate_production_no_api_keys(self):
        """Test validation fails if no API keys in production."""
        config = AuthConfig(enabled=True, api_keys=set())
        errors = config.validate(Environment.PRODUCTION)
        
        assert any("api key" in e.lower() for e in errors)

    def test_validate_production_short_jwt_secret(self):
        """Test validation fails if JWT secret too short in production."""
        config = AuthConfig(enabled=True, api_keys={"key1"}, jwt_secret="short")
        errors = config.validate(Environment.PRODUCTION)
        
        assert any("jwt secret" in e.lower() for e in errors)

    def test_validate_production_valid_config(self):
        """Test validation passes with valid production config."""
        config = AuthConfig(
            enabled=True,
            api_keys={"valid-api-key"},
            jwt_secret="a" * 64,  # 64 character secret
        )
        errors = config.validate(Environment.PRODUCTION)
        
        assert errors == []

    def test_validate_development_relaxed(self):
        """Test validation is relaxed in development."""
        config = AuthConfig(enabled=False)
        errors = config.validate(Environment.DEVELOPMENT)
        
        assert errors == []


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()
        
        assert config.enabled is True
        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 1000
        assert config.burst_size == 20

    def test_from_env_defaults(self):
        """Test from_env uses defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = RateLimitConfig.from_env()
        
        assert config.enabled is True
        assert config.requests_per_minute == 100

    def test_from_env_disabled(self):
        """Test from_env respects disabled flag."""
        env = {"DSA110_RATE_LIMIT_DISABLED": "true"}
        with patch.dict(os.environ, env, clear=True):
            config = RateLimitConfig.from_env()
        
        assert config.enabled is False

    def test_from_env_custom_limits(self):
        """Test from_env reads custom limits."""
        env = {
            "DSA110_RATE_LIMIT_MINUTE": "200",
            "DSA110_RATE_LIMIT_HOUR": "5000",
            "DSA110_RATE_LIMIT_BURST": "50",
        }
        with patch.dict(os.environ, env, clear=True):
            config = RateLimitConfig.from_env()
        
        assert config.requests_per_minute == 200
        assert config.requests_per_hour == 5000
        assert config.burst_size == 50


class TestCORSConfig:
    """Tests for CORSConfig dataclass."""

    def test_default_values(self):
        """Test default CORS configuration."""
        config = CORSConfig()
        
        assert config.allowed_origins == []
        assert config.allow_credentials is True

    def test_from_env_uses_defaults(self):
        """Test from_env includes default origins."""
        with patch.dict(os.environ, {}, clear=True):
            config = CORSConfig.from_env()
        
        # Should include some default origins
        assert any("localhost" in origin for origin in config.allowed_origins)

    def test_from_env_custom_origins(self):
        """Test from_env reads custom origins."""
        env = {"DSA110_CORS_ORIGINS": "https://example.com,https://app.example.com"}
        with patch.dict(os.environ, env, clear=True):
            config = CORSConfig.from_env()
        
        assert "https://example.com" in config.allowed_origins
        assert "https://app.example.com" in config.allowed_origins


class TestConfigError:
    """Tests for ConfigError exception."""

    def test_is_exception(self):
        """Test ConfigError is an exception."""
        error = ConfigError("Test error")
        
        assert isinstance(error, Exception)

    def test_message(self):
        """Test ConfigError stores message."""
        error = ConfigError("Configuration failed")
        
        assert str(error) == "Configuration failed"


class TestTimeoutConfig:
    """Tests for TimeoutConfig dataclass."""

    def test_default_values(self):
        """Test default timeout configuration."""
        from dsa110_contimg.api.config import TimeoutConfig
        
        config = TimeoutConfig()
        
        assert config.db_connection == 30.0
        assert config.db_quick_check == 2.0
        assert config.db_metrics_sync == 10.0
        assert config.websocket_ping == 30.0
        assert config.websocket_pong == 10.0
        assert config.service_health_check == 5.0
        assert config.http_request == 30.0
        assert config.background_poll == 30.0
        assert config.startup_retry_base == 0.5

    def test_from_env_defaults(self):
        """Test from_env uses defaults when env vars not set."""
        from dsa110_contimg.api.config import TimeoutConfig
        
        with patch.dict(os.environ, {}, clear=True):
            config = TimeoutConfig.from_env()
        
        assert config.db_connection == 30.0
        assert config.websocket_ping == 30.0

    def test_from_env_custom_values(self):
        """Test from_env reads custom values from environment."""
        from dsa110_contimg.api.config import TimeoutConfig
        
        env = {
            "DSA110_TIMEOUT_DB_CONNECTION": "60.0",
            "DSA110_TIMEOUT_DB_QUICK": "5.0",
            "DSA110_TIMEOUT_WS_PING": "45.0",
        }
        with patch.dict(os.environ, env, clear=True):
            config = TimeoutConfig.from_env()
        
        assert config.db_connection == 60.0
        assert config.db_quick_check == 5.0
        assert config.websocket_ping == 45.0
        # Defaults for unset values
        assert config.db_metrics_sync == 10.0

    def test_integration_with_api_config(self):
        """Test TimeoutConfig is included in APIConfig."""
        from dsa110_contimg.api.config import APIConfig, TimeoutConfig
        
        config = APIConfig()
        
        assert hasattr(config, 'timeouts')
        assert isinstance(config.timeouts, TimeoutConfig)

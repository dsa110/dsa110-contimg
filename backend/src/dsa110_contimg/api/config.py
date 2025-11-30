"""
Configuration and secrets management for the DSA-110 API.

Provides centralized configuration with:
- Environment variable validation
- Type coercion and defaults
- Secrets handling (JWT, API keys)
- Environment-specific settings
"""

import os
import secrets
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class Environment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class DatabaseConfig:
    """Database connection settings."""
    products_path: Path = field(default_factory=lambda: Path("/data/dsa110-contimg/state/products.sqlite3"))
    cal_registry_path: Path = field(default_factory=lambda: Path("/data/dsa110-contimg/state/cal_registry.sqlite3"))
    hdf5_path: Path = field(default_factory=lambda: Path("/data/dsa110-contimg/state/hdf5.sqlite3"))
    ingest_path: Path = field(default_factory=lambda: Path("/data/dsa110-contimg/state/ingest.sqlite3"))
    data_registry_path: Path = field(default_factory=lambda: Path("/data/dsa110-contimg/state/data_registry.sqlite3"))
    connection_timeout: float = 30.0
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables."""
        base_dir = Path(os.getenv("DSA110_STATE_DIR", "/data/dsa110-contimg/state"))
        return cls(
            products_path=Path(os.getenv("PIPELINE_PRODUCTS_DB", str(base_dir / "products.sqlite3"))),
            cal_registry_path=Path(os.getenv("PIPELINE_CAL_REGISTRY_DB", str(base_dir / "cal_registry.sqlite3"))),
            hdf5_path=Path(os.getenv("PIPELINE_HDF5_DB", str(base_dir / "hdf5.sqlite3"))),
            ingest_path=Path(os.getenv("PIPELINE_INGEST_DB", str(base_dir / "ingest.sqlite3"))),
            data_registry_path=Path(os.getenv("PIPELINE_DATA_REGISTRY_DB", str(base_dir / "data_registry.sqlite3"))),
            connection_timeout=float(os.getenv("DB_CONNECTION_TIMEOUT", "30.0")),
        )
    
    def validate(self) -> List[str]:
        """Validate database configuration. Returns list of errors."""
        errors = []
        for db_name in ["products", "cal_registry", "hdf5", "ingest", "data_registry"]:
            path = getattr(self, f"{db_name}_path")
            if not path.parent.exists():
                errors.append(f"Database directory does not exist: {path.parent}")
        return errors


@dataclass
class RedisConfig:
    """Redis connection settings."""
    url: str = "redis://localhost:6379"
    queue_name: str = "dsa110-pipeline"
    max_connections: int = 10
    socket_timeout: float = 5.0
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Create config from environment variables."""
        return cls(
            url=os.getenv("DSA110_REDIS_URL", "redis://localhost:6379"),
            queue_name=os.getenv("DSA110_QUEUE_NAME", "dsa110-pipeline"),
            max_connections=int(os.getenv("DSA110_REDIS_MAX_CONNECTIONS", "10")),
            socket_timeout=float(os.getenv("DSA110_REDIS_TIMEOUT", "5.0")),
        )


@dataclass
class AuthConfig:
    """Authentication settings."""
    enabled: bool = True
    api_keys: Set[str] = field(default_factory=set)
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    @classmethod
    def from_env(cls) -> "AuthConfig":
        """Create config from environment variables."""
        # Parse API keys
        api_keys_str = os.getenv("DSA110_API_KEYS", "")
        api_keys = set(k.strip() for k in api_keys_str.split(",") if k.strip())
        
        # Get or generate JWT secret
        jwt_secret = os.getenv("DSA110_JWT_SECRET", "")
        if not jwt_secret:
            # In production, this should fail
            jwt_secret = secrets.token_hex(32)
        
        return cls(
            enabled=os.getenv("DSA110_AUTH_DISABLED", "").lower() != "true",
            api_keys=api_keys,
            jwt_secret=jwt_secret,
            jwt_algorithm=os.getenv("DSA110_JWT_ALGORITHM", "HS256"),
            jwt_expiry_hours=int(os.getenv("DSA110_JWT_EXPIRY_HOURS", "24")),
        )
    
    def validate(self, env: Environment) -> List[str]:
        """Validate auth configuration. Returns list of errors."""
        errors = []
        if env == Environment.PRODUCTION:
            if not self.enabled:
                errors.append("Authentication cannot be disabled in production")
            if not self.api_keys:
                errors.append("At least one API key must be configured for production")
            if len(self.jwt_secret) < 32:
                errors.append("JWT secret must be at least 32 characters in production")
        return errors


@dataclass
class RateLimitConfig:
    """Rate limiting settings."""
    enabled: bool = True
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    burst_size: int = 20
    
    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create config from environment variables."""
        return cls(
            enabled=os.getenv("DSA110_RATE_LIMIT_DISABLED", "").lower() != "true",
            requests_per_minute=int(os.getenv("DSA110_RATE_LIMIT_MINUTE", "100")),
            requests_per_hour=int(os.getenv("DSA110_RATE_LIMIT_HOUR", "1000")),
            burst_size=int(os.getenv("DSA110_RATE_LIMIT_BURST", "20")),
        )


@dataclass
class CORSConfig:
    """CORS settings."""
    allowed_origins: List[str] = field(default_factory=list)
    allow_credentials: bool = True
    
    @classmethod
    def from_env(cls) -> "CORSConfig":
        """Create config from environment variables."""
        default_origins = [
            "https://dsa110.github.io",
            "http://code.deepsynoptic.org",
            "https://code.deepsynoptic.org",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        origins_str = os.getenv("DSA110_CORS_ORIGINS", "")
        if origins_str:
            origins = [o.strip() for o in origins_str.split(",") if o.strip()]
        else:
            origins = default_origins
        
        return cls(
            allowed_origins=origins,
            allow_credentials=os.getenv("DSA110_CORS_CREDENTIALS", "true").lower() == "true",
        )


@dataclass
class LoggingConfig:
    """Logging settings."""
    level: str = "INFO"
    json_format: bool = True
    include_request_id: bool = True
    
    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create config from environment variables."""
        return cls(
            level=os.getenv("DSA110_LOG_LEVEL", "INFO").upper(),
            json_format=os.getenv("DSA110_LOG_JSON", "true").lower() == "true",
            include_request_id=os.getenv("DSA110_LOG_REQUEST_ID", "true").lower() == "true",
        )


@dataclass 
class APIConfig:
    """Main API configuration."""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Component configs
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig.from_env)
    auth: AuthConfig = field(default_factory=AuthConfig.from_env)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig.from_env)
    cors: CORSConfig = field(default_factory=CORSConfig.from_env)
    logging: LoggingConfig = field(default_factory=LoggingConfig.from_env)
    
    # Feature flags
    enable_swagger: bool = True
    enable_metrics: bool = True
    enable_profiling: bool = False
    
    @classmethod
    def from_env(cls) -> "APIConfig":
        """Create complete configuration from environment."""
        env_str = os.getenv("DSA110_ENV", "development").lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
        
        is_production = environment == Environment.PRODUCTION
        
        return cls(
            environment=environment,
            debug=os.getenv("DSA110_DEBUG", "false").lower() == "true" and not is_production,
            host=os.getenv("DSA110_HOST", "0.0.0.0"),
            port=int(os.getenv("DSA110_PORT", "8000")),
            workers=int(os.getenv("DSA110_WORKERS", "4" if is_production else "1")),
            database=DatabaseConfig.from_env(),
            redis=RedisConfig.from_env(),
            auth=AuthConfig.from_env(),
            rate_limit=RateLimitConfig.from_env(),
            cors=CORSConfig.from_env(),
            logging=LoggingConfig.from_env(),
            enable_swagger=os.getenv("DSA110_ENABLE_SWAGGER", "true").lower() == "true",
            enable_metrics=os.getenv("DSA110_ENABLE_METRICS", "true").lower() == "true",
            enable_profiling=os.getenv("DSA110_ENABLE_PROFILING", "false").lower() == "true" and not is_production,
        )
    
    def validate(self) -> List[str]:
        """Validate all configuration. Returns list of errors."""
        errors = []
        
        # Validate component configs
        errors.extend(self.database.validate())
        errors.extend(self.auth.validate(self.environment))
        
        # Production-specific checks
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                errors.append("Debug mode cannot be enabled in production")
            if self.enable_profiling:
                errors.append("Profiling cannot be enabled in production")
        
        return errors
    
    def validate_or_raise(self) -> None:
        """Validate configuration and raise if errors found."""
        errors = self.validate()
        if errors:
            raise ConfigError(
                f"Configuration validation failed:\n" + 
                "\n".join(f"  - {e}" for e in errors)
            )


@lru_cache()
def get_config() -> APIConfig:
    """
    Get the application configuration.
    
    Uses lru_cache for singleton behavior.
    """
    return APIConfig.from_env()


def get_required_env(name: str, description: str = "") -> str:
    """
    Get a required environment variable.
    
    Raises ConfigError if not set.
    """
    value = os.getenv(name)
    if value is None:
        desc = f" ({description})" if description else ""
        raise ConfigError(f"Required environment variable not set: {name}{desc}")
    return value


def get_env_bool(name: str, default: bool = False) -> bool:
    """Get boolean from environment variable."""
    value = os.getenv(name, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def get_env_int(name: str, default: int) -> int:
    """Get integer from environment variable."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def get_env_list(name: str, default: Optional[List[str]] = None, separator: str = ",") -> List[str]:
    """Get list from environment variable."""
    value = os.getenv(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(separator) if item.strip()]


# Environment variable documentation
ENV_VARS = {
    "DSA110_ENV": "Deployment environment (development, testing, staging, production)",
    "DSA110_DEBUG": "Enable debug mode (true/false)",
    "DSA110_HOST": "API host address",
    "DSA110_PORT": "API port number",
    "DSA110_WORKERS": "Number of worker processes",
    
    # Database
    "DSA110_DB_PATH": "Base path for database files",
    
    # Redis
    "DSA110_REDIS_URL": "Redis connection URL",
    "DSA110_QUEUE_NAME": "RQ queue name",
    
    # Auth
    "DSA110_API_KEYS": "Comma-separated list of valid API keys",
    "DSA110_JWT_SECRET": "Secret key for JWT signing",
    "DSA110_AUTH_DISABLED": "Disable authentication (development only)",
    
    # Rate limiting
    "DSA110_RATE_LIMIT_DISABLED": "Disable rate limiting",
    "DSA110_RATE_LIMIT_MINUTE": "Requests allowed per minute",
    "DSA110_RATE_LIMIT_HOUR": "Requests allowed per hour",
    
    # CORS
    "DSA110_CORS_ORIGINS": "Comma-separated list of allowed origins",
    
    # Logging
    "DSA110_LOG_LEVEL": "Log level (DEBUG, INFO, WARNING, ERROR)",
    "DSA110_LOG_JSON": "Use JSON log format (true/false)",
    
    # Features
    "DSA110_ENABLE_SWAGGER": "Enable Swagger UI",
    "DSA110_ENABLE_METRICS": "Enable Prometheus metrics",
}


def print_config_help() -> None:
    """Print configuration help."""
    print("DSA-110 API Configuration Environment Variables:\n")
    for var, desc in ENV_VARS.items():
        print(f"  {var}")
        print(f"    {desc}\n")

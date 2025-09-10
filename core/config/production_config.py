# core/config/production_config.py
"""
Production configuration management for DSA-110 pipeline.

This module provides production-ready configuration management
with environment variable support, validation, and security.
"""

import os
import yaml
import logging
import secrets
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger(__name__)


class Environment(Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "dsa110_pipeline"
    user: str = "dsa110"
    password: str = ""
    ssl_mode: str = "prefer"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class RedisConfig:
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    max_connections: int = 100
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_expiration: int = 3600
    cors_origins: List[str] = field(default_factory=list)
    rate_limit: int = 100
    rate_limit_window: int = 60
    enable_https: bool = False
    ssl_cert_path: str = ""
    ssl_key_path: str = ""


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    enabled: bool = True
    metrics_port: int = 8080
    dashboard_port: int = 8081
    health_check_interval: int = 30
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = "/app/logs/pipeline.log"
    log_max_size: str = "100MB"
    log_backup_count: int = 5
    enable_prometheus: bool = True
    prometheus_port: int = 8082
    enable_grafana: bool = True
    grafana_port: int = 8083


@dataclass
class ResourceConfig:
    """Resource configuration."""
    max_memory: str = "8Gi"
    max_cpu: str = "4000m"
    max_concurrent_tasks: int = 4
    task_timeout: int = 3600
    cleanup_interval: int = 300
    temp_dir: str = "/tmp/dsa110"
    cache_size: str = "2Gi"
    cache_ttl: int = 3600


@dataclass
class ProductionConfig:
    """Production configuration container."""
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)
    
    # Pipeline-specific config
    pipeline_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._load_from_environment()
        self._validate_config()
        self._setup_logging()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Environment
        env_str = os.getenv("ENVIRONMENT", "production").lower()
        self.environment = Environment(env_str)
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Database
        self.database.host = os.getenv("DB_HOST", self.database.host)
        self.database.port = int(os.getenv("DB_PORT", str(self.database.port)))
        self.database.name = os.getenv("DB_NAME", self.database.name)
        self.database.user = os.getenv("DB_USER", self.database.user)
        self.database.password = os.getenv("DB_PASSWORD", self.database.password)
        self.database.ssl_mode = os.getenv("DB_SSL_MODE", self.database.ssl_mode)
        
        # Redis
        self.redis.host = os.getenv("REDIS_HOST", self.redis.host)
        self.redis.port = int(os.getenv("REDIS_PORT", str(self.redis.port)))
        self.redis.db = int(os.getenv("REDIS_DB", str(self.redis.db)))
        self.redis.password = os.getenv("REDIS_PASSWORD", self.redis.password)
        
        # Security
        self.security.secret_key = os.getenv("SECRET_KEY", self.security.secret_key)
        self.security.jwt_secret = os.getenv("JWT_SECRET", self.security.jwt_secret)
        self.security.enable_https = os.getenv("ENABLE_HTTPS", "false").lower() == "true"
        
        # Monitoring
        self.monitoring.log_level = os.getenv("LOG_LEVEL", self.monitoring.log_level)
        self.monitoring.metrics_port = int(os.getenv("METRICS_PORT", str(self.monitoring.metrics_port)))
        self.monitoring.dashboard_port = int(os.getenv("DASHBOARD_PORT", str(self.monitoring.dashboard_port)))
        
        # Resources
        self.resources.max_memory = os.getenv("MAX_MEMORY", self.resources.max_memory)
        self.resources.max_cpu = os.getenv("MAX_CPU", self.resources.max_cpu)
        self.resources.max_concurrent_tasks = int(os.getenv("MAX_CONCURRENT_TASKS", str(self.resources.max_concurrent_tasks)))
    
    def _validate_config(self):
        """Validate configuration values."""
        errors = []
        
        # Validate required fields
        if not self.security.secret_key or len(self.security.secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")
        
        if not self.security.jwt_secret or len(self.security.jwt_secret) < 32:
            errors.append("JWT_SECRET must be at least 32 characters")
        
        # Validate ports
        if not (1 <= self.database.port <= 65535):
            errors.append(f"Invalid database port: {self.database.port}")
        
        if not (1 <= self.redis.port <= 65535):
            errors.append(f"Invalid Redis port: {self.redis.port}")
        
        if not (1 <= self.monitoring.metrics_port <= 65535):
            errors.append(f"Invalid metrics port: {self.monitoring.metrics_port}")
        
        if not (1 <= self.monitoring.dashboard_port <= 65535):
            errors.append(f"Invalid dashboard port: {self.monitoring.dashboard_port}")
        
        # Validate resource limits
        if self.resources.max_concurrent_tasks <= 0:
            errors.append("MAX_CONCURRENT_TASKS must be positive")
        
        if self.resources.task_timeout <= 0:
            errors.append("TASK_TIMEOUT must be positive")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.monitoring.log_level.upper()),
            format=self.monitoring.log_format,
            handlers=[
                logging.FileHandler(self.monitoring.log_file),
                logging.StreamHandler()
            ]
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ProductionConfig':
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            ProductionConfig instance
        """
        config = cls()
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
            
            # Merge file configuration
            if 'database' in file_config:
                for key, value in file_config['database'].items():
                    if hasattr(config.database, key):
                        setattr(config.database, key, value)
            
            if 'redis' in file_config:
                for key, value in file_config['redis'].items():
                    if hasattr(config.redis, key):
                        setattr(config.redis, key, value)
            
            if 'security' in file_config:
                for key, value in file_config['security'].items():
                    if hasattr(config.security, key):
                        setattr(config.security, key, value)
            
            if 'monitoring' in file_config:
                for key, value in file_config['monitoring'].items():
                    if hasattr(config.monitoring, key):
                        setattr(config.monitoring, key, value)
            
            if 'resources' in file_config:
                for key, value in file_config['resources'].items():
                    if hasattr(config.resources, key):
                        setattr(config.resources, key, value)
            
            # Store pipeline-specific config
            config.pipeline_config = file_config.get('pipeline', {})
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            'environment': self.environment.value,
            'debug': self.debug,
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'name': self.database.name,
                'user': self.database.user,
                'ssl_mode': self.database.ssl_mode,
                'pool_size': self.database.pool_size,
                'max_overflow': self.database.max_overflow,
                'pool_timeout': self.database.pool_timeout,
                'pool_recycle': self.database.pool_recycle
            },
            'redis': {
                'host': self.redis.host,
                'port': self.redis.port,
                'db': self.redis.db,
                'max_connections': self.redis.max_connections,
                'socket_timeout': self.redis.socket_timeout,
                'socket_connect_timeout': self.redis.socket_connect_timeout,
                'retry_on_timeout': self.redis.retry_on_timeout,
                'health_check_interval': self.redis.health_check_interval
            },
            'security': {
                'cors_origins': self.security.cors_origins,
                'rate_limit': self.security.rate_limit,
                'rate_limit_window': self.security.rate_limit_window,
                'enable_https': self.security.enable_https,
                'jwt_expiration': self.security.jwt_expiration
            },
            'monitoring': {
                'enabled': self.monitoring.enabled,
                'metrics_port': self.monitoring.metrics_port,
                'dashboard_port': self.monitoring.dashboard_port,
                'health_check_interval': self.monitoring.health_check_interval,
                'log_level': self.monitoring.log_level,
                'log_format': self.monitoring.log_format,
                'log_file': self.monitoring.log_file,
                'log_max_size': self.monitoring.log_max_size,
                'log_backup_count': self.monitoring.log_backup_count,
                'enable_prometheus': self.monitoring.enable_prometheus,
                'prometheus_port': self.monitoring.prometheus_port,
                'enable_grafana': self.monitoring.enable_grafana,
                'grafana_port': self.monitoring.grafana_port
            },
            'resources': {
                'max_memory': self.resources.max_memory,
                'max_cpu': self.resources.max_cpu,
                'max_concurrent_tasks': self.resources.max_concurrent_tasks,
                'task_timeout': self.resources.task_timeout,
                'cleanup_interval': self.resources.cleanup_interval,
                'temp_dir': self.resources.temp_dir,
                'cache_size': self.resources.cache_size,
                'cache_ttl': self.resources.cache_ttl
            },
            'pipeline': self.pipeline_config
        }
    
    def save_to_file(self, config_path: str):
        """
        Save configuration to YAML file.
        
        Args:
            config_path: Path to save configuration file
        """
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")
    
    def get_database_url(self) -> str:
        """
        Get database connection URL.
        
        Returns:
            Database connection URL
        """
        password_part = f":{self.database.password}" if self.database.password else ""
        return f"postgresql://{self.database.user}{password_part}@{self.database.host}:{self.database.port}/{self.database.name}"
    
    def get_redis_url(self) -> str:
        """
        Get Redis connection URL.
        
        Returns:
            Redis connection URL
        """
        password_part = f":{self.redis.password}@" if self.redis.password else ""
        return f"redis://{password_part}{self.redis.host}:{self.redis.port}/{self.redis.db}"
    
    def is_production(self) -> bool:
        """
        Check if running in production environment.
        
        Returns:
            True if production environment
        """
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """
        Check if running in development environment.
        
        Returns:
            True if development environment
        """
        return self.environment == Environment.DEVELOPMENT


# Global configuration instance
_config: Optional[ProductionConfig] = None


def get_production_config() -> ProductionConfig:
    """
    Get global production configuration instance.
    
    Returns:
        ProductionConfig instance
    """
    global _config
    if _config is None:
        config_path = os.getenv("CONFIG_PATH", "/app/config/production_config.yaml")
        _config = ProductionConfig.from_file(config_path)
    return _config


def reload_config():
    """Reload configuration from file."""
    global _config
    _config = None
    return get_production_config()

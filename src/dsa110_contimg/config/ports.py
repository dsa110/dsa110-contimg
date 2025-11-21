"""Centralized port configuration management.

This module provides a single source of truth for all port assignments
across the DSA-110 pipeline. Ports are configured in config/ports.yaml
and can be overridden via environment variables.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass
class PortConfig:
    """Port configuration for a service."""

    name: str
    default: int
    env_var: Optional[str]
    description: str
    range: Tuple[int, int]
    optional: bool = False
    immutable: bool = False
    conflict_check: bool = False


class PortManager:
    """Manages port assignments and conflict detection."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize port manager.

        Args:
            config_path: Path to ports.yaml. Defaults to config/ports.yaml
                in project root.
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "ports.yaml"

        self.config_path = config_path
        self._ports: Dict[str, PortConfig] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load port configuration from YAML or use defaults."""
        if not self.config_path.exists():
            # Use default configuration if file doesn't exist
            self._load_default_config()
            return

        try:
            import yaml

            with open(self.config_path) as f:
                config = yaml.safe_load(f) or {}

            ports_config = config.get("ports", {})
            for name, port_data in ports_config.items():
                self._ports[name] = PortConfig(
                    name=name,
                    default=port_data.get("default", 8000),
                    env_var=port_data.get("env_var"),
                    description=port_data.get("description", ""),
                    range=tuple(port_data.get("range", [8000, 8000])),
                    optional=port_data.get("optional", False),
                    immutable=port_data.get("immutable", False),
                    conflict_check=port_data.get("conflict_check", False),
                )
        except ImportError:
            # PyYAML not available, use defaults
            self._load_default_config()
        except Exception:
            # Config file error, use defaults
            self._load_default_config()

    def _load_default_config(self) -> None:
        """Load default port configuration (hardcoded fallback)."""
        defaults = {
            "api": PortConfig(
                name="api",
                default=8000,
                env_var="CONTIMG_API_PORT",
                description="Backend FastAPI server",
                range=(8000, 8009),
            ),
            "docs": PortConfig(
                name="docs",
                default=8001,
                env_var="CONTIMG_DOCS_PORT",
                description="MkDocs documentation server",
                range=(8001, 8001),
            ),
            "frontend_dev": PortConfig(
                name="frontend_dev",
                default=5173,
                env_var="CONTIMG_FRONTEND_DEV_PORT",
                description="Vite development server",
                range=(5173, 5173),
            ),
            "dashboard": PortConfig(
                name="dashboard",
                default=3210,
                env_var="CONTIMG_DASHBOARD_PORT",
                description="Script-managed dashboard",
                range=(3210, 3220),
            ),
            "dashboard_docker": PortConfig(
                name="dashboard_docker",
                default=3000,
                env_var="CONTIMG_DASHBOARD_DOCKER_PORT",
                description="Docker production dashboard",
                range=(3000, 3000),
                conflict_check=True,
            ),
            "mcp_http": PortConfig(
                name="mcp_http",
                default=3111,
                env_var="CONTIMG_MCP_HTTP_PORT",
                description="Browser MCP HTTP server",
                range=(3111, 3111),
            ),
            "mcp_ws": PortConfig(
                name="mcp_ws",
                default=9009,
                env_var=None,
                description="Browser MCP WebSocket (hardcoded)",
                range=(9009, 9009),
                immutable=True,
            ),
            "redis": PortConfig(
                name="redis",
                default=6379,
                env_var="REDIS_PORT",
                description="Redis cache backend",
                range=(6379, 6379),
                optional=True,
            ),
        }
        self._ports = defaults

    def get_port(self, service: str, check_conflict: bool = True, auto_resolve: bool = True) -> int:
        """Get port for a service.

        Args:
            service: Service name (e.g., 'api', 'dashboard')
            check_conflict: Whether to check for port conflicts
            auto_resolve: Whether to automatically find alternative port if conflict

        Returns:
            Port number for the service

        Raises:
            ValueError: If service is unknown or port is out of range
            RuntimeError: If port conflict detected and cannot be resolved
        """
        if service not in self._ports:
            raise ValueError(f"Unknown service: {service}. Available: {list(self._ports.keys())}")

        config = self._ports[service]

        # Check environment variable first
        port = config.default
        if config.env_var:
            env_value = os.getenv(config.env_var)
            if env_value:
                try:
                    port = int(env_value)
                except ValueError:
                    raise ValueError(f"Invalid port value for {config.env_var}: {env_value}")

        # Validate port is in range
        if not (config.range[0] <= port <= config.range[1]):
            raise ValueError(f"Port {port} for {service} outside allowed range {config.range}")

        # Check for conflicts if enabled
        if check_conflict and config.conflict_check:
            if self._check_conflict(port, service):
                if auto_resolve and config.range[0] != config.range[1]:
                    # Try fallback range
                    port = self._find_free_port_in_range(config.range, service)
                    if port is None:
                        raise RuntimeError(f"No free ports in range {config.range} for {service}")
                else:
                    raise RuntimeError(
                        f"Port {port} conflict detected for {service}. "
                        f"Process using port: {self._get_port_process(port)}"
                    )

        return port

    def _check_conflict(self, port: int, service: str) -> bool:
        """Check if port is in use.

        Args:
            port: Port number to check
            service: Service name (for logging)

        Returns:
            True if port is in use, False otherwise
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        try:
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            return result == 0
        except Exception:
            sock.close()
            # If we can't check, assume it's free (optimistic)
            return False

    def _get_port_process(self, port: int) -> str:
        """Get information about process using a port.

        Args:
            port: Port number

        Returns:
            Process information string
        """
        try:
            import subprocess

            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    return lines[1]  # Return first process line
        except Exception:
            pass
        return "unknown"

    def _find_free_port_in_range(self, port_range: Tuple[int, int], service: str) -> Optional[int]:
        """Find first free port in range.

        Args:
            port_range: (min, max) port range
            service: Service name (for logging)

        Returns:
            First free port in range, or None if none available
        """
        for port in range(port_range[0], port_range[1] + 1):
            if not self._check_conflict(port, service):
                return port
        return None

    def list_ports(self, check_conflict: bool = False) -> Dict[str, int]:
        """List all configured ports with current values.

        Args:
            check_conflict: Whether to check for conflicts

        Returns:
            Dictionary mapping service names to port numbers
        """
        ports = {}
        for service in self._ports:
            try:
                port = self.get_port(service, check_conflict=check_conflict)
                ports[service] = port
            except Exception:
                # Skip services that fail (e.g., conflicts)
                pass
        return ports

    def validate_all(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """Validate all ports are available.

        Returns:
            Dictionary mapping service names to (is_valid, error_message) tuples
        """
        results = {}
        for service in self._ports:
            try:
                self.get_port(service, check_conflict=True, auto_resolve=False)
                results[service] = (True, None)
            except Exception as e:
                results[service] = (False, str(e))
        return results

    def get_config(self, service: str) -> Optional[PortConfig]:
        """Get port configuration for a service.

        Args:
            service: Service name

        Returns:
            PortConfig if service exists, None otherwise
        """
        return self._ports.get(service)


# Global instance for convenience
_port_manager: Optional[PortManager] = None


def get_port_manager() -> PortManager:
    """Get global PortManager instance."""
    global _port_manager
    if _port_manager is None:
        _port_manager = PortManager()
    return _port_manager


def get_port(service: str, check_conflict: bool = True) -> int:
    """Convenience function to get a port.

    Args:
        service: Service name
        check_conflict: Whether to check for conflicts

    Returns:
        Port number
    """
    return get_port_manager().get_port(service, check_conflict=check_conflict)

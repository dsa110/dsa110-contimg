"""
Docker client wrapper for container management.

Provides a clean interface to Docker operations using the Docker Python SDK,
with fallback to subprocess when the SDK isn't available or socket isn't mounted.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

try:
    import docker

    HAVE_DOCKER_SDK = True
except ImportError:
    HAVE_DOCKER_SDK = False
    docker = None


class DockerClient:
    """Wrapper for Docker operations."""

    def __init__(self):
        self._client: Optional[Any] = None
        self._sdk_available = False

        if HAVE_DOCKER_SDK:
            try:
                # Try to connect to Docker socket
                self._client = docker.from_env()
                self._client.ping()  # Test connection
                self._sdk_available = True
                log.info("Docker SDK connected successfully")
            except Exception as e:
                log.warning(f"Docker SDK not available: {e}")
                self._client = None
                self._sdk_available = False

    def is_available(self) -> bool:
        """Check if Docker client is available."""
        return self._sdk_available

    def get_container(self, container_name: str):
        """Get a container by name."""
        if not self._sdk_available or not self._client:
            return None

        try:
            return self._client.containers.get(container_name)
        except docker.errors.NotFound:
            return None
        except Exception as e:
            log.error(f"Error getting container {container_name}: {e}")
            return None

    def is_container_running(self, container_name: str) -> bool:
        """Check if a container is running."""
        if self._sdk_available and self._client:
            container = self.get_container(container_name)
            if container:
                return container.status == "running"

        # Fallback to subprocess
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception:
            return False

    def start_container(self, container_name: str) -> Dict[str, Any]:
        """Start a container."""
        if self._sdk_available and self._client:
            container = self.get_container(container_name)
            if container:
                try:
                    container.start()
                    return {
                        "success": True,
                        "message": f"Container {container_name} started",
                    }
                except Exception as e:
                    return {"success": False, "message": f"Failed to start: {str(e)}"}
            else:
                return {
                    "success": False,
                    "message": f"Container {container_name} not found",
                }

        # Fallback to subprocess
        try:
            result = subprocess.run(
                ["docker", "start", container_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"Container {container_name} started",
                }
            else:
                return {"success": False, "message": result.stderr or "Unknown error"}
        except Exception as e:
            return {"success": False, "message": f"Failed to start: {str(e)}"}

    def stop_container(self, container_name: str, timeout: int = 10) -> Dict[str, Any]:
        """Stop a container."""
        if self._sdk_available and self._client:
            container = self.get_container(container_name)
            if container:
                try:
                    container.stop(timeout=timeout)
                    return {
                        "success": True,
                        "message": f"Container {container_name} stopped",
                    }
                except Exception as e:
                    return {"success": False, "message": f"Failed to stop: {str(e)}"}
            else:
                return {
                    "success": False,
                    "message": f"Container {container_name} not found",
                }

        # Fallback to subprocess
        try:
            result = subprocess.run(
                ["docker", "stop", "-t", str(timeout), container_name],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"Container {container_name} stopped",
                }
            else:
                return {"success": False, "message": result.stderr or "Unknown error"}
        except Exception as e:
            return {"success": False, "message": f"Failed to stop: {str(e)}"}

    def restart_container(self, container_name: str, timeout: int = 10) -> Dict[str, Any]:
        """Restart a container."""
        if self._sdk_available and self._client:
            container = self.get_container(container_name)
            if container:
                try:
                    container.restart(timeout=timeout)
                    return {
                        "success": True,
                        "message": f"Container {container_name} restarted",
                    }
                except Exception as e:
                    return {"success": False, "message": f"Failed to restart: {str(e)}"}
            else:
                return {
                    "success": False,
                    "message": f"Container {container_name} not found",
                }

        # Fallback to subprocess
        try:
            result = subprocess.run(
                ["docker", "restart", "-t", str(timeout), container_name],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"Container {container_name} restarted",
                }
            else:
                return {"success": False, "message": result.stderr or "Unknown error"}
        except Exception as e:
            return {"success": False, "message": f"Failed to restart: {str(e)}"}

    def get_container_stats(self, container_name: str) -> Optional[Dict[str, Any]]:
        """Get container statistics."""
        if self._sdk_available and self._client:
            container = self.get_container(container_name)
            if container:
                try:
                    stats = container.stats(stream=False)
                    return {
                        "cpu_percent": self._calculate_cpu_percent(stats),
                        "memory_usage": stats.get("memory_stats", {}).get("usage", 0),
                        "memory_limit": stats.get("memory_stats", {}).get("limit", 0),
                        "memory_percent": self._calculate_memory_percent(stats),
                    }
                except Exception as e:
                    log.error(f"Error getting stats: {e}")
                    return None

        # Fallback to subprocess
        try:
            result = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.CPUPerc}},{{.MemUsage}}",
                    container_name,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                if len(parts) == 2:
                    try:
                        cpu_percent = float(parts[0].replace("%", ""))
                        mem_str = parts[1].strip()
                        mem_mb = self._parse_memory(mem_str)
                        return {
                            "cpu_percent": cpu_percent,
                            "memory_mb": mem_mb,
                        }
                    except (ValueError, AttributeError):
                        pass
        except Exception as e:
            log.error(f"Error getting stats via subprocess: {e}")

        return None

    def get_container_info(self, container_name: str) -> Optional[Dict[str, Any]]:
        """Get container information."""
        if self._sdk_available and self._client:
            container = self.get_container(container_name)
            if container:
                try:
                    container.reload()
                    attrs = container.attrs
                    state = attrs.get("State", {})
                    return {
                        "id": container.id,
                        "name": container.name,
                        "status": container.status,
                        "started_at": state.get("StartedAt"),
                        "pid": state.get("Pid"),
                    }
                except Exception as e:
                    log.error(f"Error getting container info: {e}")
                    return None

        # Fallback to subprocess
        try:
            import json

            result = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data:
                    state = data[0].get("State", {})
                    return {
                        "id": data[0].get("Id"),
                        "name": data[0].get("Name", "").lstrip("/"),
                        "status": "running" if state.get("Running") else "stopped",
                        "started_at": state.get("StartedAt"),
                        "pid": state.get("Pid"),
                    }
        except Exception as e:
            log.error(f"Error getting container info via subprocess: {e}")

        return None

    @staticmethod
    def _calculate_cpu_percent(stats: Dict[str, Any]) -> Optional[float]:
        """Calculate CPU percentage from Docker stats."""
        try:
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get(
                "cpu_usage", {}
            ).get("total_usage", 0)
            system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
                "system_cpu_usage", 0
            )

            if system_delta > 0 and cpu_delta > 0:
                num_cpus = len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [])) or 1
                return (cpu_delta / system_delta) * num_cpus * 100.0
        except Exception:
            pass
        return None

    @staticmethod
    def _calculate_memory_percent(stats: Dict[str, Any]) -> Optional[float]:
        """Calculate memory percentage from Docker stats."""
        try:
            memory_stats = stats.get("memory_stats", {})
            usage = memory_stats.get("usage", 0)
            limit = memory_stats.get("limit", 0)
            if limit > 0:
                return (usage / limit) * 100.0
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_memory(mem_str: str) -> Optional[float]:
        """Parse memory string (e.g., '123.45MiB' or '1.23GiB') to MB."""
        try:
            mem_str_upper = mem_str.upper()
            if mem_str_upper.endswith("MIB"):
                return float(mem_str.replace("MiB", "").replace("miB", "").strip())
            elif mem_str_upper.endswith("GIB"):
                return float(mem_str.replace("GiB", "").replace("giB", "").strip()) * 1024
        except (ValueError, AttributeError):
            pass
        return None


# Global instance
_docker_client: Optional[DockerClient] = None


def get_docker_client() -> DockerClient:
    """Get or create the global Docker client instance."""
    global _docker_client
    if _docker_client is None:
        _docker_client = DockerClient()
    return _docker_client

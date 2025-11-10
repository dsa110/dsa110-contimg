"""
Streaming Service Manager

Provides unified control and monitoring of the streaming converter service.
Allows the API to start, stop, configure, and monitor the streaming service
without requiring command-line access.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import psutil

from dsa110_contimg.api.docker_client import get_docker_client, DockerClient

log = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """Configuration for streaming service."""

    input_dir: str
    output_dir: str
    queue_db: str
    registry_db: str
    scratch_dir: str
    expected_subbands: int = 16
    chunk_duration: float = 5.0  # minutes
    log_level: str = "INFO"
    use_subprocess: bool = True
    monitoring: bool = True
    monitor_interval: float = 60.0
    poll_interval: float = 5.0
    worker_poll_interval: float = 5.0
    max_workers: int = 4
    stage_to_tmpfs: bool = False
    tmpfs_path: str = "/dev/shm"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StreamingConfig:
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class StreamingStatus:
    """Status of streaming service."""

    running: bool
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    uptime_seconds: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
    config: Optional[StreamingConfig] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "running": self.running,
            "pid": self.pid,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "uptime_seconds": self.uptime_seconds,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "error": self.error,
        }
        if self.config:
            result["config"] = self.config.to_dict()
        return result


class StreamingServiceManager:
    """Manages the streaming converter service lifecycle."""

    def __init__(
        self, pid_file: Optional[Path] = None, config_file: Optional[Path] = None
    ):
        """
        Initialize the streaming service manager.

        Args:
            pid_file: Path to PID file for tracking service process
            config_file: Path to configuration file
        """
        self.pid_file = (
            pid_file or Path(os.getenv("PIPELINE_STATE_DIR", "state")) / "streaming.pid"
        )
        self.config_file = (
            config_file
            or Path(os.getenv("PIPELINE_STATE_DIR", "state")) / "streaming_config.json"
        )
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._docker_client: Optional[DockerClient] = None

    def _get_docker_client(self) -> DockerClient:
        """Get or create the cached Docker client instance."""
        if self._docker_client is None:
            self._docker_client = get_docker_client()
        return self._docker_client

    def get_status(self) -> StreamingStatus:
        """Get current status of streaming service."""
        # Check Docker first if in Docker environment
        if self._is_docker_environment():
            return self._get_status_via_docker()

        pid = self._get_pid()

        if pid is None:
            return StreamingStatus(running=False, config=self._load_config())

        try:
            process = psutil.Process(pid)
            if not process.is_running():
                # PID file exists but process is dead
                self._clear_pid()
                return StreamingStatus(running=False, config=self._load_config())

            # Process is running
            started_at = datetime.fromtimestamp(process.create_time())
            uptime = (datetime.now() - started_at).total_seconds()

            try:
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cpu_percent = None
                memory_mb = None

            return StreamingStatus(
                running=True,
                pid=pid,
                started_at=started_at,
                uptime_seconds=uptime,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                config=self._load_config(),
            )
        except psutil.NoSuchProcess:
            self._clear_pid()
            return StreamingStatus(running=False, config=self._load_config())
        except FileNotFoundError as e:
            # Handle missing commands gracefully
            error_msg = str(e)
            if "docker-compose" in error_msg.lower():
                log.warning("docker-compose not available")
                return StreamingStatus(
                    running=False,
                    error="Docker control unavailable: docker-compose not found. Use Docker SDK or direct docker commands.",
                    config=self._load_config(),
                )
            return StreamingStatus(
                running=False,
                error=f"Command not found: {error_msg}",
                config=self._load_config(),
            )
        except Exception as e:
            log.error(f"Error getting streaming status: {e}")
            # Filter docker-compose errors for cleaner messages
            error_msg = str(e)
            if "docker-compose" in error_msg.lower():
                return StreamingStatus(
                    running=False,
                    error="Docker control unavailable. Please use Docker SDK or direct docker commands.",
                    config=self._load_config(),
                )
            return StreamingStatus(
                running=False,
                error=str(e),
                config=self._load_config(),
            )

    def _get_status_via_docker(self) -> StreamingStatus:
        """Get streaming service status via Docker."""
        try:
            docker_client = self._get_docker_client()
            container_name = "contimg-stream"

            # Check if container is running
            if not docker_client.is_container_running(container_name):
                return StreamingStatus(running=False, config=self._load_config())

            # Get container info
            info = docker_client.get_container_info(container_name)
            if not info:
                return StreamingStatus(running=False, config=self._load_config())

            # Get stats
            stats = docker_client.get_container_stats(container_name)

            # Parse start time
            started_at = None
            uptime = None
            if info.get("started_at"):
                try:
                    started_at_str = info["started_at"]
                    started_at = datetime.fromisoformat(
                        started_at_str.replace("Z", "+00:00")
                    )
                    uptime = (
                        datetime.now() - started_at.replace(tzinfo=None)
                    ).total_seconds()
                except (ValueError, AttributeError):
                    pass

            # Get PID
            pid = info.get("pid")
            if pid:
                self._save_pid(pid)

            return StreamingStatus(
                running=True,
                pid=pid,
                started_at=started_at,
                uptime_seconds=uptime,
                cpu_percent=stats.get("cpu_percent") if stats else None,
                memory_mb=(
                    stats.get("memory_mb")
                    if stats
                    else (stats.get("memory_usage", 0) / 1024 / 1024 if stats else None)
                ),
                config=self._load_config(),
            )
        except FileNotFoundError as e:
            # Handle missing docker-compose or docker command gracefully
            error_msg = str(e)
            if "docker-compose" in error_msg:
                # Don't log as error - this is expected when docker-compose isn't available
                log.debug(
                    "docker-compose not available (expected), using Docker SDK or direct docker commands"
                )
                return StreamingStatus(
                    running=False,
                    error="Docker control unavailable: docker-compose not found. Use Docker SDK or direct docker commands.",
                    config=self._load_config(),
                )
            else:
                log.warning(f"Docker command not found (handled gracefully): {e}")
                return StreamingStatus(
                    running=False,
                    error=f"Docker command not found: {error_msg}",
                    config=self._load_config(),
                )
        except Exception as e:
            # Filter out docker-compose related errors for cleaner user messages
            error_msg = str(e)
            if "docker-compose" in error_msg.lower():
                # Don't log this as an error - it's expected when docker-compose isn't available
                log.debug(f"Docker-compose not available (expected): {e}")
                return StreamingStatus(
                    running=False,
                    error="Docker control unavailable. Please use Docker SDK or direct docker commands.",
                    config=self._load_config(),
                )
            # Log other errors as warnings/info since we handle them gracefully
            log.warning(f"Error getting Docker status (handled gracefully): {e}")
            return StreamingStatus(
                running=False,
                error=str(e),
                config=self._load_config(),
            )

    def _is_docker_environment(self) -> bool:
        """Check if we're running in a Docker environment."""
        # Check if we're in a container
        if Path("/.dockerenv").exists():
            return True
        # Check if docker-compose.yml exists nearby
        docker_compose = (
            Path(__file__).parent.parent.parent.parent
            / "ops"
            / "docker"
            / "docker-compose.yml"
        )
        return docker_compose.exists()

    def start(self, config: Optional[StreamingConfig] = None) -> Dict[str, Any]:
        """
        Start the streaming service.

        Args:
            config: Configuration to use. If None, loads from file or uses defaults.

        Returns:
            Dictionary with status information
        """
        status = self.get_status()
        if status.running:
            return {
                "success": False,
                "message": "Streaming service is already running",
                "pid": status.pid,
            }

        # Check if we should use Docker
        if self._is_docker_environment():
            return self._start_via_docker()

        # Load or use provided config
        if config is None:
            config = self._load_config()
        if config is None:
            # Use defaults from environment with validation
            def safe_int(
                env_var: str, default: str, min_val: int = 1, max_val: int = 32
            ) -> int:
                """Safely convert environment variable to integer with validation."""
                value_str = os.getenv(env_var, default)
                try:
                    value = int(value_str)
                    if value < min_val or value > max_val:
                        raise ValueError(
                            f"{env_var}={value} must be between {min_val} and {max_val}"
                        )
                    return value
                except ValueError as e:
                    if "invalid literal" in str(e) or "could not convert" in str(e):
                        raise ValueError(
                            f"Invalid integer value for {env_var}: '{value_str}'. "
                            f"Expected integer between {min_val} and {max_val}."
                        ) from e
                    raise

            def safe_float(env_var: str, default: str, min_val: float = 0.0) -> float:
                """Safely convert environment variable to float with validation."""
                value_str = os.getenv(env_var, default)
                try:
                    value = float(value_str)
                    if value < min_val:
                        raise ValueError(f"{env_var}={value} must be >= {min_val}")
                    return value
                except ValueError as e:
                    if "invalid literal" in str(e) or "could not convert" in str(e):
                        raise ValueError(
                            f"Invalid float value for {env_var}: '{value_str}'. "
                            f"Expected float >= {min_val}."
                        ) from e
                    raise

            config = StreamingConfig(
                input_dir=os.getenv("CONTIMG_INPUT_DIR", "/data/incoming"),
                output_dir=os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/ms"),
                queue_db=os.getenv("CONTIMG_QUEUE_DB", "state/ingest.sqlite3"),
                registry_db=os.getenv(
                    "CONTIMG_REGISTRY_DB", "state/cal_registry.sqlite3"
                ),
                scratch_dir=os.getenv("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg"),
                expected_subbands=safe_int("CONTIMG_EXPECTED_SUBBANDS", "16"),
                chunk_duration=safe_float("CONTIMG_CHUNK_MINUTES", "5.0", min_val=0.1),
                log_level=os.getenv("CONTIMG_LOG_LEVEL", "INFO"),
                use_subprocess=True,
                monitoring=True,
                monitor_interval=safe_float(
                    "CONTIMG_MONITOR_INTERVAL", "60.0", min_val=1.0
                ),
            )

        # Save config
        self._save_config(config)

        # Build command
        cmd = self._build_command(config)

        try:
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent.parent,
            )

            # Save PID
            self._save_pid(process.pid)

            # Wait a moment to check if it started successfully
            time.sleep(1)
            if process.poll() is not None:
                # Process exited immediately
                stdout, stderr = process.communicate()
                error_msg = stderr.decode() if stderr else "Unknown error"
                self._clear_pid()
                return {
                    "success": False,
                    "message": f"Streaming service failed to start: {error_msg}",
                }

            return {
                "success": True,
                "message": "Streaming service started successfully",
                "pid": process.pid,
            }
        except Exception as e:
            log.error(f"Error starting streaming service: {e}")
            return {
                "success": False,
                "message": f"Failed to start streaming service: {str(e)}",
            }

    def _start_via_docker(self) -> Dict[str, Any]:
        """Start streaming service via Docker."""
        try:
            docker_client = self._get_docker_client()
            container_name = "contimg-stream"

            # Try to start the container directly
            result = docker_client.start_container(container_name)

            if result["success"]:
                # Get container info to save PID
                info = docker_client.get_container_info(container_name)
                if info and info.get("pid"):
                    self._save_pid(info["pid"])

            return result
        except Exception as e:
            log.error(f"Error starting streaming service via Docker: {e}")
            return {
                "success": False,
                "message": f"Failed to start via Docker: {str(e)}",
            }

    def _stop_via_docker(self) -> Dict[str, Any]:
        """Stop streaming service via Docker."""
        try:
            docker_client = self._get_docker_client()
            container_name = "contimg-stream"

            result = docker_client.stop_container(container_name)
            self._clear_pid()

            return result
        except Exception as e:
            log.error(f"Error stopping streaming service via Docker: {e}")
            self._clear_pid()
            return {
                "success": False,
                "message": f"Failed to stop via Docker: {str(e)}",
            }

    def stop(self, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Stop the streaming service.

        Args:
            timeout: Maximum time to wait for graceful shutdown

        Returns:
            Dictionary with status information
        """
        # Check if we should use Docker
        if self._is_docker_environment():
            return self._stop_via_docker()

        status = self.get_status()
        if not status.running or status.pid is None:
            return {
                "success": False,
                "message": "Streaming service is not running",
            }

        try:
            process = psutil.Process(status.pid)

            # Try graceful shutdown first
            process.terminate()

            try:
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                process.kill()
                process.wait()

            self._clear_pid()
            return {
                "success": True,
                "message": "Streaming service stopped successfully",
            }
        except psutil.NoSuchProcess:
            self._clear_pid()
            return {
                "success": True,
                "message": "Streaming service was not running (stale PID)",
            }
        except Exception as e:
            log.error(f"Error stopping streaming service: {e}")
            return {
                "success": False,
                "message": f"Failed to stop streaming service: {str(e)}",
            }

    def restart(self, config: Optional[StreamingConfig] = None) -> Dict[str, Any]:
        """
        Restart the streaming service.

        Args:
            config: Optional new configuration

        Returns:
            Dictionary with status information
        """
        # Check if we should use Docker
        if self._is_docker_environment():
            try:
                docker_client = self._get_docker_client()
                container_name = "contimg-stream"
                result = docker_client.restart_container(container_name)

                # Update config if provided
                if config:
                    self._save_config(config)

                return result
            except Exception as e:
                log.error(f"Error restarting streaming service via Docker: {e}")
                return {
                    "success": False,
                    "message": f"Failed to restart via Docker: {str(e)}",
                }

        stop_result = self.stop()
        if not stop_result.get("success") and "not running" not in stop_result.get(
            "message", ""
        ):
            return {
                "success": False,
                "message": f"Failed to stop service: {stop_result.get('message')}",
            }

        time.sleep(1)  # Brief pause before restart
        return self.start(config)

    def update_config(self, config: StreamingConfig) -> Dict[str, Any]:
        """
        Update streaming service configuration.

        Args:
            config: New configuration

        Returns:
            Dictionary with status information
        """
        status = self.get_status()
        was_running = status.running

        # Save new config
        self._save_config(config)

        # Restart if service was running
        if was_running:
            return self.restart(config)
        else:
            return {
                "success": True,
                "message": "Configuration updated (service not running)",
            }

    def get_health(self) -> Dict[str, Any]:
        """
        Get health check information.

        Returns:
            Dictionary with health status
        """
        status = self.get_status()

        health = {
            "healthy": status.running and status.error is None,
            "running": status.running,
            "uptime_seconds": status.uptime_seconds,
        }

        if status.error:
            health["error"] = status.error

        if status.running:
            health["cpu_percent"] = status.cpu_percent
            health["memory_mb"] = status.memory_mb

        return health

    def _build_command(self, config: StreamingConfig) -> list[str]:
        """Build command to start streaming service."""
        python_bin = os.getenv("CASA6_PYTHON", "/opt/miniforge/envs/casa6/bin/python")

        cmd = [
            python_bin,
            "-m",
            "dsa110_contimg.conversion.streaming.streaming_converter",
            "--input-dir",
            config.input_dir,
            "--output-dir",
            config.output_dir,
            "--queue-db",
            config.queue_db,
            "--registry-db",
            config.registry_db,
            "--scratch-dir",
            config.scratch_dir,
            "--log-level",
            config.log_level,
            "--expected-subbands",
            str(config.expected_subbands),
            "--chunk-duration",
            str(config.chunk_duration),
            "--monitor-interval",
            str(config.monitor_interval),
            "--poll-interval",
            str(config.poll_interval),
            "--worker-poll-interval",
            str(config.worker_poll_interval),
            "--max-workers",
            str(config.max_workers),
        ]

        if config.use_subprocess:
            cmd.append("--use-subprocess")
        if config.monitoring:
            cmd.append("--monitoring")
        if config.stage_to_tmpfs:
            cmd.append("--stage-to-tmpfs")
            cmd.extend(["--tmpfs-path", config.tmpfs_path])

        return cmd

    def _get_pid(self) -> Optional[int]:
        """Get PID from file."""
        if not self.pid_file.exists():
            return None
        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())
            return pid
        except (ValueError, IOError):
            return None

    def _save_pid(self, pid: int) -> None:
        """Save PID to file."""
        with open(self.pid_file, "w") as f:
            f.write(str(pid))

    def _clear_pid(self) -> None:
        """Clear PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()

    def _load_config(self) -> Optional[StreamingConfig]:
        """Load configuration from file."""
        if not self.config_file.exists():
            return None
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            return StreamingConfig.from_dict(data)
        except (json.JSONDecodeError, IOError, TypeError) as e:
            log.warning(f"Failed to load streaming config: {e}")
            return None

    def _save_config(self, config: StreamingConfig) -> None:
        """Save configuration to file."""
        with open(self.config_file, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

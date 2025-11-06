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
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "error": self.error,
        }
        if self.config:
            result["config"] = self.config.to_dict()
        return result


class StreamingServiceManager:
    """Manages the streaming converter service lifecycle."""

    def __init__(self, pid_file: Optional[Path] = None, config_file: Optional[Path] = None):
        """
        Initialize the streaming service manager.
        
        Args:
            pid_file: Path to PID file for tracking service process
            config_file: Path to configuration file
        """
        self.pid_file = pid_file or Path(os.getenv("PIPELINE_STATE_DIR", "state")) / "streaming.pid"
        self.config_file = config_file or Path(os.getenv("PIPELINE_STATE_DIR", "state")) / "streaming_config.json"
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

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
        except Exception as e:
            log.error(f"Error getting streaming status: {e}")
            return StreamingStatus(
                running=False,
                error=str(e),
                config=self._load_config(),
            )

    def _get_status_via_docker(self) -> StreamingStatus:
        """Get streaming service status via Docker."""
        try:
            docker_compose_dir = Path(__file__).parent.parent.parent.parent / "ops" / "docker"
            
            # Check if container is running
            result = subprocess.run(
                ["docker-compose", "ps", "-q", "stream"],
                cwd=docker_compose_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            container_id = result.stdout.strip()
            
            if not container_id:
                return StreamingStatus(running=False, config=self._load_config())
            
            # Get container status
            inspect_result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if inspect_result.returncode != 0 or inspect_result.stdout.strip() != "true":
                return StreamingStatus(running=False, config=self._load_config())
            
            # Container is running - get stats
            stats_result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}},{{.MemUsage}}", container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            cpu_percent = None
            memory_mb = None
            
            if stats_result.returncode == 0:
                parts = stats_result.stdout.strip().split(",")
                if len(parts) == 2:
                    try:
                        cpu_percent = float(parts[0].replace("%", ""))
                        # Parse memory (e.g., "123.45MiB" or "1.23GiB")
                        mem_str = parts[1].strip()
                        mem_str_upper = mem_str.upper()
                        if mem_str_upper.endswith("MIB"):
                            memory_mb = float(mem_str.replace("MiB", "").replace("miB", "").strip())
                        elif mem_str_upper.endswith("GIB"):
                            memory_mb = float(mem_str.replace("GiB", "").replace("giB", "").strip()) * 1024
                    except (ValueError, AttributeError):
                        pass
            
            # Get start time
            started_result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.StartedAt}}", container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            started_at = None
            uptime = None
            
            if started_result.returncode == 0:
                try:
                    started_at_str = started_result.stdout.strip()
                    started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                    uptime = (datetime.now() - started_at.replace(tzinfo=None)).total_seconds()
                except (ValueError, AttributeError):
                    pass
            
            # Get PID
            pid_result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Pid}}", container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            pid = None
            if pid_result.returncode == 0:
                try:
                    pid = int(pid_result.stdout.strip())
                    self._save_pid(pid)
                except ValueError:
                    pass
            
            return StreamingStatus(
                running=True,
                pid=pid,
                started_at=started_at,
                uptime_seconds=uptime,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                config=self._load_config(),
            )
        except Exception as e:
            log.error(f"Error getting Docker status: {e}")
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
        docker_compose = Path(__file__).parent.parent.parent.parent / "ops" / "docker" / "docker-compose.yml"
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
            # Use defaults from environment
            config = StreamingConfig(
                input_dir=os.getenv("CONTIMG_INPUT_DIR", "/data/incoming"),
                output_dir=os.getenv("CONTIMG_OUTPUT_DIR", "/scratch/dsa110-contimg/ms"),
                queue_db=os.getenv("CONTIMG_QUEUE_DB", "state/ingest.sqlite3"),
                registry_db=os.getenv("CONTIMG_REGISTRY_DB", "state/cal_registry.sqlite3"),
                scratch_dir=os.getenv("CONTIMG_SCRATCH_DIR", "/scratch/dsa110-contimg"),
                expected_subbands=int(os.getenv("CONTIMG_EXPECTED_SUBBANDS", "16")),
                chunk_duration=float(os.getenv("CONTIMG_CHUNK_MINUTES", "5.0")),
                log_level=os.getenv("CONTIMG_LOG_LEVEL", "INFO"),
                use_subprocess=True,
                monitoring=True,
                monitor_interval=float(os.getenv("CONTIMG_MONITOR_INTERVAL", "60.0")),
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
        """Start streaming service via docker-compose."""
        try:
            docker_compose_dir = Path(__file__).parent.parent.parent.parent / "ops" / "docker"
            result = subprocess.run(
                ["docker-compose", "up", "-d", "stream"],
                cwd=docker_compose_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                # Get container PID
                pid_result = subprocess.run(
                    ["docker-compose", "ps", "-q", "stream"],
                    cwd=docker_compose_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                container_id = pid_result.stdout.strip()
                
                if container_id:
                    # Get actual process PID from container
                    inspect_result = subprocess.run(
                        ["docker", "inspect", "-f", "{{.State.Pid}}", container_id],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if inspect_result.returncode == 0:
                        try:
                            pid = int(inspect_result.stdout.strip())
                            self._save_pid(pid)
                        except ValueError:
                            pass
                
                return {
                    "success": True,
                    "message": "Streaming service started via Docker",
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to start via Docker: {result.stderr}",
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Timeout starting streaming service via Docker",
            }
        except Exception as e:
            log.error(f"Error starting streaming service via Docker: {e}")
            return {
                "success": False,
                "message": f"Failed to start via Docker: {str(e)}",
            }

    def _stop_via_docker(self) -> Dict[str, Any]:
        """Stop streaming service via docker-compose."""
        try:
            docker_compose_dir = Path(__file__).parent.parent.parent.parent / "ops" / "docker"
            result = subprocess.run(
                ["docker-compose", "stop", "stream"],
                cwd=docker_compose_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            self._clear_pid()
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Streaming service stopped via Docker",
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to stop via Docker: {result.stderr}",
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Timeout stopping streaming service via Docker",
            }
        except Exception as e:
            log.error(f"Error stopping streaming service via Docker: {e}")
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
        stop_result = self.stop()
        if not stop_result.get("success") and "not running" not in stop_result.get("message", ""):
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
            "--input-dir", config.input_dir,
            "--output-dir", config.output_dir,
            "--queue-db", config.queue_db,
            "--registry-db", config.registry_db,
            "--scratch-dir", config.scratch_dir,
            "--log-level", config.log_level,
            "--expected-subbands", str(config.expected_subbands),
            "--chunk-duration", str(config.chunk_duration),
            "--monitor-interval", str(config.monitor_interval),
            "--poll-interval", str(config.poll_interval),
            "--worker-poll-interval", str(config.worker_poll_interval),
            "--max-workers", str(config.max_workers),
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


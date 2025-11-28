"""Docker utilities for WSClean operations.

This module provides utilities for running WSClean in Docker containers,
specifically designed to avoid volume unmounting issues that cause hangs
on NFS filesystems.
"""

import atexit
import logging
import os
import signal
import subprocess
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dsa110_contimg.utils.gpu_utils import GPUConfig

logger = logging.getLogger(__name__)


class WSCleanContainer:
    """Manages a long-running WSClean Docker container.

    This class avoids Docker volume unmounting hangs by using a single
    long-running container and executing commands inside it with `docker exec`.

    Usage:
        # Context manager (recommended - automatic cleanup)
        with WSCleanContainer() as container:
            container.wsclean(["-predict", ...])

        # Manual lifecycle management
        container = WSCleanContainer()
        container.start()
        container.wsclean(["-predict", ...])
        container.stop()
        
        # With GPU acceleration
        from dsa110_contimg.utils.gpu_utils import get_gpu_config
        gpu_config = get_gpu_config()
        with WSCleanContainer(gpu_config=gpu_config) as container:
            container.wsclean(["-gridder", "idg", "-idg-mode", "gpu", ...])

    See: docs/troubleshooting/docker_wsclean_longrunning_solution.md
    """

    def __init__(
        self,
        container_name: Optional[str] = None,
        image: str = "wsclean-everybeam:0.7.4",
        mount_path: str = "/stage/dsa110-contimg",
        container_mount: str = "/data",
        gpu_config: Optional["GPUConfig"] = None,
    ):
        """Initialize WSClean container manager.

        Args:
            container_name: Unique name for container (default: wsclean-worker-{pid})
            image: Docker image to use
            mount_path: Host path to mount
            container_mount: Path inside container for mount
            gpu_config: GPU configuration for enabling GPU acceleration
        """
        self.container_name = container_name or f"wsclean-worker-{os.getpid()}"
        self.image = image
        self.mount_path = mount_path
        self.container_mount = container_mount
        self.gpu_config = gpu_config
        self._started = False

    def start(self) -> bool:
        """Start the long-running container.

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            logger.info(f"Container {self.container_name} already running")
            self._started = True
            return True

        try:
            cmd = [
                "docker",
                "run",
                "-d",  # Detached
                "--name",
                self.container_name,
            ]
            
            # Add GPU support if enabled
            if self.gpu_config is not None and self.gpu_config.enabled and self.gpu_config.has_gpu:
                cmd.extend(["--gpus", "all"])
                logger.info(f"Container {self.container_name} will have GPU access")
            
            cmd.extend([
                "-v",
                f"{self.mount_path}:{self.container_mount}",
                self.image,
                "sleep",
                "infinity",  # Keep container running
            ])

            logger.info(f"Starting WSClean container: {self.container_name}")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            container_id = result.stdout.strip()
            logger.info(f"Started WSClean container: {container_id[:12]}")
            self._started = True
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout starting container {self.container_name}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start container: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting container: {e}")
            return False

    def is_running(self) -> bool:
        """Check if container is running.

        Returns:
            True if container is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"name=^{self.container_name}$"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def exec(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess:
        """Execute command inside the running container.

        Args:
            cmd: Command and arguments to execute
            timeout: Timeout in seconds (None for no timeout)
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess instance

        Raises:
            RuntimeError: If container is not running
            subprocess.CalledProcessError: If command fails
            subprocess.TimeoutExpired: If command times out
        """
        if not self.is_running():
            # Try to restart container
            logger.warning(f"Container {self.container_name} not running, attempting restart")
            if not self.start():
                raise RuntimeError(
                    f"Container {self.container_name} is not running and failed to start"
                )

        docker_cmd = ["docker", "exec", self.container_name] + cmd

        logger.debug(f"Executing in container: {' '.join(cmd)}")

        return subprocess.run(
            docker_cmd,
            check=True,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
        )

    def wsclean(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess:
        """Execute wsclean command inside container.

        Args:
            args: WSClean arguments (without 'wsclean' command itself)
            timeout: Timeout in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess instance
        """
        cmd = ["wsclean"] + args
        return self.exec(cmd, timeout=timeout, capture_output=capture_output)

    def stop(self) -> None:
        """Stop and remove the container.

        This method is safe to call multiple times.
        """
        if not self.is_running():
            logger.debug(f"Container {self.container_name} not running, nothing to stop")
            return

        try:
            logger.info(f"Stopping container {self.container_name}")
            subprocess.run(
                ["docker", "stop", self.container_name],
                check=True,
                capture_output=True,
                timeout=30,
            )
            subprocess.run(
                ["docker", "rm", self.container_name],
                check=True,
                capture_output=True,
                timeout=10,
            )
            logger.info(f"Stopped and removed container {self.container_name}")
            self._started = False
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout stopping container {self.container_name}, forcing kill")
            try:
                subprocess.run(
                    ["docker", "kill", self.container_name],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    ["docker", "rm", self.container_name],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )
            except Exception as e:
                logger.error(f"Failed to force-kill container: {e}")
        except Exception as e:
            logger.error(f"Error stopping container: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False  # Don't suppress exceptions


# Global container instance for reuse across function calls
_global_wsclean_container: Optional[WSCleanContainer] = None


def get_wsclean_container(force_new: bool = False, **kwargs) -> WSCleanContainer:
    """Get or create a global WSClean container instance.

    This function maintains a single global container that can be reused
    across multiple wsclean operations for better performance.

    Args:
        force_new: If True, stop existing container and create new one
        **kwargs: Arguments passed to WSCleanContainer constructor

    Returns:
        WSCleanContainer instance
    """
    global _global_wsclean_container

    if force_new and _global_wsclean_container is not None:
        _global_wsclean_container.stop()
        _global_wsclean_container = None

    if _global_wsclean_container is None or not _global_wsclean_container.is_running():
        _global_wsclean_container = WSCleanContainer(**kwargs)
        _global_wsclean_container.start()

        # Register cleanup on exit
        atexit.register(_cleanup_global_container)

    return _global_wsclean_container


def _cleanup_global_container():
    """Cleanup function called on process exit."""
    global _global_wsclean_container
    if _global_wsclean_container is not None:
        logger.debug("Cleaning up global WSClean container on exit")
        _global_wsclean_container.stop()
        _global_wsclean_container = None


# Register signal handlers for graceful shutdown
def _signal_handler(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}, cleaning up containers")
    _cleanup_global_container()
    # Re-raise signal for normal termination
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def convert_host_path_to_container(
    host_path: str,
    host_mount: str = "/stage/dsa110-contimg",
    container_mount: str = "/data",
) -> str:
    """Convert host filesystem path to container path.

    Args:
        host_path: Path on host filesystem
        host_mount: Host mount point
        container_mount: Container mount point

    Returns:
        Equivalent path inside container

    Example:
        >>> convert_host_path_to_container("/stage/dsa110-contimg/test.ms")
        "/data/test.ms"
    """
    host_path = str(Path(host_path).resolve())
    host_mount = str(Path(host_mount).resolve())

    if not host_path.startswith(host_mount):
        raise ValueError(f"Path {host_path} is not under mount point {host_mount}")

    relative = Path(host_path).relative_to(host_mount)
    container_path = Path(container_mount) / relative
    return str(container_path)

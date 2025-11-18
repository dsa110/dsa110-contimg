"""
CARTA service management.

Provides functionality to start, stop, and check the status of CARTA services.
CARTA can run as a Docker container or as standalone processes.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import time
from typing import Any, Dict, Optional

import requests

from dsa110_contimg.api.docker_client import get_docker_client

log = logging.getLogger(__name__)

# CARTA service configuration
CARTA_CONTAINER_NAME = "carta-backend"
CARTA_BACKEND_PORT = 9002
CARTA_FRONTEND_PORT = 9003
CARTA_IMAGE = "cartavis/carta-backend:latest"
CARTA_HEALTH_ENDPOINT = f"http://localhost:{CARTA_BACKEND_PORT}/api/health"
CARTA_STARTUP_TIMEOUT = 30  # seconds


class CARTAServiceManager:
    """Manages CARTA backend and frontend services."""

    def __init__(self):
        self.docker_client = get_docker_client()

    def is_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open and accepting connections."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def check_backend_health(self) -> bool:
        """Check if CARTA backend is healthy by calling the health endpoint."""
        try:
            response = requests.get(CARTA_HEALTH_ENDPOINT, timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of CARTA services.

        Returns:
            Dictionary with status information including:
            - running: bool - Whether services are running
            - backend_port_open: bool - Whether backend port is open
            - frontend_port_open: bool - Whether frontend port is open
            - backend_healthy: bool - Whether backend health check passes
            - container_running: bool - Whether Docker container is running (if using Docker)
            - method: str - How CARTA is running ("docker", "standalone", or "unknown")
        """
        status: Dict[str, Any] = {
            "running": False,
            "backend_port_open": False,
            "frontend_port_open": False,
            "backend_healthy": False,
            "container_running": False,
            "method": "unknown",
        }

        # Check if ports are open
        status["backend_port_open"] = self.is_port_open("localhost", CARTA_BACKEND_PORT)
        status["frontend_port_open"] = self.is_port_open("localhost", CARTA_FRONTEND_PORT)

        # Check Docker container
        if self.docker_client.is_available():
            status["container_running"] = self.docker_client.is_container_running(
                CARTA_CONTAINER_NAME
            )
            if status["container_running"]:
                status["method"] = "docker"

        # Check backend health
        if status["backend_port_open"]:
            status["backend_healthy"] = self.check_backend_health()

        # Overall running status
        status["running"] = (
            status["backend_port_open"]
            and status["frontend_port_open"]
            and status["backend_healthy"]
        )

        # If ports are open but no Docker container, assume standalone
        if status["running"] and status["method"] == "unknown":
            status["method"] = "standalone"

        return status

    def start_service(self) -> Dict[str, Any]:
        """
        Start CARTA services.

        Tries Docker first, then falls back to checking if services are already running.

        Returns:
            Dictionary with success status and message.
        """
        # Check if already running
        status = self.get_status()
        if status["running"]:
            return {
                "success": True,
                "message": "CARTA services are already running",
                "method": status["method"],
            }

        # Try to start via Docker
        if self.docker_client.is_available():
            container = self.docker_client.get_container(CARTA_CONTAINER_NAME)

            if container:
                # Container exists, try to start it
                result = self.docker_client.start_container(CARTA_CONTAINER_NAME)
                if result["success"]:
                    # Wait for services to be ready
                    if self._wait_for_services():
                        return {
                            "success": True,
                            "message": "CARTA services started via Docker",
                            "method": "docker",
                        }
                    else:
                        return {
                            "success": False,
                            "message": "CARTA container started but services not ready",
                        }
                else:
                    return result
            else:
                # Container doesn't exist, try to create and run it
                return self._create_and_start_container()

        # Docker not available, check if services are already running
        status = self.get_status()
        if status["backend_port_open"] or status["frontend_port_open"]:
            return {
                "success": False,
                "message": "CARTA ports are in use but services may not be fully ready. "
                "Please start CARTA manually or install Docker.",
            }

        return {
            "success": False,
            "message": "Cannot start CARTA: Docker is not available and services are not running. "
            "Please install Docker or start CARTA manually.",
        }

    def _create_and_start_container(self) -> Dict[str, Any]:
        """Create and start a new CARTA Docker container."""
        try:
            # Check if Docker is available
            if not self.docker_client.is_available():
                return {
                    "success": False,
                    "message": "Docker is not available. Cannot create CARTA container.",
                }

            # Use subprocess to run docker command (Docker SDK create is more complex)
            # Note: cmd is a list of static strings, not user-controlled input, so this is safe
            cmd = [
                "docker",
                "run",
                "-d",
                "--name",
                CARTA_CONTAINER_NAME,
                "-p",
                f"{CARTA_BACKEND_PORT}:3002",
                "-p",
                f"{CARTA_FRONTEND_PORT}:3000",
                CARTA_IMAGE,
            ]

            log.info(f"Creating CARTA container: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,  # Safe: list of static strings, not user input
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Wait for services to be ready
                if self._wait_for_services():
                    return {
                        "success": True,
                        "message": "CARTA container created and started",
                        "method": "docker",
                    }
                else:
                    return {
                        "success": False,
                        "message": "CARTA container created but services not ready",
                    }
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                # Check if container already exists
                if "already in use" in error_msg or "Conflict" in error_msg:
                    # Try to start existing container
                    start_result = self.docker_client.start_container(CARTA_CONTAINER_NAME)
                    if start_result["success"] and self._wait_for_services():
                        return {
                            "success": True,
                            "message": "CARTA container started (was already created)",
                            "method": "docker",
                        }
                return {
                    "success": False,
                    "message": f"Failed to create container: {error_msg}",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Timeout creating CARTA container"}
        except Exception as e:
            log.exception("Error creating CARTA container")
            return {"success": False, "message": f"Error creating container: {str(e)}"}

    def _wait_for_services(self, timeout: int = CARTA_STARTUP_TIMEOUT) -> bool:
        """Wait for CARTA services to become ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status()
            if status["running"]:
                return True
            time.sleep(1)
        return False

    def stop_service(self) -> Dict[str, Any]:
        """
        Stop CARTA services.

        Returns:
            Dictionary with success status and message.
        """
        status = self.get_status()

        if not status["running"]:
            return {
                "success": True,
                "message": "CARTA services are not running",
            }

        # Try to stop Docker container
        if status["method"] == "docker" and self.docker_client.is_available():
            result = self.docker_client.stop_container(CARTA_CONTAINER_NAME)
            return result

        # Services are running but not via Docker - can't stop them automatically
        return {
            "success": False,
            "message": "CARTA services are running but not managed by Docker. "
            "Please stop them manually.",
        }

    def restart_service(self) -> Dict[str, Any]:
        """
        Restart CARTA services.

        Returns:
            Dictionary with success status and message.
        """
        # Stop first
        stop_result = self.stop_service()
        if not stop_result["success"] and "not running" not in stop_result["message"]:
            return stop_result

        # Wait a moment
        time.sleep(2)

        # Start
        return self.start_service()


# Global instance
_carta_service_manager: Optional[CARTAServiceManager] = None


def get_carta_service_manager() -> CARTAServiceManager:
    """Get or create the global CARTA service manager instance."""
    global _carta_service_manager
    if _carta_service_manager is None:
        _carta_service_manager = CARTAServiceManager()
    return _carta_service_manager

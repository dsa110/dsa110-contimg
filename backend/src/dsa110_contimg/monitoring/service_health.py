"""
Service Health Checker - Monitors infrastructure dependencies.

This module provides utilities to:
1. Check Docker container health
2. Check systemd service status
3. Check external service connectivity
4. Aggregate overall system health
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service health status."""
    RUNNING = "running"
    STOPPED = "stopped"
    DEGRADED = "degraded"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealthResult:
    """Health check result for a single service."""
    
    name: str
    status: ServiceStatus
    message: str = ""
    response_time_ms: Optional[float] = None
    details: Dict = field(default_factory=dict)
    checked_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "checked_at": self.checked_at,
        }


@dataclass
class SystemHealthReport:
    """Aggregated system health report."""
    
    overall_status: ServiceStatus = ServiceStatus.UNKNOWN
    services: List[ServiceHealthResult] = field(default_factory=list)
    docker_available: bool = False
    systemd_available: bool = False
    checked_at: str = ""
    check_duration_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status.value,
            "services": [s.to_dict() for s in self.services],
            "docker_available": self.docker_available,
            "systemd_available": self.systemd_available,
            "checked_at": self.checked_at,
            "check_duration_ms": round(self.check_duration_ms, 2),
            "summary": {
                "total": len(self.services),
                "running": sum(1 for s in self.services if s.status == ServiceStatus.RUNNING),
                "stopped": sum(1 for s in self.services if s.status == ServiceStatus.STOPPED),
                "degraded": sum(1 for s in self.services if s.status == ServiceStatus.DEGRADED),
                "error": sum(1 for s in self.services if s.status == ServiceStatus.ERROR),
            }
        }


def check_docker_container(container_name: str) -> ServiceHealthResult:
    """Check health of a Docker container."""
    result = ServiceHealthResult(
        name=f"docker:{container_name}",
        status=ServiceStatus.UNKNOWN,
        checked_at=datetime.utcnow().isoformat() + "Z",
    )
    
    docker_cmd = shutil.which("docker")
    if not docker_cmd:
        result.status = ServiceStatus.UNKNOWN
        result.message = "Docker not installed"
        return result
    
    start = time.time()
    try:
        proc = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        result.response_time_ms = (time.time() - start) * 1000
        
        if proc.returncode != 0:
            result.status = ServiceStatus.STOPPED
            result.message = f"Container not found: {container_name}"
            return result
        
        state = proc.stdout.strip().lower()
        result.details["state"] = state
        
        if state == "running":
            result.status = ServiceStatus.RUNNING
            result.message = "Container running"
        elif state == "exited":
            result.status = ServiceStatus.STOPPED
            result.message = "Container exited"
        else:
            result.status = ServiceStatus.DEGRADED
            result.message = f"Container state: {state}"
            
    except subprocess.TimeoutExpired:
        result.status = ServiceStatus.ERROR
        result.message = "Docker command timed out"
    except Exception as e:
        result.status = ServiceStatus.ERROR
        result.message = str(e)
    
    return result


def check_systemd_service(service_name: str) -> ServiceHealthResult:
    """Check health of a systemd service."""
    result = ServiceHealthResult(
        name=f"systemd:{service_name}",
        status=ServiceStatus.UNKNOWN,
        checked_at=datetime.utcnow().isoformat() + "Z",
    )
    
    systemctl = shutil.which("systemctl")
    if not systemctl:
        result.status = ServiceStatus.UNKNOWN
        result.message = "systemctl not available"
        return result
    
    start = time.time()
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        result.response_time_ms = (time.time() - start) * 1000
        
        state = proc.stdout.strip().lower()
        result.details["active_state"] = state
        
        if state == "active":
            result.status = ServiceStatus.RUNNING
            result.message = "Service active"
        elif state == "inactive":
            result.status = ServiceStatus.STOPPED
            result.message = "Service inactive"
        elif state == "failed":
            result.status = ServiceStatus.ERROR
            result.message = "Service failed"
        else:
            result.status = ServiceStatus.DEGRADED
            result.message = f"Service state: {state}"
            
    except subprocess.TimeoutExpired:
        result.status = ServiceStatus.ERROR
        result.message = "systemctl command timed out"
    except Exception as e:
        result.status = ServiceStatus.ERROR
        result.message = str(e)
    
    return result


async def check_http_endpoint(
    name: str,
    url: str,
    timeout: float = 5.0,
    expected_status: int = 200,
) -> ServiceHealthResult:
    """Check health of an HTTP endpoint."""
    import httpx
    
    result = ServiceHealthResult(
        name=f"http:{name}",
        status=ServiceStatus.UNKNOWN,
        checked_at=datetime.utcnow().isoformat() + "Z",
    )
    
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            result.response_time_ms = (time.time() - start) * 1000
            result.details["status_code"] = response.status_code
            
            if response.status_code == expected_status:
                result.status = ServiceStatus.RUNNING
                result.message = f"HTTP {response.status_code}"
            elif response.status_code < 500:
                result.status = ServiceStatus.DEGRADED
                result.message = f"Unexpected status: {response.status_code}"
            else:
                result.status = ServiceStatus.ERROR
                result.message = f"Server error: {response.status_code}"
                
    except Exception as e:
        result.status = ServiceStatus.STOPPED
        result.message = str(e)
    
    return result


async def check_system_health(
    docker_containers: Optional[List[str]] = None,
    systemd_services: Optional[List[str]] = None,
    http_endpoints: Optional[Dict[str, str]] = None,
) -> SystemHealthReport:
    """Check health of all system services."""
    start = time.time()
    report = SystemHealthReport(
        checked_at=datetime.utcnow().isoformat() + "Z",
    )
    
    report.docker_available = shutil.which("docker") is not None
    report.systemd_available = shutil.which("systemctl") is not None
    
    if docker_containers:
        for container in docker_containers:
            result = check_docker_container(container)
            report.services.append(result)
    
    if systemd_services:
        for service in systemd_services:
            result = check_systemd_service(service)
            report.services.append(result)
    
    if http_endpoints:
        tasks = [
            check_http_endpoint(name, url)
            for name, url in http_endpoints.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, ServiceHealthResult):
                report.services.append(r)
    
    # Calculate overall status
    if not report.services:
        report.overall_status = ServiceStatus.UNKNOWN
    else:
        error_count = sum(1 for s in report.services if s.status == ServiceStatus.ERROR)
        stopped_count = sum(1 for s in report.services if s.status == ServiceStatus.STOPPED)
        degraded_count = sum(1 for s in report.services if s.status == ServiceStatus.DEGRADED)
        
        if error_count > 0:
            report.overall_status = ServiceStatus.ERROR
        elif stopped_count > 0 or degraded_count > 0:
            report.overall_status = ServiceStatus.DEGRADED
        else:
            report.overall_status = ServiceStatus.RUNNING
    
    report.check_duration_ms = (time.time() - start) * 1000
    return report


# Default service configuration for DSA-110 pipeline
DEFAULT_DOCKER_CONTAINERS = [
    "ragflow-ragflow-1",
    "ragflow-elasticsearch01-1", 
    "ragflow-redis-1",
]

DEFAULT_SYSTEMD_SERVICES = [
    "contimg-api",
    "contimg-stream",
]

DEFAULT_HTTP_ENDPOINTS = {
    "api": "http://localhost:8000/api/status",
}

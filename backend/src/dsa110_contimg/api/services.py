"""
Service health checking module for the DSA-110 Pipeline API.

Provides server-side health checks for all dependent services,
bypassing browser CORS/CSP restrictions.
"""

from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx


class ServiceStatus(str, Enum):
    """Service health status."""
    RUNNING = "running"
    STOPPED = "stopped"
    DEGRADED = "degraded"
    ERROR = "error"
    CHECKING = "checking"


@dataclass
class ServiceDefinition:
    """Definition of a service to monitor."""
    name: str
    port: int
    description: str
    health_endpoint: Optional[str] = None
    protocol: str = "http"  # http, tcp, redis


@dataclass
class ServiceHealthResult:
    """Result of a service health check."""
    name: str
    port: int
    description: str
    status: ServiceStatus
    response_time_ms: float
    last_checked: datetime
    error: Optional[str] = None
    details: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "port": self.port,
            "description": self.description,
            "status": self.status.value,
            "responseTime": round(self.response_time_ms, 2),
            "lastChecked": self.last_checked.isoformat() + "Z",
            "error": self.error,
            "details": self.details,
        }


# Define all services the frontend monitors
MONITORED_SERVICES: list[ServiceDefinition] = [
    ServiceDefinition(
        name="Vite Dev Server",
        port=3000,
        description="Frontend development server with HMR",
        health_endpoint="/",
        protocol="http",
    ),
    ServiceDefinition(
        name="Grafana",
        port=3030,
        description="Metrics visualization dashboards",
        health_endpoint="/api/health",
        protocol="http",
    ),
    ServiceDefinition(
        name="Redis",
        port=6379,
        description="API response caching",
        protocol="redis",
    ),
    ServiceDefinition(
        name="FastAPI Backend",
        port=8000,
        description="REST API for pipeline data",
        health_endpoint="/api/health",
        protocol="http",
    ),
    ServiceDefinition(
        name="MkDocs",
        port=8001,
        description="Documentation server (dev only)",
        health_endpoint="/",
        protocol="http",
    ),
    ServiceDefinition(
        name="Prometheus",
        port=9090,
        description="Metrics collection and storage",
        health_endpoint="/-/healthy",
        protocol="http",
    ),
]


async def check_http_service(
    service: ServiceDefinition,
    timeout: float = 3.0,
) -> ServiceHealthResult:
    """Check an HTTP service health."""
    start_time = time.perf_counter()
    url = f"http://127.0.0.1:{service.port}{service.health_endpoint or '/'}"
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            # Most services return 200 for healthy
            # Grafana returns 200 with JSON
            # Prometheus /-/healthy returns 200 with "Prometheus Server is Healthy.\n"
            status = ServiceStatus.RUNNING if response.status_code < 400 else ServiceStatus.DEGRADED
            
            details = None
            if service.port == 8000:
                # Parse FastAPI health response
                try:
                    details = response.json()
                    if details.get("status") == "degraded":
                        status = ServiceStatus.DEGRADED
                except Exception:
                    pass
            
            return ServiceHealthResult(
                name=service.name,
                port=service.port,
                description=service.description,
                status=status,
                response_time_ms=elapsed,
                last_checked=datetime.utcnow(),
                details=details,
            )
            
    except httpx.ConnectError:
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.STOPPED,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error="Connection refused",
        )
    except httpx.TimeoutException:
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.ERROR,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error="Connection timeout",
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.ERROR,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error=str(e)[:100],
        )


async def check_redis_service(
    service: ServiceDefinition,
    timeout: float = 3.0,
) -> ServiceHealthResult:
    """Check Redis service using PING command."""
    start_time = time.perf_counter()
    
    try:
        # Use raw socket for Redis PING/PONG
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", service.port),
            timeout=timeout,
        )
        
        # Send PING command
        writer.write(b"PING\r\n")
        await writer.drain()
        
        # Read response
        response = await asyncio.wait_for(reader.readline(), timeout=timeout)
        elapsed = (time.perf_counter() - start_time) * 1000
        
        writer.close()
        await writer.wait_closed()
        
        # Redis responds with +PONG\r\n
        if b"PONG" in response:
            return ServiceHealthResult(
                name=service.name,
                port=service.port,
                description=service.description,
                status=ServiceStatus.RUNNING,
                response_time_ms=elapsed,
                last_checked=datetime.utcnow(),
                details={"response": "PONG"},
            )
        else:
            return ServiceHealthResult(
                name=service.name,
                port=service.port,
                description=service.description,
                status=ServiceStatus.DEGRADED,
                response_time_ms=elapsed,
                last_checked=datetime.utcnow(),
                error=f"Unexpected response: {response.decode()[:50]}",
            )
            
    except asyncio.TimeoutError:
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.ERROR,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error="Connection timeout",
        )
    except (ConnectionRefusedError, OSError):
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.STOPPED,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error="Connection refused",
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.ERROR,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error=str(e)[:100],
        )


async def check_tcp_service(
    service: ServiceDefinition,
    timeout: float = 3.0,
) -> ServiceHealthResult:
    """Check a TCP service by attempting to connect."""
    start_time = time.perf_counter()
    
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", service.port),
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - start_time) * 1000
        
        writer.close()
        await writer.wait_closed()
        
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.RUNNING,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
        )
        
    except asyncio.TimeoutError:
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.ERROR,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error="Connection timeout",
        )
    except (ConnectionRefusedError, OSError):
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.STOPPED,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error="Connection refused",
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.ERROR,
            response_time_ms=elapsed,
            last_checked=datetime.utcnow(),
            error=str(e)[:100],
        )


async def check_service(service: ServiceDefinition) -> ServiceHealthResult:
    """Check a service health based on its protocol."""
    if service.protocol == "http":
        return await check_http_service(service)
    elif service.protocol == "redis":
        return await check_redis_service(service)
    elif service.protocol == "tcp":
        return await check_tcp_service(service)
    else:
        return ServiceHealthResult(
            name=service.name,
            port=service.port,
            description=service.description,
            status=ServiceStatus.ERROR,
            response_time_ms=0,
            last_checked=datetime.utcnow(),
            error=f"Unknown protocol: {service.protocol}",
        )


async def check_all_services() -> list[ServiceHealthResult]:
    """Check all monitored services concurrently."""
    tasks = [check_service(svc) for svc in MONITORED_SERVICES]
    results = await asyncio.gather(*tasks)
    return list(results)

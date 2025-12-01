"""
Tests for services_monitor module.

Tests service health checking functionality with mocked network connections.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from dsa110_contimg.api.services_monitor import (
    MONITORED_SERVICES,
    ServiceDefinition,
    ServiceHealthResult,
    ServiceStatus,
    check_all_services,
    check_http_service,
    check_redis_service,
    check_service,
    check_tcp_service,
)


# ============================================================================
# ServiceStatus Enum Tests
# ============================================================================


class TestServiceStatus:
    """Tests for ServiceStatus enum."""

    def test_status_values(self):
        """All expected status values should exist."""
        assert ServiceStatus.RUNNING.value == "running"
        assert ServiceStatus.STOPPED.value == "stopped"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.ERROR.value == "error"
        assert ServiceStatus.CHECKING.value == "checking"

    def test_status_is_string_enum(self):
        """ServiceStatus should be a string enum."""
        assert isinstance(ServiceStatus.RUNNING, str)
        assert ServiceStatus.RUNNING == "running"


# ============================================================================
# ServiceDefinition Tests
# ============================================================================


class TestServiceDefinition:
    """Tests for ServiceDefinition dataclass."""

    def test_minimal_definition(self):
        """ServiceDefinition should work with required fields only."""
        svc = ServiceDefinition(
            name="Test Service",
            port=8080,
            description="A test service",
        )
        assert svc.name == "Test Service"
        assert svc.port == 8080
        assert svc.description == "A test service"
        assert svc.health_endpoint is None
        assert svc.protocol == "http"

    def test_full_definition(self):
        """ServiceDefinition should accept all fields."""
        svc = ServiceDefinition(
            name="Redis",
            port=6379,
            description="Cache service",
            health_endpoint="/health",
            protocol="redis",
        )
        assert svc.name == "Redis"
        assert svc.port == 6379
        assert svc.health_endpoint == "/health"
        assert svc.protocol == "redis"


# ============================================================================
# ServiceHealthResult Tests
# ============================================================================


class TestServiceHealthResult:
    """Tests for ServiceHealthResult dataclass."""

    def test_minimal_result(self):
        """ServiceHealthResult should work with required fields."""
        result = ServiceHealthResult(
            name="Test",
            port=8080,
            description="Test service",
            status=ServiceStatus.RUNNING,
            response_time_ms=15.5,
            last_checked=datetime(2024, 1, 15, 10, 30, 0),
        )
        assert result.error is None
        assert result.details is None

    def test_to_dict_format(self):
        """to_dict should return properly formatted dictionary."""
        result = ServiceHealthResult(
            name="FastAPI",
            port=8000,
            description="API server",
            status=ServiceStatus.RUNNING,
            response_time_ms=12.345,
            last_checked=datetime(2024, 1, 15, 10, 30, 0),
            details={"version": "1.0"},
        )
        d = result.to_dict()
        
        assert d["name"] == "FastAPI"
        assert d["port"] == 8000
        assert d["description"] == "API server"
        assert d["status"] == "running"
        assert d["responseTime"] == 12.35  # Rounded to 2 decimals
        assert d["lastChecked"] == "2024-01-15T10:30:00Z"
        assert d["error"] is None
        assert d["details"] == {"version": "1.0"}

    def test_to_dict_with_error(self):
        """to_dict should include error when present."""
        result = ServiceHealthResult(
            name="Redis",
            port=6379,
            description="Cache",
            status=ServiceStatus.STOPPED,
            response_time_ms=0.5,
            last_checked=datetime(2024, 1, 15, 10, 30, 0),
            error="Connection refused",
        )
        d = result.to_dict()
        
        assert d["status"] == "stopped"
        assert d["error"] == "Connection refused"


# ============================================================================
# MONITORED_SERVICES Configuration Tests
# ============================================================================


class TestMonitoredServices:
    """Tests for the MONITORED_SERVICES configuration."""

    def test_services_defined(self):
        """MONITORED_SERVICES should contain expected services."""
        service_names = [s.name for s in MONITORED_SERVICES]
        
        assert "Vite Dev Server" in service_names
        assert "Grafana" in service_names
        assert "Redis" in service_names
        assert "FastAPI Backend" in service_names
        assert "MkDocs" in service_names
        assert "Prometheus" in service_names

    def test_service_ports(self):
        """Services should have expected ports."""
        port_map = {s.name: s.port for s in MONITORED_SERVICES}
        
        assert port_map["Vite Dev Server"] == 3000
        assert port_map["Grafana"] == 3030
        assert port_map["Redis"] == 6379
        assert port_map["FastAPI Backend"] == 8000
        assert port_map["MkDocs"] == 8001
        assert port_map["Prometheus"] == 9090

    def test_redis_uses_redis_protocol(self):
        """Redis should use redis protocol."""
        redis = next(s for s in MONITORED_SERVICES if s.name == "Redis")
        assert redis.protocol == "redis"

    def test_http_services_have_endpoints(self):
        """HTTP services should have health endpoints."""
        for svc in MONITORED_SERVICES:
            if svc.protocol == "http":
                assert svc.health_endpoint is not None


# ============================================================================
# check_http_service Tests
# ============================================================================


class TestCheckHttpService:
    """Tests for check_http_service function."""

    @pytest.fixture
    def http_service(self):
        """Create a test HTTP service definition."""
        return ServiceDefinition(
            name="Test HTTP",
            port=8080,
            description="Test HTTP service",
            health_endpoint="/health",
            protocol="http",
        )

    @pytest.mark.asyncio
    async def test_healthy_service(self, http_service):
        """Healthy HTTP service should return RUNNING status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(http_service)
            
            assert result.status == ServiceStatus.RUNNING
            assert result.name == "Test HTTP"
            assert result.port == 8080
            assert result.error is None
            assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_degraded_service_status_code(self, http_service):
        """Service returning 4xx/5xx should be DEGRADED."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")
        
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(http_service)
            
            assert result.status == ServiceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_connection_refused(self, http_service):
        """Connection refused should return STOPPED status."""
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("Connection refused")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(http_service)
            
            assert result.status == ServiceStatus.STOPPED
            assert result.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_timeout(self, http_service):
        """Timeout should return ERROR status."""
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.TimeoutException("Timed out")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(http_service)
            
            assert result.status == ServiceStatus.ERROR
            assert result.error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_request_error(self, http_service):
        """Generic request error should return ERROR status."""
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.RequestError("Network error")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(http_service)
            
            assert result.status == ServiceStatus.ERROR
            assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_fastapi_health_details(self):
        """FastAPI backend should parse health response details."""
        fastapi_service = ServiceDefinition(
            name="FastAPI Backend",
            port=8000,
            description="API",
            health_endpoint="/api/health",
            protocol="http",
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "version": "1.0"}
        
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(fastapi_service)
            
            assert result.status == ServiceStatus.RUNNING
            assert result.details == {"status": "healthy", "version": "1.0"}

    @pytest.mark.asyncio
    async def test_fastapi_degraded_from_response(self):
        """FastAPI returning degraded status should be DEGRADED."""
        fastapi_service = ServiceDefinition(
            name="FastAPI Backend",
            port=8000,
            description="API",
            health_endpoint="/api/health",
            protocol="http",
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "degraded"}
        
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(fastapi_service)
            
            assert result.status == ServiceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_default_health_endpoint(self):
        """Service without health endpoint should use root path."""
        service = ServiceDefinition(
            name="Test",
            port=8080,
            description="Test",
            health_endpoint=None,
            protocol="http",
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(service)
            
            # Verify the URL used
            mock_instance.get.assert_called_once()
            url = mock_instance.get.call_args[0][0]
            assert url == "http://127.0.0.1:8080/"


# ============================================================================
# check_redis_service Tests
# ============================================================================


class TestCheckRedisService:
    """Tests for check_redis_service function."""

    @pytest.fixture
    def redis_service(self):
        """Create a test Redis service definition."""
        return ServiceDefinition(
            name="Redis",
            port=6379,
            description="Cache service",
            protocol="redis",
        )

    @pytest.mark.asyncio
    async def test_healthy_redis(self, redis_service):
        """Redis responding with PONG should be RUNNING."""
        mock_reader = AsyncMock()
        mock_reader.readline.return_value = b"+PONG\r\n"
        
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        
        async def mock_open_connection(*args, **kwargs):
            return (mock_reader, mock_writer)
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_redis_service(redis_service)
            
            assert result.status == ServiceStatus.RUNNING
            assert result.details == {"response": "PONG"}
            assert result.error is None

    @pytest.mark.asyncio
    async def test_redis_unexpected_response(self, redis_service):
        """Redis with unexpected response should be DEGRADED."""
        mock_reader = AsyncMock()
        mock_reader.readline.return_value = b"-ERR unknown\r\n"
        
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        
        async def mock_open_connection(*args, **kwargs):
            return (mock_reader, mock_writer)
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_redis_service(redis_service)
            
            assert result.status == ServiceStatus.DEGRADED
            assert "Unexpected response" in result.error

    @pytest.mark.asyncio
    async def test_redis_timeout(self, redis_service):
        """Redis timeout should return ERROR status."""
        async def mock_open_connection(*args, **kwargs):
            await asyncio.sleep(10)  # Will be interrupted by timeout
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_redis_service(redis_service, timeout=0.001)
            
            assert result.status == ServiceStatus.ERROR
            assert result.error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_redis_connection_refused(self, redis_service):
        """Redis connection refused should return STOPPED status."""
        async def mock_open_connection(*args, **kwargs):
            raise ConnectionRefusedError()
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_redis_service(redis_service)
            
            assert result.status == ServiceStatus.STOPPED
            assert result.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_redis_os_error(self, redis_service):
        """Redis OSError should return STOPPED status."""
        async def mock_open_connection(*args, **kwargs):
            raise OSError("Network unreachable")
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_redis_service(redis_service)
            
            assert result.status == ServiceStatus.STOPPED
            assert result.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_redis_connection_error(self, redis_service):
        """Redis ConnectionError should return ERROR status."""
        async def mock_open_connection(*args, **kwargs):
            raise ConnectionError("Lost connection")
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_redis_service(redis_service)
            
            assert result.status == ServiceStatus.ERROR
            assert "Lost connection" in result.error

    @pytest.mark.asyncio
    async def test_redis_unicode_error(self, redis_service):
        """Redis UnicodeDecodeError should return ERROR status."""
        async def mock_open_connection(*args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_redis_service(redis_service)
            
            assert result.status == ServiceStatus.ERROR


# ============================================================================
# check_tcp_service Tests
# ============================================================================


class TestCheckTcpService:
    """Tests for check_tcp_service function."""

    @pytest.fixture
    def tcp_service(self):
        """Create a test TCP service definition."""
        return ServiceDefinition(
            name="Custom TCP",
            port=9000,
            description="Custom TCP service",
            protocol="tcp",
        )

    @pytest.mark.asyncio
    async def test_healthy_tcp(self, tcp_service):
        """TCP service accepting connections should be RUNNING."""
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        
        async def mock_open_connection(*args, **kwargs):
            return (mock_reader, mock_writer)
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_tcp_service(tcp_service)
            
            assert result.status == ServiceStatus.RUNNING
            assert result.error is None
            mock_writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_tcp_timeout(self, tcp_service):
        """TCP timeout should return ERROR status."""
        async def mock_open_connection(*args, **kwargs):
            await asyncio.sleep(10)  # Will be interrupted by timeout
        
        with patch("asyncio.open_connection", mock_open_connection):
            # Use a very short timeout to trigger asyncio.TimeoutError
            result = await check_tcp_service(tcp_service, timeout=0.001)
            
            assert result.status == ServiceStatus.ERROR
            assert result.error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_tcp_connection_refused(self, tcp_service):
        """TCP connection refused should return STOPPED status."""
        async def mock_open_connection(*args, **kwargs):
            raise ConnectionRefusedError()
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_tcp_service(tcp_service)
            
            assert result.status == ServiceStatus.STOPPED
            assert result.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_tcp_os_error(self, tcp_service):
        """TCP OSError should return STOPPED status."""
        async def mock_open_connection(*args, **kwargs):
            raise OSError("Network down")
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_tcp_service(tcp_service)
            
            assert result.status == ServiceStatus.STOPPED
            assert result.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_tcp_connection_error(self, tcp_service):
        """TCP ConnectionError should return ERROR status."""
        async def mock_open_connection(*args, **kwargs):
            raise ConnectionResetError("Reset by peer")
        
        with patch("asyncio.open_connection", mock_open_connection):
            result = await check_tcp_service(tcp_service)
            
            assert result.status == ServiceStatus.ERROR
            assert "Reset by peer" in result.error


# ============================================================================
# check_service Dispatcher Tests
# ============================================================================


class TestCheckService:
    """Tests for check_service dispatcher function."""

    @pytest.mark.asyncio
    async def test_dispatch_http(self):
        """HTTP protocol should use check_http_service."""
        service = ServiceDefinition(
            name="HTTP Test",
            port=8080,
            description="HTTP",
            health_endpoint="/health",
            protocol="http",
        )
        
        with patch("dsa110_contimg.api.services_monitor.check_http_service") as mock_check:
            mock_check.return_value = ServiceHealthResult(
                name=service.name,
                port=service.port,
                description=service.description,
                status=ServiceStatus.RUNNING,
                response_time_ms=10.0,
                last_checked=datetime.utcnow(),
            )
            
            result = await check_service(service)
            
            mock_check.assert_called_once_with(service)
            assert result.status == ServiceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_dispatch_redis(self):
        """Redis protocol should use check_redis_service."""
        service = ServiceDefinition(
            name="Redis",
            port=6379,
            description="Cache",
            protocol="redis",
        )
        
        with patch("dsa110_contimg.api.services_monitor.check_redis_service") as mock_check:
            mock_check.return_value = ServiceHealthResult(
                name=service.name,
                port=service.port,
                description=service.description,
                status=ServiceStatus.RUNNING,
                response_time_ms=5.0,
                last_checked=datetime.utcnow(),
            )
            
            result = await check_service(service)
            
            mock_check.assert_called_once_with(service)
            assert result.status == ServiceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_dispatch_tcp(self):
        """TCP protocol should use check_tcp_service."""
        service = ServiceDefinition(
            name="TCP Service",
            port=9000,
            description="TCP",
            protocol="tcp",
        )
        
        with patch("dsa110_contimg.api.services_monitor.check_tcp_service") as mock_check:
            mock_check.return_value = ServiceHealthResult(
                name=service.name,
                port=service.port,
                description=service.description,
                status=ServiceStatus.RUNNING,
                response_time_ms=2.0,
                last_checked=datetime.utcnow(),
            )
            
            result = await check_service(service)
            
            mock_check.assert_called_once_with(service)
            assert result.status == ServiceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_unknown_protocol(self):
        """Unknown protocol should return ERROR status."""
        service = ServiceDefinition(
            name="Unknown",
            port=9999,
            description="Unknown protocol",
            protocol="websocket",  # Not supported
        )
        
        result = await check_service(service)
        
        assert result.status == ServiceStatus.ERROR
        assert "Unknown protocol: websocket" in result.error


# ============================================================================
# check_all_services Tests
# ============================================================================


class TestCheckAllServices:
    """Tests for check_all_services function."""

    @pytest.mark.asyncio
    async def test_checks_all_services(self):
        """Should check all monitored services concurrently."""
        with patch("dsa110_contimg.api.services_monitor.check_service") as mock_check:
            mock_check.return_value = ServiceHealthResult(
                name="Test",
                port=8000,
                description="Test",
                status=ServiceStatus.RUNNING,
                response_time_ms=10.0,
                last_checked=datetime.utcnow(),
            )
            
            results = await check_all_services()
            
            # Should call check_service for each monitored service
            assert mock_check.call_count == len(MONITORED_SERVICES)
            assert len(results) == len(MONITORED_SERVICES)

    @pytest.mark.asyncio
    async def test_returns_list(self):
        """Should return a list of results."""
        with patch("dsa110_contimg.api.services_monitor.check_service") as mock_check:
            mock_check.return_value = ServiceHealthResult(
                name="Test",
                port=8000,
                description="Test",
                status=ServiceStatus.RUNNING,
                response_time_ms=10.0,
                last_checked=datetime.utcnow(),
            )
            
            results = await check_all_services()
            
            assert isinstance(results, list)
            for result in results:
                assert isinstance(result, ServiceHealthResult)

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Should execute checks concurrently."""
        call_times = []
        
        async def mock_check(service):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Small delay
            return ServiceHealthResult(
                name=service.name,
                port=service.port,
                description=service.description,
                status=ServiceStatus.RUNNING,
                response_time_ms=10.0,
                last_checked=datetime.utcnow(),
            )
        
        with patch("dsa110_contimg.api.services_monitor.check_service", mock_check):
            await check_all_services()
            
            # All checks should start at approximately the same time
            # (within 0.01 second tolerance)
            if len(call_times) > 1:
                time_spread = max(call_times) - min(call_times)
                assert time_spread < 0.05  # All started within 50ms


# ============================================================================
# Error Message Truncation Tests
# ============================================================================


class TestErrorTruncation:
    """Tests for error message truncation."""

    @pytest.mark.asyncio
    async def test_long_error_truncated(self):
        """Long error messages should be truncated to 100 characters."""
        service = ServiceDefinition(
            name="Test",
            port=8080,
            description="Test",
            protocol="http",
        )
        
        long_error = "x" * 200
        
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.RequestError(long_error)
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(service)
            
            assert len(result.error) <= 100


# ============================================================================
# Response Time Tracking Tests
# ============================================================================


class TestResponseTime:
    """Tests for response time measurement."""

    @pytest.mark.asyncio
    async def test_response_time_measured(self):
        """Response time should be measured in milliseconds."""
        service = ServiceDefinition(
            name="Test",
            port=8080,
            description="Test",
            protocol="http",
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        
        with patch("dsa110_contimg.api.services_monitor.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await check_http_service(service)
            
            # Response time should be a positive number
            assert result.response_time_ms >= 0
            assert isinstance(result.response_time_ms, float)

    @pytest.mark.asyncio
    async def test_error_includes_response_time(self):
        """Even failed checks should include response time."""
        service = ServiceDefinition(
            name="Test",
            port=8080,
            description="Test",
            protocol="tcp",
        )
        
        with patch("asyncio.wait_for", side_effect=ConnectionRefusedError()):
            result = await check_tcp_service(service)
            
            assert result.response_time_ms >= 0

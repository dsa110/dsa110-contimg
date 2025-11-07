# Docker Client Reference

## Overview

The Docker Client (`docker_client.py`) provides a clean abstraction layer for Docker container operations. It automatically uses the Docker Python SDK when available, with graceful fallback to subprocess calls.

## Architecture

### Design Principles

1. **Automatic Detection**: Detects Docker SDK availability and Docker socket access
2. **Graceful Fallback**: Falls back to subprocess if SDK unavailable
3. **Unified Interface**: Same API regardless of underlying implementation
4. **Error Handling**: Clear error messages and exception handling

### Components

```
DockerClient
├── SDK Mode (docker.from_env())
│   ├── Container operations via SDK
│   ├── Stats via container.stats()
│   └── Info via container.attrs
└── Fallback Mode (subprocess)
    ├── docker ps/inspect/start/stop
    ├── docker stats for metrics
    └── docker inspect for info
```

## API Reference

### Initialization

```python
from dsa110_contimg.api.docker_client import get_docker_client

client = get_docker_client()
```

The `get_docker_client()` function returns a singleton instance that is reused across calls.

### Methods

#### `is_available() -> bool`

Check if Docker client is available and connected.

```python
if client.is_available():
    print("Docker SDK connected")
else:
    print("Using subprocess fallback")
```

#### `is_container_running(container_name: str) -> bool`

Check if a container is running.

```python
if client.is_container_running("contimg-stream"):
    print("Streaming service is running")
```

#### `start_container(container_name: str) -> Dict[str, Any]`

Start a container.

```python
result = client.start_container("contimg-stream")
if result["success"]:
    print(f"Started: {result['message']}")
else:
    print(f"Failed: {result['message']}")
```

#### `stop_container(container_name: str, timeout: int = 10) -> Dict[str, Any]`

Stop a container with optional timeout.

```python
result = client.stop_container("contimg-stream", timeout=30)
```

#### `restart_container(container_name: str, timeout: int = 10) -> Dict[str, Any]`

Restart a container.

```python
result = client.restart_container("contimg-stream")
```

#### `get_container_stats(container_name: str) -> Optional[Dict[str, Any]]`

Get container resource statistics.

```python
stats = client.get_container_stats("contimg-stream")
if stats:
    print(f"CPU: {stats['cpu_percent']}%")
    print(f"Memory: {stats['memory_mb']} MB")
```

**Response Format:**

```python
{
    "cpu_percent": 15.2,      # CPU usage percentage
    "memory_usage": 536870912,  # Memory usage in bytes
    "memory_limit": 1073741824,  # Memory limit in bytes
    "memory_percent": 50.0,    # Memory usage percentage
    "memory_mb": 512.0         # Memory usage in MB (fallback mode)
}
```

#### `get_container_info(container_name: str) -> Optional[Dict[str, Any]]`

Get container information.

```python
info = client.get_container_info("contimg-stream")
if info:
    print(f"Status: {info['status']}")
    print(f"Started: {info['started_at']}")
    print(f"PID: {info['pid']}")
```

**Response Format:**

```python
{
    "id": "abc123...",
    "name": "contimg-stream",
    "status": "running",
    "started_at": "2025-11-06T14:30:00Z",
    "pid": 12345
}
```

## Usage Examples

### Basic Container Control

```python
from dsa110_contimg.api.docker_client import get_docker_client

client = get_docker_client()

# Check if container is running
if not client.is_container_running("contimg-stream"):
    # Start it
    result = client.start_container("contimg-stream")
    print(result["message"])

# Get stats
stats = client.get_container_stats("contimg-stream")
if stats:
    print(f"CPU: {stats.get('cpu_percent', 0):.1f}%")
    print(f"Memory: {stats.get('memory_mb', 0):.1f} MB")
```

### Advanced Container Management

```python
from dsa110_contimg.api.docker_client import get_docker_client
import time
from typing import Optional, Dict, Any

class ContainerManager:
    """Advanced container management with health monitoring."""
    
    def __init__(self, container_name: str):
        self.container_name = container_name
        self.client = get_docker_client()
    
    def ensure_running(self, max_retries: int = 3) -> bool:
        """Ensure container is running, start if needed."""
        for attempt in range(max_retries):
            if self.client.is_container_running(self.container_name):
                return True
            
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff
            
            result = self.client.start_container(self.container_name)
            if result["success"]:
                # Wait a moment for container to fully start
                time.sleep(2)
                if self.client.is_container_running(self.container_name):
                    return True
        
        return False
    
    def graceful_restart(self, timeout: int = 30) -> bool:
        """Restart container gracefully."""
        if not self.client.is_container_running(self.container_name):
            return self.ensure_running()
        
        result = self.client.restart_container(self.container_name, timeout=timeout)
        return result["success"]
    
    def get_resource_usage(self) -> Optional[Dict[str, Any]]:
        """Get current resource usage."""
        if not self.client.is_container_running(self.container_name):
            return None
        
        stats = self.client.get_container_stats(self.container_name)
        info = self.client.get_container_info(self.container_name)
        
        if stats and info:
            return {
                "cpu_percent": stats.get("cpu_percent"),
                "memory_mb": stats.get("memory_mb"),
                "memory_percent": stats.get("memory_percent"),
                "status": info.get("status"),
                "uptime": self._calculate_uptime(info.get("started_at")),
            }
        return None
    
    def monitor(self, interval: int = 10, duration: int = 300):
        """Monitor container for specified duration."""
        start_time = time.time()
        while time.time() - start_time < duration:
            usage = self.get_resource_usage()
            if usage:
                print(f"CPU: {usage['cpu_percent']:.1f}%, "
                      f"Memory: {usage['memory_mb']:.1f} MB, "
                      f"Status: {usage['status']}")
            else:
                print("Container not running")
            time.sleep(interval)
    
    @staticmethod
    def _calculate_uptime(started_at: Optional[str]) -> Optional[float]:
        """Calculate uptime from start timestamp."""
        if not started_at:
            return None
        from datetime import datetime
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            return (datetime.now() - start.replace(tzinfo=None)).total_seconds()
        except Exception:
            return None

# Usage
manager = ContainerManager("contimg-stream")
if manager.ensure_running():
    manager.monitor(interval=5, duration=60)
```

### Error Handling and Retry Logic

```python
from dsa110_contimg.api.docker_client import get_docker_client
import time
import logging
from typing import Callable, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_on_failure(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Any:
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = func()
            if isinstance(result, dict) and result.get("success", True):
                return result
            elif not isinstance(result, dict):
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = delay * (backoff ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    raise RuntimeError(f"Function {func.__name__} failed after {max_retries} attempts")

# Usage with retry
client = get_docker_client()

# Start container with retry
try:
    result = retry_on_failure(
        lambda: client.start_container("contimg-stream"),
        max_retries=3,
        delay=2.0
    )
    print(f"Success: {result['message']}")
except Exception as e:
    logger.error(f"Failed to start container: {e}")
```

### Integration with Streaming Service

```python
from dsa110_contimg.api.docker_client import get_docker_client
from dsa110_contimg.api.streaming_service import StreamingServiceManager
import time

class StreamingServiceMonitor:
    """Monitor streaming service using both Docker client and service manager."""
    
    def __init__(self):
        self.docker_client = get_docker_client()
        self.service_manager = StreamingServiceManager()
        self.container_name = "contimg-stream"
    
    def get_comprehensive_status(self) -> dict:
        """Get status from both Docker and service manager."""
        status = self.service_manager.get_status()
        docker_info = self.docker_client.get_container_info(self.container_name)
        docker_stats = self.docker_client.get_container_stats(self.container_name)
        
        result = {
            "service_running": status.running,
            "docker_running": docker_info.get("status") == "running" if docker_info else False,
            "pid": status.pid or docker_info.get("pid") if docker_info else None,
        }
        
        # Prefer Docker stats if available (more accurate)
        if docker_stats:
            result["cpu_percent"] = docker_stats.get("cpu_percent")
            result["memory_mb"] = docker_stats.get("memory_mb")
        else:
            result["cpu_percent"] = status.cpu_percent
            result["memory_mb"] = status.memory_mb
        
        # Check for inconsistencies
        if result["service_running"] != result["docker_running"]:
            result["warning"] = "Status mismatch between service manager and Docker"
        
        return result
    
    def health_check(self) -> tuple[bool, str]:
        """Perform comprehensive health check."""
        status = self.get_comprehensive_status()
        
        if not status["service_running"]:
            return False, "Service is not running"
        
        if not status["docker_running"]:
            return False, "Docker container is not running"
        
        if status.get("warning"):
            return False, status["warning"]
        
        # Check resource usage
        cpu = status.get("cpu_percent", 0)
        if cpu and cpu > 95:
            return False, f"CPU usage too high: {cpu:.1f}%"
        
        memory = status.get("memory_mb", 0)
        if memory and memory > 8192:  # 8GB threshold
            return False, f"Memory usage too high: {memory:.1f} MB"
        
        return True, "Service is healthy"

# Usage
monitor = StreamingServiceMonitor()
healthy, message = monitor.health_check()
print(f"Health: {healthy}, Message: {message}")

status = monitor.get_comprehensive_status()
print(f"CPU: {status.get('cpu_percent', 0):.1f}%")
print(f"Memory: {status.get('memory_mb', 0):.1f} MB")
```

### Testing Examples

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from dsa110_contimg.api.docker_client import DockerClient, get_docker_client

class TestDockerClient:
    """Test suite for Docker client."""
    
    @pytest.fixture
    def mock_docker_client(self):
        """Create mock Docker client."""
        client = Mock(spec=DockerClient)
        return client
    
    def test_is_container_running_true(self):
        """Test container running check when running."""
        client = get_docker_client()
        with patch.object(client, '_sdk_available', True):
            with patch.object(client, '_client') as mock_client:
                container = Mock()
                container.status = "running"
                mock_client.containers.get.return_value = container
                
                assert client.is_container_running("contimg-stream") is True
    
    def test_is_container_running_false(self):
        """Test container running check when stopped."""
        client = get_docker_client()
        with patch.object(client, '_sdk_available', True):
            with patch.object(client, '_client') as mock_client:
                container = Mock()
                container.status = "stopped"
                mock_client.containers.get.return_value = container
                
                assert client.is_container_running("contimg-stream") is False
    
    def test_start_container_success(self):
        """Test successful container start."""
        client = get_docker_client()
        with patch.object(client, '_sdk_available', True):
            with patch.object(client, '_client') as mock_client:
                container = Mock()
                mock_client.containers.get.return_value = container
                
                result = client.start_container("contimg-stream")
                assert result["success"] is True
                container.start.assert_called_once()
    
    def test_start_container_not_found(self):
        """Test starting non-existent container."""
        client = get_docker_client()
        with patch.object(client, '_sdk_available', True):
            with patch.object(client, '_client') as mock_client:
                import docker.errors
                mock_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
                
                result = client.start_container("contimg-stream")
                assert result["success"] is False
                assert "not found" in result["message"].lower()
    
    def test_get_container_stats(self):
        """Test getting container statistics."""
        client = get_docker_client()
        with patch.object(client, '_sdk_available', True):
            with patch.object(client, '_client') as mock_client:
                container = Mock()
                container.stats.return_value = {
                    "cpu_stats": {
                        "cpu_usage": {"total_usage": 1000000000},
                        "system_cpu_usage": 2000000000,
                        "cpu_usage": {"percpu_usage": [1, 2, 3, 4]},
                    },
                    "precpu_stats": {
                        "cpu_usage": {"total_usage": 500000000},
                        "system_cpu_usage": 1000000000,
                    },
                    "memory_stats": {
                        "usage": 536870912,  # 512 MB
                        "limit": 1073741824,  # 1 GB
                    },
                }
                mock_client.containers.get.return_value = container
                
                stats = client.get_container_stats("contimg-stream")
                assert stats is not None
                assert "cpu_percent" in stats
                assert "memory_percent" in stats
                assert stats["memory_percent"] == 50.0  # 512MB / 1GB
```

### Monitoring Loop with Error Recovery

```python
import time
import logging
from dsa110_contimg.api.docker_client import get_docker_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitor_with_recovery(container_name: str, interval: int = 10):
    """Monitor container and auto-recover on failure."""
    client = get_docker_client()
    consecutive_failures = 0
    max_failures = 3
    
    while True:
        try:
            if not client.is_container_running(container_name):
                consecutive_failures += 1
                logger.warning(f"Container not running (failure {consecutive_failures}/{max_failures})")
                
                if consecutive_failures >= max_failures:
                    logger.info("Attempting to restart container...")
                    result = client.start_container(container_name)
                    if result["success"]:
                        logger.info("Container restarted successfully")
                        consecutive_failures = 0
                    else:
                        logger.error(f"Failed to restart: {result['message']}")
            else:
                consecutive_failures = 0
                stats = client.get_container_stats(container_name)
                if stats:
                    logger.info(f"CPU: {stats.get('cpu_percent', 0):.1f}%, "
                              f"Memory: {stats.get('memory_mb', 0):.1f} MB")
            
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Monitor stopped")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(interval)

# Usage
if __name__ == "__main__":
    monitor_with_recovery("contimg-stream", interval=10)
```

## Docker Socket Access

### For Full Functionality

To use the Docker SDK (recommended), mount the Docker socket:

```yaml
# docker-compose.yml
services:
  api:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### Without Socket Mount

The client will automatically fall back to subprocess calls. This works but:
- Slightly slower (subprocess overhead)
- Less detailed stats (parsed from text output)
- Still fully functional for basic operations

## Implementation Details

### SDK Mode

When Docker SDK is available:
- Uses `docker.from_env()` to connect
- Direct container object manipulation
- Native stats and info access
- Better error handling

### Fallback Mode

When SDK unavailable:
- Uses `subprocess.run()` with `docker` commands
- Parses text output for stats
- Uses `docker inspect` for container info
- Handles command errors gracefully

### CPU Calculation

In SDK mode, CPU percentage is calculated from:
```
cpu_percent = (cpu_delta / system_delta) * num_cpus * 100
```

In fallback mode, parsed from `docker stats` output.

### Memory Calculation

In SDK mode, uses `memory_stats.usage` and `memory_stats.limit`.

In fallback mode, parses from `docker stats` output (e.g., "512MiB").

## Troubleshooting

### "Docker SDK not available"

**Cause:** Docker Python package not installed or socket not accessible.

**Solution:**
```bash
pip install docker
```

Or ensure Docker socket is mounted in container.

### "Container not found"

**Cause:** Container name incorrect or container doesn't exist.

**Solution:** Check container name:
```bash
docker ps -a | grep contimg-stream
```

### "Permission denied"

**Cause:** Docker socket permissions or user not in docker group.

**Solution:**
```bash
sudo usermod -aG docker $USER
# Or use sudo for docker commands
```

## Best Practices

### 1. Always Check Availability

```python
client = get_docker_client()
if not client.is_available():
    logger.warning("Docker SDK not available, using subprocess fallback")
```

### 2. Handle Errors Gracefully

```python
try:
    result = client.start_container("contimg-stream")
    if not result["success"]:
        # Handle specific error cases
        if "not found" in result["message"].lower():
            logger.error("Container does not exist")
        elif "permission" in result["message"].lower():
            logger.error("Permission denied - check Docker socket access")
        else:
            logger.error(f"Start failed: {result['message']}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

### 3. Use Timeouts for Long Operations

```python
# Stop with longer timeout for graceful shutdown
result = client.stop_container("contimg-stream", timeout=30)
```

### 4. Cache Client Instance

```python
# Good: Reuse client instance
client = get_docker_client()  # Returns singleton
status1 = client.is_container_running("contimg-stream")
status2 = client.is_container_running("contimg-api")  # Reuses same client

# Avoid: Creating new instances unnecessarily
```

### 5. Monitor Resource Usage

```python
def check_resource_limits(container_name: str, max_cpu: float = 90.0, max_memory_mb: float = 8192):
    """Check if container exceeds resource limits."""
    client = get_docker_client()
    stats = client.get_container_stats(container_name)
    
    if not stats:
        return False, "Could not get stats"
    
    cpu = stats.get("cpu_percent", 0)
    memory = stats.get("memory_mb", 0)
    
    issues = []
    if cpu and cpu > max_cpu:
        issues.append(f"CPU usage {cpu:.1f}% exceeds limit {max_cpu}%")
    if memory and memory > max_memory_mb:
        issues.append(f"Memory {memory:.1f} MB exceeds limit {max_memory_mb} MB")
    
    return len(issues) == 0, "; ".join(issues) if issues else "OK"
```

## Performance Considerations

### SDK vs Subprocess

- **SDK Mode**: Faster (~10-50ms per operation), more accurate stats
- **Subprocess Mode**: Slower (~50-200ms per operation), parsed text output

### Stats Collection

Stats collection is the slowest operation:
- SDK mode: ~100-500ms (depends on Docker daemon)
- Subprocess mode: ~200-1000ms (command execution + parsing)

**Recommendation:** Cache stats for 1-5 seconds if polling frequently.

## See Also

- [Streaming Service Manager](../concepts/streaming-architecture.md#streaming-service-manager)
- [Docker Deployment Guide](../operations/deploy-docker.md)
- [Streaming API Reference](./streaming-api.md)
- [Streaming Architecture](../concepts/streaming-architecture.md)


# Streaming Service API Reference

## Overview

The Streaming Service API provides RESTful endpoints for controlling and
monitoring the streaming converter service. All endpoints are under the base
path api/streaming (base path, not a standalone endpoint).

Base path: `http://localhost:8010/api/streaming`

**Authentication:** None (currently)

**Content-Type:** `application/json`

## Endpoints

### GET /api/streaming/status

Get the current status of the streaming service.

**Response:**

```json
{
  "running": true,
  "pid": 12345,
  "started_at": "2025-11-06T14:30:00Z",
  "uptime_seconds": 3600.5,
  "cpu_percent": 15.2,
  "memory_mb": 512.3,
  "last_heartbeat": "2025-11-06T15:30:00Z",
  "config": {
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16,
    "chunk_duration": 5.0,
    "max_workers": 4
  },
  "error": null
}
```

**Fields:**

- `running`: Boolean indicating if service is running
- `pid`: Process ID (if running)
- `started_at`: ISO timestamp when service started
- `uptime_seconds`: Time since service started
- `cpu_percent`: Current CPU usage percentage
- `memory_mb`: Current memory usage in MB
- `config`: Current service configuration
- `error`: Error message if service is unhealthy

**Example:**

```bash
curl http://localhost:8010/api/streaming/status
```

---

### GET /api/streaming/health

Get health check information for the streaming service.

**Response:**

```json
{
  "healthy": true,
  "running": true,
  "uptime_seconds": 3600.5,
  "cpu_percent": 15.2,
  "memory_mb": 512.3,
  "error": null
}
```

**Fields:**

- `healthy`: Overall health status (true if running and no errors)
- `running`: Service running status
- `uptime_seconds`: Service uptime
- `cpu_percent`: Current CPU usage
- `memory_mb`: Current memory usage
- `error`: Error message if unhealthy

**Example:**

```bash
curl http://localhost:8010/api/streaming/health
```

---

### GET /api/streaming/config

Get the current streaming service configuration.

**Response:**

```json
{
  "input_dir": "/data/incoming",
  "output_dir": "/stage/dsa110-contimg/ms",
  "queue_db": "state/ingest.sqlite3",
  "registry_db": "state/cal_registry.sqlite3",
  "scratch_dir": "/stage/dsa110-contimg",
  "expected_subbands": 16,
  "chunk_duration": 5.0,
  "log_level": "INFO",
  "use_subprocess": true,
  "monitoring": true,
  "monitor_interval": 60.0,
  "poll_interval": 5.0,
  "worker_poll_interval": 5.0,
  "max_workers": 4,
  "stage_to_tmpfs": false,
  "tmpfs_path": "/dev/shm"
}
```

**Example:**

```bash
curl http://localhost:8010/api/streaming/config
```

---

### POST /api/streaming/config

Update the streaming service configuration. If the service is running, it will
be restarted with the new configuration.

**Request Body:**

```json
{
  "input_dir": "/data/incoming",
  "output_dir": "/stage/dsa110-contimg/ms",
  "expected_subbands": 16,
  "chunk_duration": 5.0,
  "log_level": "INFO",
  "max_workers": 4
}
```

**Response:**

```json
{
  "success": true,
  "message": "Configuration updated (service not running)",
  "pid": null
}
```

**Example:**

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16,
    "chunk_duration": 5.0,
    "max_workers": 4
  }'
```

---

### POST /api/streaming/start

Start the streaming service.

**Request Body (Optional):**

```json
{
  "input_dir": "/data/incoming",
  "output_dir": "/stage/dsa110-contimg/ms",
  "expected_subbands": 16,
  "chunk_duration": 5.0
}
```

If no body is provided, uses saved configuration or defaults.

**Response:**

```json
{
  "success": true,
  "message": "Streaming service started successfully",
  "pid": 12345
}
```

**Example:**

```bash
# Start with default/saved config
curl -X POST http://localhost:8010/api/streaming/start

# Start with custom config
curl -X POST http://localhost:8010/api/streaming/start \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16
  }'
```

---

### POST /api/streaming/stop

Stop the streaming service.

**Response:**

```json
{
  "success": true,
  "message": "Streaming service stopped successfully",
  "pid": null
}
```

**Example:**

```bash
curl -X POST http://localhost:8010/api/streaming/stop
```

---

### POST /api/streaming/restart

Restart the streaming service.

**Request Body (Optional):**

```json
{
  "input_dir": "/data/incoming",
  "output_dir": "/stage/dsa110-contimg/ms",
  "expected_subbands": 16
}
```

If no body is provided, restarts with current configuration.

**Response:**

```json
{
  "success": true,
  "message": "Streaming service restarted successfully",
  "pid": 12345
}
```

**Example:**

```bash
curl -X POST http://localhost:8010/api/streaming/restart
```

---

### GET /api/streaming/metrics

Get processing metrics and queue statistics.

**Response:**

```json
{
  "service_running": true,
  "uptime_seconds": 3600.5,
  "cpu_percent": 15.2,
  "memory_mb": 512.3,
  "queue_stats": {
    "collecting": 2,
    "pending": 5,
    "in_progress": 1,
    "completed": 150,
    "failed": 3
  },
  "processing_rate_per_hour": 12
}
```

**Fields:**

- `service_running`: Whether the service is running
- `uptime_seconds`: Service uptime
- `cpu_percent`: Current CPU usage
- `memory_mb`: Current memory usage
- `queue_stats`: Count of queue items by state
- `processing_rate_per_hour`: Groups processed in the last hour

**Example:**

```bash
curl http://localhost:8010/api/streaming/metrics
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Endpoint or resource not found
- `500 Internal Server Error`: Server error

---

## Python Client Examples

### Basic Usage

```python
import requests
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8010/api/streaming"

# Get status
response = requests.get(f"{BASE_URL}/status")
status = response.json()
print(f"Service running: {status['running']}")

# Start service
response = requests.post(f"{BASE_URL}/start")
result = response.json()
print(f"Start result: {result['message']}")

# Update configuration
config = {
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16,
    "max_workers": 4
}
response = requests.post(f"{BASE_URL}/config", json=config)
result = response.json()
print(f"Config update: {result['message']}")

# Get metrics
response = requests.get(f"{BASE_URL}/metrics")
metrics = response.json()
print(f"Processing rate: {metrics['processing_rate_per_hour']} groups/hour")
```

### Advanced Usage with Error Handling

```python
import requests
import time
from typing import Dict, Any, Optional
from requests.exceptions import RequestException, ConnectionError, Timeout

BASE_URL = "http://localhost:8010/api/streaming"

class StreamingServiceClient:
    """Client for streaming service API with error handling."""

    def __init__(self, base_url: str = BASE_URL, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request with error handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method, url, timeout=self.timeout, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except ConnectionError:
            raise RuntimeError(f"Cannot connect to API at {self.base_url}")
        except Timeout:
            raise RuntimeError(f"Request to {url} timed out after {self.timeout}s")
        except requests.HTTPError as e:
            error_detail = e.response.json().get("detail", str(e))
            raise RuntimeError(f"API error: {error_detail}")
        except RequestException as e:
            raise RuntimeError(f"Request failed: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return self._request("GET", "/status")

    def get_health(self) -> Dict[str, Any]:
        """Get health check."""
        return self._request("GET", "/health")

    def start(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start the service."""
        data = config if config else None
        return self._request("POST", "/start", json=data)

    def stop(self) -> Dict[str, Any]:
        """Stop the service."""
        return self._request("POST", "/stop")

    def restart(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Restart the service."""
        data = config if config else None
        return self._request("POST", "/restart", json=data)

    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration."""
        return self._request("POST", "/config", json=config)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._request("GET", "/config")

    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        return self._request("GET", "/metrics")

    def wait_for_healthy(self, timeout: int = 60, poll_interval: int = 2) -> bool:
        """Wait for service to become healthy."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                health = self.get_health()
                if health.get("healthy", False):
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        return False

    def ensure_running(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Ensure service is running, start if not."""
        try:
            status = self.get_status()
            if status.get("running", False):
                return True

            # Service not running, start it
            result = self.start(config)
            if not result.get("success", False):
                raise RuntimeError(f"Failed to start: {result.get('message')}")

            # Wait for it to become healthy
            return self.wait_for_healthy()
        except Exception as e:
            print(f"Error ensuring service is running: {e}")
            return False

# Usage example
if __name__ == "__main__":
    client = StreamingServiceClient()

    # Ensure service is running
    if client.ensure_running():
        print("Service is running")

        # Monitor for a while
        for i in range(10):
            metrics = client.get_metrics()
            status = client.get_status()
            print(f"Status: {status['running']}, "
                  f"CPU: {status.get('cpu_percent', 0):.1f}%, "
                  f"Rate: {metrics.get('processing_rate_per_hour', 0)} groups/hr")
            time.sleep(5)
    else:
        print("Failed to start service")
```

### Integration Example: Monitoring Script

```python
#!/usr/bin/env python3
"""
Monitor streaming service and send alerts if unhealthy.
"""
import requests
import time
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8010/api/streaming"

def check_service_health() -> tuple[bool, Dict[str, Any]]:
    """Check service health and return status."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        health = response.json()
        return health.get("healthy", False), health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False, {"error": str(e)}

def check_processing_rate(metrics: Dict[str, Any], min_rate: float = 1.0) -> bool:
    """Check if processing rate is above minimum."""
    rate = metrics.get("processing_rate_per_hour", 0)
    return rate >= min_rate

def send_alert(message: str):
    """Send alert (implement your notification method)."""
    logger.warning(f"ALERT: {message}")
    # TODO: Implement Slack, email, or other notification

def monitor_service(interval: int = 60, min_rate: float = 1.0):
    """Monitor service continuously."""
    logger.info("Starting streaming service monitor")

    consecutive_failures = 0
    max_failures = 3

    while True:
        try:
            # Check health
            healthy, health_data = check_service_health()

            if not healthy:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    send_alert(f"Service unhealthy: {health_data.get('error', 'Unknown error')}")
                logger.warning(f"Service unhealthy (failure {consecutive_failures}/{max_failures})")
            else:
                consecutive_failures = 0

                # Check processing rate
                response = requests.get(f"{BASE_URL}/metrics", timeout=5)
                metrics = response.json()

                if not check_processing_rate(metrics, min_rate):
                    send_alert(f"Low processing rate: {metrics.get('processing_rate_per_hour', 0)} groups/hour")

                logger.info(f"Service healthy - Rate: {metrics.get('processing_rate_per_hour', 0)} groups/hr")

            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    monitor_service(interval=60, min_rate=1.0)
```

### Testing Example

```python
import pytest
import requests
from unittest.mock import Mock, patch

BASE_URL = "http://localhost:8010/api/streaming"

class TestStreamingService:
    """Test suite for streaming service API."""

    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock()
        response.json.return_value = {"running": True, "pid": 12345}
        response.raise_for_status = Mock()
        return response

    def test_get_status_success(self, mock_response):
        """Test successful status retrieval."""
        with patch('requests.get', return_value=mock_response):
            response = requests.get(f"{BASE_URL}/status")
            status = response.json()
            assert status["running"] is True
            assert "pid" in status

    def test_start_service(self, mock_response):
        """Test starting service."""
        mock_response.json.return_value = {
            "success": True,
            "message": "Service started",
            "pid": 12345
        }
        with patch('requests.post', return_value=mock_response):
            response = requests.post(f"{BASE_URL}/start")
            result = response.json()
            assert result["success"] is True
            assert result["pid"] == 12345

    def test_start_service_already_running(self, mock_response):
        """Test starting service when already running."""
        mock_response.json.return_value = {
            "success": False,
            "message": "Service already running",
            "pid": 12345
        }
        with patch('requests.post', return_value=mock_response):
            response = requests.post(f"{BASE_URL}/start")
            result = response.json()
            assert result["success"] is False
            assert "already running" in result["message"].lower()

    def test_update_config(self, mock_response):
        """Test configuration update."""
        config = {
            "input_dir": "/data/incoming",
            "output_dir": "/scratch/output",
            "max_workers": 8
        }
        mock_response.json.return_value = {
            "success": True,
            "message": "Configuration updated"
        }
        with patch('requests.post', return_value=mock_response):
            response = requests.post(f"{BASE_URL}/config", json=config)
            result = response.json()
            assert result["success"] is True

    def test_get_metrics(self, mock_response):
        """Test metrics retrieval."""
        mock_response.json.return_value = {
            "service_running": True,
            "processing_rate_per_hour": 12,
            "queue_stats": {
                "pending": 5,
                "in_progress": 1,
                "completed": 150
            }
        }
        with patch('requests.get', return_value=mock_response):
            response = requests.get(f"{BASE_URL}/metrics")
            metrics = response.json()
            assert metrics["service_running"] is True
            assert "queue_stats" in metrics
            assert metrics["processing_rate_per_hour"] > 0
```

---

## JavaScript/TypeScript Examples

### Basic Usage

```typescript
const BASE_URL = "http://localhost:8010/api/streaming";

// Get status
async function getStatus() {
  const response = await fetch(`${BASE_URL}/status`);
  const status = await response.json();
  console.log("Service running:", status.running);
  return status;
}

// Start service
async function startService(config?: StreamingConfig) {
  const response = await fetch(`${BASE_URL}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: config ? JSON.stringify(config) : undefined,
  });
  const result = await response.json();
  console.log("Start result:", result.message);
  return result;
}

// Get metrics
async function getMetrics() {
  const response = await fetch(`${BASE_URL}/metrics`);
  const metrics = await response.json();
  console.log("Processing rate:", metrics.processing_rate_per_hour);
  return metrics;
}
```

### Advanced Client Class with Error Handling

```typescript
interface StreamingStatus {
  running: boolean;
  pid?: number;
  started_at?: string;
  uptime_seconds?: number;
  cpu_percent?: number;
  memory_mb?: number;
  error?: string;
}

interface StreamingConfig {
  input_dir: string;
  output_dir: string;
  expected_subbands?: number;
  chunk_duration?: number;
  max_workers?: number;
  [key: string]: any;
}

interface ApiResponse<T> {
  success?: boolean;
  message?: string;
  [key: string]: any;
}

class StreamingServiceClient {
  private baseUrl: string;
  private timeout: number;

  constructor(
    baseUrl: string = "http://localhost:8010/api/streaming",
    timeout: number = 30000
  ) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === "AbortError") {
        throw new Error(`Request timeout after ${this.timeout}ms`);
      }
      if (error instanceof TypeError) {
        throw new Error(`Network error: ${error.message}`);
      }
      throw error;
    }
  }

  async getStatus(): Promise<StreamingStatus> {
    return this.request<StreamingStatus>("/status");
  }

  async getHealth(): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>("/health");
  }

  async start(config?: StreamingConfig): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>("/start", {
      method: "POST",
      body: config ? JSON.stringify(config) : undefined,
    });
  }

  async stop(): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>("/stop", {
      method: "POST",
    });
  }

  async restart(config?: StreamingConfig): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>("/restart", {
      method: "POST",
      body: config ? JSON.stringify(config) : undefined,
    });
  }

  async updateConfig(config: StreamingConfig): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>("/config", {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  async getConfig(): Promise<StreamingConfig> {
    return this.request<StreamingConfig>("/config");
  }

  async getMetrics(): Promise<any> {
    return this.request<any>("/metrics");
  }

  async waitForHealthy(
    timeout: number = 60000,
    pollInterval: number = 2000
  ): Promise<boolean> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      try {
        const health = await this.getHealth();
        if (health.healthy) {
          return true;
        }
      } catch (error) {
        // Continue polling
      }
      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }
    return false;
  }

  async ensureRunning(config?: StreamingConfig): Promise<boolean> {
    try {
      const status = await this.getStatus();
      if (status.running) {
        return true;
      }

      const result = await this.start(config);
      if (!result.success) {
        throw new Error(result.message || "Failed to start service");
      }

      return await this.waitForHealthy();
    } catch (error) {
      console.error("Error ensuring service is running:", error);
      return false;
    }
  }
}

// Usage example
const client = new StreamingServiceClient();

async function monitorService() {
  if (await client.ensureRunning()) {
    console.log("Service is running");

    // Monitor for a while
    for (let i = 0; i < 10; i++) {
      const metrics = await client.getMetrics();
      const status = await client.getStatus();
      console.log(
        `Status: ${status.running}, ` +
          `CPU: ${status.cpu_percent?.toFixed(1)}%, ` +
          `Rate: ${metrics.processing_rate_per_hour} groups/hr`
      );
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }
  } else {
    console.error("Failed to start service");
  }
}
```

### React Hook Example

```typescript
import { useState, useEffect, useCallback } from 'react';

interface UseStreamingServiceReturn {
  status: StreamingStatus | null;
  metrics: any | null;
  loading: boolean;
  error: string | null;
  start: (config?: StreamingConfig) => Promise<void>;
  stop: () => Promise<void>;
  restart: (config?: StreamingConfig) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useStreamingService(
  pollInterval: number = 5000
): UseStreamingServiceReturn {
  const [status, setStatus] = useState<StreamingStatus | null>(null);
  const [metrics, setMetrics] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const client = new StreamingServiceClient();

  const fetchStatus = useCallback(async () => {
    try {
      const newStatus = await client.getStatus();
      setStatus(newStatus);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  }, []);

  const fetchMetrics = useCallback(async () => {
    try {
      const newMetrics = await client.getMetrics();
      setMetrics(newMetrics);
    } catch (err: any) {
      // Metrics failure is not critical
      console.warn('Failed to fetch metrics:', err);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchStatus(), fetchMetrics()]);
    setLoading(false);
  }, [fetchStatus, fetchMetrics]);

  const start = useCallback(async (config?: StreamingConfig) => {
    try {
      setLoading(true);
      await client.start(config);
      await refresh();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [refresh]);

  const stop = useCallback(async () => {
    try {
      setLoading(true);
      await client.stop();
      await refresh();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [refresh]);

  const restart = useCallback(async (config?: StreamingConfig) => {
    try {
      setLoading(true);
      await client.restart(config);
      await refresh();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [refresh]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, pollInterval);
    return () => clearInterval(interval);
  }, [refresh, pollInterval]);

  return {
    status,
    metrics,
    loading,
    error,
    start,
    stop,
    restart,
    refresh,
  };
}

// Usage in React component
function StreamingControl() {
  const { status, metrics, loading, error, start, stop, restart } = useStreamingService();

  if (loading && !status) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div>
      <p>Status: {status?.running ? 'Running' : 'Stopped'}</p>
      {status?.running && (
        <>
          <p>CPU: {status.cpu_percent?.toFixed(1)}%</p>
          <p>Memory: {status.memory_mb?.toFixed(0)} MB</p>
          <p>Processing Rate: {metrics?.processing_rate_per_hour} groups/hour</p>
        </>
      )}
      <button onClick={() => status?.running ? stop() : start()}>
        {status?.running ? 'Stop' : 'Start'}
      </button>
      {status?.running && (
        <button onClick={() => restart()}>Restart</button>
      )}
    </div>
  );
}
```

### Error Handling Patterns

```typescript
// Pattern 1: Try-catch with specific error types
async function safeStartService() {
  try {
    const client = new StreamingServiceClient();
    const result = await client.start();
    if (!result.success) {
      console.error("Start failed:", result.message);
      return false;
    }
    return true;
  } catch (error: any) {
    if (error.message.includes("timeout")) {
      console.error("Request timed out - service may be overloaded");
    } else if (error.message.includes("Network error")) {
      console.error("Cannot connect to API - check if API is running");
    } else {
      console.error("Unexpected error:", error);
    }
    return false;
  }
}

// Pattern 2: Retry logic
async function startWithRetry(maxRetries: number = 3) {
  const client = new StreamingServiceClient();
  for (let i = 0; i < maxRetries; i++) {
    try {
      const result = await client.start();
      if (result.success) {
        return true;
      }
      if (i < maxRetries - 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000 * (i + 1)));
      }
    } catch (error) {
      if (i === maxRetries - 1) {
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
  return false;
}

// Pattern 3: Health check before operations
async function safeRestart() {
  const client = new StreamingServiceClient();
  try {
    const health = await client.getHealth();
    if (!health.healthy) {
      console.warn("Service is unhealthy, attempting restart...");
    }
    return await client.restart();
  } catch (error) {
    console.error("Restart failed:", error);
    throw error;
  }
}
```

---

## See Also

- [Streaming Control Guide](../how-to/streaming-control.md) - User guide for
  dashboard control
- [Streaming Architecture](../concepts/streaming-architecture.md) - System
  architecture
- [Docker Client Reference](../reference/docker-client.md) - Docker integration
  details

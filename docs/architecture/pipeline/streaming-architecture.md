# Streaming Service Architecture

## Overview

The streaming service control system provides unified management of the DSA-110
streaming converter through a REST API and web dashboard. This document
describes the architecture, design decisions, and component interactions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard (Frontend)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         StreamingPage.tsx (React Component)          │   │
│  │  - Status Display  - Control Buttons  - Config UI    │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                             │ HTTP/REST
┌───────────────────────────▼─────────────────────────────────┐
│                    API Server (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              /api/streaming/* endpoints               │   │
│  │  - GET /status  - POST /start  - POST /stop  etc.     │   │
│  └──────────────────────────┬───────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                             │
┌───────────────────────────▼─────────────────────────────────┐
│            StreamingServiceManager                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  - Service lifecycle management                       │   │
│  │  - Configuration persistence                          │   │
│  │  - Status monitoring                                  │   │
│  └──────────────────────────┬───────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                          │
┌───────▼────────┐                      ┌─────────▼──────────┐
│ DockerClient   │                      │  Direct Process    │
│  - SDK mode    │                      │  - subprocess      │
│  - Fallback    │                      │  - psutil          │
└───────┬────────┘                      └─────────┬──────────┘
        │                                          │
        └──────────────────┬───────────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Streaming Service  │
                │  (streaming_converter)│
                └─────────────────────┘
```

## Components

### 1. Frontend (React/TypeScript)

**Location:** `frontend/src/pages/StreamingPage.tsx`

**Responsibilities:**

- Display service status and metrics
- Provide control UI (start/stop/restart)
- Configuration editor
- Real-time updates via polling

**Key Features:**

- Auto-refresh status every 5 seconds
- Visual indicators for service state
- Resource usage charts
- Queue statistics display

### 2. API Endpoints (FastAPI)

**Location:** `backend/src/dsa110_contimg/api/routes.py`

**Endpoints:**

- `GET /api/streaming/status` - Service status
- `GET /api/streaming/health` - Health check
- `GET /api/streaming/config` - Get configuration
- `POST /api/streaming/config` - Update configuration
- `POST /api/streaming/start` - Start service
- `POST /api/streaming/stop` - Stop service
- `POST /api/streaming/restart` - Restart service
- `GET /api/streaming/metrics` - Processing metrics

### 3. Streaming Service Manager

**Location:** `backend/src/dsa110_contimg/api/streaming_service.py`

**Class:** `StreamingServiceManager`

**Responsibilities:**

- Service lifecycle management (start/stop/restart)
- Configuration persistence (JSON file)
- Status monitoring and health checks
- Process/container detection

**Key Methods:**

- `get_status()` - Get current service status
- `start()` - Start the service
- `stop()` - Stop the service
- `restart()` - Restart the service
- `update_config()` - Update configuration
- `get_health()` - Health check

**Configuration Storage:**

- Location: `state/streaming_config.json`
- Format: JSON
- Persists across restarts

### 4. Docker Client

**Location:** `backend/src/dsa110_contimg/api/docker_client.py`

**Class:** `DockerClient`

**Responsibilities:**

- Docker container operations
- Automatic SDK/fallback detection
- Resource statistics collection
- Container information retrieval

**Modes:**

1. **SDK Mode**: Uses Docker Python SDK (`docker` package)
2. **Fallback Mode**: Uses subprocess calls to `docker` command

**Key Methods:**

- `is_container_running()` - Check container status
- `start_container()` - Start container
- `stop_container()` - Stop container
- `restart_container()` - Restart container
- `get_container_stats()` - Get resource stats
- `get_container_info()` - Get container metadata

## Design Decisions

### 1. Docker vs Direct Process

**Decision:** Support both Docker containers and direct processes.

**Rationale:**

- Flexibility for different deployment scenarios
- Development vs production environments
- Testing without Docker

**Implementation:**

- Detects Docker environment via `/.dockerenv` or `docker-compose.yml` presence
- Falls back to direct process management if not in Docker

### 2. Docker SDK vs Subprocess

**Decision:** Use Docker SDK with subprocess fallback.

**Rationale:**

- SDK provides better error handling and type safety
- Fallback ensures functionality without SDK installation
- Works in containers without socket mount

**Implementation:**

- Tries to connect via `docker.from_env()`
- Falls back to `subprocess.run()` with `docker` commands
- Same API interface regardless of mode

### 3. Configuration Persistence

**Decision:** Store configuration in JSON file.

**Rationale:**

- Simple and human-readable
- Easy to edit manually if needed
- No database dependency
- Survives API restarts

**Location:** `state/streaming_config.json`

### 4. Status Polling vs WebSockets

**Decision:** Use HTTP polling for status updates.

**Rationale:**

- Simpler implementation
- Works with standard HTTP infrastructure
- Sufficient for current use case (5-30s refresh)
- Can upgrade to WebSockets later if needed

**Refresh Intervals:**

- Status: 5 seconds
- Health: 10 seconds
- Metrics: 30 seconds

### 5. PID File Management

**Decision:** Store PID in file for process tracking.

**Rationale:**

- Allows status checking after API restart
- Works for both Docker and direct processes
- Simple and reliable

**Location:** `state/streaming.pid`

## Data Flow

### Starting the Service

```
1. User clicks "Start" in dashboard
2. Frontend sends POST /api/streaming/start
3. StreamingServiceManager.start() called
4. Detects Docker environment
5. DockerClient.start_container() called
6. Container started via SDK or subprocess
7. PID saved to file
8. Status returned to frontend
9. Frontend polls /api/streaming/status
```

### Status Monitoring

```
1. Frontend polls /api/streaming/status every 5s
2. StreamingServiceManager.get_status() called
3. Checks Docker environment
4. DockerClient.get_container_info() called
5. DockerClient.get_container_stats() called
6. Status object constructed
7. Returned to frontend
8. UI updates with new data
```

### Configuration Update

```
1. User edits config in dashboard
2. Frontend sends POST /api/streaming/config
3. StreamingServiceManager.update_config() called
4. Config saved to JSON file
5. If service running, restart() called
6. Service restarted with new config
7. Status returned to frontend
```

## Error Handling

### Service Start Failures

- **Container not found**: Returns error message
- **Permission denied**: Returns error with guidance
- **Docker not available**: Falls back to direct process
- **Config invalid**: Validates before starting

### Status Check Failures

- **Container stopped**: Returns `running: false`
- **Docker unavailable**: Falls back to subprocess
- **Stats unavailable**: Returns partial status
- **Network errors**: Logged and returned in error field

## Security Considerations

### Docker Socket Access

**Risk:** Mounting Docker socket gives full Docker control.

**Mitigation:**

- Only mount when necessary
- Use read-only socket if possible (future enhancement)
- Document security implications

### API Authentication

**Current:** None (local network assumed)

**Future:** Add authentication for production deployments

## Performance

### Status Polling

- **Frequency**: 5-30 seconds
- **Impact**: Minimal (lightweight queries)
- **Optimization**: Could use WebSockets for real-time updates

### Docker Operations

- **SDK Mode**: ~10-50ms per operation
- **Subprocess Mode**: ~50-200ms per operation
- **Stats Collection**: ~100-500ms (depends on Docker)

## Future Enhancements

### Planned

1. **WebSocket Support**: Real-time status updates
2. **Log Viewer**: Stream logs to dashboard
3. **Historical Metrics**: Store and graph metrics over time
4. **Alert System**: Notifications for service issues
5. **Multi-Instance**: Support multiple streaming services

### Potential

1. **Kubernetes Support**: Native K8s integration
2. **Resource Limits**: Configurable CPU/memory limits
3. **Auto-Restart**: Automatic restart on failure
4. **Health Checks**: Built-in health check endpoints
5. **Metrics Export**: Prometheus-compatible metrics

## See Also

- [Streaming Guide](../../guides/streaming/index.md) - User guide
- [Streaming API Reference](../../guides/streaming/api.md) - API documentation
- [Streaming Troubleshooting](../../guides/streaming/troubleshooting.md) - Common issues

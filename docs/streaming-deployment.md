# Streaming Service Deployment & Control

## Overview

This document describes the complete streaming service deployment and control system that provides full dashboard-based management of the DSA-110 continuum imaging pipeline streaming service.

## Features

### ✅ Complete Dashboard Control
- **Start/Stop/Restart** streaming service from the dashboard
- **Real-time status monitoring** with CPU, memory, and uptime metrics
- **Configuration management** via UI
- **Queue statistics** and processing rate monitoring
- **Health checks** and error reporting

### ✅ Unified Architecture
- **Streaming Service Manager** (`streaming_service.py`) - Handles service lifecycle
- **REST API Endpoints** - Full control via HTTP API
- **Docker Integration** - Automatically detects and uses Docker when available
- **Process Management** - Works with both Docker containers and direct processes

### ✅ Clean Deployment
- **Deployment Script** (`ops/deploy.sh`) - Single command deployment
- **Mode Selection** - Choose streaming, manual, or both modes
- **Environment Validation** - Validates configuration before deployment
- **Health Checks** - Automatic service health verification

## API Endpoints

All endpoints are under `/api/streaming/`:

- `GET /api/streaming/status` - Get current service status
- `GET /api/streaming/health` - Get health check information
- `GET /api/streaming/config` - Get current configuration
- `POST /api/streaming/config` - Update configuration (restarts if running)
- `POST /api/streaming/start` - Start the service
- `POST /api/streaming/stop` - Stop the service
- `POST /api/streaming/restart` - Restart the service
- `GET /api/streaming/metrics` - Get processing metrics and queue stats

## Dashboard Access

Navigate to: **http://localhost:5173/streaming**

The streaming control page provides:
- Service status with visual indicators
- Resource usage (CPU, memory) with progress bars
- Queue statistics (pending, in_progress, completed, failed)
- Processing rate (groups per hour)
- Current configuration display
- Configuration editor dialog
- Start/Stop/Restart controls

## Deployment

### Quick Start

```bash
# Deploy in streaming mode (all services)
./ops/deploy.sh --mode streaming

# Deploy in manual mode (API + Frontend only)
./ops/deploy.sh --mode manual

# Deploy everything (default)
./ops/deploy.sh --mode both
```

### Deployment Script Options

```bash
./ops/deploy.sh [--mode streaming|manual|both] [--env-file path/to/.env]
```

**Modes:**
- `streaming`: Deploy with streaming service enabled
- `manual`: Deploy API and frontend only (no streaming)
- `both`: Deploy everything (default)

**Features:**
- Validates environment variables
- Creates required directories
- Builds Docker images
- Starts services
- Performs health checks
- Provides status summary

## Architecture

### Streaming Service Manager

The `StreamingServiceManager` class provides:
- **Process Detection**: Automatically detects Docker vs direct process execution
- **Lifecycle Management**: Start, stop, restart with proper cleanup
- **Status Monitoring**: Real-time status with resource usage
- **Configuration Persistence**: Saves/loads configuration from JSON file
- **Health Checks**: Comprehensive health status reporting

### Docker Integration

When running in Docker:
- Uses `docker-compose` commands to control containers
- Monitors container status via `docker inspect`
- Gets resource stats via `docker stats`
- Handles container PIDs correctly

### Direct Process Mode

When not in Docker:
- Spawns subprocess directly
- Uses `psutil` for process management
- Tracks PID in state directory
- Graceful shutdown with timeout

## Configuration

Configuration is stored in `state/streaming_config.json` and includes:

- `input_dir`: Directory to watch for UVH5 files
- `output_dir`: Output directory for MS files
- `queue_db`: Path to queue database
- `registry_db`: Path to calibration registry
- `scratch_dir`: Scratch directory for processing
- `expected_subbands`: Number of subbands (default: 16)
- `chunk_duration`: Minutes per group (default: 5.0)
- `log_level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `use_subprocess`: Use subprocess execution
- `monitoring`: Enable monitoring
- `monitor_interval`: Monitoring interval in seconds
- `poll_interval`: File polling interval
- `worker_poll_interval`: Worker polling interval
- `max_workers`: Maximum concurrent workers
- `stage_to_tmpfs`: Stage files to tmpfs
- `tmpfs_path`: TMPFS path

## Monitoring

### Real-time Metrics

The dashboard displays:
- **Service Status**: Running/Stopped with health indicator
- **Resource Usage**: CPU percentage and memory usage
- **Uptime**: Time since service started
- **Queue Stats**: Count by state (collecting, pending, in_progress, completed, failed)
- **Processing Rate**: Groups processed per hour

### Health Checks

Health endpoint returns:
- `healthy`: Overall health status
- `running`: Service running status
- `uptime_seconds`: Service uptime
- `cpu_percent`: Current CPU usage
- `memory_mb`: Current memory usage
- `error`: Error message if unhealthy

## Troubleshooting

### Service Won't Start

1. Check logs: `docker-compose logs stream`
2. Verify configuration in dashboard
3. Check directory permissions
4. Verify CASA6 Python is available

### Service Status Not Updating

1. Check API connectivity: `curl http://localhost:8010/api/streaming/status`
2. Verify Docker container is running: `docker-compose ps`
3. Check API logs: `docker-compose logs api`

### Configuration Not Saving

1. Verify `PIPELINE_STATE_DIR` is writable
2. Check disk space
3. Review API logs for errors

## Future Enhancements

Potential improvements:
- [ ] Log viewer in dashboard
- [ ] Historical metrics graphs
- [ ] Alert notifications
- [ ] Automatic restart on failure
- [ ] Resource limits configuration
- [ ] Multi-instance support
- [ ] WebSocket for real-time updates

## Files Created/Modified

### New Files
- `src/dsa110_contimg/api/streaming_service.py` - Service manager
- `frontend/src/pages/StreamingPage.tsx` - Dashboard UI
- `ops/deploy.sh` - Deployment script
- `docs/streaming-deployment.md` - This document

### Modified Files
- `src/dsa110_contimg/api/models.py` - Added streaming models
- `src/dsa110_contimg/api/routes.py` - Added streaming endpoints
- `frontend/src/api/queries.ts` - Added streaming hooks
- `frontend/src/App.tsx` - Added streaming route
- `frontend/src/components/Navigation.tsx` - Added streaming nav item


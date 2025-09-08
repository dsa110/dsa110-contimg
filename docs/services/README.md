# DSA-110 Pipeline Services

## Overview

The DSA-110 pipeline services provide a modern, distributed architecture for processing radio telescope data. The services are built using async Python with Redis-based distributed state management and message queuing.

## Service Architecture

### Core Services

1. **HDF5 Watcher Service** - Monitors HDF5 file creation and triggers MS conversion
2. **MS Processor Service** - Processes Measurement Sets using the enhanced pipeline
3. **Variability Analyzer Service** - Analyzes variability in photometry data
4. **Service Manager** - Orchestrates all services with health monitoring

### Key Features

- **Async Processing**: All services use async/await for non-blocking operations
- **Distributed State**: Redis-based state management for coordination
- **Message Queuing**: Inter-service communication via Redis queues
- **Health Monitoring**: Real-time health checks and metrics
- **Error Recovery**: Circuit breakers and retry mechanisms
- **Graceful Shutdown**: Proper cleanup on service termination

## Service Details

### HDF5 Watcher Service

**Purpose**: Monitors incoming HDF5 files and triggers MS conversion when complete sets are detected.

**Key Components**:
- `HDF5EventHandler`: Handles filesystem events
- `HDF5WatcherService`: Main service orchestrator

**Features**:
- File system monitoring using watchdog
- Complete set detection (all required subbands)
- Async processing to avoid blocking
- Distributed state for coordination
- Message queuing for processing triggers

**Configuration**:
```yaml
services:
  hdf5_watcher:
    enabled: true
    poll_interval_sec: 60
    expected_subbands: 12
    file_pattern: "20*T*.hdf5"
    processing_timeout_sec: 300
```

### MS Processor Service

**Purpose**: Processes Measurement Sets using the enhanced pipeline orchestrator.

**Key Components**:
- `MSProcessingHandler`: Handles MS processing logic
- `MSProcessorService`: Main service orchestrator

**Features**:
- Block-based processing (mosaic duration + overlap)
- Enhanced pipeline with error recovery
- Distributed state for processing locks
- Message queuing for processing coordination
- Automatic retry on failures

**Configuration**:
```yaml
services:
  ms_processor:
    enabled: true
    poll_interval_sec: 120
    mosaic_duration_min: 60
    mosaic_overlap_min: 5
    ms_chunk_duration_min: 5
    processing_timeout_sec: 1800
```

### Variability Analyzer Service

**Purpose**: Analyzes variability in photometry data to detect transient sources.

**Key Components**:
- `VariabilityAnalysisHandler`: Handles analysis logic
- `VariabilityAnalyzerService`: Main service orchestrator

**Features**:
- Periodic analysis of photometry data
- Variability metrics calculation
- Source identification and classification
- Results storage and reporting
- Configurable analysis intervals

**Configuration**:
```yaml
services:
  variability_analyzer:
    enabled: true
    analysis_interval_hours: 1
    min_data_points: 10
    variability_threshold: 0.1
    analysis_timeout_sec: 600
```

### Service Manager

**Purpose**: Orchestrates all services with unified health monitoring and management.

**Key Components**:
- `ServiceManager`: Main orchestrator
- Health monitoring and metrics
- Service lifecycle management
- Message routing and coordination

**Features**:
- Start/stop/restart individual services
- Health monitoring and alerting
- Service status reporting
- Automatic service recovery
- Unified configuration management

## Quick Start

### Prerequisites

1. **Redis Server**: Required for distributed state and messaging
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis
   
   # macOS
   brew install redis
   brew services start redis
   ```

2. **Python Dependencies**: Install required packages
   ```bash
   pip install redis aiohttp aiohttp-cors pandas numpy
   ```

### Starting Services

#### Start All Services
```bash
# Start all services in development mode
./scripts/start_services.sh development

# Start all services in production mode
./scripts/start_services.sh production
```

#### Start Individual Services
```bash
# Start only HDF5 watcher
./scripts/start_services.sh development hdf5_watcher

# Start only MS processor
./scripts/start_services.sh development ms_processor

# Start only variability analyzer
./scripts/start_services.sh development variability_analyzer

# Start only service manager
./scripts/start_services.sh development service_manager
```

### Checking Service Status

```bash
# Check all services
./scripts/status_services.sh

# Check specific service
./scripts/status_services.sh hdf5_watcher
```

### Stopping Services

```bash
# Stop all services
./scripts/stop_services.sh

# Stop specific service
./scripts/stop_services.sh hdf5_watcher
```

## Configuration

### Environment-Specific Configs

Services use environment-specific configurations in `config/environments/services.yaml`:

- **Development**: Optimized for testing with shorter intervals
- **Production**: Full-scale processing with optimized performance
- **Testing**: Minimal data for fast test execution

### Service Configuration

Each service can be configured with:

- **Polling intervals**: How often to check for new work
- **Timeouts**: Maximum time for operations
- **Thresholds**: Analysis and processing thresholds
- **Retry settings**: Error recovery configuration

### Redis Configuration

```yaml
redis:
  host: "localhost"
  port: 6379
  db: 0
  password: null
  max_connections: 10
  socket_timeout: 5
  socket_connect_timeout: 5
  retry_on_timeout: true
  health_check_interval: 30
```

## Monitoring and Health Checks

### Health Status

Services report health status through:
- **HEALTHY**: Service running normally
- **DEGRADED**: Service running with issues
- **UNHEALTHY**: Service not functioning
- **STOPPING**: Service shutting down

### Metrics

Each service reports metrics:
- Processing statistics
- Error rates
- Resource usage
- Performance metrics

### Logs

Service logs are stored in `logs/` directory:
- `hdf5_watcher.log`
- `ms_processor.log`
- `variability_analyzer.log`
- `service_manager.log`

## Message Queuing

### Message Types

- **HDF5_PROCESSING**: HDF5 file processing messages
- **MS_PROCESSING**: MS processing messages
- **VARIABILITY_ANALYSIS**: Variability analysis messages
- **SYSTEM**: System management messages

### Message Flow

1. HDF5 Watcher detects complete file sets
2. Sends HDF5_PROCESSING message
3. MS Processor receives message and processes files
4. Sends MS_PROCESSING completion message
5. Variability Analyzer processes photometry data
6. Sends VARIABILITY_ANALYSIS results

## Error Recovery

### Circuit Breakers

Services use circuit breakers to prevent cascading failures:
- Automatic failure detection
- Service isolation on repeated failures
- Gradual recovery attempts

### Retry Mechanisms

- Exponential backoff for transient failures
- Configurable retry limits
- Dead letter queues for failed messages

### State Management

- Distributed locks prevent duplicate processing
- State persistence across service restarts
- Automatic cleanup of stale state

## Development

### Running Examples

```bash
# Run service examples
python examples/service_examples.py

# Run specific example
python -c "
import asyncio
from examples.service_examples import example_hdf5_watcher
asyncio.run(example_hdf5_watcher())
"
```

### Testing Services

```bash
# Run unit tests
python -m pytest tests/unit/test_services.py

# Run integration tests
python -m pytest tests/integration/test_services.py
```

### Adding New Services

1. Create service directory in `services/`
2. Implement service class with async methods
3. Add to ServiceManager
4. Update configuration
5. Add deployment scripts

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check Redis is running: `redis-cli ping`
   - Verify configuration in `services.yaml`

2. **Service Won't Start**
   - Check logs in `logs/` directory
   - Verify configuration file exists
   - Check Python dependencies

3. **Services Not Processing**
   - Check Redis queues: `redis-cli llen hdf5_processing`
   - Verify file permissions
   - Check service status: `./scripts/status_services.sh`

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export DSA110_LOG_LEVEL=DEBUG
./scripts/start_services.sh development
```

### Performance Tuning

- Adjust polling intervals in configuration
- Increase Redis connection pool size
- Tune service timeouts based on data volume
- Monitor memory usage and adjust accordingly

## Production Deployment

### System Requirements

- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM recommended
- **Storage**: SSD recommended for data processing
- **Network**: Reliable connection for Redis

### Security Considerations

- Secure Redis with authentication
- Use TLS for inter-service communication
- Implement proper access controls
- Regular security updates

### Monitoring

- Set up monitoring dashboards
- Configure alerting for service failures
- Monitor resource usage
- Track processing metrics

## Support

For issues and questions:
1. Check logs in `logs/` directory
2. Review configuration files
3. Check Redis connectivity
4. Verify file permissions
5. Check system resources

The services are designed to be robust and self-healing, but proper monitoring and maintenance are essential for production use.

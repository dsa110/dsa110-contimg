cd # DSA-110 Pipeline - Phase 3 Advanced Features

## Overview

Phase 3 introduces advanced features for production-ready pipeline operation including error recovery, distributed state management, message queuing, and comprehensive monitoring. These features provide enterprise-grade reliability, scalability, and observability.

## **PHASE 3 FEATURES**

### 1. **Advanced Error Recovery System**

#### **Circuit Breakers**
- **Purpose**: Prevent cascading failures by temporarily stopping calls to failing services
- **States**: Closed (normal), Open (failing fast), Half-Open (testing recovery)
- **Configuration**: Failure thresholds, recovery timeouts, success thresholds

```python
from core.utils.error_recovery import CircuitBreakerConfig, get_error_recovery_manager

# Create circuit breaker for calibration operations
cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=300,  # 5 minutes
    expected_exception=Exception,
    success_threshold=2
)

recovery_manager = get_error_recovery_manager()
circuit_breaker = recovery_manager.create_circuit_breaker("calibration", cb_config)
```

#### **Retry Mechanisms**
- **Exponential Backoff**: Increasing delays between retries
- **Jitter**: Random variation to prevent thundering herd
- **Configurable Exceptions**: Define which exceptions are retryable

```python
from core.utils.error_recovery import RetryConfig, with_circuit_breaker

# Configure retry behavior
retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)

# Use decorator for automatic retry and circuit breaking
@with_circuit_breaker("calibration", cb_config, retry_config)
async def calibrate_data(ms_path):
    # Calibration logic here
    pass
```

#### **Failure Analysis**
- **Failure Tracking**: Record and analyze failure patterns
- **Recovery Strategies**: Automatic and manual recovery options
- **Failure Summaries**: Get insights into failure trends

```python
# Get failure summary for last 24 hours
failure_summary = recovery_manager.get_failure_summary(hours=24)
print(f"Total failures: {failure_summary['total_failures']}")
print(f"By operation: {failure_summary['operation_counts']}")
```

### 2. **Distributed State Management**

#### **Redis-Based State Storage**
- **Key-Value Storage**: Store processing states, service statuses, metadata
- **TTL Support**: Automatic expiration of stale data
- **Atomic Operations**: Thread-safe state updates

```python
from core.utils.distributed_state import initialize_distributed_state, get_distributed_state_manager

# Initialize distributed state
await initialize_distributed_state(
    redis_url="redis://localhost:6379",
    namespace="dsa110_pipeline"
)

state_manager = get_distributed_state_manager()

# Set processing block state
await state_manager.set_processing_block_state(
    "block_20230101_001",
    "processing",
    {"start_time": "2023-01-01T00:00:00", "ms_count": 5}
)

# Get processing status
status = await state_manager.get_processing_block_state("block_20230101_001")
```

#### **Distributed Locks**
- **Coordination**: Prevent concurrent processing of the same resources
- **Timeout Support**: Automatic lock expiration
- **Owner Tracking**: Ensure only lock owners can release locks

```python
# Acquire distributed lock
lock_acquired = await state_manager.acquire_lock(
    "process_block_20230101_001",
    timeout=300,  # 5 minutes
    owner="orchestrator_instance_1"
)

if lock_acquired:
    try:
        # Process the block
        await process_block(block)
    finally:
        # Release lock
        await state_manager.release_lock("process_block_20230101_001")
```

#### **Service Status Tracking**
- **Health Monitoring**: Track service health across instances
- **Status Updates**: Real-time service status updates
- **Service Discovery**: Find available services

```python
# Update service status
await state_manager.set_service_status(
    "hdf5_watcher",
    "healthy",
    {"last_heartbeat": "2023-01-01T00:00:00", "processed_files": 150}
)

# Get all service statuses
service_statuses = await state_manager.get_all_service_statuses()
```

### 3. **Message Queue System**

#### **Redis-Based Messaging**
- **Publish/Subscribe**: Real-time event broadcasting
- **Priority Queues**: Message prioritization for critical operations
- **TTL Support**: Automatic message expiration

```python
from core.messaging import initialize_message_queues, get_message_queue_manager

# Initialize message queues
await initialize_message_queues(
    redis_url="redis://localhost:6379",
    namespace="dsa110_pipeline"
)

queue_manager = get_message_queue_manager()
queue = await queue_manager.get_queue("processing_events")

# Publish message
message = queue.create_message(
    MessageType.PROCESSING_REQUEST,
    {"block_id": "block_001", "action": "start"},
    "orchestrator",
    priority=MessagePriority.HIGH
)

await queue.publish("processing_events", message)
```

#### **Message Types**
- **Processing Events**: Block processing start/complete notifications
- **Service Status**: Health check and status updates
- **Error Notifications**: Failure alerts and error reports
- **Metrics Updates**: Performance and monitoring data

#### **Queue Management**
- **Multiple Queues**: Separate queues for different message types
- **Message Routing**: Route messages to appropriate handlers
- **Dead Letter Queues**: Handle failed message processing

### 4. **Advanced Monitoring & Alerting**

#### **Real-Time Metrics**
- **Custom Metrics**: Define and collect custom metrics
- **Metric Types**: Counters, gauges, histograms, timers
- **Tagging**: Add metadata to metrics for filtering

```python
from monitoring.advanced_monitoring import AdvancedMonitor, MetricType

monitor = AdvancedMonitor()

# Record custom metrics
await monitor.record_metric("block_processing_time", 120.5, MetricType.TIMER, unit="seconds")
await monitor.record_metric("ms_files_processed", 1, MetricType.COUNTER)
await monitor.record_metric("memory_usage", 85.2, MetricType.GAUGE, unit="percent")
```

#### **Threshold-Based Alerting**
- **Configurable Rules**: Define alert conditions
- **Multiple Operators**: >, <, >=, <=, ==, !=
- **Alert Levels**: Info, Warning, Error, Critical

```python
from monitoring.advanced_monitoring import ThresholdRule, AlertLevel

# Create threshold rule
rule = ThresholdRule(
    name="high_processing_time",
    metric_name="block_processing_time",
    operator=">",
    threshold_value=300.0,  # 5 minutes
    alert_level=AlertLevel.WARNING,
    duration=60  # Alert after 60 seconds
)

await monitor.add_threshold_rule(rule)
```

#### **Web-Based Dashboard**
- **Real-Time Updates**: Live monitoring of pipeline status
- **Health Overview**: Service health and status
- **Active Alerts**: Current alerts and their severity
- **Metrics Visualization**: Charts and graphs of key metrics

```python
from monitoring.advanced_monitoring import MonitoringDashboard

# Start monitoring dashboard
dashboard = MonitoringDashboard(monitor, port=8080)
await dashboard.start()

# Access dashboard at http://localhost:8080
```

### 5. **Enhanced Pipeline Orchestrator**

#### **Advanced Processing**
- **Recovery-Aware Processing**: Automatic retry and recovery
- **Stage-Level Recovery**: Retry individual stages on failure
- **Partial Success Handling**: Continue processing with reduced data

```python
from core.pipeline import EnhancedPipelineOrchestrator

# Initialize enhanced orchestrator
orchestrator = EnhancedPipelineOrchestrator(config)
await orchestrator.initialize_advanced_features()

# Process with advanced recovery
result = await orchestrator.process_block_with_recovery(block)
```

#### **Distributed Coordination**
- **Multi-Instance Support**: Coordinate across multiple orchestrator instances
- **Load Balancing**: Distribute processing across available instances
- **State Synchronization**: Keep state consistent across instances

#### **Comprehensive Monitoring**
- **Processing Metrics**: Track processing performance and success rates
- **Error Tracking**: Monitor and analyze processing errors
- **Resource Usage**: Monitor CPU, memory, and disk usage

## **USAGE EXAMPLES**

### **Basic Advanced Processing**

```python
import asyncio
from core.pipeline import EnhancedPipelineOrchestrator
from core.utils.config_loader import load_pipeline_config

async def main():
    # Load configuration
    config = load_pipeline_config(environment="production")
    
    # Initialize enhanced orchestrator
    orchestrator = EnhancedPipelineOrchestrator(config)
    await orchestrator.initialize_advanced_features()
    
    # Create processing block
    block = orchestrator.create_processing_block(block_end_time, ms_files)
    
    # Process with advanced features
    result = await orchestrator.process_block_with_recovery(block)
    
    # Get processing status
    status = await orchestrator.get_processing_status(block.block_id)
    
    # Get error recovery status
    recovery_status = await orchestrator.get_error_recovery_status()
    
    # Clean up
    await orchestrator.cleanup_advanced_features()

asyncio.run(main())
```

### **Monitoring and Alerting**

```python
from monitoring.advanced_monitoring import AdvancedMonitor, MonitoringDashboard

async def setup_monitoring():
    # Initialize monitor
    monitor = AdvancedMonitor()
    
    # Add threshold rules
    await monitor.add_threshold_rule(ThresholdRule(
        name="high_failure_rate",
        metric_name="block_failure_rate",
        operator=">",
        threshold_value=0.5,
        alert_level=AlertLevel.ERROR,
        duration=120
    ))
    
    # Start monitoring
    monitor_task = asyncio.create_task(monitor.start())
    
    # Start dashboard
    dashboard = MonitoringDashboard(monitor, port=8080)
    dashboard_task = asyncio.create_task(dashboard.start())
    
    return monitor, dashboard
```

### **Distributed Processing**

```python
async def distributed_processing():
    # Initialize orchestrator
    orchestrator = EnhancedPipelineOrchestrator(config)
    await orchestrator.initialize_advanced_features()
    
    # Process multiple blocks concurrently
    blocks = [create_block(i) for i in range(5)]
    tasks = [orchestrator.process_block_with_recovery(block) for block in blocks]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Get all processing statuses
    all_statuses = await orchestrator.get_all_processing_statuses()
    
    return results
```

## **INFRASTRUCTURE REQUIREMENTS**

### **Redis Server**
- **Version**: Redis 6.0 or later
- **Configuration**: Enable persistence and clustering for production
- **Memory**: Allocate sufficient memory for state and message storage

```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server

# Test connection
redis-cli ping
```

### **Python Dependencies**
```bash
# Install additional dependencies for Phase 3 features
pip install redis aiohttp aiohttp-cors
```

### **Production Configuration**
```yaml
# config/environments/production.yaml
redis:
  url: "redis://redis-cluster:6379"
  namespace: "dsa110_pipeline_prod"
  connection_pool_size: 20
  socket_timeout: 5
  socket_connect_timeout: 5

monitoring:
  dashboard_port: 8080
  metrics_retention_hours: 168  # 7 days
  alert_retention_hours: 72     # 3 days

error_recovery:
  default_circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
    success_threshold: 2
  default_retry:
    max_attempts: 3
    base_delay: 1.0
    max_delay: 60.0
```

## **MONITORING DASHBOARD**

### **Accessing the Dashboard**
1. Start the monitoring system
2. Open browser to `http://localhost:8080`
3. View real-time pipeline status

### **Dashboard Features**
- **Health Status**: Overview of all services
- **Active Alerts**: Current alerts with severity levels
- **Metrics**: Real-time performance metrics
- **Processing Status**: Current and recent processing blocks
- **Error Recovery**: Circuit breaker and retry status

### **API Endpoints**
- `GET /api/health` - Health status
- `GET /api/metrics` - Metrics data
- `GET /api/alerts` - Active alerts
- `GET /api/dashboard` - Dashboard HTML

## **TROUBLESHOOTING**

### **Common Issues**

#### **Redis Connection Errors**
```bash
# Check Redis status
sudo systemctl status redis-server

# Check Redis logs
sudo journalctl -u redis-server

# Test connection
redis-cli ping
```

#### **Circuit Breaker Issues**
```python
# Check circuit breaker status
recovery_status = await orchestrator.get_error_recovery_status()
print(recovery_status['circuit_breakers'])

# Reset circuit breaker
await orchestrator.reset_circuit_breaker("calibration")
```

#### **Message Queue Issues**
```python
# Check queue status
queue_manager = get_message_queue_manager()
queue = await queue_manager.get_queue("processing_events")
length = await queue.get_queue_length("processing_events")
print(f"Queue length: {length}")
```

### **Performance Tuning**

#### **Redis Optimization**
- Increase memory limits
- Configure persistence settings
- Use Redis clustering for high availability

#### **Monitoring Optimization**
- Adjust metric retention periods
- Configure alert thresholds
- Optimize dashboard refresh rates

## **DEPLOYMENT**

### **Production Deployment**
1. **Setup Redis Cluster**: Configure Redis for high availability
2. **Configure Monitoring**: Set up alerting and dashboards
3. **Deploy Services**: Deploy pipeline services with advanced features
4. **Monitor Health**: Use dashboard to monitor system health

### **Scaling Considerations**
- **Horizontal Scaling**: Deploy multiple orchestrator instances
- **Load Balancing**: Distribute processing across instances
- **State Management**: Use Redis clustering for state storage
- **Monitoring**: Scale monitoring infrastructure with pipeline

## **BENEFITS**

### **Reliability**
- **Fault Tolerance**: Circuit breakers prevent cascading failures
- **Automatic Recovery**: Retry mechanisms handle transient failures
- **State Persistence**: Distributed state survives service restarts

### **Observability**
- **Real-Time Monitoring**: Live dashboard with key metrics
- **Comprehensive Alerting**: Proactive notification of issues
- **Failure Analysis**: Detailed failure tracking and analysis

### **Scalability**
- **Distributed Processing**: Scale across multiple instances
- **Message Queuing**: Decouple services for better scalability
- **State Management**: Shared state enables coordination

### **Maintainability**
- **Centralized Monitoring**: Single dashboard for all services
- **Automated Recovery**: Reduce manual intervention
- **Comprehensive Logging**: Detailed logs for debugging

The Phase 3 features transform the DSA-110 pipeline into a production-ready, enterprise-grade system with advanced reliability, observability, and scalability capabilities.

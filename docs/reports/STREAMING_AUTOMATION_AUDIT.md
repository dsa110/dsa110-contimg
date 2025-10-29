# DSA-110 Streaming Pipeline: Automation Audit & Recommendations

**Date:** 2025-10-24  
**Purpose:** Architectural review for fully automated streaming operations with minimal human intervention

## Executive Summary

The pipeline is well-designed for streaming operations with good fault tolerance. This audit identifies opportunities to enhance automation, reliability, and observability for lights-out operations.

##Changes Implemented

### 1. ✓ tmpfs Staging Now Default (COMPLETED)

**Change:** Made `--stage-to-tmpfs` default to `True` in conversion orchestrator

**File:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`

**Rationale:**
- System has 47GB tmpfs (plenty of headroom for typical 5-10GB MS files)
- 3-5x I/O performance improvement over SSD-only
- Conservative 2× safety margin prevents OOM
- Explicit `--no-stage-to-tmpfs` flag available if needed

**Impact:** Maximum throughput for real-time streaming with automatic fallback to SSD

---

## Architectural Recommendations for Full Automation

### Priority 1: Critical for Lights-Out Operation

#### 1.1 Automatic Calibrator Selection & Fallback

**Current State:**
- Imaging worker skips MS if no caltables found (`status='skipped_no_caltables'`)
- No automatic calibrator identification
- Manual calibrator observation scheduling

**Recommendation:**
```python
# In imaging/worker.py - add calibrator fallback chain
def get_or_create_caltables(ms_path, mid_mjd, registry_db, cal_catalog_db):
    """
    Priority chain:
    1. Check registry for active caltables within time window
    2. If none, find nearest calibrator transit from catalog
    3. Auto-schedule calibrator observation if gap > threshold
    4. Use last-known-good caltables with staleness warning
    """
    applylist = get_active_applylist(registry_db, mid_mjd)
    if applylist:
        return applylist
    
    # Fallback: find nearest calibrator
    nearest_cal = find_nearest_calibrator_observation(mid_mjd, threshold_hours=6)
    if nearest_cal:
        logger.warning(f"Using calibrator from {nearest_cal.age_hours}h ago")
        return nearest_cal.caltables
    
    # Last resort: use last known good
    last_good = get_last_valid_caltables(registry_db)
    if last_good:
        logger.error(f"Using stale caltables from {last_good.age_hours}h ago")
        return last_good.caltables
    
    raise RuntimeError("No calibration solutions available")
```

**Implementation:**
- Add `calibrator_scheduler.py` module
- Track calibrator transit times from VLA/NVSS catalogs
- Auto-trigger calibrator observations when validity window expires
- Add staleness metrics to API

#### 1.2 Intelligent Retry with Backoff

**Current State:**
- Queue has `retry_count` field but basic retry logic
- No exponential backoff
- No error classification (transient vs permanent)

**Recommendation:**
```python
# Enhanced retry strategy in streaming_converter.py
RETRY_STRATEGIES = {
    "disk_full": {"max_retries": 3, "backoff": "exponential", "base_delay": 300},
    "casa_timeout": {"max_retries": 5, "backoff": "exponential", "base_delay": 60},
    "memory_error": {"max_retries": 2, "backoff": "linear", "base_delay": 600},
    "corrupt_input": {"max_retries": 0, "backoff": None, "action": "quarantine"},
    "missing_calibration": {"max_retries": 10, "backoff": "constant", "base_delay": 1800},
}

def should_retry(error_type, retry_count):
    strategy = RETRY_STRATEGIES.get(error_type, DEFAULT_STRATEGY)
    if retry_count >= strategy["max_retries"]:
        return False, None
    
    if strategy["backoff"] == "exponential":
        delay = strategy["base_delay"] * (2 ** retry_count)
    elif strategy["backoff"] == "linear":
        delay = strategy["base_delay"] * (retry_count + 1)
    else:
        delay = strategy["base_delay"]
    
    return True, delay
```

**Implementation:**
- Add error classification in queue DB
- Implement backoff scheduler
- Add `error_category` column to `ingest_queue`
- Quarantine corrupt files to separate directory

#### 1.3 Self-Healing Mechanisms

**Current State:**
- Manual intervention required for stuck processes
- No automatic resource cleanup
- Limited health monitoring

**Recommendation:**

**A. Watchdog for Stuck Conversions**
```python
# Add to streaming_converter.py monitoring thread
def check_stuck_jobs(queue_db, timeout_minutes=30):
    """Detect and recover from stuck conversions"""
    stuck = queue_db.get_stuck_jobs(timeout_minutes)
    for job in stuck:
        logger.error(f"Job {job.group_id} stuck for {job.age_minutes}m")
        
        # Check if process is alive
        if job.pid and not psutil.pid_exists(job.pid):
            logger.info(f"Dead process detected, resetting {job.group_id}")
            queue_db.reset_job(job.group_id)
            continue
        
        # Check if tmpfs is full
        if shutil.disk_usage("/dev/shm").free < MIN_TMPFS_FREE:
            logger.warning("tmpfs full, cleaning up old staged files")
            cleanup_tmpfs_staging()
        
        # Force kill and retry
        if job.age_minutes > 2 * timeout_minutes:
            logger.error(f"Killing stuck job {job.group_id}")
            kill_job_process(job.pid)
            queue_db.mark_failed(job.group_id, "timeout_killed")
```

**B. Automatic Disk Space Management**
```python
def enforce_retention_policy(output_dir, products_db, min_free_gb=100):
    """Auto-cleanup old MS files when disk fills"""
    du = shutil.disk_usage(output_dir)
    if du.free / (1024**3) < min_free_gb:
        logger.warning(f"Low disk space: {du.free / (1024**3):.1f}GB free")
        
        # Find old, already-imaged MS files
        candidates = products_db.get_old_completed_ms(age_days=7)
        for ms_path, age_days in candidates:
            if du.free / (1024**3) >= min_free_gb:
                break
            logger.info(f"Archiving {ms_path} (age: {age_days}d)")
            archive_and_delete(ms_path)
            du = shutil.disk_usage(output_dir)
```

**Implementation:**
- Add `stuck_job_monitor` thread to streaming converter
- Implement PID tracking in queue DB
- Add retention policy configuration to `contimg.env`
- Create archive mechanism (compress + move to cold storage)

#### 1.4 Comprehensive Alerting

**Current State:**
- Logging to files/journald
- No proactive alerting
- Manual log monitoring required

**Recommendation:**

**A. Alert Conditions**
```python
ALERT_CONDITIONS = {
    "critical": [
        "No calibration tables for > 6 hours",
        "Conversion failure rate > 20% over 1 hour",
        "Disk space < 50GB",
        "Queue depth > 100 groups",
        "API endpoint down",
        "tmpfs full (> 95%)",
    ],
    "warning": [
        "Calibration tables > 3 hours old",
        "Conversion failure rate > 10% over 1 hour",
        "Disk space < 200GB",
        "Queue depth > 50 groups",
        "Single group retry count > 3",
    ],
    "info": [
        "New calibration tables registered",
        "Successful mosaic completion",
        "Queue fully processed (depth = 0)",
    ],
}
```

**B. Alert Channels**
```python
# Add alerting module: utils/alerting.py
class AlertManager:
    def __init__(self, config):
        self.channels = {
            "slack": SlackChannel(config.slack_webhook) if config.slack_webhook else None,
            "email": EmailChannel(config.smtp_config) if config.smtp_config else None,
            "pagerduty": PagerDutyChannel(config.pd_key) if config.pd_key else None,
            "grafana": GrafanaChannel(config.grafana_url) if config.grafana_url else None,
        }
    
    def send_alert(self, severity, message, context=None):
        for name, channel in self.channels.items():
            if channel and channel.enabled_for_severity(severity):
                channel.send(severity, message, context)
```

**Implementation:**
- Add `CONTIMG_ALERT_WEBHOOK` to environment
- Integrate with monitoring thread
- Add `/api/alerts` endpoint for query/acknowledge
- Support multiple channels (Slack, email, PagerDuty)

---

### Priority 2: Enhanced Observability

#### 2.1 Prometheus Metrics Export

**Recommendation:**
```python
# Add to api/routes.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Metrics
conversion_duration = Histogram('contimg_conversion_duration_seconds', 
                                'Time to convert UVH5 group',
                                buckets=[10, 30, 60, 120, 300, 600, 1200])
calibration_duration = Histogram('contimg_calibration_duration_seconds',
                                 'Time to calibrate MS')
imaging_duration = Histogram('contimg_imaging_duration_seconds',
                            'Time to produce image')
queue_depth = Gauge('contimg_queue_depth', 'Number of pending groups')
active_conversions = Gauge('contimg_active_conversions', 'Groups in progress')
failure_rate = Counter('contimg_failures_total', 'Total failures', ['stage', 'error_type'])
tmpfs_usage_bytes = Gauge('contimg_tmpfs_usage_bytes', 'tmpfs utilization')

@app.get("/metrics")
def metrics():
    """Prometheus-compatible metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")
```

**Implementation:**
- Add `prometheus-client` dependency
- Instrument all major operations
- Configure Grafana dashboards
- Set up retention policies

#### 2.2 Distributed Tracing

**Recommendation:**
```python
# Add OpenTelemetry spans for end-to-end tracing
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("convert_group")
def process_group(group_id):
    with tracer.start_as_current_span("read_uvh5"):
        uvdata = read_subbands(group_id)
    
    with tracer.start_as_current_span("write_ms"):
        ms_path = write_ms(uvdata)
    
    with tracer.start_as_current_span("calibrate"):
        caltables = calibrate_ms(ms_path)
    
    return ms_path, caltables
```

**Implementation:**
- Add OpenTelemetry instrumentation
- Deploy Jaeger or Tempo for trace collection
- Add trace IDs to all log messages
- Correlate traces with queue entries

---

### Priority 3: Operational Resilience

#### 3.1 Configuration Hot-Reload

**Current State:**
- Requires service restart for config changes
- No dynamic parameter adjustment

**Recommendation:**
```python
# Add config watcher in streaming_converter.py
class ConfigWatcher:
    def __init__(self, config_path):
        self.config_path = config_path
        self.last_mtime = 0
        self.reload_callbacks = []
    
    def check_for_updates(self):
        current_mtime = os.path.getmtime(self.config_path)
        if current_mtime > self.last_mtime:
            logger.info("Config file changed, reloading...")
            new_config = load_config(self.config_path)
            for callback in self.reload_callbacks:
                callback(new_config)
            self.last_mtime = current_mtime
    
    def register_callback(self, func):
        self.reload_callbacks.append(func)
```

**Implementation:**
- Add config reload endpoint: `POST /api/admin/reload-config`
- Support hot-reload for non-critical settings (log level, thresholds)
- Validate config before applying
- Log all config changes

#### 3.2 Blue-Green Deployments

**Recommendation:**
```bash
# Deployment strategy for zero-downtime updates
./ops/scripts/deploy.sh --strategy=blue-green

# Steps:
# 1. Deploy new version as "green" service
# 2. Run health checks
# 3. Switch load balancer to green
# 4. Drain blue service queue
# 5. Stop blue service
# 6. Promote green to blue for next deployment
```

**Implementation:**
- Add deployment automation scripts
- Implement graceful shutdown (drain queue first)
- Add API readiness/liveness probes
- Support rolling updates for API service

#### 3.3 Backup & Disaster Recovery

**Current State:**
- No automated backups
- Manual DB management
- No documented recovery procedures

**Recommendation:**

**A. Automated Backups**
```bash
# Add to cron: /etc/cron.daily/contimg-backup
#!/bin/bash
BACKUP_DIR=/data/backups/contimg/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup SQLite databases
sqlite3 /data/dsa110-contimg/state/ingest.sqlite3 ".backup $BACKUP_DIR/ingest.sqlite3"
sqlite3 /data/dsa110-contimg/state/cal_registry.sqlite3 ".backup $BACKUP_DIR/cal_registry.sqlite3"
sqlite3 /data/dsa110-contimg/state/products.sqlite3 ".backup $BACKUP_DIR/products.sqlite3"

# Backup critical calibration tables (recent 7 days)
find /scratch/dsa110-contimg/ms -name "*cal" -mtime -7 -exec cp -r {} $BACKUP_DIR/caltables/ \;

# Compress and ship to remote storage
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rclone copy $BACKUP_DIR.tar.gz remote:dsa110-backups/

# Cleanup old local backups (keep 14 days)
find /data/backups/contimg -type d -mtime +14 -exec rm -rf {} \;
```

**B. Recovery Procedures**
```markdown
### Recovery Scenarios

**Scenario 1: Queue DB Corruption**
1. Stop streaming service: `systemctl stop contimg-stream`
2. Restore DB: `cp /data/backups/contimg/latest/ingest.sqlite3 /data/dsa110-contimg/state/`
3. Bootstrap from incoming files: `--bootstrap-directory /data/incoming/`
4. Restart service: `systemctl start contimg-stream`

**Scenario 2: Lost Calibration Tables**
1. Restore from backup: `rclone sync remote:dsa110-backups/latest/caltables/ /scratch/dsa110-contimg/ms/`
2. Re-register in cal_registry: `python -m dsa110_contimg.database.registry_cli scan-and-register`
3. Verify active tables: `python -m dsa110_contimg.database.registry_cli active --mjd <current_mjd>`

**Scenario 3: Full System Recovery**
1. Restore all databases from backup
2. Restore recent caltables
3. Clear queue of incomplete conversions
4. Restart all services
5. Bootstrap queue from /data/incoming/
6. Monitor for 1 hour to ensure stable operation
```

**Implementation:**
- Add backup scripts to `ops/scripts/`
- Document recovery in `docs/operations/disaster-recovery.md`
- Test recovery procedures monthly
- Set up monitoring for backup success/failure

---

### Priority 4: Performance Optimization

#### 4.1 Parallel Pipeline Stages

**Current State:**
- Sequential: convert → calibrate → image
- Single conversion at a time in streaming mode

**Recommendation:**
```python
# Pipeline parallelization in streaming_converter.py
class PipelineStageManager:
    def __init__(self, max_concurrent_conversions=2, max_concurrent_images=4):
        self.conversion_pool = ThreadPoolExecutor(max_concurrent_conversions)
        self.imaging_pool = ThreadPoolExecutor(max_concurrent_images)
        self.calibration_queue = Queue()
    
    def process_pipeline(self, group_id):
        # Stage 1: Conversion (I/O bound, limit concurrency)
        future_ms = self.conversion_pool.submit(convert_group, group_id)
        
        # Stage 2: Calibration (CPU bound, can run while converting next group)
        ms_path = future_ms.result()
        if is_calibrator(ms_path):
            caltables = calibrate(ms_path)
            register_caltables(caltables)
        
        # Stage 3: Imaging (CPU + I/O bound, highly parallel)
        self.imaging_pool.submit(apply_and_image, ms_path)
```

**Implementation:**
- Add concurrent conversion support (respect tmpfs limits)
- Parallelize imaging across multiple MS files
- Add resource throttling (CPU, memory, disk I/O)
- Monitor resource contention

#### 4.2 Caching & Precomputation

**Recommendation:**
```python
# Cache frequently accessed data
@lru_cache(maxsize=128)
def get_nvss_sources_in_fov(ra_deg, dec_deg, radius_deg):
    """Cache NVSS catalog queries"""
    return query_nvss_catalog(ra_deg, dec_deg, radius_deg)

@lru_cache(maxsize=32)
def get_primary_beam_model(freq_hz):
    """Cache beam models"""
    return load_beam_model(freq_hz)

# Precompute common calibrator models
def build_calibrator_model_cache():
    """Precompute models for common calibrators"""
    for cal in STANDARD_CALIBRATORS:
        model = build_component_list(cal)
        cache.set(f"cal_model_{cal.name}", model)
```

**Implementation:**
- Add Redis or in-memory cache
- Precompute calibrator models at startup
- Cache catalog queries
- Add cache hit/miss metrics

---

## Implementation Roadmap

### Phase 1: Critical Automation (Weeks 1-2)
- [ ] Deploy tmpfs staging as default
- [ ] Implement automatic calibrator fallback
- [ ] Add intelligent retry with error classification
- [ ] Set up basic alerting (Slack webhook)
- [ ] Add stuck job watchdog

### Phase 2: Observability (Weeks 3-4)
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Enhanced logging with trace IDs
- [ ] API metrics endpoints
- [ ] Alert manager integration

### Phase 3: Resilience (Weeks 5-6)
- [ ] Automated backup system
- [ ] Disaster recovery documentation
- [ ] Configuration hot-reload
- [ ] Graceful shutdown handling
- [ ] Health check endpoints

### Phase 4: Optimization (Weeks 7-8)
- [ ] Parallel pipeline stages
- [ ] Catalog caching
- [ ] Distributed tracing
- [ ] Performance profiling
- [ ] Resource optimization

---

## Success Metrics

### Automation Goals
- **Zero-touch operation:** 99.5% of observations processed without human intervention
- **Recovery time:** < 5 minutes for automatic recovery from transient failures
- **Calibration coverage:** > 95% of observations have valid caltables within 6 hours

### Reliability Goals
- **Conversion success rate:** > 99%
- **Imaging success rate:** > 95% (excluding missing calibration cases)
- **Uptime:** > 99.9% for streaming service
- **Data loss:** 0% (all ingested data eventually processed or quarantined with reason)

### Performance Goals
- **End-to-end latency:** < 10 minutes from file arrival to image product
- **Queue depth:** < 10 groups during normal operations
- **Resource utilization:** CPU < 80%, Memory < 75%, Disk I/O < 60%

---

## Monitoring Dashboard Requirements

### Real-Time View
- Queue depth trend (last 24h)
- Active conversions / imaging jobs
- Success/failure rates by stage
- System resource utilization
- Calibration table freshness
- Alert status

### Historical Analysis
- Processing throughput (groups/hour)
- Failure distribution by error type
- Performance trends (latency percentiles)
- Resource usage patterns
- Data volume trends

### Alert Status
- Active alerts by severity
- Alert history (last 7 days)
- Acknowledged vs unacknowledged
- Time to resolution
- False positive rate

---

## Configuration Management

### Recommended Environment Variables (Add to contimg.env)
```bash
# Automation
CONTIMG_AUTO_CALIBRATOR_FALLBACK=true
CONTIMG_CALIBRATOR_STALENESS_HOURS=6
CONTIMG_MAX_RETRY_ATTEMPTS=5
CONTIMG_STUCK_JOB_TIMEOUT_MINUTES=30

# Alerting
CONTIMG_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
CONTIMG_ALERT_CRITICAL_EMAIL=ops@dsa110.example.com
CONTIMG_ALERT_LEVEL=warning

# Resource Management
CONTIMG_MIN_FREE_DISK_GB=100
CONTIMG_TMPFS_MIN_FREE_PERCENT=20
CONTIMG_MAX_CONCURRENT_CONVERSIONS=2
CONTIMG_MAX_CONCURRENT_IMAGES=4

# Retention
CONTIMG_MS_RETENTION_DAYS=7
CONTIMG_IMAGE_RETENTION_DAYS=30
CONTIMG_LOG_RETENTION_DAYS=14

# Performance
CONTIMG_ENABLE_CACHING=true
CONTIMG_CACHE_TTL_SECONDS=3600
CONTIMG_PARALLEL_IMAGING=true
```

---

## Conclusion

The DSA-110 pipeline has a solid foundation for streaming operations. Implementing these recommendations will significantly enhance automation, reduce operational burden, and improve reliability for lights-out operations.

**Immediate Actions:**
1. ✓ Enable tmpfs staging by default (DONE)
2. Implement automatic calibrator fallback
3. Set up basic alerting
4. Add stuck job recovery
5. Document disaster recovery procedures

**Next Steps:**
1. Review and prioritize recommendations with operations team
2. Establish success metrics baseline
3. Implement Phase 1 changes
4. Monitor and iterate based on operational experience


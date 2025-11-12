# Pipeline Robustness Analysis & Recommendations

**Date:** 2025-01-XX  
**Purpose:** Comprehensive analysis of pipeline robustness with actionable recommendations

---

## Executive Summary

The DSA-110 continuum imaging pipeline has a solid foundation with quality assurance, retry logic, and state management. However, several areas need strengthening for production-grade robustness:

**Critical Gaps:**
1. **Incomplete error classification** - Not all errors are properly categorized as retryable vs. fatal
2. **Limited transaction boundaries** - Multi-step operations lack atomicity guarantees
3. **Resource exhaustion handling** - Disk space, memory, and file handle limits not proactively managed
4. **Partial failure recovery** - Intermediate artifacts not cleaned up on failure
5. **Calibration fallback strategy** - No automatic fallback when calibrator fails
6. **Validation gaps** - Some checks are optional rather than mandatory gates

**Strengths:**
- Quality assurance framework exists
- Retry logic for file I/O operations
- State machine with checkpointing
- Alerting infrastructure
- Database-backed queue persistence

---

## 1. Error Handling & Classification

### Current State

**What Works:**
- Basic retry logic in `direct_subband.py` for concat operations
- Error classification for file I/O errors (retryable vs. fatal)
- Exception handling in job runner with status updates

**Gaps:**

1. **Incomplete Error Taxonomy**
   - Only file I/O errors are classified
   - CASA task failures not categorized
   - Calibration failures not classified by recoverability
   - Network/storage errors not distinguished

2. **No Error Context Propagation**
   - Errors lose context as they bubble up
   - No structured error metadata (stage, input files, parameters)
   - Recovery hints not consistently provided

3. **Silent Failures**
   - Some operations catch exceptions but don't log adequately
   - Validation failures may not trigger alerts
   - Partial writes not detected

### Recommendations

**1.1 Implement Comprehensive Error Classification**

```python
# src/dsa110_contimg/utils/error_classification.py

class ErrorCategory(Enum):
    RETRYABLE = "retryable"      # Transient, can retry
    RECOVERABLE = "recoverable"  # Can recover with different approach
    FATAL = "fatal"              # Cannot proceed, requires intervention
    VALIDATION = "validation"    # Data quality issue, skip this item

class ErrorClassifier:
    """Classify errors by category and provide recovery strategies."""
    
    @staticmethod
    def classify(error: Exception, context: dict) -> ErrorCategory:
        """Classify error and return category."""
        error_msg = str(error).lower()
        error_type = type(error).__name__
        
        # File I/O errors (retryable)
        if any(term in error_msg for term in ['lock', 'cannot be opened', 'readblock']):
            return ErrorCategory.RETRYABLE
        
        # CASA task errors (context-dependent)
        if error_type == 'CASAToolError':
            if 'disk space' in error_msg or 'permission' in error_msg:
                return ErrorCategory.RETRYABLE
            if 'corrupted' in error_msg or 'invalid' in error_msg:
                return ErrorCategory.FATAL
        
        # Calibration errors
        if 'calibration' in context.get('stage', '').lower():
            if 'low snr' in error_msg or 'flagged' in error_msg:
                return ErrorCategory.RECOVERABLE  # Try different calibrator
            if 'model_data' in error_msg:
                return ErrorCategory.RECOVERABLE  # Try different model
        
        # Validation errors (skip this item, continue pipeline)
        if error_type in ['ValidationError', 'QualityError']:
            return ErrorCategory.VALIDATION
        
        # Default: fatal if unknown
        return ErrorCategory.FATAL
```

**1.2 Add Structured Error Context**

```python
@dataclass
class PipelineError:
    """Structured error with full context."""
    category: ErrorCategory
    stage: str
    operation: str
    error: Exception
    context: dict
    recovery_hint: Optional[str] = None
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """Serialize for logging/database."""
        return {
            'category': self.category.value,
            'stage': self.stage,
            'operation': self.operation,
            'error_type': type(self.error).__name__,
            'error_msg': str(self.error),
            'context': self.context,
            'recovery_hint': self.recovery_hint,
            'retry_count': self.retry_count,
            'timestamp': self.timestamp,
        }
```

**1.3 Implement Error Recovery Strategies**

```python
class ErrorRecovery:
    """Execute recovery strategies based on error category."""
    
    @staticmethod
    def recover(error: PipelineError, pipeline_state: dict) -> bool:
        """Attempt recovery, return True if successful."""
        
        if error.category == ErrorCategory.RETRYABLE:
            return ErrorRecovery._retry_with_backoff(error, pipeline_state)
        
        elif error.category == ErrorCategory.RECOVERABLE:
            return ErrorRecovery._try_alternative_approach(error, pipeline_state)
        
        elif error.category == ErrorCategory.VALIDATION:
            return ErrorRecovery._skip_and_continue(error, pipeline_state)
        
        else:  # FATAL
            return False
    
    @staticmethod
    def _retry_with_backoff(error: PipelineError, state: dict) -> bool:
        """Retry with exponential backoff."""
        max_retries = state.get('max_retries', 3)
        if error.retry_count >= max_retries:
            return False
        
        wait_time = min(2 ** error.retry_count, 60)  # Cap at 60s
        time.sleep(wait_time)
        return True  # Caller should retry operation
```

---

## 2. Transaction Boundaries & Atomicity

### Current State

**What Works:**
- Queue state updates are transactional (SQLite)
- Checkpoint files for conversion progress

**Gaps:**

1. **Multi-Step Operations Not Atomic**
   - Conversion → Calibration → Imaging not atomic
   - If calibration fails, MS may be left in inconsistent state
   - Partial calibration tables not cleaned up
   - Images created but not registered if final step fails

2. **File System Operations Not Atomic**
   - MS writes can leave partial files on failure
   - Calibration table writes not atomic
   - Image products not atomically created

3. **Database Inconsistencies**
   - Products DB may reference files that don't exist
   - Queue state may not match filesystem state
   - Calibration registry may have orphaned entries

### Recommendations

**2.1 Implement Two-Phase Commit Pattern**

```python
class AtomicPipelineStage:
    """Ensure atomicity of multi-step pipeline stages."""
    
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.artifacts = []  # Files created during stage
        self.db_updates = []  # DB operations to commit
        self.rollback_actions = []  # Actions to undo on failure
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
            return False  # Re-raise exception
        else:
            self.commit()
            return True
    
    def add_artifact(self, path: Path, cleanup_on_rollback: bool = True):
        """Register an artifact created during stage."""
        self.artifacts.append(path)
        if cleanup_on_rollback:
            self.rollback_actions.append(lambda: self._cleanup_artifact(path))
    
    def add_db_update(self, conn, query: str, params: tuple):
        """Register a DB update to commit atomically."""
        self.db_updates.append((conn, query, params))
    
    def commit(self):
        """Commit all changes atomically."""
        # 1. Commit all DB updates
        for conn, query, params in self.db_updates:
            conn.execute(query, params)
            conn.commit()
        
        # 2. Clear rollback actions (success, no rollback needed)
        self.rollback_actions = []
    
    def rollback(self):
        """Rollback all changes on failure."""
        # Execute rollback actions in reverse order
        for action in reversed(self.rollback_actions):
            try:
                action()
            except Exception as e:
                logger.error(f"Rollback action failed: {e}")
        
        # Rollback DB updates (if using transactions)
        for conn, _, _ in self.db_updates:
            try:
                conn.rollback()
            except Exception:
                pass
```

**2.2 Use Temporary Files + Atomic Moves**

```python
def write_ms_atomically(ms_path: Path, writer_func):
    """Write MS atomically using temp file + atomic move."""
    temp_path = ms_path.with_suffix('.ms.tmp')
    
    try:
        # Write to temp location
        writer_func(temp_path)
        
        # Validate before moving
        validate_ms_basic(temp_path)
        
        # Atomic move
        temp_path.rename(ms_path)
        
    except Exception:
        # Cleanup temp file on failure
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)
        raise
```

**2.3 Database Transaction Wrappers**

```python
@contextmanager
def db_transaction(conn: sqlite3.Connection):
    """Ensure DB operations are transactional."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

---

## 3. Resource Management

### Current State

**What Works:**
- tmpfs staging with fallback to SSD
- Basic disk space checks in some operations

**Gaps:**

1. **No Proactive Resource Monitoring**
   - Disk space not checked before operations
   - Memory usage not monitored
   - File handle limits not tracked
   - tmpfs capacity not verified before staging

2. **Resource Exhaustion Not Handled**
   - Operations fail mid-way when disk fills
   - No cleanup of partial files on disk full
   - No graceful degradation when resources low

3. **No Resource Quotas**
   - No limits on concurrent operations
   - No per-stage resource budgets
   - No prioritization of operations

### Recommendations

**3.1 Implement Resource Preflight Checks**

```python
class ResourceManager:
    """Manage and monitor system resources."""
    
    @staticmethod
    def check_disk_space(path: Path, required_gb: float) -> bool:
        """Check if sufficient disk space available."""
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024**3)
        
        if free_gb < required_gb * 1.2:  # 20% safety margin
            raise ResourceError(
                f"Insufficient disk space: {free_gb:.1f} GB free, "
                f"{required_gb:.1f} GB required"
            )
        return True
    
    @staticmethod
    def check_tmpfs_capacity(required_gb: float) -> bool:
        """Check tmpfs capacity before staging."""
        tmpfs_path = Path("/dev/shm")
        if not tmpfs_path.exists():
            return False
        
        stat = shutil.disk_usage(tmpfs_path)
        free_gb = stat.free / (1024**3)
        
        if free_gb < required_gb * 1.2:
            logger.warning(
                f"tmpfs capacity low: {free_gb:.1f} GB free, "
                f"{required_gb:.1f} GB required. Falling back to SSD."
            )
            return False
        return True
    
    @staticmethod
    def estimate_ms_size(num_subbands: int, duration_min: float) -> float:
        """Estimate MS size in GB."""
        # Rough estimate: ~1 GB per subband per 5 minutes
        base_size_gb = 1.0
        return base_size_gb * num_subbands * (duration_min / 5.0)
```

**3.2 Add Resource Monitoring**

```python
class ResourceMonitor:
    """Monitor resource usage and trigger alerts."""
    
    def __init__(self, alert_thresholds: dict):
        self.thresholds = alert_thresholds
    
    def check_resources(self) -> dict:
        """Check all resources and return status."""
        status = {
            'disk_free_gb': self._get_disk_free(),
            'memory_percent': self._get_memory_usage(),
            'tmpfs_free_gb': self._get_tmpfs_free(),
            'file_handles': self._get_file_handle_usage(),
        }
        
        # Check thresholds and alert
        if status['disk_free_gb'] < self.thresholds['disk_warning_gb']:
            alerting.warning(
                "system",
                f"Low disk space: {status['disk_free_gb']:.1f} GB free",
                context=status
            )
        
        return status
```

**3.3 Implement Resource Quotas**

```python
class ResourceQuota:
    """Enforce resource quotas per operation."""
    
    def __init__(self, max_concurrent: int = 4):
        self.semaphore = threading.Semaphore(max_concurrent)
        self.active_operations = {}
    
    @contextmanager
    def acquire(self, operation_id: str, resource_budget: dict):
        """Acquire resources for an operation."""
        self.semaphore.acquire()
        try:
            self.active_operations[operation_id] = resource_budget
            yield
        finally:
            self.semaphore.release()
            self.active_operations.pop(operation_id, None)
```

---

## 4. Calibration Robustness

### Current State

**What Works:**
- Calibration registry tracks validity windows
- Quality checks for calibration tables

**Gaps:**

1. **No Automatic Calibrator Fallback**
   - If primary calibrator fails, pipeline stops
   - No fallback to secondary calibrator
   - No fallback to last-known-good calibration

2. **Calibration Validity Not Enforced**
   - Old calibration tables may be used
   - No automatic recalibration when validity expires
   - No warning when using stale calibration

3. **Calibration Quality Gates Not Enforced**
   - Low-quality calibration may proceed
   - No automatic rejection of poor solutions
   - No retry with different parameters

### Recommendations

**4.1 Implement Calibrator Fallback Chain**

```python
class CalibratorSelector:
    """Select calibrator with fallback chain."""
    
    def __init__(self, cal_registry_db: Path):
        self.registry_db = cal_registry_db
    
    def select_calibrator(
        self,
        ms_path: Path,
        time_mjd: float,
        fallback_chain: List[str] = None
    ) -> Optional[dict]:
        """Select calibrator with automatic fallback."""
        
        if fallback_chain is None:
            fallback_chain = self._get_default_fallback_chain()
        
        for cal_name in fallback_chain:
            cal = self._try_calibrator(ms_path, time_mjd, cal_name)
            if cal:
                return cal
        
        # Last resort: use most recent valid calibration
        return self._get_last_known_good(time_mjd)
    
    def _try_calibrator(
        self,
        ms_path: Path,
        time_mjd: float,
        cal_name: str
    ) -> Optional[dict]:
        """Try to use a specific calibrator."""
        try:
            # Check if calibrator is in FoV
            if not self._calibrator_in_fov(ms_path, cal_name):
                return None
            
            # Check if valid calibration exists
            cal_tables = self._get_valid_caltables(cal_name, time_mjd)
            if not cal_tables:
                return None
            
            # Validate calibration quality
            if not self._validate_calibration_quality(cal_tables):
                return None
            
            return {
                'calibrator': cal_name,
                'caltables': cal_tables,
                'valid_until': self._get_validity_end(cal_tables),
            }
        except Exception as e:
            logger.warning(f"Calibrator {cal_name} failed: {e}")
            return None
```

**4.2 Enforce Calibration Validity**

```python
def apply_calibration_with_validation(
    ms_path: Path,
    cal_tables: List[Path],
    time_mjd: float
) -> bool:
    """Apply calibration only if valid."""
    
    # Check validity windows
    for cal_table in cal_tables:
        valid_until = get_caltable_validity(cal_table)
        if time_mjd > valid_until:
            raise CalibrationExpiredError(
                f"Calibration table {cal_table} expired. "
                f"Valid until {valid_until}, current time {time_mjd}"
            )
    
    # Apply calibration
    apply_to_target(ms_path, cal_tables)
    
    # Validate application
    if not validate_corrected_data_quality(ms_path):
        raise CalibrationApplicationError(
            "Calibration application failed quality check"
        )
    
    return True
```

---

## 5. Validation & Quality Gates

### Current State

**What Works:**
- Quality assurance framework exists
- Checks for MS, calibration, and images
- Alerting for quality issues

**Gaps:**

1. **Quality Checks Are Optional**
   - Many checks are warnings, not failures
   - Pipeline can proceed with low-quality data
   - No mandatory quality gates

2. **Validation Not Comprehensive**
   - Some checks are quick-only (skip detailed validation)
   - Cross-stage validation missing (e.g., MS vs. calibration compatibility)
   - End-to-end validation not enforced

3. **No Quality-Based Routing**
   - Low-quality data not automatically routed to different processing
   - No quality-based retry with different parameters

### Recommendations

**5.1 Implement Mandatory Quality Gates**

```python
class QualityGate:
    """Enforce quality gates at pipeline stages."""
    
    def __init__(self, stage: str, thresholds: dict, mandatory: bool = True):
        self.stage = stage
        self.thresholds = thresholds
        self.mandatory = mandatory
    
    def check(self, data_path: Path) -> Tuple[bool, dict]:
        """Check quality and return (passed, metrics)."""
        if self.stage == "ms":
            passed, metrics = check_ms_after_conversion(data_path)
        elif self.stage == "calibration":
            passed, metrics = check_calibration_quality(data_path)
        elif self.stage == "image":
            passed, metrics = check_image_quality(data_path)
        else:
            raise ValueError(f"Unknown stage: {self.stage}")
        
        # Apply thresholds
        passed = self._apply_thresholds(metrics)
        
        if not passed and self.mandatory:
            raise QualityGateError(
                f"Quality gate failed for {self.stage}: {metrics}",
                stage=self.stage,
                metrics=metrics
            )
        
        return passed, metrics
```

**5.2 Add Cross-Stage Validation**

```python
def validate_pipeline_consistency(ms_path: Path, cal_tables: List[Path]) -> bool:
    """Validate consistency across pipeline stages."""
    
    # Check MS and calibration compatibility
    ms_spws = get_ms_spws(ms_path)
    cal_spws = get_caltable_spws(cal_tables)
    
    if not set(ms_spws).issubset(set(cal_spws)):
        raise ValidationError(
            f"MS SPWs {ms_spws} not covered by calibration SPWs {cal_spws}"
        )
    
    # Check time ranges
    ms_time_range = get_ms_time_range(ms_path)
    cal_validity = get_caltable_validity_range(cal_tables)
    
    if not (cal_validity[0] <= ms_time_range[0] <= cal_validity[1]):
        raise ValidationError(
            f"MS time range {ms_time_range} outside calibration validity {cal_validity}"
        )
    
    return True
```

---

## 6. State Management & Recovery

### Current State

**What Works:**
- Queue state machine with persistence
- Checkpoint files for conversion
- Housekeeping for stale state recovery

**Gaps:**

1. **Incomplete State Recovery**
   - Some operations don't checkpoint
   - Calibration state not checkpointed
   - Imaging state not checkpointed

2. **State Inconsistencies**
   - Queue state may not match filesystem
   - Products DB may have orphaned entries
   - Calibration registry may be out of sync

3. **No State Validation**
   - No periodic validation of state consistency
   - No automatic repair of inconsistencies
   - No detection of orphaned artifacts

### Recommendations

**6.1 Implement Comprehensive Checkpointing**

```python
class PipelineCheckpoint:
    """Checkpoint pipeline state for recovery."""
    
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        group_id: str,
        stage: str,
        state: dict,
        artifacts: List[Path]
    ):
        """Save checkpoint for stage."""
        checkpoint_path = self.checkpoint_dir / f"{group_id}_{stage}.json"
        
        checkpoint_data = {
            'group_id': group_id,
            'stage': stage,
            'state': state,
            'artifacts': [str(p) for p in artifacts],
            'timestamp': time.time(),
        }
        
        # Atomic write
        temp_path = checkpoint_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(checkpoint_data, f)
        temp_path.rename(checkpoint_path)
    
    def load(self, group_id: str, stage: str) -> Optional[dict]:
        """Load checkpoint for stage."""
        checkpoint_path = self.checkpoint_dir / f"{group_id}_{stage}.json"
        if not checkpoint_path.exists():
            return None
        
        with open(checkpoint_path) as f:
            return json.load(f)
    
    def clear(self, group_id: str, stage: str):
        """Clear checkpoint after successful completion."""
        checkpoint_path = self.checkpoint_dir / f"{group_id}_{stage}.json"
        checkpoint_path.unlink(missing_ok=True)
```

**6.2 Add State Consistency Validation**

```python
def validate_pipeline_state_consistency(
    queue_db: Path,
    products_db: Path,
    cal_registry_db: Path,
    ms_base_dir: Path
) -> List[str]:
    """Validate consistency across all state stores."""
    issues = []
    
    # Check queue vs. filesystem
    with sqlite3.connect(queue_db) as conn:
        completed = conn.execute(
            "SELECT group_id FROM ingest_queue WHERE state='completed'"
        ).fetchall()
        
        for (group_id,) in completed:
            ms_path = find_ms_for_group(ms_base_dir, group_id)
            if not ms_path or not ms_path.exists():
                issues.append(f"Queue says completed but MS missing: {group_id}")
    
    # Check products DB vs. filesystem
    with sqlite3.connect(products_db) as conn:
        images = conn.execute("SELECT path FROM images").fetchall()
        for (path,) in images:
            if not Path(path).exists():
                issues.append(f"Products DB references missing image: {path}")
    
    # Check calibration registry vs. filesystem
    with sqlite3.connect(cal_registry_db) as conn:
        caltables = conn.execute("SELECT path FROM caltables").fetchall()
        for (path,) in caltables:
            if not Path(path).exists():
                issues.append(f"Cal registry references missing table: {path}")
    
    return issues
```

---

## 7. Monitoring & Observability

### Current State

**What Works:**
- Alerting infrastructure (Slack/email)
- Performance metrics tracking
- API endpoints for status

**Gaps:**

1. **Limited Observability**
   - No distributed tracing
   - No correlation IDs across stages
   - Limited metrics aggregation
   - No health check endpoints

2. **Incomplete Monitoring**
   - Some failures not monitored
   - No trend analysis
   - No predictive alerts
   - No SLA tracking

### Recommendations

**7.1 Add Correlation IDs**

```python
class PipelineContext:
    """Context for tracking operations across pipeline stages."""
    
    def __init__(self, correlation_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.stage = None
        self.start_time = time.time()
        self.metadata = {}
    
    def set_stage(self, stage: str):
        """Set current pipeline stage."""
        self.stage = stage
        self.metadata['stage'] = stage
        self.metadata['stage_start'] = time.time()
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to context."""
        self.metadata[key] = value
    
    def to_dict(self) -> dict:
        """Serialize context for logging."""
        return {
            'correlation_id': self.correlation_id,
            'stage': self.stage,
            'duration': time.time() - self.start_time,
            'metadata': self.metadata,
        }
```

**7.2 Implement Health Checks**

```python
def health_check() -> dict:
    """Comprehensive health check endpoint."""
    health = {
        'status': 'healthy',
        'timestamp': time.time(),
        'checks': {}
    }
    
    # Check casa6 environment
    casa6_python = Path("/opt/miniforge/envs/casa6/bin/python")
    health['checks']['casa6'] = {
        'status': 'ok' if casa6_python.exists() else 'missing',
        'path': str(casa6_python)
    }
    
    # Check disk space
    disk_usage = shutil.disk_usage('/scratch')
    health['checks']['disk'] = {
        'status': 'ok' if disk_usage.free > 100 * 1024**3 else 'low',
        'free_gb': disk_usage.free / (1024**3)
    }
    
    # Check databases
    for db_name, db_path in [
        ('queue', Path('/data/dsa110-contimg/state/ingest.sqlite3')),
        ('products', Path('/data/dsa110-contimg/state/products.sqlite3')),
        ('cal_registry', Path('/data/dsa110-contimg/state/cal_registry.sqlite3')),
    ]:
        health['checks'][db_name] = {
            'status': 'ok' if db_path.exists() else 'missing',
            'path': str(db_path)
        }
    
    # Overall status
    if any(c['status'] != 'ok' for c in health['checks'].values()):
        health['status'] = 'degraded'
    
    return health
```

---

## 8. Implementation Priority

### Phase 1: Critical (Weeks 1-2)
1. Error classification and recovery strategies
2. Resource preflight checks
3. Mandatory quality gates
4. Calibrator fallback chain

### Phase 2: Important (Weeks 3-4)
5. Atomic operations and transaction boundaries
6. Comprehensive checkpointing
7. State consistency validation
8. Health check endpoints

### Phase 3: Enhancement (Weeks 5-6)
9. Distributed tracing
10. Predictive monitoring
11. Resource quotas
12. Quality-based routing

---

## 9. Testing Strategy

### Unit Tests
- Error classification logic
- Resource management functions
- Quality gate thresholds
- State validation functions

### Integration Tests
- End-to-end pipeline with failures injected
- Recovery from checkpoints
- Calibrator fallback scenarios
- Resource exhaustion scenarios

### Chaos Engineering
- Random failures at each stage
- Disk space exhaustion
- Network interruptions
- Database corruption

---

## Summary

The pipeline has a solid foundation but needs strengthening in error handling, resource management, and state consistency. The recommendations above provide a roadmap for production-grade robustness.

**Key Principles:**
1. **Fail fast with clear errors** - Classify errors and provide recovery hints
2. **Atomic operations** - Ensure consistency across multi-step operations
3. **Proactive resource management** - Check before operations, not after failures
4. **Mandatory quality gates** - Don't proceed with low-quality data
5. **Comprehensive observability** - Track everything, correlate across stages
6. **Automatic recovery** - Retry, fallback, and self-heal where possible


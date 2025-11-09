# Architectural Elegance: Large-Scale Improvements

This document explores ways to make the DSA-110 continuum imaging pipeline more elegant at larger scales, focusing on architecture, orchestration, and maintainability.

## Current State Analysis

### Strengths
- Clear separation of stages (conversion, calibration, imaging, mosaicking)
- Unified exception hierarchy (Phase 2)
- Standardized utilities (Phase 1)
- Job tracking via SQLite database
- API for monitoring

### Pain Points
- **Manual workflow chaining**: `run_workflow_job()` manually calls stages
- **Scattered configuration**: Multiple config classes, environment variables, defaults
- **Subprocess-based execution**: Stages invoked via subprocess rather than direct calls
- **Limited error recovery**: No automatic retry or partial failure handling
- **Tight coupling**: Stages know about database structure directly
- **No dependency graph**: Hard to reason about stage dependencies
- **Resource management**: Manual handling of temp files, scratch dirs, cleanup

---

## Proposed Improvements

### 1. Pipeline Orchestration Framework

**Current**: Manual chaining in `run_workflow_job()`

**Proposed**: Declarative pipeline with dependency graph

```python
# pipeline/orchestrator.py
from dataclasses import dataclass
from typing import Protocol, Dict, Any, Optional
from enum import Enum

class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class PipelineStage(Protocol):
    """Protocol for pipeline stages."""
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute stage and return updated context."""
        ...
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Validate prerequisites."""
        ...

@dataclass
class StageDefinition:
    name: str
    stage: PipelineStage
    dependencies: list[str]  # Names of prerequisite stages
    retry_policy: Optional[RetryPolicy] = None
    timeout: Optional[float] = None
    resource_requirements: Optional[ResourceRequirements] = None

class PipelineOrchestrator:
    """Orchestrates multi-stage pipeline with dependency resolution."""
    
    def __init__(self, stages: list[StageDefinition]):
        self.stages = {s.name: s for s in stages}
        self.graph = self._build_dependency_graph()
    
    def execute(self, initial_context: Dict[str, Any]) -> PipelineResult:
        """Execute pipeline respecting dependencies."""
        execution_order = self._topological_sort()
        context = initial_context.copy()
        results = {}
        
        for stage_name in execution_order:
            stage_def = self.stages[stage_name]
            
            # Check if prerequisites met
            if not self._prerequisites_met(stage_name, results):
                results[stage_name] = StageResult(
                    status=StageStatus.SKIPPED,
                    reason="Prerequisites not met"
                )
                continue
            
            # Execute with retry policy
            result = self._execute_with_retry(stage_def, context)
            results[stage_name] = result
            
            if result.status == StageStatus.FAILED:
                # Handle failure (stop, continue, retry)
                if not stage_def.retry_policy.should_continue():
                    break
            
            # Update context with stage outputs
            context.update(result.outputs)
        
        return PipelineResult(results, context)
```

**Benefits**:
- Declarative pipeline definition
- Automatic dependency resolution
- Built-in retry and error handling
- Easy to test individual stages
- Parallel execution where possible

---

### 2. Unified Configuration System

**Current**: Scattered configs (`ApiConfig`, `CalibratorMSConfig`, environment variables)

**Proposed**: Hierarchical configuration with validation

```python
# config/pipeline_config.py
from pydantic import BaseModel, Field, validator
from pathlib import Path
from typing import Optional, Dict, Any

class PathsConfig(BaseModel):
    """Path configuration."""
    input_dir: Path = Field(..., description="Input directory for UVH5 files")
    output_dir: Path = Field(..., description="Output directory for MS files")
    scratch_dir: Optional[Path] = Field(None, description="Scratch directory")
    state_dir: Path = Field(default=Path("state"), description="State directory")
    
    @property
    def products_db(self) -> Path:
        return self.state_dir / "products.sqlite3"
    
    @property
    def registry_db(self) -> Path:
        return self.state_dir / "cal_registry.sqlite3"

class ConversionConfig(BaseModel):
    """Conversion stage configuration."""
    writer: str = Field(default="auto", description="Writer strategy")
    max_workers: int = Field(default=4, ge=1, le=32)
    stage_to_tmpfs: bool = Field(default=True)
    expected_subbands: int = Field(default=16, ge=1, le=32)

class CalibrationConfig(BaseModel):
    """Calibration stage configuration."""
    cal_bp_minsnr: float = Field(default=3.0, ge=1.0, le=10.0)
    cal_gain_solint: str = Field(default="inf")
    default_refant: str = Field(default="103")
    auto_select_refant: bool = Field(default=True)

class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""
    paths: PathsConfig
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    imaging: ImagingConfig = Field(default_factory=ImagingConfig)
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Load from environment variables."""
        ...
    
    @classmethod
    def from_file(cls, path: Path) -> "PipelineConfig":
        """Load from YAML/TOML file."""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineConfig":
        """Load from dictionary (e.g., API request)."""
        ...
```

**Benefits**:
- Single source of truth for configuration
- Type-safe with validation
- Hierarchical (can override at stage level)
- Supports multiple sources (env, file, API)
- Auto-generates documentation

---

### 3. Stage Abstraction with Context Passing

**Current**: Stages invoked via subprocess, context passed via database

**Proposed**: Direct stage interface with typed context

```python
# pipeline/stages.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Dict, Any

@dataclass
class PipelineContext:
    """Immutable context passed between stages."""
    config: PipelineConfig
    job_id: Optional[int] = None
    inputs: Dict[str, Any] = None  # Stage inputs
    outputs: Dict[str, Any] = None  # Stage outputs
    metadata: Dict[str, Any] = None  # Additional metadata
    
    def with_output(self, key: str, value: Any) -> "PipelineContext":
        """Return new context with added output."""
        new_outputs = (self.outputs or {}).copy()
        new_outputs[key] = value
        return PipelineContext(
            config=self.config,
            job_id=self.job_id,
            inputs=self.inputs,
            outputs=new_outputs,
            metadata=self.metadata
        )

class PipelineStage(ABC):
    """Base class for pipeline stages."""
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage and return updated context."""
        ...
    
    @abstractmethod
    def validate(self, context: PipelineContext) -> tuple[bool, Optional[str]]:
        """Validate prerequisites. Returns (is_valid, error_message)."""
        ...
    
    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup resources after execution (optional)."""
        pass

class ConversionStage(PipelineStage):
    """Conversion stage: UVH5 → MS."""
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms
        )
        
        ms_path = convert_subband_groups_to_ms(
            input_dir=str(context.config.paths.input_dir),
            output_dir=str(context.config.paths.output_dir),
            start_time=context.inputs["start_time"],
            end_time=context.inputs["end_time"],
            writer=context.config.conversion.writer,
            max_workers=context.config.conversion.max_workers,
        )
        
        return context.with_output("ms_path", ms_path)
    
    def validate(self, context: PipelineContext) -> tuple[bool, Optional[str]]:
        if not context.config.paths.input_dir.exists():
            return False, f"Input directory not found: {context.config.paths.input_dir}"
        return True, None
```

**Benefits**:
- Type-safe context passing
- Easy to test (mock context)
- Clear stage interfaces
- No subprocess overhead
- Better error handling

---

### 4. Resource Management and Cleanup

**Current**: Manual cleanup, scattered temp file handling

**Proposed**: Context managers and resource pools

```python
# pipeline/resources.py
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import tempfile
import shutil

class ResourceManager:
    """Manages pipeline resources (temp files, scratch dirs, etc.)."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._temp_dirs = []
        self._temp_files = []
    
    @contextmanager
    def temp_dir(self, prefix: str = "dsa110_") -> Iterator[Path]:
        """Create temporary directory, cleanup on exit."""
        tmp = Path(tempfile.mkdtemp(prefix=prefix))
        self._temp_dirs.append(tmp)
        try:
            yield tmp
        finally:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
                self._temp_dirs.remove(tmp)
    
    @contextmanager
    def scratch_dir(self) -> Iterator[Path]:
        """Get or create scratch directory."""
        scratch = self.config.paths.scratch_dir or Path("/tmp")
        scratch.mkdir(parents=True, exist_ok=True)
        yield scratch
    
    def cleanup_all(self) -> None:
        """Cleanup all managed resources."""
        for tmp in self._temp_dirs:
            shutil.rmtree(tmp, ignore_errors=True)
        self._temp_dirs.clear()
        for tmp_file in self._temp_files:
            if tmp_file.exists():
                tmp_file.unlink()
        self._temp_files.clear()

# Usage in stages
class ConversionStage(PipelineStage):
    def execute(self, context: PipelineContext) -> PipelineContext:
        resource_mgr = ResourceManager(context.config)
        
        with resource_mgr.temp_dir() as tmp_dir:
            # Use tmp_dir for intermediate files
            ms_path = self._convert_with_temp(tmp_dir, context)
        
        # Temp dir automatically cleaned up
        return context.with_output("ms_path", ms_path)
```

**Benefits**:
- Automatic cleanup
- No resource leaks
- Clear resource lifecycle
- Easy to track resource usage

---

### 5. Observability and Monitoring

**Current**: Database logging, basic API monitoring

**Proposed**: Structured logging, metrics, tracing

```python
# pipeline/observability.py
import structlog
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time

@dataclass
class StageMetrics:
    """Metrics for a pipeline stage."""
    stage_name: str
    duration_seconds: float
    input_size_bytes: Optional[int] = None
    output_size_bytes: Optional[int] = None
    memory_peak_mb: Optional[float] = None
    cpu_time_seconds: Optional[float] = None

class PipelineObserver:
    """Observes pipeline execution for monitoring."""
    
    def __init__(self):
        self.logger = structlog.get_logger("pipeline")
        self.metrics: list[StageMetrics] = []
    
    def stage_started(self, stage_name: str, context: PipelineContext) -> None:
        """Called when stage starts."""
        self.logger.info(
            "stage_started",
            stage=stage_name,
            job_id=context.job_id,
            inputs=context.inputs
        )
    
    def stage_completed(
        self,
        stage_name: str,
        context: PipelineContext,
        duration: float
    ) -> None:
        """Called when stage completes."""
        metrics = StageMetrics(
            stage_name=stage_name,
            duration_seconds=duration
        )
        self.metrics.append(metrics)
        
        self.logger.info(
            "stage_completed",
            stage=stage_name,
            job_id=context.job_id,
            duration_seconds=duration,
            outputs=context.outputs
        )
    
    def stage_failed(
        self,
        stage_name: str,
        context: PipelineContext,
        error: Exception,
        duration: float
    ) -> None:
        """Called when stage fails."""
        self.logger.error(
            "stage_failed",
            stage=stage_name,
            job_id=context.job_id,
            error=str(error),
            error_type=type(error).__name__,
            duration_seconds=duration
        )
```

**Benefits**:
- Structured logging (easy to query)
- Performance metrics
- Error tracking
- Integration with monitoring systems

---

### 6. Workflow Composition and Reusability

**Current**: Hardcoded workflows (`run_workflow_job`)

**Proposed**: Composable workflow definitions

```python
# pipeline/workflows.py
from typing import List, Callable

class WorkflowBuilder:
    """Builder for creating reusable workflows."""
    
    def __init__(self):
        self.stages: List[StageDefinition] = []
    
    def add_stage(
        self,
        name: str,
        stage: PipelineStage,
        depends_on: List[str] = None
    ) -> "WorkflowBuilder":
        """Add stage to workflow."""
        self.stages.append(StageDefinition(
            name=name,
            stage=stage,
            dependencies=depends_on or []
        ))
        return self
    
    def build(self) -> PipelineOrchestrator:
        """Build pipeline orchestrator."""
        return PipelineOrchestrator(self.stages)

# Define standard workflows
def standard_imaging_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Standard workflow: Convert → Calibrate → Image."""
    return (WorkflowBuilder()
        .add_stage("convert", ConversionStage())
        .add_stage("calibrate", CalibrationStage(), depends_on=["convert"])
        .add_stage("image", ImagingStage(), depends_on=["calibrate"])
        .build())

def quicklook_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Quicklook workflow: Convert → Image (no calibration)."""
    return (WorkflowBuilder()
        .add_stage("convert", ConversionStage())
        .add_stage("image", ImagingStage(), depends_on=["convert"])
        .build())

def reprocessing_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Reprocessing workflow: Calibrate → Image (MS already exists)."""
    return (WorkflowBuilder()
        .add_stage("calibrate", CalibrationStage())
        .add_stage("image", ImagingStage(), depends_on=["calibrate"])
        .build())
```

**Benefits**:
- Reusable workflow definitions
- Easy to create new workflows
- Clear dependencies
- Testable

---

### 7. Error Recovery and Resilience

**Current**: Failures stop entire workflow

**Proposed**: Configurable retry and recovery strategies

```python
# pipeline/resilience.py
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum

class RetryStrategy(Enum):
    NONE = "none"
    EXPONENTIAL_BACKOFF = "exponential"
    FIXED_INTERVAL = "fixed"
    IMMEDIATE = "immediate"

@dataclass
class RetryPolicy:
    """Retry policy for stage execution."""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_delay: float = 1.0
    max_delay: float = 60.0
    retryable_errors: Optional[Callable[[Exception], bool]] = None
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if should retry after error."""
        if attempt >= self.max_attempts:
            return False
        
        if self.retryable_errors and not self.retryable_errors(error):
            return False
        
        return True
    
    def get_delay(self, attempt: int) -> float:
        """Get delay before retry."""
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.initial_delay * (2 ** (attempt - 1))
            return min(delay, self.max_delay)
        elif self.strategy == RetryStrategy.FIXED_INTERVAL:
            return self.initial_delay
        elif self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        return 0.0

class FailureHandler:
    """Handles stage failures with recovery strategies."""
    
    def __init__(self, policy: RetryPolicy):
        self.policy = policy
    
    def handle_failure(
        self,
        stage: PipelineStage,
        context: PipelineContext,
        error: Exception,
        attempt: int
    ) -> tuple[bool, Optional[PipelineContext]]:
        """Handle failure and decide on recovery."""
        if not self.policy.should_retry(attempt, error):
            return False, None
        
        # Log retry
        delay = self.policy.get_delay(attempt)
        time.sleep(delay)
        
        # Retry execution
        try:
            result = stage.execute(context)
            return True, result
        except Exception as retry_error:
            return False, None
```

**Benefits**:
- Automatic retry for transient failures
- Configurable retry strategies
- Better resilience to network/filesystem issues
- Can continue pipeline on non-critical failures

---

### 8. State Management Abstraction

**Current**: Direct SQLite access scattered throughout

**Proposed**: Repository pattern with abstraction

```python
# pipeline/state.py
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class JobState:
    """Job state representation."""
    id: int
    type: str
    status: str
    context: Dict[str, Any]
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

class StateRepository(ABC):
    """Abstract interface for state persistence."""
    
    @abstractmethod
    def create_job(self, job_type: str, context: Dict[str, Any]) -> int:
        """Create new job and return ID."""
        ...
    
    @abstractmethod
    def update_job(self, job_id: int, updates: Dict[str, Any]) -> None:
        """Update job state."""
        ...
    
    @abstractmethod
    def get_job(self, job_id: int) -> Optional[JobState]:
        """Get job state."""
        ...
    
    @abstractmethod
    def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100
    ) -> List[JobState]:
        """List jobs with filters."""
        ...

class SQLiteStateRepository(StateRepository):
    """SQLite implementation of state repository."""
    ...

class InMemoryStateRepository(StateRepository):
    """In-memory implementation for testing."""
    ...
```

**Benefits**:
- Testable (can use in-memory implementation)
- Swappable backends (SQLite, PostgreSQL, etc.)
- Clean separation of concerns
- Easy to mock for testing

---

## Implementation Strategy

### Phase 1: Foundation (Low Risk)
1. Create `PipelineContext` and `PipelineStage` base classes
2. Implement `StateRepository` abstraction
3. Add `ResourceManager` for cleanup

### Phase 2: Orchestration (Medium Risk)
1. Implement `PipelineOrchestrator` with dependency resolution
2. Convert one stage to new interface (e.g., `ConversionStage`)
3. Test with simple workflow

### Phase 3: Configuration (Low Risk)
1. Implement unified `PipelineConfig` with Pydantic
2. Migrate existing configs gradually
3. Add config validation

### Phase 4: Observability (Low Risk)
1. Add structured logging
2. Implement metrics collection
3. Add monitoring integration

### Phase 5: Resilience (Medium Risk)
1. Add retry policies
2. Implement failure handlers
3. Add recovery strategies

---

## Benefits Summary

1. **Maintainability**: Clear separation of concerns, testable components
2. **Flexibility**: Easy to add new stages, workflows, or change execution order
3. **Reliability**: Built-in retry, error handling, resource cleanup
4. **Observability**: Structured logging, metrics, tracing
5. **Testability**: Mockable interfaces, in-memory implementations
6. **Performance**: Direct calls instead of subprocess overhead
7. **Developer Experience**: Declarative workflows, type safety, clear APIs

---

## Migration Path

1. **Parallel Implementation**: Build new system alongside existing
2. **Gradual Migration**: Convert one stage at a time
3. **Feature Flags**: Use flags to switch between old/new implementations
4. **Validation**: Run both systems in parallel to validate correctness
5. **Deprecation**: Remove old system once new system is proven

---

## Current Implementation Analysis

### Database Schema

**Jobs Table** (`database/jobs.py`):
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,              -- 'convert', 'calibrate', 'image', 'workflow'
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'done', 'failed'
    ms_path TEXT NOT NULL,            -- Empty string for workflow jobs
    params TEXT,                      -- JSON dict of parameters
    logs TEXT,                        -- Plain text log output
    artifacts TEXT,                   -- JSON array of output paths
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL
)
```

**MS Index Table** (`database/products.py`):
```sql
CREATE TABLE ms_index (
    path TEXT PRIMARY KEY,
    start_mjd REAL,
    end_mjd REAL,
    mid_mjd REAL,
    processed_at REAL,
    status TEXT,                      -- Processing status
    stage TEXT,                       -- Current pipeline stage
    stage_updated_at REAL,
    cal_applied INTEGER DEFAULT 0,    -- Boolean flag
    imagename TEXT
)
```

**Current Pain Points**:
- `artifacts` stored as JSON string, requires parsing
- `params` stored as JSON string, no type validation
- `logs` stored as plain text, hard to query/analyze
- No relationship between jobs and ms_index entries
- Manual database queries scattered throughout code

### Current Workflow Execution

**Example: `run_workflow_job()` (lines 693-776)**:

```python
# Current implementation issues:
1. Manual database queries to get artifacts
   cursor.execute("SELECT artifacts, status FROM jobs WHERE id = ?", (job_id,))
   artifacts = json.loads(row[0]) if row and row[0] else []

2. Subprocess-based execution (overhead, harder to debug)
   run_convert_job(job_id, convert_params, products_db)  # Spawns subprocess

3. No retry logic - single failure stops entire workflow

4. Error handling is basic
   except Exception as e:
       append_job_log(conn, job_id, f"ERROR: {e}\n")
       update_job_status(conn, job_id, "failed", finished_at=time.time())

5. Context passed via database (artifacts JSON field)
   ms_path = artifacts[0]  # Fragile: assumes first artifact is MS
```

### Concrete Refactoring Example

**BEFORE (Current)**:
```python
def run_workflow_job(job_id: int, params: dict, products_db: Path):
    # Step 1: Convert
    run_convert_job(job_id, convert_params, products_db)
    
    # Manual database query to get results
    conn = ensure_products_db(products_db)
    cursor = conn.cursor()
    cursor.execute("SELECT artifacts, status FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if not row or row[1] == "failed":
        raise Exception("Conversion step failed")
    artifacts = json.loads(row[0]) if row and row[0] else []
    ms_path = artifacts[0]  # Fragile assumption
    
    # Step 2: Image
    run_image_job(job_id, ms_path, image_params, products_db)
```

**AFTER (Proposed)**:
```python
def run_workflow_job(job_id: int, params: dict, products_db: Path):
    # Create pipeline context
    config = PipelineConfig.from_dict(params)
    context = PipelineContext(
        config=config,
        job_id=job_id,
        inputs={"start_time": params["start_time"], "end_time": params["end_time"]}
    )
    
    # Define workflow
    workflow = standard_imaging_workflow(config)
    
    # Execute with automatic dependency resolution
    result = workflow.execute(context)
    
    # Results are in typed context, not database
    if result.status == PipelineStatus.COMPLETED:
        ms_path = result.context.outputs["ms_path"]
        image_path = result.context.outputs["image_path"]
        # All artifacts tracked automatically
```

### Database Schema Evolution

**Proposed Enhanced Schema**:

```sql
-- Enhanced jobs table with better structure
CREATE TABLE jobs_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    workflow_name TEXT,               -- Name of workflow template used
    context_inputs TEXT,              -- JSON: initial inputs
    context_outputs TEXT,             -- JSON: final outputs
    stage_results TEXT,               -- JSON: per-stage results
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL,
    error_message TEXT,               -- Structured error info
    retry_count INTEGER DEFAULT 0
)

-- Stage execution tracking
CREATE TABLE stage_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at REAL,
    finished_at REAL,
    duration_seconds REAL,
    inputs TEXT,                      -- JSON: stage inputs
    outputs TEXT,                     -- JSON: stage outputs
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (job_id) REFERENCES jobs_v2(id)
)

-- Better indexing for queries
CREATE INDEX idx_stage_executions_job ON stage_executions(job_id, stage_name);
CREATE INDEX idx_stage_executions_status ON stage_executions(status);
```

### Performance Considerations

**Current Subprocess Overhead**:
- Each stage spawns new Python process
- Environment setup (CASA, PYTHONPATH) repeated
- Process startup time: ~100-500ms per stage
- For 3-stage workflow: ~300-1500ms overhead

**Critical Performance Bottleneck** (`api/job_runner.py:657-660`):
```python
# MAJOR ISSUE: Database commit for EVERY line of stdout
for line in proc.stdout:
    append_job_log(conn, job_id, line)
    conn.commit()  # ← Database write for every log line!
```
- **Impact**: For long-running stages (hours), this can result in 10,000+ database commits
- **Solution**: Batch commits (every N lines) or use structured logging with async writes

**Artifact Discovery Issues** (`api/job_runner.py:665-671`):
```python
# Discover created MS files AFTER execution
artifacts = []
output_path = Path(output_dir)
if output_path.exists():
    for ms in output_path.glob("**/*.ms"):  # ← Slow glob, no guarantee of correctness
        if ms.is_dir():
            artifacts.append(str(ms))
```
- **Problem**: No guarantee we find the right MS (could find old ones)
- **Problem**: Glob is slow for large directories
- **Solution**: Stages should return artifacts directly, not discover them

**Proposed Direct Call Benefits**:
- No process startup overhead
- Shared memory for context passing
- Better error propagation (exceptions vs exit codes)
- Easier debugging (single process)
- No line-by-line database commits
- Direct artifact tracking

**Trade-offs**:
- Subprocess isolation prevents memory leaks from affecting other stages
- Subprocess allows independent resource limits
- Direct calls require careful resource management
- **Hybrid approach**: Use subprocess for memory-intensive stages, direct calls for others

**Hybrid Approach**:
```python
class PipelineStage(ABC):
    execution_mode: ExecutionMode = ExecutionMode.DIRECT
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        ...

class ExecutionMode(Enum):
    DIRECT = "direct"      # In-process (default, faster)
    SUBPROCESS = "subprocess"  # Isolated (for memory safety)
    REMOTE = "remote"      # Distributed (future)
```

### Backward Compatibility Strategy

**Phase 1: Parallel Implementation**
- Keep existing `run_workflow_job()` unchanged
- Add new `PipelineOrchestrator` alongside
- Use feature flag to switch between implementations

**Phase 2: Adapter Layer**
```python
class LegacyWorkflowAdapter:
    """Adapter to run new pipeline with legacy job tracking."""
    
    def run_workflow_job(self, job_id: int, params: dict, products_db: Path):
        # Convert legacy params to PipelineConfig
        config = PipelineConfig.from_dict(params)
        context = PipelineContext(config=config, job_id=job_id)
        
        # Execute new pipeline
        workflow = standard_imaging_workflow(config)
        result = workflow.execute(context)
        
        # Update legacy database format
        self._update_legacy_job_table(job_id, result, products_db)
```

**Phase 3: Gradual Migration**
- Migrate one workflow type at a time
- Keep both systems running in parallel
- Validate outputs match
- Deprecate old system once validated

### Real-World Migration Example

**Converting `run_convert_job()` to new system**:

```python
# BEFORE: Subprocess-based
def run_convert_job(job_id: int, params: dict, products_db: Path):
    cmd = [sys.executable, "-m", "dsa110_contimg.conversion.strategies.hdf5_orchestrator", ...]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, ...)
    # Parse stdout, update database

# AFTER: Direct stage
class ConversionStage(PipelineStage):
    def execute(self, context: PipelineContext) -> PipelineContext:
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms
        )
        
        ms_path = convert_subband_groups_to_ms(
            input_dir=str(context.config.paths.input_dir),
            output_dir=str(context.config.paths.output_dir),
            start_time=context.inputs["start_time"],
            end_time=context.inputs["end_time"],
            writer=context.config.conversion.writer,
            max_workers=context.config.conversion.max_workers,
        )
        
        # Update ms_index via repository (not direct SQL)
        state_repo = context.get_state_repository()
        state_repo.upsert_ms_index(ms_path, {
            "status": "converted",
            "stage": "conversion",
            "mid_mjd": extract_ms_time_range(ms_path)[2]
        })
        
        return context.with_output("ms_path", ms_path)
```

### Testing Strategy

**Current Testing Challenges**:
- Hard to test subprocess-based execution
- Database state required for tests
- Difficult to mock external dependencies

**Proposed Testing Approach**:
```python
# Test individual stages in isolation
def test_conversion_stage():
    config = PipelineConfig.from_dict({
        "paths": {"input_dir": "/test/input", "output_dir": "/test/output"},
        "conversion": {"writer": "auto", "max_workers": 2}
    })
    context = PipelineContext(
        config=config,
        inputs={"start_time": "2024-01-01T00:00:00", "end_time": "2024-01-01T01:00:00"}
    )
    
    # Mock state repository
    mock_repo = MockStateRepository()
    context.state_repository = mock_repo
    
    # Execute stage
    stage = ConversionStage()
    result = stage.execute(context)
    
    # Assertions
    assert result.outputs["ms_path"] is not None
    assert mock_repo.ms_index_upserted == True

# Test workflow composition
def test_standard_workflow():
    workflow = standard_imaging_workflow(test_config)
    context = PipelineContext(config=test_config, inputs=test_inputs)
    
    result = workflow.execute(context)
    
    assert result.status == PipelineStatus.COMPLETED
    assert "ms_path" in result.context.outputs
    assert "image_path" in result.context.outputs
```

### Resource Management Details

**Current Issues**:
- Temp files created but not always cleaned up
- Scratch directories managed manually
- CASA file handles can leak

**Proposed Solution**:
```python
class ResourceManager:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._resources = []
    
    @contextmanager
    def managed_temp_dir(self, prefix: str = "dsa110_") -> Iterator[Path]:
        """Create temp dir, cleanup on exit or error."""
        tmp = Path(tempfile.mkdtemp(prefix=prefix))
        self._resources.append(("dir", tmp))
        try:
            yield tmp
        finally:
            self._cleanup_resource("dir", tmp)
    
    @contextmanager
    def managed_casa_environment(self) -> Iterator[None]:
        """Ensure CASA environment is set up, cleanup on exit."""
        # Setup CASA
        setup_casa_environment()
        try:
            yield
        finally:
            # Cleanup CASA file handles
            cleanup_casa_file_handles()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup all resources on exit
        for resource_type, resource in reversed(self._resources):
            self._cleanup_resource(resource_type, resource)
        self._resources.clear()
```

### Observability Implementation

**Structured Logging Example**:
```python
import structlog

logger = structlog.get_logger("pipeline")

# Current: Plain text logs
append_job_log(conn, job_id, f"Converting {ms_path}...\n")

# Proposed: Structured logs
logger.info(
    "stage_started",
    job_id=job_id,
    stage="conversion",
    ms_path=ms_path,
    config=config.dict()
)

# Queryable: SELECT * FROM logs WHERE stage='conversion' AND duration > 3600
```

**Metrics Collection**:
```python
class PipelineMetrics:
    def record_stage_metrics(
        self,
        stage_name: str,
        duration: float,
        input_size: int,
        output_size: int
    ):
        # Store in metrics table or send to Prometheus
        self.metrics_db.execute(
            """
            INSERT INTO stage_metrics 
            (stage_name, duration_seconds, input_size_bytes, output_size_bytes, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (stage_name, duration, input_size, output_size, time.time())
        )
```

### Specific Bottlenecks Identified

**1. Database Commit Frequency** (Critical)
- **Location**: `api/job_runner.py:660` - `conn.commit()` called for every log line
- **Impact**: 10,000+ commits for long-running stages
- **Fix**: Batch commits (every 10-100 lines) or async logging

**2. Artifact Discovery** (Medium)
- **Location**: `api/job_runner.py:665-671` - Post-execution globbing
- **Impact**: Slow, unreliable, may find wrong files
- **Fix**: Stages return artifacts directly in context

**3. Subprocess Environment Setup** (Low-Medium)
- **Location**: All `run_*_job()` functions
- **Impact**: ~100-500ms overhead per stage
- **Fix**: Direct calls or persistent worker processes

**4. Error Information Loss** (Medium)
- **Location**: `api/job_runner.py:687` - Generic exception handling
- **Impact**: Lost context, hard to debug
- **Fix**: Structured error capture with context

**5. Log Format** (Low)
- **Location**: Plain text logs in database
- **Impact**: Hard to query, analyze, or filter
- **Fix**: Structured logging (JSON) with separate log table

### Integration Points

**Current Integration**:
- API → Job Runner → Subprocess → Stage Function
- Database used as communication channel
- No direct function calls between stages

**Proposed Integration**:
- API → Pipeline Orchestrator → Stage Functions (direct)
- Context passed in-memory
- Database used only for persistence/observability

**Migration Strategy for Integration**:
1. Keep existing API endpoints unchanged
2. Add adapter layer: `LegacyJobAdapter` wraps new pipeline
3. Gradually migrate internal callers to direct pipeline API
4. Eventually deprecate subprocess-based execution

## Questions to Consider

1. **Backward Compatibility**: How important is maintaining exact API compatibility?
   - **Answer**: Critical for production. Use adapter pattern to maintain compatibility.

2. **Performance**: Is subprocess overhead actually a problem?
   - **Answer**: Yes, but isolation benefits may outweigh. Hybrid approach recommended.

3. **Complexity**: Does the added abstraction justify the benefits?
   - **Answer**: For long-term maintainability, yes. Start with simple implementation.

4. **Team Capacity**: Can the team maintain the more complex architecture?
   - **Answer**: Start with minimal viable implementation, add complexity gradually.

5. **Testing**: How will we test the new orchestration system?
   - **Answer**: Mock state repository, test stages in isolation, integration tests with test database.

6. **Migration Risk**: How do we validate the new system works correctly?
   - **Answer**: Run both systems in parallel, compare outputs, gradual rollout.

---

## Implementation Priority Matrix

| Improvement | Impact | Effort | Risk | Priority |
|------------|--------|--------|------|----------|
| Unified Configuration | High | Medium | Low | **1** |
| State Repository Abstraction | High | Medium | Low | **2** |
| Resource Management | Medium | Low | Low | **3** |
| Pipeline Orchestrator | High | High | Medium | **4** |
| Structured Logging | Medium | Low | Low | **5** |
| Retry Policies | Medium | Medium | Low | **6** |
| Workflow Composition | Low | Medium | Low | **7** |

---

## References

- **Pipeline Patterns**: Prefect, Airflow, Luigi, Dagster
- **Configuration**: Pydantic, Hydra, OmegaConf
- **State Management**: Repository Pattern, Event Sourcing
- **Observability**: OpenTelemetry, Prometheus, Grafana
- **Testing**: pytest, unittest.mock, testcontainers


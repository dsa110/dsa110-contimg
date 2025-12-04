# Execution Path Unification Plan (Issue #11)

**Status**: In Progress  
**Created**: 2025-12-03  
**Issue**: Subprocess vs In-Process Execution Inconsistency

## Problem Statement

The pipeline has two execution paths for running conversions:

1. **In-process**: Direct function calls within the streaming daemon
2. **Subprocess**: Spawning `python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator`

These paths have divergent behavior in:

- **Error handling**: Different exception types, return codes, and DB state transitions
- **Resource limits**: Subprocess can use `rlimit`/cgroups; in-process has no enforcement
- **Path organization**: Subprocess writes flat then reorganizes; in-process uses `PathMapper` directly

## Solution Architecture

### Key Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    streaming_converter.py                        │
│                                                                 │
│  ┌─────────────────┐                                           │
│  │ ExecutionTask   │ ─────────────────────────────────────┐    │
│  │ (input/output/  │                                      │    │
│  │  limits/config) │                                      ▼    │
│  └─────────────────┘                              ┌────────────┐│
│                                                   │  Executor  ││
│                                                   │  Factory   ││
│                                                   └─────┬──────┘│
│                          ┌──────────────────────────────┼──────┐│
│                          ▼                              ▼      ││
│                 ┌─────────────────┐          ┌─────────────────┐│
│                 │ InProcessExecutor│          │SubprocessExecutor│
│                 └────────┬────────┘          └────────┬────────┘│
│                          │                            │        │
│                          ▼                            ▼        │
│                 ┌─────────────────────────────────────────────┐│
│                 │           ResourceManager                    ││
│                 │  (OMP_THREADS, memory limits, cgroups)      ││
│                 └─────────────────────────────────────────────┘│
│                          │                            │        │
│                          ▼                            ▼        │
│                 ┌─────────────────────────────────────────────┐│
│                 │              PathMapper                      ││
│                 │  (canonical output organization)            ││
│                 └─────────────────────────────────────────────┘│
│                          │                                     │
│                          ▼                                     │
│                 ┌─────────────────┐                            │
│                 │ ExecutionResult │                            │
│                 │ (success/code/  │                            │
│                 │  paths/metrics) │                            │
│                 └─────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### New Modules

| Module                   | Purpose                                                          |
| ------------------------ | ---------------------------------------------------------------- |
| `execution/__init__.py`  | Package exports                                                  |
| `execution/executor.py`  | `Executor` base class, `InProcessExecutor`, `SubprocessExecutor` |
| `execution/task.py`      | `ExecutionTask` and `ExecutionResult` dataclasses                |
| `execution/resources.py` | `ResourceManager` for limits enforcement                         |
| `execution/errors.py`    | Canonical error codes and exception mapping                      |
| `io/path_mapper.py`      | Unified `PathMapper` for output organization                     |

---

## Implementation Tasks

### Phase 1: Core Abstractions

- [x] Task 1.1: Create `execution/task.py` with `ExecutionTask` and `ExecutionResult` dataclasses
- [x] Task 1.2: Create `execution/errors.py` with canonical error codes
- [x] Task 1.3: Create `execution/resources.py` with `ResourceManager`
- [ ] Task 1.4: Create `execution/executor.py` with base class and both implementations
- [ ] Task 1.5: Create `execution/__init__.py` with exports

### Phase 2: Path Organization

- [ ] Task 2.1: Refactor `PathMapper` into `io/path_mapper.py`
- [ ] Task 2.2: Ensure both executors use `PathMapper` for final output organization

### Phase 3: Integration

- [ ] Task 3.1: Update `streaming_converter.py` to use `Executor` abstraction
- [ ] Task 3.2: Update `hdf5_orchestrator.py` CLI to use same internal path
- [ ] Task 3.3: Add execution config to `config.py`

### Phase 4: Testing

- [ ] Task 4.1: Unit tests for `ExecutionTask`/`ExecutionResult`
- [ ] Task 4.2: Unit tests for `ResourceManager`
- [ ] Task 4.3: Unit tests for `InProcessExecutor`
- [ ] Task 4.4: Unit tests for `SubprocessExecutor`
- [ ] Task 4.5: Integration tests comparing both execution modes

### Phase 5: Documentation & Rollout

- [ ] Task 5.1: Update developer docs
- [ ] Task 5.2: Add monitoring for execution mode metrics
- [ ] Task 5.3: Staged rollout with `auto` mode default

---

## Detailed Specifications

### ExecutionTask Dataclass

```python
@dataclass
class ExecutionTask:
    """Encapsulates all inputs for a conversion job."""
    group_id: str
    input_dir: Path
    output_dir: Path
    scratch_dir: Path
    start_time: str  # ISO format
    end_time: str    # ISO format

    # Writer configuration
    writer: str = "auto"

    # Resource limits
    resource_limits: Optional[ResourceLimits] = None

    # Path organization
    organize_outputs: bool = True
    is_calibrator: Optional[bool] = None  # Auto-detect if None

    # Environment
    env_overrides: Dict[str, str] = field(default_factory=dict)

    # Execution preferences
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
```

### ExecutionResult Dataclass

```python
@dataclass
class ExecutionResult:
    """Standardized result from any execution mode."""
    success: bool
    return_code: int  # 0=success, standardized codes for failures

    # Error details (if failed)
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None

    # Output paths (if successful)
    ms_path: Optional[Path] = None
    final_paths: Dict[str, Path] = field(default_factory=dict)

    # Performance metrics
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)

    # Execution metadata
    execution_mode: str = "unknown"  # "inprocess" or "subprocess"
    started_at: float = 0.0
    ended_at: float = 0.0
```

### Canonical Error Codes

| Code | Name              | Description                      |
| ---- | ----------------- | -------------------------------- |
| 0    | SUCCESS           | Completed successfully           |
| 1    | GENERAL_ERROR     | Unspecified error                |
| 2    | IO_ERROR          | File I/O failure                 |
| 3    | OOM_ERROR         | Out of memory                    |
| 4    | TIMEOUT_ERROR     | Execution timeout exceeded       |
| 5    | VALIDATION_ERROR  | Input validation failed          |
| 6    | RESOURCE_LIMIT    | Resource limit exceeded          |
| 7    | CALIBRATION_ERROR | Calibration data missing/invalid |
| 8    | CONVERSION_ERROR  | UVH5→MS conversion failed        |

### ResourceLimits Dataclass

```python
@dataclass
class ResourceLimits:
    """Resource constraints for execution."""
    memory_mb: Optional[int] = None      # Max memory in MB
    cpu_seconds: Optional[int] = None    # Max CPU time
    omp_threads: int = 4                 # OpenMP thread count
    mkl_threads: int = 4                 # MKL thread count
    max_workers: int = 4                 # ThreadPool workers
    use_cgroups: bool = False            # Use cgroups for isolation
```

### Executor Interface

```python
class Executor(ABC):
    """Base class for execution strategies."""

    @abstractmethod
    def run(self, task: ExecutionTask) -> ExecutionResult:
        """Execute a conversion task and return standardized result."""
        pass

    def validate_task(self, task: ExecutionTask) -> None:
        """Validate task inputs. Raises ValidationError if invalid."""
        # Shared validation logic
        pass
```

---

## Configuration

Add to `config.py`:

```python
@dataclass
class ExecutionConfig:
    """Execution mode configuration."""
    mode: str = "auto"  # "auto", "inprocess", "subprocess"

    # Resource limits
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)

    # Subprocess-specific
    subprocess_timeout_seconds: int = 600  # 10 minutes
    subprocess_use_cgroups: bool = False

    # Retry policy
    max_retries: int = 2
    retry_delay_seconds: int = 30
```

---

## Migration Path

1. **Phase 1**: Implement abstractions without changing existing behavior
2. **Phase 2**: Wire up `streaming_converter.py` to use `InProcessExecutor` only (no behavior change)
3. **Phase 3**: Implement `SubprocessExecutor` using same abstractions
4. **Phase 4**: Enable `auto` mode that selects based on config/context
5. **Phase 5**: Monitor and tune; consider making `inprocess` the default

---

## Verification Commands

```bash
# Run unit tests for execution module
cd /data/dsa110-contimg/backend
conda activate casa6
python -m pytest tests/unit/execution/ -v

# Test in-process execution
python -c "
from dsa110_contimg.execution import InProcessExecutor, ExecutionTask
task = ExecutionTask(group_id='test', input_dir='/tmp', output_dir='/tmp',
                     scratch_dir='/tmp', start_time='2025-01-01T00:00:00',
                     end_time='2025-01-01T00:05:00')
executor = InProcessExecutor()
# result = executor.run(task)  # Would run actual conversion
"

# Compare execution modes (when implemented)
python -m dsa110_contimg.execution.compare --group-id "2025-10-05T12:00:00"
```

---

## Files to Create/Modify

### New Files

- `backend/src/dsa110_contimg/execution/__init__.py`
- `backend/src/dsa110_contimg/execution/task.py`
- `backend/src/dsa110_contimg/execution/errors.py`
- `backend/src/dsa110_contimg/execution/resources.py`
- `backend/src/dsa110_contimg/execution/executor.py`
- `backend/tests/unit/execution/test_task.py`
- `backend/tests/unit/execution/test_executor.py`
- `backend/tests/unit/execution/test_resources.py`

### Modified Files

- `backend/src/dsa110_contimg/config.py` - Add `ExecutionConfig`
- `backend/src/dsa110_contimg/conversion/streaming_converter.py` - Use `Executor`
- `backend/src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py` - Expose programmatic API

---

## Success Criteria

1. ✅ Both execution modes produce identical `ExecutionResult` for same inputs
2. ✅ Path organization is identical regardless of execution mode
3. ✅ Error codes and DB state transitions are consistent
4. ✅ Resource limits are enforced in both modes (to extent possible)
5. ✅ All existing tests continue to pass
6. ✅ New tests verify parity between modes

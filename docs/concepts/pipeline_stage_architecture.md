# Pipeline Stage Architecture

**Purpose:** Comprehensive guide to the stage-based pipeline architecture  
**Last Updated:** 2025-11-11  
**Status:** Production

---

## Overview

The DSA-110 continuum imaging pipeline uses a **stage-based architecture** with dependency resolution. This design provides:

- **Separation of Concerns:** Each stage has a single, well-defined responsibility
- **Testability:** Stages can be tested independently
- **Composability:** Stages can be combined in different workflows
- **Error Handling:** Retry policies and validation at each stage
- **Observability:** Logging and metrics at stage boundaries

---

## Core Concepts

### PipelineStage (Abstract Base Class)

All pipeline stages inherit from `PipelineStage`, which defines the interface:

```python
class PipelineStage(ABC):
    """Base class for all pipeline stages."""
    
    execution_mode: ExecutionMode = ExecutionMode.DIRECT
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage and return updated context."""
        ...
    
    @abstractmethod
    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for stage execution."""
        ...
    
    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup resources after execution (optional)."""
        pass
    
    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate stage outputs after execution (optional)."""
        return True, None
    
    def get_name(self) -> str:
        """Get stage name for logging and tracking."""
        return self.__class__.__name__
```

### PipelineContext (Immutable Data Structure)

The `PipelineContext` is an **immutable** data structure that carries state between stages:

```python
@dataclass(frozen=True)
class PipelineContext:
    """Immutable context passed between pipeline stages."""
    
    config: PipelineConfig
    job_id: Optional[int] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state_repository: Optional[StateRepository] = None
```

**Key Properties:**
- **Immutability:** Prevents accidental mutations
- **Type Safety:** Uses Pydantic for configuration validation
- **Extensibility:** Can add outputs/metadata without modifying existing code

### Stage Execution Flow

1. **Validation:** `validate()` checks prerequisites
2. **Execution:** `execute()` performs the work
3. **Output Validation:** `validate_outputs()` checks outputs (if implemented)
4. **Cleanup:** `cleanup()` releases resources (always called, even on failure)

---

## Stage Lifecycle

```
┌─────────────┐
│   PENDING   │  Stage defined, waiting for prerequisites
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  VALIDATING │  validate() called
└──────┬──────┘
       │
       ├─► Invalid ──► FAILED
       │
       ▼
┌─────────────┐
│   RUNNING   │  execute() called
└──────┬──────┘
       │
       ├─► Error ──► FAILED ──► cleanup()
       │
       ▼
┌─────────────┐
│ VALIDATING  │  validate_outputs() called (if implemented)
│   OUTPUTS   │
└──────┬──────┘
       │
       ├─► Invalid ──► FAILED ──► cleanup()
       │
       ▼
┌─────────────┐
│  COMPLETED  │  cleanup() called
└─────────────┘
```

---

## Pipeline Stages

### 1. CatalogSetupStage

**Purpose:** Build catalog databases for declination strip

**Responsibilities:**
- Extract declination from HDF5 file
- Detect declination changes (threshold: 0.1 degrees)
- Build NVSS, FIRST, RAX catalogs if missing
- Log pointing to `pointing_history` table

**Scientific Reasoning:**
- DSA-110 only slews in elevation
- Declination changes rarely
- Catalogs need to be updated when declination changes
- Prevents rebuilding catalogs unnecessarily

**Inputs:**
- `input_path` (HDF5 file path)

**Outputs:**
- `catalog_setup_status` (built/existed/failed/skipped)
- `dec_center` (declination center)
- `dec_range` (declination range)

**Dependencies:** None (runs first)

---

### 2. ConversionStage

**Purpose:** Convert UVH5 to Measurement Sets

**Responsibilities:**
- Discover complete subband groups in time window
- Convert UVH5 files to CASA Measurement Sets
- Validate output MS files
- Update database records

**Inputs:**
- `input_path` (HDF5 file path)
- `time_window` (optional, for grouping)

**Outputs:**
- `ms_path` (path to created MS file)
- `conversion_status` (success/failed)

**Dependencies:** None (can run independently)

---

### 3. CalibrationSolveStage

**Purpose:** Solve calibration solutions

**Responsibilities:**
- Identify calibrator observations
- Solve bandpass calibration (BP)
- Solve gain calibration (G)
- Register caltables in registry

**Inputs:**
- `ms_path` (calibrator MS path)

**Outputs:**
- `calibration_tables` (list of caltable paths)
- `calibration_status` (solved/failed)

**Dependencies:** ConversionStage (needs MS file)

---

### 4. CalibrationStage

**Purpose:** Apply calibration solutions to MS

**Responsibilities:**
- Select active caltables from registry
- Apply calibration to science targets
- Write CORRECTED_DATA column
- Validate calibration application

**Inputs:**
- `ms_path` (science MS path)
- `calibration_tables` (optional, auto-selected if not provided)

**Outputs:**
- `calibrated_ms_path` (path to calibrated MS)
- `calibration_applied` (boolean)

**Dependencies:** ConversionStage, CalibrationSolveStage

---

### 5. ImagingStage

**Purpose:** Create continuum images from calibrated MS

**Responsibilities:**
- Run tclean or WSClean
- Apply primary beam correction
- Use NVSS-based masking (2-4x faster)
- Generate image products

**Inputs:**
- `ms_path` (calibrated MS path)
- `field` (optional field name/coordinates)

**Outputs:**
- `image_path` (path to primary beam corrected image)
- `residual_path` (path to residual image)
- `beam_size` (arcseconds)

**Dependencies:** CalibrationStage

---

### 6. OrganizationStage

**Purpose:** Organize MS files into date-based directory structure

**Responsibilities:**
- Move MS files to organized locations:
  - Calibrators → `ms/calibrators/YYYY-MM-DD/`
  - Science → `ms/science/YYYY-MM-DD/`
  - Failed → `ms/failed/YYYY-MM-DD/`
- Update database paths
- Atomic moves (prevents partial states)

**Inputs:**
- `ms_path` (MS file path)
- `ms_type` (calibrator/science/failed)

**Outputs:**
- `organized_ms_path` (new path after organization)
- `organization_status` (moved/existed)

**Dependencies:** ConversionStage (or any stage that creates MS files)

---

### 7. ValidationStage

**Purpose:** Run catalog-based validation on images

**Responsibilities:**
- Cross-match with reference catalogs (NVSS, VLASS)
- Validate astrometry (positional accuracy)
- Validate flux scale (calibration accuracy)
- Source counts completeness analysis
- Generate HTML reports

**Inputs:**
- `image_path` (image to validate)
- `catalog` (nvss/vlass, default: nvss)

**Outputs:**
- `validation_report_path` (HTML report path)
- `astrometry_offset` (arcseconds)
- `flux_ratio` (observed/reference)
- `completeness` (fraction)

**Dependencies:** ImagingStage

---

### 8. CrossMatchStage

**Purpose:** Match detected sources with reference catalogs

**Responsibilities:**
- Detect sources in image
- Cross-match with NVSS, FIRST, RACS
- Calculate astrometric offsets
- Calculate flux scale corrections
- Store results in database

**Inputs:**
- `image_path` (image with sources)
- `catalog` (nvss/first/racs)

**Outputs:**
- `crossmatch_results` (list of matches)
- `astrometry_offset` (arcseconds)
- `flux_scale` (correction factor)

**Dependencies:** ImagingStage

---

### 9. AdaptivePhotometryStage

**Purpose:** Measure photometry using adaptive channel binning

**Responsibilities:**
- Adaptive channel binning (optimize frequency resolution)
- Forced photometry at known positions
- Variability analysis across epochs
- Detect Extreme Scattering Events (>5σ variability)

**Inputs:**
- `image_path` (image for photometry)
- `source_coordinates` (optional, queries NVSS if not provided)

**Outputs:**
- `photometry_results` (list of measurements)
- `variability_stats` (statistics per source)
- `ese_candidates` (Extreme Scattering Event candidates)

**Dependencies:** ImagingStage

---

## Dependency Resolution

The `PipelineOrchestrator` uses **topological sort** (Kahn's algorithm) to resolve dependencies:

```python
def _topological_sort(self) -> List[str]:
    """Topologically sort stages by dependencies."""
    # Kahn's algorithm
    in_degree = {name: len(deps) for name, deps in self.graph.items()}
    queue = [name for name, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        
        # Reduce in-degree of dependent nodes
        for name, deps in self.graph.items():
            if node in deps:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)
    
    # Check for cycles
    if len(result) != len(self.stages):
        raise ValueError("Circular dependency detected")
    
    return result
```

**Example Dependency Graph:**
```
CatalogSetupStage (no deps)
    ↓
ConversionStage (no deps)
    ↓
CalibrationSolveStage (depends on ConversionStage)
    ↓
CalibrationStage (depends on ConversionStage, CalibrationSolveStage)
    ↓
ImagingStage (depends on CalibrationStage)
    ↓
OrganizationStage (depends on ConversionStage)
ValidationStage (depends on ImagingStage)
CrossMatchStage (depends on ImagingStage)
AdaptivePhotometryStage (depends on ImagingStage)
```

---

## Error Handling

### Retry Policies

Each stage can have a retry policy:

```python
retry_policy = RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_delay=1.0,
    max_delay=60.0
)
```

### Validation

**Input Validation:** `validate()` checks prerequisites before execution
**Output Validation:** `validate_outputs()` checks outputs after execution (if implemented)

### Cleanup

`cleanup()` is **always called**, even on failure, to prevent resource leaks.

---

## Best Practices

### Writing Stages

1. **Keep stages focused:** Single responsibility principle
2. **Validate inputs:** Always implement `validate()`
3. **Validate outputs:** Implement `validate_outputs()` when possible
4. **Handle errors gracefully:** Use cleanup() for resource management
5. **Document dependencies:** Clear docstrings about inputs/outputs
6. **Use immutable context:** Never mutate context directly

### Testing Stages

1. **Unit tests:** Test each stage independently
2. **Mock dependencies:** Use mock stages for testing
3. **Test validation:** Test both valid and invalid inputs
4. **Test error handling:** Test failure scenarios
5. **Test cleanup:** Verify cleanup is called

### Performance

1. **Parallel execution:** Stages without dependencies can run in parallel (future)
2. **Caching:** Cache expensive computations in context metadata
3. **Resource management:** Use ResourceManager for temporary files
4. **Monitoring:** Use PipelineObserver for metrics

---

## Architecture Strengths

1. **Separation of Concerns:** Each stage has a single responsibility
2. **Testability:** Stages can be tested independently
3. **Composability:** Stages can be combined in different workflows
4. **Type Safety:** Pydantic configuration validation
5. **Immutability:** Context immutability prevents bugs
6. **Error Handling:** Retry policies and validation at each stage
7. **Observability:** Logging and metrics at stage boundaries
8. **Dependency Resolution:** Automatic topological sort
9. **Extensibility:** Easy to add new stages
10. **Scientific Rigor:** Output validation ensures correctness

---

## Future Enhancements

1. **Parallel Execution:** Run independent stages in parallel
2. **Checkpointing:** Save state for long-running stages
3. **Distributed Execution:** Run stages on remote workers
4. **Dynamic Dependencies:** Dependencies determined at runtime
5. **Stage Versioning:** Support multiple versions of stages
6. **Stage Composition:** Higher-order stages that compose others

---

## Related Documentation

- [Pipeline Overview](./pipeline_overview.md) - Configuration overview
- [Pipeline Production Features](./pipeline_production_features.md) - Production configuration
- Testing Strategy: `../../../tests/PIPELINE_TESTING_STRATEGY.md` (external file)
- [Directory Architecture](DIRECTORY_ARCHITECTURE.md)

---

**See Also:**
- `src/dsa110_contimg/pipeline/stages.py` - Base class definition
- `src/dsa110_contimg/pipeline/stages_impl.py` - Stage implementations
- `src/dsa110_contimg/pipeline/orchestrator.py` - Orchestrator implementation


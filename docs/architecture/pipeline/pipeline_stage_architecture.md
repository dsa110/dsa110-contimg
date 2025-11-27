# Pipeline Stage Architecture

**Purpose:** Comprehensive guide to the stage-based pipeline architecture  
**Last Updated:** 2025-11-26  
**Status:** Production

---

## Executive Summary

### Pipeline Stages (12 total)

| #   | Stage                       | Line | Purpose                                       | Inputs                                 | Outputs                |
| --- | --------------------------- | ---- | --------------------------------------------- | -------------------------------------- | ---------------------- |
| 1   | **CatalogSetupStage**       | 39   | Build NVSS/FIRST/RAX catalogs for declination | `input_path`                           | `catalog_setup_status` |
| 2   | **ConversionStage**         | 383  | Convert UVH5 → Measurement Set                | `input_path`, `start_time`, `end_time` | `ms_path`              |
| 3   | **CalibrationSolveStage**   | 673  | Solve calibration tables (K, BP, G)           | `ms_path`                              | `calibration_tables`   |
| 4   | **CalibrationStage**        | 1351 | Apply calibration solutions to MS             | `ms_path`, `calibration_tables`        | `ms_path` (calibrated) |
| 5   | **ImagingStage**            | 1746 | Create continuum images via tclean            | `ms_path`                              | `image_path`           |
| 6   | **MosaicStage**             | 2066 | Combine multiple images into mosaic           | `image_paths`                          | `mosaic_path`          |
| 7   | **LightCurveStage**         | 2318 | Compute variability metrics (η, V, σ)         | `source_ids` or `mosaic_path`          | `variable_sources`     |
| 8   | **OrganizationStage**       | 2742 | Organize MS into date-based dirs              | `ms_path`                              | Updated paths          |
| 9   | **ValidationStage**         | 2899 | Astrometry & flux validation                  | `image_path`                           | `validation_results`   |
| 10  | **CrossMatchStage**         | 3070 | Match sources with NVSS/FIRST/RACS            | `detected_sources`                     | `crossmatch_results`   |
| 11  | **AdaptivePhotometryStage** | 3641 | Measure photometry with adaptive binning      | `ms_path`                              | `photometry_results`   |
| 12  | **TransientDetectionStage** | 3912 | Detect new/variable/fading sources            | `detected_sources`                     | `transient_results`    |

> **Source:** `backend/src/dsa110_contimg/pipeline/stages_impl.py`

### Predefined Workflows (4 total)

| Workflow             | Stages                                                                                 | Use Case                         |
| -------------------- | -------------------------------------------------------------------------------------- | -------------------------------- |
| **standard_imaging** | CatalogSetup → Conversion → CalibrationSolve → CalibrationApply → Imaging [+ optional] | Full end-to-end processing       |
| **quicklook**        | CatalogSetup → Conversion → Imaging                                                    | Fast preview without calibration |
| **reprocessing**     | CatalogSetup → Calibration → Imaging                                                   | Re-process existing MS           |
| **streaming**        | Full pipeline with TransientDetection                                                  | Real-time ingest with alerts     |

> **Source:** `backend/src/dsa110_contimg/pipeline/workflows.py`

### Stage Dependency Graph

```text
                    CatalogSetup
                         │
                    Conversion
                         │
                  CalibrationSolve
                         │
                  CalibrationApply
                         │
                      Imaging
                    /    │    \
               Mosaic  Validation  AdaptivePhotometry
                 │        │              │
                 └────CrossMatch    LightCurve
                                        │
                                TransientDetection
```

---

## Overview

The DSA-110 continuum imaging pipeline uses a **stage-based architecture** with
dependency resolution. This design provides:

- **Separation of Concerns:** Each stage has a single, well-defined
  responsibility
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

The `PipelineContext` is an **immutable** data structure that carries state
between stages:

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

**Default behavior (2025-11):** `CrossMatchConfig.catalog_types` now defaults to
`["nvss", "rax"]` so NVSS + RACS are queried automatically, and the RACS strip
resolver allows filenames up to ±6° from the requested declination to match the
12° strip width produced by `build_rax_strip_db`.

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

### 10. MosaicStage

**Purpose:** Create mosaics from groups of imaged MS files

**Responsibilities:**

- Group images by time (configurable, default 10 per mosaic)
- Validate tile quality and consistency
- Create weighted mosaics using optimal overlap handling
- Register mosaics in the products database

**Inputs:**

- `image_paths` (list of image paths from previous imaging stages)
- `ms_paths` (optional, source MS files for metadata)

**Outputs:**

- `mosaic_path` (path to output mosaic FITS file)
- `mosaic_id` (product ID in database)
- `group_id` (mosaic group identifier)

**Dependencies:** ImagingStage

**Configuration:** `MosaicConfig`

- `enabled` (default: True) - Enable mosaic creation
- `ms_per_mosaic` (default: 10) - Number of MS files per mosaic
- `overlap_count` (default: 2) - MS files overlap between mosaics
- `min_images` (default: 5) - Minimum images required
- `enable_photometry` (default: True) - Run photometry after mosaic
- `enable_crossmatch` (default: True) - Run cross-matching after mosaic

---

### 11. LightCurveStage

**Purpose:** Compute variability metrics from photometry measurements

**Responsibilities:**

- Query photometry measurements from products database
- Compute variability metrics (η, V, σ-deviation, χ²/ν)
- Update variability_stats table
- Trigger alerts for ESE candidates exceeding thresholds

**Variability Metrics:**

- **η (eta):** Weighted variance metric, sensitive to variability accounting for
  measurement errors
- **V:** Coefficient of variation (std/mean), fractional variability
- **σ-deviation:** Maximum deviation from mean in units of std (ESE detection)
- **χ²/ν:** Reduced chi-squared relative to constant flux model

**Inputs:**

- `source_ids` (optional, specific sources to process)
- `mosaic_path` (optional, derive sources from mosaic)
- If neither provided, processes all sources with sufficient epochs

**Outputs:**

- `variable_sources` (list of source IDs flagged as variable)
- `ese_candidates` (list of source IDs flagged as ESE candidates)
- `metrics_updated` (number of sources with updated metrics)

**Dependencies:** AdaptivePhotometryStage, MosaicStage (optional)

**Configuration:** `LightCurveConfig`

- `enabled` (default: True) - Enable light curve computation
- `min_epochs` (default: 3) - Minimum epochs required for metrics
- `eta_threshold` (default: 2.0) - η threshold for variable flag
- `v_threshold` (default: 0.1) - V threshold for variable flag
- `sigma_threshold` (default: 3.0) - σ-deviation threshold for ESE detection
- `use_normalized_flux` (default: True) - Use normalized flux values
- `update_database` (default: True) - Update variability_stats table
- `trigger_alerts` (default: True) - Trigger alerts for ESE candidates

---

## Dependency Resolution

The `PipelineOrchestrator` uses **topological sort** (Kahn's algorithm) to
resolve dependencies:

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
    ├── OrganizationStage (depends on ConversionStage)
    ├── ValidationStage (depends on ImagingStage)
    ├── CrossMatchStage (depends on ImagingStage)
    └── MosaicStage (depends on ImagingStage)
            ↓
        AdaptivePhotometryStage (depends on MosaicStage or ImagingStage)
            ↓
        LightCurveStage (depends on AdaptivePhotometryStage, MosaicStage)
```

**Complete Streaming Workflow:**

```
HDF5 → MS → Calibration → Imaging → Mosaic → Photometry → Light Curves
```

---

## Workflow Definitions

The pipeline provides several pre-built workflow compositions in
`dsa110_contimg.pipeline.workflows`. These use the `WorkflowBuilder` to compose
stages with dependencies, retry policies, and timeouts.

### `streaming_workflow()`

The **complete end-to-end streaming workflow** implements the full data path
from HDF5 ingestion through transient detection. This is the primary workflow
for production streaming operations.

```python
from dsa110_contimg.pipeline.workflows import streaming_workflow
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_env()
workflow = streaming_workflow(config)
result = await workflow.execute(context)
```

**Stages (11 total):**

| Stage                 | Timeout | Description                                    |
| --------------------- | ------- | ---------------------------------------------- |
| `catalog_setup`       | 5 min   | Initialize calibrator catalog                  |
| `conversion`          | 30 min  | UVH5 → Measurement Set                         |
| `calibration_solve`   | 15 min  | Solve delay, bandpass, gain tables             |
| `calibration_apply`   | 10 min  | Apply calibration to MS                        |
| `imaging`             | 30 min  | WSClean imaging                                |
| `mosaic`              | 60 min  | Combine images into mosaic (if enabled)        |
| `validation`          | 5 min   | QA checks (if enabled)                         |
| `crossmatch`          | 10 min  | Catalog cross-matching (if enabled)            |
| `adaptive_photometry` | 20 min  | Source extraction & photometry (if enabled)    |
| `light_curve`         | 10 min  | Time-series light curves (requires photometry) |
| `transient_detection` | 5 min   | ESE/transient detection (if enabled)           |

**Conditional Inclusion:**

Stages are conditionally included based on configuration flags:

```python
config = PipelineConfig(
    mosaic=MosaicConfig(enabled=True),        # Include mosaic stage
    validation=ValidationConfig(enabled=True), # Include validation stage
    crossmatch=CrossMatchConfig(enabled=True), # Include cross-match stage
    photometry=PhotometryConfig(enabled=True), # Include photometry stage
    light_curve=LightCurveConfig(enabled=True),# Include light curve stage
    transient_detection=TransientDetectionConfig(enabled=True),
)
```

**Dependency Graph:**

```
catalog_setup
     ↓
conversion
     ↓
calibration_solve
     ↓
calibration_apply
     ↓
imaging
     ↓
     ├── mosaic (if enabled)
     │      ↓
     │      └─┬── validation (if enabled)
     │        │
     │        └── crossmatch (depends on validation if enabled)
     │
     └── adaptive_photometry (if enabled)
            ↓
         light_curve (if enabled, requires photometry + mosaic)
            ↓
         transient_detection (if enabled)
```

**Retry Policy:**

All stages use exponential backoff retry:

- Max attempts: 3
- Initial delay: 5 seconds
- Max delay: 60 seconds

### Other Workflows

| Workflow                      | Description                                    |
| ----------------------------- | ---------------------------------------------- |
| `standard_imaging_workflow()` | Convert → Calibrate → Image (production)       |
| `quicklook_workflow()`        | Convert → Image (no calibration, fast preview) |
| `reprocessing_workflow()`     | Calibrate → Image (MS already exists)          |

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
**Output Validation:** `validate_outputs()` checks outputs after execution (if
implemented)

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

1. **Parallel execution:** Stages without dependencies can run in parallel
   (future)
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
- [Pipeline Production Features](./pipeline_production_features.md) - Production
  configuration
- Testing Strategy: `../../../tests/PIPELINE_TESTING_STRATEGY.md` (external
  file)
- [Directory Architecture](../architecture/DIRECTORY_ARCHITECTURE.md)

---

**See Also:**

- `backend/src/dsa110_contimg/pipeline/stages.py` - Base class definition
- `backend/src/dsa110_contimg/pipeline/stages_impl.py` - Stage implementations
- `backend/src/dsa110_contimg/pipeline/orchestrator.py` - Orchestrator implementation

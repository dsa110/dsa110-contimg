# Pipeline Module

Stage-based processing pipeline for DSA-110 data.

## Overview

The pipeline module orchestrates the full data processing workflow:

```
Ingest → Convert → Calibrate → Image → Extract → Catalog
```

Each step is implemented as a **stage** that can run independently or as part of
the coordinated pipeline.

## Key Files

| File             | Purpose                          |
| ---------------- | -------------------------------- |
| `stages.py`      | Stage definitions and interfaces |
| `stages_impl.py` | Stage implementations            |
| `coordinator.py` | Pipeline orchestration           |
| `state.py`       | Pipeline state management        |

## Pipeline Stages

| Stage            | Input         | Output                |
| ---------------- | ------------- | --------------------- |
| `IngestStage`    | UVH5 files    | Indexed file metadata |
| `ConvertStage`   | File groups   | Measurement Sets      |
| `CalibrateStage` | MS files      | Calibrated MS         |
| `ImagingStage`   | Calibrated MS | FITS images           |
| `ExtractStage`   | FITS images   | Source catalogs       |
| `CatalogStage`   | Sources       | Cross-matched catalog |

## Running the Pipeline

```python
from dsa110_contimg.pipeline.coordinator import PipelineCoordinator

coordinator = PipelineCoordinator()
coordinator.run(
    start_time="2025-01-01T00:00:00",
    end_time="2025-01-01T12:00:00",
)
```

## Stage Implementation

Each stage follows the pattern:

```python
class MyStage(PipelineStage):
    def run(self, context: PipelineContext) -> StageResult:
        # 1. Get input from context
        # 2. Process data
        # 3. Return result with output artifacts
        pass
```

## State Tracking

Pipeline state is tracked in the products database:

- `/data/dsa110-contimg/state/db/products.sqlite3`

Job status visible via API: `GET /api/v1/jobs/`

# Streaming Data Pipeline Module

This module provides a modular, refactored implementation of the DSA-110 streaming
data pipeline. It replaces the monolithic `streaming_converter.py` with a cleaner
architecture that is easier to maintain, test, and extend.

## Architecture

```
streaming/
├── __init__.py          # Module exports and public API
├── cli.py               # Command-line interface
├── launcher.py          # Entry point for console script
├── queue.py             # SubbandQueue - SQLite-backed work queue
├── watcher.py           # StreamingWatcher - Filesystem monitoring
├── worker.py            # StreamingWorker - Pipeline orchestrator
└── stages/
    ├── __init__.py      # Stage exports
    ├── calibration.py   # CalibrationStage - Calibration solving/application
    ├── conversion.py    # ConversionStage - HDF5 → MS conversion
    ├── imaging.py       # ImagingStage - MS imaging
    ├── mosaic.py        # MosaicStage - Multi-observation mosaics
    └── photometry.py    # PhotometryStage - Source measurement
```

## Usage

### As a Console Script

After installing the package:

```bash
# Run the streaming pipeline
dsa110-stream \
    --input-dir /data/incoming \
    --output-dir /data/ms \
    --queue-db state/db/pipeline.sqlite3 \
    --enable-calibration-solving \
    --enable-photometry
```

### As a Python Module

```python
from dsa110_contimg.conversion.streaming import (
    SubbandQueue,
    StreamingWatcher,
    StreamingWorker,
)
from dsa110_contimg.conversion.streaming.worker import WorkerConfig
from pathlib import Path

# Create queue
queue = SubbandQueue(
    db_path=Path("state/db/pipeline.sqlite3"),
    expected_subbands=16,
)

# Create worker configuration
config = WorkerConfig(
    input_dir=Path("/data/incoming"),
    output_dir=Path("/data/ms"),
    scratch_dir=Path("/stage"),
    queue_db=Path("state/db/pipeline.sqlite3"),
    registry_db=Path("state/db/pipeline.sqlite3"),
    enable_calibration_solving=True,
    enable_photometry=True,
)

# Create and run worker
worker = StreamingWorker(config, queue)
worker.run()
```

### Running Individual Stages

Each stage can be used independently:

```python
from dsa110_contimg.conversion.streaming.stages import ConversionStage
from dsa110_contimg.conversion.streaming.stages.conversion import ConversionConfig

config = ConversionConfig(
    output_dir=Path("/data/ms"),
    scratch_dir=Path("/stage"),
    products_db=Path("state/db/pipeline.sqlite3"),
)

stage = ConversionStage(config)
result = stage.execute(
    group_id="2025-10-02T00:12:00",
    hdf5_files=["/data/incoming/2025-10-02T00:12:00_sb00.hdf5", ...],
)
```

## Key Components

### SubbandQueue

SQLite-backed queue that:

- Tracks incoming subband files
- Groups files by observation time (5-minute chunks)
- Manages processing state (pending → processing → completed/failed)
- Handles concurrent access with WAL mode and atomic transactions

### StreamingWatcher

Filesystem monitoring using watchdog:

- Watches for new HDF5 files in input directory
- FUSE-aware locking to wait for file writes to complete
- Validates HDF5 file integrity before registration
- Falls back to polling if watchdog unavailable

### StreamingWorker

Pipeline orchestrator that:

- Polls queue for pending work
- Runs processing through pipeline stages
- Manages state machine transitions
- Handles disk space monitoring
- Records metrics for observability

### Pipeline Stages

Each stage follows a common pattern:

- `execute()`: Main processing logic
- `validate()`: Pre-execution validation
- `cleanup()`: Resource cleanup

Stages are composable and can be used independently or orchestrated by StreamingWorker.

## Configuration

### Environment Variables

- `CASA_LOGDIR`: Directory for CASA log files (default: `/tmp/casa_logs`)
- `OMP_NUM_THREADS`: Number of OpenMP threads (default: 4)
- `OPENBLAS_NUM_THREADS`: OpenBLAS threads (default: 1)
- `MKL_NUM_THREADS`: Intel MKL threads (default: 1)

### Command-Line Options

See `dsa110-stream --help` for full list of options.

Key options:

- `--input-dir`: Watch directory for incoming HDF5 files
- `--output-dir`: Output directory for MS files and images
- `--queue-db`: Path to SQLite database for queue/products
- `--enable-calibration-solving`: Enable automatic calibration
- `--enable-photometry`: Enable source measurement
- `--enable-mosaic-creation`: Enable mosaic creation for complete groups

## Migration from streaming_converter.py

The new module maintains backwards compatibility with the original interface.
To migrate:

1. Replace imports:

   ```python
   # Old
   from dsa110_contimg.conversion.streaming_converter import QueueDB

   # New
   from dsa110_contimg.conversion.streaming import SubbandQueue
   ```

2. Update systemd service to use new console script:

   ```ini
   [Service]
   ExecStart=/path/to/venv/bin/dsa110-stream --input-dir /data/incoming --output-dir /data/ms
   ```

3. Remove shell wrapper scripts (no longer needed)

## Testing

```bash
# Run unit tests
pytest tests/unit/test_streaming*.py

# Run with specific test file
pytest tests/unit/test_streaming_queue.py -v
```

## Observability

The module integrates with the pipeline's observability infrastructure:

- Processing state machine for crash recovery
- Disk space monitoring with configurable thresholds
- Metrics recording for Prometheus/Grafana
- Structured logging with configurable levels

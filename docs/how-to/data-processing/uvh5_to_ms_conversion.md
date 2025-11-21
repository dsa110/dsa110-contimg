# DSA-110 UVH5 to CASA Measurement Set Converter

This repository now focuses on two supported conversion paths:

- `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py` – batch
  converter invoked by the streaming service.
- `src/dsa110_contimg/conversion/streaming/streaming_converter.py` – real-time
  daemon that watches an ingest directory and dispatches the batch converter.

Legacy tools (the dsacalib wrappers and the old `UnifiedHDF5Converter`) have
been relocated to `pipeline/legacy/` for archival reference.

## Supported Entry Points

- `python -m dsa110_contimg.conversion.streaming.streaming_converter ...` – run
  the streaming daemon directly for manual testing or non-systemd environments.
- `systemctl enable --now contimg-stream.service contimg-api.service` – deploy
  via the units in `ops/systemd/contimg-stream.service` and
  `ops/systemd/contimg-api.service` (adjust ExecStart paths as needed).
- `from dsa110_contimg.conversion import convert_subband_groups_to_ms` –
  programmatic access to the batch converter used by the streaming worker.

## Legacy Code

The historical utilities (`dsa110_uvh5_to_ms.py`, `UnifiedHDF5Converter`, etc.)
are preserved in `pipeline/legacy/conversion/` and `pipeline/legacy/scripts/`.
They are no longer maintained and should not be used for new automation.

## Staging & Storage Strategy

The converter uses a two-tier staging approach combined with direct-to-organized
writing:

### Direct-to-Organized Writing

MS files are written directly to organized, date-based directory structures:

- **Science MS**: `ms/science/YYYY-MM-DD/<timestamp>.ms`
- **Calibrator MS**: `ms/calibrators/YYYY-MM-DD/<timestamp>.ms`
- **Failed MS**: `ms/failed/YYYY-MM-DD/<timestamp>.ms`

This is achieved using a `path_mapper` function that computes organized paths
before conversion:

```python
from dsa110_contimg.utils.ms_organization import create_path_mapper

path_mapper = create_path_mapper(
    ms_base_dir=Path('/stage/dsa110-contimg/ms'),
    is_calibrator=False,
    is_failed=False
)

convert_subband_groups_to_ms(
    ...,
    path_mapper=path_mapper  # Direct-to-organized writing
)
```

**Benefits:**

- No post-conversion file moves
- Database always has correct paths
- Better performance (eliminates move operations)

### Staging Strategy

- **tmpfs (RAM) staging**: When enabled (`stage_to_tmpfs=True`) and sufficient
  free space exists under `tmpfs_path` (default `/dev/shm`), the MS is written
  to RAM first, then atomically moved into the final organized location. A
  conservative 80% free-space threshold is used to avoid exhausting tmpfs.
  - Relevant kwargs: `stage_to_tmpfs=True`, `tmpfs_path="/dev/shm"`.

- **Scratch SSD staging**: For the per‑subband writer path, intermediate
  single‑subband MS parts are created under a scratch directory and
  concatenated. Set `scratch_dir` to a fast SSD (e.g., `/stage/dsa110-contimg`)
  to minimize I/O contention; otherwise the output directory is used.
  - Relevant kwargs: `scratch_dir="/stage/dsa110-contimg"` (optional),
    `direct_ms=True/False`, `parallel_subband=True/False`.

- **Finalization**: If tmpfs staging was used, the staged MS is moved (or
  copy‑fallback) to the final organized destination. Imaging columns are ensured
  post‑write, and optional MODEL_DATA initialization can be applied afterward.

This strategy keeps write‑amplification low (concat parts locally, single move
into place), leverages RAM when available for best throughput, and writes
directly to organized locations for consistent file management.

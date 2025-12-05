---
description: Debugging, logging, and observability practices
applyTo: "**"
---

# Debugging and Logging

- **Logs to check**:
  - `/data/dsa110-contimg/state/logs/pipeline.log`
  - `/data/dsa110-contimg/state/logs/api.log`
  - `journalctl -u contimg-stream -f` for streaming converter
- **Structured logging**: Use `pipeline/structured_logging` helpers and `get_logger`. Include `component`, `group_id`, `correlation_id` when available.
- **Metrics**: Record metrics via `pipeline/metrics` for detection/conversion stages.
- **Retries and circuit breakers**: Use `pipeline/retry_enhanced`, `pipeline/circuit_breaker` patterns. Add DLQ entries with context on failures.
- **DB inspection**:
  - Pipeline queue: `SELECT group_id, state, processing_stage FROM ingest_queue ORDER BY received_at DESC LIMIT 10;`
  - Performance: `SELECT group_id, total_time, load_time, phase_time, write_time FROM performance_metrics ORDER BY recorded_at DESC LIMIT 10;`
  - HDF5 index: `SELECT group_id, COUNT(*) FROM hdf5_file_index GROUP BY group_id;`
- **MS sanity checks**: Ensure MS tables exist (`ANTENNA`, `SPECTRAL_WINDOW`, `MAIN`) and antenna positions use ITRF.
- **Repros**: Capture minimal failing input (one group, one record) and exact command/env used.
- **Fallbacks**: Avoid silent fallbacks; log warnings at most, errors on failure paths.
- **Caching**: When using caches (e.g., variability stats), log cache hits/misses sparingly; ensure invalidation paths exist.


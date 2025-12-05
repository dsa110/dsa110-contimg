---
description: Performance, scaling, and I/O guidance
applyTo: "**"
---

# Performance and Scaling

- **I/O locality**: Use `/scratch` or `/stage` for builds, temp files, and conversions; avoid heavy reads/writes on `/data` (HDD).
- **Batching**: Load subbands in batches (default 4) to control memory; combine to 16 subbands for full bandwidth.
- **Memory**: A full 16-subband group can use 2-4 GB RAM; avoid unbounded concatenations or in-memory copies.
- **Threading**: Tune OpenMP/MKL threads (`--omp-threads 4` on 8-core, `--omp-threads 8` on 16-core) to prevent oversubscription.
- **Streaming converter**: Monitors ingest queue; watch `performance_metrics` for total/load/phase/write times. Groups >4.5 min indicate I/O bottlenecks.
- **Precomputation**: Pointing tracker triggers catalog/calibrator prep on Dec changes; avoid disabling unless necessary.
- **Filenames**: Normalization reduces clustering overhead—prefer normalized workflows.
- **Frontend builds**: Use `npm run build:scratch` to keep Vite builds off HDD.
- **Docs builds**: Build MkDocs to `/scratch/mkdocs-build/site` then move to `/data/dsa110-contimg/site`.
- **Logging overhead**: Prefer structured, leveled logs; avoid chatty debug in tight loops.


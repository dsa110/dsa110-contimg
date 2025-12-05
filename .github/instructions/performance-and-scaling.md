---
description: Performance, scaling, and I/O guidance
applyTo: "**"
---

# Performance and Scaling

- **I/O locality**: Put heavy builds and temp files on fast storage; avoid heavy reads/writes on slow or production-only volumes.
- **Batching**: Process data in batches to control memory; avoid unbounded concatenations or full in-memory copies.
- **Memory**: Estimate footprint before running; stream or chunk large data when possible.
- **Threading**: Set thread/worker counts to avoid oversubscription relative to available cores.
- **Pipelines/queues**: Monitor throughput and latency metrics; investigate stragglers or long-running groups.
- **Precomputation**: Keep useful precomputation enabled; only disable with a clear reason.
- **Normalization**: Normalize inputs early to reduce grouping or clustering overhead.
- **Builds**: Run heavy builds (frontend/docs) on fast storage and move artifacts to their final destinations afterward.
- **Logging overhead**: Prefer structured, leveled logs; avoid chatty debug in tight loops.

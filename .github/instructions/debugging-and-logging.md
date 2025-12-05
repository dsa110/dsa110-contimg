---
description: Debugging, logging, and observability practices
applyTo: "**"
---

# Debugging and Logging

- **Logs to check**: Inspect relevant application/service logs and system logs for errors and warnings.
- **Structured logging**: Use the project’s structured logging utilities; include context (component, IDs, correlation IDs) when available.
- **Metrics**: Record metrics around key operations to track latency, throughput, and failures.
- **Retries and circuit breakers**: Use existing retry/circuit-breaker patterns; capture context when operations fail.
- **Data inspection**: Query state with targeted reads instead of full scans; verify indexes are used.
- **Sanity checks**: Ensure outputs contain expected tables/fields/files before proceeding.
- **Repros**: Capture minimal failing input (one record/group) and the exact command/environment used.
- **Fallbacks**: Avoid silent fallbacks; log warnings at most and errors on failure paths.
- **Caching**: Log cache hits/misses sparingly; ensure invalidation paths exist.

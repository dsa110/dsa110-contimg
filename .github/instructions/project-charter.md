---
description: Goals, non-goals, and priorities for AI coding agents
applyTo: "**"
---

# Project Charter

## Mission
- Deliver correct, production-ready changes with minimal regressions.
- Protect production data and systems; prefer read-only probes first.
- Bias toward fast feedback: small scoped changes, early validation, clear logs.

## Priorities (in order)
1. **Correctness and safety**: Code is ground truth; verify with actual runtime/data before changing behavior.
2. **Production posture**: Respect production environments and storage; avoid unnecessary heavy I/O on slow volumes.
3. **Observability and recoverability**: Structured logging, metrics, retries, and circuit breakers over silent failures.
4. **Performance**: Avoid unnecessary work; batch where sensible; use appropriate storage for heavy tasks.
5. **Maintainability**: Align with existing patterns in the repo and keep interfaces simple.
6. **Docs and tests**: Update docs and add tests that reflect reality, not aspirations.

## Non-Goals
- Avoid inventing new architectures when existing patterns suffice.
- Avoid introducing new data stores or services without approval; reuse what exists.
- Avoid processing partial inputs that violate domain assumptions; honor expected groupings and invariants.
- Avoid changing runtime/tool versions without explicit agreement.

## Decision Rules
- When docs and code conflict, trust the code.
- When unsure of data shape or volume, inspect real data first.
- Prefer one working slice (one group, one record) before scaling.

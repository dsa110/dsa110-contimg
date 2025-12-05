---
description: Goals, non-goals, and priorities for AI agents on dsa110-contimg
applyTo: "**"
---

# Project Charter

## Mission
- Deliver correct, production-ready changes to the DSA-110 continuum imaging pipeline with minimal regressions.
- Protect production data and pipelines; prefer read-only probes first.
- Bias toward fast feedback: small scoped changes, early validation, clear logs.

## Priorities (in order)
1. **Correctness and safety**: Code is ground truth; verify with actual data and databases before changing behavior.
2. **Production posture**: Respect prod paths (`/data`, `/stage`, `/scratch`), avoid slow HDD builds, and keep CASA compatibility.
3. **Observability and recoverability**: Structured logging, metrics, retries, and circuit breakers over silent failures.
4. **Performance**: Avoid unnecessary I/O on `/data`; use batching and scratch storage.
5. **Maintainability**: Align with existing patterns in `backend/src/dsa110_contimg/` and `frontend/src/`.
6. **Docs and tests**: Update docs and add tests that reflect reality, not aspirations.

## Non-Goals
- Do not invent new architectures; extend or refine existing patterns first.
- Do not add new data stores; stay with SQLite (or project-defined PostgreSQL for ABSURD).
- Do not process single subbands in isolation; always group 16 subbands.
- Do not diverge from casa6/pyuvdata pinned versions without explicit approval.

## Decision Rules
- When docs and code conflict, trust the code (`ground-truth.instructions.md`).
- When unsure of data shape or volume, query the database first (`data-first.instructions.md`).
- Prefer one working slice (one group, one record) before scaling.


---
description: Required tests and checks before shipping changes
applyTo: "**"
---

# Testing Checklist

- **Scope the fastest test**: run the smallest relevant test (unit/contract) before full suite.
- **Python backend**:
  - `conda activate casa6`
  - `cd backend`
  - Unit/contract: `python -m pytest tests/unit/ -v` or `tests/contract/ -v`
  - Integration (CASA): `python -m pytest tests/integration/ -v` when MS/CASA involved
  - Lint/format: `ruff check src/`; format with `ruff format src/` if needed
- **Frontend**:
  - `cd frontend`
  - `npm run lint`
  - `npm run test` (or targeted `npm test -- <file>`)
  - Type checks when relevant: `npm run type-check`
- **Data-sensitive ops**:
  - For converters, verify a single group first (16 subbands) and inspect MS key tables exist.
  - For DB changes, run read-only queries to confirm counts/shapes.
- **Performance-sensitive changes**: capture before/after timings or counts; note storage path (`/scratch` vs `/data`).
- **Failure paths**: exercise retries/circuit breakers/DLQ where modified.
- Record what was run in the PR/summary; if a check was skipped, state why.


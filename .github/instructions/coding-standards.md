---
description: Coding standards for backend and frontend changes
applyTo: "**"
---

# Coding Standards

## General
- Code is truth; mirror active patterns in `backend/src/dsa110_contimg/` and `frontend/src/`.
- Prefer explicit, pure functions and typed interfaces (pydantic models, Protocols, TS types).
- Keep functions focused; avoid hidden globals and side effects.

## Python (backend)
- Python 3.11 in casa6; stay compatible with CASA 6.7 and pyuvdata 3.2.4.
- Imports: standard library, third party, local; no unused imports.
- Types: use type hints; prefer `typing` Protocols/TypedDict for contracts.
- Logging: use structured logging helpers (`pipeline/structured_logging`, `get_logger`), include correlation IDs when available.
- Database: SQLite only unless in ABSURD PostgreSQL; use adapters/repos, not raw file scans when DBs exist.
- File/group rules: always handle 16 subbands; use time-windowing or normalization utilities, never process lone `_sbXX` files.
- Style/tools: follow ruff (`ruff check src/`), `ruff format` for formatting. Line length 100.

## TypeScript/React (frontend)
- Use React Query for server state; Zustand for client state.
- Prefer functional components, hooks, and explicit props typing.
- Data fetching: centralize in hooks/api; handle loading/error states.
- Routing: React Router v7 patterns; avoid ad-hoc history manipulation.
- Linting/format: `npm run lint`, `npm run lint:fix`; follow existing Tailwind/utility classes patterns.

## Error Handling
- Fail fast with clear messages; avoid bare `except` or silent passes.
- Add retries/circuit breakers where patterns exist (pipeline retry/circuit breaker utilities).
- Return structured errors (error_code, message) at API boundaries.

## I/O and Paths
- Prefer `/scratch` or `/stage` for temp/build outputs; `/data` is HDD and production.
- Never create new top-level data stores; keep SQLite DBs in `state/db/` or `state/catalogs/`.


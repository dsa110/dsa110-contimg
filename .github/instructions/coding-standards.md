---
description: Coding standards for backend and frontend changes
applyTo: "**"
---

# Coding Standards

## General
- Code is truth; mirror active patterns in the repository.
- Prefer explicit, pure functions and typed interfaces; avoid hidden globals and side effects.
- Keep functions focused and small; favor clarity over cleverness.

## Python (backend)
- Match the project’s runtime and dependency constraints.
- Imports: standard library, third party, local; no unused imports.
- Types: use type hints; prefer Protocols/TypedDict for contracts.
- Logging: use structured logging utilities; include correlation IDs when available.
- Data access: use repositories/adapters and existing stores; avoid ad-hoc file scans when indexed data exists.
- Style/tools: follow the repo’s linters/formatters and line-length rules.

## TypeScript/React (frontend)
- Prefer functional components, hooks, and explicit props typing.
- Match the project’s state management and data-fetching patterns; handle loading and error states.
- Follow established routing/navigation approaches; avoid ad-hoc history manipulation.
- Use the repo’s lint/format commands and styling conventions.

## Error Handling
- Fail fast with clear messages; avoid bare `except` or silent passes.
- Add retries/circuit breakers where patterns exist.
- Return structured errors (error_code, message) at API boundaries.

## I/O and Paths
- Use appropriate storage for temp/build outputs; avoid polluting production paths.
- Do not introduce new data stores or directories without alignment and approval; follow existing conventions.

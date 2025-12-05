---
description: Required tests and checks before shipping changes
applyTo: "**"
---

# Testing Checklist

- **Scope the fastest test**: run the smallest relevant test (unit/contract) before full suite.
- **Backend**: run targeted unit/contract/integration tests using the project’s test command; run linters/formatters.
- **Frontend**: run lint, unit tests, and type checks using project scripts; target the smallest scope first.
- **Data-sensitive ops**: verify a single record/group first; run read-only queries to confirm counts/shapes before writes.
- **Performance-sensitive changes**: capture before/after timings or counts; note environment and storage choices.
- **Failure paths**: exercise retries/circuit breakers/dead-letter handling where modified.
- Record what was run in the PR/summary; if a check was skipped, state why.

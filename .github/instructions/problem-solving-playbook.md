---
description: Problem solving loop for AI agents
applyTo: "**"
---

# Problem-Solving Playbook

1) **Clarify the ask**
- Restate the goal, inputs, outputs, and constraints (envs, data paths, perf targets).
- Identify prod vs experimental subsystems (see ground-truth hierarchy).

2) **Inspect reality first**
- Read the relevant code before trusting docs.
- Query existing data/DBs (SQLite in `/data/dsa110-contimg/state/db/`) before writing code.
- Check scale (counts) before scanning directories or tables.

3) **Plan**
- Outline 2-5 steps; pick a single narrow slice first (one group/record).
- Choose the fastest validation path (unit/contract test, dry-run, small sample).

4) **Implement**
- Follow existing patterns in `backend/src/dsa110_contimg/` and `frontend/src/`.
- Keep changes small; prefer pure functions and explicit parameters.
- Use scratch/NVMe for I/O-heavy work; avoid `/data` for builds.

5) **Validate**
- Run targeted tests (`python -m pytest ...`, `npm run test`, `npm run lint`, `ruff check`).
- For conversions, sanity-check counts/shapes and key tables (MS, SQLite indexes).
- Log or print minimal, structured evidence.

6) **Document and decide next**
- Update module docs/READMEs if behavior changes.
- Summarize risks, follow-ups, and how to run verification.

Defaults: fail closed on ambiguity, add guardrails (timeouts, retries, logging), and prefer incremental rollout.


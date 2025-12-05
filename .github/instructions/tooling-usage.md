---
description: Canonical commands for build, test, lint, and tooling
applyTo: "**"
---

# Tooling Usage

## Environments
- Activate the project’s expected runtime (virtualenv/conda) before running commands.
- Use fast storage for heavy builds and temp files when available.

## Backend (Python)
- Use project-defined commands for tests, lint, formatting, and type checks.
- Run services via documented entry points; avoid ad-hoc scripts.
- Apply database migrations using the project’s migration tooling.

## Conversion/CLI
- Use documented CLI commands and flags for batch or single operations; prefer dry-run options first.
- Configure inputs/outputs via parameters or environment variables instead of hardcoded paths.

## Frontend (React/Vite)
- Use project scripts for install, dev server, build, lint, tests, type checks, Storybook/E2E (if applicable).
- For large builds, use fast storage and avoid polluting production data locations.

## Docs/Search
- Use project-provided commands for building docs or indexing search; keep heavy builds off slow storage when possible.

## Storage Paths
- Keep temp/build artifacts in designated scratch/working locations.
- Avoid writing heavy outputs to production data paths; clean up temporary files.

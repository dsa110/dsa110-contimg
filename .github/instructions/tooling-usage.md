---
description: Canonical commands for build, test, lint, and tooling
applyTo: "**"
---

# Tooling Usage

## Environments
- Activate casa6 for backend Python: `conda activate casa6`
- Use NVMe scratch for heavy builds: set `TMPDIR=/scratch` where applicable.

## Backend (Python)
- Tests: `cd backend && python -m pytest tests/unit/ -v` (or `tests/contract/`, `tests/integration/`)
- Lint: `cd backend && ruff check src/`
- Format: `cd backend && ruff format src/`
- Run API: `cd backend && uvicorn dsa110_contimg.api.app:app --reload --host 0.0.0.0 --port 8000`
- Alembic migrations: `cd backend && alembic upgrade head`

## Conversion/CLI
- Batch groups: `python -m dsa110_contimg.conversion.cli groups <input_dir> <output_dir> <start> <end> [--dry-run]`
- Single file: `python -m dsa110_contimg.conversion.cli single <uvh5> <ms_path>`
- Streaming: `PIPELINE_DB=/data/dsa110-contimg/state/db/pipeline.sqlite3 python -m dsa110_contimg.conversion.streaming.streaming_converter ...`

## Frontend (React/Vite)
- Install deps: `cd frontend && npm install`
- Dev server: `npm run dev`
- Build (scratch): `npm run build:scratch`
- Lint: `npm run lint`; Tests: `npm run test`; Type check: `npm run type-check`
- Storybook: `npm run storybook`; E2E: `npm run test:e2e`

## Docs/Search
- DocSearch: `python -m dsa110_contimg.docsearch.cli search "<query>"`; reindex: `python -m dsa110_contimg.docsearch.cli index`
- MkDocs build on scratch: `mkdocs build -f mkdocs.yml -d /scratch/mkdocs-build/site`

## Storage Paths
- HDD: `/data` (slow; prod data); NVMe: `/stage`, `/scratch`; tmpfs: `/dev/shm`
- Products/DBs live in `/data/dsa110-contimg/state/`; Measurement Sets in `/stage/dsa110-contimg/`


# Dashboard Guide

Unified guide for using and developing the Dashboard: quick start, development
workflow, deployment, and testing — with links to reference and conceptual docs.

## Quick Start (local dev)

```bash
# Backend
cd /data/dsa110-contimg
conda activate casa6
uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd /data/dsa110-contimg/frontend
conda activate casa6
npm run dev -- --host 0.0.0.0 --port 5173
```

Open http://localhost:5173

## Development Workflow

- API contracts: `docs/reference/dashboard_backend_api.md`
- Client: `frontend/src/api/` (axios client, React Query hooks)
- Components & Pages: `frontend/src/components` and `frontend/src/pages`
- Common pitfalls: see Prettier and hooks in the pre-commit

## Quick Start Warnings

- Use casa6 for backend development and tests.
- Ensure Vite proxy points to the correct API base (`/api`).
- Avoid console.log in production code; use the logger utilities.

## Sky View (folded from plan)

- Image gallery filters rely on Products endpoints (type/pbcor/date/noise).
- Image detail uses JS9; prefer FITS with correct WCS for overlays.
- Catalog overlay validation lives in Validation/QA endpoints.

## Deployment

- Docker Compose: bring up API + UI; see Streaming Guide → Deployment for steps
- systemd: run API as a service; UI via static hosting or dev server
- Safe start: `docs/operations/starting_dashboard_safely.md`

## Testing

- Unit: `frontend/src/components/**/*.{test.ts, test.tsx}`
- E2E: `frontend/tests/e2e/`
- Troubleshooting: refresh cache, verify API reachable, watch console errors

## Feature Overview

- Status & Health, Streaming Control, Mosaics, Sources, Sky View, QA
- Cheatsheet: `docs/reference/control-panel-cheatsheet.md`

## References

- API reference: `docs/reference/dashboard_backend_api.md`
- Concepts: architecture, state management, data models under `docs/concepts/`

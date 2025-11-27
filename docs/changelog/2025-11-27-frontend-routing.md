# 2025-11-27 — Frontend Routing & Validation Notes

## What Changed

- Enabled strict TypeScript-and-ESLint enforcement across the dashboard and
  added `.eslintignore` to keep linting fast.
- Added Zod-based validation for the pipeline status API and surfaced the parsed
  metrics inside `PipelineStatusSection`.
- Created `/ui` preview smoke tests plus a `test:routes` npm script so we can
  validate the Vite preview base path locally under the casa6 Node runtime.
- Refactored the legacy route integration tests to use
  `window.history.pushState` followed by a direct `<App />` render, eliminating
  the nested-router invariant and matching production navigation more closely.

## How To Verify

Run the standard frontend checks from `/data/dsa110-contimg/frontend` with the
casa6 toolchain on PATH:

```bash
PATH="/opt/miniforge/envs/casa6/bin:$PATH" npm run lint
PATH="/opt/miniforge/envs/casa6/bin:$PATH" npm run type-check
PATH="/opt/miniforge/envs/casa6/bin:$PATH" npm run test:routes
```

All commands should pass without warnings; the route suites now emit zero router
nesting errors.

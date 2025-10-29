# Documentation Audit (2025-10-23)

This report lists MkDocs pages and any items that appear out-of-date or inconsistent with the current codebase and deployment.

## Summary of Flags

- CLI, services, and module paths are largely consistent. A few docs reference legacy paths or omit newer API endpoints and options.

## Detailed Findings

- docs/pipeline/README_uvh5_to_ms.md
  - Flag: Mentions “pipeline/scripts/dsa110-streaming-converter.service”. Current unit lives at `ops/systemd/contimg-stream.service`.
  - Suggestion: Replace the path reference; also add `contimg-api.service` mention where appropriate.

- docs/pipeline/streaming_converter_README.md
  - Status: Mostly aligned. Shows systemd example that matches `ops/systemd/contimg-stream.service` options.
  - Suggestion: Add `--queue-db` and `--registry-db` environment-pass-through reference consistent with `ops/docker/docker-compose.yml` and `ops/systemd/contimg-stream.service`.

- docs/reference/cli.md
  - Status: Good coverage of streaming worker, imaging worker, orchestrator, and downsample unified CLI.
  - Suggestion: Add `conversion/cli.py` top-level unified CLI (if intended for users) or confirm it’s internal only. Add calibration and catalog CLIs already present in code.
    - Proposed add: `python -m dsa110_contimg.calibration.cli --help`, `python -m dsa110_contimg.calibration.catalog_cli --help`.

- docs/reference/api.md
  - Status: Lists `/api/status`, `/api/products`, `/api/calibrator_matches`, `/api/ms_index`, `/api/reprocess/{group_id}`.
  - Suggestion: Add `/api/qa`, `/api/qa/file/{group}/{name}`, and `/api/metrics/system` + `/api/metrics/system/history` present in `src/dsa110_contimg/api/routes.py`.

- docs/ops/deploy-systemd.md
  - Status: Minimal. Mentions enabling `contimg-stream.service` and `contimg-api.service`.
  - Suggestion: Include env file keys from `ops/systemd/contimg.env` (CONTIMG_INPUT_DIR, OUTPUT_DIR, QUEUE_DB, REGISTRY_DB, PRODUCTS_DB, STATE_DIR, LOG_LEVEL, EXPECTED_SUBBANDS, CHUNK_MINUTES, MONITOR_INTERVAL). Link to `ops/systemd/contimg-stream.service` for full command example.

- docs/ops/deploy-docker.md
  - Status: Aligned with Makefile/docker-compose. Suggest expanding environment variables table (same keys as above) and mention `make compose-up-scheduler`.

- docs/quickstart.md
  - Status: Consistent. Uses compose and systemd flows. Mentions `PIPELINE_TELESCOPE_NAME` and optional `CASACORE_DATA` overlay.
  - Suggestion: Add quick link to `reference/api.md` and `/ui` dashboard notes.

- docs/quicklook.md
  - Status: Consistent with scripts and options.
  - Suggestion: None.

- docs/concepts/architecture.md and docs/pipeline.md
  - Status: Diagrams match current modules and DBs.
  - Suggestion: Add products DB table names (`ms_index`, `images`, `qa_artifacts`) to notes.

- docs/downsampling_guide.md
  - Flag: Mixed invocation styles. Some examples call module CLI, others reference direct script paths under `src/…/downsample_hdf5_fast.py` and `downsample_hdf5_batch.py`.
  - Suggestion: Standardize on `python -m dsa110_contimg.conversion.downsample_uvh5.cli` for single/fast/batch examples; keep direct scripts only in developer section.

- docs/tutorials/convert-standalone.md
  - Status: Shows `python -m dsa110_contimg.conversion.uvh5_to_ms` usage which exists and exposes args via `create_parser()`.
  - Suggestion: Add note that streaming path typically uses the orchestrator instead.

- docs/tutorials/streaming.md
  - Status: High-level ops tasks; consistent.
  - Suggestion: Link to `/api/ui/calibrators` UI view.

- docs/tutorials/calibrate-apply.md
  - Status: Uses `database/registry_cli.py` as in code.
  - Suggestion: Add a brief example of imaging worker `scan` mode.

- docs/reference/modules.md
  - Status: Diagrams include ops scripts and match current module layout.
  - Suggestion: Add API models/data_access references if needed.

- docs/legacy-overview.md
  - Flag: “Recent Additions (MS Conversion)” mentions dask‑ms writer flags (`--dask-write`) and files not present in the current tree.
  - Suggestion: Mark that section as historical or remove; align with current `hdf5_orchestrator` writer choices (`direct-subband`, `pyuvdata`, `auto`).

- docs/reports/CONVERSION_PROCESS_SUMMARY.md
  - Flag: Describes UVFITS → importuvfits flow and scripts `dsa110_uvh5_to_ms.py`/`simple_uvh5_to_ms.py` which do not exist in current tree.
  - Suggestion: Rewrite to reflect current strategies: direct-subband writer and pyuvdata monolithic path; remove UVFITS import flow unless explicitly supported.

- docs/reference/env.md
  - Status: Matches current env usage (PIPELINE_TELESCOPE_NAME, CASACORE_DATA overlay, etc.).
  - Suggestion: Add queue/registry/products DB env variables used by API and streaming services.

## Quick Fix Checklist

- [ ] Update systemd references to `ops/systemd/contimg-stream.service`
- [ ] Add API endpoints: `/api/qa`, `/api/qa/file/{group}/{name}`, `/api/metrics/system`, `/api/metrics/system/history`
- [ ] Standardize downsampling examples on the unified CLI
- [ ] Rewrite legacy conversion report to current orchestrator + writers
- [ ] Trim/remove legacy dask‑ms section unless reinstated
- [ ] Expand env var docs for systemd/docker
- [ ] Add calibration/imaging worker snippets where appropriate

## Cross-Checks Performed

- Verified CLIs and subcommands in:
  - `src/dsa110_contimg/conversion/uvh5_to_ms.py`
  - `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`
  - `src/dsa110_contimg/conversion/downsample_uvh5/cli.py`
  - `src/dsa110_contimg/imaging/worker.py`
  - `src/dsa110_contimg/mosaic/cli.py`
  - `src/dsa110_contimg/database/registry_cli.py`
- Verified API endpoints in `src/dsa110_contimg/api/routes.py` and docker/systemd manifests.

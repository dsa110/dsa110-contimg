# Project Memory – dsa110-contimg

- Prefer RAM staging for per-subband MS writes and concat (`/dev/shm`) when available; fall back to SSD.
- Auto writer heuristic: ≤2 subbands -> monolithic (pyuvdata), else direct-subband.
- Fast calibration: use `--fast` with time/channel averaging; solve K on peak field, BP/G across window; phase-only by default; optional `--uvrange` cuts for speed.
- Quick imaging: `--quick` to cap imsize/niter; `--skip-fits` to avoid export; auto-selects CORRECTED_DATA when valid.
- Add concise timers around major steps to track drift (conversion concat, K/BP/G, tclean).

## 2025-10-22/23 – Telescope Identity + API/service fixes

Telescope identity standardization (OVRO_DSA)

- Single source of truth: `PIPELINE_TELESCOPE_NAME=OVRO_DSA` added to `ops/systemd/contimg.env`. Default OVRO coords: lon −118.2817°, lat 37.2314°, alt 1222 m.
- Helper `set_telescope_identity` added in `src/dsa110_contimg/conversion/helpers.py`.
  - Sets `uv.telescope_name` and location in ITRF + geodetic (rad/deg); mirrors onto `uv.telescope` when present.
- Applied on all write paths:
  - Orchestrator (`strategies/hdf5_orchestrator.py`) after merge, pre‑phasing.
  - Direct‑subband worker (`strategies/direct_subband.py`) after per‑subband read, pre‑phasing.
  - Standalone converter (`conversion/uvh5_to_ms.py`) after `read_uvh5_file`, pre‑phasing.
- MS backstop stamping: `configure_ms_for_imaging` now writes `OBSERVATION::TELESCOPE_NAME` from `PIPELINE_TELESCOPE_NAME`.
- Antenna coordinates: `utils/antpos_local/data/DSA110_Station_Coordinates.csv` is authoritative and used by `set_antenna_positions()` with safe elevation fallback.
- Docs updated with “Telescope Identity” and optional casacore Measures overlay:
  - `docs/reference/env.md`, `docs/quickstart.md`.
  - Overlay instructions: copy/append `geodetic/Observatories`, set `CASACORE_DATA=<repo>/data/measures`; not required for imaging since MS carries positions.

Systemd + API service hardening

- Units installed to `/etc/systemd/system`: `contimg-stream.service`, `contimg-api.service`; env in `ops/systemd/contimg.env`.
- Drop‑in overrides use conda: `conda run -n casa6 …` and `Environment=PYTHONPATH=/data/dsa110-contimg/src`.
- API startup fixed:
  - Exposed `app = create_app()` in `src/dsa110_contimg/api/__init__.py`.
  - Switched ExecStart to `uvicorn dsa110_contimg.api:app` (avoid `--factory` parsing issue).
- Env for API made explicit (no nested expansion): `PIPELINE_QUEUE_DB`, `PIPELINE_PRODUCTS_DB`, `PIPELINE_STATE_DIR`, `PIPELINE_EXPECTED_SUBBANDS`, `CAL_REGISTRY_DB` now set to concrete paths in `contimg.env`.
- DB initialization (one‑time) completed:
  - `/data/dsa110-contimg/state/cal_registry.sqlite3` with table `caltables`.
  - `/data/dsa110-contimg/state/ingest.sqlite3` with tables `ingest_queue`, `subband_files`, `performance_metrics`.
- Verified API endpoints:
  - `/api/status` returns queue stats and calibration sets.
  - `/api/metrics/system` returns system metrics.
- Note: systemd `append:` log redirection warnings observed; acceptable. Use journald if desired.

Operational notes / next steps

- Backfill existing MS telescope names if needed (stamp `OBSERVATION::TELESCOPE_NAME`).
- Optional casacore Measures overlay only needed for code calling `measures().observatory('OVRO_DSA')`.
- Streamer (`contimg-stream`) populates `ingest.sqlite3`; API reads DB paths from env.
# DSA-110 Continuum Imaging Project Memory

## Key Lessons and Principles

### UVH5 to MS Conversion Process

1. **Circular Import Issues**: The historical `uvh5_to_ms_converter_v2.py` had circular import dependencies that were resolved by:
   - Implementing lazy imports in `dsa110_contimg.conversion.__init__.py`
   - Creating missing modules (`writers.py`) and functions (`write_ms_from_subbands`)
   - Using direcports from specific modules rather than package-level imports

2. **FUSE Temporary Files**: Large `.fuse_hidden*` files (70+ GB each) are created during MS writing operations:
   - These are temporary files created by FUSE filesystems during large data operations
   - They can accumulate in multiple locations: root directory, MS directories, and QA directories
   - They can accumulate if processes don't clean up properly
   - Use `sudo fuser -k` and `sudo rm -f` to force cleanup when processes hold file descriptors
   - Normal behavior for CASA/pyuvdata operations writing large datasets
   - Total cleanup freed ~400GB of disk space (from 5.1T to 4.7T usage)

3. **Python Environment**: The system requires:
   - `casa6` conda environment for `pyuvdata` and CASA tools
   - `PYTHONPATH=/data/dsa110-contimg/src` for package imports
   - Python 3.11 (not Python 2.7) for modern syntax support

4. **Conversion Success**: The v2 converter successfully:
   - Groups subbands by timestamp (30s tolerance)
   - Merges frequency channels in ascending order
   - Creates proper CASA Measurement Sets with UVW coordinates
   - Finds and creates calibrator MS files with MODEL_DATA
   - Uses direct subband writer for optimal performance
   - Preallocates `MODEL_DATA`/`CORRECTED_DATA` after writing to avoid CASA errors
5. **Module Layout**: Active conversion code now lives in `dsa110_contimg/conversion/` (helpers, batch converter, streaming daemon, strategy writers). Legacy implementations are archived under `archive/legacy/core_conversion/`; imports from `dsa110_contimg.core.conversion` are no longer supported.

### File Structure
- Input: `/data/incoming/` (UVH5 subband files)
- Output: `/data/dsa110-contimg/data-samples/ms/` (CASA MS files)
- QA: `/data/dsa110-contimg/state/qa/` (Quality assurance plots)

### Common Issues and Solutions
- **ImportError**: Check PYTHONPATH and conda environment
- **Circular imports**: Use lazy imports and direct module references
- **Outdated import paths**: Update any remaining `dsa110_contimg.core.conversion.*` imports to `dsa110_contimg.conversion.*`
- **Large temp files**: Monitor for `.fuse_hidden*` files and clean up if needed
- **Missing modules**: Create required modules and functions as needed
- **CASA Calibrater error (no array in MODEL_DATA row)**: If `MODEL_DATA` exists but arrays are uninitialized, CASA `gaincal`/`bandpass` can fail with "TSM: no array in row ... of column MODEL_DATA". Fix by preallocating `MODEL_DATA` (unity or zeros) and initializing `CORRECTED_DATA` across all rows after MS write. The converter now does this automatically.

### Recent Fixes (2025-10-10 → 2025-10-13)
- Field selection in delay solve now honors CASA-style names/ranges: numeric IDs, `A~B`, comma lists, and glob matches against `FIELD::NAME`. This removes a crash when `--field` is a name.
- Calibration table prefixes now use `os.path.splitext(ms)[0]` instead of `rstrip('.ms')`, preventing accidental truncation (e.g., `runs.ms` → `runs`, not `run`).
- Streaming converter now uses the strategy orchestrator (writer=`direct-subband`) in both subprocess and in‑process paths; writer type is recorded in metrics.

### Integration Notes: Zapier MCP + Azure OpenAI (2025-10-20)
- Use the Zapier Azure OpenAI actions only after configuring the action UI fields; runtime overrides via MCP may be ignored.
- Required: set the exact Azure OpenAI `Deployment Name` (alias) in the Zapier action UI.
- Ensure the Azure resource host configured in Zapier matches the actual resource (e.g., `jfaber-9261-resource.openai.azure.com` vs a stale `myoairesourced1ce90.openai.azure.com`).
- If calls fail with “Deployment Name is missing,” confirm the action UI contains the alias (e.g., `gpt-5-codex`), not the model name.
- Legacy action endpoints may reveal misconfigured hosts; fix in Zapier, then retry calls without passing `deployment` at runtime.
- Products DB helpers added: centralized `ms_index`/`images` schema management, upserts, and indices.
- API/monitoring integrates recent calibrator matches and QA discovery.

### Catalog: Master Sources (NVSS + VLASS + FIRST)
- New builder: `python -m dsa110_contimg.catalog.build_master` creates `state/catalogs/master_sources.sqlite3`.
- Inputs: NVSS (required), optional VLASS and FIRST catalogs (CSV/TSV/FITS); auto column detection with optional explicit mappings.
- Crossmatch radius: configurable (default 7.5"). Computes:
  - Spectral index α from NVSS (1.4 GHz) and VLASS (3.0 GHz) peak fluxes (units converted to Jy).
  - Compactness via FIRST deconvolved sizes; confusion when multiple matches within radius.
- DB schema:
  - `sources(source_id, ra_deg, dec_deg, s_nvss, snr_nvss, s_vlass, alpha, resolved_flag, confusion_flag)`
  - Views: `good_references` (quality cuts), `final_references` (stricter SNR + optional stable IDs)
  - Optional materialized snapshot: `final_references_table`
  - `meta` records thresholds, build_time_iso, and input file provenance (sha256/size/mtime/rows)
- Useful flags: `--nvss-flux-unit|--vlass-flux-unit {jy|mjy|ujy}`, `--goodref-snr-min|-alpha-min|-alpha-max`, `--finalref-snr-min|--finalref-ids|--materialize-final`, `--export-view|--export-csv`.

# Currently Working On:

## 2025-10-23 – Environment standardization
- Drop `casa-dev` channel and replace `casa6` with explicit `casatools`, `casatasks`, `casaconfig` from conda-forge; keep `python-casacore`.
- `ops/docker/environment.yml` updated accordingly; image builds and passes CASA + stack import tests.
- `.cursor/Dockerfile` added to mirror container runtime for background agents using conda-forge environment; user `mambauser`.
- Verified container CLI help for `imaging.worker` and `hdf5_orchestrator`; module imports OK.


"""
Repository overview for the DSA-110 continuum imaging pipeline.
"""

# Layout Overview

- `src/dsa110_contimg/` – Active Python package (conversion, calibration, imaging, QA, API, utils)
- `tests/` – Unit and integration tests
- `docs/` – User guides, architecture notes, templates
- `docs/notebooks/` – Interactive notebooks (e.g., measurement-set staging walkthrough)
- `docs/notebooks/` – Interactive notebooks (MS staging, calibration tests)
- `config/` – Runtime and deployment configuration templates
- `ops/` – Operational scripts and service manifests
- `state/` – Runtime artifacts (queue SQLite DBs, CASA logs, checkpoints); gitignored
- `data-samples/` – Curated measurement sets and UVH5 examples for QA
- `archive/legacy/` – Historical scripts, notebooks, and deprecated code paths

## Recent Additions (MS Conversion)

- Optional dask-ms writer (experimental)
  - Converter `dsa110_contimg/conversion/uvh5_to_ms_converter_v2.py` now supports `--dask-write` to write Measurement Sets via dask‑ms (python‑casacore backend) for improved parallel I/O.
  - Use `--dask-write-failfast` to abort immediately on any dask‑ms error (no fallback to the direct writer) to speed up debugging.
  - Writer order: creates the main table first, then writes and links the required subtables (SPECTRAL_WINDOW, POLARIZATION, ANTENNA, FIELD, DATA_DESCRIPTION).
  - ANTENNA subtable builder is robust to missing `antenna_numbers`, synthesizing names (`pad1..padN`) when needed; positions are required.

- Quick downsampling knobs (for fast testing)
  - Frequency downsample: set environment `DS_FREQ=<int>` to average adjacent channels (updates `DATA`, `FLAG`, `NSAMPLE`, `freq_array`, `channel_width`).
  - Time downsample: set environment `DS_TIME=<int>` to combine adjacent time samples per baseline (averages `DATA/UVW/TIME/LST`, ORs `FLAG`, sums `NSAMPLE` and `integration_time`).
  - Both operate in‑memory on the merged UVData object prior to writing and reduce write volume substantially (e.g., `DS_TIME=2`, `DS_FREQ=4` → ~8× reduction).

Usage examples
```
# Quick synthetic (2 subbands) → fast dask‑write with downsampling
export PYTHONPATH=/data/dsa110-contimg/src:$PYTHONPATH
export DS_TIME=2 DS_FREQ=4
/opt/miniforge/envs/casa6/bin/python -u dsa110_contimg/conversion/uvh5_to_ms_converter_v2.py \
  /data/dsa110-contimg/synth_quick \
  /data/dsa110-contimg/out_dask_quick \
  "2025-10-08 00:12:59" "2025-10-08 00:12:59" \
  --dask-write --dask-write-failfast --no-stage-tmpfs --log-level INFO

# Validate in CASA
python - <<'PY'
from casatools import ms
m=ms(); m.open('/data/dsa110-contimg/out_dask_quick/2025-10-08T00:12:59.ms');
print(m.summary().get('nrow')); m.close()
PY
```

Notes
- Keep dask/distributed pinned to versions compatible with dask‑ms (currently dask 2024.10.x).
- The default converter path (pyuvdata write) remains unchanged; `--dask-write` is optional and can be toggled per run.

# Monitoring API

- FastAPI service under `src/dsa110_contimg/api/`
  - Endpoints: `/api/status`, `/api/products`, `/api/calibrator_matches`
    - `/api/calibrator_matches` supports `limit` and `matched_only` query params
  - UI routes: `/api/ui/calibrators` (server‑side HTML), `/ui` (static dashboard), `/ui/static/calibrators.html` (JS view)
  - Env configuration handled via `ApiConfig`
  - Tests in `tests/api/test_routes.py`

# Runtime Artifact Guidance

- All logs, queue databases, and other ephemeral outputs should live under `state/`
- Ensure operational scripts point CASA log outputs (`CASALOGFILE`) and SQLite files to `state/`
- `state/` contains a `.gitkeep` so the directory persists without tracking contents

# Next Steps

- Add documentation for pipeline execution workflows and dashboard integration
- Expand API endpoints (e.g., live monitoring metrics, calibration registry management)

# Calibrator Matching & Transits

The pipeline can automatically identify VLA calibrators within the primary beam during drift scanning and expose results via the API/UI. Helpers are also provided for computing meridian transits at OVRO and ad‑hoc catalog queries.

What it does
- Per group (5‑min by default), the streaming worker computes the meridian RA at the group midpoint for a configured declination strip, searches a VLA calibrator catalog within a radius, and stores top matches (PB‑weighted) in the queue DB.
- Recent groups and their matches surface in `/api/status`, `/api/calibrator_matches`, and the dashboard.
- Utilities assist with reading the VLA catalog, resolving RA/Dec, and computing previous meridian transits.

Configure
- `VLA_CALIBRATOR_CSV` – path to a VLA calibrator CSV (parsed form). Default:
  `references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv`
- `PIPELINE_POINTING_DEC_DEG` – declination of the drift strip (deg), e.g., `55.0`
- Optional: `CAL_MATCH_RADIUS_DEG` (default `1.0`), `CAL_MATCH_TOPN` (default `3`)

Key helpers
- Catalog: `read_vla_parsed_catalog_csv`, `get_calibrator_radec`, `calibrator_match` – `src/dsa110_contimg/calibration/catalogs.py`
- Transits: `previous_transits`, `next_transit_time`, constants `OVRO`, `SIDEREAL_RATE` – `src/dsa110_contimg/calibration/schedule.py`

CLI examples
```
# Previous 3 transits for a named calibrator
python -m dsa110_contimg.calibration.catalog_cli transit \
    --catalog references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv \
    --name 0834+555 --n 3

# In‑beam matches for a drift strip (pointing dec, time)
python -m dsa110_contimg.calibration.catalog_cli inbeam \
    --catalog references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv \
    --pt-dec 55.0 --time "2025-10-07 15:22:00" --radius 1.0 --top 5
```

Programmatic snippets
```
from astropy.time import Time
import astropy.units as u
from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv, get_calibrator_radec, calibrator_match
from dsa110_contimg.calibration.schedule import previous_transits

df = read_vla_parsed_catalog_csv('references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv')
ra_deg, dec_deg = get_calibrator_radec(df, '0834+555')
times = previous_transits(ra_deg, n=3)  # OVRO

mid = Time('2025-10-07T15:22:00', scale='utc')
matches = calibrator_match(df, 55.0 * u.deg, mid.mjd, radius_deg=1.0, top_n=3)
```

Streaming integration
- Queue DB schema gains: `ingest_queue.has_calibrator` (INTEGER), `ingest_queue.calibrators` (TEXT, JSON array)
- Worker hook (per group): reads env config, computes group midpoint, runs `calibrator_match`, updates DB
- Logging: “Calibrator(s) in beam: [...]” or “No calibrators in beam …”

Monitoring/API/UI
- `/api/status` recent_groups include `has_calibrator` and `matches`; `matched_recent` summarizes recent match count.
- `/api/calibrator_matches?limit=50&matched_only=true` returns recent groups with match lists.
- Dashboard: `/ui` shows queue stats and recent groups with match info; `/ui/static/calibrators.html` provides an interactive list (limit and matched_only filters).

Notes
- The VLA CSV should include `J2000_NAME` and either sexagesimal RA/Dec (e.g., `RA_J2000`, `DEC_J2000`) or numeric `RA_deg`, `DEC_deg`. The reader normalizes to degrees.
- Meridian computations use OVRO (`EarthLocation`) and sidereal time from Astropy; “previous transits” are spaced by one sidereal day (~23h56m).
- Primary‑beam weighting uses a simple Airy pattern at 1.4 GHz; adjust `radius`/`top_n` or substitute a different PB model if needed.

# QA Quicklooks (shadeMS)

Optional quicklook plots can be produced automatically after each MS is written using shadeMS (external CLI). This is disabled by default.

Enable via converter CLI flags (no env variables required):

```
python -m dsa110_contimg.conversion.uvh5_to_ms_converter_v2 \
  <input_dir> <output_dir> "YYYY-MM-DD HH:MM:SS" "YYYY-MM-DD HH:MM:SS" \
  --qa-shadems \
  --qa-shadems-resid \
  --qa-shadems-max 4 \
  --qa-shadems-timeout 600 \
  --qa-state-dir state
```

Or, enable via environment variables before running the converter or streaming worker:

```
export QA_SHADEMS_ENABLE=1            # turn on quicklooks
export QA_SHADEMS_RESID=1             # include residual plot (CORRECTED_DATA-MODEL_DATA) if MODEL_DATA exists
export QA_SHADEMS_MAX=4               # limit number of plots (default 4)
export QA_SHADEMS_TIMEOUT=600         # per-plot timeout (seconds)
export PIPELINE_STATE_DIR=state       # base dir for outputs
```

Artifacts are written to `state/qa/<ms_stem>/` alongside the measurement set name (or under the directory provided via `--qa-state-dir`). The converter invokes `shadems` as a separate process; if it is not installed or on `PATH`, quicklooks are skipped with a warning.

For existing Measurement Sets you can generate the same quicklooks without reconverting:

```
python -m dsa110_contimg.qa.quicklooks \
  --ms /scratch/dsa110-contimg/data-samples/ms/run123/2025-10-03T15:15:58.ms \
  --state-dir state \
  --ragavi               # optional HTML inspector in addition to shadeMS plots

# Fast Matplotlib quicklooks

When shadeMS/ragavi are unavailable or you just need an ultra-fast view, use the built-in matplotlib helper:

```
python -m dsa110_contimg.qa.fast_plots \
  --ms /scratch/dsa110-contimg/data-samples/ms/run123/2025-10-03T15:15:58.ms \
  --output-dir /data/dsa110-contimg/state/qa/run123_fast
```

You can combine everything via the quicklooks wrapper:

```
python -m dsa110_contimg.qa.quicklooks \
  --ms /scratch/.../2025-10-03T15:15:58.ms \
  --state-dir /data/dsa110-contimg/state \
  --fast-plots --fast-include-residual
```
```

Streaming service flags

You can enable quicklooks for the streaming path without environment variables by passing flags that are forwarded to the converter per group:

```
python -m dsa110_contimg.conversion.streaming_converter \
  --input-dir /data/incoming \
  --output-dir state/ms \
  --use-subprocess \
  --qa-shadems \
  --qa-shadems-cal-only \
  --qa-shadems-resid \
  --qa-shadems-max 4 \
  --qa-shadems-timeout 600 \
  --qa-state-dir state
```

The dashboard links to a “quicklooks” gallery under `/ui/static/qa.html`, and individual groups link to a detail view at `/ui/static/group.html?group=<group_id>`.

# Reference Antenna Recommendation

The fast QA pass produces a per‑antenna quality summary and an automatic reference‑antenna ranking suitable for `solve_delay`/`solve_bandpass`.

How it works
- Metrics computed per antenna over the scan:
  - Mean amplitude (signal strength)
  - Phase coherence R and circular phase standard deviation σ (stability)
  - Flagged‑row fraction (data completeness)
  - Amplitude variance (sanity check)
  - Array centrality factor (distance to array centroid, favouring central dishes)
- A composite score ranks antennas (higher is better):
  - `score = amp_norm^0.5 × coherence^1.0 × (1 − flagged_frac)^1.0 × stability^1.0 × center_factor^0.5`
  - where `stability = 1 / (1 + phase_sigma_deg / 45)` and `amp_norm = mean_amp / max(mean_amp)`
- Artifacts written alongside quicklooks:
  - `per_antenna_metrics_fast.png` — bar charts for mean amp, phase σ, flagged fraction, variance
  - `phase_sigma_sorted_fast.png` — antennas sorted by phase σ
  - `coherence_vs_flagged_fast.png` — coherence vs. flagged fraction scatter (colour = mean amp)
  - `phase_heatmap_fast.png` — phase σ over time for each antenna
  - `refant_ranking.json` and `refant_ranking.csv` — full ranking and the recommended antenna

Usage
```
python -m dsa110_contimg.qa.fast_plots \
  --ms /scratch/.../2025-10-03T15:15:58.ms \
  --output-dir /data/dsa110-contimg/state/qa/2025-10-03T15:15:58_fast

# Inspect refant_ranking.json for the recommended antenna_id
```

Calibration with the recommended refant
```
PYTHONPATH=/data/dsa110-contimg/src \
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/.../2025-10-03T15:15:58.ms \
    --field <cal_field> \
    --refant <recommended_antenna_id>
```

Notes
- The weighting above is conservative and aims to avoid obviously bad choices without overfitting. If you prefer different trade‑offs (e.g., penalise flagged fraction more strongly, or ignore centrality), the scoring can be tuned.
- When several antennas tie on score, prefer the one with higher mean amplitude or closer to the array centre.

# To Develop

Dashboard/UI and API enhancements planned to round out monitoring and operator experience:

- Live refresh and UX polish
  - Auto‑refresh the dashboard and calibrator views (10–30 s)
  - Human‑friendly timestamps (local timezone, relative age) and sortable columns
- Products and calibration sets in UI
  - Render `/api/products` on the dashboard (recent images, pbcor, noise, beam)
  - Display `/api/status.calibration_sets` with active/total and table paths
- Group detail view
  - Add `/api/groups/{group_id}` with subbands, errors, timings, matches, artifacts
  - Link group_id on the dashboard to this detail view
- Performance and system metrics
  - Expose performance metrics (load/phase/write/total) over API and chart on UI
  - Add lightweight system metrics (CPU/mem/disk IO) endpoint and sparklines
- Status/errors visibility
  - Show failure reasons and highlight errored groups; add quick retry control (if applicable)
- Calibrator UX
  - Dashboard toggle to filter “only matched”; show `weighted_flux` and a calibrator info drawer
  - Optional: sidebar for upcoming transits via `schedule.previous_transits`
- Config/health panel
  - Surface key env/config (e.g., `VLA_CALIBRATOR_CSV`, `PIPELINE_POINTING_DEC_DEG`, `CAL_MATCH_RADIUS_DEG`) and warnings when missing/disabled
- Pagination and filters
  - Add limit/offset filters for `/api/status` and pagination in UI tables
- Tests
  - Extend API test coverage for `/api/calibrator_matches` and expanded `/api/status`
- Security/hardening (as deployment requires)
  - Optional API/UI auth gate and CORS configuration

High‑value next steps
- Implement auto‑refresh + relative time formatting
- Add Products and Calibration Sets tables to `/ui`
- Create Group Detail API and link from dashboard
- Surface performance/system metrics and basic charts

# Bandpass Calibration (Notebook)

An end-to-end calibration test notebook is available at:

- `docs/notebooks/bandpass_calibration_test.ipynb`

What it does
- Runs fast QA on the MS to generate `refant_ranking.json` and recommends a reference antenna.
- Auto-selects the bandpass field range using the VLA calibrator catalog (primary-beam weighted).
- Executes K/BA/BP/G solves via CASA tasks using pipeline helpers.

Prerequisites
- Run with a CASA 6 kernel (both `casatools` and `casatasks` importable).
- Ensure the package is importable from the notebook (`../../src` is pre-added to `sys.path`).

Quick start
1) Open `docs/notebooks/bandpass_calibration_test.ipynb` and set your MS path.
2) Run the QA cell; review `/tmp/qa-auto/refant_ranking.json`.
3) Run the catalog auto-selection cell (defaults to `data-samples/catalogs/vlacalibrators.txt`, adjustable search radius and window).
4) Run the calibration cell; it prints the produced calibration tables.

CLI equivalent
```
# Fast QA (reference antenna ranking)
python -m dsa110_contimg.qa.fast_plots \
  --ms /scratch/.../2025-10-03T15:15:58.ms \
  --output-dir /tmp/qa-auto

# Calibration with catalog-driven auto fields and recommended refant
PYTHONPATH=src:$PYTHONPATH \
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /scratch/.../2025-10-03T15:15:58.ms \
  --auto-fields \
  --cal-catalog /data/dsa110-contimg/data-samples/catalogs/vlacalibrators.txt \
  --cal-search-radius-deg 2.0 \
  --bp-window 3 \
  --refant-ranking /tmp/qa-auto/refant_ranking.json
```

Notes
- The notebook plots the PB-weighted flux per field and highlights the selected field window.
- Adjust `bp-window` and search radius to widen or tighten the selection.

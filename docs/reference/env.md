# Reference: Environment Variables

- CORE: `PIPELINE_QUEUE_DB`, `PIPELINE_REGISTRY_DB`, `PIPELINE_PRODUCTS_DB`, `PIPELINE_STATE_DIR`, `HDF5_USE_FILE_LOCKING`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`
- STREAMING: `PIPELINE_POINTING_DEC_DEG`, `VLA_CALIBRATOR_CSV`, `CAL_MATCH_RADIUS_DEG`, `CAL_MATCH_TOPN`
- IMAGING: `IMG_IMSIZE`, `IMG_ROBUST`, `IMG_NITER`, `IMG_THRESHOLD`
- SCHED: `SCHED_*` variables for mosaic + housekeeping

Queue/Registry/Products DB

- `PIPELINE_QUEUE_DB`: SQLite path for the streaming ingest queue (used by API and ops tooling)
- `PIPELINE_REGISTRY_DB`: SQLite path for calibration registry (used by API/imaging)
- `PIPELINE_PRODUCTS_DB`: SQLite path for products (ms_index, images, qa_artifacts)

Telescope Identity

- `PIPELINE_TELESCOPE_NAME` (default: `OVRO_DSA`)
  - Used by converters to set `UVData.telescope_name` and populate MS `OBSERVATION::TELESCOPE_NAME`.
  - Coordinates used (authoritative for OVRO): lon −118.2817°, lat 37.2314°, alt 1222 m.
  - These are applied to every write path so imaging/calibration do not depend on casacore observatory lookup.

Optional Measures Overlay

- Some tools call casacore Measures to resolve an observatory by name (e.g., `measures().observatory('OVRO_DSA')`).
- To make the name resolvable without system-wide changes, you can provide a local overlay for casacore data and point `CASACORE_DATA` at it.
- Steps:
  - Locate current casacore data root: `python -c "from casatools import ctsys; print(ctsys.resolve('data'))"` (or check `$CASACORE_DATA`).
  - Copy its `geodetic/Observatories` file and append an entry for `OVRO_DSA` using the coordinates above.
  - Place it under `<repo>/data/measures/geodetic/Observatories`, then set `CASACORE_DATA=<repo>/data/measures` in the service env.
  - Services should be restarted for the change to take effect.
  - Guardrail: even without this overlay, the MS carries full positions and pipeline tasks work; only explicit name→location lookups depend on the catalog.

Backfill Existing MS (one-time)

- Stamp the `OBSERVATION::TELESCOPE_NAME` column on existing products:
  - `python - <<'PY'\nfrom casacore.tables import table; import glob, os\nname=os.getenv('PIPELINE_TELESCOPE_NAME','OVRO_DSA')\nfor ms in glob.glob('/data/ms/**/*.ms', recursive=True):\n  try:\n    with table(ms+'::OBSERVATION', readonly=False) as tb:\n      tb.putcol('TELESCOPE_NAME', [name]*tb.nrows())\n    print('Stamped', ms)\n  except Exception as e:\n    print('Skip', ms, e)\nPY`

Validation

- PyUVData roundtrip:
  - `python - <<'PY'\nfrom pyuvdata import UVData\nu=UVData(); u.read('/path/to.ms', file_type='ms')\nprint(u.telescope_name, getattr(u,'telescope_location_lat_lon_alt_deg',None))\nPY`
- casacore Measures lookup (requires overlay):
  - `python - <<'PY'\nfrom casacore.measures import measures\nm=measures(); print(m.observatory('OVRO_DSA'))\nPY`

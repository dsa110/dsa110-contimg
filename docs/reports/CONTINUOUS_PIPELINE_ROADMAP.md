# Continuum Pipeline: Toward Continuous Operations

This note summarizes the new building blocks added to reach a continuous workflow and how to run them.

## New Components

- Calibration Registry (SQLite)
  - Module: `dsa110_contimg/database/registry.py`
  - CLI: `python -m dsa110_contimg.database.registry_cli ...`
  - Tracks calibration tables (K/BA/BP/GA/GP/2G/FLUX), validity windows, and ordered apply lists.

- Calibrator CLI (CASA solves/apply)
  - Module/CLI: `python -m dsa110_contimg.calibration.cli ...`
  - Commands:
    - `calibrate`: run CASA solves on a calibrator MS and print resulting tables.
    - `apply`: apply an ordered set of tables to a target MS.

- Imaging Worker (5-min)
 - Module/CLI: `python -m dsa110_contimg.imaging.worker ...`
  - Scans or polls an MS directory, looks up the active caltables by mid-MJD, applies them, and produces quick images. Records artifacts in a small `products` DB.

## Quickstart

1) Initialize the registry DB

```
python -m dsa110_contimg.database.registry_cli init --db pipeline/cal_registry.sqlite3
```

2) Solve on a calibrator MS and register the tables

```
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/2025-10-06_J1234+5678.ms \
  --field J1234+5678 --refant 23

python -m dsa110_contimg.database.registry_cli register-prefix \
  --db pipeline/cal_registry.sqlite3 \
  --set-name 2025-10-06_J1234+5678 \
  --prefix /data/ms/solves/2025-10-06_J1234+5678
```

3) Process new 5-min MS into images

```
python -m dsa110_contimg.imaging.worker scan \
  --ms-dir /data/ms/5min \
  --out-dir /data/images/5min \
  --registry-db pipeline/cal_registry.sqlite3 \
  --products-db pipeline/products.sqlite3
```

4) Query active tables for a given MJD

```
python -m dsa110_contimg.database.registry_cli active \
  --db pipeline/cal_registry.sqlite3 --mjd 60295.30000
```

## Next Phases

- Mosaic Builder (rolling 60-min)
- Forced Photometry on mosaics (NVSS)
- Cutout generation and storage
- Variability metrics + ESE candidate detection
- JSON exporters for UI dashboard

These can be layered on the `products` DB created by the imaging worker.

***

CASA 6.7 is required for solving/applying/imaging. Ensure `casatools`, `casatasks`, and `casaplotms` are present in the environment.

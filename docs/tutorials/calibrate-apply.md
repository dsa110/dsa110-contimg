# Tutorial: Calibrate + Apply

Solve on a calibrator and apply to a target using the registry.

## Quick Note: K-Calibration

**K-calibration (delay) is skipped by default for DSA-110** (connected-element array with 2.6 km max baseline). This follows VLA/ALMA practice - residual delays are absorbed into gain calibration. Use `--do-k` to explicitly enable if needed.

## Workflow

- Use streaming or generate a calibrator MS
- Register a set from a prefix:
```
python -m dsa110_contimg.database.registry_cli register-prefix   --db state/cal_registry.sqlite3   --name calset_2025_10_07   --prefix /data/ms/2025-10-07_calibrator   --cal-field Jxxxx+xxxx --refant 23   --valid-start 60295.20 --valid-end 60295.45
```
- Imaging worker backfill applies to any MS in a directory

Example imaging worker (scan mode):
```
python -m dsa110_contimg.imaging.worker scan \
  --ms-dir /data/ms \
  --out-dir /data/out/images \
  --registry-db state/cal_registry.sqlite3 \
  --products-db state/products.sqlite3 \
  --log-level INFO
```

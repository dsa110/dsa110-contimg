# Quick-Look Pipeline (sub-minute)

This guide summarizes the fast path to convert, calibrate, and image a 5‑minute
observation in under ~60s.

## Conversion

- Writer: `--writer auto` (monolithic for ≤2 subbands, else direct-subband)
- RAM staging: `--stage-to-tmpfs --tmpfs-path /dev/shm` (enabled by default in
  `scripts/run_conversion.sh` when `/dev/shm` is mounted)
- Scratch: `SCRATCH_ROOT=/dev/shm/dsa110-contimg` fallback to
  `/stage/dsa110-contimg`.

Example:

```bash
scripts/run_conversion.sh /path/to/uvh5_dir /stage/dsa110-contimg/ms \
  2025-10-13T13:25:00 2025-10-13T13:30:00
```

## Calibration (development tier)

- Optional subset: `--preset development` (⚠️ NON-SCIENCE quality)
- Phase-only gains by default in development tier; optional
  `--uvrange '>1klambda'` to speed solves
- Telemetry prints durations for K/BP/G

Example:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /stage/dsa110-contimg/ms/<obs>.ms \
  --field 0~4 --refant 1 --preset development
```

## Imaging (development tier)

- Development tier: `--quality-tier development` reduces `imsize` and `niter`
  (⚠️ NON-SCIENCE)
- Skip FITS export for speed: `--skip-fits`
- Uses `CORRECTED_DATA` if nonzero; falls back to `DATA`

Example:

```bash
scripts/image_ms.sh /stage/dsa110-contimg/ms/<obs>.ms /scratch/out/<obs> \
  --quality-tier development --skip-fits
```

## Notes & Fallbacks

- If RAM is low, staging falls back to SSD automatically.
- For very few subbands (≤2), monolithic write is chosen to avoid concat.
- If FITS are required downstream, omit `--skip-fits`.

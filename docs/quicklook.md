# Quick-Look Pipeline (sub-minute)

This guide summarizes the fast path to convert, calibrate, and image a 5‑minute observation in under ~60s.

## Conversion

- Writer: `--writer auto` (monolithic for ≤2 subbands, else direct-subband)
- RAM staging: `--stage-to-tmpfs --tmpfs-path /dev/shm` (enabled by default in `scripts/run_conversion.sh` when `/dev/shm` is mounted)
- Scratch: `SCRATCH_ROOT=/dev/shm/dsa110-contimg` fallback to `/scratch/dsa110-contimg`.

Example:

```bash
scripts/run_conversion.sh /path/to/uvh5_dir /scratch/dsa110-contimg/ms \
  2025-10-13T13:25:00 2025-10-13T13:30:00
```

## Calibration (fast)

- Optional subset: `--fast --timebin 30s --chanbin 4` (or adjust for your CPU/IO)
- Phase-only gains by default in fast mode; optional `--uvrange '>1klambda'` to speed solves
- Telemetry prints durations for K/BP/G

Example:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /scratch/dsa110-contimg/ms/<obs>.ms \
  --field 0~4 --refant 1 --fast --timebin 30s --chanbin 4 --uvrange '>1klambda'
```

## Imaging (quick)

- Quick-look: `--quick` reduces `imsize` and `niter` conservatively
- Skip FITS export for speed: `--skip-fits`
- Uses `CORRECTED_DATA` if nonzero; falls back to `DATA`

Example:

```bash
scripts/image_ms.sh /scratch/dsa110-contimg/ms/<obs>.ms /scratch/out/<obs> \
  --quick --skip-fits --uvrange '>1klambda'
```

## Notes & Fallbacks

- If RAM is low, staging falls back to SSD automatically.
- For very few subbands (≤2), monolithic write is chosen to avoid concat.
- If FITS are required downstream, omit `--skip-fits`.



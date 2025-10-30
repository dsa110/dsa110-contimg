# Quick Start

Pick one path: Docker Compose (easiest) or systemd (closer to the metal).

## Docker Compose

1) Copy and edit env
```
cp ops/docker/.env.example ops/docker/.env
# Edit absolute host paths: REPO_ROOT, CONTIMG_*; set UID/GID and CONTIMG_API_PORT
```
2) Build and start
```
make compose-build
make compose-up
make compose-logs SERVICE=stream
```
3) Verify
- Output MS under `${CONTIMG_OUTPUT_DIR}`
- Products DB `images` and `ms_index` in `${CONTIMG_PRODUCTS_DB}`
- API at `http://localhost:${CONTIMG_API_PORT}/api/status` (dashboard at `/ui`, QA at `/api/qa`)

## systemd

1) Edit env and install units
```
vi ops/systemd/contimg.env
# Add PIPELINE_TELESCOPE_NAME=DSA_110 (and optional CASACORE_DATA overlay path)
sudo mkdir -p /data/dsa110-contimg/state/logs
sudo cp ops/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contimg-stream.service contimg-api.service
```
2) Verify
- `journalctl -u contimg-stream -f`
- API status at `/api/status`

Telescope Identity

- The pipeline stamps `UVData.telescope_name` and `MS::OBSERVATION.TELESCOPE_NAME` with `PIPELINE_TELESCOPE_NAME` (default `DSA_110`).
- Coordinates used (OVRO): lon −118.2817°, lat 37.2314°, alt 1222 m.
- **Important**: `DSA_110` is recognized by EveryBeam 0.7.4+ for automatic beam model detection.
- Optional: to make casacore resolve `DSA_110` by name, create a Measures overlay (`geodetic/Observatories`) and set `CASACORE_DATA` to that directory in `ops/systemd/contimg.env`.

## One-page Quick-Look (sub-minute)

1) Convert (auto writer, RAM staging):
```bash
scripts/run_conversion.sh /path/to/uvh5_dir /scratch/dsa110-contimg/ms \
  2025-10-13T13:25:00 2025-10-13T13:30:00
```

2) Calibrate fast (optional subset + phase-only):
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /scratch/dsa110-contimg/ms/<obs>.ms \
  --field 0~4 --refant 1 --fast --timebin 30s --chanbin 4 --uvrange '>1klambda'
```

3) Image quick (skip FITS for speed):
```bash
scripts/image_ms.sh /scratch/dsa110-contimg/ms/<obs>.ms /scratch/out/<obs> \
  --quick --skip-fits --uvrange '>1klambda'
```

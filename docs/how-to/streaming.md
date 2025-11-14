# Streaming Guide

This single guide covers operating the streaming converter: overview, control
from the Dashboard, standalone CLI, deployment, troubleshooting, and pointers to
deeper references.

## Overview

The streaming service watches incoming UVH5 subband files and converts them into
CASA Measurement Sets (MS), then triggers calibration/imaging as configured.

- What it does: ingest → group → convert → (optional) calibrate/apply → quick
  image
- Where it runs: Docker Compose or systemd (both supported)
- Where to view results: Products DB (`ms_index`, `images`) and Dashboard pages

## Control from Dashboard

- Page: Dashboard → Streaming (URL: `/streaming`)
- Controls: Start, Stop, Restart; edit configuration; view status, metrics,
  queue
- Health: service uptime, CPU/memory, error indicators; link to logs

## Standalone Converter (CLI)

For one‑off or batch conversion without the daemon:

```bash
# Quick look convert (RAM staging recommended)
scripts/run_conversion.sh /path/to/uvh5_dir /stage/dsa110-contimg/ms \
  2025-10-13T13:25:00 2025-10-13T13:30:00
```

See also: calibration/imaging one‑liners in `docs/how-to/quickstart.md`.

## Deployment

Pick one path and stick with it.

### Docker Compose (recommended for full stack)

1. Configure env

```bash
cp ops/docker/.env.example ops/docker/.env
# Edit absolute host paths (REPO_ROOT, CONTIMG_*), UID/GID, ports
```

2. Build and start

```bash
make compose-build
make compose-up
make compose-logs SERVICE=stream
```

3. Verify

- Output MS under `${CONTIMG_OUTPUT_DIR}`
- API at `http://localhost:${CONTIMG_API_PORT}/api/status`
- Dashboard at `http://localhost:5173`

### systemd (production host services)

1. Install units and env

```bash
sudo mkdir -p /data/dsa110-contimg/state/logs
sudo cp ops/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contimg-stream.service contimg-api.service
```

2. Verify

```bash
journalctl -u contimg-stream -f
curl http://localhost:8000/api/status
```

## Troubleshooting

- Service won’t start: confirm casa6 environment, env vars, and directory
  permissions.
- Converter stalls: check queue state and recent logs; verify HDF5 lock
  settings.
- Dashboard shows stale status: refresh, verify API reachable from browser,
  check CORS.

See detailed troubleshooting in the archived guide (links below).

## References

- Streaming API: `docs/reference/streaming-api.md`
- Streaming Architecture: `docs/concepts/streaming-architecture.md`
- Converter design (archived): `docs/archive/analysis/` and
  `docs/archive/reports/`
- Docker/systemd specifics: see `ops/` and notes under Deployment above

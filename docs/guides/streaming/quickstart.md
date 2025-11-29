# Streaming Quick Start

Get the streaming service running in 5 minutes.

---

## Prerequisites

- CASA6 environment (`/opt/miniforge/envs/casa6/bin/python`)
- Docker (for compose deployment) or systemd access
- Input directory for UVH5 files
- Output directory for Measurement Sets

---

## Option 1: Docker Compose (Recommended)

### 1. Configure Environment

```bash
cp ops/docker/.env.example ops/docker/.env
# Edit: REPO_ROOT, CONTIMG_*, UID/GID, ports
```

### 2. Build and Start

```bash
make compose-build
make compose-up
make compose-logs SERVICE=stream
```

### 3. Verify

- Output MS: `${CONTIMG_OUTPUT_DIR}`
- API: `http://localhost:${CONTIMG_API_PORT}/api/status`
- Dashboard: `http://localhost:5173`

---

## Option 2: systemd (Production)

### 1. Install Units

```bash
sudo mkdir -p /data/dsa110-contimg/state/logs
sudo cp ops/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contimg-stream.service contimg-api.service
```

### 2. Verify

```bash
journalctl -u contimg-stream -f
curl http://localhost:8000/api/status
```

---

## Dashboard Control

1. Navigate to Dashboard → Streaming (`/streaming`)
2. Click **Start** to begin the service
3. Monitor status, metrics, and queue
4. Use **Stop** or **Restart** as needed

---

## Standalone Conversion (CLI)

For one-off conversions without the daemon:

```bash
# Basic conversion
scripts/run_conversion.sh /path/to/uvh5_dir /stage/dsa110-contimg/ms \
  2025-10-13T13:25:00 2025-10-13T13:30:00
```

---

## API Quick Reference

```bash
# Check status
curl http://localhost:8010/api/streaming/status

# Start service
curl -X POST http://localhost:8010/api/streaming/start

# Stop service
curl -X POST http://localhost:8010/api/streaming/stop

# Get configuration
curl http://localhost:8010/api/streaming/config

# Update configuration
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16,
    "chunk_duration": 5.0
  }'
```

---

## Next Steps

- [Deployment Guide](deployment.md) - Detailed deployment options
- [Troubleshooting](troubleshooting.md) - Common issues
- [API Reference](api.md) - Full API documentation

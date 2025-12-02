# Streaming Deployment Guide

Detailed deployment options for the streaming service.

---

## Deployment Options

| Method         | Best For               | Pros                 | Cons            |
| -------------- | ---------------------- | -------------------- | --------------- |
| Docker Compose | Full stack development | Easy setup, isolated | Requires Docker |
| systemd        | Production hosts       | Native, persistent   | Manual setup    |

---

## Docker Compose Deployment

### Prerequisites

- Docker and Docker Compose installed
- Repository cloned to `/data/dsa110-contimg`

### Configuration

1. Copy environment template:

   ```bash
   cp ops/docker/.env.example ops/docker/.env
   ```

2. Edit `ops/docker/.env`:

```bash
# Host paths (must be absolute)
REPO_ROOT=/data/dsa110-contimg
CONTIMG_INPUT_DIR=/data/incoming
CONTIMG_OUTPUT_DIR=/stage/dsa110-contimg/ms
CONTIMG_SCRATCH_DIR=/stage/dsa110-contimg
CONTIMG_STATE_DIR=/data/dsa110-contimg/state

# User/Group IDs (match host user)
HOST_UID=1000
HOST_GID=1000

# Ports
CONTIMG_API_PORT=8010
CONTIMG_DASHBOARD_PORT=5173
```

### Build and Start

```bash
# Build all services
make compose-build

# Start all services
make compose-up

# View logs
make compose-logs SERVICE=stream
make compose-logs SERVICE=api

# Stop services
make compose-down
```

### Verify

```bash
# Check container status
docker-compose ps

# Check API
curl http://localhost:8010/api/status

# Check streaming status
curl http://localhost:8010/api/streaming/status
```

---

## systemd Deployment

### systemd Prerequisites

- CASA6 environment installed
- Repository at `/data/dsa110-contimg`
- sudo access

### Installation

1. Create directories:

   ```bash
   sudo mkdir -p /data/dsa110-contimg/state/logs
   sudo chown -R $USER:$USER /data/dsa110-contimg/state
   ```

2. Install service units:

   ```bash
   sudo cp ops/systemd/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

3. Enable and start services:

```bash
sudo systemctl enable --now contimg-stream.service
sudo systemctl enable --now contimg-api.service
```

### Service Files

**contimg-stream.service:**

```ini
[Unit]
Description=DSA-110 Streaming Converter
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/data/dsa110-contimg
Environment=PATH=/opt/miniforge/envs/casa6/bin:/usr/local/bin:/usr/bin
ExecStart=/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming \
    --output-dir /stage/dsa110-contimg/ms \
    --scratch-dir /stage/dsa110-contimg \
    --chunk-duration 5.0 \
    --omp-threads 4
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Management Commands

```bash
# Check status
sudo systemctl status contimg-stream

# View logs
journalctl -u contimg-stream -f

# Restart
sudo systemctl restart contimg-stream

# Stop
sudo systemctl stop contimg-stream

# Disable
sudo systemctl disable contimg-stream
```

---

## Directory Setup

### Required Directories

```bash
# Create directories
mkdir -p /data/incoming                    # Input UVH5 files
mkdir -p /stage/dsa110-contimg/ms          # Output MS files
mkdir -p /stage/dsa110-contimg             # Scratch/staging
mkdir -p /data/dsa110-contimg/state        # SQLite databases
mkdir -p /data/dsa110-contimg/state/logs   # Log files

# Set permissions
chmod 755 /data/incoming /stage/dsa110-contimg/ms /stage/dsa110-contimg
chown -R $USER:$USER /data/incoming /stage/dsa110-contimg
```

### Directory Structure

```text
/data/incoming/                    # UVH5 input files
/stage/dsa110-contimg/
├── ms/                            # Output Measurement Sets
│   ├── science/YYYY-MM-DD/
│   ├── calibrators/YYYY-MM-DD/
│   └── failed/YYYY-MM-DD/
└── (staging area)

/data/dsa110-contimg/state/
├── ingest.sqlite3                 # Queue database
├── products.sqlite3               # Products database
├── cal_registry.sqlite3           # Calibration registry
├── streaming_config.json          # Service configuration
└── logs/
    └── streaming.log
```

---

## Configuration Persistence

Configuration is stored in `state/streaming_config.json`:

```json
{
  "input_dir": "/data/incoming",
  "output_dir": "/stage/dsa110-contimg/ms",
  "queue_db": "state/db/ingest.sqlite3",
  "registry_db": "state/db/cal_registry.sqlite3",
  "scratch_dir": "/stage/dsa110-contimg",
  "expected_subbands": 16,
  "chunk_duration": 5.0,
  "log_level": "INFO",
  "max_workers": 4,
  "stage_to_tmpfs": false,
  "tmpfs_path": "/dev/shm"
}
```

Update via API:

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d @streaming_config.json
```

---

## Performance Tuning

### tmpfs Staging

For faster conversion, stage files to RAM:

```bash
# Enable tmpfs staging
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "stage_to_tmpfs": true,
    "tmpfs_path": "/dev/shm"
  }'
```

**Requirements:**

- Sufficient RAM (files are ~500MB each)
- tmpfs mounted at `/dev/shm`

### Worker Count

Adjust based on CPU cores:

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 4}'
```

**Guidelines:**

- 2-4 workers for most systems
- More workers = higher CPU/memory usage
- Too many workers can cause resource contention

### HDF5 on NFS

If input files are on NFS:

```bash
export HDF5_USE_FILE_LOCKING=FALSE
```

Add to `.bashrc` or service environment.

---

## Monitoring

### Health Check

```bash
curl http://localhost:8010/api/streaming/health
```

### Metrics

```bash
curl http://localhost:8010/api/streaming/metrics
```

### Logs

```bash
# Docker
docker-compose logs -f stream

# systemd
journalctl -u contimg-stream -f

# File
tail -f /data/dsa110-contimg/state/logs/streaming.log
```

---

## Security Considerations

- Service runs as non-root user
- Input/output directories should have restricted permissions
- API has no authentication (internal network only)
- Consider firewall rules for production

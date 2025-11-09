# Installing DSA-110 Services

## Prerequisites

1. Create log directory:
```bash
sudo mkdir -p /var/log/dsa110
sudo chown ubuntu:ubuntu /var/log/dsa110
```

2. Verify conda environment path:
```bash
which conda
# Adjust ExecStart path in dsa110-api.service if different
```

## Installation Steps

### 1. Install API Service

```bash
# Copy service file
sudo cp /data/dsa110-contimg/ops/systemd/contimg-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable dsa110-api.service

# Start service
sudo systemctl start dsa110-api.service

# Check status
sudo systemctl status dsa110-api.service
```

### 2. Install Pointing Monitor Service

```bash
# Copy service file
sudo cp /data/dsa110-contimg/ops/systemd/contimg-pointing-monitor.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable contimg-pointing-monitor.service

# Start service
sudo systemctl start contimg-pointing-monitor.service

# Check status
sudo systemctl status contimg-pointing-monitor.service

# Check status file
cat /data/dsa110-contimg/state/pointing-monitor-status.json
```

### 3. Install Dashboard Service (Optional - for production)

```bash
# First, build the production frontend
cd /data/dsa110-contimg/frontend
npm run build

# Install serve (production static server)
sudo npm install -g serve

# Update service file to use production build
sudo nano /etc/systemd/system/dsa110-dashboard.service
# Change ExecStart to:
# ExecStart=/usr/local/bin/serve -s /data/dsa110-contimg/frontend/build -l 3000

# Copy and enable
sudo cp /data/dsa110-contimg/ops/systemd/contimg-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dsa110-dashboard.service
sudo systemctl start dsa110-dashboard.service
sudo systemctl status dsa110-dashboard.service
```

## Managing Services

### View Logs
```bash
# API logs
sudo journalctl -u dsa110-api.service -f

# Pointing monitor logs
sudo journalctl -u contimg-pointing-monitor.service -f

# Dashboard logs
sudo journalctl -u dsa110-dashboard.service -f

# Or view log files directly
tail -f /data/dsa110-contimg/state/logs/pointing-monitor.out
tail -f /data/dsa110-contimg/state/logs/pointing-monitor.err
```

### Control Services
```bash
# Start
sudo systemctl start dsa110-api.service
sudo systemctl start contimg-pointing-monitor.service
sudo systemctl start dsa110-dashboard.service

# Stop
sudo systemctl stop dsa110-api.service
sudo systemctl stop contimg-pointing-monitor.service
sudo systemctl stop dsa110-dashboard.service

# Restart
sudo systemctl restart dsa110-api.service
sudo systemctl restart contimg-pointing-monitor.service
sudo systemctl restart dsa110-dashboard.service

# Check status
sudo systemctl status dsa110-api.service
sudo systemctl status contimg-pointing-monitor.service
sudo systemctl status dsa110-dashboard.service
```

### Disable Auto-Start
```bash
sudo systemctl disable dsa110-api.service
sudo systemctl disable contimg-pointing-monitor.service
sudo systemctl disable dsa110-dashboard.service
```

## Port Reservation

Systemd will automatically bind to ports 8000 (API) and 3000 (Dashboard) when services start. If another process tries to use these ports, it will fail.

### Check Port Usage
```bash
# See what's using port 8000
sudo lsof -i :8000

# See what's using port 3000
sudo lsof -i :3000
```

### Kill Conflicting Processes
```bash
# Find and kill process on port 8000
sudo fuser -k 8000/tcp

# Find and kill process on port 3000
sudo fuser -k 3000/tcp
```

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u dsa110-api.service -n 50 --no-pager

# Check if conda environment exists
ls -la /opt/miniforge/envs/casa6/bin/uvicorn

# Check permissions
ls -la /data/dsa110-contimg/state/
```

### Port already in use
```bash
# Find what's using the port
sudo netstat -tlnp | grep :8000

# Kill the process
sudo kill <PID>

# Restart service
sudo systemctl restart dsa110-api.service
```

### Service crashes on startup
```bash
# Check environment variables
sudo systemctl show dsa110-api.service | grep Environment

# Test manually
cd /data/dsa110-contimg
conda activate casa6
export PYTHONPATH=/data/dsa110-contimg/src
uvicorn dsa110_contimg.api.server:app --host 0.0.0.0 --port 8000
```

### Pointing Monitor Status

The pointing monitor writes a status JSON file for external monitoring:

```bash
# View current status
cat /data/dsa110-contimg/state/pointing-monitor-status.json | jq

# Monitor status changes
watch -n 5 'cat /data/dsa110-contimg/state/pointing-monitor-status.json | jq .metrics'
```

Status file includes:
- `running`: Whether monitor is active
- `healthy`: Health check status
- `issues`: List of health issues (if any)
- `metrics`: Processing statistics (files processed, success rate, etc.)

## Uninstall

```bash
# Stop and disable services
sudo systemctl stop dsa110-api.service
sudo systemctl disable dsa110-api.service
sudo systemctl stop contimg-pointing-monitor.service
sudo systemctl disable contimg-pointing-monitor.service
sudo systemctl stop dsa110-dashboard.service
sudo systemctl disable dsa110-dashboard.service

# Remove service files
sudo rm /etc/systemd/system/dsa110-api.service
sudo rm /etc/systemd/system/contimg-pointing-monitor.service
sudo rm /etc/systemd/system/dsa110-dashboard.service

# Reload systemd
sudo systemctl daemon-reload
```


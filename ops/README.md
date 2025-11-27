# DSA-110 Monitoring Services Installation Guide

This guide covers the installation and setup of the monitoring and visualization
services for the DSA-110 continuum imaging pipeline.

## Overview

The monitoring system consists of:

1. **Disk Usage Monitor** - Continuous disk space monitoring (systemd service)
2. **Pipeline Monitoring Service** - Performance, antenna health, and queue
   monitoring (systemd service)
3. **Pipeline Hooks** - Event-driven visualization generation after pipeline
   stages
4. **REST API** - Access to all visualizations via HTTP endpoints

## Prerequisites

- DSA-110 pipeline installed in `/data/dsa110-contimg`
- Python 3.11 with casa6 environment
- Systemd (for background services)
- Root/sudo access (for installing systemd services)

## Installation Steps

### 1. Create QA Output Directories

```bash
cd /data/dsa110-contimg
bash ops/scripts/setup_qa_directories.sh
```

This creates:

```
/data/dsa110-contimg/qa_outputs/
├── performance/current/
├── antenna_health/current/
├── queue_health/current/
├── mosaic_quality/current/
├── calibration_quality/current/
├── disk_usage/current/
└── ese_candidates/current/
```

### 2. Install Systemd Services

#### Disk Monitoring Service

```bash
# Copy service file
sudo cp ops/systemd/dsa110-disk-monitor.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable (start on boot)
sudo systemctl enable dsa110-disk-monitor

# Start service
sudo systemctl start dsa110-disk-monitor

# Check status
sudo systemctl status dsa110-disk-monitor
```

#### Pipeline Monitoring Service

```bash
# Copy service file
sudo cp ops/systemd/dsa110-monitoring.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable (start on boot)
sudo systemctl enable dsa110-monitoring

# Start service
sudo systemctl start dsa110-monitoring

# Check status
sudo systemctl status dsa110-monitoring
```

### 3. Configure Environment Variables (Optional)

Edit `/etc/systemd/system/dsa110-monitoring.service` to customize:

```ini
Environment="DSA110_MONITOR_INTERVAL_PERFORMANCE=900"  # 15 minutes
Environment="DSA110_MONITOR_INTERVAL_ANTENNA=1800"     # 30 minutes
Environment="DSA110_MONITOR_INTERVAL_QUEUE=300"        # 5 minutes
Environment="DSA110_ALERT_QUEUE_DEPTH=50"              # Queue alert threshold
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart dsa110-monitoring
```

### 4. Verify Installation

```bash
# Check logs
sudo journalctl -u dsa110-monitoring -f
sudo journalctl -u dsa110-disk-monitor -f

# Check that plots are being generated
ls -lh /data/dsa110-contimg/qa_outputs/performance/current/
ls -lh /data/dsa110-contimg/qa_outputs/disk_usage/current/
```

## Pipeline Hooks (Automatic)

Pipeline hooks are already integrated in the code and will automatically
generate plots after:

- MS Conversion complete → Performance plots
- Fast plots complete → Antenna health plots
- Calibration complete → Calibration quality plots
- Mosaic creation complete → Mosaic quality plots
- ESE detection complete → ESE candidate dashboard

No additional configuration needed!

## API Access

Once the FastAPI server is running, access visualization endpoints at:

```
http://localhost:8000/api/monitoring/
```

### Example API Calls

```bash
# Get performance metrics
curl http://localhost:8000/api/monitoring/performance/metrics?hours=24

# Get antenna health heatmap (image)
curl http://localhost:8000/api/monitoring/antenna-health/plots/heatmap?hours=24 > heatmap.png

# Get queue health metrics
curl http://localhost:8000/api/monitoring/queue-health/metrics?hours=24

# Get disk usage
curl http://localhost:8000/api/monitoring/disk-usage/current

# Get ESE candidates
curl http://localhost:8000/api/monitoring/ese-candidates/list?status=active&min_sigma=3.0
```

## Service Management Commands

### Start/Stop Services

```bash
# Start
sudo systemctl start dsa110-monitoring
sudo systemctl start dsa110-disk-monitor

# Stop
sudo systemctl stop dsa110-monitoring
sudo systemctl stop dsa110-disk-monitor

# Restart
sudo systemctl restart dsa110-monitoring
sudo systemctl restart dsa110-disk-monitor

# Status
sudo systemctl status dsa110-monitoring
sudo systemctl status dsa110-disk-monitor
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u dsa110-monitoring -f
sudo journalctl -u dsa110-disk-monitor -f

# View last 100 lines
sudo journalctl -u dsa110-monitoring -n 100
sudo journalctl -u dsa110-disk-monitor -n 100

# View logs since yesterday
sudo journalctl -u dsa110-monitoring --since yesterday
```

### Enable/Disable Auto-start

```bash
# Enable (start on boot)
sudo systemctl enable dsa110-monitoring
sudo systemctl enable dsa110-disk-monitor

# Disable (don't start on boot)
sudo systemctl disable dsa110-monitoring
sudo systemctl disable dsa110-disk-monitor
```

## Testing Individual Modules

You can test each visualization module independently:

```bash
# Performance monitoring
python -m dsa110_contimg.qa.performance_monitoring \
    --queue-db /data/dsa110-contimg/state/streaming_ingest.db \
    --output-dir /data/dsa110-contimg/qa_outputs/performance/current \
    --hours 24

# Antenna health
python -m dsa110_contimg.qa.antenna_health_monitoring \
    --products-db /data/dsa110-contimg/state/products.db \
    --output-dir /data/dsa110-contimg/qa_outputs/antenna_health/current \
    --hours 24

# Queue health
python -m dsa110_contimg.qa.queue_health_monitoring \
    --queue-db /data/dsa110-contimg/state/streaming_ingest.db \
    --output-dir /data/dsa110-contimg/qa_outputs/queue_health/current \
    --hours 24

# Disk usage
python -m dsa110_contimg.qa.disk_usage_monitoring \
    --output-dir /data/dsa110-contimg/qa_outputs/disk_usage/current
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status dsa110-monitoring

# Check logs for errors
sudo journalctl -u dsa110-monitoring -n 50

# Verify Python environment
/opt/miniforge/envs/casa6/bin/python --version

# Test module directly
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.qa.monitoring_service
```

### No Plots Being Generated

```bash
# Check directory permissions
ls -ld /data/dsa110-contimg/qa_outputs/*/current/

# Check database exists
ls -lh /data/dsa110-contimg/state/*.db

# Run module manually to see errors
python -m dsa110_contimg.qa.performance_monitoring --hours 24
```

### High CPU Usage

```bash
# Check monitoring intervals (may be too frequent)
# Edit /etc/systemd/system/dsa110-monitoring.service
# Increase interval values

sudo systemctl daemon-reload
sudo systemctl restart dsa110-monitoring
```

## Uninstallation

```bash
# Stop services
sudo systemctl stop dsa110-monitoring
sudo systemctl stop dsa110-disk-monitor

# Disable services
sudo systemctl disable dsa110-monitoring
sudo systemctl disable dsa110-disk-monitor

# Remove service files
sudo rm /etc/systemd/system/dsa110-monitoring.service
sudo rm /etc/systemd/system/dsa110-disk-monitor.service

# Reload systemd
sudo systemctl daemon-reload

# Optional: Remove QA outputs
# rm -rf /data/dsa110-contimg/qa_outputs
```

## Next Steps

- Configure alert thresholds in service files
- Set up frontend dashboard to display visualizations
- Configure email/Slack alerting (future enhancement)
- Set up automated archival and cleanup cron jobs

## Support

For issues or questions:

- Check logs: `sudo journalctl -u dsa110-monitoring -f`
- See integration guide:
  `/data/dsa110-contimg/internal/docs/dev-notes/analysis/INTEGRATION_GUIDE.md`
- Test modules individually using CLI commands above

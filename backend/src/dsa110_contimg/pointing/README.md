# DSA-110 Pointing Monitor

Monitors telescope pointing and tracks calibrator transits for the DSA-110
drift-scan telescope.

## Overview

The DSA-110 is a transit telescope that observes sources as they cross the
meridian. This monitor predicts when calibrators will transit and tracks
pointing status for pipeline coordination.

## Features

- **LST Calculation**: Real-time Local Sidereal Time at DSA-110 location
- **Transit Prediction**: Predicts when calibrators will cross the meridian
- **Active Calibrator Detection**: Identifies calibrators currently transiting
- **Status Reporting**: Writes JSON status file for health monitoring
- **Historical Tracking**: Maintains recent transit history

## Installation

The pointing monitor is part of the `dsa110_contimg` package:

```bash
conda activate casa6
pip install -e /data/dsa110-contimg/backend
```

## Usage

### As a Daemon (systemd)

```bash
# Install the service
sudo cp /data/dsa110-contimg/backend/ops/systemd/contimg-pointing.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start the service
sudo systemctl start contimg-pointing.service
sudo systemctl enable contimg-pointing.service

# Check status
sudo systemctl status contimg-pointing.service
```

### Command Line

```bash
# Run as daemon
python -m dsa110_contimg.pointing.monitor

# Single status check
python -m dsa110_contimg.pointing.monitor --once

# Custom configuration
python -m dsa110_contimg.pointing.monitor \
    --status-file /path/to/status.json \
    --update-interval 30 \
    --log-level DEBUG
```

### Python API

```python
from dsa110_contimg.pointing import (
    calculate_lst,
    predict_calibrator_transit,
    get_active_calibrator,
    PointingMonitor,
)

# Get current LST
lst = calculate_lst()
print(f"Current LST: {lst:.4f} hours")

# Predict next transit of 3C286
transit = predict_calibrator_transit("3C286")
print(f"3C286 transits at {transit.transit_utc}")
print(f"Time to transit: {transit.time_to_transit_sec/60:.1f} minutes")

# Check if a calibrator is currently transiting
active = get_active_calibrator()
if active:
    print(f"Currently observing: {active}")
```

## Status File Format

The monitor writes a JSON status file (default: `/data/dsa110-contimg/state/pointing_status.json`):

```json
{
  "current_lst": 14.5234,
  "current_utc": "2025-01-15T12:30:00Z",
  "active_calibrator": "3C286",
  "upcoming_transits": [
    {
      "calibrator": "3C48",
      "ra_deg": 24.422,
      "dec_deg": 33.1597,
      "transit_utc": "2025-01-15T14:00:00Z",
      "time_to_transit_sec": 5400.0,
      "lst_at_transit": 1.6281,
      "elevation_at_transit": 75.2,
      "status": "scheduled"
    }
  ],
  "recent_transits": [...],
  "monitor_healthy": true,
  "last_update": "2025-01-15T12:30:00Z",
  "uptime_sec": 3600.0
}
```

## Calibrators Tracked

The default calibrator list includes standard VLA flux calibrators:

| Name      | RA (deg) | Dec (deg) | Flux 1.4GHz (Jy) |
| --------- | -------- | --------- | ---------------- |
| 3C286     | 202.78   | +30.51    | 14.65            |
| 3C48      | 24.42    | +33.16    | 15.67            |
| 3C147     | 85.65    | +49.85    | 21.64            |
| 3C138     | 80.29    | +16.64    | 8.23             |
| J0834+555 | 128.58   | +55.58    | ~5.0             |

## Health Monitoring Integration

The pointing monitor integrates with the pipeline health system:

```python
from dsa110_contimg.monitoring import check_systemd_service

# Check pointing monitor health
result = check_systemd_service("contimg-pointing.service")
print(f"Status: {result.status}")
```

The unified health API at `/api/v1/health/full` includes pointing monitor status.

## Logs

Logs are written to:

- `/data/dsa110-contimg/state/logs/pointing-monitor.log`

View logs:

```bash
tail -f /data/dsa110-contimg/state/logs/pointing-monitor.log
journalctl -u contimg-pointing.service -f
```

## Technical Notes

### Transit Calculation

Transit occurs when Local Sidereal Time (LST) equals the source's Right
Ascension (RA). The calculation accounts for:

1. **Sidereal time conversion**: 1 sidereal hour ≈ 0.9973 solar hours
2. **DSA-110 location**: Lat 37.23°, Lon -118.28°
3. **Wrap-around**: Handles RA values that transit after midnight LST

### Observation Window

Each DSA-110 observation covers ~5 minutes (309 seconds) as sources drift
through the primary beam. The "active calibrator" detection uses a 5-minute
window centered on transit.

## Troubleshooting

### Monitor Not Starting

```bash
# Check service status
sudo systemctl status contimg-pointing.service

# Check logs
journalctl -u contimg-pointing.service -n 50

# Verify conda environment
conda activate casa6
python -c "from dsa110_contimg.pointing import calculate_lst; print(calculate_lst())"
```

### Incorrect Transit Times

Verify the system clock is synchronized:

```bash
timedatectl status
chronyc tracking
```

### Status File Not Updating

Check write permissions:

```bash
ls -la /data/dsa110-contimg/state/pointing_status.json
touch /data/dsa110-contimg/state/test.txt && rm /data/dsa110-contimg/state/test.txt
```

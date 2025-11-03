# Utility Scripts

This directory contains utility scripts for managing various aspects of the dsa110-contimg project.

## Files

### CASA Log Management

- **`casa_log_daemon.py`** - Python daemon that continuously monitors for new casa-*.log files and automatically moves them to the state directory
- **`move_casa_logs.sh`** - Bash script for one-time bulk moves of existing casa-*.log files
- **`cleanup_casa_logs.sh`** - Bash script for cleaning up old casa-*.log files (with optional retention period)
- **`casa-log-daemon.service`** - Systemd service file for running the daemon as a system service
- **`casa-log-cleanup.service`** - Systemd service file for cleaning up old logs
- **`casa-log-cleanup.timer`** - Systemd timer file for automatic cleanup every 6 hours

### Measurement Set Utilities

- **`create_test_ms.py`** - Create a smaller, representative MS for testing (e.g., K-calibration testing)
  - Reduces antenna/baseline count while preserving full bandwidth and calibrator field
  - Uses CASA `split` to subset data
  - See usage below

- **`check_upstream_delays.py`** - Check if instrumental delays are already corrected upstream
  - Analyzes phase vs frequency slopes in raw DATA column
  - Provides recommendation on whether K-calibration is necessary
  - See usage below

- **`verify_kcal_delays.py`** - Verify K-calibration delay solutions
  - Inspects K-calibration tables
  - Computes delay statistics
  - Analyzes phase coherence impact

## Measurement Set Utilities Usage

### Creating a Test MS

Create a smaller MS for faster testing while preserving essential characteristics:

```bash
conda run -n casa6 python scripts/create_test_ms.py \
  <input_ms> <output_ms> \
  --max-baselines 15 \
  --max-times 50
```

**Why subsetting is valid for delay testing:**

K-calibration measures frequency-independent instrumental delays per antenna.
Since delays are per-antenna (not per-baseline), a reduced baseline set is
sufficient for solving delay solutions, as long as:
1. Full bandwidth is preserved (all SPWs needed to measure phase slope vs frequency)
2. Calibrator field is present (bright source for high SNR delay measurement)
3. Reference antenna is included (needed for relative delay solutions)
4. Multiple baselines exist (sufficient to solve per-antenna delays)

**What it preserves:**
- All spectral windows (full bandwidth needed for delay testing)
- Calibrator field (bright source needed for calibration)
- Reference antenna (e.g., antenna 103) and baselines containing it
- Multiple baselines (sufficient for solving per-antenna delays)

**What it removes:**
- Most antennas (reduces from 96 to ~6-16 antennas)
- Most baselines (reduces by ~80-90%)
- Some time integrations (reduces by ~10-50%)

**Example:**
```bash
# Create test MS from full MS
python scripts/create_test_ms.py \
  /scratch/dsa110-contimg/ms/0834_555_single/sequential/0834_555_2025-10-30_134913.ms \
  /scratch/dsa110-contimg/ms/0834_555_single/sequential/0834_555_2025-10-30_134913_test.ms \
  --max-baselines 15 \
  --max-times 24

# Result: ~6.6x smaller (2.1 GB → 316 MB), still suitable for K-calibration testing
```

**Note:** The output filename suffix `_test.ms` indicates this is a subset MS
created for testing purposes. The full MS should be used for production imaging.

### Checking Upstream Delay Correction

Check if delays are already corrected upstream:

```bash
conda run -n casa6 python scripts/check_upstream_delays.py \
  <ms_path> \
  --n-baselines 50
```

**Method:**
The script analyzes phase vs frequency slopes in the raw DATA column:
1. Extracts unflagged visibilities across frequency channels
2. Computes phase and unwraps to handle 2π ambiguities
3. Fits linear model: phase = delay × 2π × frequency + constant
4. Converts phase slope to delay (nanoseconds)
5. Aggregates statistics across baselines and antennas

**Output interpretation (thresholds are estimates based on physics, not standard values):**
- **< 1 ns**: Delays likely corrected upstream, K-calibration may be redundant
  - For DSA-110's 187 MHz bandwidth, this corresponds to <0.6π radians phase slope
- **1-5 ns**: Partially corrected, K-calibration optional but recommended
- **> 5 ns**: Not corrected, K-calibration is necessary
  - For DSA-110's 187 MHz bandwidth, this corresponds to >3π radians phase slope

**Note:** These thresholds are estimates based on the relationship: 1 ns delay = π radians
phase slope across 500 MHz bandwidth (Reid, NED). Actual thresholds depend on observing
frequency, bandwidth, and instrumental characteristics. The phase-frequency slope method
itself is a standard technique for detecting delays.

**Important caveats:**
- Phase slopes can arise from instrumental delays (what we're measuring),
  geometric delays (if not perfectly phased), bandpass variations, or source
  structure
- If data is properly phased, delays > 1 ns are likely instrumental
- This provides a quick check but doesn't definitively prove delays are purely
  instrumental; K-calibration testing is still recommended for confirmation

**Example:**
```bash
python scripts/check_upstream_delays.py \
  /scratch/dsa110-contimg/ms/0834_555_single/sequential/0834_555_2025-10-30_134913_test.ms \
  --n-baselines 30
```

## Usage

### Automatic Cleanup (Recommended)

The cleanup runs automatically every 6 hours via systemd timer, keeping only logs from the last 6 hours:

```bash
# Install and enable the timer
sudo cp scripts/casa-log-cleanup.service /etc/systemd/system/
sudo cp scripts/casa-log-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable casa-log-cleanup.timer
sudo systemctl start casa-log-cleanup.timer

# Check timer status
sudo systemctl status casa-log-cleanup.timer

# View recent cleanup runs
sudo journalctl -u casa-log-cleanup.service -n 20
```

### Manual Cleanup

You can run the cleanup script manually:

```bash
# Delete all casa-*.log files
./scripts/cleanup_casa_logs.sh

# Keep logs from last 24 hours, delete older ones
./scripts/cleanup_casa_logs.sh --keep-hours 24

# Preview what would be deleted (dry run)
./scripts/cleanup_casa_logs.sh --keep-hours 6 --dry-run
```

### Continuous Monitoring (Legacy - Not Needed with Code Changes)

The daemon runs automatically as a system service and monitors `/data/dsa110-contimg/` for new casa-*.log files.

**Service Management:**
```bash
# Check status
sudo systemctl status casa-log-daemon

# Start/stop/restart
sudo systemctl start casa-log-daemon
sudo systemctl stop casa-log-daemon
sudo systemctl restart casa-log-daemon

# View logs
sudo journalctl -u casa-log-daemon -f
```

**Manual Daemon:**
```bash
# Run in foreground
python3 casa_log_daemon.py

# Run as daemon (background)
python3 casa_log_daemon.py --daemon

# Custom source/target directories
python3 casa_log_daemon.py --source /path/to/source --target /path/to/target
```

### One-time Bulk Move

For moving existing casa-*.log files:

```bash
# Preview what would be moved (dry run)
./move_casa_logs.sh --dry-run

# Actually move the files
./move_casa_logs.sh
```

## How It Works

1. **Log Redirection**: CASA log files are automatically written to `/data/dsa110-contimg/state/logs/` via code changes in `job_runner.py` (no CPU overhead)
2. **Automatic Cleanup**: Systemd timer runs cleanup every 6 hours, keeping only logs from the last 6 hours
3. **Manual Cleanup**: The cleanup script can be run manually with custom retention periods

## Requirements

- Python 3.6+
- `watchdog` library (for daemon, optional: `pip install watchdog`)
- Systemd (for service and timer management)

## Installation

1. Install the watchdog library (if using daemon):
   ```bash
   pip install watchdog
   ```

2. Install automatic cleanup timer:
   ```bash
   sudo cp scripts/casa-log-cleanup.service /etc/systemd/system/
   sudo cp scripts/casa-log-cleanup.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable casa-log-cleanup.timer
   sudo systemctl start casa-log-cleanup.timer
   ```

3. Install daemon (optional, for legacy compatibility):
   ```bash
   sudo cp scripts/casa-log-daemon.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable casa-log-daemon
   sudo systemctl start casa-log-daemon
   ```

## Logs

- **CASA logs**: `/data/dsa110-contimg/state/logs/casa-*.log` (automatically cleaned every 6 hours)
- **Daemon logs**: `/data/dsa110-contimg/state/logs/casa_log_daemon_YYYYMMDD.log` (if daemon is running)
- **Cleanup logs**: `sudo journalctl -u casa-log-cleanup.service`
- **System logs**: `sudo journalctl -u casa-log-daemon` (if daemon is running)

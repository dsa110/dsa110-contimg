# Moved

This content was consolidated into `docs/how-to/streaming.md` (Overview and
Standalone Converter sections), plus `docs/concepts/streaming-architecture.md`
for deeper details.

- Science MS → `ms/science/YYYY-MM-DD/<timestamp>.ms`
- Calibrator MS → `ms/calibrators/YYYY-MM-DD/<timestamp>.ms`
- Failed MS → `ms/failed/YYYY-MM-DD/<timestamp>.ms`

### Queue States & Stages

The `ingest_queue` table uses the following state machine:

- `collecting` → waiting for all 16 subbands to arrive
- `pending` → ready for processing
- `in_progress` → claimed by a worker
- `processing_fresh` → first-pass conversion underway
- `resuming` → recovery from an existing checkpoint
- `failed` → exceeded retry budget (check `error` column)
- `completed` → measurement set written successfully

`processing_stage` stays `resuming` for restarted jobs so operators can
distinguish them from fresh runs. Timing metrics are recorded in
`performance_metrics` with per-stage durations extracted from converter logs
(and automatically backfilled if a log line is missing).

## Setup Instructions

### Dependencies

```bash
# Core dependencies (already installed)
conda activate casa6
pip install watchdog psutil  # Optional: for file watching and system metrics
```

### Directory Structure

```
/stage/dsa110-contimg/
├── incoming/              # Watched directory for new subband files
├── ms/                    # Final Measurement Sets (organized)
│   ├── science/           # Science observations
│   │   └── YYYY-MM-DD/    # Organized by date
│   │       └── <timestamp>.ms/
│   ├── calibrators/       # Calibrator observations
│   │   └── YYYY-MM-DD/    # Organized by date
│   │       └── <timestamp>.ms/
│   └── failed/            # Failed conversions
│       └── YYYY-MM-DD/    # Organized by date
│           └── <timestamp>.ms/
└── state/                 # SQLite databases (queue, products, registry)
```

**Note**: MS files are written directly to organized locations during
conversion. See `docs/how-to/ms_organization.md` for details.

### Permissions

```bash
# Ensure write access to all directories
sudo chown -R $USER:$USER /data/incoming_data /data/output /data/scratch /data/checkpoints
chmod 755 /data/incoming_data /data/output /data/scratch /data/checkpoints
```

## Deployment Examples (superseded)

Note: Prefer the consolidated references:

- `docs/reference/cli.md` for module entrypoints
- `docs/operations/deploy-systemd.md` for systemd
- `docs/operations/deploy-docker.md` for docker-compose

### 1. Systemd Service (Recommended)

Create `/etc/systemd/system/dsa110-streaming-converter.service`:

```ini
[Unit]
Description=DSA-110 Streaming Converter
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/data/dsa110-contimg
Environment=PATH=/opt/conda/envs/casa6/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/conda/envs/casa6/bin/python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming_data \
    --output-dir /data/output/ms \
    --scratch-dir /data/scratch \
    --checkpoint-dir /data/checkpoints \
    --chunk-duration 5.0 \
    --omp-threads 4 \
    --monitor-interval 60 \
    --log-level INFO
# Append "--no-monitoring" if you need to disable runtime monitoring.
# Adjust "--chunk-duration" if the ingest cadence changes.
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dsa110-streaming-converter
sudo systemctl start dsa110-streaming-converter
sudo systemctl status dsa110-streaming-converter
```

### 2. Screen/Tmux Session

```bash
# Start in screen session
screen -S streaming-converter
cd /data/dsa110-contimg
conda activate casa6
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming_data \
    --output-dir /data/output/ms \
    --scratch-dir /data/scratch \
    --checkpoint-dir /data/checkpoints \
    --chunk-duration 5.0 \
    --omp-threads 4

# Detach: Ctrl+A, D
# Reattach: screen -r streaming-converter
```

### 3. Docker Container

```dockerfile
FROM continuumio/miniconda3

RUN conda create -n casa6 python=3.8 -y
RUN conda activate casa6 && pip install watchdog psutil

COPY . /app
WORKDIR /app

CMD ["conda", "run", "-n", "casa6", "python", "-m", "dsa110_contimg.conversion.streaming.streaming_converter", \
     "--input-dir", "/data/incoming_data", \
     "--output-dir", "/data/output/ms", \
     "--scratch-dir", "/data/scratch", \
     "--checkpoint-dir", "/data/checkpoints", \
     "--chunk-duration", "5.0"]
```

## Configuration Reference

### Required Arguments

- `--input-dir`: Directory to watch for incoming `*_sb??.hdf5` files
- `--output-dir`: Destination directory for Measurement Sets

### Optional Arguments

#### Performance Tuning

- `--scratch-dir`: Fast storage for staging UVFITS/MS (recommended: NVMe, tmpfs)
- `--checkpoint-dir`: Persistent checkpoints for fault tolerance
- `--chunk-duration N`: Duration of data chunks in minutes (default: 5.0)
- `--omp-threads N`: Limit OpenMP/MKL threads (default: 4)
- `--use-subprocess`: Launch converter in separate process (default: in-process)
- `--stage-inputs` / `--stage-workers N`: Optionally copy subband files into a
  local temp directory before conversion to reduce random I/O on networked
  disks.

#### Monitoring & Logging

- `--monitoring` / `--no-monitoring`: Enable or disable queue/resource
  monitoring (default: enabled)
- `--monitor-interval N`: Monitoring check interval in seconds (default: 60)
- `--profile`: Enable detailed performance profiling
- `--log-level LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

#### Queue Management

- `--queue-db PATH`: SQLite queue database path (default:
  streaming_queue.sqlite3)
- `--expected-subbands N`: Expected subbands per group (default: 16)
- `--max-retries N`: Maximum retries before marking failed (default: 3)
- `--in-progress-timeout N`: Seconds before stale groups are re-queued
  (default: 900)
- `--collecting-timeout N`: Warn if groups incomplete for N seconds
  (default: 600)

#### File Watching

- `--poll-interval N`: Polling interval when watchdog unavailable (default: 5)
- `--worker-poll-interval N`: Worker idle wait time (default: 5)

#### Cleanup

- `--cleanup-temp`: Remove temporary staging directories after conversion

## Troubleshooting Guide

### Queue Inspection

```bash
# Check queue status
sqlite3 streaming_queue.sqlite3 "SELECT group_id, state, processing_stage, retry_count, error FROM ingest_queue ORDER BY received_at DESC LIMIT 10;"
# processing_stage will report 'processing_fresh' for new work and 'resuming' for checkpoint recoveries.

# Check performance metrics
sqlite3 streaming_queue.sqlite3 "SELECT group_id, total_time, load_time, phase_time, write_time FROM performance_metrics ORDER BY recorded_at DESC LIMIT 10;"
# Missing log lines are automatically backfilled so totals stay within the 5-minute chunk.

# Check queue statistics
sqlite3 streaming_queue.sqlite3 "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state;"
```

### Common Issues

#### 1. High Queue Depth

```
WARNING: High queue depth: 15 groups queued
```

**Solution**: Check if worker is running, increase `--omp-threads`, or use
faster storage

#### 2. Performance Warnings

```
WARNING: Group 2025-10-05T12:30:00 took 285.2 s (exceeds 4.5 min threshold)
```

**Solution**: Use `--scratch-dir` with fast storage, reduce `--omp-threads`, or
check system load

#### 3. Stale In-Progress Groups

```
WARNING: Found 2 stale in-progress groups (>15 min)
```

**Solution**: Check for hung processes, restart service, or reduce
`--in-progress-timeout`

#### 4. Missing Subbands

```
WARNING: Group 2025-10-05T12:30:00 has been waiting for missing subbands longer than 600 s
```

**Solution**: Check data ingest pipeline, verify file permissions, or increase
`--collecting-timeout`

### Checkpoint Recovery

```bash
# List checkpoints
ls -la /data/checkpoints/*.checkpoint.uvh5

# Resume from specific checkpoint
sqlite3 streaming_queue.sqlite3 "UPDATE ingest_queue SET state='pending', processing_stage='collecting' WHERE group_id='2025-10-05T12:30:00';"
```

### Performance Tuning

#### 1. Storage Optimization

```bash
# Use tmpfs for scratch (if sufficient RAM)
sudo mount -t tmpfs -o size=50G tmpfs /data/scratch

# Use NVMe for scratch
--scratch-dir /mnt/nvme/scratch
```

#### 2. Thread Optimization

```bash
# For 8-core system
--omp-threads 4

# For 16-core system
--omp-threads 8
```

#### 3. Monitoring Setup

```bash
# Enable detailed profiling
--profile --log-level DEBUG

# Monitor system resources
htop
iotop
```

### Log Analysis

```bash
# Follow logs in real-time
tail -f /var/log/syslog | grep streaming-converter

# Check for errors
grep ERROR /var/log/syslog | grep streaming-converter

# Performance analysis
grep "completed in" /var/log/syslog | grep streaming-converter
```

## Production Deployment Checklist

- [ ] Install dependencies (`watchdog`, `psutil`)
- [ ] Create directory structure with proper permissions
- [ ] Configure systemd service with appropriate resource limits
- [ ] Set up log rotation for long-running service
- [ ] Configure monitoring/alerting for queue depth and failures
- [ ] Test with sample data before production deployment
- [ ] Document recovery procedures for your environment
- [ ] Set up backup strategy for checkpoints and queue database

## Migration from Batch Converter

The streaming converter is designed to replace the batch converter for real-time
processing:

1. **Batch converter**: Processes historical data in large chunks
2. **Streaming converter**: Processes data as it arrives in 5-minute windows

For historical data processing, continue using the batch converter. For
real-time ingest, use the streaming converter.

### Staging & Storage Strategy

The streaming worker forwards scratch configuration to the batch converter and
benefits from its tmpfs/SSD staging behavior:

- Inputs: With `--stage-inputs`, subbands are copied (in parallel) into a local
  temp directory; otherwise they are symlinked. This can improve locality on
  systems where the ingest directory is remote.
- Scratch: Set `--scratch-dir /scratch` to keep per‑subband MS parts on fast
  local SSD. The converter concatenates these parts into the staged MS.
- tmpfs: When enabled by the converter (default), the final MS is staged in RAM
  (`/dev/shm`) when capacity allows and then moved into the output directory.

See `docs/concepts/streaming-architecture.md` for details on the converter’s
tmpfs thresholding and finalization.

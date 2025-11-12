# Quality Assurance & Alerting Setup Guide

## Overview

The DSA-110 pipeline includes comprehensive quality assurance checks and alerting to ensure high-quality MS files and images with minimal human intervention.

## Quick Start

### 1. Enable Slack Alerts

Get a Slack webhook URL from your workspace:
1. Go to https://api.slack.com/apps
2. Create a new app or use existing
3. Enable Incoming Webhooks
4. Add webhook to workspace
5. Copy the webhook URL

Add to `/data/dsa110-contimg/ops/systemd/contimg.env`:
```bash
CONTIMG_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Restart services:
```bash
sudo systemctl restart contimg-stream contimg-api
```

### 2. Test Alerting

```python
from dsa110_contimg.utils import alerting

# Send a test alert
alerting.info("test", "Alerting system is working!")

# Test different severity levels
alerting.warning("test", "This is a warning")
alerting.error("test", "This is an error")
alerting.critical("test", "This is critical!")
```

### 3. Fast Pipeline Validation (<60 seconds)

For rapid validation of the entire pipeline, use the fast validation system:

```python
from dsa110_contimg.qa.fast_validation import ValidationMode, validate_pipeline_fast

# Fast mode (<30s) - Recommended for quick checks
result = validate_pipeline_fast(
    ms_path="/path/to/your.ms",
    caltables=["/path/to/cal.kcal"],
    image_paths=["/path/to/image.fits"],
    mode=ValidationMode.FAST,
    alert_on_issues=True,
)

if not result.passed:
    print("Pipeline validation failed!")
    print(f"Errors: {result.errors}")
    print(f"Timing: {result.timing}")
```

**Validation Modes:**
- `FAST`: <30s, aggressive sampling, skip expensive checks
- `STANDARD`: <60s, balanced detail/speed (recommended)
- `COMPREHENSIVE`: <5min, full validation

### 4. Check MS Quality After Conversion

```python
from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion

# Quick check (fast)
passed, metrics = check_ms_after_conversion(
    "/path/to/your.ms",
    quick_check_only=True,
    alert_on_issues=True,
)

# Full validation (comprehensive)
passed, metrics = check_ms_after_conversion(
    "/path/to/your.ms",
    quick_check_only=False,
    alert_on_issues=True,
)

if not passed:
    print("MS has quality issues!")
    print(metrics)
```

### 5. Check Calibration Quality

```python
from dsa110_contimg.qa.pipeline_quality import check_calibration_quality

# Check calibration tables and CORRECTED_DATA
passed, results = check_calibration_quality(
    caltables=[
        "/path/to/ms.kcal",
        "/path/to/ms.bpcal",
        "/path/to/ms.gpcal",
    ],
    ms_path="/path/to/calibrated.ms",
    alert_on_issues=True,
)

if not passed:
    print("Calibration has quality issues!")
    print(results)
```

### 6. Check Image Quality

```python
from dsa110_contimg.qa.pipeline_quality import check_image_quality

# Check final image
passed, metrics = check_image_quality(
    "/path/to/image.image.pbcor",
    alert_on_issues=True,
    quick_check_only=False,
)

if passed:
    print(f"Image quality: SNR={metrics['peak_snr']:.1f}, DR={metrics['dynamic_range']:.1f}")
```

## Quality Metrics Collected

### MS Quality Metrics

**Basic Properties:**
- Number of rows, antennas, baselines, channels, SPWs, fields, scans
- Time range and MS size
- Column presence (DATA, MODEL_DATA, CORRECTED_DATA, WEIGHT_SPECTRUM)

**Data Quality:**
- Fraction flagged
- Fraction of zero amplitudes
- Median/RMS amplitude
- Amplitude range

**UVW Validity:**
- UVW presence and validity
- Median UV distance
- All-zeros check

**Alerts Triggered:**
- CRITICAL: Missing required columns, zero rows, all-zero UVW
- WARNING: High flagging (>50%), high zero fraction (>30%)

### Calibration Quality Metrics

**Solution Statistics:**
- Number of solutions per antenna/SPW
- Fraction of flagged solutions
- Median amplitude and scatter
- Median phase and scatter

**CORRECTED_DATA Checks:**
- Presence and validity
- Calibration factor (corrected/original amplitude ratio)
- All-zeros check

**Alerts Triggered:**
- ERROR: All solutions flagged, CORRECTED_DATA all zeros
- WARNING: High flagging (>30%), unusual amplitudes, large phase scatter (>90°)

### Image Quality Metrics

**Image Properties:**
- Dimensions (nx, ny, channels, Stokes)
- Image type (image, residual, psf, pb, pbcor)
- Image size

**Pixel Statistics:**
- Median, RMS, min, max
- Dynamic range (peak/RMS)
- Peak SNR

**Source Detection:**
- Number of pixels above 5-sigma
- Peak location and value

**Alerts Triggered:**
- ERROR: All NaN/Inf pixels, all zeros
- WARNING: Low dynamic range (<5), low peak SNR (<5), few detections

## Quality Thresholds

Configure in `contimg.env`:

```bash
# MS quality thresholds
CONTIMG_QA_MS_MAX_FLAGGED=0.5          # Max fraction flagged
CONTIMG_QA_MS_MAX_ZEROS=0.3            # Max fraction zeros
CONTIMG_QA_MS_MIN_AMP=1e-6             # Min median amplitude

# Calibration quality thresholds
CONTIMG_QA_CAL_MAX_FLAGGED=0.3         # Max fraction flagged
CONTIMG_QA_CAL_MIN_AMP=0.1             # Min median amplitude
CONTIMG_QA_CAL_MAX_AMP=10.0            # Max median amplitude
CONTIMG_QA_CAL_MAX_PHASE_SCATTER=90.0  # Max phase scatter (deg)

# Image quality thresholds
CONTIMG_QA_IMG_MIN_DYNAMIC_RANGE=5.0   # Min peak/RMS
CONTIMG_QA_IMG_MIN_PEAK_SNR=5.0        # Min peak SNR
CONTIMG_QA_IMG_MIN_5SIGMA_PIXELS=10    # Min pixels > 5-sigma
```

## Integration with Pipeline

### In Conversion (streaming_converter.py)

```python
from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion

# After MS creation
ms_path = convert_group(group_id)

# Quick validation
passed, metrics = check_ms_after_conversion(ms_path, quick_check_only=True)
if not passed:
    # Mark as failed in queue
    queue_db.mark_failed(group_id, "ms_quality_check_failed")
    return
```

### In Calibration (calibration/cli.py)

```python
from dsa110_contimg.qa.pipeline_quality import check_calibration_quality

# After solving calibration
caltables = solve_delay(...) + solve_bandpass(...) + solve_gains(...)

# Validate calibration quality
passed, results = check_calibration_quality(caltables, ms_path=ms)
if not passed:
    logger.error("Calibration quality check failed")
    # Could retry with different parameters or flag for manual review
```

### In Imaging (imaging/worker.py)

```python
from dsa110_contimg.qa.pipeline_quality import check_image_quality

# After imaging
artifacts = image_ms(ms_path, imagename=img_base)

# Validate each image product
for artifact in artifacts:
    if artifact.endswith(".image.pbcor"):
        passed, metrics = check_image_quality(artifact, alert_on_issues=True)
        if passed and metrics["peak_snr"] > 10:
            # High-quality image - success alert sent automatically
            pass
```

## Alert Categories

Alerts are organized by pipeline stage:

- **`ms_conversion`**: MS quality issues after UVH5→MS conversion
- **`calibration`**: Calibration table or CORRECTED_DATA issues
- **`imaging`**: Image quality issues
- **`disk_space`**: Low disk space warnings
- **`queue_depth`**: Queue backup warnings
- **`stuck_job`**: Stuck conversion/calibration/imaging jobs
- **`system`**: System health issues (CPU, memory, I/O)

## Rate Limiting

Alerts are rate-limited to prevent spam:
- Default: Max 10 alerts per category per 5 minutes
- Suppressed alerts summarized periodically
- Configure via AlertManager parameters

## Email Alerts (Optional)

For critical issues, you can also enable email alerts:

```bash
CONTIMG_SMTP_HOST=smtp.gmail.com
CONTIMG_SMTP_PORT=587
CONTIMG_SMTP_USER=your-email@gmail.com
CONTIMG_SMTP_PASSWORD=your-app-password
CONTIMG_ALERT_FROM_EMAIL=dsa110-pipeline@example.com
CONTIMG_ALERT_TO_EMAILS=ops@example.com,admin@example.com
```

Email alerts default to ERROR and CRITICAL severity only.

## Viewing Alert History

Via API:
```bash
curl http://localhost:8000/api/alerts/recent?minutes=60
```

Via Python:
```python
from dsa110_contimg.utils.alerting import get_alert_manager

manager = get_alert_manager()
recent_alerts = manager.get_recent_alerts(minutes=60)

for alert in recent_alerts:
    print(f"{alert.severity.name}: {alert.message}")
```

## Best Practices

1. **Start with INFO alerts** to understand normal operation
2. **Tune thresholds** based on your data characteristics
3. **Monitor alert frequency** - too many means thresholds need adjustment
4. **Review suppressed alerts** periodically
5. **Test alerts** after any configuration changes
6. **Document false positives** and adjust thresholds
7. **Set up alerting** before going to production

## Troubleshooting

### No alerts being sent

1. Check environment variable is set:
   ```bash
   echo $CONTIMG_SLACK_WEBHOOK_URL
   ```

2. Test webhook directly:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     $CONTIMG_SLACK_WEBHOOK_URL
   ```

3. Check logs for alerting errors:
   ```bash
   journalctl -u contimg-stream -f | grep -i alert
   ```

### Too many alerts (spam)

1. Increase rate limit window or decrease count
2. Adjust quality thresholds in `contimg.env`
3. Consider raising minimum severity level

### Alerts not reaching Slack

1. Verify webhook URL is correct
2. Check Slack app permissions
3. Verify network connectivity from server to Slack
4. Check for SSL/TLS errors in logs

## Example: Full Pipeline Integration

```python
from dsa110_contimg.qa.pipeline_quality import (
    check_ms_after_conversion,
    check_calibration_quality,
    check_image_quality,
)
from dsa110_contimg.utils import alerting

def process_observation(group_id):
    """Process one observation with full QA."""
    
    # Stage 1: Convert
    alerting.info("pipeline", f"Starting conversion of {group_id}")
    ms_path = convert_uvh5_to_ms(group_id)
    
    # QA: Check MS
    passed, metrics = check_ms_after_conversion(ms_path, quick_check_only=False)
    if not passed:
        alerting.critical("pipeline", f"MS quality check failed for {group_id}")
        return False
    
    # Stage 2: Calibrate (if calibrator)
    if is_calibrator(ms_path):
        caltables = run_calibration(ms_path)
        
        # QA: Check calibration
        passed, results = check_calibration_quality(caltables, ms_path=ms_path)
        if not passed:
            alerting.error("pipeline", f"Calibration quality check failed for {group_id}")
            return False
    
    # Stage 3: Image
    artifacts = run_imaging(ms_path)
    
    # QA: Check images
    for artifact in artifacts:
        if ".image" in artifact:
            passed, metrics = check_image_quality(artifact)
            if not passed:
                alerting.error("pipeline", f"Image quality check failed: {artifact}")
    
    alerting.info("pipeline", f"Successfully processed {group_id}")
    return True
```

## Next Steps

1. Enable Slack webhook in `contimg.env`
2. Test alerting with sample data
3. Monitor alerts for 24 hours
4. Tune thresholds based on false positive rate
5. Add email alerts for critical issues
6. Document your threshold choices in operations runbook


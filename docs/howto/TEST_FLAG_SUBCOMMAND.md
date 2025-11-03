# Testing the Flag Subcommand

This guide explains how to test the `flag` subcommand on a real Measurement Set.

## Prerequisites

The flag subcommand requires:
- CASA6 with `casatasks` module
- Python environment with project dependencies
- Valid CASA Measurement Set (MS) file

## Test Target

MS file: `/data/dsa110-contimg/ms/2025-11-02T13:40:03.ms`

This is a 5.1 GB MS file with calibrator data from 2025-11-02.

## Running Environment

The flag subcommand should be run in the same environment as other CASA-dependent commands. Based on the project setup:

1. **With conda environment** (if available):
   ```bash
   conda activate contimg  # or your CASA environment name
   cd /data/dsa110-contimg
   python -m dsa110_contimg.calibration.cli flag --help
   ```

2. **With systemd service environment** (if using systemd):
   The systemd service should source `/data/dsa110-contimg/ops/systemd/contimg.env`
   which sets up CASA environment variables.

3. **Direct Python execution** (if CASA is installed system-wide):
   ```bash
   cd /data/dsa110-contimg
   export PYTHONPATH=/data/dsa110-contimg/src:$PYTHONPATH
   python -m dsa110_contimg.calibration.cli flag --help
   ```

## Test Sequence

### Step 1: Check Help (Verification)

First, verify the command is accessible and shows proper help:

```bash
python -m dsa110_contimg.calibration.cli flag --help
```

Expected output should show:
- All 12 flagging modes listed
- Mode-specific argument descriptions
- Examples for common use cases

### Step 2: Summary Mode (Safe, Read-Only)

Start with the read-only `summary` mode to check current flagging status:

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode summary
```

**Expected output:**
```
[INFO] Computing flagging statistics...
======================================================================
Flagging Summary
======================================================================
MS: /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms
Total fraction flagged: X.XX%
Total rows: X,XXX
======================================================================
```

This establishes a baseline before making any flagging changes.

### Step 3: Shadow Flagging (Fast, Safe)

Test geometric shadow flagging. This is fast and safe:

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode shadow
```

**Expected output:**
```
[INFO] Flagging mode: shadow
[INFO] Flagging shadowed baselines (tolerance: 0.0 deg)...
[INFO] ✓ Shadow flagging complete

Flagging complete. Total flagged: X.XX%
```

### Step 4: Quack Flagging (Scan Edges)

Test flagging of scan beginnings to remove antenna settling transients:

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode quack \
  --quack-interval 2.0 \
  --quack-mode beg
```

**Expected output:**
```
[INFO] Flagging mode: quack
[INFO] Flagging beg of scans (2.0s)...
[INFO] ✓ Quack flagging complete (beg, 2.0s)

Flagging complete. Total flagged: X.XX%
```

### Step 5: Zero-Value Flagging

Flag zero-amplitude data (correlator failures):

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode zeros
```

**Expected output:**
```
[INFO] Flagging mode: zeros
[INFO] Flagging zero-value data...
[INFO] ✓ Zero-value data flagged

Flagging complete. Total flagged: X.XX%
```

### Step 6: RFI Flagging (Longer Operation)

Test the two-stage RFI detection (tfcrop + rflag). This may take several minutes:

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode rfi
```

**Expected output:**
```
[INFO] Flagging mode: rfi
[INFO] Flagging RFI (tfcrop + rflag)...
[INFO] ✓ RFI flagging complete

Flagging complete. Total flagged: X.XX%
```

### Step 7: Verify Changes

After flagging operations, verify the final state:

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode summary
```

Compare the flagged fraction before and after operations.

## Additional Test Modes

### Elevation Flagging

Flag low-elevation observations (< 10 degrees):

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode elevation \
  --lower-limit 10
```

### Amplitude Clip Flagging

Flag data outside amplitude range (e.g., > 10 Jy):

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode clip \
  --clip-min 0.0 \
  --clip-max 10.0
```

### Manual Selection Flagging

Flag specific antennas or scans:

```bash
# Flag a specific antenna
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode antenna \
  --antenna "10"

# Flag by UV range
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode baselines \
  --uvrange "2~50m"

# Manual selection with multiple criteria
python -m dsa110_contimg.calibration.cli flag \
  --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
  --mode manual \
  --antenna "10" \
  --scan "1~5"
```

## Troubleshooting

### ModuleNotFoundError: No module named 'casatasks'

**Solution:** Ensure you're running in a CASA environment. CASA must be installed and available in your Python path.

```bash
# Check if CASA is available
python -c "from casatasks import flagdata; print('CASA available')"

# If using conda
conda activate contimg  # or your CASA environment

# If using CASA standalone
source /path/to/casa/bin/thisinit.sh
```

### ValidationError: MS validation failed

**Solution:** Check that the MS path is correct and the MS is readable:

```bash
ls -ld /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms
```

### Permission Denied

**Solution:** Ensure you have write permissions on the MS directory:

```bash
ls -ld /data/dsa110-contimg/ms/
chmod -R u+w /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms  # if needed
```

## Expected Behavior

1. **All modes should:**
   - Validate the MS before flagging
   - Show progress messages
   - Report flagging statistics after completion
   - Exit with status 0 on success

2. **Summary mode should:**
   - Not modify any data
   - Display current flagging statistics
   - Work on read-only MS files

3. **Flagging modes should:**
   - Modify FLAG column in the MS
   - Show increased flagged fraction after operations
   - Handle errors gracefully with clear messages

## Notes

- **Backup recommendation:** Before extensive flagging, consider backing up the MS:
  ```bash
  cp -r /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
        /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms.backup
  ```

- **Flagging is cumulative:** Each flagging operation adds to existing flags unless you first run `--mode reset`.

- **Reset flags:** To unflag all data first:
  ```bash
  python -m dsa110_contimg.calibration.cli flag \
    --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
    --mode reset
  ```

- **Extend flags:** To grow existing flags to neighbors:
  ```bash
  python -m dsa110_contimg.calibration.cli flag \
    --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
    --mode extend \
    --grow-time 0.5 \
    --grow-freq 0.5
  ```

## Quick Reference

| Mode | Purpose | Speed | Modifies Data |
|------|---------|-------|---------------|
| `summary` | Statistics only | Fast | No |
| `shadow` | Geometric shadows | Fast | Yes |
| `quack` | Scan edges | Fast | Yes |
| `zeros` | Zero values | Fast | Yes |
| `elevation` | Elevation limits | Fast | Yes |
| `rfi` | RFI detection | Slow | Yes |
| `clip` | Amplitude thresholds | Medium | Yes |
| `extend` | Grow flags | Medium | Yes |
| `manual` | Custom selection | Fast | Yes |
| `antenna` | Specific antennas | Fast | Yes |
| `baselines` | UV range | Fast | Yes |
| `reset` | Unflag all | Fast | Yes |


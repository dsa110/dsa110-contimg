# HDF5-to-MS Conversion: User Tutorial

## What This Stage Does

The HDF5-to-MS conversion stage takes raw DSA-110 observation data (stored as UVH5 files in HDF5 format) and converts them into CASA Measurement Sets (MS) that can be calibrated and imaged.

**Input**: UVH5 files (`*_sb00.hdf5`, `*_sb01.hdf5`, ..., `*_sb15.hdf5` - 16 subbands)
**Output**: CASA Measurement Set (`.ms` directory)

---

## What You Can Do as a User

### 1. **Convert Data by Time Window** (Most Common)

Convert all complete 16-subband groups within a specific time range:

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00"
```

**What happens:**
- Finds all complete 16-subband groups between the start and end times
- Converts each group to a separate MS file
- Skips incomplete groups (missing subbands)
- Names MS files based on the group timestamp

**Use this when:** You know the exact time window you want to process.

---

### 2. **Find and Convert Calibrator Transit Data** (Recommended for Calibration)

Automatically find a calibrator transit and convert the data around it:

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30
```

**What happens:**
- Calculates when calibrator 0834+555 transited on the specified date
- Finds the observation group containing that transit
- Uses a ±30 minute window around the transit (configurable)
- Converts only the group that git addmatches the calibrator's declination

**Use this when:** You want to process calibrator data for calibration pipeline.

**Options:**
- `--transit-date YYYY-MM-DD` - Specific date (finds transit on that date)
- `--window-minutes 60` - Search window around transit (default: 60 minutes, i.e., ±30 min)
- `--max-days-back 30` - How many days to search if date not found (default: 30)
- `--dec-tolerance-deg 2.0` - Declination matching tolerance (default: 2.0°)

---

### 3. **Validate Files Before Converting** (Recommended First Step)

Check if your files are valid without actually converting:

```bash
# Validate HDF5 files in a time window
python -m dsa110_contimg.conversion.cli validate \
    --input-dir /data/incoming \
    --start-time "2025-10-30 10:00:00" \
    --end-time "2025-10-30 11:00:00"

# Validate a specific calibrator transit
python -m dsa110_contimg.conversion.cli validate \
    --input-dir /data/incoming \
    --validate-calibrator 0834+555 \
    --transit-date 2025-10-30
```

**What you get:**
- File structure validation (are files readable? do they have time arrays?)
- Missing file detection
- Calibrator transit validation (does transit exist? does data match declination?)
- Warnings about potential issues

**Use this when:** You want to check data availability before committing to a long conversion.

---

### 4. **Find Which Calibrators Have Data Available**

Discover which calibrator sources you can actually process:

```bash
python -m dsa110_contimg.conversion.cli find-calibrators \
    --input-dir /data/incoming \
    --catalog /path/to/catalog.csv \
    --json
```

**What you get:**
- List of calibrators with observation data
- Transit times for each calibrator
- File counts and declination matches
- Can output as JSON for scripting

**Use this when:** You want to see what calibrator data is available in your archive.

---

### 5. **Find Transit Without Converting** (Exploration Mode)

Just find and list the files for a transit without converting:

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --find-only
```

**What you get:**
- Transit time information
- List of all HDF5 files that would be converted
- Time window that would be used
- No MS files created

**Use this when:** You want to verify you have the right data before converting.

---

### 6. **Dry-Run Conversion** (Simulation Mode)

See what would be converted without actually doing it:

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --dry-run
```

**What you get:**
- List of groups that would be converted
- Validation of directories and permissions
- No files written

**Use this when:** Testing parameters or checking disk space before conversion.

---

### 7. **Skip Already-Converted Groups** (Incremental Mode)

Only convert groups that don't already have MS files:

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --skip-existing
```

**What you get:**
- Faster iteration during testing
- Resume capability if conversion was interrupted
- Avoids re-converting existing data

**Use this when:** Re-running conversions or testing incremental workflows.

---

### 8. **Resumable Conversions** (Checkpoint Mode)

Save progress and resume if conversion fails:

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --checkpoint-file /tmp/conversion_checkpoint.json
```

**What you get:**
- Checkpoint file saved after each successful group conversion
- Contains: completed groups, MS paths, timestamps, file lists
- Can manually resume from last checkpoint (future enhancement)

**Use this when:** Converting large time ranges that might fail partway through.

---

### 9. **Verify MS Quality After Conversion**

Check that your converted MS files are valid:

```bash
python -m dsa110_contimg.conversion.cli verify-ms \
    --ms /data/ms/2025-10-30T10:00:00.ms \
    --check-imaging-columns \
    --check-field-structure \
    --check-spw-structure
```

**What you get:**
- Validation that MS structure is correct
- Check for required columns (DATA, CORRECTED_DATA, MODEL_DATA, etc.)
- Field and SPW table verification
- Statistics (row counts, column counts)

**Use this when:** After conversion to verify the MS is ready for calibration/imaging.

---

### 10. **Quick Smoke Test** (Sanity Check)

Fast end-to-end test of the entire pipeline:

```bash
python -m dsa110_contimg.conversion.cli smoke-test \
    --output /tmp/smoke-test.ms \
    --cleanup
```

**What you get:**
- Generates minimal synthetic data (4 subbands, 1 minute)
- Converts to MS
- Validates result
- Completes in < 1 minute
- Cleans up temporary files

**Use this when:** After environment changes, code updates, or as a quick sanity check.

---

### 11. **Convert Single File or Directory** (Advanced)

Convert a single UVH5 file or loose collection of files:

```bash
python -m dsa110_contimg.conversion.cli single \
    --input /path/to/single_file.hdf5 \
    --output /path/to/output.ms
```

**What you get:**
- Single file converted directly
- Useful for testing or special cases
- Less optimized than batch conversion

**Use this when:** Working with individual files or test data.

---

### 12. **Create Test MS from Full MS** (Testing)

Make a smaller MS from a full MS for faster testing:

```bash
python -m dsa110_contimg.conversion.cli create-test-ms \
    --ms-in /data/ms/full.ms \
    --ms-out /data/ms/test.ms \
    --max-baselines 20 \
    --max-times 100
```

**What you get:**
- Smaller MS (fewer baselines, fewer time integrations)
- Preserves all spectral windows
- Prioritizes reference antenna baselines
- Much faster for testing calibration

**Use this when:** You need a small MS for quick calibration testing.

---

## Common Workflows

### Workflow 1: Processing a Calibrator Transit

```bash
# Step 1: Validate that data exists
python -m dsa110_contimg.conversion.cli validate \
    --input-dir /data/incoming \
    --validate-calibrator 0834+555 \
    --transit-date 2025-10-30

# Step 2: Find the files (optional, for verification)
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --find-only

# Step 3: Convert to MS
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30

# Step 4: Verify MS quality
python -m dsa110_contimg.conversion.cli verify-ms \
    --ms /data/ms/2025-10-30T13:34:54.ms \
    --check-imaging-columns
```

### Workflow 2: Processing a Time Window

```bash
# Step 1: Dry-run to see what would be converted
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --dry-run

# Step 2: Convert (with checkpoint for safety)
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --checkpoint-file /tmp/conversion_checkpoint.json \
    --skip-existing
```

### Workflow 3: Discovering Available Calibrators

```bash
# Find all calibrators with data
python -m dsa110_contimg.conversion.cli find-calibrators \
    --input-dir /data/incoming \
    --catalog /data/catalogs/vla_calibrators_parsed.csv \
    --json > available_calibrators.json

# Then process one of them
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30
```

---

## Performance Options

### Faster Conversion (For Testing)

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 10:05:00" \
    --writer pyuvdata \
    --max-workers 1
```

**Options:**
- `--writer pyuvdata` - Faster but only for ≤2 subbands (testing only)
- `--max-workers 1` - Single-threaded (slower but simpler)

### Production Conversion (Default)

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --writer parallel-subband \
    --max-workers 8 \
    --stage-to-tmpfs \
    --tmpfs-path /dev/shm
```

**Options:**
- `--writer parallel-subband` - Production writer for 16 subbands
- `--max-workers 8` - Parallel processing (adjust based on CPU)
- `--stage-to-tmpfs` - Use RAM for faster I/O (requires sufficient RAM)
- `--tmpfs-path /dev/shm` - RAM disk path (default)

---

## Progress and Verbosity

### Quiet Mode (For Scripts)

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --disable-progress \
    --log-level WARNING
```

### Verbose Mode (For Debugging)

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --verbose \
    --log-level DEBUG
```

---

## Understanding Outputs

### What Gets Created

For each complete 16-subband group, you get:
- One MS file named after the group timestamp: `YYYY-MM-DDTHH:MM:SS.ms`
- Located in the output directory you specified
- Contains all 16 subbands concatenated
- Ready for calibration

### MS Structure

Each MS contains:
- **DATA column**: Raw visibility data
- **CORRECTED_DATA column**: Empty initially, populated after calibration
- **MODEL_DATA column**: Optional, can be populated with source model
- **WEIGHT_SPECTRUM column**: Per-channel weights
- **FIELD table**: Pointing information
- **SPECTRAL_WINDOW table**: Frequency information
- **ANTENNA table**: Antenna positions and characteristics

---

## Troubleshooting

### Problem: "No groups found"

**Possible causes:**
- Time window doesn't contain data
- Files are missing subbands (need all 16)
- Files outside time window

**Solution:**
```bash
# Validate to see what files exist
python -m dsa110_contimg.conversion.cli validate \
    --input-dir /data/incoming \
    --start-time "2025-10-30 10:00:00" \
    --end-time "2025-10-30 11:00:00"
```

### Problem: "No transit found for calibrator"

**Possible causes:**
- Calibrator name incorrect
- No data on that date
- Declination mismatch (data pointing elsewhere)

**Solution:**
```bash
# Validate calibrator transit
python -m dsa110_contimg.conversion.cli validate \
    --input-dir /data/incoming \
    --validate-calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --dec-tolerance-deg 5.0  # Try wider tolerance
```

### Problem: MS conversion fails partway through

**Solution:**
```bash
# Resume using checkpoint
# (Checkpoint contains last successful group)
# Then re-run with --skip-existing to avoid re-converting
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    "2025-10-30 10:00:00" \
    "2025-10-30 11:00:00" \
    --skip-existing
```

### Problem: Want to see what would happen without converting

**Solution:**
```bash
# Use --find-only or --dry-run
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /data/ms \
    --calibrator 0834+555 \
    --find-only  # Lists files
    # OR
    --dry-run    # Simulates conversion
```

---

## Tips and Best Practices

1. **Always validate first** - Use `validate` command before converting large time ranges
2. **Use calibrator mode** - It automatically handles transit finding and declination matching
3. **Use --skip-existing** - When re-running, avoids redundant work
4. **Use checkpoints** - For long conversions, save progress
5. **Verify after conversion** - Use `verify-ms` to ensure MS is ready
6. **Use smoke-test** - Quick sanity check after environment changes
7. **Find calibrators first** - Use `find-calibrators` to discover available data

---

## Advanced Options

### Custom Writer Selection

```bash
--writer auto          # Auto-selects based on subband count (default)
--writer parallel-subband  # Production writer (16 subbands)
--writer pyuvdata      # Testing only (≤2 subbands)
```

### SPW Merging

```bash
--merge-spws  # Merge 16 SPWs into 1 SPW during conversion
```

**Note:** Generally better to merge CORRECTED_DATA after calibration, not during conversion.

### Scratch Directory

```bash
--scratch-dir /scratch/dsa110-contimg  # Use fast SSD for intermediate files
```

### Flux Model

```bash
--flux 10.5  # Write flux value to MODEL_DATA column (Jy)
```

---

## Summary: Your Options

As a user, you can:

✅ **Convert** data by time window or calibrator transit  
✅ **Validate** files before converting  
✅ **Find** which calibrators have data  
✅ **Explore** transits without converting  
✅ **Simulate** conversions with dry-run  
✅ **Resume** failed conversions with checkpoints  
✅ **Skip** already-converted groups  
✅ **Verify** MS quality after conversion  
✅ **Test** the pipeline with smoke-test  
✅ **Customize** writer, workers, staging options  
✅ **Monitor** progress with progress bars  
✅ **Control** verbosity and logging  

All through a single, unified CLI with consistent flags and clear error messages!


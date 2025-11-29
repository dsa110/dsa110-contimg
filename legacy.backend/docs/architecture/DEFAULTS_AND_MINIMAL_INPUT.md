# Pipeline Defaults: Minimal Input Behavior

## Overview

The DSA-110 imaging pipeline is designed to operate with **minimal user input**
through carefully chosen defaults. All critical pipeline components provide
sensible production-ready defaults that work for standard DSA-110 observations.

---

## Stage 1: Streaming HDF5 Conversion (No Defaults - Required)

### Command

```bash
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/
```

### Minimal Input Requirements

- `--input-dir` **(REQUIRED)** - Directory where HDF5 files arrive
- `--output-dir` **(REQUIRED)** - Directory where MS files are written

### Defaults Applied (No --enable flags = Conservative Mode)

| Parameter                | Default                      | Behavior                                        |
| ------------------------ | ---------------------------- | ----------------------------------------------- |
| `--queue-db`             | `state/ingest.sqlite3`       | Tracks registered HDF5 files                    |
| `--registry-db`          | `state/cal_registry.sqlite3` | Stores calibration table paths                  |
| `--scratch-dir`          | `/stage/dsa110-contimg`      | Intermediate staging directory                  |
| `--expected-subbands`    | `16`                         | Number of subbands per observation              |
| `--chunk-duration`       | `5.0` minutes                | Groups of ~5 min HDF5 files into one MS         |
| `--log-level`            | `INFO`                       | Standard logging output                         |
| `--poll-interval`        | `5.0` seconds                | Check for new files every 5 sec                 |
| `--worker-poll-interval` | `5.0` seconds                | Workers poll for work every 5 sec               |
| `--max-workers`          | `4`                          | 4 parallel conversion workers                   |
| `--use-subprocess`       | `False`                      | In-process conversion (faster for small groups) |
| `--monitoring`           | `False`                      | Don't emit monitoring metrics                   |
| `--monitor-interval`     | `60.0` seconds               | (Unused without --monitoring)                   |
| `--stage-to-tmpfs`       | `False`                      | Keep staging on main disk                       |
| `--tmpfs-path`           | `/dev/shm`                   | RAM disk if staging to tmpfs                    |

### **All --enable Flags Disabled by Default (Conservative Mode)**

```
--enable-calibration-solving       FALSE  [Conversion stage only]
--enable-group-imaging             FALSE  [Reserved for streaming_mosaic]
--enable-mosaic-creation           FALSE  [Reserved for streaming_mosaic]
--enable-auto-qa                   FALSE  [Reserved for streaming_mosaic]
--enable-auto-publish              FALSE  [Reserved for streaming_mosaic]
--enable-photometry                FALSE  [Reserved for streaming_mosaic]
```

**Rationale**: Conversion stage has one job: create MS files. All downstream
features (calibration, imaging, mosaicking, publishing) are handled by separate
processes (streaming_mosaic.py).

---

## Stage 2-9: Streaming Mosaic Orchestration

### Command (Minimal)

```bash
dsa110-contimg-streaming-mosaic
```

### Minimal Input Requirements

**NONE** - All parameters have defaults

### Defaults Applied

| Parameter             | Default                         | Behavior                                     |
| --------------------- | ------------------------------- | -------------------------------------------- |
| `--products-db`       | `state/products.sqlite3`        | Index of MS files and images                 |
| `--registry-db`       | `state/cal_registry.sqlite3`    | Calibration table registry                   |
| `--ms-dir`            | `/stage/dsa110-contimg/raw/ms`  | Where raw MS files live (from converter)     |
| `--images-dir`        | `/stage/dsa110-contimg/images`  | Output individual images                     |
| `--mosaic-dir`        | `/stage/dsa110-contimg/mosaics` | Output mosaics (staging)                     |
| `--no-sliding-window` | `False`                         | Use sliding window grouping (allows overlap) |
| `--loop`              | `False`                         | Process once and exit                        |
| `--sleep`             | `60.0` seconds                  | (Unused without --loop)                      |

### What Happens on Minimal Input

With just `dsa110-contimg-streaming-mosaic`, the pipeline:

1. **Checks for complete groups** (10 MS files)
   - Queries `products.sqlite3` for completed MS conversions
   - Looks for chronologically ordered groups
   - Uses sliding window: can start at any index, not just multiples of 10

2. **Applies calibration to group**
   - Queries `cal_registry.sqlite3` for valid calibration tables
   - If tables don't exist: solves bandpass and gain using 5th MS as calibrator
   - Applies BP, GP, 2G corrections to all 10 MS files
   - Status: `mosaic_groups.stage='calibrated'`

3. **Images the group**
   - Creates clean images for all 10 MS files
   - Default imaging parameters:
     - Image size: `1024 × 1024` pixels
     - Cell size: Auto-calculated (~3.5" for DSA-110)
     - Weighting: Briggs (`robust=0.0`)
     - Deconvolver: Hogbom
     - Iterations: 1000
   - Status: `mosaic_groups.stage='imaged'`

4. **Creates mosaic**
   - Combines 10 images using **mean stacking** (simple average)
   - No primary beam correction applied
   - Output: `/stage/dsa110-contimg/mosaics/mosaic_<group_id>_<timestamp>.fits`
   - Status: `mosaic_groups.status='completed'`

5. **Validates mosaic**
   - Tile consistency check: verifies tiles align and don't overlap
   - QA status set: `qa_status='passed'` (or `'warning'` if minor issues)
   - Validation status: `validation_status='validated'`

6. **Registers mosaic in data registry**
   - Stores in `data_registry` table
   - Status: `'staging'`
   - Auto-publish flag: `True`
   - Metadata: group_id, n_images, time_range, validation_issues

7. **Auto-publishes mosaic** (if QA passed)
   - Moves from `/stage/dsa110-contimg/mosaics/` to
     `/data/dsa110-contimg/products/mosaics/`
   - Updates `data_registry` status to `'published'`
   - Mosaic is now discoverable by external systems

### Continuous Daemon Mode

Add `--loop` to run continuously:

```bash
dsa110-contimg-streaming-mosaic --loop
```

**Default behavior**:

- Check for new groups every 60 seconds (`--sleep 60`)
- Process groups as they complete
- Run until interrupted (Ctrl+C)
- Automatically log errors and continue on next cycle

---

## Calibration Defaults

All from `utils/defaults.py`:

### Bandpass Calibration

| Parameter               | Default    | Meaning                                       |
| ----------------------- | ---------- | --------------------------------------------- |
| `CAL_BP_MINSNR`         | `3.0`      | Minimum signal-to-noise for BP solutions      |
| `CAL_BP_SOLINT`         | `"inf"`    | Solve over entire scan (no time segmentation) |
| `CAL_BP_SMOOTH_TYPE`    | `"none"`   | No smoothing applied                          |
| `CAL_BP_WINDOW`         | `3` fields | Include 3 fields around peak                  |
| `CAL_BP_MIN_PB`         | `None`     | No primary beam threshold                     |
| `CAL_SEARCH_RADIUS_DEG` | `1.0°`     | Search 1° radius for catalog matches          |

### Gain Calibration

| Parameter          | Default | Meaning                            |
| ------------------ | ------- | ---------------------------------- |
| `CAL_GAIN_MINSNR`  | `3.0`   | Minimum SNR for gain solutions     |
| `CAL_GAIN_SOLINT`  | `"inf"` | Solve over entire scan             |
| `CAL_GAIN_CALMODE` | `"ap"`  | Amplitude + phase (not phase-only) |

### K-Calibration (Delays)

| Parameter           | Default | Meaning                              |
| ------------------- | ------- | ------------------------------------ |
| `CAL_K_MINSNR`      | `5.0`   | Higher threshold for delay solutions |
| `CAL_K_COMBINE_SPW` | `False` | Solve each subband separately        |

### Flagging

| Parameter           | Default   | Meaning                              |
| ------------------- | --------- | ------------------------------------ |
| `CAL_FLAGGING_MODE` | `"zeros"` | Flag zero-value data points          |
| `CAL_FLAG_AUTOCORR` | `True`    | Flag autocorrelations before solving |

### Model Source

| Parameter                  | Default                | Meaning                            |
| -------------------------- | ---------------------- | ---------------------------------- |
| `CAL_MODEL_SOURCE`         | `"catalog"`            | Use catalog for model (not manual) |
| `CAL_MODEL_SETJY_STANDARD` | `"Perley-Butler 2017"` | Flux density standard              |

---

## Imaging Defaults

All from `utils/defaults.py`:

| Parameter         | Default       | Meaning                                            |
| ----------------- | ------------- | -------------------------------------------------- |
| `IMG_IMSIZE`      | `1024` pixels | Image size (square)                                |
| `IMG_CELL_ARCSEC` | `None` (auto) | Cell size auto-calculated from frequency           |
| `IMG_WEIGHTING`   | `"briggs"`    | Briggs weighting (balanced resolution/sensitivity) |
| `IMG_ROBUST`      | `0.0`         | Uniform weighting (natural + uniform)              |
| `IMG_NITER`       | `1000`        | Deconvolution iterations                           |
| `IMG_THRESHOLD`   | `None` (auto) | Stopping threshold auto-set                        |
| `IMG_DECONVOLVER` | `"hogbom"`    | Hogbom algorithm (best for point sources)          |

---

## Mosaic Combination Defaults

### Minimal Mosaic CLI

```bash
dsa110-contimg-mosaic plan --name my_mosaic
dsa110-contimg-mosaic build --name my_mosaic --output /data/my_mosaic.image
```

### Defaults for `plan`

| Parameter           | Default                  | Behavior                               |
| ------------------- | ------------------------ | -------------------------------------- |
| `--products-db`     | `state/products.sqlite3` | Source of image tiles                  |
| `--method`          | `"mean"`                 | Simple averaging (no weighting)        |
| `--since`           | `None`                   | Include all tiles from history         |
| `--until`           | `None`                   | Include all tiles up to now            |
| `--include-unpbcor` | `False`                  | Only use primary-beam corrected images |

### Defaults for `build`

| Parameter             | Default                  | Behavior                                  |
| --------------------- | ------------------------ | ----------------------------------------- |
| `--products-db`       | `state/products.sqlite3` | Where planned tiles stored                |
| `--ignore-validation` | `False`                  | Fail if validation issues found           |
| `--dry-run`           | `False`                  | Actually build mosaic (not just validate) |

---

## Database Defaults

### Database Location Hierarchy

Each database checks environment variables, then falls back to defaults:

| Database      | Env Variable           | Default                      | Purpose                 |
| ------------- | ---------------------- | ---------------------------- | ----------------------- |
| Products      | `PIPELINE_PRODUCTS_DB` | `state/products.sqlite3`     | MS & image index        |
| Cal Registry  | `CAL_REGISTRY_DB`      | `state/cal_registry.sqlite3` | Calibration table paths |
| Ingest Queue  | -                      | `state/ingest.sqlite3`       | HDF5 file tracking      |
| Data Registry | -                      | (API-managed)                | Published data registry |

### Database File Locations

If not specified, all database paths are **relative to current working
directory**. Best practice: run pipeline from project root.

---

## Service Port Defaults

From `config/ports.py`:

| Service            | Default Port | Env Variable                    | Range     |
| ------------------ | ------------ | ------------------------------- | --------- |
| Backend API        | `8000`       | `CONTIMG_API_PORT`              | 8000-8009 |
| Documentation      | `8001`       | `CONTIMG_DOCS_PORT`             | 8001      |
| Frontend Dev       | `5173`       | `CONTIMG_FRONTEND_DEV_PORT`     | 5173      |
| Dashboard          | `3210`       | `CONTIMG_DASHBOARD_PORT`        | 3210-3220 |
| Dashboard (Docker) | `3000`       | `CONTIMG_DASHBOARD_DOCKER_PORT` | 3000      |
| MCP HTTP           | `3111`       | `CONTIMG_MCP_HTTP_PORT`         | 3111      |
| MCP WebSocket      | `9009`       | (hardcoded)                     | 9009      |
| Redis              | `6379`       | `REDIS_PORT`                    | 6379      |

---

## Typical Minimal Production Setup

### Start converter (one-time)

```bash
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/
```

### Start mosaic daemon (one-time)

```bash
dsa110-contimg-streaming-mosaic --loop
```

**That's it.** The pipeline will:

1. Poll for HDF5 files every 5 seconds
2. Convert to MS (5-minute chunks)
3. Form 10-MS groups
4. Solve calibration
5. Image each MS
6. Create mosaics
7. Validate and publish automatically

No additional configuration needed.

---

## Environment Override Examples

### Use faster gain calibration

```bash
export CONTIMG_CAL_GAIN_MINSNR=2.0
dsa110-contimg-streaming-mosaic --loop
```

### Use 2048-pixel images

```bash
export IMG_IMSIZE=2048
dsa110-contimg-streaming-mosaic --loop
```

### Run with 8 conversion workers

```bash
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/ \
  --max-workers 8
```

### Run mosaic daemon with 30-second polling

```bash
dsa110-contimg-streaming-mosaic --loop --sleep 30
```

---

## Summary: What the Pipeline Does by Default

**With zero optional flags**, the pipeline:

1. :check_mark: Continuously polls for HDF5 files
2. :check_mark: Converts HDF5 to MS format (5-min chunks, 16 subbands)
3. :check_mark: Groups MS files chronologically (10 per group, sliding window)
4. :check_mark: Solves bandpass & gain calibration (once per day/hour as appropriate)
5. :check_mark: Applies calibration corrections to all MS files
6. :check_mark: Creates clean images (1024×1024, Briggs weighting)
7. :check_mark: Stacks images into mosaics (simple mean averaging)
8. :check_mark: Validates mosaic quality
9. :check_mark: Registers mosaic in data registry
10. :check_mark: Auto-publishes to `/data/dsa110-contimg/products/mosaics/`

**No user intervention required** between HDF5 arrival and published mosaic.

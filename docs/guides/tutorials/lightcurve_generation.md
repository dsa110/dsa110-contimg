# Lightcurve Generation Tutorial

**Purpose:** This tutorial guides you through generating lightcurves from
DSA-110 observations using the continuum imaging pipeline. It covers both manual
step-by-step processing and automated streaming workflows.

**Prerequisites:**

- Access to the DSA-110 dashboard at `http://localhost:5173` (or production URL)
- Raw UVH5 data in `/data/incoming/`
- The `casa6` conda environment activated for CLI commands

**Last Updated:** November 26, 2025 (CLI commands corrected to match
implementation)

---

## Overview

The DSA-110 lightcurve generation pipeline follows this workflow:

```
UVH5 Files → Measurement Sets → Calibration → Imaging → Mosaics → Photometry → Lightcurves
```

This tutorial is divided into two parts:

1. **Part 1: Manual Workflow** - Step-by-step processing through the dashboard
2. **Part 2: Streaming Workflow** - Automated real-time processing

---

## Part 1: Manual Workflow

This section walks you through manually processing observations to generate
lightcurves, ideal for reprocessing archival data or understanding the pipeline.

### Step 1: Convert UVH5 to Measurement Sets

The first step converts raw correlator output (UVH5/HDF5 files) into CASA
Measurement Sets.

#### Via Dashboard

1. Navigate to **Pipeline Control** in the left sidebar
2. Click the **Conversion** tab
3. In the **Time Range Conversion** section:
   - Set **Start Time**: e.g., `2025-10-30 10:00:00`
   - Set **End Time**: e.g., `2025-10-30 11:00:00`
   - Set **Input Directory**: `/data/incoming/`
   - Set **Output Directory**: `/stage/dsa110-contimg/ms/`
4. Click **Start Conversion**
5. Monitor progress in the **Jobs** panel below

> **Note:** Each observation consists of 16 subbands that are automatically
> grouped by timestamp (within 60-second tolerance) and combined into a single
> MS.

#### Via CLI (Alternative)

```bash
conda activate casa6
python -m dsa110_contimg.conversion.cli groups \
    --input-dir /data/incoming/ \
    --output-dir /stage/dsa110-contimg/ms/ \
    --start-time "2025-10-30T10:00:00" \
    --end-time "2025-10-30T11:00:00"
```

> **Note:** The `groups` command discovers complete 16-subband groups within the
> time window and converts each group to a single Measurement Set.

### Step 2: Calibrate the Measurement Sets

Calibration corrects for instrumental and atmospheric effects.

#### Via Dashboard

1. Navigate to **Calibration** in the left sidebar
2. The wizard has three steps: **Configure → Run → Review**

**Step 2a: Configure**

3. Select the MS to calibrate from the dropdown (or browse to path)
4. Choose calibration mode:
   - **Bandpass Only**: For observations with strong calibrators
   - **Full Calibration**: Bandpass + Gain + Phase
5. Set the **Reference Antenna** (default: auto-select)
6. Click **Next**

**Step 2b: Run**

7. Review the configuration summary
8. Click **Start Calibration**
9. Monitor the progress bar and log output
10. Wait for "Calibration Complete" message

**Step 2c: Review**

11. Examine the calibration plots:
    - Bandpass amplitude vs. frequency
    - Phase vs. time
    - Antenna-based gains
12. Check the quality metrics (should show green checkmarks)
13. Click **Apply Calibration** to write corrected data

### Step 3: Generate Images

Create continuum images from the calibrated Measurement Sets.

#### Via Dashboard

1. Navigate to **Pipeline Control** → **Imaging** tab
2. Select the calibrated MS from the list
3. Configure imaging parameters:
   - **Image Size**: 4096 (pixels, default)
   - **Cell Size**: 3.0 (arcsec, default)
   - **Backend**: WSClean (recommended) or tclean
   - **Robust**: 0.0 (Briggs weighting)
4. Click **Create Image**
5. Monitor progress in the job panel

The pipeline generates:

- `*-image.fits` - Primary beam corrected image
- `*-residual.fits` - Residual image
- `*-psf.fits` - Point spread function

#### View Images

1. Navigate to **Sky View** in the left sidebar
2. Click **Load Image** and select the FITS file
3. Use the JS9 viewer controls to:
   - Adjust color scale (click the colorbar)
   - Zoom/pan (mouse wheel, drag)
   - Show catalog overlays (NVSS, FIRST)

### Step 4: Create Mosaics

Combine multiple images into a mosaic for deeper sensitivity.

#### Via Dashboard (Absurd Workflow)

1. Navigate to **Absurd** in the left sidebar
2. Click the **Workflow Builder** tab
3. Create a new workflow:
   - **Name**: `mosaic_2025-10-30`
   - **Add Task**: Select `create-mosaic`
   - **Parameters**:
     ```json
     {
       "image_paths": [
         "/stage/dsa110-contimg/images/2025-10-30T10*.fits",
         "/stage/dsa110-contimg/images/2025-10-30T11*.fits"
       ],
       "output_path": "/stage/dsa110-contimg/mosaics/2025-10-30_mosaic.fits",
       "method": "linear"
     }
     ```
4. Click **Submit Workflow**
5. Monitor progress in the **Task Dashboard** tab

#### Via CLI (Alternative)

Mosaic creation is a two-step process: **plan** then **build**.

```bash
conda activate casa6

# Step 1: Plan the mosaic (selects tiles from products DB)
python -m dsa110_contimg.mosaic.cli plan \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --name "mosaic_2025-10-30" \
    --since $(date -d "2025-10-30 00:00:00" +%s) \
    --until $(date -d "2025-10-30 23:59:59" +%s) \
    --method pbweighted

# Step 2: Build the mosaic from the plan
python -m dsa110_contimg.mosaic.cli build \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --name "mosaic_2025-10-30" \
    --output /stage/dsa110-contimg/mosaics/2025-10-30_mosaic
```

> **Tip:** Use `--dry-run` with `build` to validate the plan without creating
> the mosaic. Method options: `mean`, `weighted`, `pbweighted` (recommended).

#### View Mosaics

1. Navigate to **Mosaic Gallery** in the left sidebar
2. Find your mosaic in the list (sorted by date)
3. Click on the mosaic to open **Mosaic View**
4. The JS9 viewer displays the mosaic with overlay options

### Step 5: Perform Forced Photometry

Measure source fluxes at specific positions across all images.

#### Via Dashboard (Single Source)

1. Navigate to **Sky View**
2. Load your mosaic or image
3. Click the **Photometry** tool in the toolbar (aperture icon)
4. Click on a source position in the image
5. The **PhotometryPlugin** panel shows:
   - RA/Dec coordinates
   - Peak flux (Jy/beam)
   - Integrated flux (Jy)
   - Local noise estimate
   - Signal-to-noise ratio
6. Click **Save Measurement** to store in the database

#### Via Dashboard (Multiple Sources)

For measuring sources across images:

1. Navigate to **Sky View**
2. Load an image and use the **PhotometryPlugin** (aperture icon)
3. Click on each source position to measure flux
4. Each measurement is automatically saved to the database

> **Note:** Batch photometry via CSV upload is planned for a future release. For
> now, use the CLI commands below for batch processing. See
> [Issue #59](https://github.com/dsa110/dsa110-contimg/issues/59) for progress.

#### Via CLI (Recommended for Large Batches)

**Option 1: Measure specific coordinates**

```bash
conda activate casa6
# Measure multiple positions on a single image
python -m dsa110_contimg.photometry.cli peak-many \
    --fits /stage/dsa110-contimg/images/2025-10-30T10_image.fits \
    --coords "123.456,45.678; 124.567,46.789; 125.678,47.890"
```

**Option 2: NVSS catalog sources in field of view**

```bash
# Measure all NVSS sources brighter than 10 mJy within the image
python -m dsa110_contimg.photometry.cli nvss \
    --fits /stage/dsa110-contimg/images/2025-10-30T10_image.fits \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --min-mjy 10.0
```

**Option 3: Single source measurement**

```bash
# Precise measurement at one position with Aegean fitting
python -m dsa110_contimg.photometry.cli peak \
    --fits /stage/dsa110-contimg/images/2025-10-30T10_image.fits \
    --ra 123.456 --dec 45.678 \
    --use-aegean
```

> **Note:** Results are stored in the `photometry` table of `products.sqlite3`
> when using `--products-db`. Use the NVSS command for systematic flux
> measurements across multiple epochs.

### Step 6: View Lightcurves

Once photometry measurements are stored, view lightcurves in the dashboard.

#### Via Dashboard

1. Navigate to **Source Monitoring** in the left sidebar
2. Use the search/filter controls:
   - Search by name or coordinates
   - Filter by variability metrics (η, V-index)
   - Sort by SNR, flux, or detection count
3. Click on a source row to open **Source Detail**

The **Source Detail** page shows:

- **Lightcurve Chart**: Interactive time-series plot
  - Flux vs. time with error bars
  - Zoom/pan controls
  - Export as CSV or PNG
- **Variability Metrics**:
  - η (eta): Variability index
  - V: Fractional variability
  - χ²: Reduced chi-squared
- **Postage Stamps**: Cutout images at each epoch
- **External Crossmatch**: Links to SIMBAD, NED, Gaia

#### Interpret Variability Metrics

| Metric   | Threshold     | Interpretation                       |
| -------- | ------------- | ------------------------------------ |
| η > 2.0  | Variable      | Source shows significant variability |
| V > 0.1  | 10% variation | Fractional flux change               |
| χ² > 3.0 | Non-constant  | Rejects constant source hypothesis   |

---

## Part 2: Streaming Workflow

The streaming workflow automatically processes new observations in real-time.

### Architecture Overview

```
/data/incoming/          Streaming           /stage/dsa110-contimg/
    │                    Converter                    │
    ▼                        │                        ▼
 UVH5 files ──────────────►  │  ──────────────► MS files
                             │                        │
                             │                        ▼
                     Absurd Workers ◄────────── Calibration
                             │                        │
                             │                        ▼
                     Task Queue ──────────────► Imaging
                             │                        │
                             │                        ▼
                     Products DB ◄────────── Photometry
                             │                        │
                             │                        ▼
                     Dashboard ◄────────── Lightcurves
```

### Step 1: Start the Streaming Converter

#### Via Dashboard

1. Navigate to **Pipeline Control** in the left sidebar
2. Find the **Streaming Service** panel
3. Check the current status (Running/Stopped)
4. If stopped, click **Start Service**
5. Verify the service shows:
   - Status: ✅ Running
   - Health: ✅ Healthy
   - Queue: Processing count increasing

#### Via CLI (Alternative)

```bash
conda activate casa6
sudo systemctl start contimg-stream.service
sudo systemctl status contimg-stream.service
```

### Step 2: Configure Streaming Settings

#### Via Dashboard

1. In **Pipeline Control** → **Streaming Service** panel
2. Click **Configure**
3. Review/modify settings:
   - **Input Directory**: `/data/incoming/`
   - **Output Directory**: `/stage/dsa110-contimg/ms/`
   - **Poll Interval**: 30 seconds
   - **Subband Timeout**: 120 seconds (wait for all 16 subbands)
   - **Auto-Calibrate**: ✅ Enabled
   - **Auto-Image**: ✅ Enabled
4. Click **Save Configuration**

### Step 3: Set Up Automated Workflows

Configure Absurd to automatically process new data.

#### Via Dashboard

1. Navigate to **Absurd** → **Schedules** tab
2. Click **Create Schedule**
3. Configure the workflow template:

**Full Pipeline Schedule:**

```yaml
name: streaming_pipeline
trigger: new_ms # Triggered when new MS appears
tasks:
  - name: calibrate
    type: solve-calibration
    params:
      mode: bandpass
    timeout: 600

  - name: image
    type: create-image
    depends_on: [calibrate]
    params:
      backend: wsclean
      imsize: 4096
    timeout: 900

  - name: photometry
    type: run-photometry
    depends_on: [image]
    params:
      source_catalog: /data/dsa110-contimg/state/catalogs/monitoring_sources.csv
      store_db: true
    timeout: 300
```

4. Click **Enable Schedule**

### Step 4: Monitor Pipeline Health

#### Via Dashboard

1. Navigate to **System Health** for overall status
2. Key panels to monitor:

**Queue Statistics (Pipeline Control)**

- Pending: Files waiting to process
- Processing: Currently being converted
- Completed: Successfully processed
- Failed: Check Dead Letter Queue

**Worker Status (Absurd → Workers)**

- Active workers count
- Tasks per worker
- CPU/Memory usage

**Real-time Metrics (Absurd → Metrics)**

- Throughput: Files/hour
- Latency: Time per file
- Error rate

### Step 5: Handle Failures

#### Dead Letter Queue

1. Navigate to **Pipeline Control** → **DLQ** tab
2. Review failed items:
   - Click on an item to see error details
   - Check logs for root cause
3. Actions:
   - **Retry**: Attempt processing again
   - **Skip**: Mark as permanently failed
   - **Requeue**: Send back to main queue

#### Circuit Breaker

If errors exceed threshold, the circuit breaker trips:

1. Navigate to **Pipeline Control** → **Circuit Breaker**
2. View current state (Closed/Open/Half-Open)
3. If Open:
   - Check error logs
   - Fix underlying issue
   - Click **Reset Circuit Breaker**

### Step 6: Access Streaming Lightcurves

As the pipeline processes new observations, lightcurves update automatically.

#### Via Dashboard

1. Navigate to **Source Monitoring**
2. The table updates in real-time (WebSocket connection)
3. Sort by **Last Updated** to see recent detections
4. Click on a source to view the updating lightcurve

#### Real-time Alerts

For transient detection:

1. Navigate to **Transients** (if enabled)
2. View candidate alerts triggered by:
   - Rapid flux increase (> 3σ)
   - New source detection
   - Variability threshold exceeded

---

## Advanced Topics

### Custom Source Lists for Monitoring

To monitor specific sources:

1. Create a CSV file with target coordinates:

```csv
name,ra,dec,priority
3C286,202.784,30.509,high
Cygnus_A,299.868,40.734,high
My_Target,180.0,45.0,normal
```

2. Store this file in the catalogs directory:

```bash
cp sources.csv /data/dsa110-contimg/state/catalogs/monitoring_sources.csv
```

3. Run photometry on each image using the NVSS command (which stores results in
   the products database):

```bash
# For each image, measure sources at your target positions
for img in /stage/dsa110-contimg/images/2025-10-30T*.fits; do
    python -m dsa110_contimg.photometry.cli nvss \
        --fits "$img" \
        --products-db /data/dsa110-contimg/state/products.sqlite3 \
        --min-mjy 5.0
done
```

4. View results in **Source Monitoring** page or query the database directly.

> **Note:** Source monitoring registration via API is planned for a future
> release. See [Issue #55](https://github.com/dsa110/dsa110-contimg/issues/55).

### Photometry Normalization

To correct for systematic flux variations:

```bash
# Via API
curl -X POST http://localhost:8000/api/photometry/normalize \
    -H "Content-Type: application/json" \
    -d '{
        "source_id": "My_Target",
        "reference_sources": ["3C286", "3C48"],
        "time_range": ["2025-10-01", "2025-10-31"]
    }'
```

### Exporting Lightcurve Data

From **Source Detail** page:

1. Click **Export** dropdown
2. Choose format:
   - **CSV**: Time, flux, error columns
   - **JSON**: Full metadata
   - **VOTable**: Virtual Observatory format
3. Download file

Via SQL (for programmatic access):

```bash
# Export photometry for a specific source
sqlite3 -header -csv /data/dsa110-contimg/state/products.sqlite3 \
    "SELECT image_path, ra_deg, dec_deg, peak_jyb, peak_err_jyb, measured_at
     FROM photometry
     WHERE source_id = 'My_Target'
     ORDER BY measured_at" \
    > /path/to/lightcurve.csv
```

Via API:

```bash
curl "http://localhost:8000/api/sources/My_Target/lightcurve" \
    -H "Accept: application/json" \
    -o lightcurve.json
```

> **Note:** A dedicated `export` CLI command is planned for a future release.
> See [Issue #59](https://github.com/dsa110/dsa110-contimg/issues/59).

---

## Troubleshooting

### Common Issues

| Problem                | Cause                  | Solution                                          |
| ---------------------- | ---------------------- | ------------------------------------------------- |
| No MS created          | Incomplete subbands    | Wait for all 16 subbands or check input directory |
| Calibration fails      | No calibrator in field | Use different time range with calibrator transit  |
| Empty lightcurve       | Source not in catalog  | Register source via CLI or add to monitoring list |
| Dashboard not updating | WebSocket disconnected | Refresh page or check API health                  |
| Streaming stalled      | Disk full              | Run `cleanup_disk_space.sh` or expand storage     |

### Checking Logs

```bash
# Streaming converter logs
tail -f /data/dsa110-contimg/state/logs/streaming_converter.log

# Absurd worker logs
tail -f /data/dsa110-contimg/state/logs/absurd_worker.log

# API logs
tail -f /data/dsa110-contimg/state/logs/api.log
```

### Database Inspection

```bash
# Check photometry measurements
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
    "SELECT source_id, image_path, peak_jyb, peak_err_jyb, measured_at
     FROM photometry
     WHERE source_id = 'My_Target'
     ORDER BY measured_at DESC
     LIMIT 10;"

# List all measured sources with detection counts
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
    "SELECT source_id, COUNT(*) as n_detections,
            AVG(peak_jyb) as mean_flux_jy,
            (MAX(peak_jyb) - MIN(peak_jyb)) / AVG(peak_jyb) as frac_var
     FROM photometry
     WHERE source_id IS NOT NULL
     GROUP BY source_id
     HAVING n_detections > 3
     ORDER BY frac_var DESC;"
```

> **Note:** Variability metrics (η, V-index, χ²) are computed dynamically by the
> API. Dedicated database columns for these metrics are planned. See
> [Issue #55](https://github.com/dsa110/dsa110-contimg/issues/55).

---

## Summary

| Step        | Manual (Part 1)               | Streaming (Part 2)              |
| ----------- | ----------------------------- | ------------------------------- |
| Conversion  | Pipeline Control → Conversion | Automatic via Streaming Service |
| Calibration | Calibration Page wizard       | Automatic via Absurd Schedule   |
| Imaging     | Pipeline Control → Imaging    | Automatic via Absurd Schedule   |
| Mosaics     | Absurd Workflow Builder       | Scheduled or on-demand          |
| Photometry  | Sky View PhotometryPlugin     | Automatic via Absurd Schedule   |
| Lightcurves | Source Detail page            | Real-time updates               |

The dashboard provides comprehensive monitoring and visualization, while the
Absurd workflow system handles automation. For large-scale reprocessing, CLI
tools offer additional flexibility and batch processing capabilities.

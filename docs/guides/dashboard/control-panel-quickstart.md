# Control Panel Quick Start Guide

> **Note:** For the main dashboard quick start, see
> [dashboard-quickstart.md](dashboard-quickstart.md). This guide focuses
> specifically on the Control Panel for calibration and imaging operations.

## Prerequisites

- Backend running: FastAPI server on port 8000
- Frontend running: Vite dev server on port 5173
- At least one MS in `ms_index` table (or in `/stage/dsa110-contimg/ms/`)
- CASA environment configured (`casa6` conda environment)

## Starting the Services

### Terminal 1: Backend

```bash
cd /data/dsa110-contimg
conda activate casa6
export PYTHONPATH=/data/dsa110-contimg/src
export PIPELINE_PRODUCTS_DB=state/db/products.sqlite3

# Start FastAPI server
uvicorn dsa110_contimg.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:

```text
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2: Frontend

```bash
cd /data/dsa110-contimg/frontend
npm run dev
```

Expected output:

```text
  VITE v5.x.x  ready in xxx ms

  :heavy_round-tipped_rightwards_arrow:  Local:   http://localhost:3000/
  :heavy_round-tipped_rightwards_arrow:  Network: http://192.168.x.x:3000/
```

## Accessing the Control Panel

1. Open browser to `http://localhost:3000`
2. Click "Control" in the navigation bar
3. You should see:
   - Left side: MS picker and operation tabs
   - Right side: Log viewer and job table

## Example Workflow: Full Calibration & Imaging

### Step 1: Calibrate a Calibrator MS

1. **Select MS**: Choose a calibrator MS from dropdown

   - Example:
     `/stage/dsa110-contimg/ms/range_2025-10-13_13_14/2025-10-13T13:28:03.ms`

2. **Go to "Calibrate" tab**

3. **Set parameters**:

   - Field ID: `0` (first field, usually calibrator)
   - Reference Antenna: `103` (or another stable antenna)

4. **Click "Run Calibration"**

5. **Watch logs stream**:

   ```
   Starting calibration...
   Solving K (delay) calibration...
   K-solve complete: /scratch/.../2025-10-13T13:28:03.kcal
   Solving BP (bandpass) calibration...
   BP-solve complete: /scratch/.../2025-10-13T13:28:03.bpcal
   Solving G (gain) calibration...
   G-solve complete: /scratch/.../2025-10-13T13:28:03.gpcal
   [Job done]
   ```

6. **Note the artifact paths** (caltable locations) from logs

### Step 2: Apply Calibration to Target MS

1. **Select target MS**: Choose a science target MS

2. **Go to "Apply" tab**

3. **Enter gaintable paths** (copy from previous job artifacts):

   ```
   /stage/dsa110-contimg/ms/range_2025-10-13_13_14/2025-10-13T13:28:03.kcal,
   /stage/dsa110-contimg/ms/range_2025-10-13_13_14/2025-10-13T13:28:03.bpcal,
   /stage/dsa110-contimg/ms/range_2025-10-13_13_14/2025-10-13T13:28:03.gpcal
   ```

4. **Click "Apply Calibration"**

5. **Watch logs**:
   ```
   Clearing calibration...
   Applying calibration tables: ['.kcal', '.bpcal', '.gpcal']
   Apply complete
   [Job done]
   ```

### Step 3: Image the Calibrated MS

1. **Select same target MS** (now has CORRECTED_DATA)

2. **Go to "Image" tab**

3. **Set parameters**:

   - Gridder: `wproject`
   - W-Projection Planes: `-1` (auto)
   - Data Column: `corrected`

4. **Click "Run Imaging"**

5. **Watch logs**:

   ```
   Imaging /scratch/.../target.ms -> /scratch/images/target.img
   Auto-detecting cell size...
   Running tclean with wprojplanes=-1...
   tclean complete
   Registering VP table...
   Exporting FITS...
   [Job done]
   ```

6. **Check artifacts**:
   - `.image` - cleaned image
   - `.image.pbcor` - primary beam corrected
   - `.residual` - residual map
   - `.psf` - point spread function
   - `.pb` - primary beam

## Monitoring Jobs

### Job Table (bottom right)

- **ID**: Unique job identifier
- **Type**: calibrate, apply, or image
- **Status**:
  - :blue_circle: pending - waiting to start
  - :green_circle: running - in progress
  - :check: done - completed successfully
  - :cross: failed - error occurred
- **MS**: Basename of Measurement Set

**Click any row** to load that job's logs in the viewer.

### Live Log Viewer (top right)

- Shows real-time output from selected job
- Auto-scrolls to bottom as new lines arrive
- Displays job ID in header
- Shows status chip and artifact count when complete

## Tips & Tricks

### Finding Calibrator MSs

Calibrators typically have:

- Known source names (3C48, 3C286, etc.)
- Higher flux (look for `has_calibrator=true` in queue)
- Field names containing calibrator IDs

### Discovering Existing Caltables

Check the MS directory:

```bash
ls /stage/dsa110-contimg/ms/range_*/2025-*/*cal
```

### Checking Job Status from CLI

```bash
sqlite3 state/db/products.sqlite3 \
  "SELECT id, type, status, datetime(created_at, 'unixepoch')
   FROM jobs
   ORDER BY id DESC
   LIMIT 5;"
```

### Viewing Full Logs

```bash
sqlite3 state/db/products.sqlite3 \
  "SELECT logs FROM jobs WHERE id=<JOB_ID>;" | less
```

### Clearing Failed Jobs

```bash
sqlite3 state/db/products.sqlite3 \
  "DELETE FROM jobs WHERE status='failed';"
```

## Common Issues

### "No MS found in dropdown"

**Solution**:

1. Check that backend is connected to correct database
2. Verify `ms_index` table has entries:
   ```bash
   sqlite3 state/db/products.sqlite3 "SELECT COUNT(*) FROM ms_index;"
   ```
3. If empty, run conversion pipeline to populate MS entries

### "Job stuck in pending"

**Solution**:

1. Check backend terminal for errors
2. Verify `casa6` conda environment is available
3. Ensure `PYTHONPATH` is set correctly
4. Restart FastAPI server

### "Logs not streaming"

**Solution**:

1. Open browser DevTools :arrow_right: Network tab
2. Look for `/api/jobs/id/{job_id}/logs` with type `eventsource`
3. If connection fails, check CORS settings
4. Verify job ID is valid

### "Apply fails: gaintables not found"

**Solution**:

1. Verify gaintable paths are absolute (not relative)
2. Check paths exist: `ls <path_to_caltable>`
3. Ensure no extra spaces in comma-separated list
4. Copy paths exactly from calibrate job artifacts

### "Image produces blank output"

**Solution**:

1. Verify CORRECTED_DATA exists:
   ```bash
   conda run -n casa6 python -c "
   from casacore.tables import table
   t = table('/path/to/ms')
   print('CORRECTED_DATA' in t.colnames())
   t.close()
   "
   ```
2. If False, run apply step first
3. Check that calibration was successful (logs show no errors)

## Performance Expectations

- **Calibrate**: 2-5 minutes (depends on MS size, solution intervals)
- **Apply**: <1 minute (mostly I/O, clearcal + applycal)
- **Image**: 5-15 minutes (depends on imsize, niter, wprojplanes)

## Advanced: Parameter Reference

### Calibrate Parameters

- `field`: Field ID or name (0-indexed integer or string)
- `refant`: Reference antenna (comma-separated list, e.g., "103,100,104")

### Apply Parameters

- `gaintables`: Comma-separated list of absolute paths to `.kcal`, `.bpcal`,
  `.gpcal` files

### Image Parameters

- `gridder`:
  - `wproject` - w-term correction (recommended)
  - `standard` - simple FFT (fast, no w-correction)
  - `mosaic` - mosaic mode (for multi-pointing)
- `wprojplanes`:
  - `-1` - auto-calculate
  - `0` - disable w-projection
  - `>0` - specific number of planes (more = slower but more accurate)
- `datacolumn`:
  - `corrected` - use CORRECTED_DATA (default, requires apply)
  - `data` - use DATA (raw visibilities)

## Next Steps

After imaging completes:

1. **View images**: Use CASA viewer or DS9
   ```bash
   casaviewer /scratch/images/target.img.image
   ```
2. **Run QA**: Check noise, beam, source extraction
3. **Export**: FITS files in same directory as `.image`
4. **Photometry**: Run forced photometry on known sources

---

**Questions?** Check `CONTROL_PANEL_README.md` for detailed architecture docs.

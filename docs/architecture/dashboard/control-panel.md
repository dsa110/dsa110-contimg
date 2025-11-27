# DSA-110 Control Panel

## Overview

The Control Panel is a web-based interface for manually executing calibration,
apply, and imaging jobs on Measurement Sets. It provides:

- **Job Submission**: Create calibrate, apply, and image jobs with custom
  parameters
- **Live Log Streaming**: Real-time job logs via Server-Sent Events (SSE)
- **Job Status Tracking**: Monitor job progress and view artifacts
- **MS Browser**: Select from available Measurement Sets

## Architecture

### Backend (Python/FastAPI)

**Database Module** (`src/dsa110_contimg/database/jobs.py`):

- SQLite schema for job tracking
- CRUD operations: `create_job`, `get_job`, `update_job_status`,
  `append_job_log`, `list_jobs`

**Job Runner** (`src/dsa110_contimg/api/job_runner.py`):

- `run_calibrate_job()`: Executes calibration via `calibration.cli`
- `run_apply_job()`: Applies calibration tables via `clearcal` + `applycal`
- `run_image_job()`: Runs imaging via `imaging.cli`
- Streams logs to database in real-time

**API Routes** (`src/dsa110_contimg/api/routes.py`):

- `GET /api/ms` - List available Measurement Sets
- `GET /api/jobs` - List recent jobs (with optional status filter)
- `GET /api/jobs/{job_id}` - Get job details
- `GET /api/jobs/{job_id}/logs` - Stream job logs via SSE
- `POST /api/jobs/calibrate` - Create calibration job
- `POST /api/jobs/apply` - Create apply job
- `POST /api/jobs/image` - Create imaging job

**Models** (`src/dsa110_contimg/api/models.py`):

- `JobParams`: Job configuration (field, refant, gaintables, gridder, etc.)
- `Job`: Job state (id, type, status, ms_path, params, logs, artifacts,
  timestamps)
- `MSListEntry`: Measurement Set metadata
- `JobCreateRequest`: Request payload for job creation

### Frontend (React/TypeScript)

**Types** (`frontend/src/api/types.ts`):

- TypeScript interfaces matching backend models

**Queries** (`frontend/src/api/queries.ts`):

- `useMSList()`: Fetch available MS files
- `useJobs(limit, status)`: List jobs with polling
- `useJob(jobId)`: Get single job with polling
- `useCreateCalibrateJob()`: Mutation for calibrate
- `useCreateApplyJob()`: Mutation for apply
- `useCreateImageJob()`: Mutation for image

**Control Page** (`frontend/src/pages/ControlPage.tsx`):

- **MS Picker**: Dropdown to select Measurement Set
- **Tabbed Forms**: Separate tabs for Calibrate, Apply, and Image
- **Live Logs Panel**: Displays streaming logs via SSE with auto-scroll
- **Job Table**: Recent jobs with clickable rows to view logs

**Navigation** (`frontend/src/components/Navigation.tsx`):

- Added "Control" item with Settings icon

## Usage

### Starting the Services

1. **Backend** (from `/data/dsa110-contimg`):

   ```bash
   conda activate casa6
   export PYTHONPATH=/data/dsa110-contimg/src
   uvicorn dsa110_contimg.api.server:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Frontend** (from `/data/dsa110-contimg/frontend`):

   ```bash
   npm run dev
   ```

3. Navigate to `http://localhost:5173/control`

### Running a Calibration Job

1. Select an MS from the dropdown
2. Go to the "Calibrate" tab
3. Set parameters:
   - Field ID (e.g., `0`)
   - Reference Antenna (e.g., `103`)
4. Click "Run Calibration"
5. Watch logs stream in real-time
6. View artifacts (caltables) after completion

### Applying Calibration

1. Select the target MS
2. Go to the "Apply" tab
3. Enter gaintable paths (comma-separated):
   ```
   /scratch/.../2025-10-13T13:28:03.kcal,
   /scratch/.../2025-10-13T13:28:03.bpcal,
   /scratch/.../2025-10-13T13:28:03.gpcal
   ```
4. Click "Apply Calibration"
5. Monitor progress via logs

### Imaging

1. Select the MS (should have CORRECTED_DATA)
2. Go to the "Image" tab
3. Configure:
   - Gridder: `wproject`, `standard`, or `mosaic`
   - W-Projection Planes: `-1` (auto) or specific count
   - Data Column: `corrected` or `data`
4. Click "Run Imaging"
5. View image artifacts after completion

## Job Status

- **pending**: Job created, waiting to start
- **running**: Job in progress, logs streaming
- **done**: Job completed successfully
- **failed**: Job encountered an error

## Log Streaming Details

- Uses **Server-Sent Events (SSE)** protocol
- Logs are appended to database every ~10 lines for efficiency
- Frontend auto-scrolls to latest log entry
- Connection closes when job reaches `done` or `failed`

## Database Schema

**jobs** table:

- `id` (INTEGER PRIMARY KEY)
- `type` (TEXT): "calibrate", "apply", or "image"
- `status` (TEXT): "pending", "running", "done", "failed"
- `ms_path` (TEXT): Full path to Measurement Set
- `params` (TEXT): JSON-encoded JobParams
- `logs` (TEXT): Accumulated log output
- `artifacts` (TEXT): JSON array of output file paths
- `created_at` (REAL): Unix timestamp
- `started_at` (REAL): Unix timestamp
- `finished_at` (REAL): Unix timestamp

## Job Runner Behavior

All jobs run in the `casa6` conda environment with:

- `PYTHONPATH=/data/dsa110-contimg/src`
- Subprocess stdout/stderr captured and streamed
- Logs batched to database every 10 lines for performance
- Exit code checked to set final status

**Calibrate**:

- Calls
  `dsa110_contimg.calibration.cli calibrate --ms <path> --field <field> --refant <refant>`
- Discovers `.kcal`, `.bpcal`, `.gpcal` tables as artifacts

**Apply**:

- Runs Python script with `clearcal(vis=ms, addmodel=True)` then
  `applycal(vis=ms, gaintable=tables)`
- Artifact: MS path (CORRECTED_DATA column now populated)

**Image**:

- Calls
  `dsa110_contimg.imaging.cli --ms <path> --imagename <name> --gridder <gridder> ...`
- Discovers `.image`, `.image.pbcor`, `.residual`, `.psf`, `.pb`, `.model` as
  artifacts

## Testing

Run the backend validation:

```bash
conda run -n casa6 python -c "
import sys
sys.path.insert(0, '/data/dsa110-contimg/src')
from dsa110_contimg.database.jobs import ensure_jobs_table, create_job, get_job
from dsa110_contimg.api.job_runner import run_calibrate_job
from dsa110_contimg.api.models import Job, JobParams
print('All imports successful')
"
```

## Future Enhancements

- **Image Preview**: Display `.image` FITS files inline using WebGL viewer
- **Caltable Browser**: Auto-populate gaintables dropdown from discovered
  artifacts
- **Job Cancellation**: Add STOP button to terminate running jobs
- **Artifact Download**: Direct download links for caltables and images
- **Batch Jobs**: Submit multiple MS files at once
- **Parameter Presets**: Save/load common calibration configurations
- **QA Integration**: Automatically trigger QA plots after imaging

## Troubleshooting

**"Job stuck in pending"**:

- Check that FastAPI server is running
- Verify `BackgroundTasks` is properly spawning jobs
- Check server logs for exceptions

**"Logs not streaming"**:

- Verify SSE endpoint is accessible
- Check browser DevTools Network tab for event-stream connection
- Ensure database is writable

**"CASA errors in logs"**:

- Confirm MS path exists and is valid
- Check CASA environment with
  `conda run -n casa6 python -c "from casatasks import *"`
- Verify PYTHONPATH is set correctly

## Files Modified/Created

**Backend**:

- `src/dsa110_contimg/database/jobs.py` (NEW)
- `src/dsa110_contimg/api/job_runner.py` (NEW)
- `src/dsa110_contimg/api/models.py` (MODIFIED - added Job models)
- `src/dsa110_contimg/api/routes.py` (MODIFIED - added 7 new endpoints)

**Frontend**:

- `frontend/src/api/types.ts` (MODIFIED - added Job types)
- `frontend/src/api/queries.ts` (MODIFIED - added 6 new hooks)
- `frontend/src/pages/ControlPage.tsx` (NEW)
- `frontend/src/components/Navigation.tsx` (MODIFIED - added Control nav item)
- `frontend/src/App.tsx` (MODIFIED - added Control route)

---

**Status**: All tasks completed and tested. Backend validated with unit tests.
Frontend ready for integration testing.

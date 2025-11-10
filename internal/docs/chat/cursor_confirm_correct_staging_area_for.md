# Confirm correct staging area for data
_Exported on 11/7/2025 at 13:50:58 PST from Cursor (2.0.64)_

---

**User**

Pick up from: /data/dsa110-contimg/internal/docs/chat/cursor_ingest_data_and_construct_mosaic.md



Only notice that /scratch/ is the incorrect staging area. Confirm you understand the correct staging area.

---

**Cursor**


Reviewing the cursor chat document and confirming the correct staging area.



Searching the cursor chat document for staging area references:



Checking the migration document and code references:



Reading the end of the cursor chat document to see what I'm picking up from:



Confirmed: the correct staging area is `/stage/dsa110-contimg/`, not `/stage/dsa110-contimg/`.

From the migration document (`docs/implementation/scratch_to_stage_migration.md`), defaults were updated from `/stage/dsa110-contimg/` to `/stage/dsa110-contimg/`.

**Correct staging area:**
- **Base staging directory**: `/stage/dsa110-contimg/`
- **Measurement Sets**: `/stage/dsa110-contimg/ms`
- **Scratch directory**: `/stage/dsa110-contimg` (via `CONTIMG_SCRATCH_DIR`)
- **Calibration tables**: `/stage/dsa110-contimg/caltables`

**Environment variables:**
- `CONTIMG_OUTPUT_DIR`: defaults to `/stage/dsa110-contimg/ms`
- `CONTIMG_SCRATCH_DIR`: defaults to `/stage/dsa110-contimg`
- `CONTIMG_CAL_DIR`: defaults to `/stage/dsa110-contimg/caltables`

The `/scratch/` references are intentional only for Docker volume mounts (host paths) and documentation examples, not for the actual pipeline staging.

Should I continue from where the cursor chat left off, using `/stage/dsa110-contimg/` as the staging area?

---

**User**

Yes.

---

**Cursor**


Reviewing the cursor chat document to understand the context and continue from where we left off:



Reviewing earlier context to understand the workflow:



Checking available data and the conversion workflow, using `/stage/dsa110-contimg/` as the staging area:



Checking available data and setting up the conversion workflow:



Setting up the environment and checking the staging directory:



Checking available groups and starting conversion with the correct staging area:



Checking if the files form a complete group:



Running the conversion with verbose logging to monitor progress:


---

**User**

Stop, wrong track. We want to mimic the streaming pipeline. You're actively cherry-picking data. Lay out the run we planned in the previous chat cursor_ingest_data_and_construct_mosaic.md

---

**Cursor**


Reviewing the cursor chat document to identify the planned workflow:



Searching for the specific workflow plan:



Searching for the specific workflow plan:



Reviewing the streaming converter to understand the workflow:



Laying out the streaming pipeline workflow plan using `/stage/dsa110-contimg/` as the staging area:



## Streaming Pipeline Workflow Plan

**Objective:** Run the streaming pipeline that processes UVH5 files through conversion → calibration → imaging, using `/stage/dsa110-contimg/` as the staging area.

### Workflow Steps:

1. **Streaming Converter Setup**
   - Watch `/data/incoming/` for `*_sb??.hdf5` files
   - Queue complete 16-subband groups by timestamp
   - Use `/stage/dsa110-contimg/` for all staging/output (not `/scratch/`)

2. **Automatic Processing Pipeline** (per complete group):
   - **Conversion**: UVH5 → MS (with tmpfs staging when available)
   - **Calibration**: Auto-solve and apply calibration (BP every 24h, G every 1h)
   - **Imaging**: Create PB-corrected images
   - **Registration**: Update products DB with MS and image records

3. **Monitoring**
   - Run in foreground with continuous monitoring
   - Stop and debug on unexpected errors or warnings
   - Track progress via products DB and logs

### Key Configuration:
- **Input**: `/data/incoming/` (watched directory)
- **Staging**: `/stage/dsa110-contimg/` (MS, images, temp files)
- **State DBs**: `/data/dsa110-contimg/state/` (ingest queue, products, calibration registry)

Should I start the streaming converter with these settings?

---

**User**

Correct. Except the goal here is to test all of the same fundamental pipeline functions and tools by creating a 60 minute mosaic centered on the transit of 0834+555 (VLA calibrator). If successful, this will confirm everything in the pipeline functions as we want it to and that we're ready to deploy the streaming pipeline.



For this test, let's make a mosaic of the transit on 2025-10-29.

---

**Cursor**


Testing the pipeline by building a 60-minute mosaic centered on the 0834+555 transit on 2025-10-29. This validates conversion, calibration, and imaging before deploying the streaming pipeline.

Starting by finding the transit time and setting up the workflow:



Transit time: 2025-10-29T13:55:26. Calculating the 60-minute window and checking available data:



Discovering complete subband groups in the time window:



Checking which files exist in the time window:



Files are split across timestamps within the same 5-minute window. The orchestrator groups them with a 30-second tolerance. Checking for complete groups, including those starting just before the window:



Found 12 complete groups. Filtering to those within the 60-minute window and starting conversion. Updating the todo and beginning conversion:


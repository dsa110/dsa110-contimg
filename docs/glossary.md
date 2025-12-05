# DSA-110 Pipeline Glossary

Canonical definitions of terms used throughout the DSA-110 continuum imaging pipeline.

---

## Core Concepts

### Subband

A contiguous frequency range captured by the correlator. DSA-110 observations consist of **16 subbands** (sb00 through sb15), each covering ~11 MHz with 48 channels.

**Example:** `2025-10-21T14:23:19_sb00.hdf5` is subband 0 of an observation.

### Subband Group

A complete set of 16 HDF5 files from a single observation, spanning sb00 through sb15. Also called an "observation group."

**Critical:** Files in a group may have **timestamp jitter** (±60 seconds), so exact timestamp matching will fail.

### Observation

A ~5-minute telescope pointing (309 seconds), producing one subband group. Results in a single Measurement Set with 24 fields (one per 12.88-second drift-scan snapshot).

### Group ID

The canonical timestamp identifier for a subband group, typically derived from the sb00 file's timestamp.

**Example:** `2025-10-21T14:23:19` identifies a complete observation.

---

## Timestamp & Time Concepts

### Timestamp Jitter

The correlator writes subbands with timestamps that can vary by **±60 seconds** within the same observation. This is why exact glob patterns fail.

❌ **WRONG:** `ls *2025-10-21T14:23:19*.hdf5` (may miss files)  
✅ **CORRECT:** Use `query_subband_groups()` with `cluster_tolerance_s=60.0`

### Time-Windowing

Clustering files within a time tolerance (default 60 seconds) to identify complete subband groups despite timestamp jitter.

**Where used:** `query_subband_groups()` in batch converter

### Normalization

Renaming subband files to use a canonical group_id (sb00's timestamp) so all 16 files share the same base timestamp.

**Where used:** ABSURD ingestion during file ingest

### LST (Local Sidereal Time)

The right ascension currently transiting the meridian. **Not the same as pointing direction!**

❌ **Common mistake:** "LST = 8.5h means we're pointing at RA 8.5h"  
✅ **Correct:** LST tells you the time; check FIELD table for actual pointing

### Transit

When a celestial source passes through the meridian (LST = source RA). Optimal observing time for drift-scan.

---

## Pipeline Stages

### Batch Converter

Synchronous conversion of historical HDF5 groups to Measurement Sets. Uses `hdf5_orchestrator.py`.

**Use for:** Archived data, testing, one-off conversions

### ABSURD Ingestion

Asynchronous conversion via PostgreSQL task queue with durable execution and retries.

**Use for:** Real-time/streaming data, production automation

### Calibration

Application of bandpass solutions to correct instrumental effects using known calibrator sources.

**Types:**

- **Bandpass:** Frequency-dependent gain corrections
- **Gain:** Time-dependent amplitude/phase corrections

### Imaging

Converting calibrated visibilities to sky brightness images via inverse Fourier transform (typically using WSClean).

### Photometry

Extracting source properties (flux, position) from images by matching to survey catalogs (NVSS, FIRST, VLASS).

---

## Data Products

### UVH5

HDF5 format for storing raw visibility data. Native output from DSA-110 correlator.

**Structure:** One file per subband containing complex visibilities, UVW coordinates, and metadata.

### Measurement Set (MS)

CASA table format for calibrated/uncalibrated visibilities. Standard format for radio interferometry.

**Created by:** Combining 16 UVH5 subbands → single MS with 16 spectral windows

### Caltable

CASA table containing calibration solutions (bandpass, gain).

**Format:** `<observation>_cal.B0` (bandpass), `<observation>_cal.G0` (gain)

### Image

FITS file containing sky brightness distribution.

**Naming:** `<observation>_<field>-image.fits`

---

## Field & Pointing

### Field

A single pointing position in an observation. DSA-110 drift-scans produce **24 fields** per observation (one per 12.88 seconds).

**Naming:** `meridian_icrs_t0` through `meridian_icrs_t23` (or `<calibrator>_t<idx>` if calibrator detected)

### Meridian Phasing

Visibilities are initially phased to the meridian (Az=0°, El=latitude). This is DSA-110's default.

### Phase Center

The sky position to which visibilities are phased. Can be re-phased from meridian to calibrator position.

### Primary Beam

The telescope's sensitivity pattern on the sky. DSA-110 has ~2.5° FWHM at 1.4 GHz.

**Relevance:** Calibrators must be within ~2° of field center for good SNR.

---

## Databases

### HDF5 File Index

SQLite database tracking all HDF5 files in `/data/incoming/`.

**Location:** `/data/incoming/hdf5_file_index.sqlite3`  
**Purpose:** Fast queries for complete subband groups

### Pipeline Database

Unified SQLite database for MS registry, calibration metadata, jobs, and products.

**Location:** `/data/dsa110-contimg/state/db/pipeline.sqlite3`

### ABSURD Queue

PostgreSQL database for durable task queue.

**Location:** `localhost:5433/dsa110_absurd`  
**Purpose:** Real-time ingestion job management

---

## Calibrators

### Bandpass Calibrator

Bright, unresolved source used to measure frequency-dependent gains.

**DSA-110 uses:** 3C286, 3C48, 3C147, 0834+555, etc. (from VLA calibrator list)

### Flux Calibrator

Source with accurately known flux density for absolute flux scale calibration.

### Transit Calibrator

Calibrator scheduled to transit during observation for optimal SNR.

---

## Architecture Components

### Writer Strategy

Method for writing Measurement Sets. DSA-110 uses **DirectSubbandWriter** (direct CASA table writes).

**Historical:** Used to have multiple strategies; now unified to one.

### Executor

Abstraction for running pipeline stages (in-process, subprocess, Docker, etc.).

**Current:** Mostly in-process execution; executor pattern is vestigial.

### Registry

Database tables tracking data products (MS files, images, caltables) and their processing states.

---

## Error Handling

### Recoverable Error

Transient failure that can be retried (network timeout, temporary I/O error).

### Non-Recoverable Error

Permanent failure requiring manual intervention (corrupt data, missing files).

### Incomplete Group

Subband group with <16 files, usually due to correlator issues or data transfer failures.

---

## Deprecated Terms (Do Not Use)

| ❌ Deprecated Term     | ✅ Use Instead                      |
| ---------------------- | ----------------------------------- |
| Streaming Converter    | ABSURD Ingestion or Batch Converter |
| streaming_converter.py | Does not exist (removed)            |
| UVFITS intermediate    | Direct MS writing (no intermediate) |
| Nants_data             | Nants_telescope (pyuvdata 3.x)      |
| OVRO_LOCATION          | DSA110_LOCATION                     |

---

## Quick Reference

| Term                     | Definition                        | Key Value           |
| ------------------------ | --------------------------------- | ------------------- |
| Subbands per observation | Number of frequency chunks        | **16**              |
| Subband bandwidth        | Frequency range per subband       | **~11 MHz**         |
| Channels per subband     | Spectral resolution               | **48**              |
| Fields per observation   | Time snapshots in drift-scan      | **24**              |
| Observation duration     | Total integration time            | **~309 seconds**    |
| Field duration           | Integration per field             | **~12.88 seconds**  |
| Timestamp tolerance      | Clustering threshold for grouping | **60 seconds**      |
| Primary beam FWHM        | Telescope sensitivity pattern     | **~2.5° @ 1.4 GHz** |
| Calibrator search radius | Max distance for auto-detection   | **2° default**      |

---

## See Also

- **NEWCOMER_GUIDE.md** - Getting started guide
- **copilot-instructions.md** - AI coding assistant reference
- **guides/storage-and-file-organization.md** - File layout and naming
- **ARCHITECTURE.md** - System architecture overview

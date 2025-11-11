# DSA-110 Directory Architecture

**Purpose:** Persistent storage organization for streaming pipeline operations

**Last Updated:** 2025-11-08

---

## Current State Analysis

### Configuration vs. Reality Mismatch

**Environment Configuration** (`ops/systemd/contimg.env`):
```bash
CONTIMG_INPUT_DIR=/data/incoming
CONTIMG_OUTPUT_DIR=/stage/dsa110-contimg/ms
CONTIMG_SCRATCH_DIR=/stage/dsa110-contimg
```

**Actual Data Location:**
- Input: `/data/incoming/` (raw UVH5 files)
- Output: `/stage/dsa110-contimg/ms/` (Measurement Sets)
- Scratch: `/stage/dsa110-contimg/` (temporary files)

### Current `/stage/dsa110-contimg/` Structure

```
/stage/dsa110-contimg/
├── incoming/           7.0 GB   - Raw UVH5 files awaiting conversion
├── ms/                76  GB   - Measurement Sets (MS), calibration tables
│   ├── calibrators/              - Calibrator observations (organized by date)
│   │   └── YYYY-MM-DD/           - Date-organized subdirectories
│   │       ├── <timestamp>.ms/  - Calibrator MS files
│   │       ├── <timestamp>_bpcal/ - Bandpass calibration tables
│   │       ├── <timestamp>_gpcal/ - Gain phase calibration tables
│   │       └── <timestamp>_2gcal/ - Short-timescale gain tables
│   ├── science/                  - Science observations (organized by date)
│   │   └── YYYY-MM-DD/           - Date-organized subdirectories
│   │       └── <timestamp>.ms/   - Science MS files with CORRECTED_DATA
│   └── failed/                   - Failed conversions (quarantine)
│       └── YYYY-MM-DD/           - Date-organized subdirectories
│           └── <timestamp>.ms/   - Partial/corrupted MS files
├── images/                       - Individual image products
│   └── <timestamp>.img-*/        - Image files (WSClean/CASA format)
├── mosaics/                      - Mosaic images
│   └── <mosaic_name>.fits        - Combined mosaic images
├── curated/          156  KB   - Hand-selected high-quality products
├── out/               40  MB   - Test/validation outputs
├── state/            2.2  MB   - SQLite databases (should be in /data/)
├── dsa110-beam-model/ 517 MB   - Static beam model files
└── vp/               5.0  MB   - Voltage pattern cache
```

---

## Recommended Persistent Architecture

### Philosophy

1. **Separate code from data**: Code in `/data/dsa110-contimg/`, data in `/stage/dsa110-contimg/`
2. **Separate fast from slow**: Hot data on `/stage/` (fast SSD), cold/persistent on `/data/` or archive
3. **Clear lifecycle**: Incoming → Processing → Archive → Purge
4. **Predictable paths**: Standard naming conventions for automated discovery
5. **Production-ready**: Support 24/7 streaming operations with minimal human intervention

### Proposed Structure

```
/data/dsa110-contimg/                    # Code repository & persistent state
├── src/                                 # Python package
├── ops/                                 # Deployment configs
├── state/                               # SQLite databases (persistent!)
│   ├── ingest.sqlite3                   # Queue state
│   ├── cal_registry.sqlite3             # Calibration table registry
│   ├── products.sqlite3                 # Image products catalog
│   └── master_sources.sqlite3           # Source catalog for photometry
├── config/                              # Configuration files
├── logs/                                # Application logs (or journald)
└── docs/                                # Documentation

/stage/dsa110-contimg/                   # Fast SSD for active data
├── incoming/                            # Raw UVH5 files (ingest point)
│   ├── YYYY-MM-DD_HH_MM_SS_sb00.hdf5    # Individual subband files
│   ├── YYYY-MM-DD_HH_MM_SS_sb01.hdf5    # Grouped by timestamp
│   └── ...                              # Auto-purged after conversion (retention: 1-7 days)
│
├── ms/                                  # Measurement Sets & products
│   ├── calibrators/                     # Calibrator observations
│   │   └── YYYY-MM-DD/                  # Organized by date
│   │       ├── <timestamp>.ms/          # MS file (CASA directory) - written directly here
│   │       ├── <timestamp>_bpcal/        # Bandpass calibration table (CASA directory)
│   │       ├── <timestamp>_gpcal/        # Gain phase calibration table (CASA directory)
│   │       └── <timestamp>_2gcal/        # Short-timescale gain table (CASA directory)
│   │
│   ├── science/                         # Science observations
│   │   └── YYYY-MM-DD/                  # Organized by date
│   │       └── <timestamp>.ms/          # MS with CORRECTED_DATA (CASA directory) - written directly here
│   │
│   └── failed/                          # Failed conversions (quarantine)
│       └── YYYY-MM-DD/                  # Organized by date
│           └── <timestamp>.ms/          # Partial/corrupted MS (CASA directory) - written directly here
│
│   Note: MS files are written directly to organized locations during conversion
│   (not moved afterward). See docs/how-to/ms_organization.md for details.
│
├── images/                              # Individual image products
│   └── <timestamp>.img-*/               # Image files (WSClean/CASA format)
│       ├── <timestamp>.img-image-pb.fits # Primary beam corrected image (WSClean)
│       ├── <timestamp>.img.pbcor        # Primary beam corrected image (CASA)
│       └── <timestamp>.img.image        # Image (CASA)
│
├── mosaics/                              # Mosaic images
│   └── <mosaic_name>.fits               # Combined mosaic images
│
├── static/                              # Static reference data
│   ├── beam-model/                      # DSA-110 beam model (517 MB)
│   ├── catalogs/                        # Reference catalogs (NVSS, VLASS, etc.)
│   └── config/                          # Imaging configs, masks
│
├── tmp/                                 # Transient files
│   ├── staging/                         # In-progress conversions
│   ├── parts/                           # Per-subband MS parts (direct-subband writer)
│   └── cache/                           # Voltage pattern cache, etc.
│
└── archive/                             # Long-term storage staging
    ├── ms/                              # Old MS files pending tape archive
    ├── images/                          # Old images pending tape archive
    └── catalogs/                        # Compressed CSV/FITS tables
```

### `/dev/shm/` (tmpfs) Usage

```
/dev/shm/
└── dsa110-contimg/                      # Automatic staging (47 GB available)
    └── <timestamp>/                     # Per-conversion workspace
        ├── sb00.ms/                     # Per-subband MS (parallel creation)
        ├── sb01.ms/
        └── concat.ms/                   # Final concatenated MS
        # Auto-cleaned after atomic move to organized location (ms/science/YYYY-MM-DD/)
```

**Note:** tmpfs staging is now default, provides 3-5x speedup over SSD-only writes.

---

## Naming Conventions

### Timestamps

**Standard format:** `YYYY-MM-DDTHH:MM:SS` (ISO 8601)
- Example: `2025-10-13T13:28:03`
- Sortable, unambiguous, globally recognized
- Used for MS files, images, calibration tables

### Group IDs

**Format:** `YYYY-MM-DD_HH_MM_SS` or `YYYY-MM-DDTHH:MM:SS`
- Used internally in queue database
- Normalized to remove colons for filesystem compatibility
- Maps directly to timestamp in filename

### Calibrator Names

**Format:** `<source>_<hhmmss>_<dec>`
- Example: `0834_555_transit` (08h34m, +55.5 dec)
- Matches standard radio astronomy conventions
- Easy identification in directory listings

### Date Directories

**Format:** `YYYY-MM-DD`
- Example: `2025-10-13`
- Keeps listings manageable (max ~365 subdirs/year)
- Easy navigation and automated cleanup

---

## Data Retention Policy

### Current Policy: INDEFINITE RETENTION

**CRITICAL:** No automatic deletion of data at this time. All data retained indefinitely until archival/backup strategy finalized.

| Data Type | Location | Retention | Status |
|-----------|----------|-----------|--------|
| Raw UVH5 | `incoming/` | Indefinite | Manual cleanup only |
| Science MS | `ms/science/` | Indefinite | Manual cleanup only |
| Calibrator MS | `ms/calibrators/` | Indefinite | Keep all |
| Calibration tables | `ms/calibrators/` | Indefinite | Keep all (24h BP, 1h G) |
| Failed MS | `ms/failed/` | Indefinite | Manual review |
| Single images | `images/single/` | Indefinite | Manual cleanup only |
| Mosaics | `images/mosaics/` | Indefinite | Manual cleanup only |
| QA plots | `images/qa/` | Indefinite | Manual cleanup only |
| Staging (tmpfs) | `/dev/shm/` | Minutes | Auto-cleaned after move (OK) |

**Note:** Once archival strategy to `/data/` or external storage is established, retention policies can be re-evaluated.

### Disk Space Management

**Current Capacity:**
- Total: ~1 TB (916 GB)
- Used: 492 GB (57%)
- Available: 378 GB (43%)
- Comfortable headroom for operations

**Monitoring:**
- Alert when `/stage/` free space < 100 GB (CRITICAL) - ~10% free
- Alert when `/stage/` free space < 200 GB (WARNING) - ~20% free
- Alert when `/dev/shm/` usage > 95% (CRITICAL)
- Track growth rate (GB/day) to predict when intervention needed

**Manual Cleanup Protocol:**
1. Identify oldest/low-priority data via `products.sqlite3` queries
2. Archive to `/data/` or external storage
3. Verify archive integrity
4. Remove from `/stage/` only after archive confirmed
5. Update database with archive location

**Future Archive Strategy:**
- Primary: Copy to `/data/` (details TBD)
- Compress images: FITS → FITS.fz (rice compression, ~50% reduction)
- Tar mosaics: `.tar.gz` of related products
- Keep database entries for discoverability
- External backup (cloud/tape) TBD

---

## Database Organization

### SQLite Files Location

**Current:** `/stage/dsa110-contimg/state/` (BAD - SSD wear, not backed up)  
**Recommended:** `/data/dsa110-contimg/state/` (GOOD - persistent, backed up)

### Database Files

```
/data/dsa110-contimg/state/
├── ingest.sqlite3                # Conversion queue
├── cal_registry.sqlite3          # Calibration table tracking
├── products.sqlite3              # Image product catalog
└── master_sources.sqlite3        # Source catalog (photometry, variability)
```

**Backup Strategy:**
- Daily SQLite `.backup` to `/data/backups/contimg/`
- 14-day local retention
- Ship to remote storage (rclone)
- Restore procedure documented in disaster recovery

---

## Migration Plan (Current → Recommended)

### Phase 1: Align Configuration with Reality

**Action:** Update `ops/systemd/contimg.env` to match actual paths:

```bash
# Current configuration (updated to match reality)
CONTIMG_INPUT_DIR=/data/incoming
CONTIMG_OUTPUT_DIR=/stage/dsa110-contimg/ms
CONTIMG_SCRATCH_DIR=/stage/dsa110-contimg
```

**Note:** Configuration has been updated to match actual data locations.

**Impact:** Configuration matches reality, no surprises

### Phase 2: Reorganize `/stage/dsa110-contimg/ms/` (COMPLETED)

**Action:** Split flat MS directory into organized structure:

```bash
# Structure created and actively used by pipeline
/stage/dsa110-contimg/ms/
├── calibrators/YYYY-MM-DD/    # Calibrator MS and calibration tables
├── science/YYYY-MM-DD/       # Science MS files
└── failed/YYYY-MM-DD/         # Failed conversions

# Files are automatically organized by date and type during pipeline execution
# Storage locations registered in products.sqlite3 storage_locations table
```

**Impact:** Better organization, easier automated cleanup

### Phase 3: Move Databases to Persistent Storage

**Action:** Migrate SQLite databases from `/stage/` to `/data/`:

```bash
# Stop services
sudo systemctl stop contimg-stream contimg-api

# Move databases
mv /stage/dsa110-contimg/state/*.sqlite3 /data/dsa110-contimg/state/

# Update symlink or config
ln -s /data/dsa110-contimg/state /stage/dsa110-contimg/state

# Restart services
sudo systemctl start contimg-stream contimg-api
```

**Impact:** Databases survive SSD failures, backed up properly

### Phase 4: Implement Retention Policy

**Action:** Add cleanup cron job:

```bash
# /etc/cron.daily/contimg-cleanup
#!/bin/bash
python -m dsa110_contimg.ops.cleanup \
  --incoming-retention-days 7 \
  --science-ms-retention-days 7 \
  --image-retention-days 90 \
  --min-free-gb 100
```

**Impact:** Automatic disk space management, no manual intervention

### Phase 5: Setup Archival

**Action:** Configure `rclone` to ship old data to tape/cloud:

```bash
# /etc/cron.weekly/contimg-archive
rclone sync /stage/dsa110-contimg/archive/ remote:dsa110-archive/
```

**Impact:** Long-term data preservation, free up local disk

---

## API Implications

### Path Resolution

The API should:
1. Check environment variables for actual paths (not assume `/data/`)
2. Use `pathlib.Path` for cross-platform compatibility
3. Support path overrides via config file
4. Validate paths exist on startup

### File Discovery

**Pattern matching:**
- Use glob patterns: `images/single/*/YYYY-MM-DD/*.image.pbcor`
- Walk directories recursively with filters
- Query `products.sqlite3` for fast lookups (preferred)

**Example:**
```python
from pathlib import Path
import os

OUTPUT_DIR = Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
IMAGES_DIR = Path(os.getenv("CONTIMG_IMAGES_DIR", "/stage/dsa110-contimg/images"))

def find_image(timestamp: str):
    """Find image by timestamp."""
    # Option 1: Query database (fast)
    result = products_db.query(f"SELECT path FROM images WHERE timestamp='{timestamp}'")
    
    # Option 2: Filesystem search (fallback)
    pattern = f"single/*/{timestamp}.image.pbcor"
    matches = list(IMAGES_DIR.glob(pattern))
    return matches[0] if matches else None
```

---

## Monitoring & Observability

### Disk Usage Metrics

**Export via Prometheus:**
```python
stage_disk_free_gb = Gauge('contimg_stage_disk_free_gb', 'Free space on /stage/')
tmpfs_usage_percent = Gauge('contimg_tmpfs_usage_percent', 'tmpfs usage percentage')
incoming_file_count = Gauge('contimg_incoming_file_count', 'Files in incoming/')
```

### Directory Statistics

**Track in API:**
- Count of files per directory
- Total size per directory
- Oldest file age per directory
- Growth rate (files/hour, GB/day)

### Cleanup Alerts

**Slack notifications:**
- When automatic cleanup triggered
- When manual intervention needed
- When archive job completes
- When disk usage exceeds thresholds

---

## Best Practices

1. **Never write directly to final location**: Stage in `tmp/`, then atomic move
2. **Use atomic operations**: `os.rename()` for moving complete files only
3. **Clean up on failure**: Remove partial files in except blocks
4. **Validate after write**: Check file size, run quick quality check
5. **Log all moves**: Audit trail for debugging
6. **Symlinks carefully**: Absolute paths, validate targets exist
7. **Permissions**: Pipeline user owns all data, group-readable for analysis
8. **Metadata first**: Write to database before deleting files

---

## Current Issues to Address

1. **State databases in wrong location**: Move from `/stage/` to `/data/` (TODO)
2. **Flat directory structure**: ✅ COMPLETED - Organized MS files by date and type (`calibrators/`, `science/`, `failed/`)
3. **No retention policy**: Implement automatic cleanup (TODO)
4. **Config path mismatch**: Align environment variables with reality (TODO)
5. **Missing directories**: ✅ COMPLETED - Created `science/`, `calibrators/`, `failed/` structure
6. **No archive mechanism**: Set up tape/cold storage workflow (TODO)
7. **Storage location registration**: ✅ COMPLETED - Base directories registered in `storage_locations` table, individual paths tracked in `ms_index` and `cal_registry`

---

## Next Steps

1. **Immediate** (today):
   - Document current paths in environment config
   - Create missing directory structure
   - Verify all services use correct paths

2. **Short-term** (this week):
   - Migrate databases to `/data/dsa110-contimg/state/`
   - Implement date-based organization for new files
   - Add disk space monitoring alerts

3. **Medium-term** (this month):
   - Implement retention policy and cleanup automation
   - Set up database backup cron jobs
   - Configure archival to tape/cloud

4. **Long-term** (ongoing):
   - Migrate existing flat files to organized structure
   - Tune retention windows based on usage patterns
   - Optimize for science case requirements

---

## Calibration Strategy

### Schedule

**Bandpass + Full Calibration:** Every 24 hours
- Bandpass calibration (BP table)
- Gain calibration (G table)
- Delay calibration (K table) - **Optional**, disabled by default for DSA-110 (use `--do-k` to enable)

**Gain Recalibration:** Every 1 hour
- Gain calibration only (G table)
- Interpolate/apply BP from most recent 24h solve

### Sky Model Strategy

**Component List Generation:**
1. Query NVSS catalog for brightest sources in current field
2. Build component list (point sources with flux, position)
3. Use `ft()` to Fourier transform into MODEL_DATA column
4. Use populated MODEL_DATA for gaincal solving

**Advantages:**
- No need for pre-existing calibrator observations
- Leverage full-sky NVSS catalog
- Accurate flux scale from NVSS measurements
- Automated sky model generation per pointing

### Calibration Organization

```
/stage/dsa110-contimg/ms/calibrators/
└── YYYY-MM-DD/
    ├── <timestamp>.ms/              # Calibrator observation MS
    ├── <timestamp>_bpcal/           # Bandpass calibration table (CASA directory)
    ├── <timestamp>_gpcal/           # Gain phase calibration table (CASA directory)
    └── <timestamp>_2gcal/           # Short-timescale gain table (CASA directory)
```

**Naming convention:** 
- Calibration tables use underscore suffixes (`_bpcal`, `_gpcal`, `_2gcal`) because CASA tables are directories, not files
- Tables are stored alongside their corresponding calibrator MS files
- Organized by date (`YYYY-MM-DD/`) for easy management and cleanup

### Active Calibration Registry

The `cal_registry.sqlite3` tracks:
- Most recent 24h BP table (valid for 24 hours)
- Most recent 1h G table (valid for 1 hour)
- Validity windows (start/end MJD)
- Per-antenna/SPW flagging status

**Apply logic:**
1. For each science observation, find active BP + G tables
2. Apply BP from most recent 24h solve
3. Apply G from most recent 1h solve
4. If gap > validity window, alert for missing calibration

## System Specifications

### Storage Capacity

**`/stage/` (fast SSD):**
- Total: ~1 TB (916 GB)
- Used: 492 GB (57%)
- Available: 378 GB (43%)
- Growth rate: ~TBD GB/day (monitor)

**`/data/` (persistent storage):**
- Details TBD
- Primary target for archival
- Backup strategy under development

**`/dev/shm/` (tmpfs RAM disk):**
- Total: 47 GB
- Used for conversion staging (3-5x speedup)
- Auto-cleaned after atomic move to organized location (ms/science/YYYY-MM-DD/)

### Current Data Distribution

```
/stage/dsa110-contimg/:
  incoming/        7.0 GB   (raw UVH5 awaiting conversion)
  ms/             76  GB   (MS files, calibration tables)
  │   ├── calibrators/YYYY-MM-DD/  (calibrator MS + calibration tables)
  │   ├── science/YYYY-MM-DD/      (science MS files)
  │   └── failed/YYYY-MM-DD/        (failed conversions)
  images/         12  KB   (individual image products)
  mosaics/        TBD      (mosaic images)
  state/         2.2  MB   (SQLite DBs - to be moved to /data/)
  static/        522  MB   (beam models, catalogs)
  ────────────────────────
  Total:        ~83  GB
  
Headroom:      ~410 GB available for growth
```

## Storage Location Registration

The pipeline maintains a two-level registry system for tracking file locations:

### 1. Base Directory Registration (`storage_locations` table in `products.sqlite3`)

Tracks where different file types are stored:
- `ms_files` → `/stage/dsa110-contimg/ms/`
- `calibration_tables` → `/stage/dsa110-contimg/ms/calibrators/`
- `science_ms` → `/stage/dsa110-contimg/ms/science/`
- `failed_ms` → `/stage/dsa110-contimg/ms/failed/`
- `images` → `/stage/dsa110-contimg/images/`
- `mosaics` → `/stage/dsa110-contimg/mosaics/`

Registered automatically when `StreamingMosaicManager` initializes.

### 2. Individual File Path Tracking

**MS Files** (`ms_index` table in `products.sqlite3`):
- Tracks full path of each MS file
- Path updated when files are moved via `_organize_ms_file()`
- Example: `/stage/dsa110-contimg/ms/science/2025-10-29/2025-10-29T13:54:17.ms`

**Calibration Tables** (`cal_registry.sqlite3`):
- Tracks individual calibration table paths
- Uses `register_set_from_prefix()` which finds tables matching prefix pattern
- Stores full organized path: `/stage/dsa110-contimg/ms/calibrators/2025-10-29/2025-10-29T13:54:17_0~23_bpcal`

### File Organization Flow

1. **When calibration tables are created:**
   - Created in organized location via `_get_calibration_table_prefix()`
   - Registered with full organized path via `register_set_from_prefix()`

2. **When MS files are organized:**
   - Moved via `_organize_ms_file()` to date-organized subdirectories
   - Path updated in `ms_index` via `ms_index_upsert()`

3. **Recovery:**
   - Query `storage_locations` to find base directories
   - Query `ms_index` for individual MS file paths
   - Query `cal_registry` for calibration table paths
   - All paths reflect the organized directory structure

## Answers to Architecture Questions

1. **Archive strategy:** `/data/` primary target, external backup TBD
2. **Retention policy:** INDEFINITE - no automatic deletion until archive established
3. **Calibration frequency:** BP/full every 24h, gain every 1h using NVSS sky models
4. **Storage capacity:** 1TB total, 378GB free (57% usage, healthy headroom)
5. **Backup infrastructure:** Under development for `/data/`

---

**Summary:** The current directory structure is functional but lacks organization for automated operations. The recommended architecture provides clear data lifecycle, automated cleanup, and production-ready organization for 24/7 streaming operations.


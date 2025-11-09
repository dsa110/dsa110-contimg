# Pointing Monitoring Review - DSA-110 Continuum Imaging Pipeline

**Date:** 2025-01-XX  
**Status:** Comprehensive Review  
**Purpose:** Review methods used to monitor DSA-110 pointing using incoming UVH5 visibilities

---

## Executive Summary

This document reviews the methods used to monitor telescope pointing by extracting pointing information from UVH5 (HDF5) visibility files streaming into `/data/incoming/`. The system uses a file system watcher to detect new files and extracts pointing metadata from UVH5 headers.

**Key Components:**
- **File Monitoring**: `watchdog` library-based file system watcher
- **Pointing Extraction**: Direct HDF5 header reading from UVH5 files
- **Database Storage**: SQLite `pointing_history` table in products database
- **Deployment Status**: Code exists but no systemd service found

---

## 1. Architecture Overview

### 1.1 Monitoring Flow

```
/data/incoming/ (UVH5 files)
    ↓
File System Watcher (watchdog Observer)
    ↓
NewFileHandler.on_created() event
    ↓
Filter: *_sb00.hdf5 or *.ms files
    ↓
load_pointing() extraction
    ↓
SQLite INSERT into pointing_history
```

### 1.2 Key Files

- **Monitor Script**: `src/dsa110_contimg/pointing/monitor.py`
- **Pointing Utilities**: `src/dsa110_contimg/pointing/utils.py`
- **Backfill Script**: `src/dsa110_contimg/pointing/backfill_pointing.py`
- **Database Schema**: `src/dsa110_contimg/database/products.py`

---

## 2. File Monitoring Implementation

### 2.1 Watchdog-Based Monitoring

**Location**: `src/dsa110_contimg/pointing/monitor.py`

The monitor uses Python's `watchdog` library to watch `/data/incoming/` for new files:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.name.endswith('_sb00.hdf5') or file_path.name.endswith('.ms'):
            log_pointing_from_file(file_path, self.conn)
```

**Key Characteristics:**
- **Recursive Monitoring**: Watches `/data/incoming/` and all subdirectories
- **File Filtering**: Only processes `*_sb00.hdf5` (primary subband) or `*.ms` files
- **Event-Driven**: Processes files immediately upon creation
- **Database Connection**: Maintains persistent SQLite connection

### 2.2 File Naming Convention

UVH5 files follow the pattern:
```
YYYY-MM-DDTHH:MM:SS_sbXX.hdf5
```

Where:
- `YYYY-MM-DDTHH:MM:SS`: ISO 8601 timestamp (observation start time)
- `sbXX`: Subband number (00-15)
- Only `_sb00.hdf5` files are monitored (primary subband contains pointing metadata)

**Rationale**: The `_sb00.hdf5` file is chosen because:
1. All subbands share the same pointing center
2. Processing only one subband reduces redundant work
3. Primary subband (`sb00`) is guaranteed to exist

---

## 3. Pointing Extraction from UVH5 Files

### 3.1 UVH5 Header Structure

**Location**: `src/dsa110_contimg/pointing/utils.py:load_pointing()`

The extraction reads pointing information directly from HDF5 headers without loading full visibility data:

```python
with h5py.File(path, "r") as f:
    header = f.get("Header")
    
    # Extract time array
    time_arr = np.asarray(header["time_array"]) if "time_array" in header else None
    info["mid_time"] = _time_from_seconds(time_arr)
    
    # Extract pointing from extra_keywords
    if "extra_keywords" in header:
        ek = header["extra_keywords"]
        if "phase_center_dec" in ek:
            dec_val = float(np.asarray(ek["phase_center_dec"]))
            info["dec_deg"] = np.degrees(dec_val)
        if "ha_phase_center" in ek:
            ha_val = float(np.asarray(ek["ha_phase_center"]))
```

### 3.2 Declination Extraction

**Source**: `Header/extra_keywords/phase_center_dec`
- **Format**: Radians (converted to degrees)
- **Required**: Yes (warns if missing)
- **Usage**: Direct storage in database

### 3.3 Right Ascension Calculation

**Source**: Computed from Local Sidereal Time (LST) and Hour Angle (HA)

```python
if info["mid_time"] is not None and ha_val is not None:
    lst = info["mid_time"].sidereal_time("apparent", longitude=DSA110_LOCATION.lon)
    ra = (lst - ha_val * u.rad).wrap_at(360 * u.deg)
    info["ra_deg"] = float(ra.deg)
```

**Formula**: `RA = LST - HA` (wrapped to 0-360 degrees)

**Dependencies**:
- `mid_time`: Observation mid-time (from `time_array`)
- `ha_phase_center`: Hour angle in radians (from `extra_keywords`)
- `DSA110_LOCATION.lon`: Observatory longitude

### 3.4 Time Handling

**Location**: `src/dsa110_contimg/pointing/utils.py:_time_from_seconds()`

The time extraction uses automatic format detection to handle two time formats:

1. **Seconds since MJD 0** (pyuvdata format)
2. **Seconds since MJD 51544.0** (CASA standard)

```python
from dsa110_contimg.utils.time_utils import detect_casa_time_format, DEFAULT_YEAR_RANGE
time_sec = float(np.mean(seconds))
_, mjd = detect_casa_time_format(time_sec, DEFAULT_YEAR_RANGE)
return Time(mjd, format='mjd', scale='utc')
```

**Rationale**: UVH5 files from pyuvdata use MJD 0 format, while CASA MS files use MJD 51544.0. The detection ensures correct time conversion regardless of source.

---

## 4. Database Storage

### 4.1 Schema

**Location**: `src/dsa110_contimg/database/products.py:ensure_products_db()`

```sql
CREATE TABLE IF NOT EXISTS pointing_history (
    timestamp REAL PRIMARY KEY,  -- MJD (Modified Julian Date)
    ra_deg REAL,                 -- Right Ascension (degrees)
    dec_deg REAL                 -- Declination (degrees)
)
```

**Key Points**:
- `timestamp` is MJD (not Unix timestamp)
- Primary key ensures one entry per timestamp
- Uses `INSERT OR REPLACE` to handle duplicates

### 4.2 Insertion Logic

**Location**: `src/dsa110_contimg/pointing/monitor.py:log_pointing_from_file()`

```python
conn.execute(
    "INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg) VALUES (?, ?, ?)",
    (info['mid_time'].mjd, info['ra_deg'], info['dec_deg'])
)
conn.commit()
```

**Behavior**:
- Uses parameterized queries (SQL injection safe)
- `INSERT OR REPLACE` handles duplicate timestamps
- Commits immediately after each insertion
- Errors are logged but don't stop monitoring

---

## 5. Error Handling

### 5.1 File Processing Errors

**Location**: `src/dsa110_contimg/pointing/monitor.py:log_pointing_from_file()`

```python
try:
    logger.info(f"Processing new file: {file_path}")
    info = load_pointing(file_path)
    # ... insertion logic ...
except Exception as e:
    logger.error(f"Failed to process file {file_path}: {e}")
```

**Characteristics**:
- Errors are logged but don't stop the monitor
- Missing fields (`mid_time`, `dec_deg`, `ra_deg`) prevent insertion
- File format errors (non-UVH5 files) are caught and logged

### 5.2 Missing Data Handling

**Location**: `src/dsa110_contimg/pointing/utils.py:load_pointing()`

The extraction handles missing fields gracefully:

- **Missing `phase_center_dec`**: Logs warning, `dec_deg` remains `None`
- **Missing `ha_phase_center`**: Logs warning, `ra_deg` remains `None`
- **Missing `time_array`**: `mid_time` remains `None`
- **Missing `Header` group**: Raises `ValueError`

If any required field (`mid_time`, `dec_deg`, `ra_deg`) is missing, the insertion is skipped.

---

## 6. Backfill Capability

### 6.1 Backfill Script

**Location**: `src/dsa110_contimg/pointing/backfill_pointing.py`

The backfill script processes historical files using a sparse sampling strategy:

1. **Sparse Sampling**: One file per day initially
2. **Jump Detection**: Detects declination jumps > threshold (default: 0.1 degrees)
3. **Granular Search**: Processes all files in intervals with jumps
4. **Database Insertion**: Uses same `INSERT OR REPLACE` logic

**Usage**:
```bash
python -m dsa110_contimg.pointing.backfill_pointing \
    --data-dir /data/incoming \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --start-date 2025-10-01 \
    --end-date 2025-10-23
```

**Rationale**: Sparse sampling reduces processing time for large date ranges while ensuring granular coverage around pointing changes.

---

## 7. Deployment Status

### 7.1 Current State

**Finding**: No systemd service found for pointing monitor

**Evidence**:
- No service file in `ops/systemd/` directory
- Monitor script exists but appears to be manual-run only
- No cron job or scheduled task found

**Available Services**:
- `contimg-stream.service`: Streaming converter (monitors `/data/incoming/` for conversion)
- `contimg-api.service`: API server
- `contimg-test-monitor.service`: Test monitoring (unrelated)

### 7.2 Manual Execution

The monitor can be run manually:

```bash
python -m dsa110_contimg.pointing.monitor \
    /data/incoming \
    /data/dsa110-contimg/state/products.sqlite3
```

**Requirements**:
- Python environment with `watchdog` library
- Write access to products database
- Read access to `/data/incoming/`

### 7.3 Recommended Deployment

**Option 1: Systemd Service** (Recommended)

Create `ops/systemd/contimg-pointing-monitor.service`:

```ini
[Unit]
Description=DSA-110 Pointing Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/data/dsa110-contimg/ops/systemd/contimg.env
WorkingDirectory=/data/dsa110-contimg
ExecStart=/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.pointing.monitor \
    ${CONTIMG_INPUT_DIR} \
    ${PIPELINE_STATE_DIR}/products.sqlite3
Restart=always
RestartSec=60
NoNewPrivileges=true
StandardOutput=append:/data/dsa110-contimg/state/logs/pointing-monitor.out
StandardError=append:/data/dsa110-contimg/state/logs/pointing-monitor.err

[Install]
WantedBy=multi-user.target
```

**Option 2: Integration with Streaming Converter**

The streaming converter (`contimg-stream.service`) already monitors `/data/incoming/`. Pointing extraction could be integrated into the conversion workflow to avoid duplicate file watching.

---

## 8. Limitations and Considerations

### 8.1 File Filtering Limitation

**Issue**: Only `_sb00.hdf5` files are monitored

**Impact**: 
- If `_sb00.hdf5` is missing or corrupted, pointing is not logged
- Other subbands (`_sb01.hdf5` through `_sb15.hdf5`) are ignored

**Mitigation**: 
- All subbands share the same pointing center
- Primary subband is typically the first to arrive
- Backfill script can recover missing entries

### 8.2 Time Format Handling

**Issue**: UVH5 files may use different time formats

**Current Solution**: Automatic format detection via `detect_casa_time_format()`

**Risk**: Very old or future dates may fail validation (year range: 2000-2100)

**Mitigation**: Format detection validates resulting dates against expected range

### 8.3 Missing Metadata Handling

**Issue**: UVH5 files may lack `phase_center_dec` or `ha_phase_center`

**Current Behavior**: 
- Logs warning
- Skips insertion if required fields missing
- Monitor continues running

**Impact**: Some observations may not have pointing logged

**Recommendation**: Consider fallback to MS file pointing if UVH5 metadata is missing

### 8.4 Database Connection Management

**Issue**: Single persistent SQLite connection

**Current Behavior**: Connection maintained for monitor lifetime

**Risk**: 
- Connection may timeout on long-running monitor
- No connection retry logic
- Database lock conflicts if multiple processes access same DB

**Mitigation**: 
- SQLite handles concurrent reads well
- Writes are serialized by SQLite
- Monitor commits immediately after each insertion

### 8.5 Recursive Monitoring Overhead

**Issue**: `watchdog` recursive monitoring can be resource-intensive

**Current Behavior**: Watches `/data/incoming/` recursively

**Risk**: 
- High memory usage on deep directory trees
- CPU overhead on frequent file creation
- Inotify limits on Linux systems

**Mitigation**: 
- Only processes specific file patterns (`_sb00.hdf5`, `.ms`)
- Minimal processing per file (header read only)
- Consider using `inotifywait` (kernel-level) for lower overhead

---

## 9. Integration Points

### 9.1 API Access

**Location**: `src/dsa110_contimg/api/data_access.py:fetch_pointing_history()`

The API provides access to pointing history:

```python
def fetch_pointing_history(db_path: str, start_mjd: float, end_mjd: float) -> List[PointingHistoryEntry]:
    """Fetch pointing history from the database."""
    with closing(_connect(Path(db_path))) as conn:
        rows = conn.execute(
            "SELECT timestamp, ra_deg, dec_deg FROM pointing_history WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
            (start_mjd, end_mjd),
        ).fetchall()
```

**Usage**: Dashboard and frontend can query pointing history for visualization

### 9.2 Cross-Matching with Transits

**Location**: `src/dsa110_contimg/pointing/crossmatch.py:find_transit_groups()`

Pointing history is used to cross-match calibrator transits with actual observations:

- Matches transit predictions with pointing history
- Finds observation groups near transit times
- Filters by declination tolerance

**Usage**: Identifies calibrator observations for calibration workflow

---

## 10. Recommendations

### 10.1 Immediate Actions

1. **Deploy Monitor Service**: Create systemd service for automatic monitoring
2. **Add Health Checks**: Monitor script should report health status
3. **Error Alerting**: Integrate with alerting system for persistent failures

### 10.2 Code Improvements

1. **Connection Pooling**: Use connection pool or context managers for database access
2. **Batch Inserts**: Consider batching multiple insertions for better performance
3. **Retry Logic**: Add retry logic for transient file access errors
4. **Metrics**: Add metrics for files processed, errors encountered, insertion rate

### 10.3 Architecture Improvements

1. **Integration**: Consider integrating pointing extraction into streaming converter workflow
2. **Alternative Monitoring**: Evaluate `inotifywait` for lower overhead
3. **Validation**: Add validation of extracted pointing values (range checks, sanity checks)
4. **Fallback**: Add fallback to MS file pointing if UVH5 metadata missing

### 10.4 Documentation

1. **Deployment Guide**: Document systemd service deployment
2. **Troubleshooting**: Document common issues and solutions
3. **Monitoring**: Document how to verify monitor is working correctly

---

## 11. Testing Recommendations

### 11.1 Unit Tests

- Test `load_pointing()` with various UVH5 file formats
- Test time format detection edge cases
- Test missing metadata handling
- Test RA calculation accuracy

### 11.2 Integration Tests

- Test file watcher with mock file creation
- Test database insertion and duplicate handling
- Test error recovery and logging

### 11.3 End-to-End Tests

- Test full workflow: file creation → extraction → database insertion
- Test backfill script with historical data
- Test API access to pointing history

---

## 12. Conclusion

The pointing monitoring system provides a functional solution for extracting and storing telescope pointing information from UVH5 visibility files. The implementation uses efficient header-only reading and automatic time format detection. However, the system is not currently deployed as a service and relies on manual execution.

**Strengths**:
- Efficient header-only extraction (no full file load)
- Automatic time format detection
- Error-tolerant (continues on failures)
- Backfill capability for historical data

**Weaknesses**:
- Not deployed as automated service
- Single file pattern dependency (`_sb00.hdf5`)
- No health monitoring or alerting
- Limited error recovery

**Priority Actions**:
1. Deploy as systemd service
2. Add health checks and monitoring
3. Consider integration with streaming converter
4. Add comprehensive error handling and retry logic

---

## References

- **Monitor Script**: `src/dsa110_contimg/pointing/monitor.py`
- **Pointing Utilities**: `src/dsa110_contimg/pointing/utils.py`
- **Database Schema**: `src/dsa110_contimg/database/products.py`
- **Backfill Script**: `src/dsa110_contimg/pointing/backfill_pointing.py`
- **API Access**: `src/dsa110_contimg/api/data_access.py`
- **Time Utilities**: `src/dsa110_contimg/utils/time_utils.py`


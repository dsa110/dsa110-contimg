# Generalization Analysis: Mosaic Workflow Stages

## Analysis Date: 2025-01-XX

## Overview

This document analyzes each stage of the mosaic-building workflow, identifies duplicate implementations, and proposes generalized versions that are not hyper-specific to single-use cases.

---

## Stage 1: Transit Finding / Calibrator Matching

### Current Implementations

1. **`scripts/find_latest_transit_group.py`** - Hyper-specific
   - Finds ONLY the most recent transit for a named calibrator
   - Searches backward through time
   - Returns single transit time
   - **Use case**: Testing, manual queries

2. **`scripts/find_daily_transit_groups.py`** - Moderate generalization
   - Finds ALL daily transits for a calibrator
   - Scans all groups recursively
   - Returns list of transit matches
   - **Use case**: Finding multiple transit opportunities

3. **`scripts/crossmatch_transits_pointings.py`** - More generalized
   - Cross-matches transit times with actual pointing data
   - Uses products DB for pointing history
   - Handles multiple transits over time window
   - **Use case**: Finding transits with available data

4. **`src/dsa110_contimg/calibration/catalogs.py::calibrator_match()`** - Core function
   - Matches calibrators to pointing at specific time
   - Returns top-N matches within radius
   - **Use case**: Real-time calibrator detection

### Duplication Issues

- Transit calculation duplicated: `previous_transits()` called in multiple scripts
- Group scanning duplicated: Each script implements its own file discovery
- Dec matching logic duplicated: Multiple implementations check declination tolerance

### Generalized Version: **Calibrator Transit Monitor**

**Components:**

1. **Transit Time Calculator** (already exists: `schedule.previous_transits()`)
   - Input: RA (deg), start_time, n_transits
   - Output: List of transit times
   - **Generalization**: Works for any source, not just calibrators

2. **Pointing Monitor** (extract from HDF5 headers)
   - Extract pointing declination from UVH5 file headers
   - Track pointing history over time
   - Store in database (`pointing_history` table exists)
   - **Generalization**: Monitor ALL pointings, not just calibrator transits

3. **Data Availability Monitor** (scan `/data/incoming/`)
   - Monitor what time ranges have observational data
   - Track group completeness (16 subbands)
   - Store in database (`ingest_queue` table exists)
   - **Generalization**: Track ALL data availability, not just transit windows

4. **Transit-Data Matcher** (selection tool)
   - Query: "Find transits of source X where we have data"
   - Query: "Find most recent transit of source X with data"
   - Query: "Find all transits in time window [T1, T2] with data"
   - **Generalization**: Generic query interface, not hardcoded to "latest"

**Proposed API:**

```python
class TransitDataMatcher:
    def __init__(self, catalogs: List[str], pointing_db: Path, ingest_db: Path):
        """Initialize with catalogs and database paths."""
        
    def find_transits_with_data(
        self,
        source_name: str,
        *,
        start_time: Optional[Time] = None,
        end_time: Optional[Time] = None,
        n_transits: int = 10,
        dec_tolerance_deg: float = 2.0,
        require_complete_groups: bool = True
    ) -> List[TransitMatch]:
        """Find transits where we have observational data."""
        
    def get_latest_transit_with_data(
        self,
        source_name: str,
        *,
        max_days_back: int = 14,
        dec_tolerance_deg: float = 2.0
    ) -> Optional[TransitMatch]:
        """Get most recent transit with available data."""
        
    def get_upcoming_transits_with_data(
        self,
        source_name: str,
        *,
        hours_ahead: int = 24,
        dec_tolerance_deg: float = 2.0
    ) -> List[TransitMatch]:
        """Get upcoming transits where we will have data."""
```

**Benefits:**
- Single source of truth for transit-data matching
- Reusable for any source (calibrators, science targets)
- Database-driven (no recursive file scanning)
- Supports multiple query patterns

---

## Stage 2: Group Discovery

### Current Implementations

1. **`hdf5_orchestrator.find_subband_groups()`** - Core implementation
   - Time-window based discovery
   - Groups by timestamp tolerance (±30s default)
   - Returns complete groups only
   - **Use case**: Conversion pipeline

2. **`build_transit_mosaic.py::_file_list_for_time()`** - Hardcoded
   - Assumes exact timestamp format
   - Hardcoded to 16 subbands
   - No tolerance handling
   - **Use case**: Transit mosaic only

3. **`find_daily_transit_groups.py::_scan_groups_recursive()`** - Recursive scan
   - Scans entire directory tree
   - Groups by expected subband codes
   - Stores in dictionary
   - **Use case**: Transit finding

4. **`scripts/crossmatch_transits_pointings.py::_scan_complete_groups()`** - Another recursive scan
   - Similar logic to above
   - Duplicates group discovery code

### Duplication Issues

- File discovery logic duplicated: glob patterns, timestamp parsing, subband extraction
- Grouping logic duplicated: timestamp tolerance, completeness checking
- Subband code extraction duplicated: regex patterns in multiple files

### Generalized Version: **Subband Group Discovery Service**

**Components:**

1. **File Scanner** (extract common logic)
   - Scan directory for UVH5 files
   - Extract metadata: timestamp, subband code, pointing declination
   - Cache results in database
   - **Generalization**: Works for any directory, not just `/data/incoming`

2. **Group Assembler** (extract common logic)
   - Group files by timestamp (tolerance-based)
   - Verify completeness (required subbands)
   - Handle partial groups gracefully
   - **Generalization**: Configurable subband requirements, not hardcoded to 16

3. **Time Window Query** (database-driven)
   - Query groups by time range
   - Query groups by pointing declination
   - Query groups by completeness status
   - **Generalization**: Generic query interface

**Proposed API:**

```python
class SubbandGroupDiscovery:
    def __init__(self, input_dir: Path, ingest_db: Path):
        """Initialize with directory and database."""
        
    def scan_directory(self, *, force_refresh: bool = False) -> int:
        """Scan directory and update database. Returns count of groups found."""
        
    def find_groups_in_window(
        self,
        start_time: Time,
        end_time: Time,
        *,
        tolerance_s: float = 30.0,
        require_complete: bool = True,
        required_subbands: Optional[List[str]] = None
    ) -> List[SubbandGroup]:
        """Find groups in time window."""
        
    def get_group_by_timestamp(
        self,
        timestamp: Time,
        *,
        tolerance_s: float = 30.0
    ) -> Optional[SubbandGroup]:
        """Get specific group by timestamp."""
        
    def get_groups_by_declination(
        self,
        dec_deg: float,
        *,
        tolerance_deg: float = 2.0,
        start_time: Optional[Time] = None,
        end_time: Optional[Time] = None
    ) -> List[SubbandGroup]:
        """Get groups matching pointing declination."""
```

**Benefits:**
- Single implementation for all group discovery
- Database-backed (no repeated file scanning)
- Configurable (not hardcoded to 16 subbands)
- Reusable across all workflows

---

## Stage 3: Conversion (UVH5 → MS)

### Current Implementations

1. **`hdf5_orchestrator.convert_subband_groups_to_ms()`** - Strategy orchestrator
   - Writer selection (auto/monolithic/direct-subband)
   - Staging strategy (tmpfs/SSD)
   - Full pipeline integration
   - **Use case**: Streaming converter, batch processing

2. **`direct_subband.write_ms_from_subbands()`** - Direct writer
   - Parallel per-subband writes
   - Concatenation
   - **Use case**: Large groups, performance-critical

3. **`pyuvdata_monolithic.write_ms()`** - Monolithic writer
   - Single UVData object write
   - **Use case**: Small groups, simplicity

4. **`uvh5_to_ms.convert_single_file()`** - Standalone converter
   - Single file conversion
   - **Use case**: Testing, manual conversion

5. **Multiple scripts have `_write_ms_group_via_uvh5_to_ms()`** - Duplicated wrappers
   - `build_transit_mosaic.py`
   - `build_calibrator_transit_offsets.py`
   - `build_central_calibrator_group.py`
   - `image_groups_in_timerange.py`
   - `run_next_field_after_central.py`

### Duplication Issues

- Multiple wrapper functions that do the same thing
- Each script imports different conversion modules
- Inconsistent error handling
- Inconsistent staging/tmpfs usage

### Generalized Version: **Unified Conversion Service**

**Components:**

1. **Conversion Orchestrator** (already exists: `hdf5_orchestrator`)
   - Writer selection logic
   - Staging strategy
   - Error handling
   - **Status**: Already generalized, but not used consistently

2. **Conversion Wrapper** (create unified wrapper)
   - Single entry point for all conversion needs
   - Consistent interface across scripts
   - Automatic writer selection
   - Automatic staging detection

**Proposed API:**

```python
class UnifiedConverter:
    def __init__(
        self,
        *,
        writer: str = "auto",
        stage_to_tmpfs: Optional[bool] = None,
        scratch_dir: Optional[Path] = None
    ):
        """Initialize converter with options."""
        
    def convert_group(
        self,
        file_list: List[Path],
        output_ms: Path,
        *,
        telescope_name: Optional[str] = None,
        phase_to_meridian: bool = True
    ) -> Path:
        """Convert subband group to MS. Returns output path."""
        
    def convert_groups_batch(
        self,
        groups: List[List[Path]],
        output_dir: Path,
        *,
        max_workers: int = 1
    ) -> List[Path]:
        """Convert multiple groups in parallel."""
```

**Benefits:**
- Single conversion interface
- Consistent behavior across all scripts
- Automatic optimization (writer selection, staging)
- Eliminates duplicate wrapper code

---

## Stage 4: Calibration Application

### Current Implementations

1. **`calibration.applycal.apply_to_target()`** - Core function
   - CASA applycal wrapper
   - Handles interp defaults
   - **Use case**: All calibration application

2. **`imaging.worker._apply_and_image()`** - Combined workflow
   - Applies calibration + images
   - **Use case**: Worker pipeline

3. **`api.job_runner.run_apply_job()`** - Job runner
   - Background job execution
   - Database updates
   - **Use case**: Control panel API

4. **Multiple scripts apply calibration inline** - Duplicated logic
   - `build_calibrator_transit_offsets.py`
   - `image_groups_in_timerange.py`
   - `run_next_field_after_central.py`
   - All have similar applycal + verification code

### Duplication Issues

- Calibration table lookup duplicated: Multiple scripts query `cal_registry`
- Verification logic duplicated: Check CORRECTED_DATA non-zero
- Error handling duplicated: Similar try/except blocks

### Generalized Version: **Calibration Application Service**

**Components:**

1. **Calibration Table Lookup** (extract to service)
   - Query registry by MS mid-MJD
   - Return active applylist
   - Handle validity windows
   - **Generalization**: Works for any MS, not just specific workflows

2. **Apply Service** (wrap existing function)
   - Apply tables with error handling
   - Verify CORRECTED_DATA populated
   - Update database status
   - **Generalization**: Reusable apply step

**Proposed API:**

```python
class CalibrationApplicationService:
    def __init__(self, registry_db: Path, products_db: Path):
        """Initialize with database paths."""
        
    def get_active_caltables(
        self,
        ms_path: Path,
        *,
        set_name: Optional[str] = None
    ) -> List[Path]:
        """Get active calibration tables for MS."""
        
    def apply_calibration(
        self,
        ms_path: Path,
        *,
        caltables: Optional[List[Path]] = None,
        set_name: Optional[str] = None,
        verify: bool = True,
        update_db: bool = True
    ) -> bool:
        """Apply calibration to MS. Returns success status."""
        
    def verify_calibration(
        self,
        ms_path: Path
    ) -> bool:
        """Verify CORRECTED_DATA is populated."""
```

**Benefits:**
- Single source for calibration application
- Consistent verification logic
- Database updates handled automatically
- Reusable across all workflows

---

## Stage 5: Imaging

### Current Implementations

1. **`imaging.cli.image_ms()`** - Core imaging function
   - CASA tclean wrapper
   - Auto-detects CORRECTED_DATA
   - NVSS seeding support
   - **Use case**: All imaging workflows

2. **`imaging.worker._apply_and_image()`** - Combined workflow
   - Calibration + imaging
   - **Use case**: Worker pipeline

3. **`build_transit_mosaic.py::_image_ms()`** - Wrapper
   - Calls `image_ms()` with specific parameters
   - Hardcoded settings
   - **Use case**: Transit mosaic only

4. **Multiple scripts call `image_ms()` directly** - Consistent usage
   - All use same function
   - Different parameter sets
   - **Status**: Already generalized, but parameters vary

### Duplication Issues

- Parameter sets duplicated: Each script hardcodes imaging parameters
- Image naming duplicated: Various naming conventions
- Product registration duplicated: Multiple scripts insert into products DB

### Generalized Version: **Imaging Service**

**Components:**

1. **Imaging Presets** (configuration-driven)
   - Quick-look preset
   - Full-quality preset
   - Transit-mosaic preset
   - **Generalization**: Configurable presets, not hardcoded

2. **Imaging Service** (wrap existing function)
   - Apply preset or custom parameters
   - Consistent naming conventions
   - Automatic product registration
   - **Generalization**: Reusable imaging step

**Proposed API:**

```python
class ImagingService:
    def __init__(self, products_db: Path):
        """Initialize with products database."""
        
    def image_ms(
        self,
        ms_path: Path,
        output_dir: Path,
        *,
        preset: str = "quick",
        **kwargs
    ) -> List[Path]:
        """Image MS with preset or custom parameters. Returns artifact paths."""
        
    def get_preset(self, name: str) -> Dict[str, Any]:
        """Get imaging preset configuration."""
```

**Benefits:**
- Consistent imaging parameters
- Configurable presets
- Automatic product registration
- Reusable across workflows

---

## Stage 6: Mosaic Planning & Building

### Current Implementations

1. **`mosaic.cli.cmd_plan()`** - Mosaic planner
   - Queries products DB for tiles
   - Time-window filtering
   - Creates mosaic plan record
   - **Use case**: All mosaics

2. **`mosaic.cli.cmd_build()`** - Mosaic builder
   - Checks tile consistency
   - CASA immath combination
   - FITS export
   - **Use case**: All mosaics

3. **`build_transit_mosaic.py`** - Hardcoded workflow
   - Hardcoded time window (last 2 hours)
   - Hardcoded mosaic name format
   - Calls CLI via subprocess
   - **Use case**: Transit mosaic only

### Duplication Issues

- Time window calculation duplicated: Multiple scripts compute since/until
- Mosaic naming duplicated: Various naming conventions
- Subprocess calls: Should use Python API instead

### Generalized Version: **Mosaic Service**

**Components:**

1. **Mosaic Planner** (enhance existing CLI)
   - Flexible time window queries
   - Configurable tile selection
   - **Generalization**: Works for any time range, not just recent

2. **Mosaic Builder** (enhance existing CLI)
   - Python API (not just CLI)
   - Multiple combination methods
   - **Generalization**: Reusable building step

**Proposed API:**

```python
class MosaicService:
    def __init__(self, products_db: Path):
        """Initialize with products database."""
        
    def plan_mosaic(
        self,
        name: str,
        *,
        since: Optional[float] = None,
        until: Optional[float] = None,
        pbcor_only: bool = True,
        method: str = "mean"
    ) -> str:
        """Plan mosaic from products DB. Returns mosaic name."""
        
    def build_mosaic(
        self,
        name: str,
        output_path: Path,
        *,
        verify_consistency: bool = True
    ) -> Path:
        """Build mosaic from plan. Returns output path."""
        
    def create_transit_mosaic(
        self,
        transit_time: Time,
        window_minutes: int = 60,
        *,
        name: Optional[str] = None
    ) -> Path:
        """Create mosaic for transit time window."""
```

**Benefits:**
- Python API (not just CLI)
- Flexible time window queries
- Consistent naming conventions
- Reusable for any mosaic type

---

## Summary: Generalized Architecture

### Proposed Service Layer

```
┌─────────────────────────────────────────────────┐
│          TransitDataMatcher Service             │
│  - Transit time calculation                    │
│  - Pointing history from HDF5 headers          │
│  - Data availability monitoring                │
│  - Transit-data matching queries               │
└─────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────┐
│      SubbandGroupDiscovery Service              │
│  - File scanning (database-backed)             │
│  - Group assembly (tolerance-based)            │
│  - Time window queries                         │
└─────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────┐
│         UnifiedConverter Service                │
│  - Writer selection (auto/manual)              │
│  - Staging strategy (tmpfs/SSD)                │
│  - Batch conversion                            │
└─────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────┐
│    CalibrationApplicationService                │
│  - Caltable lookup (registry-based)            │
│  - Apply calibration                           │
│  - Verification                                │
└─────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────┐
│           ImagingService                        │
│  - Imaging presets                              │
│  - Consistent parameters                       │
│  - Product registration                        │
└─────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────┐
│            MosaicService                        │
│  - Mosaic planning (flexible queries)          │
│  - Mosaic building (Python API)                │
│  - Transit mosaic helper                       │
└─────────────────────────────────────────────────┘
```

### Migration Path

1. **Phase 1**: Extract common functions to services
   - TransitDataMatcher
   - SubbandGroupDiscovery
   - CalibrationApplicationService

2. **Phase 2**: Update scripts to use services
   - Replace duplicate code with service calls
   - Maintain backward compatibility

3. **Phase 3**: Add new generalized workflows
   - Transit mosaic builder using services
   - Other mosaic types using services

### Benefits of Generalization

1. **Reusability**: Services work for any workflow, not just specific use cases
2. **Consistency**: Single implementation ensures consistent behavior
3. **Maintainability**: Fix bugs once, not in multiple places
4. **Testability**: Services can be tested independently
5. **Database-driven**: Reduces file system scanning overhead
6. **Query flexibility**: Supports multiple query patterns, not just "latest"


# Do you see any glaring weaknesses with the pipeline?

Based on my thorough analysis of the dsa110-contimg repository, I can identify several significant weaknesses and potential failure modes in the pipeline design:

## 1. **Critical Calibration Validity Gap**

The most glaring weakness is the **forward-only validity window** for calibration tables. When a calibrator is observed and registered:

```python
register_set_from_prefix(
    ...
    valid_start_mjd=mid_mjd,  # Calibrator observation time
    valid_end_mjd=None,        # Open-ended!
)
```

**Problem**: Science observations that occur **before** the calibrator transit have no valid calibration. The system only looks for calibrations where `valid_start_mjd <= target_mjd`, meaning:

- **At pipeline startup**: No calibrations exist yet → all science data goes uncalibrated
- **Between calibrator transits**: Data observed in the ~23 hours before the daily calibrator uses yesterday's calibration (fine), but what about the first observations of the day?
- **After maintenance/restart**: Calibration database might be empty

**Evidence from code** (`registry.py`):

```python
WHERE status = 'active'
  AND (valid_start_mjd IS NULL OR valid_start_mjd <= ?)  # Target must be AFTER cal
  AND (valid_end_mjd IS NULL OR valid_end_mjd >= ?)
```

**Consequence**: Early observations each day may be processed with stale calibrations or skip calibration entirely.

**Fix needed**: Implement **bidirectional validity windows** where calibrations apply ±12 hours from the calibrator observation, or use a "next-nearest" selection strategy.

## 2. **No Calibration Interpolation**

The pipeline uses **discrete calibration snapshots** rather than interpolating between calibrator observations. From `applycal.py`:

```python
# Interpolation defaults
if "bpcal" in low or "bandpass" in low:
    interp = "nearest"  # No interpolation for bandpass
else:
    interp = "linear"   # Linear for gains
```

**Problem**: Even with `interp='linear'`, this only interpolates **within a single calibration table's time axis**. The pipeline doesn't interpolate **between different calibration observations** (e.g., between yesterday's 3pm calibrator and today's 3pm calibrator).

**Consequence**:

- Sudden jumps in calibration at each calibrator update
- No smooth tracking of atmospheric/instrumental drift
- 24-hour validity is quite long for L-band observations

**Industry standard**: VLA uses interpolation between calibrator scans every ~30-60 minutes. DSA-110's daily calibration is extremely sparse.

## 3. **Single Calibrator Strategy is Fragile**

The system relies on **one calibrator per day** passing through the beam:

```python
# From NSFRB documentation
"daily calibrator and pulsar observations"
```

**Problems**:

a) **No redundancy**: If the calibrator observation fails (RFI, weather, system glitch), the entire day has no fresh calibration

b) **No declination tracking**: The code shows drift-scan at **fixed declination** (δ=71.6° for NSFRB, variable for continuum imaging). If the pipeline pointing changes, the previous calibrator may be at wrong declination for optimal beam response

c) **Single field calibration**: No checking for field-dependent effects (ionosphere, beam pattern variations)

**Evidence**: The `has_calibrator()` function searches within `radius_deg=2.0` of meridian, but there's no fallback or secondary calibrator strategy.

## 4. **Race Condition in Calibration Application**

The streaming converter applies calibration **immediately after conversion**:

```python
# In _worker_loop (streaming_converter.py)
# 1. Convert MS
# 2. Solve calibration IF calibrator MS
# 3. Register calibration tables
# 4. Apply calibration to target MS  ← RACE CONDITION
```

**Problem**: Target observations that arrive **during or just after** a calibrator observation might query the registry **before** the new calibration is registered, getting stale solutions.

**Timing**:

- t=0: Calibrator observation completes, files arrive
- t=5s: Calibrator MS converted
- t=35s: Calibration solved (bandpass ~31s + gains ~10s)
- t=40s: Calibration registered in DB
- **BUT**: Target observations from t=0 to t=40s already processed with old calibration!

**Fix needed**: Implement a calibration queue or lazy evaluation where targets check for newer calibrations before imaging.

## 5. **No Automated Quality Assessment of Calibrations**

When calibrations are solved, there's **no automated QA** before registration:

```python
def solve_calibration_for_ms(ms_path, ...) -> Tuple[bool, Optional[str]]:
    # Runs calibration
    # Returns (True, None) if completes
    # No quality metrics checked!
```

**Problems**:

- No SNR thresholds on calibration solutions
- No flagging statistics checks
- No comparison with previous calibrations
- Bad calibrations get registered and applied automatically

The `quality_metrics` field exists in the schema but isn't populated:

```python
quality_metrics TEXT  # JSON: SNR, flagged_fraction, etc.
# But solve_calibration_for_ms doesn't populate this!
```

**Consequence**: A poor calibrator observation (low SNR, heavy RFI) produces bad solutions that corrupt subsequent science data.

## 6. **Overlapping Calibration Set Handling is Weak**

When multiple calibration sets overlap in time:

```python
# From registry.py
if len(all_matching_sets) > 1:
    # Logs warnings about incompatibility
    # But still selects newest set!
    logger.warning("Overlapping calibration sets...")
```

**Problem**: The system **warns but proceeds** with potentially incompatible calibrations. No actual conflict resolution:

- Different reference antennas → phase reference inconsistency
- Different calibrator fields → amplitude scale mismatch
- System picks "newest" without validating quality

**Better approach**:

1. Prevent overlapping registrations entirely
2. Or implement smart merging (prefer same refant/field)
3. Or mark conflicts as failed and require manual intervention

## 7. **Catastrophic: No Transactional Safety in Multi-Step Processing**

The worker loop has **no rollback capability**:

```python
# _worker_loop does:
# 1. Convert MS ✓
# 2. Update products DB (status=converted) ✓
# 3. Solve calibration (maybe fails) ✗
# 4. Apply calibration (maybe fails) ✗
# 5. Image MS (maybe fails) ✗
# 6. Update products DB (status=done) ✓

# If step 4 fails, MS is marked "converted" but never imaged
# If step 5 fails, MS has calibration but no image
# No mechanism to retry from failure point!
```

**Evidence from code**:

```python
try:
    image_ms(...)
except (RuntimeError, OSError, subprocess.SubprocessError):
    log.error("imaging failed for %s", ms_path, exc_info=True)
    # No database update! MS stuck in limbo
```

**Consequence**:

- Failed operations leave MS in inconsistent states
- Retrying requires manual database manipulation
- No automatic recovery from partial failures

**Fix needed**: Implement proper state machine with:

- Atomic transitions between states
- Failure states that can be retried
- Checkpointing for expensive operations

## 8. **Inadequate RFI Mitigation Strategy**

The pipeline has minimal RFI handling:

```python
caltables = run_calibrator(
    ms_path,
    cal_field,
    refant,
    do_flagging=True,  # What does this actually do?
    do_k=do_k,
)
```

**Problems**:

a) **No pre-flagging**: Data isn't flagged for RFI before calibration solve
b) **No RFI statistics tracking**: No metrics on what percentage of data is RFI
c) **No adaptive strategies**: Heavy RFI events aren't detected or handled specially

The `do_flagging=True` parameter is opaque - there's no visible RFI detection/mitigation algorithm in the calibration code.

**Industry standard**: Modern pipelines (LOFAR, MeerKAT) use sophisticated RFI detection (AOFlagger, tricolour) **before** calibration.

## 9. **File I/O Bottleneck Without Proper Staging**

The conversion strategy shows concerning I/O patterns:

```python
# Storage hierarchy
/data/           # HDD - slow, persistent
/stage/          # SSD - fast
/dev/shm/        # tmpfs - fastest, volatile

# But conversion writes directly to /stage/ or /data/
# No guaranteed use of /dev/shm/ staging
```

**Problems**:

a) **Optional tmpfs staging**: `--stage-to-tmpfs` is optional, not mandatory
b) **No I/O bandwidth management**: Multiple conversions can saturate network/disk
c) **Subprocess mode bypasses path_mapper**: Files written flat then reorganized (double I/O!)

**Evidence**:

```python
if getattr(args, "use_subprocess", False):
    # Subprocess mode: compute organized path and move if needed
    ms_path_flat = os.path.join(args.output_dir, base + ".ms")
    # ... later ...
    organized_path = organize_ms_file(ms_path_obj, ...)  # MOVE operation!
```

**Consequence**: Unnecessary disk I/O during high-ingest periods could cause dropped observations.

## 10. **No Disk Space Monitoring or Cleanup**

The pipeline produces large data volumes but has **minimal housekeeping**:

```python
# housekeeping.py exists but only handles:
# - Recovering stale queue entries
# - Removing old stream_* temp directories
# - NOT removing old MS files or images!
```

**Problems**:

a) **No disk quota enforcement**: Pipeline will fill disk until failure
b) **No automatic archival**: Old products aren't moved to tape/cold storage
c) **No cleanup policies**: When to delete calibrator MS vs science MS?

**Consequence**: Operators must manually monitor disk usage and delete files, risking accidental deletion of important data.

## 11. **Weak Pointing Change Detection**

The pointing tracker feature is **optional and fragile**:

```python
try:
    from dsa110_contimg.pipeline.precompute import get_pointing_tracker
    HAS_POINTING_TRACKER = True
except ImportError:
    HAS_POINTING_TRACKER = False  # Feature silently disabled!
```

**Problems**:

a) **Import failure = silent degradation**: If precompute module has issues, pointing tracking just disappears
b) **No alerting on pointing changes**: When declination changes, only a log message
c) **No calibration invalidation**: Old calibrations aren't retired when pointing changes

**Expected behavior**: Pointing change should:

1. Force new calibrator observation
2. Invalidate previous calibrations (different beam pattern)
3. Alert operators to potential issues

## 12. **Subprocess vs In-Process Inconsistency**

The pipeline has **two execution paths** with different behaviors:

```python
if getattr(args, "use_subprocess", False):
    # Path A: Shell out to hdf5_orchestrator
    cmd = [sys.executable, "-m", "dsa110_contimg.conversion.strategies.hdf5_orchestrator", ...]
    subprocess.run(cmd, ...)
else:
    # Path B: Direct Python function call
    convert_subband_groups_to_ms(...)
```

**Problems**:

a) **Different error handling**: Subprocess errors return exit codes, in-process raises exceptions
b) **Different resource limits**: Subprocess inherits system limits, in-process shares parent's memory
c) **Different path organization**: Subprocess writes flat then reorganizes (extra I/O)
d) **Testing complexity**: Need to test both paths independently

**Symptom of**: Architectural uncertainty about stability vs. performance tradeoffs.

## 13. **Inadequate Observability**

The monitoring is **primitive**:

```python
if getattr(args, "monitoring", False):
    # Only logs queue stats every N seconds
    log.info("Queue stats: %s", stats)
```

**Missing**:

- **Prometheus/Grafana metrics**: No time-series performance data
- **Alert system**: No automated alerts on failures
- **Data quality dashboards**: Operators can't see calibration quality trends
- **Throughput metrics**: No visibility into conversion/imaging rates vs incoming data rate

**Consequence**: Problems only discovered reactively when science users complain about data quality.

## 14. **Database Schema Allows Inconsistent States**

The unified database has **no foreign key constraints**:

```sql
CREATE TABLE calibration_tables (
    source_ms_path TEXT,  -- No FK to ms_index!
    ...
)

CREATE TABLE images (
    ms_path TEXT,  -- No FK to ms_index!
    ...
)
```

**Problems**:

a) **Orphaned records**: Calibration tables can reference non-existent MS files
b) **Cascade deletes impossible**: Deleting an MS doesn't clean up related records
c) **Referential integrity violations**: Database can't enforce relationships

**Fix**: Add proper foreign keys and ON DELETE CASCADE policies.

## 15. **Mosaic Creation Trigger Logic Has Race Conditions**

The mosaic grouping uses **brittle time-window logic**:

```python
# check_for_complete_group looks for 12 MS files in ±55 minute window
# But what if observations span midnight?
# What if there's a gap in observations?
```

**Problems**:

a) **Arbitrary time window**: 55 minutes works until it doesn't (observing gaps)
b) **No declination grouping**: Mosaics could mix different pointing positions
c) **Sliding window overlap**: 3 MS overlap seems arbitrary, not scientifically justified

**Consequence**: Mosaics may group incompatible observations or miss valid groupings.

---

## Summary of Critical Weaknesses

**Tier 1 (Data Loss Risk)**:

1. Calibration validity gap (pre-calibrator observations)
2. No transactional safety in multi-step processing
3. Race condition in calibration application
4. No disk space monitoring

**Tier 2 (Data Quality Risk)**: 5. No calibration interpolation (24-hour validity too long) 6. No automated calibration QA 7. Inadequate RFI mitigation 8. Single calibrator strategy (no redundancy)

**Tier 3 (Operational Risk)**: 9. Weak overlapping calibration handling 10. File I/O bottleneck potential 11. Subprocess vs in-process inconsistency 12. Inadequate observability

**Tier 4 (Technical Debt)**: 13. Weak pointing change detection 14. Database schema lacks constraints 15. Mosaic trigger logic fragility

The pipeline is **functional for a development/commissioning phase** but would benefit significantly from hardening before sustained science operations, particularly around calibration validity windows, quality assessment, and transactional consistency.

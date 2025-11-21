# Temporal Flagging Tracking System

**Date:** 2025-11-19  
**Type:** Implementation Guide  
**Status:** ✅ Complete

---

## Overview

The DSA-110 pipeline now includes **temporal flagging tracking** that captures
flag states at each critical phase of the calibration pipeline. This enables
**definitive diagnosis** of why specific SPWs fail calibration, eliminating the
guesswork that comes from examining only post-calibration states.

### Problem Solved

**Before:** When examining a calibrated MS, we could see that SPWs 9, 14, 15
were 100% flagged, but couldn't determine:

- Were they 100% flagged BEFORE calibration (Phase 1)?
- Or did calibration fail, causing applycal to flag them 100% (Phase 3)?

**After:** The pipeline now captures snapshots at:

- **Phase 1:** After pre-calibration flagging (RFI, zeros, etc.)
- **Phase 2:** After calibration solve (before applycal)
- **Phase 3:** After calibration application (applycal)

Comparing these snapshots provides **definitive answers** about failure causes.

---

## Architecture

### Components

1. **`flagging_temporal.py`** - Core temporal tracking module
   - Data structures: `FlaggingSnapshot`, `SPWFlaggingStats`
   - Snapshot capture: `capture_flag_snapshot()`
   - Comparison: `compare_flag_snapshots()`
   - Diagnosis: `diagnose_spw_failure()`
   - Database storage: `store_temporal_analysis_in_database()`

2. **`stages_impl.py`** - Pipeline integration
   - Captures snapshots after Phase 1, 2, and 3
   - Performs automatic comparison and diagnosis
   - Logs results and stores in database

3. **`diagnose_spw_failures.py`** - CLI diagnostic tool
   - Retrospective analysis of already-calibrated MSs
   - Manual comparison and diagnosis

4. **Database** - `temporal_flagging` table in `products.sqlite3`
   - Stores phase1_snapshot, phase3_snapshot, comparison as JSON
   - Enables frontend display of temporal flag evolution

---

## Data Flow

```
MS (unflagged)
    ↓
[Phase 1: Pre-calibration Flagging]
    - RFI flagging (AOFlagger)
    - Zero flagging
    - Channel-level analysis
    → SNAPSHOT CAPTURED (phase1_post_rfi)
    ↓
[Phase 2: Calibration Solve]
    - K table solve
    - BP table solve
    - G table solve
    → SNAPSHOT CAPTURED (phase2_post_solve)
    → (NOTE: Flags unchanged from Phase 1)
    ↓
[Phase 3: Calibration Application]
    - applycal runs
    - SPWs without solutions → 100% flagged by CASA
    → SNAPSHOT CAPTURED (phase3_post_applycal)
    ↓
[Analysis]
    - Compare phase1 vs phase3
    - Identify newly fully-flagged SPWs
    - Diagnose root causes
    → STORE IN DATABASE
    → LOG RESULTS
```

---

## Example Usage

### Automatic (During Calibration)

Temporal tracking is **automatically enabled** in the pipeline. Logs will show:

```
✓ Phase 1 flag snapshot captured: 12.3% overall flagging

Calibration solve complete. Generated 3 tables...

✓ Phase 2 flag snapshot captured: 12.3% overall flagging

Applying calibration...

✓ Phase 3 flag snapshot captured: 18.7% overall flagging

================================================================================
TEMPORAL FLAGGING ANALYSIS
================================================================================
Flagging Comparison: phase1_post_rfi → phase3_post_applycal
================================================================================

SPWs that became 100% flagged: [9, 14, 15]

Flagging changes per SPW:
--------------------------------------------------------------------------------
SPW  9:  85.2% → 100.0% (+14.8%)
         Refant: 100.0% → 100.0% (+0.0%)
SPW 14:  92.1% → 100.0% (+7.9%)
         Refant: 100.0% → 100.0% (+0.0%)
SPW 15:  88.5% → 100.0% (+11.5%)
         Refant: 100.0% → 100.0% (+0.0%)
================================================================================

DIAGNOSIS of newly fully-flagged SPWs:
--------------------------------------------------------------------------------

SPW 9:
  Pre-calibration flagging: 85.2%
  Pre-calibration refant flagging: 100.0%
  Post-applycal flagging: 100.0%
  → CAUSE: Reference antenna 103 was 100% flagged pre-calibration in SPW 9,
    making calibration solve impossible
```

### Manual (Retrospective Analysis)

For already-calibrated MSs:

```bash
python /data/dsa110-contimg/scripts/diagnose_spw_failures.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103 \
  --cal-prefix /stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23 \
  --output diagnosis.txt
```

**Note:** Retrospective analysis can only show the CURRENT (post-applycal)
state. To get definitive pre-calibration percentages, re-run calibration with
the new temporal tracking enabled.

---

## Database Schema

### `temporal_flagging` Table

```sql
CREATE TABLE IF NOT EXISTS temporal_flagging (
    ms_path TEXT PRIMARY KEY,
    phase1_snapshot TEXT,          -- JSON: FlaggingSnapshot
    phase3_snapshot TEXT,          -- JSON: FlaggingSnapshot
    comparison TEXT,               -- JSON: comparison results
    newly_fully_flagged_spws TEXT, -- JSON: list of SPW IDs
    timestamp TEXT                 -- ISO format datetime
);
```

### Accessing from Frontend

```typescript
// Example API endpoint to add:
// GET /api/temporal-flagging/<ms_path>

interface TemporalFlaggingData {
  ms_path: string;
  phase1_snapshot: FlaggingSnapshot;
  phase3_snapshot: FlaggingSnapshot;
  comparison: {
    newly_fully_flagged_spws: number[];
    flag_increase_per_spw: Record<
      number,
      {
        before: number;
        after: number;
        increase_pct: number;
      }
    >;
    refant_flag_changes: Record<
      number,
      {
        before: number;
        after: number;
        increase_pct: number;
      }
    >;
  };
  timestamp: string;
}

// Usage in CalibrationSPWPanel:
const { data: temporalData } = useTemporalFlagging(msPath);

// Display:
// - Pre-calibration vs post-calibration flagging per SPW
// - Highlight SPWs that became 100% flagged
// - Show refant flagging changes
// - Display definitive diagnosis for failed SPWs
```

---

## Key Files

### Backend

- **`src/dsa110_contimg/src/dsa110_contimg/calibration/flagging_temporal.py`**
  - Core module with all temporal tracking functionality
  - ~700 lines including data structures, capture, comparison, diagnosis

- **`src/dsa110_contimg/src/dsa110_contimg/pipeline/stages_impl.py`**
  - Integration points at lines:
    - ~847-868: Phase 1 snapshot capture
    - ~973-1000: Phase 2 snapshot capture
    - ~1276-1297 & ~1337-1358: Phase 3 snapshot capture
    - ~1362-1403: Temporal analysis and database storage

- **`scripts/diagnose_spw_failures.py`**
  - CLI tool for retrospective analysis
  - ~250 lines with comprehensive help and examples

### Database

- **`state/products.sqlite3`**
  - Table: `temporal_flagging`
  - Auto-created on first use

### Frontend (Future)

- **`frontend/src/api/queries.ts`**
  - Add `useTemporalFlagging(msPath)` hook

- **`frontend/src/components/CalibrationSPWPanel.tsx`**
  - Update to display temporal flag evolution
  - Show phase1 vs phase3 comparison
  - Highlight newly flagged SPWs with diagnosis

---

## Testing

### Test Temporal Tracking

```bash
# Run calibration on a test MS
python -m dsa110_contimg.pipeline.stages_impl calibrate \
  --ms /stage/test_data/2025-10-19T14:31:45.ms \
  --refant 103

# Check logs for temporal snapshots
grep "Phase .* flag snapshot captured" <log_file>

# Check database
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT ms_path, newly_fully_flagged_spws FROM temporal_flagging;"
```

### Test Diagnostic Tool

```bash
# Analyze an MS
python scripts/diagnose_spw_failures.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103 \
  --failed-spws 9,14,15
```

---

## Benefits

### 1. Definitive Diagnosis

**Before:** "SPW 9 is 100% flagged, probably due to pre-calibration RFI"
(guessing)

**After:** "SPW 9: Pre-calibration flagging was 85.2%, refant was 100% flagged,
calibration solve failed, applycal flagged remaining 14.8%" (certain)

### 2. Root Cause Identification

Distinguish between:

- **Pre-calibration flagging** → SPW was bad before calibration
- **Calibration failure** → Solve failed due to insufficient S/N
- **applycal automatic flagging** → CASA flagged due to missing solutions

### 3. Data Quality Insights

- Track flagging evolution over time
- Identify frequency ranges with persistent RFI
- Optimize refant selection strategy
- Validate flagging thresholds

### 4. Debugging Aid

- Understand why calibration fails for specific SPWs
- Verify that calibration solve doesn't inadvertently increase flagging
- Confirm applycal behavior matches expectations

---

## Future Enhancements

### 1. Frontend Visualization

- Interactive timeline showing flag % at each phase
- Per-SPW evolution charts
- Refant flagging heatmap
- Automatic alerts for problematic patterns

### 2. Historical Trending

- Track flagging patterns across multiple observations
- Identify systematic RFI sources
- Correlate with external factors (time of day, weather, etc.)

### 3. Automated Mitigation

- Auto-exclude SPWs with high pre-calibration flagging
- Suggest alternative refants if primary is heavily flagged
- Adaptive flagging thresholds based on historical data

### 4. Integration with Alerting

- Alert when >X SPWs become fully flagged
- Notify when refant flagging exceeds threshold
- Flag observations with anomalous flagging patterns

---

## Related Documentation

- [SPW Flagging Process](./spw_flagging_process.md) - Complete flagging timeline
- [Calibration Workflow](../../docs/how-to/calibration_workflow.md) - Overall
  calibration process
- [Error Acknowledgment Rule](../../.cursor/rules/error-acknowledgment.mdc) -
  Why we don't dismiss errors

---

## Summary

Temporal flagging tracking transforms diagnostic work from **inference and
guesswork** to **definitive analysis**. By capturing flag states at each
pipeline phase, we can state with certainty what happened, when it happened, and
why it happened.

This is a foundational improvement for operational reliability and scientific
data quality.

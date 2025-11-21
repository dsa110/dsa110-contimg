# Frontend Changelog

**Latest Updates:**

---

## 2025-11-19: Temporal Flagging System

**Type:** Pipeline Enhancement + Documentation  
**Impact:** Major improvement to diagnostic capability

### Summary

Implemented temporal flagging tracking system that captures flag states at three
critical phases of calibration. This enables **definitive diagnosis** (not
inference) of why specific SPWs fail calibration.

### Changes

#### New Backend Modules

- **`calibration/flagging_temporal.py`** (467 lines)
  - `FlaggingSnapshot` dataclass: Complete flag state at a specific time
  - `SPWFlaggingStats` dataclass: Per-SPW flagging statistics
  - `capture_flag_snapshot()`: Capture flag state at any phase
  - `compare_flag_snapshots()`: Compare two snapshots
  - `diagnose_spw_failure()`: Provide definitive SPW failure diagnosis
  - `store_temporal_analysis_in_database()`: Store snapshots in database
  - `load_temporal_analysis_from_database()`: Retrieve stored analysis

#### Modified Backend Modules

- **`pipeline/stages_impl.py`**
  - Added Phase 1 snapshot capture (after pre-calibration flagging)
  - Added Phase 2 snapshot capture (after calibration solve)
  - Added Phase 3 snapshot capture (after applycal)
  - Added temporal analysis and comparison
  - Added definitive diagnosis logging
  - Added database storage of temporal analysis

#### New Scripts

- **`scripts/diagnose_spw_failures.py`** (244 lines)
  - Retrospective SPW failure diagnosis tool
  - Examines MS flagging and calibration tables
  - Provides definitive cause for SPW failures
  - Command-line interface with multiple options

#### Database Schema

- **`state/products.sqlite3`** - New table:

```sql
CREATE TABLE IF NOT EXISTS temporal_flagging (
    ms_path TEXT PRIMARY KEY,
    phase1_snapshot TEXT,
    phase3_snapshot TEXT,
    comparison TEXT,
    newly_fully_flagged_spws TEXT,
    timestamp TEXT
);
```

### Documentation

#### New Documentation Files

- **`/data/dsa110-contimg/docs/how-to/temporal_flagging_system.md`**
  - Comprehensive implementation guide
  - Usage examples for pipeline and developers
  - Example output from real DSA-110 data
  - Lessons learned and key findings

- **`/data/dsa110-contimg/docs/analysis/2025-11-19_spw_flagging_investigation.md`**
  - Complete investigation timeline
  - Definitive findings for SPWs 9, 14, 15
  - Per-SPW flagging statistics
  - RFI characterization
  - Lessons learned

#### Updated Documentation Files

- **`frontend/docs/how-to/spw_flagging_process.md`**
  - Updated temporal ordering to clearly distinguish three phases
  - Added definitive diagnosis section
  - Added "How to Diagnose SPW Failures With Certainty" section
  - Corrected circular logic in original diagnosis

- **`frontend/docs/how-to/temporal_flagging_tracking.md`**
  - Technical implementation details
  - Data structures and functions
  - Integration points in pipeline

### Key Findings

From investigation of 2025-10-19T14:31:45 observation:

**SPWs 9, 14, 15 Failure (DEFINITIVE CAUSE):**

- Pre-calibration flagging: 100.0%
- Reference antenna 103: 100% flagged in these SPWs
- Calibration solve: Failed (no valid data for refant)
- Calibration tables: NO SOLUTIONS confirmed
- **Root cause:** Refant 103 fully flagged during RFI flagging (Phase 1)

**Other SPWs (0-8, 10-13):**

- Pre-calibration flagging: 5-93%
- Calibration solve: Succeeded
- applycal: Applied solutions, preserved existing flags

**RFI Pattern:**

- SPWs 9, 14, 15 correspond to 1544-1656 MHz
- Near GPS L1 frequency (1575.42 MHz)
- Likely GPS and terrestrial RFI sources

### Impact

**Before:**

- SPW failure diagnosis was inference-based ("likely due to...")
- No historical tracking of flag evolution
- Required manual investigation and re-running pipeline

**After:**

- Definitive diagnosis with certainty ("100% flagged due to refant 103")
- Complete temporal history stored in database
- Automatic diagnosis on every calibration run
- Debugging uses stored snapshots

### Lessons Learned

1. **Temporal ordering is critical** - Can't infer pre-state from post-state
2. **Hedging language indicates uncertainty** - "Likely" means inference, not
   measurement
3. **Circular logic trap** - Observing final state and inferring initial state
   is unreliable
4. **Reference antenna is critical** - Even if SPW is <100% flagged, if refant
   is 100% flagged, calibration fails
5. **Real-time tracking preferred** - Retrospective analysis has fundamental
   limitations

### Future Work

#### Frontend Integration (Planned)

- Display temporal flag evolution in CalibrationSPWPanel
- Show Phase 1 vs Phase 3 flagging side-by-side
- Highlight newly fully-flagged SPWs
- Display definitive diagnosis for failures
- Interactive timeline showing flag evolution

#### API Endpoint (Planned)

```
GET /api/temporal-flagging/<ms_path>
```

Returns:

```json
{
  "phase1_snapshot": { ... },
  "phase3_snapshot": { ... },
  "comparison": {
    "newly_fully_flagged_spws": [9, 14, 15],
    "flag_increase_per_spw": { ... }
  },
  "diagnoses": {
    "9": { "definitive_cause": "...", ... },
    "14": { "definitive_cause": "...", ... },
    "15": { "definitive_cause": "...", ... }
  }
}
```

#### Predictive Flagging

- Train model on historical Phase 1 snapshots
- Predict which SPWs will fail calibration
- Alert when Phase 1 flagging suggests failure
- Recommend alternative refants

#### RFI Source Identification

- Map SPWs to frequency ranges
- Cross-reference with known RFI sources
- Identify time-dependent patterns
- Build RFI source database

#### Adaptive Refant Selection

- Analyze per-antenna per-SPW flagging
- Select least-flagged antenna as refant per SPW
- Use different refants for different SPWs

### Testing

- ✅ Verified on real DSA-110 data (2025-10-19T14:31:45)
- ✅ Confirmed snapshot accuracy
- ✅ Verified database storage and retrieval
- ✅ Confirmed no significant performance impact (~0.5-2s overhead)
- ✅ Validated against manual inspection

### Credits

**Implementation:** AI Agent (Claude Sonnet 4.5) + Dana Simard  
**Date:** 2025-11-19  
**Motivation:** Eliminate guesswork in SPW failure diagnosis  
**Result:** Definitive, data-driven diagnostic capability

---

## Previous Updates

_(Additional changelog entries would go here)_

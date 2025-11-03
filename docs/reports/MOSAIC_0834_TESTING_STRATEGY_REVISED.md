# Corrected Testing Strategy: Use Actual Pipeline Components

**Date:** 2025-11-02  
**Status:** CORRECTED APPROACH

---

## Problem Identified

### What Was Wrong

The previous approach **bypassed actual pipeline components**:

1. **Manual time-based search** instead of `CalibratorMSGenerator.find_transit()`
2. **No coordinate verification** (Dec matching)
3. **No transit calculation** using `previous_transits()`
4. **Bypassed** all components that will actually run in streaming

### Why This Is Wrong for End-to-End Testing

- End-to-end testing **MUST** test actual pipeline components
- Streaming pipeline will use:
  * `CalibratorMSGenerator.find_transit()` - **MUST TEST**
  * `previous_transits()` transit calculation - **MUST TEST**
  * Dec matching verification - **MUST TEST**
  * `find_subband_groups()` group discovery - **MUST TEST**
- Previous approach bypassed ALL of these
- Therefore, was NOT testing what will actually run

---

## Correct Approach

### Use Actual Pipeline Components

The streaming pipeline uses `CalibratorMSGenerator` service. We must test this.

### Solution Options

#### Option 1: Fix Python Compatibility (Recommended)

Remove `from __future__ import annotations` from modules that need Python 3.6 compatibility, or use Python 3.7+ if available.

#### Option 2: Use Working Scripts

Use `scripts/list_calibrator_transits.py` which:
- Uses `CalibratorMSGenerator` (actual production component)
- Handles transit finding properly
- Verifies coordinates
- Returns validated results

**However**, this script imports modules with `from __future__ import annotations`, so we need to fix compatibility first.

#### Option 3: Use API Endpoints

If API is running, use actual API endpoints that will be used in streaming:
- `/api/calibrator/transits/{name}` - List transits
- `/api/calibrator/ms` - Generate MS for transit

---

## Revised Phase 1: Find Transit Using Actual Pipeline

### Correct Method

```bash
# Use actual pipeline script (after fixing compatibility)
python3 scripts/list_calibrator_transits.py \
    --name 0834+555 \
    --input-dir /data/incoming \
    --max-days-back 30

# OR use Python 3.7+ if available
python3.7 scripts/list_calibrator_transits.py \
    --name 0834+555 \
    --input-dir /data/incoming \
    --max-days-back 30
```

### What This Tests

✓ `CalibratorMSGenerator.find_transit()` - Actual production component  
✓ `previous_transits()` transit calculation - Proper LST calculation  
✓ Dec matching verification - Coordinate verification  
✓ `find_subband_groups()` - Group discovery  
✓ Complete workflow that will run in streaming  

---

## Action Plan

1. **Fix Python Compatibility:**
   - Check for Python 3.7+ availability
   - OR remove `from __future__ import annotations` from critical modules
   - OR create compatible wrapper

2. **Use Proper Tools:**
   - Use `list_calibrator_transits.py` to find transit
   - Verify it uses actual pipeline components
   - Test full workflow

3. **Proceed with End-to-End Test:**
   - Transit finding → MS generation → Calibration → Imaging → Mosaicking
   - All using actual pipeline components

---

## Key Principle

**End-to-end testing must test ACTUAL pipeline components, not shortcuts around them.**

The streaming pipeline will use `CalibratorMSGenerator`, so we must test `CalibratorMSGenerator`.

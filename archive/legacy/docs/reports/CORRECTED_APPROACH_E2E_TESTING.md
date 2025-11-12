# Corrected Approach: End-to-End Testing Using Actual Pipeline Components

**Date:** 2025-11-02  
**Status:** CORRECTED BASED ON MEMORY AND RULES REVIEW

---

## Key Insight from Memory.md

After reviewing `docs/reports/memory.md`, the actual production workflow is:

1. **Streaming Pipeline**: `streaming_converter.py` monitors `/data/incoming/` and processes **ALL incoming groups**
2. **Group Discovery**: Uses `hdf5_orchestrator.find_subband_groups()` internally
3. **Conversion**: Uses `hdf5_orchestrator.py` CLI (the orchestrator)
4. **No Specific Transit Finding**: The streaming pipeline doesn't search for calibrator transits - it processes everything based on time windows

**Key Point**: The streaming pipeline uses `hdf5_orchestrator` CLI → which calls `find_subband_groups()` internally.

---

## What Will Actually Run in Streaming

From `memory.md` Stage 1-2:

1. **Ingest & Monitoring**: `streaming_converter.py` watches for new files
2. **Group Discovery**: `find_subband_groups()` identifies complete 16-subband groups (called internally by orchestrator)
3. **Conversion**: `hdf5_orchestrator.py` CLI converts groups to MS
4. **Calibration**: Applied to all groups
5. **Imaging**: Images created
6. **Mosaicking**: Tiles combined

---

## Correct Approach for End-to-End Testing

### Use Actual Pipeline CLI Tools

**For end-to-end testing, use the CLI tools that will actually run:**

1. **Group Discovery & Conversion**: Use `hdf5_orchestrator.py` CLI
   ```bash
   python3 -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
       /data/incoming \
       /scratch/dsa110-contimg/ms/0834_transit \
       "2025-10-29 08:04:00" \
       "2025-10-29 09:04:00" \
       --writer parallel-subband
   ```
   - This is what the streaming pipeline uses
   - It calls `find_subband_groups()` internally
   - Tests actual production workflow

2. **Calibration**: Use `calibration.cli`
   ```bash
   python3 -m dsa110_contimg.calibration.cli calibrate \
       --ms /scratch/dsa110-contimg/ms/0834_transit/*.ms
   ```

3. **Imaging**: Use `imaging.cli`
   ```bash
   python3 -m dsa110_contimg.imaging.cli image_ms \
       --ms /scratch/dsa110-contimg/ms/0834_transit/*.ms \
       --pbcor
   ```

4. **Mosaicking**: Use `mosaic.cli`
   ```bash
   python3 -m dsa110_contimg.mosaic.cli build \
       --name 0834_transit_mosaic
   ```

### Why This Is Correct

✓ **Uses actual pipeline CLI** - `hdf5_orchestrator` is what streaming uses  
✓ **Tests what will actually run** - Same workflow as production  
✓ **No bypassing** - Uses proper group discovery internally  
✓ **Python 3.6 compatible** - CLI runs in casa6 environment (Python 3.11)  
✓ **Can target 0834 transit** - Use time window around transit time  

---

## Revised Phase 1: Find Transit Group

### Correct Method

**Use the orchestrator CLI directly:**

```bash
# Calculate transit time window (±30 minutes around 08:34 UTC)
# For 2025-10-29: 08:04:00 to 09:04:00

# Use ACTUAL pipeline orchestrator CLI
python3 -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /scratch/dsa110-contimg/ms/0834_transit \
    "2025-10-29 08:04:00" \
    "2025-10-29 09:04:00" \
    --writer parallel-subband \
    --stage-to-tmpfs \
    --max-workers 4
```

**What This Does:**
- Calls `find_subband_groups()` internally (actual function)
- Finds complete 16-subband groups in time window
- Converts using production writer (`parallel-subband`)
- Tests actual production workflow

---

## Key Differences: Old vs. Correct Approach

| Aspect | Old Approach (Wrong) | Correct Approach |
|--------|----------------------|------------------|
| **Group Discovery** | Manual file search | `hdf5_orchestrator` CLI (uses `find_subband_groups()` internally) |
| **Transit Finding** | Manual time search | Simple transit time calculation + orchestrator CLI |
| **Component Testing** | Bypassed pipeline | Tests actual pipeline CLI |
| **Streaming Relevance** | Not relevant | Tests what streaming uses |
| **Python Compatibility** | Had issues | CLI runs in casa6 (Python 3.11) |

---

## Why This Aligns with End-to-End Testing

**End-to-end testing should test the actual pipeline components that will run in streaming:**

1. ✓ `hdf5_orchestrator` CLI - Used by streaming pipeline
2. ✓ `find_subband_groups()` - Called internally by orchestrator
3. ✓ `calibration.cli` - Used for calibration
4. ✓ `imaging.cli` - Used for imaging
5. ✓ `mosaic.cli` - Used for mosaicking

**All components are tested, none are bypassed.**

---

## Action Plan

1. **Use `hdf5_orchestrator` CLI** to find and convert groups around 0834 transit time
2. **Process through full pipeline** using actual CLI tools
3. **Test end-to-end workflow** that matches production

This approach tests **actual pipeline components** while still targeting the 0834 transit for mosaicking.

**Note**: The CLI runs in `casa6` conda environment (Python 3.11), avoiding Python 3.6 compatibility issues.

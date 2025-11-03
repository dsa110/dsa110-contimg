# Phase 1 Execution Results: REVISED STRATEGY

**Date:** 2025-11-02  
**Status:** ✓ **STRATEGY REVISED - USING ACTUAL PIPELINE COMPONENTS**

---

## Strategy Change

**Original Approach:** Register archived PB-corrected images from October 13, 2025  
**Revised Approach:** Full end-to-end pipeline test starting from incoming HDF5 files  
**Corrected Approach:** Use `hdf5_orchestrator` CLI (actual production component)

**Rationale:** 
- End-to-end test validates latest pipeline version
- Uses actual pipeline components that will run in streaming
- Tests complete workflow: UVH5 → MS → Calibration → Imaging → Mosaicking

---

## Phase 1.1: Find and Convert 0834 Transit Using Actual Pipeline

### Objective
Use `hdf5_orchestrator` CLI to find and convert 0834 transit groups.

### Status: IN PROGRESS

**Approach:**
- Use `hdf5_orchestrator` CLI directly (what streaming uses)
- Calculate transit time window (±30 minutes around 08:34 UTC)
- Orchestrator calls `find_subband_groups()` internally
- Tests actual production workflow

**Next Steps:**
1. Calculate transit time window for 0834 transit
2. Run `hdf5_orchestrator` CLI to find and convert groups
3. Verify MS files created successfully
4. Proceed to Phase 2: Calibration

---

## Phase 1 Execution: Proper Transit Calculation

### Step 1.1: Load Calibrator Coordinates
**Status:** IN PROGRESS
**Tool:** `read_vla_parsed_catalog_csv()`
**Environment:** `casa6` conda environment

### Step 1.2: Calculate Transit Times
**Status:** IN PROGRESS
**Tool:** `previous_transits()`
**Environment:** `casa6` conda environment

### Step 1.3: Calculate Search Window
**Status:** IN PROGRESS
**Tool:** Astropy Time arithmetic
**Environment:** `casa6` conda environment

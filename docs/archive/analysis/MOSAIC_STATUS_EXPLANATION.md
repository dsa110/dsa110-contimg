# Mosaic Status Explanation

## Clarification: What "Pending" Means

There are **two different contexts** where "pending" appears:

### 1. **My Previous Statement: "Pending Real Data"**
When I said things were "pending real data", I meant:
- **Waiting for**: We need real production data to test the fixes
- **Not ready yet**: Current test data is insufficient (only 5 PB-corrected images, need ≥10)
- **Status**: Code is ready, but testing requires real data

This is **NOT** a database status - it's just me saying "we're waiting for real data to test with."

### 2. **Database Workflow Status: "pending"**
In the actual database, there are workflow status values:

#### `mosaic_groups` Table Status
- **`pending`**: Group of MS files formed, waiting to be processed
- **`calibrated`**: Calibration solved and applied to MS files
- **`imaged`**: Images created from calibrated MS files  
- **`mosaicked`**: Mosaic created from images
- **`completed`**: Full workflow complete

#### `mosaics` Table Status (CLI Workflow)
- **`planned`**: Mosaic plan created (list of tiles selected)
- **`built`**: Mosaic successfully built from tiles

## Current Database State

### mosaic_groups
- 1 group found: `group_1762566273_e646f925`
- Status: **`completed`** ✓
- Mosaic ID: `mosaic_group_1762566273_e646f925_1762665566`

### mosaics (Science Metadata)
- 1 mosaic found: `mosaic_group_1762566273_e646f925_1762665566`
- This is a **completed mosaic** (has path, MJD times, noise, etc.)
- **No status column** in this schema (it's science metadata, not workflow tracking)

### mosaics (CLI Workflow)
- **Schema mismatch fixed**: Added workflow columns (`status`, `method`, `tiles`, etc.)
- Can now use `mosaic plan` and `mosaic build` commands
- Status will be `planned` after planning, `built` after building

## Summary

- **"Pending real data"** = Waiting for production data to test (not a database status)
- **`pending` status** = Workflow state meaning "waiting to be processed"
- **Current state**: 1 completed mosaic exists, CLI workflow schema fixed

The confusion was about terminology - I was using "pending" to mean "waiting for", not referring to an actual database status value.


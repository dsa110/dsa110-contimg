# Absurd Workflow Builder User Guide

**Author:** DSA-110 Team  
**Date:** 2025-11-18  
**Audience:** Pipeline Operators, Scientists

---

## Overview

The **Workflow Builder** provides a visual interface for composing multi-stage
pipeline workflows. You can chain together multiple tasks (conversion,
calibration, imaging, etc.) and submit them as a single workflow. Tasks execute
in priority order (higher priority first).

**Key Features:**

- ✅ Visual stepper interface
- ✅ Add/remove stages dynamically
- ✅ Configure task parameters per stage
- ✅ Priority-based execution
- ✅ Submit entire workflow at once

---

## Accessing the Workflow Builder

1. Navigate to **Control Page** in the web interface
2. Click the **"Workflow Builder"** tab (6th tab)
3. The builder loads with one default stage

**URL:** `http://your-server:8000/control` → "Workflow Builder" tab

---

## Workflow Builder Layout

### 1. Header

- **Title**: "Workflow Builder"
- **Description**: Brief explanation of how workflows work

### 2. Stepper Interface

**Visual representation of workflow stages:**

- Each stage appears as a step in a vertical stepper
- Steps are numbered (Stage 1, Stage 2, etc.)
- Priority badge shown next to each step
- Arrow (↓) between stages indicates execution order

### 3. Stage Configuration

Each stage has:

- **Task Type** dropdown (9 available tasks)
- **Priority** field (1-20)
- **Timeout** field (seconds, optional)
- **Task-specific parameters** (varies by task type)
- **Additional Parameters** JSON editor

### 4. Action Buttons

- **Add Stage**: Add new stage to workflow
- **Submit Workflow**: Spawn all tasks in workflow

---

## Available Task Types

| Task Type              | Description                           | Default Priority |
| ---------------------- | ------------------------------------- | ---------------- |
| **Catalog Setup**      | Prepare NVSS catalog                  | 10               |
| **Convert UVH5 to MS** | Convert UVH5 files to Measurement Set | 15               |
| **Calibration Solve**  | Solve K/BP/G calibration tables       | 12               |
| **Apply Calibration**  | Apply calibration to MS               | 10               |
| **Imaging**            | Create images using WSClean/tclean    | 8                |
| **Validation**         | Validate image quality                | 5                |
| **Crossmatch**         | Crossmatch with NVSS catalog          | 5                |
| **Photometry**         | Perform adaptive photometry           | 5                |
| **Organize Files**     | Organize MS files                     | 3                |

---

## Building a Workflow

### Step 1: Add Stages

1. Click **"Add Stage"** button
2. New stage appears in stepper
3. Repeat to add more stages

**Example Workflow:**

```
Stage 1: Convert UVH5 to MS (Priority 15)
  ↓
Stage 2: Calibration Solve (Priority 12)
  ↓
Stage 3: Apply Calibration (Priority 10)
  ↓
Stage 4: Imaging (Priority 8)
```

### Step 2: Configure Each Stage

For each stage:

1. **Select Task Type**
   - Choose from dropdown
   - Default priority auto-filled

2. **Set Priority**
   - Higher priority = executed first
   - Range: 1-20
   - Recommended: 15 (convert) → 12 (calibrate) → 10 (apply) → 8 (image)

3. **Set Timeout** (optional)
   - Maximum execution time in seconds
   - Leave empty for default timeout
   - Example: `3600` = 1 hour

4. **Configure Task Parameters**
   - Parameters vary by task type
   - See "Task-Specific Parameters" section below

### Step 3: Submit Workflow

1. Review all stages
2. Verify parameters are correct
3. Click **"Submit Workflow"** button
4. All tasks spawned in priority order
5. Auto-navigation to "Absurd Tasks" tab

---

## Task-Specific Parameters

### Convert UVH5 to MS

**Required:**

- **Start Time**: `YYYY-MM-DD HH:MM:SS` format
- **End Time**: `YYYY-MM-DD HH:MM:SS` format

**Optional:**

- **Input Directory**: Default `/data/incoming`
- **Output Directory**: Default `/stage/dsa110-contimg/ms`

**Example:**

```
Start Time: 2025-11-18 14:00:00
End Time: 2025-11-18 14:05:00
Input Directory: /data/incoming
Output Directory: /stage/dsa110-contimg/ms
```

---

### Calibration Solve

**Required:**

- **MS Path**: Full path to Measurement Set

**Example:**

```
MS Path: /stage/dsa110-contimg/ms/science/2025-11-18/obs-001.ms
```

---

### Apply Calibration

**Required:**

- **MS Path**: Full path to Measurement Set

**Example:**

```
MS Path: /stage/dsa110-contimg/ms/science/2025-11-18/obs-001.ms
```

---

### Imaging

**Required:**

- **MS Path**: Full path to Measurement Set

**Optional:**

- **Image Size**: Default `2048` pixels
- **Backend**: `wsclean` (default) or `tclean`

**Example:**

```
MS Path: /stage/dsa110-contimg/ms/science/2025-11-18/obs-001.ms
Image Size: 2048
Backend: wsclean
```

---

### Additional Parameters (JSON)

**All tasks support additional parameters via JSON editor:**

**Example for Imaging:**

```json
{
  "imsize": 4096,
  "cell_arcsec": 1.0,
  "niter": 1000,
  "threshold": "0.001Jy",
  "weighting": "briggs",
  "robust": 0.5
}
```

**Note:** JSON must be valid. Invalid JSON is ignored.

---

## Priority-Based Execution

**How It Works:**

- Tasks with **higher priority** are claimed first
- Tasks with **same priority** are claimed in creation order (FIFO)
- Lower priority tasks wait until higher priority tasks complete

**Recommended Priority Scheme:**

| Stage             | Priority | Reason                |
| ----------------- | -------- | --------------------- |
| Convert           | 15       | Must happen first     |
| Calibration Solve | 12       | Needed before apply   |
| Apply Calibration | 10       | Needed before imaging |
| Imaging           | 8        | Final processing step |
| Validation        | 5        | Post-processing       |
| Crossmatch        | 5        | Post-processing       |
| Photometry        | 5        | Post-processing       |

**Example:**

```
Workflow:
  Stage 1: Convert (Priority 15)      ← Executed first
  Stage 2: Calibrate (Priority 12)    ← Executed second
  Stage 3: Apply (Priority 10)        ← Executed third
  Stage 4: Image (Priority 8)          ← Executed last
```

---

## Common Workflows

### Workflow 1: Standard Imaging Pipeline

**Stages:**

1. Convert UVH5 to MS (Priority 15)
   - Start Time: `2025-11-18 14:00:00`
   - End Time: `2025-11-18 14:05:00`
2. Calibration Solve (Priority 12)
   - MS Path: (auto-filled from Stage 1 output)
3. Apply Calibration (Priority 10)
   - MS Path: (same as Stage 2)
4. Imaging (Priority 8)
   - MS Path: (same as Stage 2)
   - Image Size: `2048`
   - Backend: `wsclean`

**Execution Order:** Convert → Calibrate → Apply → Image

---

### Workflow 2: Quick-Look Pipeline

**Stages:**

1. Convert UVH5 to MS (Priority 15)
2. Calibration Solve (Priority 12)
3. Apply Calibration (Priority 10)
4. Imaging (Priority 8)
   - Image Size: `1024` (smaller for speed)
   - Backend: `wsclean`
5. Validation (Priority 5)

**Execution Order:** Convert → Calibrate → Apply → Image → Validate

---

### Workflow 3: Full Analysis Pipeline

**Stages:**

1. Convert UVH5 to MS (Priority 15)
2. Calibration Solve (Priority 12)
3. Apply Calibration (Priority 10)
4. Imaging (Priority 8)
5. Validation (Priority 5)
6. Crossmatch (Priority 5)
7. Photometry (Priority 5)

**Execution Order:** Convert → Calibrate → Apply → Image → Validate → Crossmatch
→ Photometry

---

## Tips and Best Practices

### 1. Set Appropriate Priorities

- **Higher priority** for earlier stages (convert, calibrate)
- **Lower priority** for later stages (imaging, validation)
- **Gap of 2-3** between stages ensures ordering

### 2. Use Timeouts Wisely

- **Convert**: 900s (15 minutes)
- **Calibration**: 1800s (30 minutes)
- **Imaging**: 1800s (30 minutes)
- **Validation**: 300s (5 minutes)

### 3. Validate Parameters

- Check all required fields are filled
- Verify time formats are correct
- Ensure MS paths exist (for calibration/imaging)
- Validate JSON parameters

### 4. Test Workflows

- Start with simple workflows (2-3 stages)
- Test with small datasets first
- Monitor in "Absurd Tasks" tab after submission
- Review failed tasks and adjust parameters

### 5. Reuse Workflows

- Save common workflows as templates (future feature)
- Document successful workflows
- Share workflows with team

---

## Troubleshooting

### Issue: Cannot Submit Workflow

**Symptoms:** "Submit Workflow" button disabled

**Solutions:**

1. Ensure at least one stage is configured
2. Check all required fields are filled
3. Verify task type is selected for each stage
4. Check for validation errors

---

### Issue: Tasks Not Executing in Order

**Symptoms:** Lower priority tasks execute before higher priority

**Solutions:**

1. Verify priorities are set correctly (higher = first)
2. Check if workers are processing tasks concurrently
3. Ensure priority gap is sufficient (2-3 points)
4. Review task execution in "Absurd Tasks" tab

---

### Issue: Tasks Failing

**Symptoms:** Tasks fail after submission

**Solutions:**

1. Review error details in Task Inspector
2. Check task parameters are correct
3. Verify MS paths exist (for calibration/imaging)
4. Check system resources (CPU, memory, disk)
5. Review CASA environment

---

### Issue: JSON Parameters Not Applied

**Symptoms:** Additional parameters ignored

**Solutions:**

1. Verify JSON is valid (use JSON validator)
2. Check parameter names match task requirements
3. Review task documentation for supported parameters
4. Test with minimal JSON first

---

## Advanced Usage

### Custom Parameters via JSON

**Example: Advanced Imaging Parameters**

```json
{
  "imsize": 4096,
  "cell_arcsec": 0.5,
  "niter": 5000,
  "threshold": "0.0001Jy",
  "weighting": "briggs",
  "robust": 0.0,
  "deconvolver": "multiscale",
  "nterms": 2,
  "pbcor": true,
  "uvrange": ">100m"
}
```

### Conditional Workflows

**Note:** Current version doesn't support conditional execution. All stages
execute in priority order.

**Workaround:** Use separate workflows for different conditions.

---

## Related Documentation

- **[Task Dashboard Guide](absurd_task_dashboard.md)** - Monitoring and managing
  tasks
- **[Absurd Operations Guide](absurd_operations.md)** - Backend operations
- **[Performance Tuning Guide](../../architecture/pipeline/absurd_performance_tuning.md)** -
  Optimizing workflows

---

## Support

**For Issues:**

- Check browser console for errors
- Review backend logs: `journalctl -u dsa110-contimg-api -f`
- Contact DSA-110 operations team

**For Questions:**

- Review this guide
- Check operations documentation
- Contact development team

---

**Last Updated:** 2025-11-18

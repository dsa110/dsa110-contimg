# Task 3 Phase 2: ControlPage Refactoring Plan

**Date:** 2025-11-13  
**Status:** in-progress  
**Related:** [Task 3 Progress](task3_progress.md),
[Task 3 Architecture Refactoring](task3_architecture_refactoring.md)

---

## Overview

Splitting `ControlPage.tsx` (2,439 lines) into focused, maintainable components
following single responsibility principle.

## Target Structure

```
frontend/src/
├── pages/
│   └── ControlPage.tsx (~300 lines) - Orchestration only
└── components/
    └── workflows/
        ├── JobManagement.tsx ✅ (Created)
        ├── ConversionWorkflow.tsx (Tab 0: Convert)
        ├── CalibrationWorkflow.tsx (Tab 1: Calibrate + Tab 2: Apply)
        └── ImagingWorkflow.tsx (Tab 3: Image)
```

## Component Responsibilities

### ✅ JobManagement.tsx (Complete)

**Location:** `frontend/src/components/workflows/JobManagement.tsx`  
**Lines:** ~150  
**Responsibilities:**

- Display recent jobs list
- Stream and display job logs
- Job selection handling

**Props:**

- `selectedJobId: number | null`
- `onJobSelect: (jobId: number | null) => void`

### 📋 ConversionWorkflow.tsx (Pending)

**Location:** ConversionWorkflow.tsx  
**Estimated Lines:** ~400-500  
**Responsibilities:**

- UVH5 file selection
- Conversion parameters form
- Conversion job submission
- Workflow integration

**State to Extract:**

- `convertParams: ConversionJobParams`
- `workflowParams` (for full pipeline)

**Hooks to Use:**

- `useUVH5Files()`
- `useCreateConvertJob()`
- `useCreateWorkflowJob()`

### 📋 CalibrationWorkflow.tsx (Pending)

**Location:** CalibrationWorkflow.tsx  
**Estimated Lines:** ~800-1000  
**Responsibilities:**

- Calibration parameters form
- Existing calibration tables selection
- Calibration QA panel
- Apply calibration form
- Calibration job submission

**State to Extract:**

- `calibParams: CalibrateJobParams`
- `applyParams: JobParams`
- `compatibilityChecks`
- `selectedMS` (shared with other workflows)

**Hooks to Use:**

- `useCreateCalibrateJob()`
- `useCreateApplyJob()`
- `useExistingCalTables()`
- `useCalibrationQA()`
- `useValidateCalTable()`

### 📋 ImagingWorkflow.tsx (Pending)

**Location:** ImagingWorkflow.tsx  
**Estimated Lines:** ~500-600  
**Responsibilities:**

- Imaging parameters form
- Mask configuration
- Image job submission

**State to Extract:**

- `imageParams: JobParams`

**Hooks to Use:**

- `useCreateImageJob()`

## Shared State & Context

### MS Selection (Shared)

- `selectedMS: string`
- `selectedMSList: string[]`
- `msList` from `useMSList()`
- `msMetadata` from `useMSMetadata()`

**Solution:** Pass as props to workflow components, or create a shared context.

### Keyboard Shortcuts

Currently handled in ControlPage. Options:

1. Keep in ControlPage and delegate to workflows
2. Move to each workflow component
3. Create a shared hook

**Recommendation:** Keep in ControlPage, delegate via callbacks.

## Refactoring Steps

### Step 1: ✅ Create JobManagement Component

- [x] Extract job list display
- [x] Extract job logs streaming
- [x] Extract job selection logic
- [x] Test component in isolation

### Step 2: Create ConversionWorkflow Component

- [ ] Extract conversion form (Tab 0)
- [ ] Extract workflow form (full pipeline)
- [ ] Extract conversion submission logic
- [ ] Test component

### Step 3: Create CalibrationWorkflow Component

- [ ] Extract calibration form (Tab 1)
- [ ] Extract apply calibration form (Tab 2)
- [ ] Extract calibration QA panel
- [ ] Extract calibration submission logic
- [ ] Test component

### Step 4: Create ImagingWorkflow Component

- [ ] Extract imaging form (Tab 3)
- [ ] Extract imaging submission logic
- [ ] Test component

### Step 5: Refactor ControlPage

- [ ] Import workflow components
- [ ] Replace tab content with components
- [ ] Pass shared state as props
- [ ] Maintain keyboard shortcuts
- [ ] Test full integration

## Testing Strategy

1. **Unit Tests:** Test each workflow component in isolation
2. **Integration Tests:** Test ControlPage composition
3. **E2E Tests:** Verify workflows still function end-to-end

## Success Criteria

- [x] JobManagement component created and working
- [ ] ControlPage.tsx < 500 lines
- [ ] Each workflow component < 1,000 lines
- [ ] All existing functionality preserved
- [ ] No regressions in user workflows

## Files Modified

### Created

- `frontend/src/components/workflows/JobManagement.tsx` ✅

### To Create

- ConversionWorkflow.tsx
- CalibrationWorkflow.tsx
- ImagingWorkflow.tsx

### To Modify

- `frontend/src/pages/ControlPage.tsx` (reduce from 2,439 to ~300 lines)

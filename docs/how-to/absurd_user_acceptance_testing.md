# Absurd User Acceptance Testing (UAT) Guide

**Author:** DSA-110 Team  
**Date:** 2025-11-18  
**Audience:** Testers, QA Team, Operations Team

---

## Overview

This guide provides comprehensive test scenarios for validating the Absurd
workflow manager frontend integration. These tests should be performed before
production deployment.

**Testing Scope:**

- ✅ Task Dashboard functionality
- ✅ Workflow Builder functionality
- ✅ Real-time WebSocket updates
- ✅ Task Inspector actions (retry, cancel)
- ✅ End-to-end workflows

---

## Pre-Testing Setup

### 1. Environment Setup

```bash
# Start backend with Absurd enabled
export ABSURD_ENABLED=true
export ABSURD_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/absurd"
export ABSURD_QUEUE_NAME="dsa110-pipeline"

# Start API server
uvicorn dsa110_contimg.api.app:app --reload

# Start worker (in separate terminal)
python scripts/run_absurd_worker.py \
  --database-url postgresql://postgres:postgres@localhost:5432/absurd \
  --queue-name dsa110-pipeline \
  --concurrency 2
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Test Data

- Ensure test UVH5 files available in `/data/incoming/`
- Ensure test MS files available in `/stage/dsa110-contimg/ms/`
- PostgreSQL database with Absurd tables created

---

## Test Scenarios

### Test Suite 1: Task Dashboard

#### Test 1.1: Dashboard Load

**Objective:** Verify dashboard loads correctly

**Steps:**

1. Navigate to Control Page
2. Click "Absurd Tasks" tab
3. Wait for dashboard to load

**Expected Results:**

- ✅ Dashboard displays without errors
- ✅ Health status card visible
- ✅ Queue statistics cards visible (6 cards)
- ✅ Status filter dropdown visible
- ✅ Task list table visible (may be empty)

**Pass Criteria:** All elements visible, no console errors

---

#### Test 1.2: Health Status Display

**Objective:** Verify health status displays correctly

**Steps:**

1. Open Absurd Tasks tab
2. Observe health status card

**Expected Results:**

- ✅ Status shows "healthy", "degraded", "critical", or "down"
- ✅ Color coding matches status:
  - Green = healthy
  - Yellow = degraded
  - Red = critical/down
- ✅ Message provides brief description

**Pass Criteria:** Status and color match system state

---

#### Test 1.3: Queue Statistics

**Objective:** Verify queue statistics display correctly

**Steps:**

1. Open Absurd Tasks tab
2. Observe queue statistics cards

**Expected Results:**

- ✅ 6 cards visible: Pending, In Progress, Completed, Failed, Cancelled, Total
- ✅ Numbers match actual queue state
- ✅ Cards update in real-time (within 5 seconds)

**Pass Criteria:** Statistics accurate and update automatically

---

#### Test 1.4: Status Filtering

**Objective:** Verify status filter works correctly

**Steps:**

1. Open Absurd Tasks tab
2. Select "Pending" from filter dropdown
3. Observe task list
4. Select "Completed" from filter dropdown
5. Observe task list
6. Select "All Tasks" from filter dropdown
7. Observe task list

**Expected Results:**

- ✅ Filter dropdown works
- ✅ Task list updates immediately when filter changes
- ✅ Only tasks matching filter are shown
- ✅ "All Tasks" shows all tasks

**Pass Criteria:** Filtering works for all status types

---

#### Test 1.5: Task List Display

**Objective:** Verify task list displays correctly

**Steps:**

1. Open Absurd Tasks tab
2. Ensure tasks exist in queue (spawn test task if needed)
3. Observe task list table

**Expected Results:**

- ✅ Table displays all columns:
  - Task ID (truncated)
  - Task Name
  - Status (with icon)
  - Priority (color-coded)
  - Retry Count
  - Created timestamp
  - Duration
  - Actions button
- ✅ Status chips have correct colors
- ✅ Priority badges have correct colors
- ✅ Timestamps formatted correctly
- ✅ Durations calculated correctly

**Pass Criteria:** All columns display correctly

---

### Test Suite 2: Task Inspector

#### Test 2.1: Open Task Inspector

**Objective:** Verify Task Inspector opens correctly

**Steps:**

1. Open Absurd Tasks tab
2. Click on a task row
3. Observe Task Inspector drawer

**Expected Results:**

- ✅ Drawer opens from right side
- ✅ Task details displayed
- ✅ All sections visible (Task Information, Timeline, Parameters)
- ✅ Close button (X) visible

**Pass Criteria:** Inspector opens and displays task details

---

#### Test 2.2: Task Information Section

**Objective:** Verify task information displays correctly

**Steps:**

1. Open Task Inspector for a task
2. Expand "Task Information" section
3. Review all fields

**Expected Results:**

- ✅ Task ID (full UUID)
- ✅ Task Name
- ✅ Queue Name
- ✅ Status (with chip)
- ✅ Priority (with chip)
- ✅ Retry Count

**Pass Criteria:** All fields display correctly

---

#### Test 2.3: Timeline Section

**Objective:** Verify timeline displays correctly

**Steps:**

1. Open Task Inspector for a completed task
2. Expand "Timeline" section
3. Review timeline

**Expected Results:**

- ✅ Created At timestamp
- ✅ Claimed At timestamp (if claimed)
- ✅ Completed At timestamp (if completed)
- ✅ Wait Time calculated correctly
- ✅ Execution Time calculated correctly

**Pass Criteria:** Timeline accurate and formatted correctly

---

#### Test 2.4: Parameters Section

**Objective:** Verify parameters display correctly

**Steps:**

1. Open Task Inspector
2. Expand "Task Parameters" section
3. Review JSON

**Expected Results:**

- ✅ JSON formatted correctly (pretty-printed)
- ✅ All parameters visible
- ✅ JSON syntax valid

**Pass Criteria:** Parameters display correctly

---

#### Test 2.5: Result Section (Completed Tasks)

**Objective:** Verify result displays for completed tasks

**Steps:**

1. Open Task Inspector for a completed task
2. Expand "Result" section
3. Review result JSON

**Expected Results:**

- ✅ Result section visible
- ✅ JSON formatted correctly
- ✅ Result data accurate

**Pass Criteria:** Result displays correctly

---

#### Test 2.6: Error Section (Failed Tasks)

**Objective:** Verify error displays for failed tasks

**Steps:**

1. Open Task Inspector for a failed task
2. Expand "Error Details" section
3. Review error message

**Expected Results:**

- ✅ Error section visible
- ✅ Error message displayed
- ✅ Error formatted correctly

**Pass Criteria:** Error displays correctly

---

### Test Suite 3: Task Actions

#### Test 3.1: Retry Failed Task

**Objective:** Verify retry functionality works

**Steps:**

1. Open Absurd Tasks tab
2. Filter: "Failed"
3. Click on a failed task
4. Click "Retry Task" button
5. Confirm in dialog
6. Observe new task in queue

**Expected Results:**

- ✅ Retry button visible for failed tasks
- ✅ Confirmation dialog appears
- ✅ New task spawned after confirmation
- ✅ New task appears in "Pending" queue
- ✅ New task has same parameters as original

**Pass Criteria:** Retry creates new task successfully

---

#### Test 3.2: Cancel Pending Task

**Objective:** Verify cancel functionality works

**Steps:**

1. Open Absurd Tasks tab
2. Filter: "Pending"
3. Click on a pending task
4. Click "Cancel Task" button
5. Confirm in dialog
6. Observe task status change

**Expected Results:**

- ✅ Cancel button visible for pending tasks
- ✅ Confirmation dialog appears
- ✅ Task cancelled after confirmation
- ✅ Task status changes to "cancelled"
- ✅ Task removed from pending queue

**Pass Criteria:** Cancel works correctly

---

#### Test 3.3: Cancel In-Progress Task

**Objective:** Verify cancel works for claimed tasks

**Steps:**

1. Open Absurd Tasks tab
2. Filter: "In Progress"
3. Click on a claimed task
4. Click "Cancel Task" button
5. Confirm in dialog
6. Observe task status change

**Expected Results:**

- ✅ Cancel button visible for claimed tasks
- ✅ Confirmation dialog appears
- ✅ Task cancelled after confirmation
- ✅ Task status changes to "cancelled"

**Pass Criteria:** Cancel works for in-progress tasks

---

### Test Suite 4: Workflow Builder

#### Test 4.1: Workflow Builder Load

**Objective:** Verify Workflow Builder loads correctly

**Steps:**

1. Navigate to Control Page
2. Click "Workflow Builder" tab
3. Wait for builder to load

**Expected Results:**

- ✅ Builder displays without errors
- ✅ Stepper interface visible
- ✅ One default stage present
- ✅ "Add Stage" button visible
- ✅ "Submit Workflow" button visible

**Pass Criteria:** Builder loads correctly

---

#### Test 4.2: Add Stage

**Objective:** Verify adding stages works

**Steps:**

1. Open Workflow Builder
2. Click "Add Stage" button
3. Observe new stage in stepper

**Expected Results:**

- ✅ New stage appears in stepper
- ✅ Stage numbered correctly
- ✅ Stage configuration fields visible
- ✅ Can add multiple stages

**Pass Criteria:** Stages can be added successfully

---

#### Test 4.3: Remove Stage

**Objective:** Verify removing stages works

**Steps:**

1. Open Workflow Builder
2. Add 2 stages (total 3 stages)
3. Click delete button on middle stage
4. Observe stage removal

**Expected Results:**

- ✅ Delete button visible (when > 1 stage)
- ✅ Stage removed after click
- ✅ Remaining stages renumbered correctly
- ✅ Cannot delete last stage

**Pass Criteria:** Stages can be removed successfully

---

#### Test 4.4: Configure Stage

**Objective:** Verify stage configuration works

**Steps:**

1. Open Workflow Builder
2. Select task type for Stage 1
3. Set priority
4. Set timeout (optional)
5. Fill task-specific parameters

**Expected Results:**

- ✅ Task type dropdown works
- ✅ Priority field accepts 1-20
- ✅ Timeout field accepts numbers
- ✅ Task-specific parameters display correctly
- ✅ Parameters save correctly

**Pass Criteria:** Stage configuration works

---

#### Test 4.5: Submit Workflow

**Objective:** Verify workflow submission works

**Steps:**

1. Open Workflow Builder
2. Configure 2-3 stages
3. Fill all required parameters
4. Click "Submit Workflow" button
5. Observe task creation

**Expected Results:**

- ✅ Submit button enabled when stages configured
- ✅ All tasks spawned successfully
- ✅ Tasks appear in queue
- ✅ Auto-navigation to "Absurd Tasks" tab
- ✅ Tasks have correct priorities

**Pass Criteria:** Workflow submits successfully

---

#### Test 4.6: Workflow Validation

**Objective:** Verify workflow validation works

**Steps:**

1. Open Workflow Builder
2. Add stage without selecting task type
3. Click "Submit Workflow" button

**Expected Results:**

- ✅ Submit button disabled or shows error
- ✅ Error message displayed
- ✅ Invalid stage highlighted

**Pass Criteria:** Validation prevents invalid submissions

---

### Test Suite 5: Real-time Updates

#### Test 5.1: WebSocket Connection

**Objective:** Verify WebSocket connects

**Steps:**

1. Open browser DevTools → Network tab
2. Open Absurd Tasks tab
3. Check for WebSocket connection

**Expected Results:**

- ✅ WebSocket connection established
- ✅ Connection shows as "101 Switching Protocols"
- ✅ No connection errors

**Pass Criteria:** WebSocket connects successfully

---

#### Test 5.2: Task Status Updates

**Objective:** Verify task status updates in real-time

**Steps:**

1. Open Absurd Tasks tab
2. Spawn a test task (via API or Workflow Builder)
3. Observe task appear in list
4. Wait for task to be claimed
5. Observe status change to "In Progress"
6. Wait for task to complete
7. Observe status change to "Completed"

**Expected Results:**

- ✅ Task appears in list within 1 second
- ✅ Status updates automatically (no refresh needed)
- ✅ Status changes: pending → claimed → completed
- ✅ Queue statistics update automatically

**Pass Criteria:** Real-time updates work correctly

---

#### Test 5.3: Queue Statistics Updates

**Objective:** Verify queue statistics update in real-time

**Steps:**

1. Open Absurd Tasks tab
2. Note current statistics
3. Spawn a test task
4. Observe statistics update
5. Complete the task
6. Observe statistics update again

**Expected Results:**

- ✅ Statistics update within 1 second
- ✅ Pending count increases when task spawned
- ✅ Completed count increases when task completes
- ✅ No page refresh needed

**Pass Criteria:** Statistics update in real-time

---

#### Test 5.4: Polling Fallback

**Objective:** Verify polling fallback works when WebSocket disconnected

**Steps:**

1. Open Absurd Tasks tab
2. Disconnect WebSocket (close browser tab, then reopen)
3. Observe task list
4. Spawn a test task
5. Observe task appear (may take up to 5 seconds)

**Expected Results:**

- ✅ Polling activates when WebSocket disconnected
- ✅ Tasks update via polling (every 5 seconds)
- ✅ No errors in console

**Pass Criteria:** Polling fallback works correctly

---

### Test Suite 6: End-to-End Workflows

#### Test 6.1: Simple Conversion Workflow

**Objective:** Verify simple conversion workflow

**Steps:**

1. Open Workflow Builder
2. Add stage: "Convert UVH5 to MS"
3. Configure:
   - Start Time: `2025-11-18 14:00:00`
   - End Time: `2025-11-18 14:05:00`
   - Priority: 15
4. Submit workflow
5. Monitor in Absurd Tasks tab
6. Wait for completion

**Expected Results:**

- ✅ Task spawned successfully
- ✅ Task executes successfully
- ✅ Task completes without errors
- ✅ Result contains MS path

**Pass Criteria:** Simple workflow executes successfully

---

#### Test 6.2: Multi-Stage Workflow

**Objective:** Verify multi-stage workflow execution

**Steps:**

1. Open Workflow Builder
2. Add stages:
   - Stage 1: Convert (Priority 15)
   - Stage 2: Calibration Solve (Priority 12)
   - Stage 3: Imaging (Priority 8)
3. Configure all stages
4. Submit workflow
5. Monitor execution in Absurd Tasks tab
6. Verify execution order

**Expected Results:**

- ✅ All tasks spawned successfully
- ✅ Tasks execute in priority order (15 → 12 → 8)
- ✅ Each stage completes before next starts
- ✅ Final task completes successfully

**Pass Criteria:** Multi-stage workflow executes correctly

---

#### Test 6.3: Failed Task Recovery

**Objective:** Verify failed task can be retried

**Steps:**

1. Spawn a task with invalid parameters (to force failure)
2. Wait for task to fail
3. Open Task Inspector for failed task
4. Review error details
5. Click "Retry Task"
6. Monitor retry execution

**Expected Results:**

- ✅ Task fails as expected
- ✅ Error details visible in inspector
- ✅ Retry creates new task
- ✅ New task executes (may fail again if parameters still invalid)

**Pass Criteria:** Retry functionality works

---

## Test Results Template

### Test Execution Log

| Test ID | Test Name             | Status     | Notes | Tester | Date |
| ------- | --------------------- | ---------- | ----- | ------ | ---- |
| 1.1     | Dashboard Load        | ✅ Pass    | -     | -      | -    |
| 1.2     | Health Status Display | ⏳ Pending | -     | -      | -    |
| ...     | ...                   | ...        | ...   | ...    | ...  |

### Issues Found

| Issue ID | Test ID | Severity | Description              | Status |
| -------- | ------- | -------- | ------------------------ | ------ |
| #1       | 3.1     | Medium   | Retry button not visible | Fixed  |
| ...      | ...     | ...      | ...                      | ...    |

---

## Acceptance Criteria

**Overall Acceptance:**

- ✅ All critical tests (1.x, 2.x, 3.x) pass
- ✅ At least 80% of all tests pass
- ✅ No blocking issues (P0/P1 severity)
- ✅ Real-time updates work correctly
- ✅ End-to-end workflows execute successfully

**Sign-off:**

- [ ] QA Team Lead
- [ ] Operations Team Lead
- [ ] Development Team Lead

---

## Post-Testing

### 1. Issue Reporting

Report all issues found during testing:

- Issue description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/logs
- Severity (P0/P1/P2/P3)

### 2. Feedback Collection

Gather feedback on:

- UI/UX improvements
- Missing features
- Performance concerns
- Documentation gaps

### 3. Test Report

Create test report with:

- Test execution summary
- Pass/fail statistics
- Issues found
- Recommendations

---

**Last Updated:** 2025-11-18

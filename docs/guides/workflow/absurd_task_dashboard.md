# Absurd Task Dashboard User Guide

**Author:** DSA-110 Team  
**Date:** 2025-11-18  
**Audience:** Pipeline Operators, Scientists

---

## Overview

The **Absurd Task Dashboard** provides a real-time interface for monitoring and
managing workflow tasks in the DSA-110 continuum imaging pipeline. Tasks are
executed by the Absurd workflow manager, which provides fault tolerance,
automatic retries, and durable task persistence.

**Key Features:**

- ✅ Real-time task monitoring
- ✅ Queue statistics and health status
- ✅ Task filtering and search
- ✅ Detailed task inspection
- ✅ Retry failed tasks
- ✅ Cancel pending tasks

---

## Accessing the Dashboard

1. Navigate to **Control Page** in the web interface
2. Click the **"Absurd Tasks"** tab (5th tab)
3. The dashboard loads automatically

**URL:** `http://your-server:8000/control` → "Absurd Tasks" tab

---

## Dashboard Layout

### 1. Health Status Card

**Location:** Top of dashboard

**Displays:**

- **Status**: `healthy`, `degraded`, `critical`, or `down`
- **Message**: Brief description of system state
- **Color Coding**:
  - 🟢 Green: Healthy (all systems operational)
  - 🟡 Yellow: Degraded (warnings, but functional)
  - 🔴 Red: Critical (alerts, may need attention)
  - ⚫ Gray: Down (system unavailable)

**Example:**

```
Status: HEALTHY - All systems operational
```

---

### 2. Queue Statistics Cards

**Location:** Below health status

**Displays 6 Metrics:**

| Card            | Description                       | Color     |
| --------------- | --------------------------------- | --------- |
| **Pending**     | Tasks waiting to be claimed       | 🟡 Yellow |
| **In Progress** | Tasks currently being executed    | 🔵 Blue   |
| **Completed**   | Successfully completed tasks      | 🟢 Green  |
| **Failed**      | Tasks that failed (after retries) | 🔴 Red    |
| **Cancelled**   | Manually cancelled tasks          | ⚫ Gray   |
| **Total**       | Total tasks in queue              | 🔵 Blue   |

**Real-time Updates:**

- Statistics update automatically via WebSocket (or polling every 5 seconds)
- No page refresh needed

---

### 3. Status Filter

**Location:** Below statistics cards

**Options:**

- **All Tasks** - Show all tasks regardless of status
- **Pending** - Show only pending tasks
- **In Progress** - Show only claimed/in-progress tasks
- **Completed** - Show only completed tasks
- **Failed** - Show only failed tasks
- **Cancelled** - Show only cancelled tasks

**Usage:**

1. Select filter from dropdown
2. Task list updates immediately
3. Filter persists until changed

---

### 4. Task List Table

**Location:** Below filter

**Columns:**

| Column        | Description                        | Example               |
| ------------- | ---------------------------------- | --------------------- |
| **Task ID**   | Unique task identifier (truncated) | `a1b2c3d4...`         |
| **Task Name** | Type of task                       | `calibration-solve`   |
| **Status**    | Current task status                | `completed`           |
| **Priority**  | Task priority (1-20)               | `15`                  |
| **Retry**     | Number of retry attempts           | `0`                   |
| **Created**   | Task creation timestamp            | `2025-11-18 14:30:00` |
| **Duration**  | Execution time                     | `2.5m`                |
| **Actions**   | View details button                | 👁️                    |

**Status Colors:**

- 🟡 **Pending**: Yellow chip
- 🔵 **In Progress**: Blue chip with spinner
- 🟢 **Completed**: Green chip
- 🔴 **Failed**: Red chip
- ⚫ **Cancelled**: Gray chip

**Priority Colors:**

- 🔴 **15-20**: Red (critical/high priority)
- 🟡 **10-14**: Yellow (high priority)
- 🔵 **5-9**: Blue (normal priority)
- ⚫ **1-4**: Gray (low priority)

**Interactions:**

- **Click row**: Opens Task Inspector with full details
- **Hover**: Highlights row
- **Scroll**: Table is scrollable if many tasks

---

## Task Inspector

**Opens:** When clicking a task row or the "View Details" button

**Sections:**

### 1. Task Information

- **Task ID**: Full UUID
- **Task Name**: Task type
- **Queue Name**: Queue the task belongs to
- **Status**: Current status with icon
- **Priority**: Priority level (1-20)
- **Retry Count**: Number of retry attempts

### 2. Timeline

Shows task lifecycle:

- **Created At**: When task was spawned
- **Claimed At**: When worker claimed the task
- **Completed At**: When task finished (if completed)
- **Wait Time**: Time between creation and claim
- **Execution Time**: Time between claim and completion

### 3. Task Parameters

- **JSON View**: Full task parameters in JSON format
- **Read-only**: Parameters cannot be edited (spawn new task to change)

### 4. Result (Completed Tasks)

- **JSON View**: Task execution result
- **Contains**: Output paths, metrics, artifacts

### 5. Error Details (Failed Tasks)

- **Error Message**: Full error text
- **Read-only**: For reference when retrying

---

## Actions

### Retry Failed Task

**When:** Task status is `failed`

**Steps:**

1. Click failed task to open Task Inspector
2. Click **"Retry Task"** button
3. Confirm in dialog
4. New task spawned with same parameters
5. Task appears in pending queue

**Note:** Retry creates a new task (does not reuse the failed task ID)

---

### Cancel Task

**When:** Task status is `pending` or `claimed` (in progress)

**Steps:**

1. Click task to open Task Inspector
2. Click **"Cancel Task"** button
3. Confirm in dialog
4. Task cancelled immediately
5. Task removed from queue

**Note:** Cannot cancel completed or failed tasks

---

## Real-time Updates

**WebSocket Integration:**

- Tasks update automatically when status changes
- No page refresh needed
- Updates appear within < 1 second

**Polling Fallback:**

- If WebSocket disconnected, falls back to polling every 5 seconds
- Automatic reconnection when WebSocket available

**What Updates:**

- Task status changes (pending → claimed → completed)
- Queue statistics (pending count, completed count, etc.)
- Task details (timeline, result, error)

---

## Common Workflows

### Workflow 1: Monitor Active Tasks

1. Open **Absurd Tasks** tab
2. Filter: **"In Progress"**
3. View tasks currently being executed
4. Click task to see progress details
5. Monitor until completion

---

### Workflow 2: Review Failed Tasks

1. Open **Absurd Tasks** tab
2. Filter: **"Failed"**
3. Review failed tasks
4. Click task to see error details
5. Decide: Retry or investigate further

---

### Workflow 3: Check Queue Health

1. Open **Absurd Tasks** tab
2. Check **Health Status** card
3. Review **Queue Statistics** cards
4. If many pending tasks, consider:
   - Adding more workers
   - Increasing worker concurrency
   - Checking for stuck tasks

---

### Workflow 4: Retry Failed Task

1. Filter: **"Failed"**
2. Click failed task
3. Review error in Task Inspector
4. Click **"Retry Task"**
5. Confirm retry
6. Switch filter to **"Pending"** to see new task
7. Monitor until completion

---

## Tips and Best Practices

### 1. Use Filters Effectively

- **Pending**: Check for tasks waiting too long
- **Failed**: Review errors and retry if needed
- **Completed**: Verify successful execution

### 2. Monitor Queue Depth

- **Pending > 50**: Consider adding workers
- **Pending > 100**: System may be overloaded
- **Failed > 10**: Investigate root cause

### 3. Priority Management

- **High Priority (15-20)**: Time-sensitive tasks
- **Normal Priority (5-9)**: Routine processing
- **Low Priority (1-4)**: Backfill, reprocessing

### 4. Task Inspection

- Always inspect failed tasks before retrying
- Check error details to understand failure
- Review parameters if task fails repeatedly

### 5. Real-time Monitoring

- Keep dashboard open during critical operations
- Watch for status changes in real-time
- Use Task Inspector for detailed progress

---

## Troubleshooting

### Issue: Tasks Not Updating

**Symptoms:** Task status doesn't change in real-time

**Solutions:**

1. Check WebSocket connection (browser console)
2. Refresh page if WebSocket disconnected
3. Check backend logs for errors

---

### Issue: High Pending Count

**Symptoms:** Many tasks stuck in "pending" status

**Solutions:**

1. Check if workers are running: `ps aux | grep run_absurd_worker`
2. Check worker logs for errors
3. Increase worker concurrency or add more workers
4. Check database connectivity

---

### Issue: Many Failed Tasks

**Symptoms:** High failure rate

**Solutions:**

1. Review error details in Task Inspector
2. Check common error patterns
3. Verify task parameters are correct
4. Check system resources (CPU, memory, disk)
5. Review CASA environment and MS file validity

---

### Issue: Task Inspector Not Opening

**Symptoms:** Clicking task doesn't open inspector

**Solutions:**

1. Check browser console for errors
2. Refresh page
3. Try clicking "View Details" button instead of row
4. Check if task still exists (may have been cancelled)

---

## Keyboard Shortcuts

| Shortcut | Action                |
| -------- | --------------------- |
| `R`      | Refresh dashboard     |
| `Esc`    | Close Task Inspector  |
| `F`      | Focus filter dropdown |

---

## Related Documentation

- **[Workflow Builder Guide](absurd_workflow_builder.md)** - Building
  multi-stage workflows
- **[Absurd Operations Guide](absurd_operations.md)** - Backend operations and
  configuration
- **[Performance Tuning Guide](../../architecture/pipeline/absurd_performance_tuning.md)** -
  Optimizing throughput

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

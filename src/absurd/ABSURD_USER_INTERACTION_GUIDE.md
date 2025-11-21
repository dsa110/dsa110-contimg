# Absurd User Interaction Guide

## Overview

This document describes how users would interact with Absurd workflows through
the DSA-110 frontend dashboard. The integration maintains consistency with
existing UI patterns while adding durable execution capabilities.

## User Journey Overview

### Current Flow (Without Absurd)

1. User selects MS files or inputs parameters
2. User clicks "Start Workflow" button
3. Job is created and runs synchronously
4. If job fails, user must manually restart from beginning
5. No visibility into intermediate steps or checkpoints

### New Flow (With Absurd)

1. User selects MS files or inputs parameters
2. User clicks "Start Durable Workflow" button
3. **Workflow is spawned as Absurd task** (with automatic checkpointing)
4. User can monitor progress in real-time
5. **If workflow fails, it automatically retries** from last checkpoint
6. User can see **exact checkpoint state** and resume manually if needed
7. **Long-running workflows survive crashes** and resume automatically

## User Interface Components

### 1. Dashboard Integration

**Location**: Main Dashboard (`/dashboard`)

Add an "Absurd Workflows" section showing:

- Active workflows count
- Queue metrics (pending, running, completed, failed)
- Recent workflow activity

```typescript
// Dashboard shows Absurd metrics alongside existing pipeline status
<Box>
  <Typography variant="h6">Durable Workflows</Typography>
  <Grid container spacing={2}>
    <Grid item xs={3}>
      <MetricCard
        label="Active"
        value={absurdMetrics?.running || 0}
        color="info"
      />
    </Grid>
    <Grid item xs={3}>
      <MetricCard
        label="Pending"
        value={absurdMetrics?.pending || 0}
        color="warning"
      />
    </Grid>
    <Grid item xs={3}>
      <MetricCard
        label="Completed"
        value={absurdMetrics?.completed || 0}
        color="success"
      />
    </Grid>
    <Grid item xs={3}>
      <MetricCard
        label="Failed"
        value={absurdMetrics?.failed || 0}
        color="error"
      />
    </Grid>
  </Grid>
</Box>
```

### 2. Workflow Creation (Enhanced Control Page)

**Location**: `/pipeline/control` (existing ControlPage)

**Enhancement**: Add "Durable Execution" toggle to existing workflow forms

```typescript
// In ConversionWorkflow.tsx, CalibrationWorkflow.tsx, etc.
<FormControlLabel
  control={
    <Switch
      checked={useDurableExecution}
      onChange={(e) => setUseDurableExecution(e.target.checked)}
    />
  }
  label={
    <Box>
      <Typography>Use Durable Execution</Typography>
      <Typography variant="caption" color="text.secondary">
        Enable automatic retries and checkpointing
      </Typography>
    </Box>
  }
/>

{useDurableExecution && (
  <Alert severity="info" sx={{ mt: 1 }}>
    This workflow will automatically retry on failure and resume from checkpoints.
    Progress is saved after each stage.
  </Alert>
)}
```

**User Actions**:

1. Fill in workflow parameters (same as before)
2. Toggle "Use Durable Execution" ON
3. Click "Start Durable Workflow"
4. See confirmation: "Workflow started with task ID: abc-123-def"

### 3. Workflow List View

**Location**: New page `/workflows/absurd` or tab in Pipeline Control

**Features**:

- List all Absurd tasks (filterable by status, queue, task name)
- Real-time updates (auto-refresh every 15 seconds)
- Quick actions: View details, Cancel, Retry

```typescript
// AbsurdWorkflowsPage.tsx
<Box>
  <Typography variant="h4">Durable Workflows</Typography>

  {/* Filters */}
  <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
    <Select value={statusFilter} onChange={handleStatusChange}>
      <MenuItem value="">All Statuses</MenuItem>
      <MenuItem value="pending">Pending</MenuItem>
      <MenuItem value="running">Running</MenuItem>
      <MenuItem value="completed">Completed</MenuItem>
      <MenuItem value="failed">Failed</MenuItem>
    </Select>

    <Select value={queueFilter} onChange={handleQueueChange}>
      <MenuItem value="">All Queues</MenuItem>
      <MenuItem value="dsa110-pipeline">Pipeline</MenuItem>
      <MenuItem value="dsa110-mosaic">Mosaic</MenuItem>
    </Select>

    <TextField
      placeholder="Search tasks..."
      value={searchQuery}
      onChange={(e) => setSearchQuery(e.target.value)}
    />
  </Stack>

  {/* Task List */}
  <Table>
    <TableHead>
      <TableRow>
        <TableCell>Task Name</TableCell>
        <TableCell>Status</TableCell>
        <TableCell>Queue</TableCell>
        <TableCell>Attempt</TableCell>
        <TableCell>Created</TableCell>
        <TableCell>Actions</TableCell>
      </TableRow>
    </TableHead>
    <TableBody>
      {tasks?.map((task) => (
        <TableRow key={task.taskId}>
          <TableCell>{task.taskName}</TableCell>
          <TableCell>
            <Chip
              label={task.status}
              color={getStatusColor(task.status)}
              size="small"
            />
          </TableCell>
          <TableCell>{task.queueName}</TableCell>
          <TableCell>{task.attempt} / {task.maxAttempts || '∞'}</TableCell>
          <TableCell>{formatDate(task.createdAt)}</TableCell>
          <TableCell>
            <IconButton onClick={() => viewTaskDetails(task.taskId)}>
              <Visibility />
            </IconButton>
            {task.status === 'running' && (
              <IconButton onClick={() => cancelTask(task.taskId)}>
                <Cancel />
              </IconButton>
            )}
            {task.status === 'failed' && (
              <IconButton onClick={() => retryTask(task.taskId)}>
                <Refresh />
              </IconButton>
            )}
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</Box>
```

### 4. Workflow Detail View

**Location**: `/workflows/absurd/:taskId`

**Features**:

- Complete task information
- **Checkpoint timeline** (visual progress indicator)
- Step-by-step execution history
- Current state/checkpoint data
- Retry/cancel actions

```typescript
// AbsurdTaskDetailPage.tsx
<Box>
  {/* Header */}
  <Stack direction="row" justifyContent="space-between" alignItems="center">
    <Typography variant="h4">{task.taskName}</Typography>
    <Stack direction="row" spacing={1}>
      <Chip label={task.status} color={getStatusColor(task.status)} />
      {task.status === 'failed' && (
        <Button variant="contained" onClick={handleRetry}>
          Retry Task
        </Button>
      )}
      {task.status === 'running' && (
        <Button variant="outlined" onClick={handleCancel}>
          Cancel Task
        </Button>
      )}
    </Stack>
  </Stack>

  {/* Checkpoint Timeline */}
  <Paper sx={{ p: 2, mt: 2 }}>
    <Typography variant="h6" gutterBottom>Execution Timeline</Typography>
    <Stepper activeStep={currentStepIndex} orientation="vertical">
      {checkpoints.map((checkpoint, index) => (
        <Step key={checkpoint.stepName} completed={checkpoint.status === 'completed'}>
          <StepLabel>
            {checkpoint.stepName}
            {checkpoint.updatedAt && (
              <Typography variant="caption" color="text.secondary">
                {formatDate(checkpoint.updatedAt)}
              </Typography>
            )}
          </StepLabel>
          <StepContent>
            {checkpoint.status === 'completed' && (
              <Alert severity="success">Completed successfully</Alert>
            )}
            {checkpoint.status === 'pending' && (
              <Alert severity="info">Waiting to execute...</Alert>
            )}
            {checkpoint.status === 'failed' && (
              <Alert severity="error">
                Failed: {checkpoint.error}
              </Alert>
            )}

            {/* Show checkpoint state (collapsible) */}
            <Collapse in={expandedCheckpoints.has(checkpoint.stepName)}>
              <Box sx={{ mt: 1, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                <Typography variant="caption" component="pre">
                  {JSON.stringify(checkpoint.state, null, 2)}
                </Typography>
              </Box>
            </Collapse>
          </StepContent>
        </Step>
      ))}
    </Stepper>
  </Paper>

  {/* Task Parameters */}
  <Paper sx={{ p: 2, mt: 2 }}>
    <Typography variant="h6" gutterBottom>Task Parameters</Typography>
    <Box component="pre" sx={{ bgcolor: 'grey.100', p: 1, borderRadius: 1 }}>
      {JSON.stringify(task.params, null, 2)}
    </Box>
  </Paper>

  {/* Run History */}
  <Paper sx={{ p: 2, mt: 2 }}>
    <Typography variant="h6" gutterBottom>Run History</Typography>
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Run ID</TableCell>
          <TableCell>Attempt</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>Started</TableCell>
          <TableCell>Completed</TableCell>
          <TableCell>Result</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {runs?.map((run) => (
          <TableRow key={run.runId}>
            <TableCell>
              <Typography variant="caption" fontFamily="monospace">
                {run.runId.substring(0, 8)}...
              </Typography>
            </TableCell>
            <TableCell>{run.attempt}</TableCell>
            <TableCell>
              <Chip label={run.status} size="small" />
            </TableCell>
            <TableCell>{formatDate(run.startedAt)}</TableCell>
            <TableCell>{formatDate(run.completedAt)}</TableCell>
            <TableCell>
              {run.result && (
                <IconButton onClick={() => viewResult(run.result)}>
                  <Visibility />
                </IconButton>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </Paper>
</Box>
```

### 5. Queue Management

**Location**: `/workflows/absurd/queues` or section in Workflows page

**Features**:

- View all queues and their metrics
- Queue health indicators
- Task distribution across queues

```typescript
// QueueMetricsView.tsx
<Grid container spacing={2}>
  {queues.map((queue) => (
    <Grid item xs={12} md={6} lg={4} key={queue.queueName}>
      <Card>
        <CardContent>
          <Typography variant="h6">{queue.queueName}</Typography>
          <Stack spacing={1} sx={{ mt: 2 }}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Total Tasks
              </Typography>
              <Typography variant="h5">{queue.totalMessages}</Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Queued
              </Typography>
              <Typography variant="h5" color="warning.main">
                {queue.queueLength}
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Visible (Ready)
              </Typography>
              <Typography variant="h5" color="info.main">
                {queue.queueVisibleLength}
              </Typography>
            </Box>
            {queue.oldestMsgAgeSec && (
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Oldest Task Age
                </Typography>
                <Typography variant="body2">
                  {formatDuration(queue.oldestMsgAgeSec)}
                </Typography>
              </Box>
            )}
          </Stack>
          <Button
            fullWidth
            sx={{ mt: 2 }}
            onClick={() => viewQueueTasks(queue.queueName)}
          >
            View Tasks
          </Button>
        </CardContent>
      </Card>
    </Grid>
  ))}
</Grid>
```

## User Interaction Scenarios

### Scenario 1: Starting a Durable Pipeline Workflow

**User Goal**: Run a full pipeline (convert → calibrate → image) with automatic
retry

**Steps**:

1. Navigate to `/pipeline/control`
2. Select "Convert" tab
3. Fill in parameters:
   - Input directory: `/data/incoming`
   - Output directory: `/stage/dsa110-contimg/ms`
   - Time range: `2024-11-17 10:00:00` to `2024-11-17 11:00:00`
4. **Toggle "Use Durable Execution" ON**
5. Click "Start Durable Workflow"
6. See notification: "Workflow started with task ID: abc-123-def"
7. Click "View Workflow" to see progress

**What Happens Behind the Scenes**:

- Workflow is spawned as Absurd task
- Each stage (convert, calibrate, image) becomes a checkpointed step
- If any stage fails, workflow automatically retries from last checkpoint
- User can see progress in real-time

### Scenario 2: Monitoring Long-Running Mosaic Creation

**User Goal**: Monitor a 50-minute mosaic creation that's in progress

**Steps**:

1. Navigate to `/workflows/absurd`
2. Filter by status: "Running"
3. Find mosaic task (task name: "create-mosaic")
4. Click task to view details
5. See checkpoint timeline:
   - ✓ Setup (completed)
   - ✓ Find Transits (completed)
   - ✓ Process Group 1 (completed)
   - ✓ Process Group 2 (completed)
   - → Process Group 3 (in progress) ← Current step
   - ⏳ Process Group 4 (pending)
   - ⏳ Process Group 5 (pending)
   - ...
6. See estimated time remaining based on previous groups
7. Can leave page and return later - workflow continues

**What Happens Behind the Scenes**:

- Each group processing is a checkpointed step
- If process crashes, workflow resumes from last completed group
- Progress is visible in real-time

### Scenario 3: Handling a Failed Workflow

**User Goal**: Investigate and retry a failed workflow

**Steps**:

1. Navigate to `/workflows/absurd`
2. Filter by status: "Failed"
3. Click on failed task
4. View checkpoint timeline:
   - ✓ Setup (completed)
   - ✓ Convert (completed)
   - ✓ Calibrate Solve (completed)
   - ✗ Calibrate Apply (failed) ← Failed here
   - ⏳ Image (not reached)
5. Expand failed checkpoint to see error details
6. Review checkpoint state (what data was available)
7. Click "Retry Task" button
8. Workflow resumes from "Calibrate Apply" step (doesn't redo conversion)

**What Happens Behind the Scenes**:

- Absurd automatically retries failed tasks (based on retry policy)
- User can also manually retry
- Workflow resumes from last successful checkpoint
- No duplicate work (conversion already done)

### Scenario 4: Canceling a Running Workflow

**User Goal**: Stop a workflow that's taking too long

**Steps**:

1. Navigate to `/workflows/absurd`
2. Find running task
3. Click task to view details
4. Click "Cancel Task" button
5. Confirm cancellation
6. Task status changes to "Cancelled"
7. Can see which checkpoint it stopped at

**What Happens Behind the Scenes**:

- Task is marked as cancelled in Absurd
- Worker stops processing the task
- Checkpoint state is preserved (can resume later if needed)

### Scenario 5: Creating a Batch of Mosaics

**User Goal**: Create multiple mosaics with durable execution

**Steps**:

1. Navigate to `/pipeline/control` → Mosaics section
2. Select "Create Multiple Mosaics"
3. Configure:
   - Transit selection: "All available transits"
   - Mosaic parameters: (size, method, etc.)
4. **Toggle "Use Durable Execution" ON**
5. Click "Start Batch"
6. See notification: "Batch workflow started with task ID: xyz-789"
7. Navigate to `/workflows/absurd/:taskId`
8. See progress:
   - Each mosaic is a separate checkpointed step
   - Can see which mosaics completed, which are in progress
   - If one mosaic fails, others continue
   - Failed mosaics can be retried individually

**What Happens Behind the Scenes**:

- Batch workflow spawns as single Absurd task
- Each mosaic creation is a checkpointed step
- Parallel execution where possible
- Individual mosaic failures don't stop the batch

## UI/UX Patterns

### Visual Indicators

**Status Colors** (consistent with existing dashboard):

- `pending`: Blue/Info
- `running`: Yellow/Warning (animated pulse)
- `completed`: Green/Success
- `failed`: Red/Error
- `cancelled`: Grey/Default
- `sleeping`: Purple (waiting for event)

**Checkpoint Timeline**:

- Use Material-UI Stepper component
- Visual progress indicator
- Click to expand checkpoint details
- Color-coded by status

### Real-Time Updates

- Auto-refresh every 15 seconds for list views
- Auto-refresh every 5 seconds for detail views
- Manual refresh button available
- WebSocket support (future enhancement)

### Error Handling

- Clear error messages in failed checkpoints
- Retry button for failed tasks
- Error details in expandable sections
- Link to logs if available

### Performance Considerations

- Pagination for large task lists (25 per page)
- Virtual scrolling for very long lists
- Lazy loading of checkpoint details
- Debounced search/filter

## Integration Points

### 1. Existing Workflow Forms

Enhance existing workflow components:

- `ConversionWorkflow.tsx` → Add durable execution option
- `CalibrationWorkflow.tsx` → Add durable execution option
- `ImagingWorkflow.tsx` → Add durable execution option
- `WorkflowTemplates.tsx` → Include durable execution templates

### 2. Job Management

Enhance `JobManagement.tsx`:

- Show Absurd task ID for durable workflows
- Link to Absurd task detail page
- Show checkpoint status for durable jobs

### 3. Navigation

Add to main navigation:

- "Workflows" → "Durable Workflows" (`/workflows/absurd`)
- Or add tab to Pipeline Control page

### 4. Dashboard

Add Absurd metrics to dashboard:

- Active workflows count
- Queue health indicators
- Recent workflow activity feed

## User Benefits

1. **Reliability**: Workflows survive crashes and automatically resume
2. **Visibility**: See exactly where workflows are in execution
3. **Control**: Cancel, retry, or inspect workflows at any time
4. **Efficiency**: No duplicate work - resumes from checkpoints
5. **Confidence**: Long-running workflows can be safely started and left running

## Example User Flow Diagram

```
User starts workflow
    ↓
Toggle "Durable Execution" ON
    ↓
Click "Start Durable Workflow"
    ↓
Workflow spawned as Absurd task
    ↓
User navigates to Workflows page
    ↓
Sees workflow in "Running" status
    ↓
Clicks workflow to view details
    ↓
Sees checkpoint timeline showing progress
    ↓
Can leave page - workflow continues
    ↓
Returns later to check status
    ↓
Workflow completed - sees final results
```

## Conclusion

The integration provides a seamless user experience where:

- **Existing workflows** can be enhanced with durable execution
- **New durable workflows** are easy to start and monitor
- **Long-running processes** become reliable and observable
- **Failures** are handled gracefully with automatic retries
- **Users** have full visibility and control over workflow execution

The UI maintains consistency with existing DSA-110 dashboard patterns while
adding powerful durable execution capabilities.

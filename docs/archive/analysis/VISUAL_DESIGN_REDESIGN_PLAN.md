# Visual Design Redesign & Fix Plan

**Date:** 2025-11-13  
**Based on:** Visual Design Critique  
**Status:** Planning Phase

---

## Overview

This document provides a detailed, actionable plan for redesigning and fixing
visual issues across all dashboard pages. Each page includes:

- Specific issues to address
- Component-level changes
- Implementation steps
- Priority level
- Estimated effort

---

## Page-by-Page Redesign Plans

### 1. Dashboard Page (`/dashboard`)

#### Issues to Fix

1. Navigation bar overcrowding (14 links)
2. Redundant breadcrumbs ("Dashboard > dashboard")
3. Panel layout inconsistency
4. No color coding for status indicators
5. Plain empty state
6. ESE table lacks visual emphasis
7. High information density

#### Redesign Plan

**1.1 Navigation Bar Simplification**

- **Action:** Group navigation links into categories
- **Implementation:**
  ```typescript
  // Create NavigationGroup component
  const navigationGroups = {
    monitoring: ["Dashboard", "Pipeline", "Health"],
    control: ["Control", "Streaming", "Operations"],
    data: ["Data", "Mosaics", "Sources"],
    analysis: ["QA Visualization", "Sky View", "Observing"],
    system: ["Events", "Cache"],
  };
  ```
- **Files to modify:**
  - `frontend/src/components/Navigation.tsx`
  - Create `frontend/src/components/NavigationGroup.tsx`
- **Priority:** High
- **Effort:** 4-6 hours

**1.2 Breadcrumbs Fix**

- **Action:** Hide breadcrumbs on top-level pages
- **Implementation:**
  ```typescript
  // In WorkflowBreadcrumbs.tsx
  const shouldShowBreadcrumbs = breadcrumbs.length > 1;
  if (!shouldShowBreadcrumbs) return null;
  ```
- **Files to modify:**
  - `frontend/src/components/WorkflowBreadcrumbs.tsx`
- **Priority:** Medium
- **Effort:** 1 hour

**1.3 Panel Layout Standardization**

- **Action:** Use consistent 3-column grid for top row
- **Implementation:**
  ```typescript
  <Grid container spacing={3}>
    <Grid item xs={12} md={4}>
      <PipelineStatusCard />
    </Grid>
    <Grid item xs={12} md={4}>
      <SystemHealthCard />
    </Grid>
    <Grid item xs={12} md={4}>
      <RecentObservationsCard />
    </Grid>
  </Grid>
  ```
- **Files to modify:**
  - `frontend/src/pages/DashboardPage.tsx`
- **Priority:** Medium
- **Effort:** 2 hours

**1.4 Status Color Coding**

- **Action:** Add color indicators for all metrics
- **Implementation:**

  ```typescript
  // Create StatusIndicator component
  const getStatusColor = (value: number, thresholds: Thresholds) => {
    if (value >= thresholds.good) return 'success';
    if (value >= thresholds.warning) return 'warning';
    return 'error';
  };

  // Apply to CPU, Memory, Disk
  <Chip
    label={`CPU: ${cpu}%`}
    color={getStatusColor(cpu, { good: 70, warning: 50 })}
  />
  ```

- **Files to create:**
  - `frontend/src/components/StatusIndicator.tsx`
- **Files to modify:**
  - `frontend/src/pages/DashboardPage.tsx`
- **Priority:** High
- **Effort:** 3-4 hours

**1.5 Enhanced Empty State**

- **Action:** Add icon and helpful message
- **Implementation:**
  ```typescript
  <EmptyState
    icon={<InboxIcon />}
    title="No recent observations"
    description="Observations will appear here once the pipeline processes data"
    action={<Button>View Pipeline Status</Button>}
  />
  ```
- **Files to create:**
  - `frontend/src/components/EmptyState.tsx`
- **Files to modify:**
  - `frontend/src/pages/DashboardPage.tsx`
- **Priority:** Medium
- **Effort:** 2 hours

**1.6 ESE Table Enhancement**

- **Action:** Color-code σ values and add visual emphasis
- **Implementation:**

  ```typescript
  const getSigmaColor = (sigma: number) => {
    if (sigma >= 8) return 'error';
    if (sigma >= 6) return 'warning';
    return 'default';
  };

  <TableCell>
    <Chip
      label={`${sigma}σ`}
      color={getSigmaColor(sigma)}
      size="small"
    />
  </TableCell>
  ```

- **Files to modify:**
  - `frontend/src/pages/DashboardPage.tsx`
- **Priority:** High
- **Effort:** 2 hours

**1.7 Information Density Optimization**

- **Action:** Add collapsible sections
- **Implementation:**
  ```typescript
  <Accordion>
    <AccordionSummary>ESE Candidates (5)</AccordionSummary>
    <AccordionDetails>
      <ESETable />
    </AccordionDetails>
  </Accordion>
  ```
- **Files to modify:**
  - `frontend/src/pages/DashboardPage.tsx`
- **Priority:** Low
- **Effort:** 3 hours

---

### 2. Sources Page (`/sources`)

#### Issues to Fix

1. Empty state is too sparse
2. Search UX needs improvement
3. Lacks visual interest

#### Redesign Plan

**2.1 Enhanced Empty State**

- **Action:** Add statistics cards and quick actions
- **Implementation:**

  ```typescript
  <Box>
    <Grid container spacing={3}>
      <Grid item xs={12} md={4}>
        <StatCard
          title="Total Sources"
          value={totalSources}
          icon={<TableChartIcon />}
        />
      </Grid>
      <Grid item xs={12} md={4}>
        <StatCard
          title="ESE Candidates"
          value={eseCount}
          icon={<ScienceIcon />}
        />
      </Grid>
      <Grid item xs={12} md={4}>
        <StatCard
          title="High Variability"
          value={highVariabilityCount}
          icon={<TrendingUpIcon />}
        />
      </Grid>
    </Grid>

    <Divider sx={{ my: 3 }} />

    <Typography variant="h6" gutterBottom>
      Quick Filters
    </Typography>
    <Stack direction="row" spacing={2}>
      <Chip
        label="ESE Candidates"
        onClick={() => handleQuickFilter('ese')}
        clickable
      />
      <Chip
        label="High Variability"
        onClick={() => handleQuickFilter('variability')}
        clickable
      />
    </Stack>
  </Box>
  ```

- **Files to create:**
  - `frontend/src/components/StatCard.tsx`
- **Files to modify:**
  - `frontend/src/pages/SourcesPage.tsx`
- **Priority:** High
- **Effort:** 4-5 hours

**2.2 Search UX Improvements**

- **Action:** Enable Enter key, add suggestions, improve feedback
- **Implementation:**

  ```typescript
  // Add Enter key handler
  <TextField
    onKeyDown={(e) => {
      if (e.key === 'Enter' && searchTerm.trim()) {
        handleSearch();
      }
    }}
    placeholder="Search by Source ID (e.g., NVSS J123456.7+420312)"
    InputProps={{
      endAdornment: (
        <InputAdornment position="end">
          <IconButton onClick={handleSearch} disabled={!searchTerm.trim()}>
            <SearchIcon />
          </IconButton>
        </InputAdornment>
      )
    }}
  />

  // Add search suggestions
  <Autocomplete
    freeSolo
    options={recentSearches}
    renderInput={(params) => <TextField {...params} />}
  />
  ```

- **Files to modify:**
  - `frontend/src/pages/SourcesPage.tsx`
  - Add search history to localStorage
- **Priority:** Medium
- **Effort:** 3-4 hours

**2.3 Recent Activity Feed**

- **Action:** Add recent source updates section
- **Implementation:**
  ```typescript
  <Paper sx={{ p: 2, mt: 3 }}>
    <Typography variant="h6" gutterBottom>
      Recent Activity
    </Typography>
    <List>
      {recentActivity.map((activity) => (
        <ListItem>
          <ListItemIcon>
            <ActivityIcon />
          </ListItemIcon>
          <ListItemText
            primary={activity.sourceId}
            secondary={`${activity.type} - ${formatTime(activity.timestamp)}`}
          />
        </ListItem>
      ))}
    </List>
  </Paper>
  ```
- **Files to modify:**
  - `frontend/src/pages/SourcesPage.tsx`
  - Add API endpoint for recent activity
- **Priority:** Low
- **Effort:** 4-5 hours

---

### 3. Data Browser Page (`/data`)

#### Issues to Fix

1. Loading state needs skeleton loader
2. Empty state needs improvement
3. Title hierarchy needs adjustment

#### Redesign Plan

**3.1 Skeleton Loader**

- **Action:** Replace spinner with skeleton screens
- **Implementation:**

  ```typescript
  // Create DataBrowserSkeleton component
  const DataBrowserSkeleton = () => (
    <Box>
      <Skeleton variant="rectangular" height={56} sx={{ mb: 2 }} />
      <Skeleton variant="rectangular" height={400} />
    </Box>
  );

  // Use in DataBrowserPage
  {isLoading ? <DataBrowserSkeleton /> : <DataTable />}
  ```

- **Files to create:**
  - `frontend/src/components/DataBrowserSkeleton.tsx`
- **Files to modify:**
  - `frontend/src/pages/DataBrowserPage.tsx`
- **Priority:** Medium
- **Effort:** 2-3 hours

**3.2 Enhanced Empty State**

- **Action:** Add icon, message, and action buttons
- **Implementation:**
  ```typescript
  <EmptyState
    icon={<StorageIcon sx={{ fontSize: 64 }} />}
    title="No data products found"
    description="Data products will appear here once the pipeline processes observations"
    actions={[
      <Button key="pipeline" onClick={() => navigate('/pipeline')}>
        View Pipeline
      </Button>,
      <Button key="control" onClick={() => navigate('/control')}>
        Start Processing
      </Button>
    ]}
  />
  ```
- **Files to modify:**
  - `frontend/src/pages/DataBrowserPage.tsx`
  - Reuse `EmptyState` component from Dashboard
- **Priority:** Medium
- **Effort:** 1-2 hours

**3.3 Title Hierarchy Fix**

- **Action:** Change from h4 to h1 for page title
- **Implementation:**
  ```typescript
  <Typography variant="h1" component="h1" gutterBottom>
    Data Browser
  </Typography>
  ```
- **Files to modify:**
  - `frontend/src/pages/DataBrowserPage.tsx`
- **Priority:** Low
- **Effort:** 5 minutes

---

### 4. Operations Page (`/operations`)

#### Issues to Fix

1. Table too wide (9 columns)
2. Error types need color coding
3. Too many action buttons per row
4. Statistics cards need color coding

#### Redesign Plan

**4.1 Responsive Table Columns**

- **Action:** Make columns collapsible and responsive
- **Implementation:**
  ```typescript
  // Use DataGrid with column visibility toggle
  <DataGrid
    columns={columns}
    rows={rows}
    columnVisibilityModel={columnVisibility}
    onColumnVisibilityModelChange={setColumnVisibility}
    slots={{
      toolbar: GridToolbar,
    }}
    initialState={{
      columns: {
        columnVisibilityModel: {
          // Hide less important columns by default on mobile
          errorMessage: false,
          retryCount: false,
        },
      },
    }}
  />
  ```
- **Files to modify:**
  - `frontend/src/pages/OperationsPage.tsx`
  - Consider migrating to MUI DataGrid
- **Priority:** High
- **Effort:** 6-8 hours

**4.2 Error Type Color Coding**

- **Action:** Color-code error types by severity
- **Implementation:**

  ```typescript
  const getErrorTypeColor = (errorType: string): ChipColor => {
    const criticalErrors = ['RuntimeError', 'ValueError', 'KeyError'];
    const warningErrors = ['Warning', 'UserWarning'];

    if (criticalErrors.includes(errorType)) return 'error';
    if (warningErrors.includes(errorType)) return 'warning';
    return 'default';
  };

  <Chip
    label={errorType}
    color={getErrorTypeColor(errorType)}
    size="small"
  />
  ```

- **Files to modify:**
  - `frontend/src/pages/OperationsPage.tsx`
- **Priority:** High
- **Effort:** 2 hours

**4.3 Action Buttons Optimization**

- **Action:** Use icon buttons with dropdown menu
- **Implementation:**
  ```typescript
  <IconButton onClick={(e) => setMenuAnchor(e.currentTarget)}>
    <MoreVertIcon />
  </IconButton>
  <Menu
    anchorEl={menuAnchor}
    open={Boolean(menuAnchor)}
    onClose={() => setMenuAnchor(null)}
  >
    <MenuItem onClick={handleViewDetails}>
      <ListItemIcon><VisibilityIcon /></ListItemIcon>
      View Details
    </MenuItem>
    <MenuItem onClick={handleRetry}>
      <ListItemIcon><RefreshIcon /></ListItemIcon>
      Retry
    </MenuItem>
    <MenuItem onClick={handleResolve}>
      <ListItemIcon><CheckIcon /></ListItemIcon>
      Resolve
    </MenuItem>
    <Divider />
    <MenuItem onClick={handleMarkFailed} sx={{ color: 'error.main' }}>
      <ListItemIcon><CancelIcon color="error" /></ListItemIcon>
      Mark as Failed
    </MenuItem>
  </Menu>
  ```
- **Files to modify:**
  - `frontend/src/pages/OperationsPage.tsx`
- **Priority:** Medium
- **Effort:** 3-4 hours

**4.4 Statistics Cards Color Coding**

- **Action:** Add color indicators to stat cards
- **Implementation:**
  ```typescript
  <StatCard
    title="Pending"
    value={pendingCount}
    icon={<ScheduleIcon />}
    color={pendingCount > 5 ? 'error' : 'default'}
    trend={pendingTrend}
  />
  ```
- **Files to modify:**
  - `frontend/src/pages/OperationsPage.tsx`
  - Enhance StatCard component
- **Priority:** Medium
- **Effort:** 2 hours

---

### 5. Health Page (`/health`)

#### Issues to Fix

1. **CRITICAL:** JavaScript error (dayjs not defined)
2. Error display shows full stack trace
3. Need to review layout once fixed

#### Redesign Plan

**5.1 Fix dayjs Import Error**

- **Action:** Fix missing dayjs import
- **Implementation:**

  ```typescript
  // In HealthPage.tsx, add import
  import dayjs from "dayjs";

  // Or check if dayjs is installed
  // npm install dayjs
  ```

- **Files to modify:**
  - `frontend/src/pages/HealthPage.tsx`
  - Check `frontend/package.json` for dayjs dependency
- **Priority:** **CRITICAL**
- **Effort:** 30 minutes

**5.2 Error Boundary Enhancement**

- **Action:** Hide stack traces in production, show user-friendly messages
- **Implementation:**

  ```typescript
  // In ErrorBoundary component
  const isDevelopment = import.meta.env.DEV;

  {isDevelopment && (
    <Box>
      <Typography variant="h6">Error Details (Development Mode):</Typography>
      <pre>{error.stack}</pre>
    </Box>
  )}

  {!isDevelopment && (
    <Alert severity="error">
      <AlertTitle>Something went wrong</AlertTitle>
      <Typography>
        We encountered an error. Please try refreshing the page or contact support.
      </Typography>
      <Button onClick={handleRetry}>Try Again</Button>
    </Alert>
  )}
  ```

- **Files to modify:**
  - `frontend/src/components/ErrorBoundary.tsx`
- **Priority:** High
- **Effort:** 2 hours

**5.3 Health Page Layout Review**

- **Action:** Review and improve layout once error is fixed
- **Implementation:**
  - Wait for error fix, then review actual page content
  - Apply same improvements as other pages (color coding, skeleton loaders,
    etc.)
- **Priority:** Medium
- **Effort:** TBD after fix

---

### 6. Pipeline Page (`/pipeline`)

#### Issues to Fix

1. Summary cards all same size
2. Success rate not visually alarming
3. Duration formatting hard to read
4. Stage table needs more detail

#### Redesign Plan

**6.1 Summary Cards Hierarchy**

- **Action:** Make critical metrics larger and more prominent
- **Implementation:**

  ```typescript
  <Grid container spacing={3}>
    {/* Critical metrics - larger */}
    <Grid item xs={12} md={6}>
      <StatCard
        title="Success Rate"
        value={`${successRate}%`}
        size="large"
        color={getSuccessRateColor(successRate)}
        alert={successRate < 50}
      />
    </Grid>
    <Grid item xs={12} md={6}>
      <StatCard
        title="Failed"
        value={failedCount}
        size="large"
        color="error"
        alert={failedCount > 0}
      />
    </Grid>

    {/* Regular metrics */}
    <Grid item xs={6} md={3}>
      <StatCard title="Total Jobs" value={totalJobs} />
    </Grid>
    {/* ... */}
  </Grid>
  ```

- **Files to modify:**
  - `frontend/src/pages/PipelinePage.tsx`
  - Enhance StatCard to support sizes
- **Priority:** High
- **Effort:** 3-4 hours

**6.2 Success Rate Visual Emphasis**

- **Action:** Add color coding and warning styling
- **Implementation:**

  ```typescript
  const getSuccessRateColor = (rate: number) => {
    if (rate >= 80) return 'success';
    if (rate >= 50) return 'warning';
    return 'error';
  };

  <StatCard
    title="Success Rate"
    value={`${successRate}%`}
    color={getSuccessRateColor(successRate)}
    icon={successRate < 50 ? <WarningIcon /> : <CheckCircleIcon />}
    alert={successRate < 50}
    alertMessage={successRate < 50 ? "Low success rate detected" : undefined}
  />
  ```

- **Files to modify:**
  - `frontend/src/pages/PipelinePage.tsx`
- **Priority:** High
- **Effort:** 2 hours

**6.3 Duration Formatting**

- **Action:** Format durations in human-readable format
- **Implementation:**

  ```typescript
  // Create utility function
  const formatDuration = (minutes: number): string => {
    if (minutes < 60) return `${minutes.toFixed(1)} min`;
    if (minutes < 1440) return `${(minutes / 60).toFixed(1)} hours`;
    return `${(minutes / 1440).toFixed(1)} days`;
  };

  // Use in component
  <Typography>{formatDuration(1037.3)}</Typography>
  // Output: "17.3 hours"
  ```

- **Files to create:**
  - `frontend/src/utils/formatDuration.ts`
- **Files to modify:**
  - `frontend/src/pages/PipelinePage.tsx`
- **Priority:** Medium
- **Effort:** 1 hour

**6.4 Enhanced Stage Table**

- **Action:** Add progress bars and expandable details
- **Implementation:**
  ```typescript
  <TableRow>
    <TableCell>{stage.name}</TableCell>
    <TableCell>
      <Chip label={stage.status} color={getStatusColor(stage.status)} />
    </TableCell>
    <TableCell>
      {stage.status === 'running' && (
        <Box>
          <LinearProgress
            variant="determinate"
            value={stage.progress}
            sx={{ mb: 1 }}
          />
          <Typography variant="caption">
            {stage.progress}% - ETA: {formatDuration(stage.eta)}
          </Typography>
        </Box>
      )}
      {stage.status !== 'running' && formatDuration(stage.duration)}
    </TableCell>
    <TableCell>
      <IconButton onClick={() => toggleDetails(stage.id)}>
        <ExpandMoreIcon />
      </IconButton>
    </TableCell>
  </TableRow>
  {expandedStages.includes(stage.id) && (
    <TableRow>
      <TableCell colSpan={4}>
        <StageDetails stage={stage} />
      </TableCell>
    </TableRow>
  )}
  ```
- **Files to create:**
  - `frontend/src/components/StageDetails.tsx`
- **Files to modify:**
  - `frontend/src/pages/PipelinePage.tsx`
- **Priority:** Medium
- **Effort:** 4-5 hours

---

### 7. Control Page (`/control`)

#### Issues to Fix

1. Layout too complex
2. Empty table columns
3. Inconsistent status display
4. Form layout needs improvement
5. Truncated job types

#### Redesign Plan

**7.1 Layout Simplification**

- **Action:** Use collapsible sections and better visual separation
- **Implementation:**

  ```typescript
  <Accordion defaultExpanded>
    <AccordionSummary>
      <Typography variant="h6">Measurement Sets</Typography>
    </AccordionSummary>
    <AccordionDetails>
      <MeasurementSetsTable />
    </AccordionDetails>
  </Accordion>

  <Accordion>
    <AccordionSummary>
      <Typography variant="h6">Quick Pipeline Workflow</Typography>
    </AccordionSummary>
    <AccordionDetails>
      <PipelineWorkflowForm />
    </AccordionDetails>
  </Accordion>
  ```

- **Files to modify:**
  - `frontend/src/pages/ControlPage.tsx`
- **Priority:** Medium
- **Effort:** 4-5 hours

**7.2 Hide Empty Columns**

- **Action:** Conditionally show columns only when they have data
- **Implementation:**
  ```typescript
  const columns = [
    { field: "name", headerName: "MS Name" },
    { field: "time", headerName: "Time" },
    { field: "calibrator", headerName: "Calibrator" },
    // Only show if any row has quality data
    ...(rows.some((r) => r.quality)
      ? [{ field: "quality", headerName: "Quality" }]
      : []),
    ...(rows.some((r) => r.size)
      ? [{ field: "size", headerName: "Size" }]
      : []),
  ];
  ```
- **Files to modify:**
  - `frontend/src/pages/ControlPage.tsx`
- **Priority:** Low
- **Effort:** 2 hours

**7.3 Consistent Status Display**

- **Action:** Use chips/icons for all statuses
- **Implementation:**
  ```typescript
  <TableCell>
    <Stack direction="row" spacing={1}>
      {row.calibrated && (
        <Chip
          icon={<CheckIcon />}
          label="Cal"
          color="success"
          size="small"
        />
      )}
      {row.imaged && (
        <Chip
          icon={<ImageIcon />}
          label="Img"
          color="success"
          size="small"
        />
      )}
      {!row.calibrated && !row.imaged && (
        <Chip
          label="Pending"
          color="default"
          size="small"
        />
      )}
    </Stack>
  </TableCell>
  ```
- **Files to modify:**
  - `frontend/src/pages/ControlPage.tsx`
- **Priority:** Medium
- **Effort:** 2-3 hours

**7.4 Form Layout Improvement**

- **Action:** Group related fields, improve spacing
- **Implementation:**

  ```typescript
  <Paper sx={{ p: 3 }}>
    <Typography variant="h6" gutterBottom>
      Time Range
    </Typography>
    <Grid container spacing={2}>
      <Grid item xs={12} md={6}>
        <TextField label="Start Time" fullWidth />
      </Grid>
      <Grid item xs={12} md={6}>
        <TextField label="End Time" fullWidth />
      </Grid>
    </Grid>

    <Divider sx={{ my: 3 }} />

    <Typography variant="h6" gutterBottom>
      Directories
    </Typography>
    <Grid container spacing={2}>
      {/* ... */}
    </Grid>
  </Paper>
  ```

- **Files to modify:**
  - `frontend/src/pages/ControlPage.tsx`
- **Priority:** Medium
- **Effort:** 3-4 hours

**7.5 Job Type Display Fix**

- **Action:** Show full names with tooltips
- **Implementation:**

  ```typescript
  <TableCell>
    <Tooltip title={getFullJobTypeName(job.type)}>
      <Chip
        label={job.type}
        size="small"
        onClick={() => handleJobClick(job.id)}
        clickable
      />
    </Tooltip>
  </TableCell>

  const getFullJobTypeName = (type: string) => {
    const mapping = {
      'ese-d': 'ESE Detection',
      'calibra': 'Calibration',
      'workfl': 'Workflow',
    };
    return mapping[type] || type;
  };
  ```

- **Files to modify:**
  - `frontend/src/pages/ControlPage.tsx`
- **Priority:** Low
- **Effort:** 1-2 hours

---

### 8. QA Visualization Page (`/qa`)

#### Issues to Fix

1. Loading state needs skeleton
2. Input fields too large
3. Redundant titles
4. No visual feedback

#### Redesign Plan

**8.1 Skeleton Loader**

- **Action:** Add skeleton for file list
- **Implementation:**
  ```typescript
  const DirectoryBrowserSkeleton = () => (
    <Box>
      {[1, 2, 3, 4, 5].map((i) => (
        <Skeleton key={i} variant="rectangular" height={56} sx={{ mb: 1 }} />
      ))}
    </Box>
  );
  ```
- **Files to create:**
  - `frontend/src/components/DirectoryBrowserSkeleton.tsx`
- **Files to modify:**
  - `frontend/src/pages/QAPage.tsx`
- **Priority:** Medium
- **Effort:** 1-2 hours

**8.2 Compact Input Fields**

- **Action:** Reduce input field size, add helpful placeholders
- **Implementation:**
  ```typescript
  <Grid container spacing={2}>
    <Grid item xs={12} md={6}>
      <TextField
        label="Include Pattern"
        placeholder="*.fits, *.image.fits"
        size="small"
        fullWidth
        helperText="File patterns to include"
      />
    </Grid>
    <Grid item xs={12} md={6}>
      <TextField
        label="Exclude Pattern"
        placeholder="*.tmp, *.log"
        size="small"
        fullWidth
        helperText="File patterns to exclude"
      />
    </Grid>
  </Grid>
  ```
- **Files to modify:**
  - `frontend/src/pages/QAPage.tsx`
- **Priority:** Low
- **Effort:** 1 hour

**8.3 Remove Redundant Title**

- **Action:** Remove section title, keep tab title
- **Implementation:**

  ```typescript
  // Remove this:
  <Typography variant="h6">Directory Browser</Typography>

  // Keep only tab title
  ```

- **Files to modify:**
  - `frontend/src/pages/QAPage.tsx`
- **Priority:** Low
- **Effort:** 5 minutes

**8.4 Visual Feedback**

- **Action:** Add preview of expected file list structure
- **Implementation:**
  ```typescript
  <Alert severity="info" sx={{ mb: 2 }}>
    <AlertTitle>Directory Browser</AlertTitle>
    Browse and select FITS files, CASA tables, or QA reports from the file system.
    Use the path input above or click through the breadcrumbs to navigate.
  </Alert>
  ```
- **Files to modify:**
  - `frontend/src/pages/QAPage.tsx`
- **Priority:** Low
- **Effort:** 1 hour

---

### 9. Streaming Page (`/streaming`)

#### Issues to Fix

1. Empty resource usage panel
2. Status indicator needs color
3. Visual hierarchy needs improvement

#### Redesign Plan

**9.1 Resource Usage Panel Enhancement**

- **Action:** Show placeholder or hide when empty
- **Implementation:**
  ```typescript
  {serviceStatus === 'running' ? (
    <ResourceUsagePanel data={resourceData} />
  ) : (
    <Paper sx={{ p: 3, textAlign: 'center' }}>
      <Typography color="text.secondary">
        Resource usage will appear when the service is running
      </Typography>
    </Paper>
  )}
  ```
- **Files to modify:**
  - `frontend/src/pages/StreamingPage.tsx`
- **Priority:** Medium
- **Effort:** 1-2 hours

**9.2 Status Indicator Color Coding**

- **Action:** Use red for stopped, green for running
- **Implementation:**
  ```typescript
  <Chip
    icon={serviceStatus === 'running' ? <PlayArrowIcon /> : <StopIcon />}
    label={serviceStatus === 'running' ? 'Running' : 'Stopped'}
    color={serviceStatus === 'running' ? 'success' : 'error'}
    size="large"
    sx={{ fontSize: '1rem', py: 2 }}
  />
  ```
- **Files to modify:**
  - `frontend/src/pages/StreamingPage.tsx`
- **Priority:** High
- **Effort:** 1 hour

**9.3 Visual Hierarchy Improvement**

- **Action:** Make status more prominent
- **Implementation:**

  ```typescript
  <Grid container spacing={3}>
    {/* Status - larger, more prominent */}
    <Grid item xs={12}>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>
          Service Status
        </Typography>
        <StatusChip status={serviceStatus} size="large" />
      </Paper>
    </Grid>

    {/* Other panels - smaller */}
    <Grid item xs={12} md={4}>
      <ResourceUsagePanel />
    </Grid>
    {/* ... */}
  </Grid>
  ```

- **Files to modify:**
  - `frontend/src/pages/StreamingPage.tsx`
- **Priority:** Medium
- **Effort:** 2 hours

---

### 10. Events Page (`/events`)

#### Issues to Fix

1. Empty state needs improvement
2. Filter layout needs work
3. Lacks visual interest

#### Redesign Plan

**10.1 Enhanced Empty State**

- **Action:** Add icon, explanation, and examples
- **Implementation:**
  ```typescript
  <EmptyState
    icon={<EventNoteIcon sx={{ fontSize: 64 }} />}
    title="No events found"
    description="Events are system notifications about pipeline activities, errors, and status changes."
    actions={[
      <Button key="clear" onClick={handleClearFilters}>
        Clear Filters
      </Button>,
      <Button key="refresh" onClick={handleRefresh}>
        Refresh
      </Button>
    ]}
  >
    <Box sx={{ mt: 2 }}>
      <Typography variant="body2" color="text.secondary">
        Example event types:
      </Typography>
      <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
        <Chip label="pipeline.started" size="small" />
        <Chip label="calibration.completed" size="small" />
        <Chip label="error.occurred" size="small" />
      </Stack>
    </Box>
  </EmptyState>
  ```
- **Files to modify:**
  - `frontend/src/pages/EventsPage.tsx`
- **Priority:** Medium
- **Effort:** 2-3 hours

**10.2 Filter Layout Improvement**

- **Action:** Better spacing, add clear button, show active count
- **Implementation:**

  ```typescript
  <Paper sx={{ p: 2, mb: 2 }}>
    <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
      <FormControl size="small" sx={{ minWidth: 200 }}>
        <InputLabel>Event Type</InputLabel>
        <Select value={eventType} onChange={handleEventTypeChange}>
          <MenuItem value="">All Types</MenuItem>
          {/* ... */}
        </Select>
      </FormControl>

      <TextField
        label="Limit"
        type="number"
        size="small"
        value={limit}
        onChange={handleLimitChange}
        sx={{ width: 100 }}
      />

      <TextField
        label="Since (minutes)"
        type="number"
        size="small"
        value={since}
        onChange={handleSinceChange}
        sx={{ width: 150 }}
      />

      <Chip
        label={`${activeFilterCount} filters active`}
        onDelete={handleClearFilters}
        deleteIcon={<ClearIcon />}
      />
    </Stack>
  </Paper>
  ```

- **Files to modify:**
  - `frontend/src/pages/EventsPage.tsx`
- **Priority:** Medium
- **Effort:** 2-3 hours

**10.3 Statistics Summary**

- **Action:** Add statistics even when no events
- **Implementation:**
  ```typescript
  <Grid container spacing={2} sx={{ mb: 2 }}>
    <Grid item xs={12} md={4}>
      <StatCard title="Total Events" value={totalEvents} />
    </Grid>
    <Grid item xs={12} md={4}>
      <StatCard title="Event Types" value={eventTypeCount} />
    </Grid>
    <Grid item xs={12} md={4}>
      <StatCard title="Last Event" value={formatTime(lastEventTime)} />
    </Grid>
  </Grid>
  ```
- **Files to modify:**
  - `frontend/src/pages/EventsPage.tsx`
- **Priority:** Low
- **Effort:** 2 hours

---

### 11. Cache Page (`/cache`)

#### Issues to Fix

1. Progress bar colors misleading
2. Statistics cards need context
3. Clear cache button needs confirmation

#### Redesign Plan

**11.1 Progress Bar Color Fix**

- **Action:** Use appropriate colors for hit/miss rates
- **Implementation:**

  ```typescript
  const getProgressColor = (value: number, type: 'hit' | 'miss') => {
    if (value === 0) return 'default'; // Grey for zero
    if (type === 'hit') {
      if (value >= 80) return 'success';
      if (value >= 50) return 'warning';
      return 'error';
    } else {
      // For miss rate, reverse the logic
      if (value <= 20) return 'success';
      if (value <= 50) return 'warning';
      return 'error';
    }
  };

  <LinearProgress
    variant="determinate"
    value={hitRate}
    color={getProgressColor(hitRate, 'hit')}
  />
  ```

- **Files to modify:**
  - `frontend/src/pages/CachePage.tsx`
- **Priority:** High
- **Effort:** 2 hours

**11.2 Statistics Cards Context**

- **Action:** Add timestamps and trends
- **Implementation:**
  ```typescript
  <StatCard
    title="Total Keys"
    value={totalKeys}
    subtitle={`Last activity: ${formatTime(lastActivity)}`}
    trend={keysTrend}
    trendLabel="vs last hour"
  />
  ```
- **Files to modify:**
  - `frontend/src/pages/CachePage.tsx`
  - Enhance StatCard component
- **Priority:** Medium
- **Effort:** 3-4 hours

**11.3 Clear Cache Confirmation**

- **Action:** Add confirmation dialog
- **Implementation:**

  ```typescript
  const [confirmOpen, setConfirmOpen] = useState(false);

  <Button
    color="error"
    onClick={() => setConfirmOpen(true)}
    startIcon={<DeleteIcon />}
  >
    Clear All Cache
  </Button>

  <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
    <DialogTitle>Clear All Cache?</DialogTitle>
    <DialogContent>
      <Typography>
        This will remove all cached data. This action cannot be undone.
        Are you sure you want to continue?
      </Typography>
    </DialogContent>
    <DialogActions>
      <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
      <Button
        color="error"
        onClick={handleClearCache}
        variant="contained"
      >
        Clear Cache
      </Button>
    </DialogActions>
  </Dialog>
  ```

- **Files to modify:**
  - `frontend/src/pages/CachePage.tsx`
- **Priority:** Medium
- **Effort:** 1-2 hours

---

## Cross-Page Improvements

### 1. Shared Components to Create

**1.1 EmptyState Component**

```typescript
// frontend/src/components/EmptyState.tsx
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actions?: React.ReactNode[];
  children?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actions,
  children
}) => (
  <Box sx={{ textAlign: 'center', py: 8 }}>
    {icon && <Box sx={{ mb: 2 }}>{icon}</Box>}
    <Typography variant="h5" gutterBottom>{title}</Typography>
    {description && (
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {description}
      </Typography>
    )}
    {actions && (
      <Stack direction="row" spacing={2} justifyContent="center">
        {actions}
      </Stack>
    )}
    {children}
  </Box>
);
```

**1.2 StatCard Component**

```typescript
// frontend/src/components/StatCard.tsx
interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  color?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  size?: 'small' | 'medium' | 'large';
  trend?: number;
  trendLabel?: string;
  subtitle?: string;
  alert?: boolean;
  alertMessage?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  color = 'default',
  size = 'medium',
  trend,
  trendLabel,
  subtitle,
  alert,
  alertMessage
}) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography
            variant={size === 'large' ? 'h3' : size === 'medium' ? 'h4' : 'h5'}
            color={color !== 'default' ? `${color}.main` : 'text.primary'}
          >
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        {icon && <Box sx={{ color: `${color}.main` }}>{icon}</Box>}
      </Stack>
      {trend !== undefined && (
        <Box sx={{ mt: 1 }}>
          <TrendIndicator value={trend} label={trendLabel} />
        </Box>
      )}
      {alert && alertMessage && (
        <Alert severity="warning" sx={{ mt: 2 }}>{alertMessage}</Alert>
      )}
    </CardContent>
  </Card>
);
```

**1.3 StatusIndicator Component**

```typescript
// frontend/src/components/StatusIndicator.tsx
interface StatusIndicatorProps {
  value: number;
  thresholds: { good: number; warning: number };
  label: string;
  unit?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  value,
  thresholds,
  label,
  unit = '%'
}) => {
  const getColor = () => {
    if (value >= thresholds.good) return 'success';
    if (value >= thresholds.warning) return 'warning';
    return 'error';
  };

  return (
    <Chip
      icon={<CircleIcon sx={{ fontSize: 8 }} />}
      label={`${label}: ${value}${unit}`}
      color={getColor()}
      size="small"
    />
  );
};
```

**1.4 Skeleton Loaders**

- Create reusable skeleton components for each page type
- Use consistent skeleton patterns

### 2. Design System Implementation

**2.1 Color Palette**

- Create theme file with status colors
- Apply consistently across all components

**2.2 Typography Scale**

- Standardize heading levels
- Create typography variants

**2.3 Spacing System**

- Use 8px base unit consistently
- Create spacing utilities

**2.4 Component Patterns**

- Document button hierarchy
- Standardize table designs
- Create form patterns

---

## Implementation Priority

### Phase 1: Critical Fixes (Week 1)

1. Fix Health page dayjs error
2. Add color coding to status indicators
3. Fix navigation bar overcrowding
4. Improve empty states

### Phase 2: High-Impact Improvements (Week 2)

5. Add skeleton loaders
6. Enhance table designs
7. Improve typography hierarchy
8. Standardize spacing

### Phase 3: Polish & Optimization (Week 3)

9. Add visual flourishes
10. Optimize information density
11. Enhance error messages
12. Add micro-interactions

---

## Estimated Total Effort

- **Phase 1:** 20-25 hours
- **Phase 2:** 30-40 hours
- **Phase 3:** 15-20 hours
- **Total:** 65-85 hours

---

## Success Metrics

- All pages load without errors
- Consistent visual design across pages
- Improved user feedback (color coding, status indicators)
- Better information hierarchy
- Reduced cognitive load
- Improved accessibility

---

## Next Steps

1. Review and approve this plan
2. Create shared component library
3. Implement Phase 1 fixes
4. Test and iterate
5. Move to Phase 2 and 3

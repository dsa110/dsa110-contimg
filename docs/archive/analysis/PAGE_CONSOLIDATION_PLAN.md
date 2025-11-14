# Page Consolidation Plan

**Date:** 2025-11-13  
**Goal:** Consolidate related pages into unified interfaces for better UX and
reduced navigation complexity

---

## Current Page Analysis

### Current Pages (14 total)

1. Dashboard - Overview and status
2. Control - MS management, pipeline workflows
3. Streaming - Streaming service control
4. Data - Data browser
5. QA Visualization - QA tools
6. Mosaics - Mosaic gallery
7. Sources - Source monitoring
8. Sky View - Sky visualization
9. Observing - Observation management
10. Health - System health
11. Operations - DLQ, circuit breakers
12. Pipeline - Pipeline monitoring
13. Events - Event stream
14. Cache - Cache statistics

---

## Consolidation Strategy

### Principle: Group by User Workflow

Pages should be consolidated based on:

1. **Related functionality** - Pages that serve similar purposes
2. **User workflows** - Pages users navigate between frequently
3. **Information hierarchy** - Pages that show different views of the same data
4. **Context switching** - Pages that benefit from being viewed together

---

## Proposed Consolidated Pages

### 1. Pipeline & Operations → "Pipeline Operations"

**Rationale:**

- Pipeline monitoring, Operations (DLQ), and Events all relate to pipeline
  execution and debugging
- Users often need to see pipeline status AND failed operations together
- Events provide context for pipeline issues
- All are monitoring/debugging tools

**Consolidated Structure:**

```
Pipeline Operations Page
├── Tab: Overview
│   ├── Pipeline Summary (current Pipeline page summary)
│   ├── Active Executions (current Pipeline page)
│   └── Quick Stats (DLQ count, event count)
│
├── Tab: Executions
│   ├── Active Executions (from Pipeline page)
│   ├── Execution History (from Pipeline page)
│   └── Stage Metrics (from Pipeline page)
│
├── Tab: Operations
│   ├── Dead Letter Queue (current Operations page)
│   ├── Circuit Breakers (current Operations page)
│   └── Error Statistics
│
├── Tab: Events
│   ├── Event Stream (current Events page)
│   ├── Event Statistics (current Events page)
│   └── Event Filters
│
└── Tab: Dependency Graph
    └── (from Pipeline page)
```

**Benefits:**

- Single place for all pipeline debugging
- Can correlate events with failed operations
- See pipeline status while investigating issues
- Reduced navigation

**Implementation:**

- Merge 3 pages into 1 with tabs
- Keep all existing functionality
- Add cross-tab linking (e.g., click event → see related operation)

---

### 2. Data Browser, Mosaics, Sources, Sky View → "Data Explorer"

**Rationale:**

- All are about viewing/exploring data products
- Users often want to see source details alongside images
- Sky View and Sources are closely related (sources on sky map)
- Mosaics are collections of images (related to Data Browser)
- Natural workflow: Browse data → View mosaic → Check sources → See on sky

**Consolidated Structure:**

```
Data Explorer Page
├── Tab: Browser
│   ├── Data Browser (current Data page)
│   ├── File list/grid
│   └── Filters
│
├── Tab: Mosaics
│   ├── Mosaic Gallery (current Mosaics page)
│   ├── Mosaic viewer
│   └── Mosaic metadata
│
├── Tab: Sources
│   ├── Source Search (current Sources page)
│   ├── Source Table
│   ├── Source Details (when selected)
│   └── Light Curves
│
├── Tab: Sky View
│   ├── Interactive Sky Map (current Sky View page)
│   ├── Source Overlay
│   ├── Observation Overlay
│   └── Controls
│
└── Unified Workspace Mode (optional)
    ├── Split view: Source list + Sky map
    ├── Split view: Image + Light curve
    └── Multi-pane view
```

**Benefits:**

- Natural workflow: browse → view → analyze
- Can show source on sky map while viewing details
- Unified search across all data types
- Better context switching

**Implementation:**

- Merge 4 pages into 1 with tabs
- Add unified search bar
- Enable multi-pane views
- Cross-tab linking (select source → show on sky map)

---

### 3. Control, Streaming, Observing → "Pipeline Control"

**Rationale:**

- All are about controlling/managing the pipeline
- Control has MS management and workflows
- Streaming is a service that processes incoming data
- Observing manages observations
- Users need to coordinate these activities

**Consolidated Structure:**

```
Pipeline Control Page
├── Tab: Measurement Sets
│   ├── MS Table (from Control page)
│   ├── MS Filters
│   └── MS Actions
│
├── Tab: Workflows
│   ├── Quick Pipeline Workflow (from Control page)
│   ├── Convert Tab (from Control page)
│   ├── Calibrate Tab (from Control page)
│   ├── Apply Tab (from Control page)
│   └── Image Tab (from Control page)
│
├── Tab: Streaming
│   ├── Service Status (from Streaming page)
│   ├── Configuration (from Streaming page)
│   ├── Queue Statistics (from Streaming page)
│   └── Resource Usage (from Streaming page)
│
├── Tab: Observing
│   ├── Observation Management (from Observing page)
│   ├── Schedule
│   └── Status
│
└── Sidebar: Recent Jobs
    └── (from Control page)
```

**Benefits:**

- Single control center for pipeline
- Can start workflow and monitor streaming
- Better coordination between services
- Unified job management

**Implementation:**

- Merge 3 pages into 1 with tabs
- Keep sidebar for recent jobs
- Add status indicators across tabs

---

### 4. QA Visualization, Health, Cache → "System Diagnostics"

**Rationale:**

- All are diagnostic/analysis tools
- Health and Cache are both system monitoring
- QA is data quality analysis (related to system health)
- Users investigating issues need all diagnostic info

**Consolidated Structure:**

```
System Diagnostics Page
├── Tab: System Health
│   ├── System Monitoring (from Health page)
│   ├── Queue Status (from Health page)
│   ├── Operations Health (from Health page)
│   └── QA Diagnostics (from Health page)
│
├── Tab: QA Tools
│   ├── Directory Browser (from QA page)
│   ├── FITS Viewer (from QA page)
│   ├── CASA Table Viewer (from QA page)
│   └── Notebook Generator (from QA page)
│
├── Tab: Cache
│   ├── Cache Statistics (from Cache page)
│   ├── Keys (from Cache page)
│   └── Performance (from Cache page)
│
└── Tab: Diagnostics Dashboard
    ├── Combined health metrics
    ├── System status overview
    └── Quick actions
```

**Benefits:**

- All diagnostics in one place
- Can correlate QA issues with system health
- Better for troubleshooting
- Unified diagnostic workflow

**Implementation:**

- Merge 3 pages into 1 with tabs
- Add combined dashboard view
- Cross-reference data between tabs

---

## Final Navigation Structure

### After Consolidation: 4 Main Pages + Dashboard

1. **Dashboard** - Overview (unchanged)
2. **Pipeline Operations** - Pipeline monitoring, operations, events
3. **Data Explorer** - Data browser, mosaics, sources, sky view
4. **Pipeline Control** - Control panel, streaming, observing
5. **System Diagnostics** - Health, QA, cache

**Navigation Bar:**

```
[Dashboard] [Pipeline Operations] [Data Explorer] [Pipeline Control] [System Diagnostics] [Workflow] [⌨️]
```

**Reduction:** 14 pages → 5 pages (64% reduction)

---

## Detailed Consolidation Plans

### Consolidation 1: Pipeline Operations

**Pages to Merge:**

- `/pipeline` → Tab: Executions
- `/operations` → Tab: Operations
- `/events` → Tab: Events

**New Route:** `/pipeline-operations`

**Component Structure:**

```typescript
// frontend/src/pages/PipelineOperationsPage.tsx
const PipelineOperationsPage = () => {
  return (
    <Box>
      <Typography variant="h1">Pipeline Operations</Typography>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tab label="Overview" />
        <Tab label="Executions" />
        <Tab label="Operations" />
        <Tab label="Events" />
        <Tab label="Dependency Graph" />
      </Tabs>

      <TabPanel value="overview">
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <PipelineSummaryCard />
          </Grid>
          <Grid item xs={12} md={4}>
            <DLQSummaryCard />
          </Grid>
          <Grid item xs={12} md={4}>
            <EventSummaryCard />
          </Grid>
        </Grid>
        <RecentActivityTimeline />
      </TabPanel>

      <TabPanel value="executions">
        {/* Current Pipeline page content */}
        <PipelineExecutions />
      </TabPanel>

      <TabPanel value="operations">
        {/* Current Operations page content */}
        <OperationsManagement />
      </TabPanel>

      <TabPanel value="events">
        {/* Current Events page content */}
        <EventStream />
      </TabPanel>

      <TabPanel value="dependency">
        <DependencyGraph />
      </TabPanel>
    </Box>
  );
};
```

**Cross-Tab Features:**

- Click failed operation → Show related events
- Click event → Show related execution
- Unified search across all tabs
- Shared filters (time range, component, etc.)

---

### Consolidation 2: Data Explorer

**Pages to Merge:**

- `/data` → Tab: Browser
- `/mosaics` → Tab: Mosaics
- `/sources` → Tab: Sources
- `/sky` → Tab: Sky View

**New Route:** `/data-explorer`

**Component Structure:**

```typescript
// frontend/src/pages/DataExplorerPage.tsx
const DataExplorerPage = () => {
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [workspaceMode, setWorkspaceMode] = useState(false);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h1">Data Explorer</Typography>
        <Button onClick={() => setWorkspaceMode(!workspaceMode)}>
          {workspaceMode ? 'Tab View' : 'Workspace View'}
        </Button>
      </Box>

      {workspaceMode ? (
        <UnifiedWorkspace
          leftPane={<SourceList onSelect={setSelectedSource} />}
          centerPane={<SkyMap source={selectedSource} />}
          rightPane={<SourceDetails source={selectedSource} />}
        />
      ) : (
        <>
          <Tabs value={activeTab} onChange={setActiveTab}>
            <Tab label="Browser" />
            <Tab label="Mosaics" />
            <Tab label="Sources" />
            <Tab label="Sky View" />
          </Tabs>

          <TabPanel value="browser">
            <DataBrowser
              onImageSelect={setSelectedImage}
              onSourceSelect={setSelectedSource}
            />
          </TabPanel>

          <TabPanel value="mosaics">
            <MosaicGallery
              onMosaicSelect={setSelectedImage}
            />
          </TabPanel>

          <TabPanel value="sources">
            <SourceSearch
              onSourceSelect={(source) => {
                setSelectedSource(source);
                setActiveTab('sky'); // Switch to sky view
              }}
            />
          </TabPanel>

          <TabPanel value="sky">
            <SkyView
              selectedSource={selectedSource}
              onSourceClick={setSelectedSource}
            />
          </TabPanel>
        </>
      )}
    </Box>
  );
};
```

**Unified Features:**

- Global search across all data types
- Cross-tab navigation (select source → show on sky)
- Shared filters (time range, observation, etc.)
- Unified workspace mode for multi-pane views

---

### Consolidation 3: Pipeline Control

**Pages to Merge:**

- `/control` → Tabs: Measurement Sets, Workflows
- `/streaming` → Tab: Streaming
- `/observing` → Tab: Observing

**New Route:** `/pipeline-control`

**Component Structure:**

```typescript
// frontend/src/pages/PipelineControlPage.tsx
const PipelineControlPage = () => {
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={9}>
        <Typography variant="h1">Pipeline Control</Typography>

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tab label="Measurement Sets" />
          <Tab label="Workflows" />
          <Tab label="Streaming" />
          <Tab label="Observing" />
        </Tabs>

        <TabPanel value="ms">
          <MeasurementSetsTable />
        </TabPanel>

        <TabPanel value="workflows">
          <PipelineWorkflowTabs />
        </TabPanel>

        <TabPanel value="streaming">
          <StreamingServiceControl />
        </TabPanel>

        <TabPanel value="observing">
          <ObservingManagement />
        </TabPanel>
      </Grid>

      <Grid item xs={12} md={3}>
        <Paper sx={{ p: 2, position: 'sticky', top: 80 }}>
          <Typography variant="h6" gutterBottom>
            Recent Jobs
          </Typography>
          <RecentJobsList />

          <Divider sx={{ my: 2 }} />

          <Typography variant="h6" gutterBottom>
            Job Logs
          </Typography>
          <JobLogsViewer />
        </Paper>
      </Grid>
    </Grid>
  );
};
```

**Unified Features:**

- Sidebar with recent jobs (persistent across tabs)
- Status indicators showing service states
- Quick actions accessible from any tab
- Unified job management

---

### Consolidation 4: System Diagnostics

**Pages to Merge:**

- `/health` → Tab: System Health
- `/qa` → Tab: QA Tools
- `/cache` → Tab: Cache

**New Route:** `/system-diagnostics`

**Component Structure:**

```typescript
// frontend/src/pages/SystemDiagnosticsPage.tsx
const SystemDiagnosticsPage = () => {
  return (
    <Box>
      <Typography variant="h1">System Diagnostics</Typography>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tab label="Dashboard" />
        <Tab label="System Health" />
        <Tab label="QA Tools" />
        <Tab label="Cache" />
      </Tabs>

      <TabPanel value="dashboard">
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <SystemHealthSummary />
          </Grid>
          <Grid item xs={12} md={4}>
            <QASummary />
          </Grid>
          <Grid item xs={12} md={4}>
            <CacheSummary />
          </Grid>
        </Grid>
        <SystemStatusTimeline />
      </TabPanel>

      <TabPanel value="health">
        <SystemHealthTabs />
      </TabPanel>

      <TabPanel value="qa">
        <QAToolsTabs />
      </TabPanel>

      <TabPanel value="cache">
        <CacheTabs />
      </TabPanel>
    </Box>
  );
};
```

**Unified Features:**

- Combined dashboard showing all diagnostics
- Cross-reference between health, QA, and cache
- Unified alerting system
- Quick diagnostic actions

---

## Migration Strategy

### Phase 1: Create Consolidated Pages (Week 1)

1. Create new page components
2. Move existing content into tabs
3. Add cross-tab features
4. Test functionality

### Phase 2: Update Navigation (Week 1-2)

1. Update routes
2. Update navigation component
3. Add redirects from old routes
4. Update breadcrumbs

### Phase 3: Enhance Features (Week 2-3)

1. Add unified search
2. Add cross-tab linking
3. Add workspace modes
4. Add shared filters

### Phase 4: Remove Old Pages (Week 3)

1. Remove old page components
2. Remove old routes
3. Update documentation
4. Final testing

---

## Benefits Summary

### User Experience

- **64% reduction** in navigation complexity (14 → 5 pages)
- **Better context** - related information together
- **Faster workflows** - less navigation between pages
- **Unified search** - find anything from one place

### Technical

- **Less code duplication** - shared components
- **Better state management** - unified context
- **Easier maintenance** - fewer pages to maintain
- **Better performance** - less route switching

### Information Architecture

- **Logical grouping** - pages grouped by purpose
- **Workflow optimization** - pages follow user workflows
- **Reduced cognitive load** - less to remember
- **Better discoverability** - related features together

---

## Alternative: Hybrid Approach

If full consolidation is too aggressive, consider a hybrid:

### Keep Separate but Group in Navigation:

- Dashboard (standalone)
- Pipeline Operations (Pipeline + Operations + Events)
- Data Explorer (Data + Mosaics + Sources + Sky)
- Control (standalone, but add Streaming and Observing as sub-pages)
- Diagnostics (Health + QA + Cache)

This gives 5 main navigation items but keeps some pages separate for users who
prefer direct access.

---

## Recommendation

**Full Consolidation** is recommended because:

1. Related functionality naturally belongs together
2. Users benefit from seeing related information together
3. Reduces navigation complexity significantly
4. Enables powerful features like unified search and workspace modes
5. Better aligns with user workflows

The consolidation maintains all existing functionality while improving
organization and discoverability.

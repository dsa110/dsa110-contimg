# Control and MS Browser Page Unification Analysis

**Date:** 2025-01-27  
**Status:** Design Proposal  
**Purpose:** Analyze feasibility and approach for unifying Control and MS
Browser pages

---

## Current State

### Control Page (`/control`)

**Primary Purpose:** Manual job execution for selected Measurement Sets

**Layout:**

- **Left Panel:** Measurement Sets browser
  - MS list table with filters (Calibrator, Status)
  - Search functionality
  - Select MS for job submission
- **Right Panel:** Recent Jobs
  - Job list with status indicators
  - Job type, status, MS path
- **Bottom Right:** Job Logs
  - Live log streaming (SSE)
  - Job details and artifacts
- **Main Area:** Job submission forms
  - Tabs: Convert, Calibrate, Apply, Image, Workflow
  - Form-based job configuration

**MS Browser Features:**

- MS list display
- Filter by calibrator and status
- Sortable columns
- MS selection for job submission
- Basic MS metadata (path, timestamps, status)

### MS Browser Page (`/ms-browser`)

**Primary Purpose:** MS inspection and analysis (CASA listobs-like
functionality)

**Layout:**

- **Top Section:** Measurement Sets table
  - Similar MS list to Control page
  - Same filters (Calibrator, Status)
  - Search functionality
- **Bottom Panel:** Inspection/Analysis tools
  - **MS Inspection Tab:** listobs-like summary
    - MS metadata details
    - Observation summary
    - Field information
    - Spectral window details
  - **MS Comparison Tab:** Compare multiple MS files
    - Side-by-side comparison
    - Difference analysis
  - **Related Products Tab:** Show related data products
    - Calibration tables
    - Images
    - Catalogs
    - Processing history

---

## Analysis

### Overlap

1. **MS List Display:** Both pages show the same MS table with identical filters
2. **MS Selection:** Both allow selecting MS files (for different purposes)
3. **Filters:** Same filter options (Calibrator, Status, Search)
4. **Metadata Display:** Basic MS information shown in both

### Differences

1. **Control Page Focus:**
   - Job execution workflow
   - Job management and monitoring
   - Form-based job submission
   - Live log streaming

2. **MS Browser Page Focus:**
   - MS inspection and analysis
   - Detailed MS metadata (listobs-like)
   - MS comparison tools
   - Related products discovery

### User Workflows

**Control Page Workflow:**

1. User wants to run a job (calibrate, apply, image)
2. Selects MS from list
3. Configures job parameters
4. Submits job
5. Monitors job progress

**MS Browser Workflow:**

1. User wants to inspect/analyze MS files
2. Selects MS from list
3. Views detailed inspection (listobs summary)
4. Compares MS files if needed
5. Explores related products

---

## Unification Proposal

### Option 1: Enhanced Control Page (Recommended)

**Approach:** Add MS Browser's inspection/comparison features to Control page

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ Control Panel                                           │
├──────────────────┬──────────────────────────────────────┤
│ Measurement Sets │ Job Submission Forms                 │
│                  │ (Convert, Calibrate, Apply, Image)   │
│ [MS Table]      │                                      │
│                  │                                      │
│                  │                                      │
├──────────────────┴──────────────────────────────────────┤
│ MS Details Panel (Collapsible/Expandable)               │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Tabs: [Inspection] [Comparison] [Related Products]│ │
│ │                                                    │ │
│ │ [Selected MS inspection details]                  │ │
│ │                                                    │ │
│ └────────────────────────────────────────────────────┘ │
├──────────────────┬──────────────────────────────────────┤
│ Recent Jobs      │ Job Logs                              │
│                  │                                       │
└──────────────────┴──────────────────────────────────────┘
```

**Benefits:**

- Single page for all MS-related operations
- Contextual inspection: select MS → view details → submit job
- Reduced navigation overhead
- Unified MS selection experience
- Can collapse inspection panel when not needed

**Implementation:**

- Add collapsible bottom panel to Control page
- Port MS Inspection, Comparison, Related Products components
- Maintain existing job submission workflow
- Add toggle to show/hide inspection panel

### Option 2: Enhanced MS Browser Page

**Approach:** Add job submission capabilities to MS Browser page

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ MS Browser                                               │
├─────────────────────────────────────────────────────────┤
│ Measurement Sets Table                                   │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ MS Details Panel                                         │
│ Tabs: [Inspection] [Comparison] [Related Products]      │
│                                                          │
├──────────────────┬──────────────────────────────────────┤
│ Quick Actions    │ Job Management                       │
│ [Calibrate]      │ [Recent Jobs]                        │
│ [Apply]          │ [Job Logs]                          │
│ [Image]          │                                      │
└──────────────────┴──────────────────────────────────────┘
```

**Benefits:**

- MS-centric workflow
- Inspection-first approach
- Can add job submission as secondary action

**Drawbacks:**

- Less prominent job submission (primary use case)
- May feel cluttered with both inspection and job features

### Option 3: Keep Separate, Share Components

**Approach:** Extract shared MS Browser component, use in both pages

**Benefits:**

- Maintains separation of concerns
- Reusable components
- Each page optimized for its purpose

**Drawbacks:**

- Still requires navigation between pages
- Duplicate MS list maintenance
- User confusion about which page to use

---

## Recommendation: Option 1 (Enhanced Control Page)

### Rationale

1. **Primary Use Case:** Control page is the primary interface for job
   execution, which is the most common workflow
2. **Contextual Workflow:** Users often need to inspect MS before submitting
   jobs - having inspection in the same page provides better context
3. **Reduced Navigation:** Single page reduces cognitive load and navigation
   overhead
4. **Progressive Disclosure:** Inspection panel can be collapsed when not
   needed, keeping focus on job submission
5. **Unified Experience:** One place for all MS-related operations

### Implementation Plan

#### Phase 1: Component Extraction

1. Extract MS Browser table component (shared)
2. Extract MS Inspection component
3. Extract MS Comparison component
4. Extract Related Products component

#### Phase 2: Integration

1. Add collapsible MS Details panel to Control page
2. Integrate inspection/comparison/related products tabs
3. Connect MS selection to inspection panel
4. Add toggle button to show/hide panel

#### Phase 3: Navigation Update

1. Remove MS Browser from main navigation
2. Update breadcrumbs and routing
3. Add redirect from `/ms-browser` to `/control` (with inspection panel open)
4. Update documentation

#### Phase 4: UX Refinement

1. Add keyboard shortcuts (e.g., 'I' to toggle inspection panel)
2. Remember panel state in localStorage
3. Smooth transitions and animations
4. Responsive layout adjustments

### Layout Details

**Default State (Job Submission Focus):**

- MS list visible (left)
- Job forms visible (main area)
- Inspection panel collapsed/minimized
- Jobs and logs visible (right)

**Inspection State (MS Analysis Focus):**

- MS list visible (left)
- Job forms minimized/collapsed
- Inspection panel expanded (main area)
- Jobs and logs visible (right, smaller)

**Toggle Mechanism:**

- Button in MS table header: "Inspect Selected MS"
- Keyboard shortcut: 'I' key
- Click on MS row (if configured)
- Panel can be resized/dragged

### Component Structure

```
ControlPage
├── MSBrowserPanel (left)
│   ├── MSListTable
│   ├── MSFilters
│   └── MSSearch
├── JobSubmissionArea (main, collapsible)
│   ├── JobTabs (Convert, Calibrate, Apply, Image, Workflow)
│   └── JobForms
├── MSDetailsPanel (bottom, collapsible)
│   ├── TabBar (Inspection, Comparison, Related Products)
│   ├── MSInspectionTab
│   ├── MSComparisonTab
│   └── RelatedProductsTab
└── JobManagementPanel (right)
    ├── RecentJobsTable
    └── JobLogsPanel
```

---

## Migration Considerations

### User Impact

- **Low:** MS Browser users can still access all features via Control page
- **Positive:** Better integrated workflow
- **Training:** Minimal - features remain the same, just relocated

### Technical Impact

- **Moderate:** Component refactoring required
- **Low Risk:** Can maintain backward compatibility with redirects
- **Testing:** Need to verify all inspection features work in new context

### Documentation Updates

- Update navigation guides
- Update user workflows
- Update API documentation if routes change
- Update screenshots and tutorials

---

## Alternative: Hybrid Approach

If full unification is too disruptive, consider:

1. **Keep MS Browser as separate page** for deep inspection workflows
2. **Add quick inspection panel** to Control page (simplified version)
3. **Link between pages:** "View Full Inspection" button opens MS Browser with
   selected MS

This provides:

- Quick access to inspection from Control
- Full-featured inspection in dedicated page
- Flexibility for different user needs

---

## Conclusion

Unifying Control and MS Browser pages makes sense because:

1. They share the same MS list and filters
2. Inspection often precedes job submission
3. Reduces navigation and cognitive load
4. Provides better context for MS selection

**Recommended Approach:** Option 1 (Enhanced Control Page) with collapsible
inspection panel provides the best balance of functionality and usability.

**Next Steps:**

1. Review with stakeholders
2. Create detailed component breakdown
3. Implement Phase 1 (component extraction)
4. User testing with prototype
5. Full implementation

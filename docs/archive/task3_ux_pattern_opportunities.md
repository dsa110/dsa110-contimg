# Task 3 UX Patterns - Opportunity Analysis

**Date:** 2025-11-13  
**Status:** analysis-complete  
**Related:** [Task 3 UX Final Integration](task3_ux_final_integration.md)

---

## Summary

Comprehensive analysis of where breadcrumbs, validation, confirmation dialogs,
and sparklines would be most useful across the application.

## 1. Breadcrumbs Opportunities

### High Priority (User Navigation)

**Detail Pages** (8 pages) - Users navigate deep into data, need clear path
back:

- ✅ `SourceDetailPage.tsx` - `/sources/:sourceId`
- ✅ `ImageDetailPage.tsx` - `/images/:imageId`
- ✅ `DataDetailPage.tsx` - `/data/:type/:id`
- ✅ `MosaicViewPage.tsx` - `/mosaics/:mosaicId`
- ✅ `QACartaPage.tsx` - `/qa/carta` (nested route)

**Primary Pages** (12 pages) - Main navigation pages:

- ✅ `OperationsPage.tsx` - `/operations` (DLQ management)
- ✅ `HealthPage.tsx` - `/health` (System diagnostics)
- ✅ `SourceMonitoringPage.tsx` - `/sources` (Source monitoring)
- ✅ `QAVisualizationPage.tsx` - `/qa` (QA tools)
- ✅ `StreamingPage.tsx` - `/streaming` (Streaming service)
- ✅ `EventsPage.tsx` - `/events` (Event log)
- ✅ `CachePage.tsx` - `/cache` (Cache statistics)
- ✅ `SkyViewPage.tsx` - `/sky` (Sky visualization)
- ✅ `MosaicGalleryPage.tsx` - `/mosaics` (Mosaic gallery)
- ✅ `ObservingPage.tsx` - `/observing` (Observing interface)
- ✅ `SystemDiagnosticsPage.tsx` - `/system-diagnostics` (if different from
  HealthPage)
- ✅ `DataExplorerPage.tsx` - `/data-explorer` (if different from
  DataBrowserPage)

**Total:** 20 pages would benefit from breadcrumbs

### Implementation Priority

1. **Detail Pages** (High) - Users get lost without breadcrumbs
2. **Primary Pages** (Medium) - Improves navigation clarity
3. **Nested Routes** (High) - `/qa/carta` especially needs breadcrumbs

## 2. Validation Opportunities

### High Priority Forms

**CalibrationWorkflow.tsx** - Multiple fields need validation:

- ✅ **Field ID** (`calibParams.field`)
  - Pattern: Should match field ID format or be empty for auto-detect
  - Validation: Optional, but if provided should be valid format
- ✅ **Reference Antenna** (`calibParams.refant`)
  - Required when calibrating
  - Validation: Must exist in MS antenna list (already has warning, but should
    be validation)
- ✅ **Gain Solution Interval** (`calibParams.gain_solint`)
  - Pattern: `"inf"` or time format like `"60s"`, `"10min"`
  - Validation: Pattern matching for valid time intervals
- ✅ **Minimum PB Response** (`calibParams.min_pb`)
  - Range: 0.0 - 1.0
  - Validation: Number range validation (already has inputProps, but should use
    ValidatedTextField)

**ImagingWorkflow.tsx** - Parameter validation:

- ✅ **W-projection planes** (`imageParams.wprojplanes`)
  - Range: -1 (auto) or >= 1
  - Validation: Integer validation, range check
- ✅ **Mask Radius** (`imageParams.mask_radius_arcsec`)
  - Range: 10 - 300 arcsec
  - Validation: Number range validation (already has inputProps, but should use
    ValidatedTextField)

**SourceMonitoringPage.tsx** - Search and filter validation:

- ✅ **Source ID** (`sourceId`)
  - Pattern: Valid source identifier format
  - Validation: Pattern matching, optional but should validate format if
    provided
- ✅ **Variability Threshold** (`variabilityThreshold`)
  - Range: 0 - 100 (sigma)
  - Validation: Number range validation

**OperationsPage.tsx** - Filter validation:

- ✅ **Component Filter** (`componentFilter`)
  - Validation: Should validate against known components
- ✅ **Status Filter** (`statusFilter`)
  - Validation: Should validate against known statuses

**DataBrowserPage.tsx** - Search validation:

- ✅ **Search Query** (`searchQuery`)
  - Validation: Optional, but could validate against known patterns

**StreamingPage.tsx** - Configuration validation:

- ✅ Any configuration fields (if present)
  - Validation: Time ranges, paths, etc.

### Medium Priority Forms

**QAVisualizationPage.tsx** - QA parameter forms **SkyViewPage.tsx** -
Coordinate/field selection forms **ObservingPage.tsx** - Observation
configuration forms

### Implementation Priority

1. **CalibrationWorkflow** (High) - Most complex form, most validation needed
2. **ImagingWorkflow** (High) - Critical parameters need validation
3. **SourceMonitoringPage** (Medium) - Search validation improves UX
4. **OperationsPage** (Medium) - Filter validation prevents errors

## 3. Confirmation Dialog Opportunities

### High Priority (Destructive Actions)

**CachePage.tsx** - Already has clear dialog, but should use
`ConfirmationDialog`:

- ✅ **Clear Cache** (`clearCacheMutation`)
  - Current: Custom Dialog component
  - Should: Use `ConfirmationDialog` with severity="warning"
  - Impact: Destructive - clears all cache data

**StreamingPage.tsx** - Already has dialogs, but should use
`ConfirmationDialog`:

- ✅ **Stop Streaming** (`stopMutation`)
  - Current: Custom Dialog
  - Should: Use `ConfirmationDialog` with severity="error"
  - Impact: Critical - stops data ingestion
- ✅ **Restart Streaming** (`restartMutation`)
  - Current: Custom Dialog
  - Should: Use `ConfirmationDialog` with severity="warning"
  - Impact: Temporary service interruption

**OperationsPage.tsx** - DLQ operations:

- ✅ **Delete DLQ Item** (if exists in DeadLetterQueueTable)
  - Should: Use `ConfirmationDialog` with severity="error"
  - Impact: Permanent deletion
- ✅ **Retry DLQ Item** (if exists)
  - Should: Use `ConfirmationDialog` with severity="info"
  - Impact: Re-queues failed job

**JobManagement.tsx** - Job operations (when implemented):

- ✅ **Cancel Job** (if implemented)
  - Should: Use `ConfirmationDialog` with severity="warning"
  - Impact: Stops running job
- ✅ **Delete Job** (if implemented)
  - Should: Use `ConfirmationDialog` with severity="error"
  - Impact: Permanent deletion

**DataBrowserPage.tsx** - Data operations (if implemented):

- ✅ **Delete Data Product** (if implemented)
  - Should: Use `ConfirmationDialog` with severity="error"
  - Impact: Permanent deletion

**SourceMonitoringPage.tsx** - Source operations (if implemented):

- ✅ **Delete Source** (if implemented)
  - Should: Use `ConfirmationDialog` with severity="error"
  - Impact: Permanent deletion

### Implementation Priority

1. **CachePage** (High) - Replace custom dialog with `ConfirmationDialog`
2. **StreamingPage** (High) - Replace custom dialogs with `ConfirmationDialog`
3. **OperationsPage** (Medium) - Add confirmation for DLQ operations
4. **JobManagement** (Medium) - Add confirmation when cancel/delete implemented

## 4. Sparkline Opportunities

### High Priority (Metrics with Trends)

**HealthPage.tsx** - System metrics perfect for sparklines:

- ✅ **CPU Usage** (`metrics.cpu_percent`)
  - Current: Single value display
  - Opportunity: Show 24-hour trend
  - Data: Need historical endpoint `/api/metrics/system/history?hours=24`
- ✅ **Memory Usage** (`metrics.mem_percent`)
  - Current: Single value display
  - Opportunity: Show 24-hour trend
  - Data: Need historical endpoint
- ✅ **Disk Usage** (`(metrics.disk_used / metrics.disk_total) * 100`)
  - Current: Single value display
  - Opportunity: Show 24-hour trend
  - Data: Need historical endpoint

**CachePage.tsx** - Cache statistics:

- ✅ **Cache Hit Rate** (if available)
  - Opportunity: Show trend over time
  - Data: Need historical cache stats
- ✅ **Cache Size** (if available)
  - Opportunity: Show growth trend
  - Data: Need historical cache stats

**DashboardPage.tsx** - Pipeline metrics:

- ✅ **Queue Metrics** (pending, in_progress, completed, failed)
  - Current: Single value MetricCard
  - Opportunity: Show trends for each metric
  - Data: Need historical queue stats
- ✅ **System Health** (CPU, Memory, Disk)
  - Current: StatusIndicator (already enhanced)
  - Opportunity: Add sparklines to show trends
  - Data: Need historical metrics

**PipelinePage.tsx** - Pipeline execution metrics:

- ✅ **Average Duration** (`metricsSummary.average_duration_seconds`)
  - Opportunity: Show trend over time
  - Data: Need historical pipeline metrics
- ✅ **Success Rate** (if available)
  - Opportunity: Show trend over time
  - Data: Need historical pipeline metrics

**SourceMonitoringPage.tsx** - Source metrics:

- ✅ **ESE Candidates Count** (if available)
  - Opportunity: Show trend over time
  - Data: Need historical source stats

### Implementation Priority

1. **HealthPage** (High) - System metrics are perfect for sparklines
2. **DashboardPage** (High) - Queue metrics would benefit from trends
3. **CachePage** (Medium) - Cache statistics trends
4. **PipelinePage** (Medium) - Execution metrics trends

### Data Requirements

**Backend Endpoints Needed:**

- `/api/metrics/system/history?hours=24` - System metrics history
- `/api/pipeline/metrics/history?hours=24` - Pipeline metrics history
- `/api/cache/stats/history?hours=24` - Cache statistics history
- `/api/queue/stats/history?hours=24` - Queue statistics history

**Alternative (Mock Data):**

- Generate trend arrays from current values for demonstration
- Use `generateTrend()` helper function

## Summary by Page

### OperationsPage.tsx

- ✅ **Breadcrumbs:** High priority
- ✅ **Validation:** Medium (filter selects)
- ✅ **Confirmation Dialogs:** High (DLQ operations)
- ⚠️ **Sparklines:** Low (no metrics displayed)

### HealthPage.tsx

- ✅ **Breadcrumbs:** High priority
- ⚠️ **Validation:** Low (no forms)
- ⚠️ **Confirmation Dialogs:** Low (no destructive actions)
- ✅ **Sparklines:** High (system metrics perfect for trends)

### SourceMonitoringPage.tsx

- ✅ **Breadcrumbs:** High priority
- ✅ **Validation:** Medium (source ID search, threshold)
- ⚠️ **Confirmation Dialogs:** Low (no destructive actions visible)
- ⚠️ **Sparklines:** Low (no metrics displayed)

### CachePage.tsx

- ✅ **Breadcrumbs:** High priority
- ⚠️ **Validation:** Low (no forms)
- ✅ **Confirmation Dialogs:** High (clear cache - replace custom dialog)
- ✅ **Sparklines:** Medium (cache statistics)

### StreamingPage.tsx

- ✅ **Breadcrumbs:** High priority
- ⚠️ **Validation:** Low (no forms visible)
- ✅ **Confirmation Dialogs:** High (stop/restart - replace custom dialogs)
- ⚠️ **Sparklines:** Low (no metrics displayed)

### CalibrationWorkflow.tsx

- ⚠️ **Breadcrumbs:** N/A (component, not page)
- ✅ **Validation:** High (multiple fields need validation)
- ⚠️ **Confirmation Dialogs:** Low (no destructive actions)
- ⚠️ **Sparklines:** Low (no metrics)

### ImagingWorkflow.tsx

- ⚠️ **Breadcrumbs:** N/A (component, not page)
- ✅ **Validation:** High (parameter fields need validation)
- ⚠️ **Confirmation Dialogs:** Low (no destructive actions)
- ⚠️ **Sparklines:** Low (no metrics)

### Detail Pages (SourceDetailPage, ImageDetailPage, etc.)

- ✅ **Breadcrumbs:** High priority (users get lost)
- ⚠️ **Validation:** Low (mostly display)
- ⚠️ **Confirmation Dialogs:** Low (no destructive actions visible)
- ⚠️ **Sparklines:** Low (no metrics)

## Recommended Implementation Order

### Phase 1: High-Impact, Low-Effort

1. Add breadcrumbs to all detail pages (8 pages)
2. Replace custom dialogs in CachePage and StreamingPage with ConfirmationDialog
3. Add validation to CalibrationWorkflow critical fields

### Phase 2: High-Impact, Medium-Effort

4. Add breadcrumbs to primary pages (12 pages)
5. Add validation to ImagingWorkflow parameters
6. Add confirmation dialogs to OperationsPage DLQ operations

### Phase 3: Medium-Impact, High-Effort

7. Add sparklines to HealthPage (requires backend endpoint)
8. Add sparklines to DashboardPage (requires backend endpoint)
9. Add validation to SourceMonitoringPage search

### Phase 4: Nice-to-Have

10. Add sparklines to CachePage and PipelinePage
11. Add validation to remaining forms
12. Add confirmation dialogs to future destructive actions

---

**Total Opportunities:**

- **Breadcrumbs:** 20 pages
- **Validation:** 8 forms/components
- **Confirmation Dialogs:** 6+ actions
- **Sparklines:** 4+ metric displays (requires backend support)

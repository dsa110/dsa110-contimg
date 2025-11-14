# Dashboard Web Design Improvements

## User-Centered & Pipeline Workflow Optimizations

**Date:** 2025-11-12  
**Status:** Design Recommendations  
**Audience:** Frontend developers, UX designers, product managers

---

## Executive Summary

This document proposes significant improvements to the DSA-110 dashboard web
design, focusing on:

1. **Workflow-Optimized Navigation** - Context-aware navigation that adapts to
   user tasks
2. **Anticipatory UX Enhancements** - Proactive data loading and action
   suggestions
3. **Pipeline-Aware Interface** - UI that reflects the autonomous pipeline's
   state and workflow
4. **Science-First Improvements** - Direct access to discoveries and scientific
   insights
5. **Unified Workspace Concept** - Single-pane workflows that eliminate context
   switching

---

## 1. Workflow-Optimized Navigation

### 1.1 Context-Aware Navigation Bar

**Current State:** Static navigation bar with fixed links to all pages.

**Problem:** Users must navigate between multiple pages to complete a single
workflow (e.g., investigating an ESE candidate requires Dashboard → Sources → QA
→ Data Browser).

**Improvement:** Dynamic navigation that adapts to current context and suggests
next steps.

**Implementation:**

```typescript
// Context-aware navigation component
interface NavigationContext {
  currentWorkflow:
    | "monitoring"
    | "discovery"
    | "investigation"
    | "debugging"
    | "analysis";
  suggestedNextSteps: NavigationItem[];
  quickActions: QuickAction[];
}

// Navigation adapts based on:
// - Current page and user activity
// - Pipeline state (autonomous vs manual)
// - Active alerts or discoveries
// - User's recent actions
```

**Features:**

- **Workflow Breadcrumbs** - Show current workflow path (e.g., "Dashboard > ESE
  Alert > Source Investigation")
- **Next Step Suggestions** - Highlight likely next pages based on current
  context
- **Quick Actions Panel** - Floating action panel with context-relevant
  shortcuts
- **Recent Pages** - Quick access to recently visited pages
- **Workflow Templates** - Pre-defined navigation paths for common workflows

**Example Workflows:**

1. **ESE Discovery Flow:** Dashboard (alert) → Sources (details) → QA
   (validation) → Data Browser (images)
2. **Pipeline Debug Flow:** Dashboard (error) → Operations (DLQ) → Control
   (manual intervention) → Health (metrics)
3. **Data Exploration Flow:** Sky View (coverage) → Sources (catalog) → Data
   Browser (images) → QA (quality)

### 1.2 Unified Workspace Mode

**Current State:** Each page is separate, requiring navigation to switch
contexts.

**Problem:** Scientists need to see multiple related views simultaneously (e.g.,
source light curve + image + calibration status).

**Improvement:** Unified workspace that allows multiple views in a single pane.

**Implementation:**

```typescript
interface WorkspaceView {
  id: string;
  type:
    | "source-detail"
    | "image-viewer"
    | "light-curve"
    | "calibration-status"
    | "qa-panel";
  data: unknown;
  position: { x: number; y: number; width: number; height: number };
  linkedViews: string[]; // IDs of related views
}

interface UnifiedWorkspace {
  views: WorkspaceView[];
  layout: "grid" | "split-horizontal" | "split-vertical" | "custom";
  focus: string; // Currently focused view ID
}
```

**Features:**

- **Multi-Pane Layout** - Split screen with related views side-by-side
- **Linked Views** - Changes in one view automatically update related views
- **Workspace Templates** - Pre-configured layouts for common workflows
- **Save/Load Workspaces** - Save investigation layouts for later
- **Focus Mode** - Expand one view to full screen temporarily

**Example:** ESE candidate investigation workspace:

```
┌─────────────────────┬─────────────────────┐
│ Source Details     │ Light Curve Plot    │
│ (NVSS J1234+5678)  │ (Time Series)       │
├─────────────────────┼─────────────────────┤
│ Latest Image       │ Calibration Status  │
│ (FITS Viewer)      │ (Quality Metrics)   │
└─────────────────────┴─────────────────────┘
```

### 1.3 Command Palette / Quick Actions

**Current State:** Actions are scattered across pages and menus.

**Problem:** Common actions require multiple clicks and navigation.

**Improvement:** Global command palette (Cmd+K / Ctrl+K) for quick access to all
actions.

**Features:**

- **Fuzzy Search** - Type to find pages, actions, sources, images
- **Keyboard Shortcuts** - All actions accessible via keyboard
- **Recent Actions** - Quick access to recently used commands
- **Context-Aware Suggestions** - Show relevant actions based on current
  page/state
- **Action Chaining** - Execute multiple actions in sequence

**Example Commands:**

- `> view source NVSS J1234+5678`
- `> retry failed calibration`
- `> show images from last 6 hours`
- `> export ESE candidates to CSV`
- `> open workspace: ESE investigation`

---

## 2. Anticipatory UX Enhancements

### 2.1 Predictive Data Loading

**Current State:** Data loads when user navigates to a page.

**Problem:** Users wait for data to load, breaking workflow momentum.

**Improvement:** Pre-load data based on user behavior and pipeline state.

**Implementation:**

```typescript
interface PredictiveLoader {
  // Pre-load based on:
  preloadRules: {
    // User behavior patterns
    onPageView: (page: string) => string[]; // Pages to pre-load
    onHover: (element: string) => string[]; // Data to pre-load on hover
    onAlert: (alert: Alert) => string[]; // Data to pre-load when alert appears

    // Pipeline state
    onESEAlert: () => string[]; // Pre-load source details, images, QA
    onFailedJob: () => string[]; // Pre-load error details, DLQ, logs

    // Time-based
    scheduledPreloads: { time: string; data: string[] }[];
  };
}
```

**Features:**

- **Hover Pre-loading** - Load data when user hovers over clickable elements
- **Alert Pre-loading** - When ESE alert appears, pre-load source details,
  images, QA data
- **Workflow Pre-loading** - Pre-load next likely pages in current workflow
- **Background Refresh** - Keep data fresh in background for recently viewed
  pages
- **Smart Caching** - Cache frequently accessed data with intelligent
  invalidation

### 2.2 Proactive Action Suggestions

**Current State:** Users must discover actions themselves.

**Problem:** Users may not know what actions are available or what to do next.

**Improvement:** Context-aware action suggestions that appear when relevant.

**Implementation:**

```typescript
interface ActionSuggestion {
  id: string;
  title: string;
  description: string;
  action: () => void;
  priority: "high" | "medium" | "low";
  context: {
    trigger: "alert" | "state-change" | "user-action" | "time-based";
    conditions: Record<string, unknown>;
  };
  dismissible: boolean;
}
```

**Features:**

- **Alert-Based Suggestions** - When ESE alert appears: "View source details",
  "Check calibration", "Export light curve"
- **State-Based Suggestions** - When pipeline error: "Check DLQ", "View logs",
  "Retry failed job"
- **Workflow Suggestions** - "You viewed this source, would you like to see its
  images?"
- **Time-Based Suggestions** - "No calibration update in 2 hours, check
  telescope pointing?"
- **Dismissible Notifications** - Users can dismiss suggestions, but they
  reappear if still relevant

**Example Suggestions:**

- **ESE Alert:** "3 new ESE candidates detected. [View Sources] [Export List]
  [Check Calibration]"
- **Failed Job:** "Calibration failed for group 2025-1024-1328. [View Error]
  [Retry] [Check DLQ]"
- **Low Disk Space:** "Disk usage at 85%. [View Storage] [Archive Old Data]
  [Clean Cache]"

### 2.3 Smart Notifications & Alerts

**Current State:** Alerts appear in panels, but may be missed.

**Problem:** Critical alerts can be overlooked, especially when user is focused
on another task.

**Improvement:** Intelligent notification system that prioritizes and surfaces
alerts appropriately.

**Features:**

- **Alert Priority System** - Critical alerts interrupt workflow, informational
  alerts stay in sidebar
- **Alert Grouping** - Group related alerts (e.g., "3 ESE candidates in same
  field")
- **Alert Actions** - Quick actions directly from notification (e.g., "View
  Source" button in notification)
- **Do Not Disturb Mode** - User can silence non-critical alerts during focused
  work
- **Alert History** - Timeline of all alerts with ability to revisit dismissed
  alerts
- **Smart Dismissal** - Alerts auto-dismiss when resolved, but can be manually
  dismissed

**Alert Types:**

1. **Critical** - Pipeline stopped, disk full, critical calibration failure
   (interrupt workflow)
2. **High** - ESE candidates, failed jobs, system warnings (persistent
   notification)
3. **Medium** - Calibration updates, new images, status changes (sidebar
   notification)
4. **Low** - Informational updates, routine status (minimal notification)

---

## 3. Pipeline-Aware Interface

### 3.1 Pipeline Stage Visualization

**Current State:** Pipeline status shown as text/numbers in panels.

**Problem:** Difficult to understand pipeline flow and where data is in the
process.

**Improvement:** Visual pipeline stage diagram showing data flow and current
state.

**Implementation:**

```typescript
interface PipelineStage {
  id: string;
  name: string;
  status: "waiting" | "in-progress" | "completed" | "failed" | "skipped";
  currentItem?: {
    id: string;
    progress: number; // 0-100
    startedAt: Date;
    estimatedCompletion?: Date;
  };
  queue: {
    pending: number;
    inProgress: number;
    completed: number;
    failed: number;
  };
  metrics: {
    avgDuration: number;
    successRate: number;
    throughput: number; // items/hour
  };
}

interface PipelineVisualization {
  stages: PipelineStage[];
  flow: {
    from: string;
    to: string;
    status: "active" | "blocked" | "idle";
  }[];
}
```

**Features:**

- **Visual Flow Diagram** - Horizontal pipeline showing: Collect → Convert →
  Calibrate → Image → QA → Mosaic
- **Current Position Indicators** - Highlight where each observation group is in
  the pipeline
- **Stage Details** - Click stage to see details, queue, metrics
- **Bottleneck Detection** - Highlight stages that are slowing down the pipeline
- **Historical Trends** - Show how long data spends in each stage over time
- **Interactive** - Click observation group to see its path through pipeline

**Visual Example:**

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Collect  │ → │ Convert  │ → │Calibrate │ → │  Image   │ → │   QA     │
│  [2]     │   │  [1]     │   │   [3]    │   │   [0]    │   │   [5]    │
│ ⚠ Slow   │   │ ✓ Normal │   │ ✓ Normal │   │ ✓ Normal │   │ ✓ Normal │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### 3.2 Autonomous vs Manual Mode Indicators

**Current State:** No clear indication when pipeline is in autonomous vs manual
mode.

**Problem:** Users may not realize they've taken manual control or that
autonomous mode has resumed.

**Improvement:** Clear visual indicators and mode transitions.

**Features:**

- **Mode Badge** - Prominent badge showing "AUTONOMOUS" or "MANUAL CONTROL"
- **Mode Transition Animations** - Smooth transition when switching modes
- **Manual Override Warnings** - Clear warning when taking manual control
- **Auto-Resume Prompt** - Ask user if they want to resume autonomous mode
- **Mode History** - Timeline showing when mode switched and why
- **Mode-Specific UI** - Different UI elements available in manual vs autonomous
  mode

**Visual Indicators:**

- **Autonomous Mode:** Green badge, minimal control UI, "Pipeline running
  autonomously"
- **Manual Mode:** Orange badge, full control UI, "Manual control active -
  [Resume Autonomous]"

### 3.3 Real-Time Pipeline Activity Feed

**Current State:** Recent observations table shows static list.

**Problem:** Difficult to see pipeline activity in real-time and understand
what's happening now.

**Improvement:** Live activity feed showing pipeline events as they happen.

**Features:**

- **Event Stream** - Real-time feed of pipeline events (new observation,
  calibration complete, image created, etc.)
- **Event Filtering** - Filter by event type, stage, source, time range
- **Event Details** - Expand event to see details, related data, actions
- **Event Grouping** - Group related events (e.g., all events for one
  observation group)
- **Timeline View** - Visual timeline showing events over time
- **Search** - Search events by observation ID, source, field name, etc.

**Event Types:**

- Observation received
- Subband conversion started/completed
- Calibration solved/applied
- Image created
- QA completed
- ESE candidate detected
- Error occurred
- Manual intervention

---

## 4. Science-First Improvements

### 4.1 Discovery-Focused Dashboard

**Current State:** Dashboard shows technical metrics and status.

**Problem:** Scientific discoveries (ESE candidates) are buried in panels.

**Improvement:** Make discoveries the primary focus when they occur.

**Features:**

- **Discovery Banner** - Large, prominent banner when new ESE candidate detected
- **Discovery Dashboard Mode** - Switch to "Discovery Mode" that highlights
  scientific findings
- **Discovery Timeline** - Timeline of all discoveries with ability to compare
- **Discovery Details Panel** - Expandable panel with full discovery context
- **Discovery Actions** - Quick actions: "Investigate", "Export", "Share", "Mark
  as False Positive"
- **Discovery Notifications** - Push notifications (if enabled) for new
  discoveries

**Discovery Mode Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  🎯 NEW DISCOVERY: NVSS J1234+5678                          │
│  Extreme Scattering Event Detected (5.2σ)                   │
│  [Investigate] [View Light Curve] [Check Images] [Export]   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────┬───────────────────────────────────────┐
│ Light Curve         │ Latest Image                         │
│ [Interactive Plot]  │ [FITS Viewer]                        │
└─────────────────────┴───────────────────────────────────────┘
```

### 4.2 Enhanced Source Investigation Workflow

**Current State:** Source details spread across multiple pages.

**Problem:** Investigating a source requires navigating between Sources, QA,
Data Browser pages.

**Improvement:** Unified source investigation interface with all relevant data
in one place.

**Features:**

- **Source Detail Page** - Comprehensive page with all source information
- **Tabbed Interface** - Tabs for: Overview, Light Curve, Images, Calibration,
  QA, Catalog Info
- **Related Sources** - Show nearby sources, similar sources, sources in same
  field
- **Comparison Tools** - Compare light curves, images, calibration across time
- **Export Tools** - Export light curve data, images, source info in various
  formats
- **Annotation Tools** - Add notes, tags, flags to sources
- **Share Links** - Generate shareable links to specific source views

**Source Investigation Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│ NVSS J1234+5678                    [Flag] [Export] [Share] │
│ RA: 12h34m56.7s  Dec: +56°78'90"                            │
│ Baseline Flux: 125.3 mJy  Current: 89.2 mJy (5.2σ)         │
├─────────────────────────────────────────────────────────────┤
│ [Overview] [Light Curve] [Images] [Calibration] [QA] [Notes] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Light Curve Plot with Interactive Controls]               │
│                                                              │
│  [Image Gallery with Thumbnails]                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Scientific Data Export & Sharing

**Current State:** Limited export capabilities.

**Problem:** Scientists need to export data in various formats for analysis and
sharing.

**Improvement:** Comprehensive export system with format options and sharing
capabilities.

**Features:**

- **Format Options** - CSV, JSON, FITS, VOTable, PDF reports
- **Customizable Exports** - Select which fields/data to include
- **Batch Export** - Export multiple sources, images, observations at once
- **Export Templates** - Save export configurations for reuse
- **Share Links** - Generate shareable links that load specific views/data
- **Export History** - Track what was exported and when
- **API Access** - Programmatic access to exported data

**Export Options:**

- Source catalog (CSV, VOTable)
- Light curve data (CSV, JSON)
- Images (FITS, PNG, PDF)
- QA reports (PDF, HTML)
- Observation metadata (JSON, CSV)

---

## 5. Enhanced User Experience

### 5.1 Improved Loading States & Skeleton Screens

**Current State:** Simple loading spinners.

**Problem:** Users don't know what's loading or how long it will take.

**Improvement:** Informative loading states with progress indicators.

**Features:**

- **Skeleton Screens** - Show page structure while loading
- **Progress Indicators** - Show loading progress when available
- **Loading Messages** - Explain what's being loaded
- **Estimated Time** - Show estimated time remaining
- **Cancel Option** - Allow users to cancel long-running loads
- **Optimistic Updates** - Show expected results immediately, update when real
  data arrives

### 5.2 Better Error Handling & Recovery

**Current State:** Basic error messages, limited recovery options.

**Problem:** Errors are frustrating and don't guide users to solutions.

**Improvement:** Actionable error messages with recovery suggestions.

**Features:**

- **Error Context** - Explain what went wrong and why
- **Recovery Actions** - Suggest actions to fix the error
- **Error Details** - Expandable error details for debugging
- **Retry Mechanisms** - Automatic retry with exponential backoff
- **Error Reporting** - Easy way to report errors with context
- **Error History** - Track errors over time to identify patterns

**Error Types:**

- **Network Errors** - "Connection lost. [Retry] [Check Status]"
- **Data Errors** - "Invalid data format. [View Details] [Report Issue]"
- **Permission Errors** - "Access denied. [Request Access] [Contact Admin]"
- **Pipeline Errors** - "Calibration failed. [View Logs] [Retry] [Check DLQ]"

### 5.3 Keyboard Shortcuts & Accessibility

**Current State:** Limited keyboard navigation.

**Problem:** Power users want keyboard shortcuts for efficiency.

**Improvement:** Comprehensive keyboard shortcuts and accessibility features.

**Features:**

- **Global Shortcuts** - Cmd+K (command palette), Cmd+/ (shortcuts help)
- **Page-Specific Shortcuts** - Different shortcuts for each page
- **Shortcut Hints** - Show available shortcuts in tooltips
- **Keyboard Navigation** - Full keyboard navigation for all UI elements
- **Screen Reader Support** - Proper ARIA labels and descriptions
- **High Contrast Mode** - Option for high contrast display
- **Font Size Controls** - Adjustable font sizes

**Common Shortcuts:**

- `g d` - Go to Dashboard
- `g s` - Go to Sources
- `g q` - Go to QA
- `g c` - Go to Control
- `/` - Search
- `?` - Show shortcuts
- `Esc` - Close modals/panels

### 5.4 Personalization & Preferences

**Current State:** No user preferences or personalization.

**Problem:** Different users have different needs and workflows.

**Improvement:** User preferences and customizable interface.

**Features:**

- **Dashboard Layout** - Customize which panels appear and their order
- **Default Views** - Set default time ranges, filters, views
- **Notification Preferences** - Choose which alerts to receive
- **Theme Options** - Light/dark theme, color schemes
- **Workspace Templates** - Save and load custom workspace layouts
- **Quick Actions** - Customize quick action buttons
- **Export Templates** - Save export configurations

---

## 6. Performance & Technical Improvements

### 6.1 Optimistic Updates

**Current State:** UI updates only after server response.

**Problem:** Actions feel slow, even when they're fast.

**Improvement:** Update UI immediately, rollback if action fails.

**Features:**

- **Instant Feedback** - UI updates immediately on user action
- **Rollback on Failure** - Revert changes if action fails
- **Loading Indicators** - Show that action is in progress
- **Success Confirmation** - Confirm when action completes

### 6.2 Virtual Scrolling for Large Lists

**Current State:** All items loaded and rendered at once.

**Problem:** Performance degrades with large lists (thousands of sources,
images).

**Improvement:** Virtual scrolling to render only visible items.

**Features:**

- **Virtual Lists** - Only render visible items
- **Infinite Scroll** - Load more items as user scrolls
- **Search Integration** - Virtual scrolling works with search/filter
- **Smooth Scrolling** - Smooth scroll performance

### 6.3 Data Caching & Offline Support

**Current State:** Data fetched on demand, no offline support.

**Problem:** Users lose access when network is unavailable.

**Improvement:** Cache data locally and support offline viewing.

**Features:**

- **Local Caching** - Cache frequently accessed data
- **Offline Viewing** - View cached data when offline
- **Sync Indicators** - Show when data is cached vs fresh
- **Cache Management** - User control over cache size and contents

---

## 7. Implementation Priority

### Phase 1: High Impact, Quick Wins (2-4 weeks)

1. ✅ Command Palette / Quick Actions
2. ✅ Improved Loading States & Skeleton Screens
3. ✅ Better Error Handling & Recovery
4. ✅ Proactive Action Suggestions
5. ✅ Discovery-Focused Dashboard

### Phase 2: Workflow Improvements (4-6 weeks)

6. ✅ Context-Aware Navigation
7. ✅ Unified Workspace Mode
8. ✅ Enhanced Source Investigation Workflow
9. ✅ Pipeline Stage Visualization
10. ✅ Real-Time Pipeline Activity Feed

### Phase 3: Advanced Features (6-8 weeks)

11. ✅ Predictive Data Loading
12. ✅ Smart Notifications & Alerts
13. ✅ Scientific Data Export & Sharing
14. ✅ Personalization & Preferences
15. ✅ Optimistic Updates

### Phase 4: Performance & Polish (4-6 weeks)

16. ✅ Virtual Scrolling for Large Lists
17. ✅ Data Caching & Offline Support
18. ✅ Keyboard Shortcuts & Accessibility
19. ✅ Autonomous vs Manual Mode Indicators

---

## 8. Success Metrics

### User Experience Metrics

- **Time to Complete Workflow** - Measure time for common workflows (ESE
  investigation, pipeline debugging)
- **Page Navigation Count** - Reduce number of page navigations per workflow
- **Error Recovery Time** - Time from error to resolution
- **User Satisfaction** - Surveys and feedback

### Technical Metrics

- **Page Load Time** - Reduce initial load time
- **Time to Interactive** - Reduce time until user can interact
- **API Response Time** - Optimize backend response times
- **Cache Hit Rate** - Measure effectiveness of caching

### Scientific Metrics

- **Discovery Response Time** - Time from ESE detection to investigation
- **Data Export Usage** - Track export frequency and formats
- **Source Investigation Depth** - Measure how deeply users investigate sources

---

## Conclusion

These improvements focus on:

1. **Reducing cognitive load** - Less navigation, more context
2. **Anticipating needs** - Proactive loading and suggestions
3. **Supporting workflows** - Unified workspaces and streamlined paths
4. **Enhancing discovery** - Science-first approach to interface design
5. **Improving performance** - Faster, more responsive interface

The goal is to make the dashboard feel like a natural extension of the
scientist's workflow, anticipating needs and eliminating friction.

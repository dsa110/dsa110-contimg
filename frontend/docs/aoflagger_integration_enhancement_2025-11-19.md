# AOFlagger Integration Enhancement

**Date:** 2025-11-19  
**Status:** Complete ✅

## Overview

Enhanced the frontend to surface imaging backend information and comprehensive
AOFlagger RFI statistics, providing astronomers with detailed visibility into
data quality and flagging decisions.

## Features Implemented

### 1. Imaging Backend Display

**Location:** `/frontend/src/components/MSDetails/MSInspectionPanel.tsx`

Added display of selected imaging backend (WSClean vs tclean) in the MS Overview
section:

- Color-coded Chip components for visual distinction
  - WSClean: Primary (blue) color
  - tclean: Secondary (purple) color
- Displays imager version string when available
- Provides immediate context for which imaging pipeline processed the data

**TypeScript Types:**

```typescript
// In MSMetadata interface
imaging_backend?: "wsclean" | "tclean" | null;
imager?: string; // Version string, e.g., "WSClean 3.4"
```

**Benefits:**

- Quick identification of imaging pipeline used
- Debugging aid for pipeline-specific issues
- Supports mixed WSClean/tclean workflows

---

### 2. AOFlagger Statistics Enhancement

#### A. MSInspectionPanel Integration

**Location:** `/frontend/src/components/MSDetails/MSInspectionPanel.tsx`

Enhanced the "Flagging & RFI Statistics" card with:

**Overview Section:**

- Total flagged percentage
- RFI detected percentage (from AOFlagger)
- AOFlagger version chip (e.g., "Version 3.4.0")
- Strategy chip (e.g., "Optimal", "Default", "Conservative")

**Baseline RFI Statistics (Expandable Accordion):**

- Sorted table of baseline-wise RFI percentages
- Top 20 most affected baselines displayed
- Baseline names in monospace font for clarity
- Indication of remaining baselines if > 20

**Frequency RFI Statistics (Expandable Accordion):**

- Channel-wise RFI contamination breakdown
- Top 15 most affected frequency channels
- Helps identify narrow-band RFI sources
- Auto-expands when total flagging > 25%

**TypeScript Types:**

```typescript
// Extended FlaggingStats interface
aoflagger_version?: string;         // e.g., "3.4.0"
aoflagger_strategy?: string;        // e.g., "Optimal"
rfi_percentage?: number;            // Overall RFI detection rate
baseline_rfi_stats?: Record<string, number>;  // Baseline -> RFI fraction
time_rfi_stats?: Record<string, number>;      // Time slot -> RFI fraction
frequency_rfi_stats?: Record<string, number>; // Channel -> RFI fraction
```

#### B. Dedicated AOFlaggerStats Component

**Location:** `/frontend/src/components/QA/AOFlaggerStats.tsx`

Created a standalone, reusable component for displaying comprehensive AOFlagger
statistics:

**Features:**

- **Overview Dashboard:**
  - Total Flagged percentage with progress bar
  - RFI Detected percentage with progress bar
  - Color-coded severity levels:
    - Good (green): < 10%
    - Moderate (yellow): 10-25%
    - High (red): > 25%

- **Configuration Display:**
  - AOFlagger version badge
  - Strategy chip (Optimal/Default/Conservative)

- **Quality Assessment:**
  - Automatic quality alerts based on flagging percentage
  - Contextual recommendations (e.g., "Review baseline statistics")

- **Detailed Statistics (Accordions):**
  - Baseline RFI Statistics: Top 15 baselines with color-coded status
  - Frequency RFI Statistics: Top 15 channels with severity indicators
  - Time RFI Statistics: Top 15 time slots showing transient RFI events

**Component API:**

```typescript
interface AOFlaggerStatsProps {
  stats: FlaggingStats; // From api/types.ts
  msPath?: string; // Optional MS path for display
}
```

**Usage Example:**

```typescript
import { AOFlaggerStats } from '../components/QA/AOFlaggerStats';

<AOFlaggerStats
  stats={metadata.flagging_stats}
  msPath={metadata.ms_path}
/>
```

---

## Technical Implementation

### Type Extensions

**File:** `/frontend/src/api/types.ts`

Extended existing TypeScript interfaces:

```typescript
export interface MSMetadata {
  // ... existing fields
  imaging_backend?: "wsclean" | "tclean" | null;
  imager?: string;
}

export interface ImageInfo {
  // ... existing fields
  imaging_backend?: "wsclean" | "tclean" | null;
}

export interface FlaggingStats {
  // ... existing fields
  aoflagger_version?: string;
  aoflagger_strategy?: string;
  rfi_percentage?: number;
  baseline_rfi_stats?: Record<string, number>;
  time_rfi_stats?: Record<string, number>;
  frequency_rfi_stats?: Record<string, number>;
}
```

### Component Exports

**File:** `/frontend/src/components/QA/index.ts`

```typescript
export { AOFlaggerStats } from "./AOFlaggerStats";
// ... other exports
```

---

## Backend API Requirements

The frontend expects the following API responses:

### GET `/api/ms/{ms_id}/metadata`

```json
{
  "ms_id": "dsa110...",
  "imaging_backend": "wsclean",
  "imager": "WSClean 3.4.0",
  "flagging_stats": {
    "total_fraction": 0.15,
    "rfi_percentage": 0.12,
    "aoflagger_version": "3.4.0",
    "aoflagger_strategy": "Optimal",
    "per_antenna": { "Ant01": 0.10, ... },
    "baseline_rfi_stats": { "Ant01-Ant02": 0.08, ... },
    "frequency_rfi_stats": { "0": 0.05, "1": 0.15, ... },
    "time_rfi_stats": { "0": 0.02, "1": 0.18, ... }
  }
}
```

### GET `/api/images/{image_id}`

```json
{
  "image_id": "...",
  "imaging_backend": "wsclean",
  "ms_id": "..."
}
```

---

## User Benefits

### For Debugging:

1. **Imaging Backend Visibility:** Instantly see which imager was used without
   checking logs
2. **RFI Hot Spots:** Quickly identify problematic baselines or frequency
   channels
3. **Time-domain Analysis:** Detect transient RFI events via time_rfi_stats

### For QA Workflows:

1. **Severity-based Triage:** Color-coded severity levels prioritize review
   efforts
2. **Detailed Breakdowns:** Expandable accordions provide depth without
   overwhelming the UI
3. **Context Preservation:** AOFlagger version/strategy helps reproduce results

### For Pipeline Operations:

1. **Configuration Auditing:** Verify correct AOFlagger strategy was applied
2. **Cross-observation Comparison:** Compare RFI patterns across observations
3. **Data Quality Metrics:** Quantitative thresholds for automated QA decisions

---

## Files Modified

1. `/frontend/src/api/types.ts`
   - Extended MSMetadata with `imaging_backend`, `imager`
   - Extended ImageInfo with `imaging_backend`
   - Extended FlaggingStats with AOFlagger fields

2. `/frontend/src/components/MSDetails/MSInspectionPanel.tsx`
   - Added imaging backend display in MS Overview
   - Enhanced Flagging Statistics card with AOFlagger version/strategy
   - Added Baseline RFI Statistics accordion
   - Added Frequency RFI Statistics accordion

## Files Created

3. `/frontend/src/components/QA/AOFlaggerStats.tsx`
   - New dedicated component for AOFlagger statistics display
   - Comprehensive RFI visualization with severity indicators
   - Reusable across multiple QA contexts

4. `/frontend/src/components/QA/index.ts`
   - Added AOFlaggerStats to component exports

---

## Testing Recommendations

### Unit Tests

- Verify severity level calculations (good/moderate/high thresholds)
- Test sorting logic for baseline/frequency/time stats
- Validate component rendering with missing optional fields

### Integration Tests

- Load MS with known flagging statistics
- Verify accordion expansion behavior
- Test color-coded chip rendering for different backends

### E2E Tests

```javascript
test("Display AOFlagger statistics in MSInspectionPanel", async ({ page }) => {
  await page.goto("/control");
  await page.click("text=MS Details");
  await expect(page.locator("text=Flagging & RFI Statistics")).toBeVisible();
  await expect(page.locator("text=Version 3.4.0")).toBeVisible();
});
```

---

## Future Enhancements

1. **Time-series Plots:** Plotly visualizations of RFI evolution over time
2. **Comparative Analysis:** Side-by-side comparison of AOFlagger runs with
   different strategies
3. **Waterfall Plots:** 2D heatmaps of frequency vs. time RFI contamination
4. **Export Functionality:** Download RFI statistics as CSV/JSON for external
   analysis
5. **Threshold Configuration:** User-adjustable severity thresholds in settings
6. **Historical Tracking:** Track RFI trends across multiple observations

---

## Related Documentation

- Original Implementation: `frontend_enhancements_implementation_2025-11-19.md`
- Backend API: See `/data/dsa110-contimg/src/dsa110_contimg/frontend/` endpoints
- AOFlagger Documentation: https://aoflagger.readthedocs.io/

---

## Summary

✅ **Imaging Backend Display:** Integrated into MSInspectionPanel with
color-coded chips  
✅ **AOFlagger Statistics:** Comprehensive display with version, strategy, and
detailed RFI breakdowns  
✅ **Dedicated Component:** Created reusable AOFlaggerStats component for QA
panels  
✅ **TypeScript Types:** Extended interfaces to support new fields  
✅ **Documentation:** Complete technical and user-facing documentation

The frontend now provides astronomers with full visibility into imaging pipeline
selection and detailed RFI statistics, supporting both interactive debugging and
automated QA workflows.

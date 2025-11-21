# Comprehensive Testing Plan for DSA-110 Continuum Imaging Dashboard

## Overview

This document outlines a systematic testing approach to verify all clickable
features and user interactions across the dashboard application. The testing
strategy combines manual test cases with automated browser-based testing.

## Testing Strategy

### 1. Test Categories

- **Navigation Testing**: Verify all navigation links and routes
- **Form Interaction Testing**: Test all input fields, selects, and form
  submissions
- **Button Action Testing**: Verify all buttons perform expected actions
- **Table/List Interaction Testing**: Test row selection, sorting, filtering
- **Modal/Dialog Testing**: Test dialog open/close and form submissions
- **Tab Navigation Testing**: Verify tab switching and content display
- **API Integration Testing**: Verify API calls and responses
- **Error Handling Testing**: Test error states and error boundaries

### 2. Test Execution Approach

- **Automated Tests**: Browser-based tests using Playwright/Puppeteer for
  regression testing
- **Manual Tests**: Detailed test cases for initial validation and exploratory
  testing
- **Integration Tests**: Verify end-to-end workflows

## Test Coverage by Page

### Navigation Component

#### Test Cases: NAV-001 to NAV-007

**NAV-001: Desktop Navigation Links**

- **Action**: Click each navigation link in desktop view
- **Expected**:
  - Navigate to correct route
  - Active link is highlighted
  - Page content loads correctly
- **Links to Test**:
  - Dashboard (/dashboard)
  - Control (/control)
  - Streaming (/streaming)
  - Data (/data)
  - Mosaics (/mosaics)
  - Sources (/sources)
  - Sky View (/sky)

**NAV-002: Mobile Navigation Drawer**

- **Action**:
  1. Resize browser to mobile width (< 600px)
  2. Click hamburger menu icon
  3. Verify drawer opens
  4. Click each navigation link
  5. Verify drawer closes after navigation
- **Expected**: Drawer opens/closes correctly, navigation works

**NAV-003: Mobile Drawer Close**

- **Action**: Click outside drawer or close button
- **Expected**: Drawer closes

---

### Dashboard Page

#### Test Cases: DASH-001 to DASH-002

**DASH-001: Page Load**

- **Action**: Navigate to /dashboard
- **Expected**: Page loads without errors, displays dashboard content

**DASH-002: Dashboard Content Display**

- **Action**: Verify dashboard widgets/components render
- **Expected**: All dashboard components visible and functional

---

### Control Page

#### Test Cases: CTRL-001 to CTRL-050

**CTRL-001: Tab Navigation**

- **Action**: Click each tab (Convert, Calibrate, Apply, Image)
- **Expected**:
  - Tab switches correctly
  - Tab content displays
  - Active tab is highlighted

**CTRL-002: MS Table Selection**

- **Action**:
  1. Click on MS table row
  2. Select multiple rows (if multi-select enabled)
- **Expected**:
  - Row is highlighted
  - Selected MS is set in form
  - Selected MS list updates

**CTRL-003: Convert Tab - Form Fields**

- **Action**: Fill in form fields:
  - Start Time
  - End Time
  - Input Directory
  - Output Directory
  - Writer (Select dropdown)
  - Max Workers
- **Expected**: All fields accept input and update state

**CTRL-004: Convert Tab - Writer Dropdown**

- **Action**: Select each option from Writer dropdown:
  - Auto (recommended)
  - Sequential
  - Parallel
  - Dask
- **Expected**: Selection updates correctly

**CTRL-005: Convert Tab - Submit Button**

- **Action**:
  1. Fill required fields (Start Time, End Time)
  2. Click "Run Conversion" button
- **Expected**:
  - Button shows loading state
  - API call is made
  - Job is created
  - Success notification appears

**CTRL-006: Convert Tab - Submit Button Disabled State**

- **Action**: Try to submit without required fields
- **Expected**: Button is disabled

**CTRL-007: Calibrate Tab - Field ID Input**

- **Action**: Enter Field ID in text field
- **Expected**: Value updates correctly

**CTRL-008: Calibrate Tab - Reference Antenna Selection**

- **Action**:
  1. Select MS file
  2. Open Reference Antenna dropdown
  3. Select an antenna
- **Expected**:
  - Dropdown shows available antennas
  - Selection updates
  - Validation message appears if invalid

**CTRL-009: Calibrate Tab - Calibration Tables Selection**

- **Action**:
  1. Select MS with existing tables
  2. Choose radio option (Use Existing / Generate New)
- **Expected**: Selection updates, form adapts

**CTRL-010: Calibrate Tab - Table Type Checkboxes**

- **Action**: Toggle checkboxes for K, BP, G tables
- **Expected**: Checkboxes toggle correctly

**CTRL-011: Calibrate Tab - Submit Button**

- **Action**: Fill required fields and submit
- **Expected**: Job created, success notification

**CTRL-012: Apply Tab - Calibration Tables Selection**

- **Action**: Select calibration tables from dropdown
- **Expected**: Tables listed, selection works

**CTRL-013: Apply Tab - Submit Button**

- **Action**: Fill required fields and submit
- **Expected**: Job created successfully

**CTRL-014: Image Tab - Form Fields**

- **Action**: Fill image generation form fields
- **Expected**: All fields accept input

**CTRL-015: Image Tab - Submit Button**

- **Action**: Submit image generation job
- **Expected**: Job created successfully

**CTRL-016: Workflow Tab - Start/End Time**

- **Action**: Enter workflow start and end times
- **Expected**: Values update correctly

**CTRL-017: Workflow Tab - Run Workflow Button**

- **Action**: Click "Run Workflow" button
- **Expected**: Workflow job created

**CTRL-018: Jobs Table - Row Selection**

- **Action**: Click on job row
- **Expected**: Job details/logs display

**CTRL-019: Jobs Table - Job Actions**

- **Action**: Click action buttons (if any) on job rows
- **Expected**: Actions execute correctly

**CTRL-020: Calibration QA Panel Display**

- **Action**: Select calibrated MS
- **Expected**: QA panel displays with metrics

**CTRL-021: Calibration SPW Panel Display**

- **Action**: Select MS for calibration
- **Expected**: SPW panel displays

---

### Data Browser Page

#### Test Cases: DATA-001 to DATA-015

**DATA-001: Page Load**

- **Action**: Navigate to /data
- **Expected**: Page loads, data table displays

**DATA-002: Tab Navigation - Staging vs Published**

- **Action**: Click "Staging" and "Published" tabs
- **Expected**:
  - Tab switches
  - Correct data displays for each status
  - Table updates

**DATA-003: Data Type Filter**

- **Action**:
  1. Open "Data Type" dropdown
  2. Select each filter option:
     - All Types
     - MS
     - Calibration Table
     - Image
     - Mosaic
- **Expected**:
  - Dropdown opens/closes
  - Table filters correctly
  - Only matching data types shown

**DATA-004: Table Row Display**

- **Action**: Verify table columns display:
  - ID
  - Type
  - Status
  - QA Status
  - Finalization
  - Auto-Publish
  - Created
  - Published (if published tab)
  - Actions
- **Expected**: All columns visible with correct data

**DATA-005: View Details Button (Eye Icon)**

- **Action**: Click eye icon in Actions column
- **Expected**:
  - Navigate to detail page (/data/:type/:id)
  - Detail page loads correctly
  - Data displays

**DATA-006: Table Sorting (if implemented)**

- **Action**: Click column headers
- **Expected**: Table sorts by column

**DATA-007: Empty State**

- **Action**: Navigate with no data
- **Expected**: Empty state message displays

**DATA-008: Loading State**

- **Action**: Navigate while data loads
- **Expected**: Loading indicator displays

**DATA-009: Error State**

- **Action**: Simulate API error
- **Expected**: Error message displays

**DATA-010: Multiple Data Types Display**

- **Action**: Verify table shows different data types correctly
- **Expected**: Each type displays with correct chip/label

**DATA-011: Status Chips Display**

- **Action**: Verify status chips display correctly
- **Expected**: Chips show correct color and text

**DATA-012: Date Formatting**

- **Action**: Verify created/published dates format correctly
- **Expected**: Dates display in readable format

**DATA-013: Long ID Display**

- **Action**: Verify long data IDs display correctly
- **Expected**: IDs truncate or wrap appropriately

**DATA-014: Responsive Table**

- **Action**: Resize browser to mobile width
- **Expected**: Table adapts or scrolls horizontally

**DATA-015: Data Refresh**

- **Action**: Verify data refreshes automatically or manually
- **Expected**: New data appears in table

---

### Data Detail Page

#### Test Cases: DETAIL-001 to DETAIL-025

**DETAIL-001: Page Load**

- **Action**: Navigate to /data/:type/:id
- **Expected**: Page loads, data displays

**DETAIL-002: Back Button**

- **Action**: Click "Back to Data Browser" button
- **Expected**: Navigate to /data

**DETAIL-003: Back Icon Button**

- **Action**: Click back arrow icon
- **Expected**: Navigate to /data

**DETAIL-004: Publish Button**

- **Action**:
  1. Click "Publish" button
  2. Verify button disabled during request
- **Expected**:
  - API call made
  - Success notification
  - Status updates

**DETAIL-005: Finalize Button**

- **Action**:
  1. Click "Finalize" button
  2. Fill QA/validation status if required
- **Expected**:
  - Dialog/form opens (if applicable)
  - Finalization succeeds
  - Status updates

**DETAIL-006: Tab Navigation - Metadata**

- **Action**: Click "Metadata" tab
- **Expected**: Metadata displays in JSON or formatted view

**DETAIL-007: Tab Navigation - Lineage**

- **Action**: Click "Lineage" tab
- **Expected**: Lineage graph/table displays

**DETAIL-008: Auto-Publish Toggle**

- **Action**: Click "Enable/Disable Auto-Publish" button
- **Expected**:
  - Status toggles
  - API call made
  - Button text updates

**DETAIL-009: Loading State**

- **Action**: Navigate while data loads
- **Expected**: Loading indicator displays

**DETAIL-010: Error State**

- **Action**: Navigate with invalid ID
- **Expected**: Error message displays, back button available

**DETAIL-011: Metadata Display**

- **Action**: Verify metadata displays correctly
- **Expected**: All metadata fields visible and formatted

**DETAIL-012: Lineage Graph Display**

- **Action**: Verify lineage graph renders
- **Expected**: Graph displays relationships

**DETAIL-013: URL Encoding**

- **Action**: Navigate with data ID containing special characters
- **Expected**: Page loads correctly, API calls succeed

**DETAIL-014: Missing Data Handling**

- **Action**: Navigate with non-existent ID
- **Expected**: Error message, graceful handling

**DETAIL-015: Button States**

- **Action**: Verify buttons show correct states:
  - Disabled when not applicable
  - Loading during requests
  - Enabled when ready
- **Expected**: States display correctly

**DETAIL-016: Conditional Button Display**

- **Action**: Verify buttons show/hide based on status
- **Expected**: Only applicable buttons visible

**DETAIL-017: Mutation Success Feedback**

- **Action**: Complete publish/finalize/toggle actions
- **Expected**: Success notification appears

**DETAIL-018: Mutation Error Handling**

- **Action**: Simulate API error during mutation
- **Expected**: Error notification, button re-enabled

**DETAIL-019: Data Refresh After Mutation**

- **Action**: Complete mutation, verify data refreshes
- **Expected**: Updated data displays

**DETAIL-020: Lineage API Call**

- **Action**: Click Lineage tab
- **Expected**: Lineage API call made, data loads

**DETAIL-021: Auto-Publish Status API Call**

- **Action**: Load page
- **Expected**: Auto-publish status API call made

**DETAIL-022: Multiple Tab Switching**

- **Action**: Switch between Metadata and Lineage tabs multiple times
- **Expected**: Content loads correctly each time

**DETAIL-023: Long Data ID Handling**

- **Action**: Navigate with very long data ID
- **Expected**: Page loads, URL handles correctly

**DETAIL-024: Special Characters in Data ID**

- **Action**: Navigate with data ID containing /, :, etc.
- **Expected**: URL encoding works, page loads

**DETAIL-025: Concurrent Mutations**

- **Action**: Click multiple action buttons rapidly
- **Expected**: Only one mutation at a time, proper queuing

---

### Streaming Page

#### Test Cases: STREAM-001 to STREAM-020

**STREAM-001: Page Load**

- **Action**: Navigate to /streaming
- **Expected**: Page loads, status displays

**STREAM-002: Status Display**

- **Action**: Verify service status displays
- **Expected**: Status indicator shows running/stopped

**STREAM-003: Start Button**

- **Action**: Click "Start" button
- **Expected**:
  - API call made
  - Status updates to running
  - Button states change

**STREAM-004: Stop Button**

- **Action**: Click "Stop" button
- **Expected**:
  - API call made
  - Status updates to stopped
  - Button states change

**STREAM-005: Restart Button**

- **Action**: Click "Restart" button
- **Expected**: Service restarts, status updates

**STREAM-006: Configure Button**

- **Action**: Click "Configure" button
- **Expected**: Configuration dialog opens

**STREAM-007: Configuration Dialog - Input Directory**

- **Action**: Edit Input Directory field
- **Expected**: Value updates

**STREAM-008: Configuration Dialog - Output Directory**

- **Action**: Edit Output Directory field
- **Expected**: Value updates

**STREAM-009: Configuration Dialog - Scratch Directory**

- **Action**: Edit Scratch Directory field
- **Expected**: Value updates

**STREAM-010: Configuration Dialog - Expected Subbands**

- **Action**: Enter number in Expected Subbands field
- **Expected**: Value updates

**STREAM-011: Configuration Dialog - Chunk Duration**

- **Action**: Enter number in Chunk Duration field
- **Expected**: Value updates

**STREAM-012: Configuration Dialog - Max Workers**

- **Action**: Enter number in Max Workers field
- **Expected**: Value updates

**STREAM-013: Configuration Dialog - Log Level**

- **Action**: Select log level from dropdown
- **Expected**: Selection updates

**STREAM-014: Configuration Dialog - Cancel Button**

- **Action**: Click "Cancel" button
- **Expected**: Dialog closes, changes not saved

**STREAM-015: Configuration Dialog - Save Button**

- **Action**:
  1. Edit configuration
  2. Click "Save" button
- **Expected**:
  - API call made
  - Configuration saved
  - Dialog closes
  - Success notification

**STREAM-016: Button State Management**

- **Action**: Verify buttons enable/disable based on service state
- **Expected**: Correct buttons enabled for each state

**STREAM-017: Loading States**

- **Action**: Verify loading indicators during API calls
- **Expected**: Buttons show loading state

**STREAM-018: Error Handling**

- **Action**: Simulate API errors
- **Expected**: Error notifications display

**STREAM-019: Configuration Validation**

- **Action**: Submit invalid configuration
- **Expected**: Validation errors display

**STREAM-020: Real-time Status Updates**

- **Action**: Verify status updates automatically
- **Expected**: Status reflects current service state

---

### Mosaic Gallery Page

#### Test Cases: MOSAIC-001 to MOSAIC-015

**MOSAIC-001: Page Load**

- **Action**: Navigate to /mosaics
- **Expected**: Page loads, gallery displays

**MOSAIC-002: Start Time Input**

- **Action**: Enter start time
- **Expected**: Value updates

**MOSAIC-003: End Time Input**

- **Action**: Enter end time
- **Expected**: Value updates

**MOSAIC-004: Query Button**

- **Action**:
  1. Enter start and end times
  2. Click "Query Mosaics" button
- **Expected**:
  - API call made
  - Mosaics load
  - Gallery updates

**MOSAIC-005: Query Button Disabled State**

- **Action**: Try to query without times
- **Expected**: Button disabled

**MOSAIC-006: Create Mosaic Button**

- **Action**:
  1. Enter times
  2. Click "Create Mosaic" button
- **Expected**:
  - API call made
  - Mosaic creation initiated
  - Success notification

**MOSAIC-007: Mosaic Card Display**

- **Action**: Verify mosaic cards display:
  - Thumbnail
  - Metadata
  - Action buttons
- **Expected**: All elements visible

**MOSAIC-008: Download FITS Button**

- **Action**: Click "FITS" download button
- **Expected**: File downloads

**MOSAIC-009: Download PNG Button**

- **Action**: Click "PNG" download button
- **Expected**: File downloads

**MOSAIC-010: View Button**

- **Action**: Click "View" button
- **Expected**: Navigate to view page or open viewer

**MOSAIC-011: Empty State**

- **Action**: Query with no results
- **Expected**: Empty state message

**MOSAIC-012: Loading State**

- **Action**: Query mosaics
- **Expected**: Loading indicator displays

**MOSAIC-013: Error State**

- **Action**: Simulate query error
- **Expected**: Error message displays

**MOSAIC-014: Gallery Layout**

- **Action**: Verify responsive grid layout
- **Expected**: Cards arrange correctly

**MOSAIC-015: Card Hover Effects**

- **Action**: Hover over mosaic cards
- **Expected**: Visual feedback (if implemented)

---

### Source Monitoring Page

#### Test Cases: SOURCE-001 to SOURCE-010

**SOURCE-001: Page Load**

- **Action**: Navigate to /sources
- **Expected**: Page loads

**SOURCE-002: Source ID Input**

- **Action**: Enter source ID in text field
- **Expected**: Value updates

**SOURCE-003: Search Button**

- **Action**:
  1. Enter source ID
  2. Click "Search" button
- **Expected**:
  - API call made
  - Results display

**SOURCE-004: Search Button Disabled State**

- **Action**: Try to search with empty field
- **Expected**: Button disabled

**SOURCE-005: Results Table Display**

- **Action**: Verify results table displays:
  - Source information
  - Observation data
  - Flux measurements
- **Expected**: All columns visible

**SOURCE-006: Empty Results**

- **Action**: Search with no results
- **Expected**: Empty state message

**SOURCE-007: Error State**

- **Action**: Simulate search error
- **Expected**: Error message displays

**SOURCE-008: Loading State**

- **Action**: Perform search
- **Expected**: Loading indicator displays

**SOURCE-009: Table Sorting**

- **Action**: Click column headers
- **Expected**: Table sorts

**SOURCE-010: Multiple Searches**

- **Action**: Perform multiple searches
- **Expected**: Results update correctly

---

### Sky View Page

#### Test Cases: SKY-001 to SKY-010

**SKY-001: Page Load**

- **Action**: Navigate to /sky
- **Expected**: Page loads, viewer displays

**SKY-002: Image Browser Display**

- **Action**: Verify image browser component displays
- **Expected**: Image list/grid visible

**SKY-003: Image Selection**

- **Action**: Click on image in browser
- **Expected**: Image selected, viewer updates

**SKY-004: Sky Viewer Display**

- **Action**: Verify JS9 viewer loads
- **Expected**: Viewer displays image

**SKY-005: Viewer Controls**

- **Action**: Interact with JS9 controls
- **Expected**: Controls function correctly

**SKY-006: Catalog Overlay**

- **Action**: Toggle catalog overlay (if implemented)
- **Expected**: Overlay displays/hides

**SKY-007: Image Navigation**

- **Action**: Navigate between images
- **Expected**: Viewer updates

**SKY-008: Loading State**

- **Action**: Load large image
- **Expected**: Loading indicator

**SKY-009: Error State**

- **Action**: Load invalid image
- **Expected**: Error message

**SKY-010: Responsive Layout**

- **Action**: Resize browser
- **Expected**: Layout adapts

---

## Automated Test Script Structure

### Test Framework: Playwright

```typescript
// Example test structure
import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("should navigate to all pages", async ({ page }) => {
    // Test implementation
  });
});

test.describe("Control Page", () => {
  test("should switch tabs", async ({ page }) => {
    // Test implementation
  });

  test("should submit conversion job", async ({ page }) => {
    // Test implementation
  });
});

// ... more test suites
```

## Test Execution Plan

### Phase 1: Manual Testing

1. Execute all manual test cases
2. Document results and issues
3. Fix critical bugs

### Phase 2: Automated Test Development

1. Create Playwright test suite
2. Implement critical path tests
3. Add regression tests

### Phase 3: Continuous Testing

1. Run automated tests on each commit
2. Execute manual tests before releases
3. Update test cases as features change

## Test Data Requirements

### Test Data Setup

- Sample MS files
- Sample calibration tables
- Sample images
- Sample mosaics
- Test source IDs

### Test Environment

- Development environment with test data
- API endpoints available
- Database with test records

## Success Criteria

### Test Coverage Goals

- 100% of clickable features tested
- 100% of form submissions tested
- 100% of navigation paths tested
- 80%+ code coverage for critical paths

### Quality Metrics

- Zero critical bugs
- All test cases pass
- Performance within acceptable limits
- Accessibility standards met

## Maintenance

### Test Maintenance

- Update test cases when features change
- Review and update automated tests quarterly
- Document new features with test cases
- Remove obsolete test cases

### Test Documentation

- Keep test cases in sync with code
- Document test data requirements
- Maintain test environment setup guide

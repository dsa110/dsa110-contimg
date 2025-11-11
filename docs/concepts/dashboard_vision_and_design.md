# DSA-110 Dashboard: Vision, Philosophy & Design Principles

**Date:** 2025-01-XX  
**Status:** Consolidated from multiple design documents  
**Audience:** Frontend developers, UI/UX designers, product managers

---

## Table of Contents

1. [Core Vision](#core-vision)
2. [Design Philosophy](#design-philosophy)
3. [Core Design Principles](#core-design-principles)
4. [User Personas](#user-personas)
5. [Design Patterns & Inspiration](#design-patterns--inspiration)
6. [Visual Design Specifications](#visual-design-specifications)
7. [Accessibility & Usability](#accessibility--usability)

---

## Core Vision

### Unified Command Center

**Vision Statement:** A unified command center that anticipates user needs, eliminates unnecessary steps, and guides users seamlessly through complex workflows. The dashboard serves as the primary interface for monitoring and controlling the autonomous streaming pipeline, with manual override capabilities when needed.

**Key Aspects:**
- **Single Interface** - One place for all pipeline operations
- **Autonomous-First** - Pipeline operates autonomously; dashboard provides visibility and control
- **Anticipatory UX** - Anticipates what users need before they ask
- **Workflow-Focused** - Guides users through complex scientific workflows
- **Science-First** - Direct access to scientific data and discoveries

### Design Philosophy

**Core Philosophy:** Combine Jony Ive's minimalism with Steve Jobs' workflow-focused UX - "It just works."

**Principles:**
1. **Information Density Over Volume** - One excellent, information-rich figure beats 100 individual diagnostics
2. **Ease of Use** - Radio astronomers should quickly find what they need
3. **Real-Time Monitoring** - Pipeline health and data quality at a glance
4. **Science-First** - Direct access to the "good stuff" - images and variability detection
5. **Professional Aesthetic** - Clean, modern, data-dense interfaces for working scientists

### Autonomous Operation Philosophy

**Core Principle:** The streaming pipeline operates autonomously, but the dashboard provides complete visibility and control. When everything runs smoothly, the dashboard stays quiet. When intervention is needed, it anticipates what you'll want to do.

**State-Driven Approach:**
- **Idle State** - Minimal UI when everything is running smoothly
- **Attention State** - Dashboard highlights what needs attention
- **Action Required** - Clear guidance on what to do next
- **Manual Control** - Full control interface when autonomous operations need intervention

---

## Core Design Principles

### 1. Unified Command Center
Single interface for all pipeline operations - monitoring, control, analysis, and exploration.

### 2. Autonomous-First Design
Dashboard monitors autonomous operations, intervenes only when needed. The pipeline runs autonomously; the dashboard provides visibility and control.

### 3. State-Driven UI
Interface adapts to current context:
- **Autonomous** - Monitoring mode, minimal UI
- **Manual** - Full control interface
- **Analysis** - Exploratory workspace
- **Discovery** - ESE candidate investigation
- **Debugging** - Diagnostic interface

### 4. Predictive Loading
Data loads before it's requested. Pre-fetch based on:
- Current dashboard state
- User workflow context
- Recent actions
- Likely next steps

### 5. Contextual Actions
Only show relevant actions based on:
- Current state
- User intent
- Available data
- Workflow context

### 6. Workflow Guidance
Guide users through complex tasks:
- Step-by-step workflows
- Contextual help
- Action suggestions
- Progress indicators

### 7. Zero Configuration
Smart defaults, optional overrides. The dashboard works out-of-the-box with sensible defaults.

### 8. Manual Override
Full control when autonomous operations need intervention:
- Seamless transition from autonomous to manual
- Clear indication of control scope
- Easy return to autonomous mode

### 9. Flexible Analysis
Powerful yet trustworthy exploratory tools for data products:
- Flexible workspace layout
- Multiple analysis tools
- Data product integration
- Export capabilities

### 10. Deterministic Results
All analysis operations are reproducible and traceable:
- Reproducibility scripts
- Parameter tracking
- Data versioning
- Code versioning

---

## User Personas

### 1. Operations Monitor

**Primary Need:** "Is the pipeline healthy?"

**Key Tasks:**
- Monitor pipeline status
- Check system health metrics
- Review queue statistics
- Identify failed observations
- Monitor calibration status

**Dashboard Usage:**
- Primary page: Dashboard (home)
- Secondary pages: Health, Streaming
- Key features: Real-time status, alerts, system metrics

**Design Implications:**
- At-a-glance health indicators
- Clear visual status (green/yellow/red)
- Real-time updates (10-second refresh)
- Alert prioritization

### 2. Data Quality Scientist

**Primary Need:** "Is the data good?"

**Key Tasks:**
- Review calibration quality
- Check image quality metrics
- Examine QA artifacts
- Validate source detections
- Monitor data quality trends

**Dashboard Usage:**
- Primary pages: Health, QA Visualization, Sky View
- Key features: QA plots, calibration metrics, image quality

**Design Implications:**
- Comprehensive QA visualization
- Quality metrics at a glance
- Trend analysis tools
- Diagnostic capabilities

### 3. Science User

**Primary Need:** "Did we detect any interesting variability?"

**Key Tasks:**
- Monitor ESE candidates
- Investigate variable sources
- Review flux timeseries
- Compare with catalogs
- Generate science reports

**Dashboard Usage:**
- Primary pages: Sources, Sky View, Dashboard (ESE alerts)
- Key features: ESE detection, source monitoring, flux plots

**Design Implications:**
- Prominent ESE candidate alerts
- Easy source investigation workflow
- Rich visualization tools
- Export capabilities

---

## Design Patterns & Inspiration

### Information-Dense Interfaces

**Inspiration Sources:**
- **Trading Dashboards** - High information density, real-time updates
- **Mission Control Centers** - Status monitoring, alert systems
- **Astronomical Observatories** - Scientific workflows, data visualization

**Key Techniques:**
- **Small Multiples** - Show many sources/images in compact, comparable grids
- **Sparklines** - Inline flux trends without taking full-figure space
- **Color Coding** - Quick visual status (green=healthy, yellow=warning, red=critical)
- **Drill-Down** - Summary → Detail → Deep Dive on demand
- **Live Updates** - WebSocket or polling for real-time status changes

### Scientific UI Patterns

**Reference Projects:**
- **CARTA** - Radio astronomy UI patterns, FITS viewing
- **Grafana** - Dashboard panel system, time-series visualization
- **JupyterLab** - File browser, tabbed interface, extensibility
- **LOFAR Quality Dashboard** - Real-time observing system monitoring
- **Gaia Archive Interface** - High-density source catalog exploration
- **ZTF Fritz** - Transient classification and real-time alerts

**Adopted Patterns:**
- **Three-Column Detail Layout** - Details card, Visualization, Comments/Annotations (VAST-inspired)
- **Generic Table Component** - Reusable table template with dynamic columns
- **Query Interface** - Complex query builder with multiple filter criteria
- **Detail Page Pattern** - Comprehensive source/image detail views

---

## Visual Design Specifications

### Color Palette (Professional Dark Mode)

**Background Colors:**
- `Background`: `#0D1117` (Very dark gray-blue)
- `Surface`: `#161B22` (Dark gray-blue)
- `Surface Light`: `#21262D` (Medium dark gray)
- `Border`: `#30363D` (Gray)

**Text Colors:**
- `Text Primary`: `#C9D1D9` (Light gray)
- `Text Secondary`: `#8B949E` (Medium gray)
- `Text Tertiary`: `#6E7681` (Dark gray)

**Status Colors:**
- `Primary`: `#58A6FF` (Light blue - for links, primary actions)
- `Success`: `#3FB950` (Green - healthy status, checkmarks)
- `Warning`: `#D29922` (Amber - warnings, elevated metrics)
- `Error`: `#F85149` (Red - errors, critical alerts)
- `Info`: `#79C0FF` (Sky blue - informational)

**Chart Colors:**
- `Line 1`: `#58A6FF` (Blue)
- `Line 2`: `#FF7B72` (Coral)
- `Line 3`: `#A5D6FF` (Light blue)
- `Line 4`: `#FFA657` (Orange)
- `Line 5`: `#7EE787` (Green)

### Typography

**Font Families:**
- **Headers**: Inter or Roboto, 600 weight
- **Body**: Inter or Roboto, 400 weight
- **Monospace** (data, IDs): Fira Code or JetBrains Mono

**Font Sizes:**
- `h1`: 32px (2rem)
- `h2`: 24px (1.5rem)
- `h3`: 20px (1.25rem)
- `h4`: 18px (1.125rem)
- `h5`: 16px (1rem)
- `h6`: 14px (0.875rem)
- `body1`: 16px (1rem)
- `body2`: 14px (0.875rem)
- `caption`: 12px (0.75rem)

### Spacing & Layout

**Grid System:**
- **Base Unit**: 8px (padding, margins in multiples of 8)
- **Card Padding**: 16px (2 units)
- **Section Spacing**: 24px (3 units)
- **Page Padding**: 32px (4 units)

**Component Specifications:**
- **Card Border Radius**: 8px
- **Button Border Radius**: 4px
- **Input Border Radius**: 4px
- **Max Content Width**: 1440px (centered on ultrawide monitors)

**Responsive Breakpoints:**
- **Desktop**: 1920×1080 (primary target)
- **Laptop**: 1440×900
- **Tablet**: 768×1024
- **Mobile**: 390×844 (fallback, limited functionality)

### Component Styling

**Material-UI Theme:**
- Dark mode by default (astronomers work at night)
- Custom color palette (GitHub-inspired)
- Consistent spacing system
- Professional typography

**Visual Hierarchy:**
- Clear distinction between primary and secondary information
- Consistent use of color for status indication
- Appropriate use of whitespace
- Visual grouping of related information

---

## Accessibility & Usability

### WCAG 2.1 AA Compliance

**Minimum Standards:**
- **Contrast Ratios**: 4.5:1 for text, 3:1 for UI components
- **Keyboard Navigation**: All interactive elements keyboard accessible
- **Screen Reader Support**: ARIA labels, semantic HTML
- **Focus Indicators**: Clear focus indicators for keyboard navigation
- **Error Messages**: Clear, actionable error messages

### Usability Principles

**Efficiency:**
- **Zero Clicks for Normal Operation** - Dashboard shows nothing when autonomous operations run smoothly
- **One Click for Common Tasks** - Most actions are one click away
- **Keyboard Shortcuts** - Common actions have keyboard shortcuts
- **Bulk Operations** - Support for bulk actions where appropriate

**Clarity:**
- **Clear Labels** - All UI elements have clear, descriptive labels
- **Consistent Terminology** - Use consistent terminology throughout
- **Visual Feedback** - Clear feedback for all user actions
- **Error Prevention** - Prevent errors through validation and constraints

**Learnability:**
- **Progressive Disclosure** - Show advanced features progressively
- **Contextual Help** - Help available where needed
- **Tooltips** - Tooltips for complex features
- **Documentation** - Comprehensive documentation available

### Color-Blind Friendly Design

**Color Usage:**
- Don't rely solely on color to convey information
- Use patterns, icons, or text labels in addition to color
- Test with color-blind simulators
- Use ColorBrewer color schemes for data visualization

**Status Indicators:**
- Combine color with icons (✓, ⚠, ✗)
- Use text labels in addition to color
- Ensure sufficient contrast for all users

### Mobile & Tablet Support

**Responsive Design:**
- **Desktop-First** - Primary target is desktop (1920×1080)
- **Tablet Support** - Functional on tablets with adapted layout
- **Mobile Fallback** - Basic functionality on mobile devices
- **Touch-Friendly** - Touch targets at least 44×44px

**Mobile Limitations:**
- Some features may be limited on mobile
- Complex visualizations may be simplified
- Tables may use card layout on mobile
- Navigation may use drawer menu on mobile

---

## Key Metrics for Success

### User Experience Metrics

1. **Time to Find Source**: <30 seconds
2. **Time to Assess Pipeline Health**: <10 seconds (at-a-glance dashboard)
3. **Ease of Identifying Variable Sources**: "I know within 5 seconds if something interesting happened today"
4. **Zero Clicks for Normal Operation** - Dashboard shows nothing when autonomous operations run smoothly
5. **One Click for Common Tasks** - Most actions are one click away
6. **Time to Insight** - <2 seconds from discovery to investigation view

### Performance Metrics

1. **Initial Page Load**: <2 seconds
2. **Data Refresh Latency**: <1 second
3. **Source Table Filter/Sort**: <1 second for 10k entries
4. **Image Thumbnail Load**: <500ms per image
5. **Pre-fetch Hit Rate**: >80% of user requests should be pre-fetched

### Operational Metrics

1. **Uptime**: 99.9% (matches API uptime)
2. **No Data Loss on Refresh** - State persistence
3. **Cross-Browser Compatibility** - Chrome, Firefox, Safari
4. **Workflow Completion Rate** - >90% of workflows completed without guidance
5. **User Satisfaction** - Dashboard feels "magical" and intuitive

---

## Related Documentation

- **[Frontend Design Strategy](../concepts/frontend_design.md)** - Strategic design document
- **[Anticipatory Dashboard Implementation](../analysis/ANTICIPATORY_DASHBOARD_IMPLEMENTATION.md)** - Detailed implementation plan
- **[Dashboard Mockups](../concepts/dashboard_mockups.md)** - UI mockups and wireframes
- **[Dashboard Overview](../analysis/DASHBOARD_OVERVIEW_DETAILED.md)** - Comprehensive technical overview

---

**Last Updated:** 2025-01-XX  
**Status:** Consolidated Design Document


# Dashboard Template Recommendations for DSA-110 Pipeline

**Date:** 2025-11-12  
**Purpose:** Identify ready-to-use templates and patterns that match your pipeline monitoring dashboard needs

---

## Executive Summary

Based on your requirements (pipeline monitoring, real-time updates, system health, streaming service control) and existing documentation, here are the **best-fit templates** ranked by relevance:

1. **CARTA** (⭐⭐⭐⭐⭐) - Perfect match: radio astronomy domain, React/TypeScript, proven patterns
2. **Grafana** (⭐⭐⭐⭐) - Excellent dashboard patterns, panel system, time-series visualization
3. **Mantis React Material UI** (⭐⭐⭐⭐) - MUI-based, professional, matches your stack
4. **JupyterLab** (⭐⭐⭐) - Familiar to users, file browser patterns

---

## 1. CARTA (Cube Analysis and Rendering Tool for Astronomy) - **BEST MATCH**

### Why It's Perfect

- ✅ **Same domain**: Built for radio astronomy (ALMA, VLA, SKA)
- ✅ **Same stack**: React + TypeScript + Plotly.js
- ✅ **Proven patterns**: Used by major observatories
- ✅ **Golden Layout**: Flexible, dockable panel system
- ✅ **Widget architecture**: Modular, reusable components
- ✅ **File browser**: Excellent patterns for navigating large directories

### Key Patterns You Should Adopt

#### A. Golden Layout for Flexible Panels
**What it is**: Drag-and-drop, resizable, dockable panels  
**Why you need it**: Users can customize their workspace layout  
**Implementation**: `golden-layout` library

```bash
npm install golden-layout @types/golden-layout
```

**Your use case**: 
- Dashboard panels (Pipeline Status, System Health, ESE Candidates)
- Control panels (Streaming Service, Job Management)
- QA visualization panels (FITS viewer, plots, tables)

#### B. Widget-Based Architecture
**What it is**: Each feature is a "widget" that can be docked/undocked  
**Why you need it**: Modular, reusable components  
**Your widgets**:
- Pipeline Status Widget
- System Health Widget
- ESE Candidates Widget
- Streaming Control Widget
- FITS Viewer Widget
- QA Results Widget

#### C. File Browser with Breadcrumbs
**What it is**: Breadcrumb navigation + search filter + file type tabs  
**Why you need it**: Navigate large QA directories efficiently  
**Your use case**: QA artifact browser (`/qa` page)

#### D. Cursor Info Display
**What it is**: Always-visible cursor information (RA/Dec, pixel values)  
**Why you need it**: Essential for astronomy workflows  
**Your use case**: Sky viewer, pointing visualization

### Resources

- **GitHub**: [CARTAvis/carta-frontend](https://github.com/CARTAvis/carta-frontend)
- **Website**: [cartavis.org](https://cartavis.org/)
- **Documentation**: [CARTA Documentation](https://carta.readthedocs.io/)

### Implementation Priority: **HIGH**

CARTA's patterns are directly applicable to your use case. Start with:
1. Golden Layout for dashboard panels
2. Widget registry system
3. File browser patterns

---

## 2. Grafana Dashboard Patterns - **EXCELLENT FOR MONITORING**

### Why It's Relevant

- ✅ **Dashboard layout**: Excellent grid-based panel system
- ✅ **Time-series visualization**: Perfect for metrics over time
- ✅ **Panel system**: Reusable, consistent components
- ✅ **Real-time updates**: Built for live monitoring
- ✅ **Alert system**: Visual indicators for thresholds

### Key Patterns You Should Adopt

#### A. Dashboard Grid Layout
**What it is**: Drag-and-drop grid of panels  
**Why you need it**: Flexible, user-customizable dashboards  
**Implementation**: `react-grid-layout`

```bash
npm install react-grid-layout @types/react-grid-layout
```

**Your use case**: 
- Main dashboard page layout
- Customizable panel arrangement
- Responsive grid system

#### B. Panel System
**What it is**: Reusable panel components with consistent styling  
**Why you need it**: Consistent UX, easy to add new panel types  
**Your panels**:
- Pipeline Status Panel
- System Health Panel
- ESE Candidates Panel
- Queue Statistics Panel

#### C. Time Range Selector
**What it is**: Date/time range picker for filtering data  
**Why you need it**: Filter metrics by time period  
**Your use case**: Historical metrics, pointing history, ESE detection timeline

### Resources

- **GitHub**: [grafana/grafana](https://github.com/grafana/grafana)
- **UI Components**: [Grafana UI](https://developers.grafana.com/ui/)
- **Dashboard Patterns**: [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)

### Implementation Priority: **MEDIUM**

Grafana patterns are excellent for monitoring dashboards. Use for:
1. Grid layout system
2. Panel component patterns
3. Time-series visualization

---

## 3. Mantis React Material UI - **MATCHES YOUR STACK**

### Why It's Relevant

- ✅ **Material-UI**: Built on MUI (matches your stack)
- ✅ **Professional**: Enterprise-grade UI
- ✅ **Open source**: Free to use
- ✅ **Modern**: React 18, TypeScript
- ✅ **Complete**: Pre-built dashboard layouts

### What You Can Use

- **Layout patterns**: Dashboard layouts, sidebar navigation
- **Component examples**: Tables, forms, cards, charts
- **Theme system**: Dark mode (you already have this)
- **Navigation**: Sidebar navigation patterns

### Resources

- **GitHub**: [codedthemes/mantis-free-react-admin-template](https://github.com/codedthemes/mantis-free-react-admin-template)
- **Demo**: [Mantis Demo](https://mantisdashboard.io/)

### Implementation Priority: **LOW-MEDIUM**

Use as inspiration for:
1. Layout patterns
2. Component styling
3. Navigation structure

**Note**: You're already using MUI, so you can adopt patterns without switching templates.

---

## 4. JupyterLab Patterns - **FAMILIAR TO USERS**

### Why It's Relevant

- ✅ **Familiar**: Your users already use Jupyter notebooks
- ✅ **File browser**: Excellent sidebar file tree pattern
- ✅ **Tabbed interface**: Multiple files open simultaneously
- ✅ **Command palette**: Power user feature (Ctrl+K)

### Key Patterns You Should Adopt

#### A. File Browser Sidebar
**What it is**: Left sidebar with file tree  
**Why you need it**: Familiar to users, efficient navigation  
**Your use case**: QA artifact browser

#### B. Tabbed Interface
**What it is**: Tabs at top, content panels below  
**Why you need it**: Multiple files/views open simultaneously  
**Your use case**: Multiple QA artifacts, multiple FITS files

#### C. Command Palette
**What it is**: Ctrl+K to open command palette  
**Why you need it**: Power users love keyboard shortcuts  
**Implementation**: `kbar` library

```bash
npm install kbar
```

**Your commands**:
- Browse QA Directory
- Run QA
- View Pipeline Status
- Open Streaming Control

### Resources

- **GitHub**: [jupyterlab/jupyterlab](https://github.com/jupyterlab/jupyterlab)
- **Extension Examples**: [JupyterLab Extensions](https://github.com/jupyterlab/extension-examples)

### Implementation Priority: **MEDIUM**

Adopt for:
1. File browser sidebar (QA page)
2. Tabbed interface (multiple viewers)
3. Command palette (power user feature)

---

## 5. Other Templates (Less Relevant but Useful)

### A. CoreUI React Admin Template
- **Why**: Comprehensive UI components, Bootstrap-based
- **Use**: Layout inspiration, component examples
- **Priority**: LOW (you're using MUI, not Bootstrap)

### B. Mantine Analytics Dashboard
- **Why**: Modern design, analytics-focused
- **Use**: Chart/visualization patterns
- **Priority**: LOW (different UI library)

### C. React Admin
- **Why**: Excellent data management patterns
- **Use**: List/Detail views, filtering, pagination
- **Priority**: LOW-MEDIUM (good patterns but different approach)

---

## Recommended Implementation Strategy

### Phase 1: Adopt CARTA Patterns (Highest Priority)

**Week 1-2: Golden Layout**
1. Install `golden-layout`
2. Convert dashboard panels to Golden Layout widgets
3. Implement drag-and-drop panel arrangement
4. Add layout persistence (save/restore layouts)

**Week 3-4: Widget System**
1. Create widget registry
2. Convert existing panels to widgets
3. Implement widget docking/undocking
4. Add widget configuration dialogs

**Week 5-6: File Browser**
1. Implement CARTA-style file browser
2. Add breadcrumb navigation
3. Add search/filter functionality
4. Add file type tabs

### Phase 2: Add Grafana-Style Dashboard (Medium Priority)

**Week 7-8: Grid Layout**
1. Install `react-grid-layout`
2. Implement grid-based dashboard
3. Add panel resizing/dragging
4. Add panel configuration

**Week 9-10: Panel System**
1. Create reusable Panel component
2. Standardize panel styling
3. Add panel actions (refresh, configure, close)
4. Implement panel loading states

### Phase 3: Enhance with JupyterLab Patterns (Lower Priority)

**Week 11-12: File Browser Sidebar**
1. Add sidebar file browser to QA page
2. Implement tree view navigation
3. Add file preview on hover
4. Add keyboard navigation

**Week 13-14: Command Palette**
1. Install `kbar`
2. Implement command palette
3. Add common commands
4. Add keyboard shortcuts

---

## Specific Code Examples

### Golden Layout Integration

```typescript
// components/layout/GoldenLayoutDashboard.tsx
import GoldenLayout from 'golden-layout';
import { useEffect, useRef } from 'react';
import { PipelineStatusWidget } from '../widgets/PipelineStatusWidget';
import { SystemHealthWidget } from '../widgets/SystemHealthWidget';
import { ESECandidatesWidget } from '../widgets/ESECandidatesWidget';

export function GoldenLayoutDashboard() {
  const layoutRef = useRef<HTMLDivElement>(null);
  const glRef = useRef<GoldenLayout | null>(null);
  
  useEffect(() => {
    if (!layoutRef.current) return;
    
    const config: GoldenLayout.Config = {
      content: [{
        type: 'row',
        content: [
          {
            type: 'component',
            componentName: 'pipeline-status',
            title: 'Pipeline Status',
            width: 30,
          },
          {
            type: 'column',
            content: [
              {
                type: 'component',
                componentName: 'system-health',
                title: 'System Health',
                height: 40,
              },
              {
                type: 'component',
                componentName: 'ese-candidates',
                title: 'ESE Candidates',
                height: 60,
              },
            ],
          },
        ],
      }],
    };
    
    glRef.current = new GoldenLayout(config, layoutRef.current);
    
    // Register widgets
    glRef.current.registerComponent('pipeline-status', PipelineStatusWidget);
    glRef.current.registerComponent('system-health', SystemHealthWidget);
    glRef.current.registerComponent('ese-candidates', ESECandidatesWidget);
    
    glRef.current.init();
    
    return () => {
      glRef.current?.destroy();
    };
  }, []);
  
  return <div ref={layoutRef} style={{ height: '100vh' }} />;
}
```

### Widget Registry Pattern

```typescript
// stores/widgetRegistry.ts
import { PipelineStatusWidget } from '../widgets/PipelineStatusWidget';
import { SystemHealthWidget } from '../widgets/SystemHealthWidget';
import { ESECandidatesWidget } from '../widgets/ESECandidatesWidget';
import { StreamingControlWidget } from '../widgets/StreamingControlWidget';

export const WIDGET_REGISTRY = {
  'pipeline-status': {
    component: PipelineStatusWidget,
    title: 'Pipeline Status',
    defaultSize: { width: 400, height: 300 },
    category: 'monitoring',
  },
  'system-health': {
    component: SystemHealthWidget,
    title: 'System Health',
    defaultSize: { width: 400, height: 300 },
    category: 'monitoring',
  },
  'ese-candidates': {
    component: ESECandidatesWidget,
    title: 'ESE Candidates',
    defaultSize: { width: 600, height: 400 },
    category: 'monitoring',
  },
  'streaming-control': {
    component: StreamingControlWidget,
    title: 'Streaming Control',
    defaultSize: { width: 500, height: 400 },
    category: 'control',
  },
};

export type WidgetType = keyof typeof WIDGET_REGISTRY;
```

### CARTA-Style File Browser

```typescript
// components/browser/CARTAFileBrowser.tsx
import { Breadcrumbs, TextField, Tabs, Tab, Box } from '@mui/material';
import { Search, Folder } from '@mui/icons-material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

export function CARTAFileBrowser({ path }: { path: string }) {
  const [filter, setFilter] = useState('');
  const [tab, setTab] = useState(0);
  const { data: listing } = useDirectoryListing(path);
  
  const pathSegments = path.split('/').filter(Boolean);
  
  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', width: 300 },
    { field: 'type', headerName: 'Type', width: 150 },
    { field: 'size', headerName: 'Size', width: 120 },
    { field: 'modified', headerName: 'Modified', width: 180 },
  ];
  
  return (
    <Box>
      {/* Breadcrumb Navigation */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link onClick={() => navigateToPath('/')} sx={{ cursor: 'pointer' }}>
          Root
        </Link>
        {pathSegments.map((segment, idx) => (
          <Link
            key={idx}
            onClick={() => navigateToPath(pathSegments.slice(0, idx + 1).join('/'))}
            sx={{ cursor: 'pointer' }}
          >
            {segment}
          </Link>
        ))}
      </Breadcrumbs>
      
      {/* Search Filter */}
      <TextField
        fullWidth
        size="small"
        placeholder="Filter files..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search />
            </InputAdornment>
          ),
        }}
        sx={{ mb: 2 }}
      />
      
      {/* File Type Tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="All Files" />
        <Tab label="FITS" />
        <Tab label="Images" />
        <Tab label="Logs" />
        <Tab label="Tables" />
      </Tabs>
      
      {/* File List */}
      <DataGrid
        rows={filteredFiles}
        columns={columns}
        onRowClick={(params) => handleFileClick(params.row)}
        getRowId={(row) => row.path}
        pageSizeOptions={[25, 50, 100]}
      />
    </Box>
  );
}
```

---

## Package Recommendations

### Essential (High Priority)

```bash
# Golden Layout for flexible panels
npm install golden-layout @types/golden-layout

# Grid layout alternative (if Golden Layout is too complex)
npm install react-grid-layout @types/react-grid-layout

# Command palette
npm install kbar
```

### Useful (Medium Priority)

```bash
# Form validation
npm install react-hook-form zod @hookform/resolvers

# Notifications (replace alert())
npm install notistack

# Virtual scrolling for large lists
npm install react-window @types/react-window

# Drag & drop
npm install @dnd-kit/core @dnd-kit/sortable
```

### Optional (Low Priority)

```bash
# File viewing
npm install react-file-viewer react-pdf

# Code/text viewing
npm install react-syntax-highlighter @types/react-syntax-highlighter
```

---

## Conclusion

**Best Template Match: CARTA**

CARTA is the perfect template for your use case because:
1. Same domain (radio astronomy)
2. Same technology stack (React + TypeScript)
3. Proven patterns used by major observatories
4. Golden Layout provides flexible, customizable dashboards
5. Widget architecture matches your component needs

**Implementation Priority:**
1. **Start with CARTA patterns** - Golden Layout + Widget System
2. **Add Grafana patterns** - Grid layout + Panel system
3. **Enhance with JupyterLab** - File browser + Command palette

**Quick Win**: Replace your current dashboard layout with Golden Layout to enable drag-and-drop panel arrangement. This alone will significantly improve UX.

---

## References

- **CARTA**: [GitHub](https://github.com/CARTAvis/carta-frontend) | [Website](https://cartavis.org/)
- **Grafana**: [GitHub](https://github.com/grafana/grafana) | [UI Components](https://developers.grafana.com/ui/)
- **JupyterLab**: [GitHub](https://github.com/jupyterlab/jupyterlab)
- **Mantis**: [GitHub](https://github.com/codedthemes/mantis-free-react-admin-template)
- **Your Existing Docs**: `docs/scientific_ui_templates.md` (comprehensive analysis)

---

**Next Steps:**
1. Review CARTA's GitHub repository for implementation details
2. Install Golden Layout and create a proof-of-concept
3. Convert one dashboard panel to a widget
4. Gradually migrate other panels to the widget system


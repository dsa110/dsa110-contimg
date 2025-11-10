# Scientific Web UI Templates & Patterns

## Overview

This document analyzes existing scientific web UIs that can serve as templates or inspiration for the DSA-110 QA dashboard. Each section includes:
- What the tool does
- Key UI patterns to adopt
- How to implement similar patterns
- Code examples where applicable

---

## 1. JupyterLab (Most Relevant!)

**Why it's perfect**: You're already generating Jupyter notebooks, and JupyterLab is built with React/TypeScript.

### Key Patterns to Adopt

#### A. File Browser Sidebar
- **Pattern**: Left sidebar with file tree, right panel for content
- **Implementation**: MUI Drawer + TreeView
- **Why**: Familiar to your users (they use notebooks)

```typescript
import { Drawer, Box } from '@mui/material';
import { TreeView, TreeItem } from '@mui/x-tree-view';
import { Folder, InsertDriveFile } from '@mui/icons-material';

function FileBrowserSidebar({ path }: { path: string }) {
  return (
    <Drawer variant="permanent" sx={{ width: 250 }}>
      <TreeView>
        <TreeItem nodeId="root" label="QA Root" icon={<Folder />}>
          <TreeItem nodeId="fits" label="FITS Files" icon={<Folder />}>
            {fitsFiles.map(file => (
              <TreeItem 
                key={file.path} 
                nodeId={file.path}
                label={file.name}
                icon={<InsertDriveFile />}
                onClick={() => handleFileClick(file)}
              />
            ))}
          </TreeItem>
        </TreeItem>
      </TreeView>
    </Drawer>
  );
}
```

#### B. Tabbed Interface for Multiple Views
- **Pattern**: Tabs at top, content panels below
- **Implementation**: MUI Tabs + TabPanel
- **Why**: Users can have multiple files open simultaneously

```typescript
import { Tabs, Tab, Box } from '@mui/material';

function TabbedViewer() {
  const [value, setValue] = useState(0);
  const [openFiles, setOpenFiles] = useState<File[]>([]);
  
  return (
    <Box>
      <Tabs value={value} onChange={(_, v) => setValue(v)}>
        {openFiles.map((file, idx) => (
          <Tab key={file.path} label={file.name} />
        ))}
      </Tabs>
      {openFiles.map((file, idx) => (
        <TabPanel value={value} index={idx}>
          <FileViewer file={file} />
        </TabPanel>
      ))}
    </Box>
  );
}
```

#### C. Command Palette
- **Pattern**: Ctrl+K to open command palette
- **Implementation**: `cmdk` or `kbar` library
- **Why**: Power users love keyboard shortcuts

```bash
npm install kbar
```

```typescript
import { KBarProvider, KBarPortal, KBarPositioner, KBarAnimator, KBarSearch } from 'kbar';

function App() {
  const actions = [
    {
      id: 'browse-qa',
      name: 'Browse QA Directory',
      shortcut: ['b'],
      perform: () => navigate('/qa/browse'),
    },
    {
      id: 'run-qa',
      name: 'Run QA',
      shortcut: ['r'],
      perform: () => navigate('/qa/run'),
    },
  ];
  
  return (
    <KBarProvider actions={actions}>
      <KBarPortal>
        <KBarPositioner>
          <KBarAnimator>
            <KBarSearch />
            {/* Action list */}
          </KBarAnimator>
        </KBarPositioner>
      </KBarPortal>
      <YourApp />
    </KBarProvider>
  );
}
```

**Resources**:
- [JupyterLab GitHub](https://github.com/jupyterlab/jupyterlab)
- [JupyterLab Extension Examples](https://github.com/jupyterlab/extension-examples)

---

## 2. Grafana (Dashboard Patterns)

**Why it's relevant**: Excellent dashboard layout patterns, panel system, time-series visualization.

### Key Patterns to Adopt

#### A. Dashboard Grid Layout
- **Pattern**: Drag-and-drop grid of panels
- **Implementation**: `react-grid-layout`
- **Why**: Flexible, user-customizable dashboards

```bash
npm install react-grid-layout @types/react-grid-layout
```

```typescript
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-grid-resizable/css/styles.css';

function Dashboard() {
  const layout = [
    { i: 'qa-stats', x: 0, y: 0, w: 4, h: 2 },
    { i: 'recent-runs', x: 4, y: 0, w: 4, h: 2 },
    { i: 'file-browser', x: 0, y: 2, w: 8, h: 4 },
  ];
  
  return (
    <GridLayout
      className="layout"
      layout={layout}
      cols={12}
      rowHeight={100}
      width={1200}
      isDraggable
      isResizable
    >
      <div key="qa-stats">
        <QAStatsPanel />
      </div>
      <div key="recent-runs">
        <RecentRunsPanel />
      </div>
      <div key="file-browser">
        <FileBrowserPanel />
      </div>
    </GridLayout>
  );
}
```

#### B. Panel System
- **Pattern**: Reusable panel components with consistent styling
- **Implementation**: MUI Card + consistent props interface
- **Why**: Consistent UX, easy to add new panel types

```typescript
interface PanelProps {
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  loading?: boolean;
}

function Panel({ title, children, actions, loading }: PanelProps) {
  return (
    <Card>
      <CardHeader 
        title={title}
        action={actions}
      />
      <CardContent>
        {loading ? <Skeleton /> : children}
      </CardContent>
    </Card>
  );
}

// Usage
<Panel 
  title="QA Statistics"
  actions={<IconButton><Refresh /></IconButton>}
  loading={isLoading}
>
  <QAStats data={stats} />
</Panel>
```

#### C. Time Range Selector
- **Pattern**: Date/time range picker for filtering data
- **Implementation**: MUI DatePicker (you already have it!)
- **Why**: Common pattern for time-series data

```typescript
import { DatePicker } from '@mui/x-date-pickers';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';

function TimeRangeSelector({ onChange }: { onChange: (range: [Date, Date]) => void }) {
  const [start, setStart] = useState<Dayjs | null>(null);
  const [end, setEnd] = useState<Dayjs | null>(null);
  
  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <DatePicker label="Start" value={start} onChange={setStart} />
      <DatePicker label="End" value={end} onChange={setEnd} />
    </LocalizationProvider>
  );
}
```

**Resources**:
- [Grafana GitHub](https://github.com/grafana/grafana)
- [Grafana UI Components](https://developers.grafana.com/ui/)

---

## 3. Aladin Lite (Astronomy-Specific)

**Why it's relevant**: Built specifically for astronomy, handles FITS files, sky coordinates.

### Key Patterns to Adopt

#### A. Embedded Sky Viewer
- **Pattern**: Iframe or Web Component for Aladin Lite
- **Implementation**: Direct integration
- **Why**: Proven astronomy tool, handles coordinates well

```typescript
function SkyViewer({ ra, dec, fov }: { ra: number; dec: number; fov: number }) {
  return (
    <iframe
      src={`https://aladin.u-strasbg.fr/AladinLite/api/v3/lite/aladin.html?target=${ra}%20${dec}&fov=${fov}`}
      width="100%"
      height="600px"
      frameBorder="0"
    />
  );
}
```

#### B. Coordinate Display
- **Pattern**: Always show RA/Dec, allow coordinate input
- **Implementation**: MUI TextField with coordinate formatting
- **Why**: Essential for astronomy workflows

```typescript
function CoordinateInput({ value, onChange }: { value: [number, number]; onChange: (coords: [number, number]) => void }) {
  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      <TextField
        label="RA (deg)"
        type="number"
        value={value[0]}
        onChange={(e) => onChange([parseFloat(e.target.value), value[1]])}
      />
      <TextField
        label="Dec (deg)"
        type="number"
        value={value[1]}
        onChange={(e) => onChange([value[0], parseFloat(e.target.value)])}
      />
    </Box>
  );
}
```

**Resources**:
- [Aladin Lite](https://aladin.u-strasbg.fr/AladinLite/)
- [Aladin Lite API](https://aladin.u-strasbg.fr/AladinLite/doc/API/)

---

## 4. JS9 (FITS Viewer - You're Already Using This!)

**Why it's relevant**: You're already integrating JS9, but can learn from its UI patterns.

### Key Patterns to Adopt

#### A. Control Panel Above Viewer
- **Pattern**: Toolbar with scale/colormap controls above image
- **Implementation**: MUI AppBar or Toolbar
- **Why**: JS9's proven layout for FITS viewing

```typescript
function FITSViewerControls({ 
  scale, 
  colormap, 
  onScaleChange, 
  onColormapChange 
}: FITSViewerControlsProps) {
  return (
    <Toolbar>
      <FormControl size="small">
        <InputLabel>Scale</InputLabel>
        <Select value={scale} onChange={(e) => onScaleChange(e.target.value)}>
          <MenuItem value="linear">Linear</MenuItem>
          <MenuItem value="log">Log</MenuItem>
          <MenuItem value="sqrt">Square Root</MenuItem>
        </Select>
      </FormControl>
      
      <FormControl size="small">
        <InputLabel>Colormap</InputLabel>
        <Select value={colormap} onChange={(e) => onColormapChange(e.target.value)}>
          <MenuItem value="grey">Grey</MenuItem>
          <MenuItem value="heat">Heat</MenuItem>
          <MenuItem value="cool">Cool</MenuItem>
        </Select>
      </FormControl>
      
      <IconButton><ZoomIn /></IconButton>
      <IconButton><ZoomOut /></IconButton>
      <IconButton><Fullscreen /></IconButton>
    </Toolbar>
  );
}
```

#### B. Image Information Sidebar
- **Pattern**: Side panel showing FITS header info
- **Implementation**: MUI Drawer or Accordion
- **Why**: Users need to see header information

```typescript
function FITSHeaderPanel({ header }: { header: FITSHeader }) {
  return (
    <Drawer anchor="right" open={open} onClose={() => setOpen(false)}>
      <Box sx={{ p: 2, width: 300 }}>
        <Typography variant="h6">FITS Header</Typography>
        <List>
          {Object.entries(header).map(([key, value]) => (
            <ListItem>
              <ListItemText 
                primary={key}
                secondary={String(value)}
              />
            </ListItem>
          ))}
        </List>
      </Box>
    </Drawer>
  );
}
```

**Resources**:
- [JS9 Documentation](https://js9.si.edu/)
- [JS9 GitHub](https://github.com/ericmandel/js9)

---

## 5. Metabase (Data Exploration Patterns)

**Why it's relevant**: Excellent patterns for exploring large datasets, query builders.

### Key Patterns to Adopt

#### A. Query Builder Interface
- **Pattern**: Visual query builder for filtering data
- **Implementation**: MUI components + React Query
- **Why**: Users need to filter QA results

```typescript
function QueryBuilder({ onQueryChange }: { onQueryChange: (query: Query) => void }) {
  const [filters, setFilters] = useState<Filter[]>([]);
  
  return (
    <Box>
      <Typography variant="h6">Filters</Typography>
      {filters.map((filter, idx) => (
        <Box key={idx} sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Select value={filter.field}>
            <MenuItem value="ms_path">MS Path</MenuItem>
            <MenuItem value="date">Date</MenuItem>
            <MenuItem value="status">Status</MenuItem>
          </Select>
          <Select value={filter.operator}>
            <MenuItem value="equals">Equals</MenuItem>
            <MenuItem value="contains">Contains</MenuItem>
            <MenuItem value="greater_than">Greater Than</MenuItem>
          </Select>
          <TextField 
            value={filter.value}
            onChange={(e) => updateFilter(idx, { ...filter, value: e.target.value })}
          />
          <IconButton onClick={() => removeFilter(idx)}><Delete /></IconButton>
        </Box>
      ))}
      <Button onClick={addFilter}>Add Filter</Button>
    </Box>
  );
}
```

#### B. Saved Views/Bookmarks
- **Pattern**: Save common queries/views
- **Implementation**: LocalStorage or backend API
- **Why**: Users repeat common queries

```typescript
function SavedViews() {
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);
  
  return (
    <List>
      {savedViews.map(view => (
        <ListItem 
          button
          onClick={() => loadView(view)}
        >
          <ListItemIcon><Bookmark /></ListItemIcon>
          <ListItemText primary={view.name} />
        </ListItem>
      ))}
    </List>
  );
}
```

**Resources**:
- [Metabase GitHub](https://github.com/metabase/metabase)
- [Metabase Frontend](https://github.com/metabase/metabase/tree/master/frontend/src)

---

## 6. CASA Tools (Measurement Set Patterns)

**Why it's relevant**: You're browsing CASA tables, can learn from CASA's UI patterns.

### Key Patterns to Adopt

#### A. Table Browser with Column Selection
- **Pattern**: Checkboxes to show/hide columns
- **Implementation**: AG Grid column visibility
- **Why**: CASA tables have many columns

```typescript
import { AgGridReact } from 'ag-grid-react';

function CasaTableBrowser({ table }: { table: CasaTable }) {
  const [columnDefs, setColumnDefs] = useState(
    table.columns.map(col => ({
      field: col,
      headerName: col,
      hide: false, // Can be toggled
    }))
  );
  
  return (
    <Box>
      <Button onClick={openColumnSelector}>Select Columns</Button>
      <AgGridReact
        rowData={tableData}
        columnDefs={columnDefs}
        defaultColDef={{ resizable: true, sortable: true }}
      />
    </Box>
  );
}
```

#### B. Subtable Navigation
- **Pattern**: Breadcrumb or tree for navigating subtables
- **Implementation**: MUI Breadcrumbs
- **Why**: MS files have nested structure

```typescript
function SubtableNavigator({ path, onNavigate }: { path: string[]; onNavigate: (path: string[]) => void }) {
  return (
    <Breadcrumbs>
      {path.map((segment, idx) => (
        <Link
          key={idx}
          onClick={() => onNavigate(path.slice(0, idx + 1))}
          sx={{ cursor: 'pointer' }}
        >
          {segment}
        </Link>
      ))}
    </Breadcrumbs>
  );
}
```

---

## 7. Open Source React Dashboard Templates

### A. Material Dashboard React
- **GitHub**: https://github.com/creativetimofficial/material-dashboard-react
- **Why**: Built on MUI, scientific-friendly
- **Use**: Layout structure, navigation patterns

### B. React Admin
- **GitHub**: https://github.com/marmelab/react-admin
- **Why**: Excellent data management patterns
- **Use**: List/Detail views, filtering, pagination

### C. Refine
- **GitHub**: https://github.com/refinedev/refine
- **Why**: Modern, TypeScript-first, built on React Query
- **Use**: CRUD patterns, data fetching

---

## Recommended Implementation Strategy

### Phase 1: Adopt JupyterLab Patterns (Highest Priority)
1. **File browser sidebar** - Users are familiar with this
2. **Tabbed interface** - Multiple files open simultaneously
3. **Command palette** - Power user feature

### Phase 2: Add Grafana-Style Dashboard
1. **Grid layout** - Flexible, customizable
2. **Panel system** - Consistent components
3. **Time range selector** - For filtering QA runs

### Phase 3: Enhance with Astronomy-Specific Features
1. **Coordinate displays** - RA/Dec everywhere relevant
2. **Sky viewer integration** - Aladin Lite for context
3. **FITS header panels** - Always accessible

### Phase 4: Add Data Exploration Features
1. **Query builder** - Filter QA results
2. **Saved views** - Common queries
3. **Export options** - Download data/plots

---

## Code Template: JupyterLab-Style Layout

```typescript
import { Box, Drawer, AppBar, Toolbar, Tabs, Tab } from '@mui/material';
import { useState } from 'react';

function JupyterLabStyleLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [openTabs, setOpenTabs] = useState<File[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  
  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* Left Sidebar - File Browser */}
      <Drawer
        variant="persistent"
        open={sidebarOpen}
        sx={{
          width: 250,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: 250,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <FileBrowserTree />
      </Drawer>
      
      {/* Main Content Area */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Top Toolbar */}
        <AppBar position="static">
          <Toolbar>
            <IconButton onClick={() => setSidebarOpen(!sidebarOpen)}>
              <Menu />
            </IconButton>
            <Typography variant="h6">QA Dashboard</Typography>
          </Toolbar>
        </AppBar>
        
        {/* Tabs */}
        {openTabs.length > 0 && (
          <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
            {openTabs.map((file, idx) => (
              <Tab 
                key={file.path}
                label={file.name}
                icon={<IconButton size="small" onClick={() => closeTab(idx)}><Close /></IconButton>}
                iconPosition="end"
              />
            ))}
          </Tabs>
        )}
        
        {/* Content */}
        <Box sx={{ flexGrow: 1, p: 2 }}>
          {openTabs[activeTab] && (
            <FileViewer file={openTabs[activeTab]} />
          )}
        </Box>
      </Box>
    </Box>
  );
}
```

---

## 8. CARTA (Cube Analysis and Rendering Tool for Astronomy) - **HIGHLY RELEVANT!**

**Why it's perfect**: Built specifically for radio astronomy (ALMA, VLA, SKA), handles large data cubes, uses React/TypeScript, and has proven UI patterns for astronomical data visualization.

**GitHub**: [CARTAvis/carta-frontend](https://github.com/CARTAvis/carta-frontend)  
**Website**: [cartavis.org](https://cartavis.org/)

### Architecture Overview

CARTA uses:
- **Blueprint UI** (similar to MUI) - Component library
- **Golden Layout** - Flexible, dockable panel system
- **MobX** - State management
- **React + TypeScript** - Same stack as yours!
- **Plotly.js** - Plotting (you already have this!)
- **React Window** - Virtualization (you already have this!)
- **WebGL** - High-performance rendering via Konva

### Key Patterns to Adopt

#### A. Golden Layout for Flexible Panels
- **Pattern**: Drag-and-drop, resizable, dockable panels
- **Implementation**: `golden-layout` library
- **Why**: Users can customize their workspace layout

```bash
npm install golden-layout @types/golden-layout
```

```typescript
import GoldenLayout from 'golden-layout';
import 'golden-layout/dist/css/goldenlayout-base.css';
import 'golden-layout/dist/css/themes/goldenlayout-dark-theme.css';

function DashboardLayout() {
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
            componentName: 'file-browser',
            title: 'File Browser',
            width: 25,
          },
          {
            type: 'column',
            content: [
              {
                type: 'component',
                componentName: 'fits-viewer',
                title: 'FITS Viewer',
                height: 60,
              },
              {
                type: 'component',
                componentName: 'qa-results',
                title: 'QA Results',
                height: 40,
              },
            ],
          },
        ],
      }],
    };
    
    glRef.current = new GoldenLayout(config, layoutRef.current);
    
    // Register components
    glRef.current.registerComponent('file-browser', FileBrowser);
    glRef.current.registerComponent('fits-viewer', FITSViewer);
    glRef.current.registerComponent('qa-results', QAResults);
    
    glRef.current.init();
    
    return () => {
      glRef.current?.destroy();
    };
  }, []);
  
  return <div ref={layoutRef} style={{ height: '100vh' }} />;
}
```

#### B. File Browser with Breadcrumbs & Filtering
- **Pattern**: Breadcrumb navigation, search filter, file type tabs
- **Implementation**: MUI Breadcrumbs + TextField + Tabs
- **Why**: CARTA's file browser is excellent for navigating large directories

```typescript
import { Breadcrumbs, TextField, Tabs, Tab, InputAdornment } from '@mui/material';
import { Search, Folder } from '@mui/icons-material';

function FileBrowser({ path }: { path: string }) {
  const [filter, setFilter] = useState('');
  const [tab, setTab] = useState(0);
  
  return (
    <Box>
      {/* Breadcrumb Navigation */}
      <Breadcrumbs sx={{ mb: 2 }}>
        {path.split('/').map((segment, idx, arr) => (
          <Link
            key={idx}
            onClick={() => navigateToPath(arr.slice(0, idx + 1).join('/'))}
            sx={{ cursor: 'pointer' }}
          >
            {segment || 'Root'}
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
      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        <Tab label="All Files" />
        <Tab label="FITS" />
        <Tab label="Images" />
        <Tab label="Logs" />
        <Tab label="Tables" />
      </Tabs>
      
      {/* File List */}
      <FileList files={filteredFiles} filter={filter} type={tab} />
    </Box>
  );
}
```

#### C. Widget-Based Architecture
- **Pattern**: Each feature is a "widget" that can be docked/undocked
- **Implementation**: Component system with widget registry
- **Why**: Modular, reusable components

```typescript
// Widget registry
const WIDGET_REGISTRY = {
  'fits-viewer': FITSViewerWidget,
  'histogram': HistogramWidget,
  'spatial-profile': SpatialProfileWidget,
  'spectral-profile': SpectralProfileWidget,
  'stats': StatsWidget,
  'catalog': CatalogWidget,
};

function WidgetRenderer({ widgetType, props }: { widgetType: string; props: any }) {
  const Widget = WIDGET_REGISTRY[widgetType];
  if (!Widget) return <div>Unknown widget: {widgetType}</div>;
  return <Widget {...props} />;
}
```

#### D. Floating Widgets
- **Pattern**: Widgets can float above main layout
- **Implementation**: `react-rnd` (CARTA uses this)
- **Why**: Users can have multiple views visible simultaneously

```bash
npm install react-rnd
```

```typescript
import { Rnd } from 'react-rnd';

function FloatingWidget({ children }: { children: React.ReactNode }) {
  return (
    <Rnd
      default={{
        x: 100,
        y: 100,
        width: 400,
        height: 300,
      }}
      minWidth={200}
      minHeight={150}
      bounds="window"
    >
      <Paper sx={{ height: '100%', p: 2 }}>
        {children}
      </Paper>
    </Rnd>
  );
}
```

#### E. Dialog System
- **Pattern**: Centralized dialog management
- **Implementation**: Dialog store + dialog components
- **Why**: Consistent dialog behavior

```typescript
// Dialog Store (MobX pattern, but can use Zustand)
class DialogStore {
  @observable openDialogs: Map<string, DialogConfig> = new Map();
  
  @action openDialog(id: string, config: DialogConfig) {
    this.openDialogs.set(id, config);
  }
  
  @action closeDialog(id: string) {
    this.openDialogs.delete(id);
  }
}

// Dialog Manager Component
function DialogManager() {
  const dialogStore = useDialogStore();
  
  return (
    <>
      {Array.from(dialogStore.openDialogs.entries()).map(([id, config]) => (
        <Dialog
          key={id}
          open={true}
          onClose={() => dialogStore.closeDialog(id)}
          maxWidth={config.maxWidth}
          fullWidth={config.fullWidth}
        >
          <DialogTitle>{config.title}</DialogTitle>
          <DialogContent>
            {config.content}
          </DialogContent>
        </Dialog>
      ))}
    </>
  );
}
```

#### F. Cursor Info Display
- **Pattern**: Always-visible cursor information (RA/Dec, pixel values)
- **Implementation**: Fixed position component
- **Why**: Essential for astronomy workflows

```typescript
function CursorInfo({ position }: { position: { ra: number; dec: number; value: number } }) {
  return (
    <Paper
      sx={{
        position: 'fixed',
        bottom: 16,
        left: 16,
        p: 1,
        zIndex: 1000,
      }}
    >
      <Typography variant="caption" display="block">
        RA: {formatRA(position.ra)}
      </Typography>
      <Typography variant="caption" display="block">
        Dec: {formatDec(position.dec)}
      </Typography>
      <Typography variant="caption" display="block">
        Value: {position.value.toExponential(2)}
      </Typography>
    </Paper>
  );
}
```

#### G. Render Configuration Panel
- **Pattern**: Side panel for image rendering controls (scale, colormap, etc.)
- **Implementation**: MUI Drawer or Accordion
- **Why**: CARTA's render config is excellent

```typescript
function RenderConfigPanel({ config, onChange }: RenderConfigProps) {
  return (
    <Drawer anchor="right" open={open} onClose={() => setOpen(false)}>
      <Box sx={{ width: 300, p: 2 }}>
        <Typography variant="h6">Render Configuration</Typography>
        
        <FormControl fullWidth sx={{ mt: 2 }}>
          <InputLabel>Scale</InputLabel>
          <Select value={config.scale} onChange={(e) => onChange({ ...config, scale: e.target.value })}>
            <MenuItem value="linear">Linear</MenuItem>
            <MenuItem value="log">Logarithmic</MenuItem>
            <MenuItem value="sqrt">Square Root</MenuItem>
            <MenuItem value="power">Power</MenuItem>
          </Select>
        </FormControl>
        
        <FormControl fullWidth sx={{ mt: 2 }}>
          <InputLabel>Colormap</InputLabel>
          <Select value={config.colormap} onChange={(e) => onChange({ ...config, colormap: e.target.value })}>
            <MenuItem value="grey">Grey</MenuItem>
            <MenuItem value="heat">Heat</MenuItem>
            <MenuItem value="cool">Cool</MenuItem>
            <MenuItem value="rainbow">Rainbow</MenuItem>
          </Select>
        </FormControl>
        
        <Slider
          label="Percentile"
          value={config.percentile}
          onChange={(_, v) => onChange({ ...config, percentile: v as number })}
          min={0}
          max={100}
          step={1}
          sx={{ mt: 2 }}
        />
      </Box>
    </Drawer>
  );
}
```

#### H. Workspace/Layout Persistence
- **Pattern**: Save and restore user layouts
- **Implementation**: LocalStorage or backend API
- **Why**: Users can save their preferred workspace configuration

```typescript
function useLayoutPersistence() {
  const saveLayout = (name: string, config: LayoutConfig) => {
    const layouts = JSON.parse(localStorage.getItem('layouts') || '{}');
    layouts[name] = config;
    localStorage.setItem('layouts', JSON.stringify(layouts));
  };
  
  const loadLayout = (name: string): LayoutConfig | null => {
    const layouts = JSON.parse(localStorage.getItem('layouts') || '{}');
    return layouts[name] || null;
  };
  
  const listLayouts = (): string[] => {
    const layouts = JSON.parse(localStorage.getItem('layouts') || '{}');
    return Object.keys(layouts);
  };
  
  return { saveLayout, loadLayout, listLayouts };
}
```

### CARTA Component Structure

```
carta-frontend/src/
├── components/          # UI components
│   ├── Dialogs/        # Dialog components (FileBrowser, etc.)
│   ├── ImageView/      # Main image viewer
│   ├── Histogram/      # Histogram widget
│   ├── SpatialProfiler/ # Profile widgets
│   └── ...
├── stores/             # MobX stores (state management)
│   ├── AppStore.ts     # Main app state
│   ├── FrameStore.ts   # Image frame state
│   ├── LayoutStore.ts  # Layout management
│   └── ...
├── services/           # Backend communication
│   ├── BackendService.ts
│   ├── TileService.ts  # Image tiling
│   └── ...
└── models/             # Data models
    ├── Wcs.ts          # WCS handling
    ├── FrameView.ts    # View models
    └── ...
```

### Key Libraries CARTA Uses (You Should Consider)

1. **Golden Layout** - Flexible panel system
   ```bash
   npm install golden-layout @types/golden-layout
   ```

2. **Blueprint UI** - Alternative to MUI (or use MUI equivalents)
   - CARTA uses Blueprint, but MUI has equivalent components

3. **MobX** - State management (or use Zustand/Redux)
   ```bash
   npm install mobx mobx-react
   ```

4. **React RND** - Resizable, draggable components
   ```bash
   npm install react-rnd
   ```

5. **React Window** - Virtualization (you already have this!)

### CARTA-Style Layout Template

```typescript
import GoldenLayout from 'golden-layout';
import { FileBrowser } from './components/FileBrowser';
import { FITSViewer } from './components/FITSViewer';
import { QAResults } from './components/QAResults';

function CARTAStyleDashboard() {
  const layoutRef = useRef<HTMLDivElement>(null);
  const glRef = useRef<GoldenLayout | null>(null);
  
  useEffect(() => {
    if (!layoutRef.current) return;
    
    const config: GoldenLayout.Config = {
      content: [
        {
          type: 'row',
          content: [
            {
              type: 'component',
              componentName: 'file-browser',
              title: 'File Browser',
              width: 20,
            },
            {
              type: 'column',
              content: [
                {
                  type: 'component',
                  componentName: 'fits-viewer',
                  title: 'FITS Viewer',
                  height: 70,
                },
                {
                  type: 'row',
                  content: [
                    {
                      type: 'component',
                      componentName: 'qa-results',
                      title: 'QA Results',
                      width: 50,
                    },
                    {
                      type: 'component',
                      componentName: 'stats',
                      title: 'Statistics',
                      width: 50,
                    },
                  ],
                  height: 30,
                },
              ],
            },
          ],
        },
      ],
    };
    
    glRef.current = new GoldenLayout(config, layoutRef.current);
    
    // Register components
    glRef.current.registerComponent('file-browser', FileBrowser);
    glRef.current.registerComponent('fits-viewer', FITSViewer);
    glRef.current.registerComponent('qa-results', QAResults);
    glRef.current.registerComponent('stats', StatsWidget);
    
    glRef.current.init();
    
    return () => {
      glRef.current?.destroy();
    };
  }, []);
  
  return (
    <Box sx={{ height: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6">QA Dashboard</Typography>
        </Toolbar>
      </AppBar>
      <div ref={layoutRef} style={{ height: 'calc(100vh - 64px)' }} />
      <CursorInfo />
    </Box>
  );
}
```

### Why CARTA Patterns Are Perfect for Your Use Case

1. **Same Domain**: Radio astronomy (ALMA, VLA, SKA) - exactly your field!
2. **Same Stack**: React + TypeScript - matches your frontend
3. **Large Data**: Handles GB-TB data cubes efficiently
4. **Proven UI**: Used by thousands of astronomers
5. **Open Source**: Can study and adapt patterns
6. **Widget System**: Perfect for modular QA features
7. **Layout Flexibility**: Users can customize workspace

### Resources

- **CARTA Frontend GitHub**: https://github.com/CARTAvis/carta-frontend
- **CARTA Documentation**: https://cartavis.org/
- **CARTA User Manual**: https://cartavis.org/docs/user-manual/
- **Golden Layout Docs**: https://www.golden-layout.com/
- **Blueprint UI**: https://blueprintjs.com/ (or use MUI equivalents)

---

## Summary: Best Practices from Scientific UIs

### Priority Ranking (Most Relevant First)

1. **CARTA Patterns** ⭐⭐⭐⭐⭐
   - **Golden Layout** - Flexible, dockable panels
   - **Widget System** - Modular components
   - **File Browser** - Breadcrumbs, filtering, tabs
   - **Render Config** - Side panel for image controls
   - **Why**: Built for radio astronomy, same domain, proven UI

2. **JupyterLab Patterns** ⭐⭐⭐⭐
   - **File Browser Sidebar** - Familiar to users
   - **Tabbed Interface** - Multiple files open
   - **Command Palette** - Power user feature
   - **Why**: Users already use notebooks

3. **Grafana Dashboard Patterns** ⭐⭐⭐
   - **Grid Layout** - Drag-and-drop panels
   - **Panel System** - Reusable components
   - **Time Range Selector** - For filtering QA runs
   - **Why**: Excellent dashboard patterns

4. **Astronomy-Specific Features** ⭐⭐⭐⭐
   - **Aladin Lite** - Sky viewer integration
   - **Coordinate Displays** - RA/Dec everywhere
   - **FITS Header Panels** - Always accessible
   - **Why**: Essential astronomy context

5. **Data Exploration Patterns** ⭐⭐⭐
   - **Query Builders** - Visual filters
   - **Saved Views** - Common queries
   - **Export Options** - Download data/plots
   - **Why**: Users need to explore QA data

### Recommended Implementation Order

1. **Start with CARTA's Golden Layout** - Most relevant for your use case
2. **Add JupyterLab-style file browser** - Familiar to users
3. **Implement widget system** - Modular QA features
4. **Add astronomy context** - Coordinates, sky viewers
5. **Enhance with data exploration** - Query builders, filters

### Key Takeaways

- **CARTA is your best template** - Same domain, same stack, proven patterns
- **Golden Layout** - Essential for flexible, customizable dashboards
- **Widget Architecture** - Perfect for modular QA features
- **File Browser Patterns** - CARTA's file browser is excellent
- **Render Configuration** - Side panel for image controls
- **Workspace Persistence** - Save user layouts

By adopting CARTA's patterns (especially Golden Layout and widget system), you'll create a dashboard that feels professional and familiar to radio astronomers while leveraging proven UI patterns from a tool built specifically for your domain.


# Analysis Workspace: Complementary Tools & Libraries

Beyond Golden Layout, here are tools and patterns that would enhance the flexible, trustworthy, and deterministic analysis workspace.

---

## Table of Contents

1. [Code & Script Management](#code--script-management)
2. [Data Visualization](#data-visualization)
3. [Data Tables & Grids](#data-tables--grids)
4. [Comparison & Diff Views](#comparison--diff-views)
5. [Parameter Configuration](#parameter-configuration)
6. [Workflow Visualization](#workflow-visualization)
7. [Documentation & Notes](#documentation--notes)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [State Management & Debugging](#state-management--debugging)
10. [File Management](#file-management)
11. [Recommendations Summary](#recommendations-summary)

---

## Code & Script Management

### Monaco Editor (VS Code Editor)

**Why:** For viewing and editing reproduction scripts, Python analysis code, and parameter configurations.

**Benefits:**
- Full Python syntax highlighting
- Code completion and IntelliSense
- Multi-cursor editing
- Find/replace with regex
- Code folding
- Error highlighting
- Integrated terminal (optional)

**Use Cases:**
- View generated reproduction scripts
- Edit analysis parameters as code
- Write custom analysis scripts
- Compare script versions

**Package:** `@monaco-editor/react`

```typescript
import Editor from '@monaco-editor/react';

<Editor
  height="400px"
  language="python"
  value={reproductionScript}
  onChange={(value) => setScript(value)}
  theme="vs-dark"
  options={{
    minimap: { enabled: false },
    fontSize: 14,
    readOnly: false, // Allow editing for custom scripts
  }}
/>
```

### React Diff Viewer

**Why:** Compare analysis results, script versions, or parameter configurations side-by-side.

**Benefits:**
- Side-by-side comparison
- Syntax highlighting
- Line-by-line diff
- Split or unified view
- Copy to clipboard

**Use Cases:**
- Compare analysis results between runs
- Compare script versions
- Compare parameter configurations
- Verify reproducibility

**Package:** `react-diff-viewer`

```typescript
import ReactDiffViewer from 'react-diff-viewer';

<ReactDiffViewer
  oldValue={previousResults}
  newValue={currentResults}
  splitView={true}
  showDiffOnly={false}
/>
```

---

## Data Visualization

### You Already Have: Plotly.js & D3.js ✓

**Plotly.js** - Excellent for:
- Interactive scientific plots
- 3D visualizations
- Time series (light curves)
- Scatter plots with error bars
- Heatmaps

**D3.js** - Excellent for:
- Custom visualizations
- Network graphs
- Hierarchical data
- Custom interactions

### Additional Visualization Libraries

#### Recharts (Lightweight Alternative)

**Why:** Simpler API than D3, good for standard scientific plots.

**Benefits:**
- React-native (composable components)
- Responsive by default
- Good TypeScript support
- Smaller bundle size than Plotly

**Use Cases:**
- Quick light curve plots
- Simple histograms
- Bar charts for statistics

**Package:** `recharts`

#### Visx (Airbnb's Visualization Library)

**Why:** Low-level visualization primitives built on D3, with React components.

**Benefits:**
- Full control over rendering
- Composable primitives
- TypeScript-first
- Good performance

**Use Cases:**
- Custom scientific visualizations
- Complex multi-panel plots
- Interactive data exploration

**Package:** `@visx/visx`

---

## Data Tables & Grids

### You Already Have: AG Grid ✓

**AG Grid** - Excellent for:
- Large datasets (virtual scrolling)
- Sorting, filtering, grouping
- Column resizing
- Export to CSV/Excel

### Additional Table Options

#### TanStack Table (React Table v8)

**Why:** Headless table library - full control over UI, perfect for custom scientific table needs.

**Benefits:**
- Headless (you control the UI)
- Excellent TypeScript support
- Flexible column definitions
- Virtual scrolling
- Column resizing, sorting, filtering
- Row selection
- Column pinning

**Use Cases:**
- Custom catalog comparison tables
- Source investigation tables
- Analysis result tables with custom formatting

**Package:** `@tanstack/react-table`

```typescript
import { useReactTable, getCoreRowModel } from '@tanstack/react-table';

const table = useReactTable({
  data: catalogResults,
  columns: catalogColumns,
  getCoreRowModel: getCoreRowModel(),
});
```

#### React Data Grid

**Why:** More flexible than AG Grid, better for scientific data with custom cell renderers.

**Benefits:**
- Custom cell renderers (e.g., plot cells)
- Inline editing
- Column groups
- Row grouping
- Better for scientific data types

**Use Cases:**
- Catalog tables with embedded plots
- Analysis results with custom formatting
- Interactive data tables

**Package:** `react-data-grid`

---

## Comparison & Diff Views

### React Split Pane

**Why:** Side-by-side comparisons of images, catalogs, or analysis results.

**Benefits:**
- Resizable panes
- Horizontal or vertical split
- Multiple panes
- Simple API

**Use Cases:**
- Compare two images side-by-side
- Compare catalog matches
- Compare analysis results
- Split view for code and results

**Package:** `react-split-pane`

```typescript
import SplitPane from 'react-split-pane';

<SplitPane split="vertical" defaultSize="50%">
  <ImageComparisonView image1={image1} />
  <ImageComparisonView image2={image2} />
</SplitPane>
```

### React Image Compare

**Why:** Slider-based image comparison (before/after, catalog overlay, etc.).

**Benefits:**
- Slider overlay comparison
- Smooth transitions
- Customizable slider
- Works with FITS images (via canvas)

**Use Cases:**
- Compare images with/without catalog overlay
- Compare calibration before/after
- Compare different analysis results

**Package:** `react-image-compare`

---

## Parameter Configuration

### React JSON Schema Form

**Why:** Generate forms from JSON schemas - perfect for analysis parameter configuration.

**Benefits:**
- Schema-driven forms
- Validation built-in
- Custom widgets
- Type-safe parameters
- Deterministic (schema defines parameters)

**Use Cases:**
- Catalog comparison parameters
- Image analysis parameters
- Source finding parameters
- All analysis tool configurations

**Package:** `@rjsf/core`, `@rjsf/mui` (Material-UI theme)

```typescript
import Form from '@rjsf/mui';
import validator from '@rjsf/validator-ajv8';

const schema = {
  type: 'object',
  properties: {
    matchRadius: {
      type: 'number',
      title: 'Match Radius (arcsec)',
      default: 5.0,
      minimum: 1,
      maximum: 30,
    },
    catalog: {
      type: 'string',
      title: 'Catalog',
      enum: ['nvss', 'vlass', 'first'],
    },
  },
};

<Form
  schema={schema}
  validator={validator}
  onSubmit={handleSubmit}
  formData={parameters}
/>
```

### React Hook Form

**Why:** Lightweight form library with excellent performance and validation.

**Benefits:**
- Minimal re-renders
- Built-in validation
- TypeScript support
- Easy integration with Material-UI

**Use Cases:**
- Simple parameter forms
- Quick analysis configuration
- User preferences

**Package:** `react-hook-form`

---

## Workflow Visualization

### React Flow

**Why:** Visualize analysis workflows, data lineage, and analysis pipelines.

**Benefits:**
- Node-based workflow editor
- Custom node types
- Edge connections
- Zoom and pan
- Export to JSON/image

**Use Cases:**
- Visualize analysis workflow
- Show data lineage
- Create custom analysis pipelines
- Document analysis steps

**Package:** `reactflow`

```typescript
import ReactFlow from 'reactflow';

const nodes = [
  { id: '1', data: { label: 'Load Image' }, position: { x: 0, y: 0 } },
  { id: '2', data: { label: 'Source Finding' }, position: { x: 200, y: 0 } },
  { id: '3', data: { label: 'Catalog Comparison' }, position: { x: 400, y: 0 } },
];

const edges = [
  { id: 'e1-2', source: '1', target: '2' },
  { id: 'e2-3', source: '2', target: '3' },
];

<ReactFlow nodes={nodes} edges={edges} />
```

### React D3 Tree

**Why:** Hierarchical visualization of analysis steps, data products, or workflow history.

**Benefits:**
- Tree/hierarchical layouts
- Collapsible nodes
- Custom node rendering
- Good for nested structures

**Use Cases:**
- Analysis step hierarchy
- Data product tree
- Workflow history

**Package:** `react-d3-tree`

---

## Documentation & Notes

### React Markdown

**Why:** Rich text notes, analysis documentation, and reproducible analysis reports.

**Benefits:**
- Markdown rendering
- Code blocks with syntax highlighting
- Math equations (with KaTeX)
- Tables
- Links and images

**Use Cases:**
- Analysis notes
- Documentation panels
- Reproducible analysis reports
- Tooltips and help text

**Package:** `react-markdown`, `remark-math`, `rehype-katex`

```typescript
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

<ReactMarkdown
  remarkPlugins={[remarkMath]}
  rehypePlugins={[rehypeKatex]}
>
  {analysisNotes}
</ReactMarkdown>
```

### Tiptap (Rich Text Editor)

**Why:** WYSIWYG editor for analysis notes and documentation.

**Benefits:**
- Rich text editing
- Collaborative editing (optional)
- Export to Markdown/HTML
- Custom extensions

**Use Cases:**
- Analysis notes editor
- Documentation editor
- Report generation

**Package:** `@tiptap/react`, `@tiptap/starter-kit`

---

## Keyboard Shortcuts

### React Hotkeys Hook

**Why:** Keyboard shortcuts for power users - speed up analysis workflows.

**Benefits:**
- Global and scoped shortcuts
- Key combinations
- Visual shortcut hints
- Conflict detection

**Use Cases:**
- Quick tool switching
- Run analysis (Ctrl+Enter)
- Save workspace (Ctrl+S)
- Export results (Ctrl+E)

**Package:** `react-hotkeys-hook`

```typescript
import { useHotkeys } from 'react-hotkeys-hook';

useHotkeys('ctrl+enter', () => {
  runAnalysis();
}, { scopes: ['analysis'] });

useHotkeys('ctrl+s', (e) => {
  e.preventDefault();
  saveWorkspace();
});
```

---

## State Management & Debugging

### Zustand Devtools (You Already Have Zustand ✓)

**Why:** Debug state transitions, see state history, time-travel debugging.

**Benefits:**
- Redux DevTools integration
- State inspection
- Action history
- Time-travel debugging

**Package:** `zustand/middleware` (devtools middleware)

```typescript
import { devtools } from 'zustand/middleware';

const useStore = create(
  devtools(
    (set) => ({
      // ... store
    }),
    { name: 'AnalysisWorkspace' }
  )
);
```

### React Query Devtools (You Already Have React Query ✓)

**Why:** Debug API calls, cache state, and data fetching.

**Benefits:**
- Query inspection
- Cache visualization
- Refetch controls
- Network tab integration

**Package:** Already included with `@tanstack/react-query`

```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

<ReactQueryDevtools initialIsOpen={false} />
```

---

## File Management

### React Context Menu

**Why:** Right-click menus for data products, tools, and workspace items.

**Benefits:**
- Context-sensitive menus
- Keyboard navigation
- Custom menu items
- Works with Golden Layout

**Use Cases:**
- Right-click on image → "Open in JS9", "Compare with...", "Export"
- Right-click on tool → "Close", "Duplicate", "Save as template"
- Right-click on workspace → "Save", "Export", "Share"

**Package:** `react-contextmenu`

```typescript
import { ContextMenu, MenuItem } from 'react-contextmenu';

<ContextMenu id="image-context-menu">
  <MenuItem onClick={() => openInJS9(image)}>
    Open in JS9
  </MenuItem>
  <MenuItem onClick={() => compareWith(image)}>
    Compare with...
  </MenuItem>
  <MenuItem onClick={() => exportImage(image)}>
    Export
  </MenuItem>
</ContextMenu>
```

### React DnD Kit

**Why:** Drag and drop for organizing workspace, reordering tools, and data product management.

**Benefits:**
- Modern drag and drop
- Touch support
- Accessibility
- Smooth animations
- Works with Golden Layout

**Use Cases:**
- Drag tools between panels
- Reorder analysis steps
- Drag data products into tools
- Organize workspace layout

**Package:** `@dnd-kit/core`, `@dnd-kit/sortable`

---

## Recommendations Summary

### High Priority (Essential)

1. **Monaco Editor** - Code viewing/editing for reproduction scripts
2. **React Split Pane** - Side-by-side comparisons
3. **React JSON Schema Form** - Parameter configuration
4. **React Hotkeys Hook** - Keyboard shortcuts
5. **React Markdown** - Documentation and notes

### Medium Priority (Highly Recommended)

6. **TanStack Table** - Custom table needs beyond AG Grid
7. **React Flow** - Workflow visualization
8. **React Diff Viewer** - Result comparison
9. **React Context Menu** - Right-click menus
10. **@dnd-kit** - Drag and drop

### Low Priority (Nice to Have)

11. **Recharts** - Lightweight plotting alternative
12. **React Image Compare** - Slider-based image comparison
13. **Tiptap** - Rich text editor
14. **React D3 Tree** - Hierarchical visualizations

---

## Integration with Golden Layout

All these tools integrate seamlessly with Golden Layout:

- **Monaco Editor** → Code panel
- **React Split Pane** → Comparison panel
- **React JSON Schema Form** → Parameter configuration panel
- **React Flow** → Workflow visualization panel
- **React Markdown** → Documentation panel
- **TanStack Table** → Data table panel
- **React Diff Viewer** → Comparison panel

Each tool can be a Golden Layout component, allowing users to arrange them as needed.

---

## Example: Complete Analysis Workspace Layout

```typescript
const workspaceLayout = {
  content: [
    {
      type: 'row',
      content: [
        {
          type: 'column',
          width: 30,
          content: [
            { type: 'component', componentName: 'DataBrowser' },
            { type: 'component', componentName: 'ParameterForm' },
          ],
        },
        {
          type: 'column',
          width: 70,
          content: [
            {
              type: 'row',
              height: 50,
              content: [
                { type: 'component', componentName: 'ImageComparison' },
                { type: 'component', componentName: 'CatalogTable' },
              ],
            },
            {
              type: 'row',
              height: 50,
              content: [
                { type: 'component', componentName: 'LightCurvePlot' },
                { type: 'component', componentName: 'ReproductionScript' },
              ],
            },
          ],
        },
      ],
    },
  ],
};
```

---

## Trust & Determinism Integration

All tools support trust and determinism:

- **Monaco Editor** → Shows script version, parameters
- **React JSON Schema Form** → Validates parameters, ensures determinism
- **React Diff Viewer** → Compares results for reproducibility verification
- **React Flow** → Visualizes deterministic workflow
- **React Markdown** → Documents analysis steps for reproducibility

---

**These tools complement Golden Layout perfectly, providing a complete, flexible, trustworthy, and deterministic analysis workspace.**


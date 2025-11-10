# Dashboard Integration Plan - QA Visualization Features

## Overview

The dashboard should be the **primary interaction point** for all pipeline users, providing full access to all QA visualization features that are currently available via Python API, notebooks, and command-line tools.

## Current State

### Existing API Endpoints
- `/api/visualization/browse` - Directory browsing
- `/api/visualization/fits/info` - FITS file metadata
- `/api/visualization/fits/view` - FITS file HTML viewer
- `/api/visualization/casatable/info` - CASA table metadata
- `/api/visualization/casatable/view` - CASA table HTML viewer
- `/api/visualization/notebook/generate` - Generate QA notebooks
- `/api/visualization/notebook/qa` - Run QA and generate notebook
- `/api/visualization/qa/browse` - Browse QA directory

### Missing API Endpoints (Need to Add)

1. **Image File Support**
   - `GET /api/visualization/image/info` - Image metadata
   - `GET /api/visualization/image/view` - Image viewer/thumbnail
   - `GET /api/visualization/image/thumbnail` - Generate/get thumbnail

2. **Text File Support**
   - `GET /api/visualization/text/info` - Text file metadata
   - `GET /api/visualization/text/view` - Text file viewer with line numbers
   - `GET /api/visualization/text/head` - Get first N lines
   - `GET /api/visualization/text/tail` - Get last N lines
   - `GET /api/visualization/text/grep` - Search text file

3. **Enhanced FITS Features**
   - `GET /api/visualization/fits/view` - Add dual-window support
   - `POST /api/visualization/fits/view` - Support scale/colormap parameters

4. **QA Workflow**
   - `POST /api/visualization/qa/run` - Run QA with visualization
   - `GET /api/visualization/qa/status/{qa_id}` - Check QA status
   - `GET /api/visualization/qa/results/{qa_id}` - Get QA results

5. **Settings Management**
   - `GET /api/visualization/settings` - Get current settings
   - `PUT /api/visualization/settings` - Update settings

6. **Thumbnail Management**
   - `GET /api/visualization/thumbnail/{file_path}` - Get thumbnail
   - `POST /api/visualization/thumbnail/generate` - Generate thumbnails

## Dashboard Components Needed

### 1. QA Dashboard Home Page
**Location**: `/ui/qa` or `/ui/dashboard/qa`

**Features**:
- Recent QA runs list
- Quick stats (total runs, pass/fail counts)
- Quick actions:
  - "Run New QA"
  - "Browse QA Directory"
  - "View Recent Reports"

### 2. QA Run Interface
**Location**: `/ui/qa/run`

**Features**:
- Form to configure QA run:
  - MS path input/selector
  - QA root directory
  - Thresholds configuration
  - Options (generate notebook, display summary)
- Real-time progress indicator
- Results display when complete

### 3. File Browser Component
**Location**: `/ui/qa/browse`

**Features**:
- Directory tree navigation
- File list with type icons
- Filter by file type (FITS, images, logs, tables)
- Search/filter functionality
- Click to view files

### 4. FITS Viewer Component
**Location**: `/ui/qa/viewer/fits`

**Features**:
- JS9 integration for FITS viewing
- Dual-window mode toggle
- Scale selector (linear, log, sqrt, etc.)
- Colormap selector
- Header information display
- Download/view options

### 5. Image Viewer Component
**Location**: `/ui/qa/viewer/image`

**Features**:
- Image display with zoom/pan
- Thumbnail grid view
- Full-size view modal
- Image metadata display
- Download option

### 6. Text File Viewer Component
**Location**: `/ui/qa/viewer/text`

**Features**:
- Line-numbered text display
- Head/tail navigation
- Search/grep functionality
- Syntax highlighting (for logs)
- Download option
- Copy to clipboard

### 7. CASA Table Browser Component
**Location**: `/ui/qa/viewer/casatable`

**Features**:
- Table structure display
- Column list with types
- Row count and statistics
- Sample data display (first N rows)
- Subtable navigation
- Column data viewer

### 8. QA Report Viewer
**Location**: `/ui/qa/report/{report_id}`

**Features**:
- Complete QA report display
- Artifact list with thumbnails
- Interactive artifact viewing
- Metrics and statistics
- Export options (PDF, notebook)

### 9. Notebook Viewer/Editor
**Location**: `/ui/qa/notebook/{notebook_id}`

**Features**:
- Embedded Jupyter notebook viewer
- Or custom notebook renderer
- Execute cells (if backend supports)
- Export options

## Implementation Plan

### Phase 1: API Endpoints (Backend)

#### 1.1 Image File Endpoints
```python
@router.get("/image/info")
def get_image_info(path: str):
    """Get image file metadata."""
    img = ImageFile(path)
    return {
        "path": path,
        "exists": img.exists,
        "size": img.size,
        "format": img.format,
        "dimensions": img.dimensions,
    }

@router.get("/image/view")
def view_image(path: str, width: Optional[int] = None):
    """Get image viewer HTML."""
    img = ImageFile(path)
    return HTMLResponse(img.render_html(width=width))

@router.get("/image/thumbnail")
def get_thumbnail(path: str, width: int = 300):
    """Get or generate thumbnail."""
    img = ImageFile(path)
    thumb_html = img.render_thumb(width=width)
    return HTMLResponse(thumb_html)
```

#### 1.2 Text File Endpoints
```python
@router.get("/text/info")
def get_text_info(path: str):
    """Get text file metadata."""
    text = TextFile(path)
    return {
        "path": path,
        "exists": text.exists,
        "size": text.size,
        "line_count": len(text.lines),
    }

@router.get("/text/view")
def view_text(
    path: str,
    head: Optional[int] = None,
    tail: Optional[int] = None,
    grep: Optional[str] = None,
):
    """View text file with optional filtering."""
    text = TextFile(path)
    if grep:
        filtered = text.grep(grep)
    elif head:
        filtered = text.head(head)
    elif tail:
        filtered = text.tail(tail)
    else:
        filtered = text
    
    return HTMLResponse(filtered.render_html())
```

#### 1.3 Enhanced FITS Endpoints
```python
@router.post("/fits/view")
def view_fits_enhanced(
    path: str,
    width: int = 600,
    height: int = 600,
    dual_window: bool = False,
    scale: str = "linear",
    colormap: str = "grey",
):
    """Enhanced FITS viewer with all options."""
    fits = FITSFile(path)
    html = fits._render_js9_html(
        width=width,
        height=height,
        dual_window=dual_window,
        scale=scale,
        colormap=colormap,
    )
    return HTMLResponse(html)
```

#### 1.4 QA Workflow Endpoints
```python
@router.post("/qa/run")
async def run_qa_async(request: QARunRequest):
    """Run QA asynchronously and return job ID."""
    # Queue QA job
    job_id = queue_qa_job(request)
    return {"job_id": job_id, "status": "queued"}

@router.get("/qa/status/{job_id}")
def get_qa_status(job_id: str):
    """Get QA job status."""
    status = get_qa_job_status(job_id)
    return status

@router.get("/qa/results/{job_id}")
def get_qa_results(job_id: str):
    """Get QA results."""
    results = get_qa_job_results(job_id)
    return results
```

### Phase 2: Frontend Components

#### 2.1 Core Components Structure
```
frontend/src/
├── components/
│   ├── qa/
│   │   ├── QADashboard.tsx          # Main QA dashboard
│   │   ├── QARunForm.tsx            # QA run configuration
│   │   ├── QAResults.tsx            # QA results display
│   │   ├── FileBrowser.tsx          # File browser component
│   │   ├── FITSViewer.tsx            # FITS viewer component
│   │   ├── ImageViewer.tsx          # Image viewer component
│   │   ├── TextViewer.tsx           # Text viewer component
│   │   ├── CasaTableViewer.tsx      # CASA table viewer
│   │   └── ThumbnailGrid.tsx        # Thumbnail grid display
│   └── common/
│       ├── Layout.tsx               # Main layout
│       ├── Navigation.tsx           # Navigation bar
│       └── FileTypeIcon.tsx         # File type icons
├── pages/
│   ├── QADashboardPage.tsx           # QA dashboard page
│   ├── QARunPage.tsx                # QA run page
│   ├── FileBrowserPage.tsx           # File browser page
│   └── ViewerPage.tsx                # Generic viewer page
├── api/
│   ├── visualization.ts             # Visualization API client
│   └── qa.ts                        # QA API client
└── hooks/
    ├── useQA.ts                      # QA hooks
    ├── useFileBrowser.ts             # File browser hooks
    └── useViewer.ts                  # Viewer hooks
```

#### 2.2 Key Component Examples

**QADashboard.tsx**
```typescript
export function QADashboard() {
  const { data: recentRuns } = useRecentQARuns();
  const { data: stats } = useQAStats();
  
  return (
    <Layout>
      <h1>QA Dashboard</h1>
      <StatsCards stats={stats} />
      <RecentRunsList runs={recentRuns} />
      <QuickActions>
        <Button href="/qa/run">Run New QA</Button>
        <Button href="/qa/browse">Browse QA Directory</Button>
      </QuickActions>
    </Layout>
  );
}
```

**FileBrowser.tsx**
```typescript
export function FileBrowser({ path }: { path: string }) {
  const { data: listing } = useDirectoryListing(path);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  
  return (
    <div className="file-browser">
      <DirectoryTree path={path} />
      <FileList 
        files={listing.entries}
        onFileClick={setSelectedFile}
      />
      {selectedFile && <FileViewer path={selectedFile} />}
    </div>
  );
}
```

**FITSViewer.tsx**
```typescript
export function FITSViewer({ path }: { path: string }) {
  const [scale, setScale] = useState("linear");
  const [colormap, setColormap] = useState("grey");
  const [dualWindow, setDualWindow] = useState(false);
  
  const { data: html } = useFITSViewer({
    path,
    scale,
    colormap,
    dual_window: dualWindow,
  });
  
  return (
    <div className="fits-viewer">
      <Controls>
        <ScaleSelector value={scale} onChange={setScale} />
        <ColormapSelector value={colormap} onChange={setColormap} />
        <Toggle label="Dual Window" value={dualWindow} onChange={setDualWindow} />
      </Controls>
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
```

### Phase 3: Integration Points

#### 3.1 Dashboard Navigation
Add QA section to main dashboard navigation:
- QA Dashboard
- Run QA
- Browse Files
- View Reports

#### 3.2 Quick Actions
Add QA quick actions to main dashboard:
- "Run QA on Latest MS"
- "View Recent QA Results"
- "Browse QA Directory"

#### 3.3 File Type Handlers
Register file type handlers:
- `.fits` → FITSViewer component
- `.png`, `.jpg`, `.gif` → ImageViewer component
- `.txt`, `.log` → TextViewer component
- `.ms` (directories) → CasaTableViewer component

### Phase 4: User Experience Enhancements

#### 4.1 Thumbnail Generation
- Automatic thumbnail generation for images
- Thumbnail grid view for QA artifacts
- Lazy loading for performance

#### 4.2 Search and Filter
- Search files by name
- Filter by file type
- Filter by date range
- Filter by QA run

#### 4.3 Real-time Updates
- WebSocket support for QA job progress
- Real-time file browser updates
- Live status indicators

#### 4.4 Export Options
- Export QA reports as PDF
- Download notebooks
- Export file lists as CSV
- Share links to specific views

## API Endpoint Summary

### Required New Endpoints

1. **Image Support**
   - `GET /api/visualization/image/info?path={path}`
   - `GET /api/visualization/image/view?path={path}&width={width}`
   - `GET /api/visualization/image/thumbnail?path={path}&width={width}`

2. **Text Support**
   - `GET /api/visualization/text/info?path={path}`
   - `GET /api/visualization/text/view?path={path}&head={n}&tail={n}&grep={pattern}`

3. **Enhanced FITS**
   - `POST /api/visualization/fits/view` (with body for options)

4. **QA Workflow**
   - `POST /api/visualization/qa/run`
   - `GET /api/visualization/qa/status/{job_id}`
   - `GET /api/visualization/qa/results/{job_id}`
   - `GET /api/visualization/qa/list` (recent runs)

5. **Settings**
   - `GET /api/visualization/settings`
   - `PUT /api/visualization/settings`

6. **Thumbnails**
   - `GET /api/visualization/thumbnail?path={path}&width={width}`

## Frontend Component Summary

### Required Components

1. **QA Dashboard** - Main entry point
2. **QA Run Form** - Configure and run QA
3. **File Browser** - Navigate QA directories
4. **FITS Viewer** - Interactive FITS viewing
5. **Image Viewer** - Image display with thumbnails
6. **Text Viewer** - Log/text file viewing
7. **CASA Table Viewer** - MS table browsing
8. **QA Results Display** - Show QA results
9. **Thumbnail Grid** - Grid view of artifacts

## Success Criteria

1. ✅ Users can run QA entirely from dashboard
2. ✅ Users can browse all QA artifacts from dashboard
3. ✅ Users can view all file types (FITS, images, text, tables) in dashboard
4. ✅ Dashboard provides same functionality as notebooks/CLI
5. ✅ Dashboard is faster and more intuitive than alternatives
6. ✅ Dashboard supports all new visualization features

## Next Steps

1. **Immediate**: Add missing API endpoints for image/text support
2. **Short-term**: Build core dashboard components (browser, viewers)
3. **Medium-term**: Integrate QA workflow into dashboard
4. **Long-term**: Add advanced features (real-time updates, export)


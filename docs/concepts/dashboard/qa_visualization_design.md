# In-House QA Visualization Framework Design

**Purpose**: Build RadioPadre-like functionality within `dsa110-contimg` for
interactive QA visualization without external dependencies.

**Goal**: Provide interactive FITS viewing, CASA table browsing, and automated
QA report generation using JS9 and Jupyter notebooks, all implemented in-house.

---

## Architecture Overview

```
dsa110_contimg/qa/visualization/
├── __init__.py              # Main API (similar to radiopadre/__init__.py)
├── fitsfile.py              # FITS file handling + JS9 integration
├── casatable.py             # CASA MS table browsing
├── filelist.py              # File list management
├── datadir.py               # Directory browsing
├── render.py                # HTML rendering utilities
├── notebook.py               # Notebook generation utilities
└── js9/                     # JS9 integration
    ├── __init__.py
    └── js9_setup.py         # JS9 initialization and helpers
```

---

## Core Components

### 1. FITS File Handling (`fitsfile.py`)

**API** (mirrors RadioPadre):

```python
from dsa110_contimg.qa.visualization import FITSFile

fits = FITSFile("image.fits")
fits.show()  # Renders with JS9 viewer
fits.header  # FITS header display
fits.shape   # Image dimensions
```

**Features**:

- FITS header parsing (using `astropy.io.fits`)
- JS9 integration for browser-based viewing
- Thumbnail generation
- Summary information display
- Compatible with our existing `qa/image_quality.py`

**Dependencies**: `astropy` (already have), JS9 JavaScript library

---

### 2. CASA Table Browsing (`casatable.py`)

**API** (mirrors RadioPadre):

```python
from dsa110_contimg.qa.visualization import CasaTable

ms = CasaTable("data.ms")
ms.show()        # Shows table summary
ms[0:100].show() # Shows first 100 rows
ms.columns      # List available columns
```

**Features**:

- Browse Measurement Sets as tables
- Column access with slicing
- Flag handling
- Summary statistics
- Integration with `python-casacore` (already have)

**Dependencies**: `python-casacore` (already have)

---

### 3. Directory Browsing (`datadir.py`, `filelist.py`)

**API** (mirrors RadioPadre):

```python
from dsa110_contimg.qa.visualization import ls

qa_dir = ls("state/qa")
qa_dir.show()           # Renders as HTML table
fits_files = qa_dir.fits # Filter FITS files
images = qa_dir.images   # Filter image files
```

**Features**:

- Intelligent file type detection
- Pattern-based filtering (`include`, `exclude`)
- Recursive directory scanning
- List-like interface: `dd[0]`, `dd[5:10]`, etc.
- Automatic grouping (FITS, images, tables, dirs)

**Dependencies**: None (pure Python)

---

### 4. HTML Rendering (`render.py`)

**API** (mirrors RadioPadre):

```python
from dsa110_contimg.qa.visualization import render_table, render_status_message

render_table(data, headers)
render_status_message("Status text")
```

**Features**:

- Table rendering
- Status messages
- Error rendering
- Rich string formatting
- Compatible with Jupyter/IPython display

**Dependencies**: None (pure Python HTML generation)

---

### 5. Notebook Generation (`notebook.py`)

**API**:

```python
from dsa110_contimg.qa.visualization import generate_qa_notebook

notebook_path = generate_qa_notebook(
    ms_path="data.ms",
    qa_root="state/qa",
    artifacts=["image.fits", "plot.png"]
)
```

**Features**:

- Programmatic notebook generation
- RadioPadre-like cell structure
- Integration with our QA functions
- Template-based generation

**Dependencies**: `nbformat` (already have via Jupyter)

---

### 6. JS9 Integration (`js9/`)

**Features**:

- JS9 JavaScript library integration
- Browser-based FITS viewing
- Inline notebook viewing
- Colormap controls
- Region overlays

**Implementation**:

- Bundle JS9 JavaScript files in our package
- Serve via Jupyter static file serving
- Initialize JS9 in notebook cells
- Provide Python API for JS9 operations

**Dependencies**: JS9 JavaScript library (bundled, no npm/node required)

---

## Integration Points

### 1. Enhance `qa/casa_ms_qa.py`

```python
from dsa110_contimg.qa.visualization import CasaTable, generate_qa_notebook

def run_ms_qa_with_visualization(ms_path: str, qa_root: str) -> QaResult:
    result = run_ms_qa(ms_path, qa_root)  # Existing

    # Generate interactive notebook
    notebook_path = generate_qa_notebook(ms_path, qa_root, result.artifacts)
    result.artifacts.append(notebook_path)

    return result
```

### 2. Enhance `qa/image_quality.py`

```python
from dsa110_contimg.qa.visualization import FITSFile

def inspect_image(image_path: str):
    """Inspect image using JS9 viewer."""
    fits = FITSFile(image_path)
    fits.show()  # Opens JS9 viewer in notebook
```

### 3. New Module: `qa/visualization/__init__.py`

```python
"""
QA Visualization Framework

Provides RadioPadre-like functionality for interactive QA visualization:
- FITS file viewing with JS9
- CASA table browsing
- Directory browsing and file discovery
- Notebook generation
"""

from .fitsfile import FITSFile
from .casatable import CasaTable
from .filelist import FileList
from .datadir import DataDir, ls
from .render import render_table, render_status_message
from .notebook import generate_qa_notebook

__all__ = [
    'FITSFile',
    'CasaTable',
    'FileList',
    'DataDir',
    'ls',
    'render_table',
    'render_status_message',
    'generate_qa_notebook',
]
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

1. **Create module structure**
   - `src/dsa110_contimg/qa/visualization/`
   - Basic `__init__.py`
   - `render.py` (HTML utilities)

2. **File List & Directory Browsing**
   - `filelist.py` - File list management
   - `datadir.py` - Directory browsing
   - Test with `state/qa/` directory

3. **HTML Rendering**
   - `render.py` - Table, status, error rendering
   - Compatible with Jupyter/IPython display

### Phase 2: FITS & CASA Support (Week 2)

4. **FITS File Handling**
   - `fitsfile.py` - FITS header parsing, summary
   - Basic JS9 integration setup
   - Thumbnail generation

5. **CASA Table Browsing**
   - `casatable.py` - MS table interface
   - Column access, slicing
   - Summary statistics

### Phase 3: JS9 Integration (Week 2-3)

6. **JS9 Setup**
   - `js9/` module
   - Bundle JS9 JavaScript files
   - Initialize JS9 in notebooks
   - FITS file viewing API

### Phase 4: Notebook Generation (Week 3)

7. **Notebook Utilities**
   - `notebook.py` - Programmatic notebook generation
   - Template-based QA reports
   - Integration with QA functions

### Phase 5: Integration & Testing (Week 4)

8. **Integration**
   - Enhance `qa/casa_ms_qa.py`
   - Enhance `qa/image_quality.py`
   - Create QA notebook templates

9. **Testing**
   - Test with real pipeline outputs
   - Test remote access scenarios
   - Performance testing

---

## Key Design Decisions

### 1. **JS9 Library Handling**

**Option A**: Bundle JS9 files in our package

- Pros: No external dependencies, works offline
- Cons: Need to update JS9 manually
- **Decision**: Bundle JS9 files in `qa/visualization/js9/static/`

**Option B**: CDN link to JS9

- Pros: Always latest version
- Cons: Requires internet, potential CDN issues
- **Decision**: Use bundled version, allow CDN fallback

### 2. **Notebook vs. Standalone HTML**

**Decision**: Support both

- Notebooks for interactive QA (primary)
- HTML reports for static sharing (existing functionality)

### 3. **API Compatibility**

**Decision**: Mirror RadioPadre API closely

- Same method names (`show()`, `ls()`, etc.)
- Same class structure
- Easier migration if needed later
- Familiar API for users

### 4. **Dependencies**

**Decision**: Use only existing dependencies

- `astropy` - FITS handling ✅
- `python-casacore` - CASA tables ✅
- `nbformat` - Notebook generation ✅
- `IPython` - Display utilities ✅
- JS9 JavaScript - Bundle in package

---

## File Structure

```
src/dsa110_contimg/qa/visualization/
├── __init__.py
├── fitsfile.py
├── casatable.py
├── filelist.py
├── datadir.py
├── render.py
├── notebook.py
└── js9/
    ├── __init__.py
    ├── js9_setup.py
    └── static/
        ├── js9/
        │   ├── js9.js
        │   ├── js9.css
        │   └── ... (JS9 files)
        └── js9_prefs.js
```

---

## Testing Strategy

1. **Unit Tests**: Each module independently
2. **Integration Tests**: Full QA workflow
3. **Notebook Tests**: Generated notebooks execute correctly
4. **JS9 Tests**: FITS viewing works in notebooks

---

## Documentation

1. **API Documentation**: Docstrings for all public APIs
2. **Usage Examples**: Notebook templates
3. **Integration Guide**: How to use in QA functions
4. **JS9 Setup Guide**: How JS9 integration works

---

## Next Steps

1. Create module structure
2. Implement `render.py` (foundation)
3. Implement `filelist.py` and `datadir.py`
4. Implement `fitsfile.py` with basic JS9
5. Implement `casatable.py`
6. Complete JS9 integration
7. Implement notebook generation
8. Integrate with existing QA functions

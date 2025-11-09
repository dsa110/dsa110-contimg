# QA Visualization Framework - User Guide

## Where Features Are Accessible

The QA visualization framework is accessible through multiple import paths:

### 1. **Via Main QA Module** (Recommended for most users)

```python
from dsa110_contimg.qa import (
    FITSFile,           # View FITS files with JS9
    CasaTable,          # Browse CASA Measurement Sets
    ls,                 # List and browse directories
    generate_qa_notebook,  # Generate QA notebooks
    run_ms_qa_with_visualization,  # Enhanced QA with auto-notebook
)
```

**Location**: `dsa110_contimg/qa/__init__.py`

### 2. **Direct from Visualization Module** (Full API access)

```python
from dsa110_contimg.qa.visualization import (
    # Core classes
    FITSFile,
    CasaTable,
    FileList,
    DataDir,
    ls,
    
    # Rendering utilities
    render_table,
    render_status_message,
    render_error,
    
    # Notebook generation
    generate_qa_notebook,
    generate_fits_viewer_notebook,
    generate_ms_explorer_notebook,
    
    # QA integration
    browse_qa_outputs,
    display_qa_summary,
    generate_qa_notebook_from_result,
)
```

**Location**: `dsa110_contimg/qa/visualization/__init__.py`

### 3. **Enhanced QA Functions**

```python
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization
```

**Location**: `dsa110_contimg/qa/visualization_qa.py`

## Usage Contexts

### In Jupyter Notebooks (Primary Use Case)

```python
# Initialize JS9 for FITS viewing
from dsa110_contimg.qa import FITSFile, ls, init_js9

init_js9()

# Browse QA outputs
qa_dir = ls("state/qa")
qa_dir.show()

# View FITS files interactively
for fits_file in qa_dir.fits:
    fits_file.show()  # Opens JS9 viewer
```

### In Python Scripts

```python
#!/usr/bin/env python3
from dsa110_contimg.qa import run_ms_qa_with_visualization

result = run_ms_qa_with_visualization(
    ms_path="data.ms",
    qa_root="state/qa",
    generate_notebook=True
)
print(f"Notebook: {result.artifacts[-1]}")
```

### In Interactive Python Sessions

```python
>>> from dsa110_contimg.qa import CasaTable, ls
>>> ms = CasaTable("data.ms")
>>> ms.show()
>>> qa_dir = ls("state/qa")
>>> qa_dir.fits.show()
```

## Module Locations

All visualization code is located in:

```
src/dsa110_contimg/qa/visualization/
├── __init__.py          # Main API (exports everything)
├── file.py              # Base file class
├── filelist.py          # File list management
├── datadir.py           # Directory browsing
├── fitsfile.py          # FITS file handling
├── casatable.py         # CASA table browsing
├── render.py            # HTML rendering
├── notebook.py          # Notebook generation
├── integration.py       # QA integration functions
└── js9/                 # JS9 integration
    └── __init__.py

src/dsa110_contimg/qa/
├── visualization_qa.py  # Enhanced QA wrapper
└── __init__.py          # Exports core visualization features
```

## Feature Availability

| Feature | Import Path | Use Case |
|---------|-------------|----------|
| **FITS viewing** | `from dsa110_contimg.qa import FITSFile` | View FITS files with JS9 |
| **MS browsing** | `from dsa110_contimg.qa import CasaTable` | Browse CASA tables |
| **Directory browsing** | `from dsa110_contimg.qa import ls` | List and filter files |
| **Notebook generation** | `from dsa110_contimg.qa import generate_qa_notebook` | Create QA notebooks |
| **Enhanced QA** | `from dsa110_contimg.qa import run_ms_qa_with_visualization` | Run QA with auto-notebook |
| **QA integration** | `from dsa110_contimg.qa.visualization import browse_qa_outputs` | Browse QA outputs |

## Requirements

- **Python**: 3.11 (in `casa6` conda environment)
- **Jupyter**: Required for interactive features
- **Dependencies**: 
  - `astropy` (FITS files)
  - `casacore.tables` (CASA tables)
  - `nbformat` (notebook generation)
  - `IPython` (Jupyter display)

## Quick Reference

### Most Common Imports

```python
# For interactive QA exploration
from dsa110_contimg.qa import FITSFile, CasaTable, ls, init_js9

# For notebook generation
from dsa110_contimg.qa import generate_qa_notebook

# For enhanced QA workflow
from dsa110_contimg.qa import run_ms_qa_with_visualization
```

### Most Common Operations

```python
# Browse directory
qa_dir = ls("state/qa")
qa_dir.show()

# View FITS file
fits = FITSFile("image.fits")
fits.show()

# Browse MS
ms = CasaTable("data.ms")
ms.show()

# Generate notebook
notebook = generate_qa_notebook(ms_path="data.ms", qa_root="state/qa")
```

## Documentation

- **Quick Start**: `docs/QA_VISUALIZATION_QUICK_START.md`
- **Usage Guide**: `docs/QA_VISUALIZATION_USAGE.md`
- **Access Guide**: `docs/QA_VISUALIZATION_ACCESS.md`
- **Implementation Status**: `docs/QA_VISUALIZATION_IMPLEMENTATION_STATUS.md`


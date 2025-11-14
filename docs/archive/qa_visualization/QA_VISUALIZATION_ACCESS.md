# QA Visualization Framework - Access Guide

This document explains where and how users can access the QA visualization features.

## Access Points

### 1. Direct Import (Recommended)

The visualization framework is accessible via direct import from the `qa.visualization` module:

```python
# Full visualization framework
from dsa110_contimg.qa.visualization import (
    FITSFile,
    CasaTable,
    ls,
    generate_qa_notebook,
    browse_qa_outputs,
    display_qa_summary,
)

# Enhanced QA function with visualization
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization
```

### 2. Via Main QA Module

Core visualization features are also exported from the main `qa` module:

```python
from dsa110_contimg.qa import (
    FITSFile,
    CasaTable,
    ls,
    generate_qa_notebook,
    run_ms_qa_with_visualization,
)
```

### 3. In Jupyter Notebooks

The framework is designed for use in Jupyter notebooks:

```python
# In a Jupyter notebook cell
from dsa110_contimg.qa.visualization import FITSFile, ls, init_js9

# Initialize JS9 for FITS viewing
init_js9()

# Browse QA directory
qa_dir = ls("state/qa")
qa_dir.show()

# View FITS files
for fits_file in qa_dir.fits:
    fits_file.show()
```

### 4. Programmatic Usage in Python Scripts

```python
#!/usr/bin/env python3
"""Example script using QA visualization."""

from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization

# Run QA with automatic notebook generation
result = run_ms_qa_with_visualization(
    ms_path="data.ms",
    qa_root="state/qa",
    generate_notebook=True
)

print(f"Notebook generated: {result.artifacts[-1]}")
```

## Module Structure

```
dsa110_contimg.qa.visualization/
├── __init__.py          # Main API exports
├── file.py              # Base file class
├── filelist.py          # File list management
├── datadir.py           # Directory browsing (ls)
├── fitsfile.py          # FITS file handling
├── casatable.py         # CASA table browsing
├── render.py            # HTML rendering utilities
├── notebook.py          # Notebook generation
├── integration.py       # QA integration functions
└── js9/                 # JS9 integration
    └── __init__.py

dsa110_contimg.qa/
├── visualization_qa.py  # Enhanced QA wrapper
└── __init__.py          # Exports core visualization features
```

## Common Usage Patterns

### Pattern 1: Browse QA Outputs

```python
from dsa110_contimg.qa.visualization import ls, browse_qa_outputs

# Quick browse
browse_qa_outputs("state/qa/my_ms")

# Or use ls() directly
qa_dir = ls("state/qa")
qa_dir.show()
```

### Pattern 2: View FITS Files

```python
from dsa110_contimg.qa.visualization import FITSFile, init_js9

init_js9()
fits = FITSFile("image.fits")
fits.show()  # Opens JS9 viewer
```

### Pattern 3: Explore Measurement Sets

```python
from dsa110_contimg.qa.visualization import CasaTable

ms = CasaTable("data.ms")
ms.show()  # Display table summary
data = ms.DATA[0:100]  # Access columns
```

### Pattern 4: Generate QA Notebooks

```python
from dsa110_contimg.qa.visualization import generate_qa_notebook

notebook = generate_qa_notebook(
    ms_path="data.ms",
    qa_root="state/qa",
    artifacts=["image.fits"],
    output_path="qa_report.ipynb"
)
```

### Pattern 5: Enhanced QA with Visualization

```python
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization

result = run_ms_qa_with_visualization(
    ms_path="data.ms",
    qa_root="state/qa",
    generate_notebook=True,
    display_summary=True
)
```

## Import Paths Summary

| Feature | Import Path |
|---------|-------------|
| Core visualization | `from dsa110_contimg.qa.visualization import ...` |
| Enhanced QA | `from dsa110_contimg.qa.visualization_qa import ...` |
| Via main QA module | `from dsa110_contimg.qa import FITSFile, CasaTable, ls` |

## Environment Requirements

- **Python**: 3.11 (in `casa6` conda environment)
- **Jupyter**: Required for interactive features (JS9, notebook display)
- **Dependencies**: 
  - `astropy` (for FITS files)
  - `casacore.tables` (for CASA tables)
  - `nbformat` (for notebook generation)
  - `IPython` (for Jupyter display)

## CLI Access

Currently, visualization features are Python API only. For CLI access, use:

```bash
# Run QA (notebook generation can be added programmatically)
python -m dsa110_contimg.qa.run_ms_qa --ms data.ms --qa-root state/qa

# Then use Python to generate notebook
python -c "
from dsa110_contimg.qa.casa_ms_qa import run_ms_qa
from dsa110_contimg.qa.visualization import generate_qa_notebook_from_result
result = run_ms_qa('data.ms', 'state/qa')
notebook = generate_qa_notebook_from_result(result)
print(f'Notebook: {notebook}')
"
```

## Future Enhancements

Potential future additions:
- CLI commands for notebook generation
- Integration with API endpoints
- Batch notebook generation scripts


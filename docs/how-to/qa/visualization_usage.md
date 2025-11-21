# QA Visualization Framework - Usage Guide

This guide demonstrates how to use the in-house QA visualization framework for
interactive data exploration and QA reporting.

## Quick Start

```python
from dsa110_contimg.qa.visualization import (
    FITSFile,
    CasaTable,
    ls,
    init_js9,
    generate_qa_notebook,
)

# Initialize JS9 for FITS viewing
init_js9()

# Browse QA directory
qa_dir = ls("state/qa")
qa_dir.show()

# View FITS files
fits_files = qa_dir.fits
for fits_file in fits_files:
    fits_file.show()  # Opens JS9 viewer
```

## Integration with QA Functions

### Automatic Notebook Generation

```python
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization

# Run QA with automatic notebook generation
result = run_ms_qa_with_visualization(
    ms_path="data.ms",
    qa_root="state/qa",
    generate_notebook=True,
    display_summary=True
)

# Notebook is automatically added to result.artifacts
print(f"Notebook: {result.artifacts[-1]}")
```

### Manual Integration

```python
from dsa110_contimg.qa.casa_ms_qa import run_ms_qa
from dsa110_contimg.qa.visualization import (
    generate_qa_notebook_from_result,
    display_qa_summary,
    browse_qa_outputs,
)

# Run standard QA
result = run_ms_qa("data.ms", "state/qa")

# Generate notebook from result
notebook_path = generate_qa_notebook_from_result(result)

# Display summary
display_qa_summary(result)

# Browse outputs
browse_qa_outputs("state/qa")
```

## Directory Browsing

```python
from dsa110_contimg.qa.visualization import ls

# List directory contents
qa_dir = ls("state/qa")
qa_dir.show()

# Filter files
fits_files = qa_dir.fits
images = qa_dir.images
ms_files = qa_dir.tables

# Pattern filtering
large_fits = qa_dir.include("*.fits").filter(lambda f: f.size > 1000000)
```

## FITS File Viewing

```python
from dsa110_contimg.qa.visualization import FITSFile, init_js9

# Initialize JS9
init_js9()

# View FITS file
fits = FITSFile("image.fits")
fits.show()  # Opens JS9 viewer in notebook

# Access header and metadata
print(fits.header)
print(fits.shape)
print(fits.summary)
```

## CASA Table Browsing

```python
from dsa110_contimg.qa.visualization import CasaTable

# Open Measurement Set
ms = CasaTable("data.ms")
ms.show()  # Display table summary

# Access columns
data = ms.DATA[0:100]  # First 100 rows
flagged_data = ms.DATA_F[0:100]  # With flags applied

# Access subtables
field_table = ms["FIELD"]
antenna_table = ms["ANTENNA"]

# Table properties
print(f"Rows: {ms.nrows:,}")
print(f"Columns: {ms.columns}")
```

## Notebook Generation

### Generate QA Notebook

```python
from dsa110_contimg.qa.visualization import generate_qa_notebook

notebook_path = generate_qa_notebook(
    ms_path="data.ms",
    qa_root="state/qa",
    artifacts=["image.fits", "plot.png"],
    output_path="qa_report.ipynb"
)
```

### Generate FITS Viewer Notebook

```python
from dsa110_contimg.qa.visualization import generate_fits_viewer_notebook

notebook_path = generate_fits_viewer_notebook(
    fits_paths=["image1.fits", "image2.fits"],
    output_path="fits_viewer.ipynb"
)
```

### Generate MS Explorer Notebook

```python
from dsa110_contimg.qa.visualization import generate_ms_explorer_notebook

notebook_path = generate_ms_explorer_notebook(
    ms_path="data.ms",
    output_path="ms_explorer.ipynb"
)
```

## Examples

### Example 1: Quick QA Review

```python
from dsa110_contimg.qa.visualization import ls, FITSFile, init_js9

init_js9()

# Browse QA outputs
qa_dir = ls("state/qa/my_ms")

# View all FITS files
for fits_file in qa_dir.fits:
    fits_file.show()
```

### Example 2: Generate QA Report Notebook

```python
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization

# Run QA and generate notebook
result = run_ms_qa_with_visualization(
    ms_path="data.ms",
    qa_root="state/qa",
    generate_notebook=True
)

print(f"QA complete. Notebook: {result.artifacts[-1]}")
```

### Example 3: Explore MS Structure

```python
from dsa110_contimg.qa.visualization import CasaTable

ms = CasaTable("data.ms")

# Display summary
ms.show()

# Explore subtables
for subtable_name in ms.subtables:
    subtable = ms[subtable_name]
    subtable.show()
```

## API Reference

See `src/dsa110_contimg/qa/visualization/__init__.py` for complete API
documentation.

## Notes

- JS9 requires files to be served via HTTP in Jupyter notebooks
- CASA tables require `casacore.tables` to be available
- FITS files require `astropy.io.fits` to be available
- Notebook generation requires `nbformat` to be available

# QA Visualization Features - User Guide

This guide describes how users interact with the enhanced QA visualization features in the DSA110 pipeline.

## Table of Contents

1. [Entry Points](#entry-points)
2. [Automatic Features](#automatic-features)
3. [Interactive Notebook Usage](#interactive-notebook-usage)
4. [Common Workflows](#common-workflows)
5. [Feature-Specific Examples](#feature-specific-examples)

---

## Entry Points

Users can access QA visualization features through three main entry points:

### 1. Python API (Recommended for Programmatic Use)

#### Option A: Enhanced QA Function with Auto-Generated Notebook

```python
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization

# Run QA and automatically generate interactive notebook
result = run_ms_qa_with_visualization(
    ms_path="data/my_observation.ms",
    qa_root="state/qa/my_observation",
    generate_notebook=True,  # Automatically creates notebook
    display_summary=True      # Shows summary in Jupyter
)

# Notebook is automatically added to result.artifacts
notebook_path = [a for a in result.artifacts if a.endswith('.ipynb')][0]
print(f"Open notebook: {notebook_path}")
```

#### Option B: Standard QA + Manual Notebook Generation

```python
from dsa110_contimg.qa.casa_ms_qa import run_ms_qa
from dsa110_contimg.qa.visualization.integration import (
    generate_qa_notebook_from_result
)

# Run standard QA
result = run_ms_qa(
    ms_path="data/my_observation.ms",
    qa_root="state/qa/my_observation"
)

# Generate notebook from results
notebook_path = generate_qa_notebook_from_result(result)
```

#### Option C: Manual Notebook Generation

```python
from dsa110_contimg.qa.visualization import generate_qa_notebook

# Generate notebook with specific artifacts
notebook_path = generate_qa_notebook(
    ms_path="data/my_observation.ms",
    qa_root="state/qa/my_observation",
    artifacts=["image1.fits", "plot1.png", "log.txt"],
    output_path="my_qa_report.ipynb",
    title="My QA Report"
)
```

### 2. REST API Endpoints

#### Generate QA Notebook via API

```bash
# Run QA and generate notebook in one call
curl -X POST "http://api-server/api/visualization/notebook/qa" \
  -H "Content-Type: application/json" \
  -d '{
    "ms_path": "/data/my_observation.ms",
    "qa_root": "/state/qa/my_observation",
    "output_path": "/state/qa/my_observation/qa_report.ipynb"
  }'

# Or generate notebook from existing artifacts
curl -X POST "http://api-server/api/visualization/notebook/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "ms_path": "/data/my_observation.ms",
    "qa_root": "/state/qa/my_observation",
    "artifacts": ["image.fits", "plot.png"],
    "title": "Custom QA Report"
  }'
```

### 3. Command Line Interface

```bash
# Run QA (notebook generation can be enabled via config)
python -m dsa110_contimg.qa.run_ms_qa \
  --ms-path data/my_observation.ms \
  --qa-root state/qa/my_observation
```

---

## Automatic Features

When QA notebooks are generated, the following features are **automatically** applied:

### 1. **Smart File Type Detection**

The system automatically detects and uses appropriate handlers for different file types:

- **FITS files** → `FITSFile` with JS9 viewer
- **Image files** (PNG, JPG, GIF, SVG) → `ImageFile` with thumbnail support
- **Text/Log files** (TXT, LOG, OUT, ERR) → `TextFile` with grep/head/tail
- **CASA tables** → `CasaTable` with interactive browsing
- **HTML files** → `HTMLFile` with iframe rendering
- **PDF files** → `PDFFile` with thumbnail preview

### 2. **Enhanced Notebook Structure**

Generated notebooks automatically include:

- **Title Section**: Professional title with navigation bookmarks
- **Section Headers**: Organized sections (MS, QA Directory, Artifacts)
- **Import Cells**: All necessary imports pre-configured
- **JS9 Initialization**: FITS viewer ready to use

### 3. **Thumbnail Generation**

Image files automatically get thumbnails generated and cached for faster loading.

---

## Interactive Notebook Usage

Once you open a generated notebook in Jupyter, you can interact with all features:

### Browsing QA Directory

```python
from dsa110_contimg.qa.visualization import ls

# Browse QA output directory
qa_dir = ls("state/qa/my_observation")
qa_dir.show()

# Filter by file type
fits_files = qa_dir.fits
images = qa_dir.images
text_files = qa_dir.others  # Includes logs

# Show filtered results
fits_files.show()
images.show()
```

### Viewing FITS Files

```python
from dsa110_contimg.qa.visualization import FITSFile

# Basic FITS viewing
fits = FITSFile("image.fits")
fits.show()

# Enhanced features: dual-window comparison
fits.show(dual_window=True, width=800, height=600)

# Custom scale and colormap
fits.show(scale="log", colormap="heat")

# Large image handling (automatic segmentation)
fits.show()  # Automatically handles large images
```

### Viewing Images

```python
from dsa110_contimg.qa.visualization import ImageFile

# Display image
img = ImageFile("plot.png")
img.show()

# Show as thumbnail
img.render_thumb(width=300)

# Display multiple images
for img_path in qa_dir.images:
    img = ImageFile(img_path)
    img.show()
```

### Inspecting Log Files

```python
from dsa110_contimg.qa.visualization import TextFile

# Load log file
log = TextFile("calibration.log")

# Show first 50 lines
log.head(50).show()

# Show last 100 lines
log.tail(100).show()

# Search for errors
log.grep("ERROR").show()

# Search with regex
log.grep(r"WARNING|ERROR").show()

# Extract data matching pattern
# Extract timestamps and values
data = log.extract(r"(\d{4}-\d{2}-\d{2}) (\d+\.\d+)", groups=[1, 2])
data.show()
```

### Browsing CASA Tables

```python
from dsa110_contimg.qa.visualization import CasaTable

# Open Measurement Set
ms = CasaTable("data/my_observation.ms")
ms.show()

# Access columns
print(f"Rows: {ms.nrows:,}")
print(f"Columns: {ms.columns}")

# Get column data
data = ms.getcol("DATA", start=0, nrow=100)

# Browse subtables
for subtable_name in ms.subtables:
    subtable = ms[subtable_name]
    subtable.show()
```

### Creating Tables

```python
from dsa110_contimg.qa.visualization import Table, tabulate

# Create table from data
data = [
    ("File", "Size", "Type"),
    ("image1.fits", "10 MB", "FITS"),
    ("plot1.png", "500 KB", "Image"),
]
table = Table(data, headers=["File", "Size", "Type"])
table.show()

# Quick table from list
items = ["Item 1", "Item 2", "Item 3"]
tabulate(items, ncol=3).show()

# Styled table
table.set_style("table", "width", "100%")
table.set_style("tr", "background-color", "#f0f0f0")
table.show()
```

### Using Layouts

```python
from dsa110_contimg.qa.visualization import Title, Section

# Add title with navigation
Title("My QA Report", sections=["Overview", "Plots", "Tables"])

# Add section header
Section("Overview", refreshable=True)

# Content here...

Section("Plots", refreshable=False)
# More content...
```

### Collapsible Sections

```python
from dsa110_contimg.qa.visualization import render_titled_content

# Create collapsible section
html = render_titled_content(
    title="Detailed Analysis",
    content="<p>Detailed content here...</p>",
    collapsible=True,
    default_collapsed=False
)
display(HTML(html))
```

---

## Common Workflows

### Workflow 1: Quick QA Check

```python
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization

# Run QA and get notebook
result = run_ms_qa_with_visualization(
    ms_path="data/obs.ms",
    qa_root="state/qa/obs",
    generate_notebook=True
)

# Open notebook in Jupyter
# All artifacts are automatically displayed with appropriate viewers
```

### Workflow 2: Debugging Calibration Issues

```python
from dsa110_contimg.qa.visualization import ls, TextFile

# Find log files
qa_dir = ls("state/qa/obs")
logs = [f for f in qa_dir if str(f).endswith('.log')]

# Search for errors in all logs
for log_file in logs:
    log = TextFile(log_file)
    errors = log.grep("ERROR")
    if errors:
        print(f"Errors in {log_file}:")
        errors.show()
```

### Workflow 3: Comparing Multiple Images

```python
from dsa110_contimg.qa.visualization import ImageFile, FITSFile

# Compare two FITS images side-by-side
fits1 = FITSFile("before.fits")
fits1.show(dual_window=True)  # Opens dual-window view

# Or compare images
img1 = ImageFile("plot1.png")
img2 = ImageFile("plot2.png")
img1.show()
img2.show()
```

### Workflow 4: Exploring Large Datasets

```python
from dsa110_contimg.qa.visualization import ls, CasaTable

# Browse directory structure
qa_dir = ls("state/qa", recursive=True)
qa_dir.show()

# Explore MS structure
ms = CasaTable("data/large_observation.ms")
print(f"Rows: {ms.nrows:,}")
print(f"Columns: {len(ms.columns)}")

# Sample data
sample = ms[0:100]  # First 100 rows
sample.show()
```

### Workflow 5: Custom QA Report

```python
from dsa110_contimg.qa.visualization import (
    generate_qa_notebook, Title, Section, Table
)

# Generate custom notebook
notebook_path = generate_qa_notebook(
    ms_path="data/obs.ms",
    qa_root="state/qa/obs",
    artifacts=["custom_plot.png", "analysis.txt"],
    title="Custom Analysis Report"
)

# Open notebook and add custom sections
# In notebook:
Title("Custom Analysis", sections=["Summary", "Details"])
Section("Summary")
# Add custom content...
```

---

## Feature-Specific Examples

### Thumbnail Generation

Thumbnails are automatically generated and cached. To regenerate:

```python
from dsa110_contimg.qa.visualization import ImageFile

img = ImageFile("plot.png")
# Thumbnail is automatically generated on first access
img.render_thumb(width=300, refresh=True)  # Force refresh
```

### Settings Configuration

```python
from dsa110_contimg.qa.visualization import settings

# View current settings
settings.show()

# Temporarily change settings
with settings.fits.scale("log"), settings.fits.colormap("heat"):
    fits.show()  # Uses log scale and heat colormap

# Settings revert after context
fits.show()  # Back to defaults
```

### Parallel Processing

Thumbnail generation and other operations automatically use parallel processing:

```python
from dsa110_contimg.qa.visualization import executor, ncpu

# Check CPU count
print(f"Using {ncpu()} CPUs")

# Generate thumbnails in parallel (automatic)
for img in qa_dir.images:
    img.render_thumb()  # Automatically parallelized
```

### Advanced Table Operations

```python
from dsa110_contimg.qa.visualization import Table

# Create table
table = Table([
    ("A", "B", "C"),
    (1, 2, 3),
    (4, 5, 6),
    (7, 8, 9),
], headers=["Col1", "Col2", "Col3"])

# Slice table
table[0:2, 1:3].show()  # Rows 0-1, Columns 1-2

# Style table
table.set_style("table", "font-size", "12px")
table.set_style("th", "background-color", "#333")
table.set_style("th", "color", "white")
table.show()
```

---

## Tips and Best Practices

1. **Notebook Generation**: Use `run_ms_qa_with_visualization()` for automatic notebook generation
2. **Large Files**: FITS files are automatically segmented for large images
3. **Caching**: Thumbnails are cached - delete `.radiopadre/` directory to regenerate
4. **Performance**: Use `ls()` with filters to avoid loading unnecessary files
5. **Log Analysis**: Use `grep()` and `extract()` for efficient log parsing
6. **Customization**: All features support customization through parameters

---

## Troubleshooting

### Thumbnails Not Showing

```python
# Clear cache and regenerate
import shutil
from pathlib import Path
cache_dir = Path(".radiopadre")
if cache_dir.exists():
    shutil.rmtree(cache_dir)
```

### JS9 Not Loading

```python
from dsa110_contimg.qa.visualization import init_js9
init_js9()  # Reinitialize JS9
```

### Large Notebooks Loading Slowly

- Thumbnails are automatically used for images
- Use `head()` and `tail()` for large text files
- FITS files are automatically segmented

---

For more details, see the API documentation or explore the generated notebooks!


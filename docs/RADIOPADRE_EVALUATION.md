# RadioPadre Evaluation for dsa110-contimg

**Date**: 2025-11-12  
**Tool**: RadioPadre v1.2.0  
**Repository**: `/data/dsa110-contimg/archive/references/radiopadre`

---

## Executive Summary

RadioPadre is a Jupyter notebook framework specifically designed for radio astronomy data visualization and pipeline result examination. It provides **browser-based FITS viewing via JS9 and CARTA**, automated report generation, and intelligent file browsing - all optimized for remote cluster workflows.

**Key Finding**: RadioPadre could significantly enhance our QA workflow by providing:
1. **Interactive FITS viewing** without downloading files
2. **Automated QA report generation** from structured pipeline outputs
3. **Remote-friendly visualization** over slow SSH connections
4. **CASA table browsing** capabilities

**Recommendation**: **High value integration** - Implement RadioPadre notebooks for QA visualization and reporting.

---

## 1. What RadioPadre Is

### 1.1 Core Concept

RadioPadre is a **custom Jupyter kernel** that extends standard Jupyter notebooks with:
- Radio astronomy-specific file type detection (FITS, CASA MS, images, tables)
- JS9 integration for browser-based FITS viewing
- CARTA integration for remote FITS viewing
- Intelligent directory browsing with filtering
- Automated report generation from structured outputs

### 1.2 Use Cases (from RadioPadre README)

1. **Just browsing**: Interactively exploring 500+ pipeline output files
2. **Automated reporting**: Custom notebooks that generate reports from structured outputs
3. **Sharing notebooks**: Create shareable reports with explanatory text and visualizations

### 1.3 Architecture

```
Jupyter Notebook
    ↓
RadioPadre Kernel (custom)
    ↓
File Type Detection → FITSFile, CasaTable, ImageFile, etc.
    ↓
JS9/CARTA Integration → Browser-based FITS viewing
```

**Key Components**:
- `radiopadre/` - Core library (file types, rendering)
- `radiopadre_kernel/` - Custom Jupyter kernel
- `radiopadre_utils/` - Notebook utilities
- JS9 integration via `radiopadre_kernel/js9/`

---

## 2. Key Features Relevant to dsa110-contimg

### 2.1 FITS File Handling (`radiopadre/fitsfile.py`)

**Capabilities**:
- Automatic FITS header parsing and display
- JS9 integration for browser-based viewing
- Thumbnail generation
- Summary information (size, resolution, axes)
- CARTA integration for remote viewing

**Example Usage**:
```python
import radiopadre
fits = radiopadre.FITSFile("image.fits")
fits.show()  # Renders with JS9 button
```

**Relevance**: Our pipeline produces many FITS images (`.pbcor.fits`, `.image.fits`). RadioPadre would allow QA inspection without downloading files.

### 2.2 CASA Table Browsing (`radiopadre/casatable.py`)

**Capabilities**:
- Browse Measurement Sets as tables
- Column access with slicing: `ms[5:10]` gets rows 5-9
- Flag handling
- Summary statistics
- Integration with `python-casacore`

**Example Usage**:
```python
ms = radiopadre.CasaTable("data.ms")
ms.show()  # Shows table summary
ms[0:100].show()  # Shows first 100 rows
```

**Relevance**: Could enhance our MS QA (`qa/casa_ms_qa.py`) with interactive browsing.

### 2.3 Directory Browsing (`radiopadre/datadir.py`, `radiopadre/filelist.py`)

**Capabilities**:
- Intelligent file type detection
- Pattern-based filtering (`include`, `exclude`)
- Recursive directory scanning
- List-like interface: `dd[0]`, `dd[5:10]`, etc.
- Automatic grouping (FITS, images, tables, dirs)

**Example Usage**:
```python
dd = radiopadre.ls("state/qa")  # Directory listing
dd.show()  # Renders as HTML table
fits_files = dd.fits  # Filter FITS files
images = dd.images  # Filter image files
```

**Relevance**: Our QA outputs are structured (`state/qa/`, `products/`). RadioPadre could automatically discover and display them.

### 2.4 JS9 Integration (`radiopadre_kernel/js9/`)

**Capabilities**:
- Browser-based FITS viewing (no download needed)
- Inline viewing in notebook cells
- New tab viewing
- Colormap controls
- Region overlays
- CARTA integration (remote viewing)

**Relevance**: Critical for remote QA workflows. Currently, we generate static PNG thumbnails (`qa/fast_plots.py`). JS9 would allow interactive inspection.

### 2.5 Automated Report Generation

**Capabilities**:
- Notebook templates that scan directory structures
- Pattern-based file discovery
- Automatic rendering of discovered files
- Markdown cells for explanations

**Example Pattern**:
```python
# Scan QA directory
qa_dir = radiopadre.ls("state/qa")
# Filter by pattern
calibration_plots = qa_dir.fits.filter("calibration")
# Render automatically
calibration_plots.show()
```

**Relevance**: Could replace/enhance our current QA report generation with interactive notebooks.

---

## 3. Current dsa110-contimg QA Capabilities

### 3.1 What We Have

**File**: `qa/fast_plots.py`
- Matplotlib-based static plots
- PNG/PDF output
- Amplitude vs time/frequency
- UV coverage plots
- Phase plots

**File**: `qa/plotting.py`
- CASA `plotms` wrapper (headless)
- Virtual display support
- Multiple output formats

**File**: `qa/casa_ms_qa.py`
- MS quality checks
- Text-based reports
- HTML report generation

**File**: `qa/image_quality.py`
- Image quality metrics
- Beam analysis
- Noise estimation

### 3.2 Gaps RadioPadre Could Fill

1. **Interactive FITS viewing**: Currently static PNGs only
2. **Remote-friendly**: Large FITS files must be downloaded
3. **Automated discovery**: Manual file path specification
4. **CASA table browsing**: No interactive MS browsing
5. **Report generation**: Static HTML reports, not interactive notebooks

---

## 4. Integration Strategy

### 4.1 Option A: Library Integration (Recommended)

**Approach**: Use RadioPadre as a dependency for QA visualization

**Implementation**:
1. Add RadioPadre to `requirements.txt` or `environment.yml`
2. Create QA notebook templates in `notebooks/qa/`
3. Integrate RadioPadre calls into QA functions
4. Generate notebooks automatically from pipeline outputs

**Pros**:
- Full RadioPadre capabilities
- JS9/CARTA integration
- Minimal code changes
- Leverages existing RadioPadre features

**Cons**:
- Additional dependency
- Requires Jupyter setup
- May need `radiopadre-client` for full functionality

**Code Changes**:
```python
# In qa/casa_ms_qa.py or new qa/radiopadre_reports.py
import radiopadre

def generate_qa_notebook(qa_root: str, ms_path: str) -> str:
    """Generate RadioPadre notebook for QA inspection."""
    notebook_path = f"{qa_root}/qa_report.ipynb"
    
    # Create notebook with RadioPadre cells
    # - Directory listing of QA artifacts
    # - FITS file viewing with JS9
    # - MS table browsing
    # - Plot display
    
    return notebook_path
```

### 4.2 Option B: Algorithm Borrowing

**Approach**: Extract specific patterns/algorithms without full RadioPadre dependency

**Implementation**:
1. Borrow JS9 integration patterns
2. Extract file type detection logic
3. Adapt directory browsing patterns
4. Implement simplified version

**Pros**:
- No external dependency
- Customized to our needs
- Lighter weight

**Cons**:
- Significant development effort
- Lose JS9/CARTA integration benefits
- Maintenance burden

**Not Recommended**: RadioPadre's value is in JS9/CARTA integration, which is hard to replicate.

### 4.3 Option C: Tool Repurposing

**Approach**: Adapt RadioPadre notebooks for our pipeline structure

**Implementation**:
1. Create RadioPadre notebook templates
2. Configure for our directory structure
3. Customize file patterns for our outputs
4. Integrate with pipeline QA stages

**Pros**:
- Leverages RadioPadre's strengths
- Customized for our workflow
- Minimal code changes

**Cons**:
- Requires RadioPadre installation
- Notebook-based workflow (may not fit all use cases)

**Recommended**: Combine with Option A

---

## 5. Specific Integration Points

### 5.1 QA Report Generation

**Current**: `qa/casa_ms_qa.py::run_ms_qa()` generates HTML reports

**Enhancement**: Generate RadioPadre notebooks instead of/in addition to HTML

```python
def generate_radiopadre_qa_notebook(
    ms_path: str,
    qa_root: str,
    artifacts: List[str],
) -> str:
    """Generate RadioPadre notebook for interactive QA."""
    import nbformat
    
    # Create notebook with:
    # 1. Directory listing of QA artifacts
    # 2. FITS image viewing (JS9)
    # 3. MS table browsing
    # 4. Plot display
    # 5. Quality metrics summary
    
    notebook_path = f"{qa_root}/qa_interactive.ipynb"
    # ... notebook generation code ...
    return notebook_path
```

### 5.2 Image Quality Inspection

**Current**: `qa/image_quality.py` generates metrics, `qa/fast_plots.py` generates static plots

**Enhancement**: Add RadioPadre FITS viewing

```python
def inspect_image_with_radiopadre(image_path: str):
    """Inspect image using RadioPadre JS9 viewer."""
    import radiopadre
    fits = radiopadre.FITSFile(image_path)
    fits.show()  # Opens JS9 viewer in notebook
```

### 5.3 MS Quality Inspection

**Current**: `qa/casa_ms_qa.py` generates text reports

**Enhancement**: Add RadioPadre MS browsing

```python
def browse_ms_with_radiopadre(ms_path: str):
    """Browse MS using RadioPadre table interface."""
    import radiopadre
    ms = radiopadre.CasaTable(ms_path)
    ms.show()  # Shows table summary
    ms[0:100].show()  # Browse first 100 rows
```

### 5.4 Automated QA Reports

**Enhancement**: Create notebook templates that automatically discover QA artifacts

```python
# notebooks/qa/auto_qa_report.ipynb template
import radiopadre

# Auto-discover QA artifacts
qa_dir = radiopadre.ls("state/qa")
ms_dir = radiopadre.ls("state/qa/*.ms")

# Display FITS images
fits_images = qa_dir.fits
fits_images.show()

# Display plots
plots = qa_dir.images.filter("*.png")
plots.show()

# Browse MS if present
if ms_dir:
    ms = radiopadre.CasaTable(ms_dir[0])
    ms.show()
```

---

## 6. Technical Compatibility

### 6.1 Dependencies

**RadioPadre Requirements** (from `requirements.txt`):
- APLpy
- astropy ✅ (we have)
- bokeh
- ipython ✅ (we have)
- jupyter ✅ (we have)
- matplotlib ✅ (we have)
- python-casacore ✅ (we have)
- pillow ✅ (we have)
- jupyter-contrib-nbextensions
- nodeenv
- click ✅ (we have)

**Compatibility**: Most dependencies already present. Need to add:
- APLpy (optional, for advanced plotting)
- bokeh (optional, for interactive plots)
- jupyter-contrib-nbextensions
- nodeenv (for JS9 helper)

### 6.2 Python Version

- RadioPadre: Python 3.7+
- dsa110-contimg: Python 3.11 (in `casa6` conda environment, defined in `env/environment.yml` and `ops/docker/environment.yml`) ✅ **Compatible**

### 6.3 License

- RadioPadre: MIT License ✅ **Compatible**

### 6.4 CASA Compatibility

- RadioPadre uses `python-casacore` ✅ **Compatible**
- RadioPadre's `CasaTable` works with CASA MS files ✅ **Compatible**

---

## 7. Implementation Plan

### Phase 1: Proof of Concept (1-2 weeks)

1. **Install RadioPadre** in test environment
   ```bash
   pip install radiopadre
   # Or from source:
   cd archive/references/radiopadre
   pip install -e .
   ```

2. **Create test notebook** for QA visualization
   - Test FITS file viewing
   - Test MS table browsing
   - Test directory browsing

3. **Evaluate JS9 integration**
   - Test browser-based FITS viewing
   - Test remote access
   - Test performance

### Phase 2: Integration (2-3 weeks)

1. **Add RadioPadre to dependencies**
   - Update `requirements.txt` or `environment.yml`
   - Document installation

2. **Create QA notebook templates**
   - `notebooks/qa/ms_qa_template.ipynb`
   - `notebooks/qa/image_qa_template.ipynb`
   - `notebooks/qa/pipeline_qa_template.ipynb`

3. **Integrate with QA functions**
   - Add RadioPadre notebook generation to `qa/casa_ms_qa.py`
   - Add RadioPadre FITS viewing to `qa/image_quality.py`
   - Add RadioPadre MS browsing to `qa/casa_ms_qa.py`

4. **Update API** (optional)
   - Add endpoint to generate QA notebooks
   - Serve notebooks via Jupyter

### Phase 3: Production (1-2 weeks)

1. **Documentation**
   - Update QA documentation
   - Create RadioPadre usage guide
   - Add examples

2. **Testing**
   - Test with real pipeline outputs
   - Test remote access scenarios
   - Performance testing

3. **Deployment**
   - Update Docker images (if used)
   - Update systemd services (if needed)
   - Update CI/CD (if applicable)

---

## 8. Benefits Assessment

### 8.1 Immediate Benefits

1. **Interactive FITS viewing**: No need to download large FITS files
2. **Remote-friendly**: Works over slow SSH connections
3. **Automated discovery**: Automatically finds QA artifacts
4. **Better UX**: Interactive notebooks vs static HTML

### 8.2 Long-term Benefits

1. **Collaboration**: Shareable notebooks with explanations
2. **Documentation**: Notebooks serve as living documentation
3. **Reproducibility**: Notebooks capture QA workflow
4. **Extensibility**: Easy to add new QA visualizations

### 8.3 Risks

1. **Dependency management**: Additional package to maintain
2. **Jupyter requirement**: Requires Jupyter setup
3. **Learning curve**: Team needs to learn RadioPadre
4. **Performance**: JS9 may be slower than local viewers (but better than downloading)

---

## 9. Comparison with Current Approach

| Feature | Current (dsa110-contimg) | With RadioPadre |
|---------|-------------------------|-----------------|
| FITS viewing | Static PNG thumbnails | Interactive JS9 viewer |
| MS browsing | Text reports | Interactive table browsing |
| Remote access | Download files | Browser-based viewing |
| Report generation | Static HTML | Interactive notebooks |
| File discovery | Manual paths | Automatic pattern matching |
| Collaboration | Share HTML files | Share notebooks |
| Extensibility | Code changes needed | Notebook editing |

---

## 10. Recommendations

### 10.1 Primary Recommendation

**Implement RadioPadre integration for QA visualization** with the following approach:

1. **Start with QA reports**: Generate RadioPadre notebooks alongside HTML reports
2. **Focus on FITS viewing**: Leverage JS9 integration for image inspection
3. **Add MS browsing**: Use CasaTable for interactive MS inspection
4. **Create templates**: Develop reusable notebook templates for common QA tasks

### 10.2 Implementation Priority

1. **High Priority**: FITS image viewing with JS9
2. **Medium Priority**: MS table browsing
3. **Low Priority**: Automated report generation (can enhance later)

### 10.3 Integration Points

1. **`qa/casa_ms_qa.py`**: Add RadioPadre notebook generation
2. **`qa/image_quality.py`**: Add RadioPadre FITS viewing
3. **`qa/fast_plots.py`**: Keep as-is (static plots still useful)
4. **New module**: `qa/radiopadre_reports.py` for notebook generation

---

## 11. Code Examples

### 11.1 Basic QA Notebook Template

```python
# notebooks/qa/basic_qa_template.ipynb
import radiopadre

# Discover QA artifacts
qa_dir = radiopadre.ls("state/qa")

# Display directory structure
qa_dir.show()

# View FITS images with JS9
fits_files = qa_dir.fits
fits_files.show()

# View plots
plot_files = qa_dir.images.filter("*.png")
plot_files.show()

# Browse MS if present
ms_files = qa_dir.filter("*.ms")
if ms_files:
    ms = radiopadre.CasaTable(ms_files[0])
    ms.show()
    ms[0:100].show()  # First 100 rows
```

### 11.2 Integration with QA Functions

```python
# In qa/casa_ms_qa.py
def run_ms_qa_with_radiopadre(
    ms_path: str,
    qa_root: str,
    generate_notebook: bool = True,
) -> QaResult:
    """Run MS QA and optionally generate RadioPadre notebook."""
    result = run_ms_qa(ms_path, qa_root)  # Existing function
    
    if generate_notebook:
        notebook_path = generate_radiopadre_notebook(ms_path, qa_root, result)
        result.artifacts.append(notebook_path)
    
    return result

def generate_radiopadre_notebook(
    ms_path: str,
    qa_root: str,
    qa_result: QaResult,
) -> str:
    """Generate RadioPadre notebook for QA inspection."""
    import nbformat
    from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
    
    nb = new_notebook()
    
    # Title cell
    nb.cells.append(new_markdown_cell(f"# QA Report: {ms_path}"))
    
    # Import cell
    nb.cells.append(new_code_cell("import radiopadre"))
    
    # Directory listing
    nb.cells.append(new_markdown_cell("## QA Artifacts"))
    nb.cells.append(new_code_cell(f'qa_dir = radiopadre.ls("{qa_root}")'))
    nb.cells.append(new_code_cell("qa_dir.show()"))
    
    # FITS viewing
    nb.cells.append(new_markdown_cell("## FITS Images"))
    nb.cells.append(new_code_cell('fits = qa_dir.fits\nfits.show()'))
    
    # MS browsing
    nb.cells.append(new_markdown_cell("## Measurement Set"))
    nb.cells.append(new_code_cell(f'ms = radiopadre.CasaTable("{ms_path}")'))
    nb.cells.append(new_code_cell("ms.show()"))
    
    # Save notebook
    notebook_path = f"{qa_root}/qa_interactive.ipynb"
    with open(notebook_path, 'w') as f:
        nbformat.write(nb, f)
    
    return notebook_path
```

---

## 12. Conclusion

RadioPadre offers significant value for dsa110-contimg QA workflows:

1. **Solves real problems**: Remote FITS viewing, interactive MS browsing
2. **Good fit**: Designed for radio astronomy pipelines
3. **Compatible**: Works with our stack (CASA, Python, Jupyter)
4. **Low risk**: MIT license, active development, well-documented

**Recommendation**: **Proceed with Phase 1 proof of concept** to evaluate JS9 integration and notebook generation in our environment.

**Next Steps**:
1. Install RadioPadre in test environment
2. Create test notebook with our QA outputs
3. Evaluate JS9 performance and usability
4. Decide on full integration based on results

---

## Appendix: RadioPadre File Structure

```
radiopadre/
├── __init__.py          # Main API
├── fitsfile.py          # FITS file handling + JS9
├── casatable.py         # CASA MS table browsing
├── imagefile.py         # Image file handling
├── filelist.py         # File list management
├── datadir.py          # Directory browsing
├── render.py            # HTML rendering
├── notebook.py          # Notebook utilities
└── executor.py          # Parallel execution

radiopadre_kernel/
├── __init__.py          # Kernel initialization
└── js9/                 # JS9 integration
    └── __init__.py      # JS9 setup

radiopadre_utils/
└── notebook_utils.py     # Notebook helper functions
```


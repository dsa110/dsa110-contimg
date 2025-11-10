# QA Visualization Framework - Implementation Status

**Goal**: Build RadioPadre-like functionality in-house within `dsa110-contimg/src/dsa110_contimg/qa/visualization/`

**Status**: Phase 1 - Foundation (In Progress)

---

## ✅ Completed

### Module Structure
- Created `src/dsa110_contimg/qa/visualization/` directory
- Created `__init__.py` with exports for implemented modules
- Created `js9/static/` directory for JS9 files

### Core Components

1. **`render.py`** ✅
   - HTML rendering utilities
   - `render_table()` - Table rendering
   - `render_status_message()` - Status messages
   - `render_error()` - Error messages
   - `render_preamble()` - HTML preamble
   - `rich_string()` - Styled content wrapper
   - `display_html()` - Jupyter display helper
   - Compatible with Jupyter/IPython display

2. **`file.py`** ✅
   - Base `FileBase` class
   - File metadata handling (size, mtime, etc.)
   - Path utilities
   - File type detection (`autodetect_file_type()`)
   - Sorting utilities
   - File update detection

3. **`filelist.py`** ✅
   - `FileList` class (extends `FileBase` and `list`)
   - File filtering and grouping
   - Properties: `.fits`, `.images`, `.dirs`, `.tables`, `.others`
   - Pattern-based filtering (`include()`, `exclude()`)
   - HTML rendering of file lists
   - Human-readable size formatting
   - List-like interface with slicing support

4. **`datadir.py`** ✅
   - `DataDir` class (extends `FileList`)
   - Directory scanning (recursive and non-recursive)
   - Pattern-based filtering (`include`, `exclude`, `include_dir`, `exclude_dir`)
   - Hidden file handling
   - Empty directory filtering
   - `ls()` convenience function
   - Rescan capability

5. **`fitsfile.py`** ✅
   - `FITSFile` class (extends `FileBase`)
   - FITS header parsing using `astropy.io.fits`
   - Image dimensions and metadata extraction
   - Summary information (size, resolution, axes)
   - JS9 integration for browser-based viewing
   - Automatic JS9 initialization
   - CDN fallback if local JS9 files not available

6. **`js9/`** ✅
   - JS9 initialization module
   - Automatic CDN fallback
   - Local file support (when JS9 files are bundled)
   - Integration with FITSFile

7. **`casatable.py`** ✅
   - `CasaTable` class (extends `FileBase`)
   - CASA MS table browsing using `casacore.tables`
   - Column access with slicing support
   - Flag handling (FLAG_ROW, FLAG columns)
   - Subtable access
   - Table summary and sample row display
   - Column proxy objects for easy access
   - Context manager for table locking

8. **`notebook.py`** ✅
   - `generate_qa_notebook()` - Generate comprehensive QA notebooks
   - `generate_fits_viewer_notebook()` - Generate FITS viewer notebooks
   - `generate_ms_explorer_notebook()` - Generate MS explorer notebooks
   - `add_cell_to_notebook()` - Add cells to existing notebooks
   - Programmatic notebook generation using `nbformat`
   - Integration with visualization framework
   - Template-based cell generation

9. **`integration.py`** ✅
   - `generate_qa_notebook_from_result()` - Generate notebook from QaResult
   - `browse_qa_outputs()` - Interactive QA directory browsing
   - `display_qa_summary()` - Formatted QA result display
   - `enhance_qa_with_notebook()` - Enhance QaResult with notebook
   - `create_qa_explorer_notebook()` - Create explorer notebook for QA directory

10. **`visualization_qa.py`** ✅
    - `run_ms_qa_with_visualization()` - Enhanced QA function with automatic notebook generation
    - Wrapper around `run_ms_qa()` with visualization support
    - Optional notebook generation and summary display

---

## 🚧 In Progress

### Next Components to Implement

3. **`filelist.py`** (Next)
   - `FileList` class (list-like container for files)
   - File filtering and grouping
   - HTML rendering of file lists
   - Properties: `.fits`, `.images`, `.dirs`, `.tables`

4. **`datadir.py`** (After filelist.py)
   - `DataDir` class (extends FileList)
   - Directory scanning
   - Pattern-based filtering (`include`, `exclude`)
   - Recursive directory support
   - `ls()` function (convenience wrapper)

5. **`fitsfile.py`** (After datadir.py)
   - `FITSFile` class (extends FileBase)
   - FITS header parsing (using `astropy.io.fits`)
   - JS9 integration for browser viewing
   - Thumbnail generation
   - Summary information

6. **`casatable.py`** (After fitsfile.py)
   - `CasaTable` class (extends FileBase)
   - CASA MS table browsing
   - Column access with slicing
   - Flag handling
   - Summary statistics

7. **`js9/`** (Parallel with fitsfile.py)
   - JS9 JavaScript library integration
   - `js9_setup.py` - JS9 initialization
   - Bundle JS9 static files
   - Notebook integration

8. **`notebook.py`** (After core components)
   - `generate_qa_notebook()` function
   - Programmatic notebook generation
   - Template-based QA reports
   - Integration with QA functions

---

## 📋 Implementation Order

### Phase 1: Foundation ✅ (Complete)
1. ✅ Module structure
2. ✅ `render.py` - HTML utilities
3. ✅ `file.py` - Base file class
4. ✅ `filelist.py` - File list management
5. ✅ `datadir.py` - Directory browsing

### Phase 2: File Type Support ✅ (Complete)
6. ✅ `fitsfile.py` - FITS file handling
7. ✅ `casatable.py` - CASA table browsing
8. ✅ `js9/` - JS9 integration

### Phase 3: Notebook Generation ✅ (Complete)
9. ✅ `notebook.py` - Notebook utilities
10. ✅ Integration with QA functions

### Phase 4: Testing & Documentation
11. ⏳ Unit tests
12. ⏳ Integration tests
13. ⏳ Documentation
14. ⏳ Examples

---

## 🎯 API Design Goals

### Target API (mirrors RadioPadre)

```python
from dsa110_contimg.qa.visualization import FITSFile, CasaTable, ls

# FITS viewing
fits = FITSFile("image.fits")
fits.show()  # JS9 viewer

# CASA table browsing
ms = CasaTable("data.ms")
ms.show()
ms[0:100].show()

# Directory browsing
qa_dir = ls("state/qa")
qa_dir.show()
fits_files = qa_dir.fits
fits_files.show()
```

---

## 📝 Notes

- **Dependencies**: Using only existing dependencies (`astropy`, `python-casacore`, `nbformat`, `IPython`)
- **JS9**: Will bundle JS9 JavaScript files in `js9/static/`
- **API Compatibility**: Mirroring RadioPadre API closely for familiarity
- **Code Style**: Following `dsa110-contimg` conventions

---

## 🔄 Next Steps

1. Implement `filelist.py` - File list management
2. Implement `datadir.py` - Directory browsing
3. Test directory browsing with `state/qa/`
4. Implement `fitsfile.py` with basic JS9
5. Implement `casatable.py`
6. Complete JS9 integration
7. Implement notebook generation
8. Integrate with existing QA functions

---

## 📚 Reference

- Design document: `docs/QA_VISUALIZATION_DESIGN.md`
- RadioPadre reference: `archive/references/radiopadre/`


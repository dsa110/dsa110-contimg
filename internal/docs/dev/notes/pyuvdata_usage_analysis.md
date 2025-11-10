# pyuvdata Usage Analysis in DSA110-contimg Pipeline

**Date:** 2025-11-06  
**Analysis:** Extent of pyuvdata dependency in default production workflow

---

## Executive Summary

**In the default production workflow, pyuvdata is used for both reading UVH5 files AND writing MS files.**

The production pipeline uses the `parallel-subband` writer which:
1. **Reads UVH5 files** using `pyuvdata.UVData.read()`
2. **Writes MS files** using `pyuvdata.UVData.write_ms()` (per subband)
3. **Concatenates** subband MS files using CASA concat

**This means the TIME format issue from pyuvdata.write_ms() affects production MS files.**

---

## 1. Default Workflow Writer Selection

### Production Default: `parallel-subband`

**Location:** `conversion/strategies/hdf5_orchestrator.py`

```python
writer: str = "parallel-subband"  # Default parameter
```

**Auto-selection logic:**
```python
if writer == "auto":
    # Production processing always uses 16 subbands
    if n_sb <= 2:
        selected_writer = "pyuvdata"  # Testing only
    else:
        selected_writer = "parallel-subband"  # Production
```

**Conclusion:** Production (16 subbands) → `parallel-subband` writer  
Testing (≤2 subbands) → `pyuvdata` writer

---

## 2. Writer Implementations

### A. `parallel-subband` Writer (Production Default)

**Location:** `conversion/strategies/direct_subband.py`

**Key Characteristics:**
- **Uses pyuvdata.write_ms()** for each subband MS file
- Uses `pyuvdata.UVData.read()` to read UVH5 files
- Processes data in memory (phasing, UVW calculation)
- Writes per-subband MS files using `pyuvdata.write_ms()`
- Concatenates subband MS files using CASA concat

**Code Flow:**
1. Read UVH5 files using `pyuvdata.UVData.read()` (for data access)
2. Process data in memory (phasing, UVW calculation)
3. **Write MS files using `uv.write_ms()`** ← TIME format issue source
4. Concatenate subband MS files using CASA concat

**pyuvdata Usage:**
- ✅ **Reading:** Uses `pyuvdata.UVData.read()` to load UVH5 data
- ✅ **Writing:** Uses `pyuvdata.write_ms()` for each subband
- ✅ **Utilities:** Uses `pyuvdata.utils` for coordinate calculations (UVW, phasing)

### B. `pyuvdata` Writer (Testing Only)

**Location:** `conversion/strategies/pyuvdata_monolithic.py`

**Key Characteristics:**
- **Uses pyuvdata.write_ms()** for MS file writing
- Only used for testing scenarios (≤2 subbands)
- Not used in production workflow

**Code Flow:**
1. Read UVH5 files using `pyuvdata.UVData.read()`
2. Process data in memory
3. **Write MS using `uv.write_ms()`** ← This is where TIME format issue originates

**pyuvdata Usage:**
- ✅ **Reading:** Uses `pyuvdata.UVData.read()`
- ✅ **Writing:** Uses `pyuvdata.write_ms()` ← **TIME format issue source**
- ✅ **Utilities:** Uses `pyuvdata.utils`

---

## 3. pyuvdata Dependency Breakdown

### Core Dependencies (Always Used)

1. **UVH5 File Reading**
   - **Function:** `pyuvdata.UVData.read(file_type='uvh5')`
   - **Usage:** All writers use this to read input UVH5 files
   - **Location:** `direct_subband.py`, `pyuvdata_monolithic.py`, `hdf5_orchestrator.py`
   - **Critical:** Yes - UVH5 is the input format

2. **Coordinate Utilities**
   - **Functions:** `pyuvdata.utils.calc_uvw()`, `pyuvdata.utils.calc_app_coords()`
   - **Usage:** UVW vector calculation, coordinate transformations
   - **Location:** `conversion/helpers_coordinates.py`
   - **Critical:** Yes - Required for proper phasing and UVW calculation

### Conditional Dependencies (Testing Only)

3. **MS File Writing**
   - **Function:** `pyuvdata.UVData.write_ms()`
   - **Usage:** Only in `pyuvdata` writer (testing scenarios)
   - **Location:** `conversion/strategies/pyuvdata_monolithic.py`
   - **Critical:** No - Production uses custom casacore writer
   - **Issue:** This is where TIME format inconsistency originates

---

## 4. Production Workflow Analysis

### Default Production Path

```
UVH5 Files (16 subbands)
    ↓
hdf5_orchestrator.py
    ↓
Writer Selection: "parallel-subband" (default)
    ↓
direct_subband.py
    ↓
For each subband:
    1. pyuvdata.UVData.read() ← Read UVH5
    2. Process data (phasing, UVW)
    3. pyuvdata.write_ms() ← Write MS (TIME format issue source)
    ↓
Concatenate subband MS files (CASA concat)
    ↓
Final multi-SPW MS file
```

### Key Points

1. **pyuvdata.read()** is used for reading UVH5 files (required)
2. **pyuvdata.write_ms()** IS used in production (per subband)
3. **TIME format** in production MS files comes from pyuvdata.write_ms()
4. **Format detection** via `extract_ms_time_range()` handles the MJD 0 format

---

## 5. TIME Format Issue Context

### Where TIME Format Issues Originate

**Source: pyuvdata.write_ms() (Both Production and Testing)**
- **Location:** 
  - Production: `direct_subband.py` → `_write_ms_subband_part()` → `uv.write_ms()`
  - Testing: `pyuvdata_monolithic.py` → `uv.write_ms()`
- **Issue:** Writes TIME as seconds since MJD 0 (not CASA standard MJD 51544.0)
- **Impact:** **Both production and testing workflows**

**Root Cause:**
- `pyuvdata.write_ms()` converts from JD (Julian Date) to seconds
- JD = MJD + 2400000.5, so: `TIME = (JD - 2400000.5) * 86400.0 = MJD * 86400.0`
- This results in seconds since MJD 0, not seconds since MJD 51544.0 (CASA standard)

**Solution:**
- `extract_ms_time_range()` with format detection handles both formats
- All code now uses standardized time extraction

---

## 6. Dependency Summary

### Critical Dependencies (Cannot Remove)

| Component | Usage | Critical |
|-----------|-------|----------|
| `pyuvdata.UVData.read()` | Read UVH5 files | ✅ Yes |
| `pyuvdata.utils.calc_uvw()` | UVW calculation | ✅ Yes |
| `pyuvdata.utils.calc_app_coords()` | Coordinate transforms | ✅ Yes |

### Production Dependencies

| Component | Usage | Critical |
|-----------|-------|----------|
| `pyuvdata.UVData.write_ms()` | Write MS files (per subband) | ✅ Yes (production) |

---

## 7. Recommendations

### Current Status

✅ **Production workflow IS dependent on pyuvdata.write_ms()**  
✅ **TIME format handling is standardized via `extract_ms_time_range()`**  
✅ **Format detection handles pyuvdata's MJD 0 format correctly**

### Actions

1. **✅ Completed: Standardized Time Extraction**
   - All code now uses `extract_ms_time_range()`
   - Format detection handles both MJD 0 and MJD 51544.0 formats
   - Works correctly with pyuvdata.write_ms() output

2. **✅ Completed: Updated All Time Access**
   - Replaced all `_ms_time_range()` implementations
   - Fixed API routes to use standardized extraction
   - Updated streaming converter

3. **Documentation:**
   - Document that production uses pyuvdata.write_ms()
   - Note that TIME format is MJD 0 (not CASA standard)
   - Explain TIME format detection strategy

---

## 8. Conclusion

**Extent of pyuvdata Reliance in Default Workflow:**

- **Reading:** ✅ **Critical** - Required for UVH5 input
- **Utilities:** ✅ **Critical** - Required for coordinate calculations
- **Writing:** ✅ **Critical** - Production uses pyuvdata.write_ms() per subband

**Production Workflow:**
- Uses `parallel-subband` writer (default)
- Reads UVH5 with pyuvdata.UVData.read()
- Writes MS with pyuvdata.write_ms() (per subband)
- Concatenates with CASA concat
- **TIME format:** MJD 0 (from pyuvdata.write_ms())

**Testing Workflow:**
- Uses `pyuvdata` writer (≤2 subbands only)
- Reads UVH5 with pyuvdata
- Writes MS with pyuvdata.write_ms()
- **TIME format:** MJD 0 (same as production)

**Overall Assessment:**
The production pipeline has **significant reliance on pyuvdata**, using it for reading UVH5 files, coordinate utilities, AND writing MS files. The TIME format issue from pyuvdata.write_ms() affects both production and testing workflows. The standardized `extract_ms_time_range()` function with format detection handles this correctly.


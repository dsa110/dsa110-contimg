# Alternative RFI Flagging Methods

**Date:** 2025-11-05  
**Question:** Are there more efficient RFI flagging methods, either within CASA or external tools?

---

## Current Implementation

**Available methods:**

1. **CASA (default):** `flagdata` with two-stage approach:
   - **Stage 1:** `tfcrop` (time/frequency polynomial fitting)
   - **Stage 2:** `rflag` (residual-based flagging)
   - **Performance:** Adequate for calibrators, but not optimized for speed or large datasets.

2. **AOFlagger (implemented):** SumThreshold algorithm via Docker or native installation
   - **Status:** ✓ Fully integrated into pipeline CLI
   - **Performance:** Typically 2-5x faster than CASA tfcrop
   - **Usage:** `--rfi-backend aoflagger` flag
   - **See:** `docs/aoflagger/README.md` for details

---

## Alternative Methods

### 1. **AOFlagger (✓ IMPLEMENTED)**

**Status:** ✓ **Fully integrated into pipeline CLI** (as of 2025-11-05)

**Overview:**
- Specialized RFI flagging software used by LOFAR, MWA, Apertif
- Uses **SumThreshold algorithm** (more efficient than polynomial fitting)
- Can read/write CASA Measurement Sets

**Advantages:**
- **Faster:** SumThreshold is computationally more efficient than tfcrop
- **Better for wideband:** Optimized for large frequency ranges
- **Proven at scale:** Used by major observatories
- **Open source:** https://gitlab.com/aoflagger/aoflagger
- **Docker support:** Works on Ubuntu 18.x via Docker container

**Implementation:**
- Integrated in `src/dsa110_contimg/calibration/flagging.py`
- CLI option: `--rfi-backend aoflagger`
- Auto-detects Docker or native installation
- Supports custom Lua strategy files

**Usage via Pipeline:**
```bash
# Use AOFlagger for RFI flagging
python -m dsa110_contimg.calibration.cli flag \
  --ms /path/to/ms.ms \
  --mode rfi \
  --rfi-backend aoflagger \
  --aoflagger-strategy /path/to/custom-strategy.lua  # optional

# Or use Docker explicitly
python -m dsa110_contimg.calibration.cli flag \
  --ms /path/to/ms.ms \
  --mode rfi \
  --rfi-backend aoflagger \
  --aoflagger-path docker
```

**Documentation:**
- Strategy files: `docs/aoflagger/dsa110-default.lua`
- Setup guide: `docs/aoflagger/README.md`
- Parameter optimization: `docs/aoflagger/PARAMETER_OPTIMIZATION_GUIDE.md`

**Performance:** Typically 2-5x faster than CASA tfcrop for large datasets.

---

### 2. **PyUVData Flagging (Python Library)**

**Overview:**
- PyUVData has built-in RFI flagging capabilities
- Uses similar algorithms to CASA but with Python flexibility
- Can work with UVH5 format (before MS conversion)

**Advantages:**
- **Already in pipeline:** PyUVData is already used for conversion
- **Python-native:** Easy to integrate and customize
- **UVH5 support:** Can flag before MS conversion (earlier in pipeline)

**Disadvantages:**
- **Less mature:** Flagging algorithms less tested than CASA
- **Performance:** May be slower than CASA (pure Python)
- **Format limitation:** Primarily designed for UVH5, not MS

**Current Status in Codebase:**
- PyUVData is used for UVH5→MS conversion (`helpers_coordinates.py`)
- **Not currently used for flagging** - could be added

**Usage:**
```python
from pyuvdata import UVData
import pyuvdata.utils as uvutils

uv = UVData()
uv.read_uvh5(input_file)

# Flag RFI
uv.flag_freqs(freq_inds=[0, 1, 2])  # Manual flagging
# Or use external RFI detection algorithms
```

---

### 3. **Machine Learning Approaches**

**Overview:**
- Deep learning models (CNNs) for RFI detection
- Can achieve 35% higher F1-score than traditional methods
- Transfer learning from simulated data

**Advantages:**
- **High accuracy:** Better detection of complex RFI patterns
- **Adaptive:** Learns site-specific RFI characteristics
- **Fast inference:** Once trained, can flag very quickly

**Disadvantages:**
- **Training required:** Needs labeled training data
- **Site-specific:** Models need retraining for different locations
- **Infrastructure:** Requires ML framework (TensorFlow/PyTorch)
- **Not production-ready:** Still research-level

**Research References:**
- R-Net model: 35% higher F1-score vs traditional methods
- Transfer learning: 67% → 91% AUC improvement

**Status:** Research-level, not yet integrated into standard pipelines.

---

### 4. **CASA Alternative Modes**

**Within CASA, there are other `flagdata` modes that may be more efficient:**

#### a. **`sumthreshold` mode (if available)**
```python
flagdata(vis=ms, mode='sumthreshold', threshold=4.0)
```
- More efficient than tfcrop
- Not available in all CASA versions

#### b. **`extend` mode first (faster)**
```python
# Flag obvious outliers first
flagdata(vis=ms, mode='clip', clipminmax=[0, 100])
# Then extend flags
flagdata(vis=ms, mode='extend', growtime=0.5, growfreq=0.5)
```
- Faster than tfcrop for obvious RFI
- Less sensitive to subtle RFI

#### c. **Parallel flagging**
- CASA flagdata can be run in parallel on multiple MS files
- For large datasets, split into chunks and flag in parallel

---

### 5. **Bayesian RFI Mitigation**

**Overview:**
- Statistical approach using likelihood reweighting
- Efficient for large datasets
- Can reduce computation time

**Advantages:**
- **Theoretical foundation:** Rigorous statistical approach
- **Scalable:** Works well for very large datasets
- **Automated:** Minimal parameter tuning

**Disadvantages:**
- **Research-level:** Not yet in standard tools
- **Implementation complexity:** Requires custom implementation
- **Limited testing:** Less proven than CASA/AOFlagger

**Status:** Active research, not yet integrated into observatory pipelines.

---

## Performance Comparison

| Method | Speed | Accuracy | Integration | Status |
|--------|-------|----------|-------------|--------|
| **CASA tfcrop+rflag** (default) | Baseline | Good | ✓ Native | ✓ Production |
| **AOFlagger** | 2-5x faster | Better | ✓ Fully integrated | ✓ **IMPLEMENTED** |
| **PyUVData** | Slower | Good | ✓ Easy | Experimental |
| **Machine Learning** | Fast (inference) | Best | Complex | Research |
| **Bayesian** | Fast | Good | Complex | Research |
| **CASA sumthreshold** | Faster | Good | ✓ Native | Limited availability |

---

## Recommendations

### For Current Use (DSA-110 Pipeline)

**Option 1: Use AOFlagger (Recommended for large datasets)**
- **Pros:** ✓ Fully integrated, 2-5x faster, better for wideband data
- **Cons:** Requires Docker (or native installation)
- **Action:** Use `--rfi-backend aoflagger` flag when flagging RFI
- **Best for:** Large datasets, wideband observations, time-critical workflows

**Option 2: Use CASA (Default, stable)**
- **Pros:** ✓ Native CASA integration, no external dependencies, standard practice
- **Cons:** Not the fastest, but acceptable for calibrator data
- **Action:** Default behavior, no flags needed
- **Best for:** Small datasets, standard workflows, when Docker unavailable

**Option 3: Optimize Current CASA Usage**
- **Pros:** No new dependencies, better performance
- **Cons:** Limited improvement potential
- **Actions:**
  - Use `mode='extend'` for obvious RFI first
  - Parallel flagging for multiple MS files
  - Adjust parameters based on data characteristics

### For Future Development

1. **Short-term:** ✓ AOFlagger integration complete - monitor performance and user feedback
2. **Medium-term:** Evaluate ML-based flagging for DSA-110 site-specific RFI
3. **Long-term:** Integrate real-time FPGA-based filtering (if hardware available)

---

## Implementation Details: AOFlagger Integration

**✓ AOFlagger is fully implemented.** See:

- **Implementation:** `src/dsa110_contimg/calibration/flagging.py` → `flag_rfi_aoflagger()`
- **CLI integration:** `src/dsa110_contimg/calibration/cli_flag.py`
- **Strategy files:** `docs/aoflagger/dsa110-default.lua`
- **Documentation:** `docs/aoflagger/README.md`

**Key features:**
- Auto-detects Docker or native AOFlagger installation
- Supports custom Lua strategy files via `--aoflagger-strategy`
- Handles Docker permission issues gracefully
- Extends flags after AOFlagger (if enabled)

---

## Summary

**Available methods:**

1. **CASA tfcrop+rflag (default):**
   - ✓ Calibrator data (small datasets)
   - ✓ Standard RFI environments
   - ✓ Production stability
   - ✓ No external dependencies

2. **AOFlagger (✓ IMPLEMENTED):**
   - ✓ Large datasets (many MS files, wideband)
   - ✓ 2-5x faster performance
   - ✓ Better for wideband observations
   - ✓ Fully integrated into pipeline CLI

**Recommendation:**
- **Use AOFlagger** for large datasets or when performance is critical: `--rfi-backend aoflagger`
- **Use CASA** for standard workflows or when Docker unavailable (default)
- **Monitor performance** - if flagging takes >10% of pipeline time, use AOFlagger

---

## References

- **AOFlagger:** https://gitlab.com/aoflagger/aoflagger
- **PyUVData:** https://pyuvdata.readthedocs.io/
- **CASA flagdata:** https://casa.nrao.edu/docs/casa-ref/flagdata-task.html
- **SumThreshold algorithm:** Offringa et al. 2010 (A&A)
- **ML RFI detection:** Various papers (see web search results)


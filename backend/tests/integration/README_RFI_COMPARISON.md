# RFI Backend Comparison Test

**Purpose:** Compare AOFlagger vs CASA tfcrop+rflag for effectiveness and
efficiency

**Test Script:** `test_rfi_backend_comparison.py`

---

## Quick Start

```bash
# Basic test (5-10 minutes)
python test_rfi_backend_comparison.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103

# Full test with calibration (30-60 minutes)
python test_rfi_backend_comparison.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103 \
  --full-pipeline
```

---

## Output

Results saved to: `rfi_comparison_results/test_YYYYMMDD_HHMMSS/`

**Read this file:** `comparison_report.txt`

---

## Documentation

- **Full Guide:**
  `/data/dsa110-contimg/docs/how-to/rfi_backend_comparison_testing.md`
- **Quick Reference:**
  `/data/dsa110-contimg/docs/how-to/RFI_BACKEND_COMPARISON_QUICK_REFERENCE.md`

---

## Expected Results

- **Speed:** AOFlagger 3-5x faster than CASA
- **Flagging:** CASA typically 1-2% more aggressive
- **Calibration Success:** Usually equal

**Recommendation:** Continue using AOFlagger (default) unless CASA demonstrates
better calibration success for your specific data.

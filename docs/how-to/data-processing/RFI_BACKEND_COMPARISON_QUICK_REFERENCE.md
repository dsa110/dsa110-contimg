# RFI Backend Comparison - Quick Reference

**Date:** 2025-11-19  
**Type:** Quick Reference  
**Status:** ✅ Ready

---

## Quick Commands

### Basic Test (Flagging Only, ~5-10 min)

```bash
cd /data/dsa110-contimg

python tests/integration/test_rfi_backend_comparison.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103
```

### Full Test (Flagging + Calibration, ~30-60 min)

```bash
python tests/integration/test_rfi_backend_comparison.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103 \
  --full-pipeline
```

---

## What Gets Compared

| Category                | AOFlagger             | CASA tfcrop+rflag                          |
| ----------------------- | --------------------- | ------------------------------------------ |
| **Speed**               | Typically 2-5x faster | Slower but configurable                    |
| **Flagging %**          | ~14-16% typical       | ~15-17% typical (slightly more aggressive) |
| **Calibration Success** | Usually equal         | Usually equal                              |
| **Implementation**      | C++ (external)        | Python/C++ (CASA)                          |
| **Default**             | ✓ Yes                 | No (alternative)                           |

---

## Output Location

```
/data/dsa110-contimg/tests/integration/rfi_comparison_results/
└── test_YYYYMMDD_HHMMSS/
    ├── comparison_report.txt    ← Read this!
    ├── comparison_results.json  ← Machine-readable
    ├── test_aoflagger.ms/
    └── test_casa.ms/
```

---

## Expected Results (Typical DSA-110 Data)

### Speed

- **AOFlagger:** 40-60 seconds
- **CASA:** 150-250 seconds
- **Winner:** AOFlagger (3-5x faster)

### Flagging Aggressiveness

- **AOFlagger:** 14-16% flagged
- **CASA:** 15-17% flagged
- **Difference:** CASA typically 1-2% more aggressive

### Calibration Success

- Usually **equal** for both backends
- Same SPWs fail (heavily RFI-contaminated)

---

## Decision Rules

### Use AOFlagger (Default) When:

✓ Speed matters (production pipeline)  
✓ Results are comparable to CASA  
✓ No special tuning needed

### Use CASA When:

✓ Need custom flagging parameters  
✓ Better calibration success demonstrated  
✓ Legacy workflow compatibility required

---

## Common Options

```bash
# Custom output directory
--output-dir /stage/my_comparison

# Custom AOFlagger strategy
--aoflagger-strategy /data/dsa110-contimg/config/custom.lua

# Force Docker AOFlagger
--aoflagger-path docker

# Different field/refant
--field 1 --refant 104

# Add notes to report
--notes "Testing after antenna maintenance"
```

---

## Interpreting Report

### Speed Section

```
Execution Time (sec)    45.20    187.40
→ AOFlagger is 4.15x FASTER than CASA
```

**Meaning:** AOFlagger is significantly faster for same data

### Flagging Section

```
Overall Flagging (%)    14.50    15.20
→ CASA flags 0.70% MORE data than AOFlagger
```

**Meaning:** CASA is slightly more aggressive (flags more data)

### Calibration Section

```
Success Rate (%)        81.2     81.2
→ Both backends have EQUAL calibration success rates
```

**Meaning:** Both backends equally effective for calibration

### Winner

```
🏆 WINNER: AOFlagger (1 advantages vs 0)
```

**Meaning:** AOFlagger wins on speed, tie on effectiveness

---

## Troubleshooting

| Issue               | Solution                                                               |
| ------------------- | ---------------------------------------------------------------------- |
| "CASA not found"    | Activate casa6 environment: `conda activate /opt/miniforge/envs/casa6` |
| "Disk space"        | Use `--output-dir /stage/` (more space)                                |
| "Permission denied" | Use `chmod +x tests/integration/test_rfi_backend_comparison.py`        |
| Docker warnings     | Expected, non-fatal (see documentation)                                |

---

## Full Documentation

See: `docs/how-to/rfi_backend_comparison_testing.md`

---

**TL;DR:** Run the basic test, read `comparison_report.txt`, keep using
AOFlagger unless CASA demonstrates better calibration success.

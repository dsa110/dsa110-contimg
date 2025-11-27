# RFI Backend Comparison Testing

**Date:** 2025-11-19  
**Type:** Testing Guide  
**Status:** ✅ Ready

---

## Overview

This guide describes how to compare the **effectiveness** and **efficiency** of
the two RFI flagging backends available in the DSA-110 continuum imaging
pipeline:

1. **AOFlagger** (default) - Fast C++ implementation
2. **CASA tfcrop+rflag** (alternative) - CASA's two-stage algorithm

---

## What Gets Compared

### Efficiency Metrics

- **Execution time** - How long flagging takes
- **Memory usage** - RAM consumption during flagging

### Effectiveness Metrics

- **Overall flagging percentage** - Total data flagged
- **Per-SPW flagging statistics** - Flagging patterns across spectral windows
- **Fully flagged SPWs** - Count of completely flagged SPWs
- **Calibration success rate** - How many SPWs successfully calibrate (optional)
- **Calibration execution time** - Time to complete calibration (optional)

---

## Quick Start

### Basic Flagging Comparison (Fast)

Compares only flagging performance (~5-10 minutes):

```bash
cd /data/dsa110-contimg

python tests/integration/test_rfi_backend_comparison.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103
```

### Full Pipeline Comparison (Comprehensive)

Includes calibration success comparison (~30-60 minutes):

```bash
python tests/integration/test_rfi_backend_comparison.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103 \
  --full-pipeline
```

### Custom Configuration

```bash
python tests/integration/test_rfi_backend_comparison.py \
  /path/to/test.ms \
  --refant 103 \
  --field 0 \
  --aoflagger-path docker \
  --aoflagger-strategy /data/dsa110-contimg/config/dsa110-default.lua \
  --output-dir /stage/comparison_results \
  --notes "Testing after RFI environment changes" \
  --full-pipeline
```

---

## Test Methodology

### Phase 1: AOFlagger Test

1. Create working copy: `test_aoflagger.ms`
2. Reset all flags to baseline
3. Flag zeros (same for both backends)
4. Run AOFlagger RFI flagging with timing
5. Extend flags to adjacent channels/times
6. Collect flagging statistics:
   - Overall flagging percentage
   - Per-SPW flagging percentages
   - Fully flagged SPWs
   - Execution time

### Phase 2: CASA Test

1. Create working copy: `test_casa.ms`
2. Reset all flags to baseline
3. Flag zeros (same for both backends)
4. Run CASA tfcrop RFI flagging with timing
5. Run CASA rflag RFI flagging
6. Extend flags to adjacent channels/times
7. Collect same flagging statistics as AOFlagger

### Phase 3: Calibration Test (Optional)

If `--full-pipeline` is specified:

**For AOFlagger-flagged MS:**

1. Populate MODEL_DATA from catalog
2. Solve delay calibration (K)
3. Solve bandpass calibration (BP)
4. Solve gain calibration (G)
5. Collect calibration statistics:
   - Success/failure status
   - Execution time
   - Failed SPWs
   - Succeeded SPWs

**For CASA-flagged MS:**

1. Repeat same calibration steps
2. Collect same calibration statistics

### Phase 4: Analysis & Reporting

1. Compare execution times (efficiency)
2. Compare flagging percentages (aggressiveness)
3. Compare per-SPW patterns (consistency)
4. Compare calibration success rates (effectiveness)
5. Generate comparison report
6. Determine "winner" based on criteria

---

## Output Files

All output files are saved to the specified output directory (default:
`/data/dsa110-contimg/tests/integration/rfi_comparison_results/`).

### Directory Structure

```
rfi_comparison_results/
└── test_YYYYMMDD_HHMMSS/
    ├── test_aoflagger.ms/          # AOFlagger test MS
    ├── test_casa.ms/                # CASA test MS
    ├── comparison_results.json      # Machine-readable results
    └── comparison_report.txt        # Human-readable report
```

### JSON Results File

Contains complete structured data:

```json
{
  "test_ms": "/stage/test.ms",
  "timestamp": "2025-11-19T10:30:00",
  "aoflagger_flagging": {
    "backend": "aoflagger",
    "total_flagged_fraction": 0.145,
    "execution_time_sec": 45.2,
    "per_spw_flagging": {"0": 0.931, "1": 0.912, ...},
    "fully_flagged_spws": [9, 14, 15]
  },
  "casa_flagging": {
    "backend": "casa",
    "total_flagged_fraction": 0.152,
    "execution_time_sec": 187.4,
    "per_spw_flagging": {"0": 0.945, "1": 0.920, ...},
    "fully_flagged_spws": [9, 14, 15]
  },
  "aoflagger_calibration": { ... },
  "casa_calibration": { ... },
  "notes": "Testing notes"
}
```

### Text Report

Human-readable comparison with sections:

1. **Flagging Performance Comparison**
   - Execution times
   - Overall flagging percentages
   - Speed comparison
   - Aggressiveness comparison

2. **Per-SPW Flagging Comparison**
   - Table showing flagging per SPW for both backends

3. **Calibration Success Comparison** (if `--full-pipeline`)
   - Calibration execution times
   - Success rates
   - Failed SPWs for each backend

4. **Summary**
   - Winner determination
   - Key findings

---

## Example Report Output

```
================================================================================
RFI BACKEND COMPARISON REPORT
================================================================================
Test MS: /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms
Timestamp: 2025-11-19T10:30:00

================================================================================
FLAGGING PERFORMANCE COMPARISON
================================================================================

Metric                                   AOFlagger            CASA tfcrop+rflag
--------------------------------------------------------------------------------
Execution Time (sec)                     45.20                187.40
Overall Flagging (%)                     14.50                15.20
Fully Flagged SPWs                       3                    3

→ AOFlagger is 4.15x FASTER than CASA
→ CASA flags 0.70% MORE data than AOFlagger

================================================================================
PER-SPW FLAGGING COMPARISON
================================================================================

SPW        AOFlagger (%)        CASA (%)             Difference
--------------------------------------------------------------------------------
0          93.10                94.50                +1.40
1          91.20                92.00                +0.80
2          76.50                78.20                +1.70
...

================================================================================
CALIBRATION SUCCESS COMPARISON
================================================================================

Metric                                   AOFlagger            CASA tfcrop+rflag
--------------------------------------------------------------------------------
Execution Time (sec)                     245.60               248.30
Succeeded SPWs                           13                   13
Failed SPWs                              3                    3
Success Rate (%)                         81.2                 81.2

AOFlagger - Failed SPWs: [9, 14, 15]
CASA      - Failed SPWs: [9, 14, 15]

→ Both backends have EQUAL calibration success rates

================================================================================
SUMMARY
================================================================================

✓ AOFlagger is significantly faster
= Both have similar calibration success

🏆 WINNER: AOFlagger (1 advantages vs 0)

================================================================================
END OF REPORT
================================================================================
```

---

## Interpreting Results

### Speed Comparison

- **AOFlagger typically 2-5x faster** than CASA tfcrop+rflag
- Speed advantage increases with larger datasets
- CASA may be slower but more configurable

### Flagging Aggressiveness

- **Similar flagging percentages (±1-2%)** indicate consistent algorithms
- **>5% difference** may indicate one backend is too aggressive or too
  permissive
- Check per-SPW patterns to identify differences

### Calibration Success

- **Same failed SPWs** indicates both backends identify the same bad data
- **Different failed SPWs** indicates one backend is better at preserving good
  data
- Higher success rate = more effective RFI flagging

---

## Decision Criteria

### When to Use AOFlagger (Default)

✓ Speed is important (production pipeline)  
✓ Default strategy works well for your data  
✓ Calibration success rates are similar to CASA  
✓ Docker environment available (Ubuntu 18.x)

### When to Use CASA tfcrop+rflag

✓ Need fine-tuned flagging parameters  
✓ Calibration success rate is better with CASA  
✓ Consistency with legacy CASA workflows required  
✓ AOFlagger not available on your system

---

## Advanced Usage

### Testing Multiple Observations

Create a batch test script:

```bash
#!/bin/bash

MS_LIST=(
  "/stage/obs1.ms"
  "/stage/obs2.ms"
  "/stage/obs3.ms"
)

for ms in "${MS_LIST[@]}"; do
  echo "Testing: $ms"
  python tests/integration/test_rfi_backend_comparison.py \
    "$ms" \
    --refant 103 \
    --full-pipeline \
    --output-dir /stage/batch_comparison
done
```

### Custom AOFlagger Strategy

Test with custom flagging strategy:

```bash
python tests/integration/test_rfi_backend_comparison.py \
  /path/to/test.ms \
  --refant 103 \
  --aoflagger-strategy /path/to/custom_strategy.lua
```

### Extracting Metrics from JSON

```python
import json

with open("comparison_results.json") as f:
    results = json.load(f)

# Speed comparison
ao_time = results["aoflagger_flagging"]["execution_time_sec"]
casa_time = results["casa_flagging"]["execution_time_sec"]
speedup = casa_time / ao_time
print(f"AOFlagger is {speedup:.2f}x faster")

# Calibration success comparison
if results["aoflagger_calibration"]:
    ao_success = len(results["aoflagger_calibration"]["succeeded_spws"])
    casa_success = len(results["casa_calibration"]["succeeded_spws"])
    print(f"AOFlagger: {ao_success} SPWs succeeded")
    print(f"CASA: {casa_success} SPWs succeeded")
```

---

## Troubleshooting

### AOFlagger Docker Permission Issues

**Symptom:** Flag extension fails with permission errors

**Cause:** Docker AOFlagger writes files as root

**Solution:** Non-fatal warning, flags are still applied. This is expected
behavior.

### CASA Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'casatasks'`

**Solution:** Ensure running in `casa6` conda environment:

```bash
conda activate /opt/miniforge/envs/casa6
```

### MS Copy Fails

**Symptom:** Not enough disk space

**Solution:** Specify output directory with sufficient space:

```bash
python test_rfi_backend_comparison.py /path/to/test.ms \
  --output-dir /stage/comparison_results
```

### Calibration Fails for Both Backends

**Symptom:** All SPWs fail calibration

**Possible causes:**

- No catalog sources in field
- Refant is bad for all SPWs
- MS is corrupted

**Solution:** Verify MS is valid and has calibrator sources

---

## Related Documentation

- **[Temporal Flagging System](temporal_flagging_system.md)** - Understanding
  flagging phases
- **[SPW Flagging Process](spw_flagging_process.md)** -
  How flagging works
- **Calibration Workflow** - Full calibration process

---

## Credits

**Implementation:** AI Agent (Claude Sonnet 4.5)  
**Date:** 2025-11-19  
**Purpose:** Enable data-driven backend selection  
**Result:** Automated comparison framework for RFI flagging backends

---

## Summary

This test framework enables **objective, data-driven comparison** of AOFlagger
vs CASA tfcrop+rflag backends. Use it to:

- **Validate default backend choice** for your data characteristics
- **Identify optimal backend** for specific observations
- **Monitor performance** changes over time
- **Demonstrate effectiveness** to collaborators

Run regularly as part of pipeline quality assurance to ensure optimal RFI
flagging configuration.

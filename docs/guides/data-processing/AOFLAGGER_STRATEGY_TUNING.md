# AOFlagger Strategy Tuning Guide

**Date:** 2025-11-19  
**Type:** How-To Guide  
**Status:** ✅ Ready

---

## Overview

AOFlagger's aggressiveness can be tuned by adjusting parameters in its Lua
strategy files. This guide explains the key parameters and provides comparison
between conservative (default) and aggressive strategies.

---

## Available Strategies

### **1. Default Strategy (Conservative)**

**File:** `/data/dsa110-contimg/config/dsa110-default.lua`

**Characteristics:**

- Flags ~4-5% of data (typical)
- Optimized for preserving weak sources
- Fast execution (~4 min for 5GB MS)
- Good for most observations

**Use cases:**

- Standard continuum imaging
- Weak source detection
- Transient searches
- Real-time processing

---

### **2. Aggressive Strategy**

**File:** `/data/dsa110-contimg/config/dsa110-aggressive.lua`

**Characteristics:**

- Flags ~10-15% of data (expected)
- More thorough RFI removal
- Slightly slower (~5 min for 5GB MS, +33% due to extra iteration)
- Comparable to CASA tfcrop+rflag aggressiveness

**Use cases:**

- Extremely contaminated observations
- When calibration fails with default strategy
- High dynamic range imaging requiring cleaner data
- Comparison with CASA flagging

---

## Key Tuning Parameters

### **Aggressiveness Controls**

| Parameter                        | Default | Aggressive | Effect                                                    |
| -------------------------------- | ------- | ---------- | --------------------------------------------------------- |
| `base_threshold`                 | 1.0     | **0.6**    | **Primary control:** Lower = more sensitive RFI detection |
| `transient_threshold_factor`     | 1.0     | **0.7**    | Satellite/transient RFI: Lower = catch more transients    |
| `iteration_count`                | 3       | **4**      | More iterations = more thorough multi-pass flagging       |
| `threshold_timestep_rms` (mid)   | 3.5     | **2.5**    | Bad time samples: Lower = flag more outliers              |
| `threshold_timestep_rms` (final) | 4.0     | **3.0**    | Final outlier rejection: Lower = more aggressive          |
| `threshold_channel_rms`          | 3.0     | **2.5**    | Bad frequency channels: Lower = flag more                 |

### **Parameter Descriptions**

#### **`base_threshold`** (Most Important)

- **Range:** 0.3 - 2.0 (practical range)
- **Default:** 1.0 (balanced)
- **Effect:** Core flagging sensitivity
  - **0.6:** Aggressive (like CASA tfcrop+rflag)
  - **1.0:** Conservative (default, good balance)
  - **1.5:** Very conservative (minimal flagging)

#### **`transient_threshold_factor`**

- **Range:** 0.5 - 1.5
- **Default:** 1.0
- **Effect:** Sensitivity to transient RFI (satellites, aircraft, short-duration
  interference)
  - **0.7:** Aggressive transient detection
  - **1.0:** Standard detection
  - **1.3:** Conservative (may miss weak transients)

#### **`iteration_count`**

- **Range:** 2 - 5
- **Default:** 3
- **Effect:** Number of SumThreshold passes
  - **2:** Fast but less thorough
  - **3:** Good balance (default)
  - **4:** More thorough (aggressive mode)
  - **5:** Very thorough but slower

#### **RMS Thresholds** (`threshold_timestep_rms`, `threshold_channel_rms`)

- **Range:** 2.0 - 5.0 (in standard deviations)
- **Effect:** Statistical outlier rejection
  - **2.5σ:** Aggressive (flag ~1.2% as outliers)
  - **3.0σ:** Moderate (flag ~0.3% as outliers)
  - **3.5σ:** Conservative (flag ~0.05% as outliers)
  - **4.0σ:** Very conservative (flag ~0.006% as outliers)

---

## Performance Comparison

### **Execution Time**

From test on 5.1GB MS (16 SPWs):

| Strategy              | Time               | Relative Speed | Extra Cost           |
| --------------------- | ------------------ | -------------- | -------------------- |
| **Default**           | 235 sec (3.9 min)  | 1.0×           | —                    |
| **Aggressive**        | ~310 sec (5.2 min) | 0.76×          | +33% (4th iteration) |
| **CASA tfcrop+rflag** | 973 sec (16.2 min) | 0.24×          | +314%                |

**Conclusion:** Aggressive AOFlagger still **3× faster** than CASA!

---

## Flagging Comparison

### **Expected Flagging Percentages**

From test observations:

| Strategy              | Overall Flagging | Per-SPW Range | Notes                        |
| --------------------- | ---------------- | ------------- | ---------------------------- |
| **Default**           | 4.5%             | 2-7%          | Conservative, preserves data |
| **Aggressive**        | 10-15% (est.)    | 8-18% (est.)  | Similar to CASA              |
| **CASA tfcrop+rflag** | 13.2%            | 8-17%         | Most aggressive              |

---

## Usage Examples

### **Using Default Strategy**

```bash
# Explicit specification (though this is auto-loaded)
dsa110-contimg flag input.ms \
  --backend aoflagger \
  --aoflagger-strategy /data/dsa110-contimg/config/dsa110-default.lua
```

### **Using Aggressive Strategy**

```bash
# For contaminated observations
dsa110-contimg flag input.ms \
  --backend aoflagger \
  --aoflagger-strategy /data/dsa110-contimg/config/dsa110-aggressive.lua
```

### **Python API**

```python
from dsa110_contimg.calibration import flag_rfi

# Default strategy
flag_rfi(
    ms="input.ms",
    backend="aoflagger",
    datacolumn="DATA"
)

# Aggressive strategy
flag_rfi(
    ms="input.ms",
    backend="aoflagger",
    strategy="/data/dsa110-contimg/config/dsa110-aggressive.lua",
    datacolumn="DATA"
)
```

---

## Testing Strategy Changes

Use the RFI backend comparison test to validate strategy changes:

```bash
cd /data/dsa110-contimg

# Compare default vs aggressive AOFlagger strategies
python tests/integration/test_rfi_backend_comparison.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  --refant 103 \
  --aoflagger-strategy /data/dsa110-contimg/config/dsa110-aggressive.lua
```

---

## Creating Custom Strategies

### **Step 1: Copy Template**

```bash
cp /data/dsa110-contimg/config/dsa110-default.lua \
   /data/dsa110-contimg/config/dsa110-custom.lua
```

### **Step 2: Edit Parameters**

Modify the values in the "DSA-110 specific settings" section:

```lua
-- Custom threshold values
local base_threshold = 0.8  -- Slightly more aggressive
local transient_threshold_factor = 0.9
local iteration_count = 3
```

### **Step 3: Test**

```bash
dsa110-contimg flag test.ms \
  --backend aoflagger \
  --aoflagger-strategy /data/dsa110-contimg/config/dsa110-custom.lua
```

### **Step 4: Validate**

Check flagging statistics:

```bash
# Examine flag percentages
casa --nologger -c "
from casatasks import flagdata
flagdata(vis='test.ms', mode='summary')
"
```

---

## Recommendations

### **When to Use Default Strategy**

✅ **Use for:**

- Standard continuum imaging
- Weak source detection
- Transient searches
- Real-time/rapid processing
- Most observations

### **When to Use Aggressive Strategy**

✅ **Use for:**

- Extremely contaminated observations (nearby RFI sources)
- When calibration fails with default strategy
- High dynamic range imaging
- Observations during high RFI periods
- When CASA-like aggressiveness is needed but speed matters

### **When to Use CASA tfcrop+rflag**

✅ **Use for:**

- Maximum possible RFI removal (regardless of speed)
- Research/validation comparisons
- Extremely difficult calibration cases
- When AOFlagger aggressive mode isn't enough

---

## Advanced Tuning

### **Site-Specific Optimization**

If Owens Valley RFI environment changes:

1. **Monitor flagging percentages** over time
2. **Correlate with calibration success rates**
3. **Adjust `base_threshold`** if needed:
   - Increase if too much data lost (weak sources disappearing)
   - Decrease if calibration failures increase

### **Frequency-Specific Tuning**

For DSA-110's L-band (1.4 GHz):

- **GPS satellites:** Common at ~1575 MHz (above DSA-110 band)
- **Cell phones:** ~1700-2100 MHz (above DSA-110 band)
- **WiFi:** 2.4 GHz (not a concern)
- **L-band specific RFI:** May need custom tuning based on local sources

---

## References

- **AOFlagger Documentation:** https://aoflagger.readthedocs.io/
- **Strategy Files:** `/data/dsa110-contimg/config/`
- **Testing Guide:**
  `/data/dsa110-contimg/docs/how-to/rfi_backend_comparison_testing.md`
- **Parameter Optimization:**
  `/data/dsa110-contimg/docs/how-to/PARAMETER_OPTIMIZATION_GUIDE.md`

---

## See Also

- [RFI Backend Comparison Testing](rfi_backend_comparison_testing.md) - Test
  different strategies
- [Temporal Flagging System](temporal_flagging_system.md) - Three-phase flagging
  system
- [AOFlagger Concepts](../../architecture/science/aoflagger.md) - Strategy file basics

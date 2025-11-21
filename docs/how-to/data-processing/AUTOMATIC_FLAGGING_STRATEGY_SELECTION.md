# Automatic Flagging Strategy Selection

**Date:** 2025-11-19  
**Type:** How-To Guide  
**Status:** ✅ Proposed

---

## Problem Statement

We have two AOFlagger strategies:

- **Default (base=1.0):** 4.5% flagging - fast, conservative
- **Aggressive (base=0.75):** 6% flagging - still fast, more thorough

**Challenge:** How do we automatically detect contaminated observations that
need aggressive flagging?

---

## Approach 1: Pre-Flagging Statistics (Before RFI Flagging)

### **Indicators of Heavy Contamination**

Check these metrics on **unflagged data** before running any RFI flagging:

```python
def assess_contamination(ms: str) -> tuple[str, dict]:
    """
    Assess RFI contamination level before flagging.

    Returns:
        strategy: "default" or "aggressive"
        metrics: dict of diagnostic values
    """
    from casacore import tables
    import numpy as np

    tb = tables.table(ms, ack=False)
    data = tb.getcol('DATA')  # Or 'CORRECTED_DATA'
    tb.close()

    # Calculate metrics
    amplitudes = np.abs(data)

    # 1. High amplitude outliers (potential RFI)
    median_amp = np.median(amplitudes)
    mad = np.median(np.abs(amplitudes - median_amp))
    outlier_threshold = median_amp + 10 * mad
    outlier_fraction = (amplitudes > outlier_threshold).mean()

    # 2. Visibility amplitude variance
    amp_std = np.std(amplitudes, axis=(0, 1))  # Per channel
    high_variance_channels = (amp_std > 3 * np.median(amp_std)).sum()
    high_variance_fraction = high_variance_channels / len(amp_std)

    # 3. Zero/flagged data (already problematic)
    zero_fraction = (amplitudes == 0).mean()

    # 4. Kurtosis (RFI has high kurtosis)
    from scipy.stats import kurtosis
    kurt = kurtosis(amplitudes.flatten())

    metrics = {
        'outlier_fraction': outlier_fraction,
        'high_variance_fraction': high_variance_fraction,
        'zero_fraction': zero_fraction,
        'kurtosis': kurt,
    }

    # Decision criteria
    if (outlier_fraction > 0.02 or           # >2% outliers
        high_variance_fraction > 0.15 or     # >15% high-variance channels
        kurt > 20):                          # High kurtosis
        return "aggressive", metrics
    else:
        return "default", metrics
```

**Thresholds to tune:**

- `outlier_fraction > 0.02` - More than 2% extreme values
- `high_variance_fraction > 0.15` - More than 15% of channels very noisy
- `kurtosis > 20` - Heavy-tailed distribution (RFI characteristic)

---

## Approach 2: Adaptive Flagging (Default → Aggressive on Failure)

### **Two-Pass Strategy**

```python
def adaptive_flag_rfi(ms: str, **kwargs):
    """
    Smart flagging: try default first, escalate if needed.
    """
    # Pass 1: Default flagging
    logger.info("Pass 1: Default flagging strategy")
    flag_rfi(ms, backend="aoflagger", **kwargs)

    # Check if we need aggressive mode
    stats = get_flag_summary(ms)
    needs_aggressive = check_flagging_adequacy(ms, stats)

    if needs_aggressive:
        logger.warning("Contamination detected, switching to aggressive mode")
        # Reset flags and re-run
        reset_flags(ms)
        flag_rfi(
            ms,
            backend="aoflagger",
            strategy="/data/dsa110-contimg/config/dsa110-aggressive.lua",
            **kwargs
        )
    else:
        logger.info("Default flagging sufficient")
```

### **Indicators of Inadequate Flagging**

```python
def check_flagging_adequacy(ms: str, stats: dict) -> bool:
    """
    Check if default flagging was sufficient.

    Returns True if aggressive flagging recommended.
    """
    # 1. Very low flagging percentage (missed RFI?)
    if stats['overall_flagged_fraction'] < 0.02:  # <2% flagged
        # Sanity check: is data too clean to be real?
        # Check visibility scatter
        tb = tables.table(ms, ack=False)
        data = tb.getcol('CORRECTED_DATA')
        flags = tb.getcol('FLAG')
        tb.close()

        unflagged = data[~flags]
        if np.std(unflagged) > threshold:  # Still very noisy
            return True  # Flagged too little

    # 2. Uneven SPW flagging (some SPWs heavily flagged)
    spw_fracs = list(stats['per_spw_flagging'].values())
    if max(spw_fracs) > 0.15:  # Any SPW >15% flagged
        if min(spw_fracs) < 0.02:  # But some <2%
            return True  # Inconsistent, likely missed RFI in quiet SPWs

    # 3. High post-flagging scatter
    # After flagging, check if data still very noisy
    post_flag_noise = calculate_residual_noise(ms)
    if post_flag_noise > expected_thermal_noise * 3:
        return True  # Still too noisy after flagging

    return False
```

---

## Approach 3: Calibration-Triggered Escalation

### **Try Calibration, Retry if Failed**

```python
def flag_and_calibrate_adaptive(ms: str, refant: int, **kwargs):
    """
    Flag, calibrate, and re-flag with aggressive mode if calibration fails.
    """
    # Pass 1: Default flagging + calibration
    logger.info("Attempting calibration with default flagging")
    flag_rfi(ms, backend="aoflagger")

    try:
        calibrate(ms, refant=refant, **kwargs)
        logger.info("✓ Calibration successful with default flagging")
        return "default"

    except CalibrationFailure as e:
        logger.warning(f"Calibration failed: {e}")
        logger.info("Retrying with aggressive flagging")

        # Pass 2: Reset, aggressive flagging, re-calibrate
        reset_flags(ms)
        flag_rfi(
            ms,
            backend="aoflagger",
            strategy="/data/dsa110-contimg/config/dsa110-aggressive.lua"
        )

        calibrate(ms, refant=refant, **kwargs)
        logger.info("✓ Calibration successful with aggressive flagging")
        return "aggressive"
```

**Calibration failure indicators:**

- Excessive gain solutions (>10× median)
- Many failed SPWs (>30% unconverged)
- High solution scatter
- Chi-squared too high

---

## Approach 4: Time/Frequency-Based Heuristics

### **Known Contamination Patterns**

```python
def get_contamination_risk(ms: str) -> str:
    """
    Use observational metadata to assess contamination risk.
    """
    import astropy.time as at
    from casacore import tables

    tb = tables.table(ms, ack=False)
    time_mjd = tb.getcol('TIME')[0] / 86400.0  # Convert to MJD
    freqs = tb.getcol('FREQUENCY')  # Or from spectral window table
    tb.close()

    # Convert to UTC hour
    t = at.Time(time_mjd, format='mjd')
    hour_utc = t.datetime.hour

    # Time-based risk
    # GPS satellites more active during business hours (local time)
    # At Owens Valley (UTC-8): 9am-5pm local = 17:00-01:00 UTC
    if 17 <= hour_utc or hour_utc <= 1:
        time_risk = "high"
    else:
        time_risk = "low"

    # Frequency-based risk
    # Check if we're near known RFI bands
    center_freq = np.mean(freqs) / 1e9  # GHz

    # L-band RFI hotspots
    if 1.2 < center_freq < 1.35:  # GPS L2 band
        freq_risk = "high"
    elif 1.55 < center_freq < 1.62:  # GPS L1, Iridium
        freq_risk = "high"
    else:
        freq_risk = "low"

    # Combine risks
    if time_risk == "high" or freq_risk == "high":
        return "aggressive"
    else:
        return "default"
```

**Considerations:**

- DSA-110 observes at ~1.4 GHz (safe from GPS L1/L2)
- But satellite downlinks and ground transmitters still present
- Time-of-day patterns from local interference

---

## Approach 5: Historical Database (Recommended)

### **Learn from Past Observations**

```python
def get_strategy_from_history(ms: str, db_path: str) -> str:
    """
    Query historical database for similar observations.
    """
    import sqlite3

    # Extract observation metadata
    metadata = extract_metadata(ms)  # time, freq, weather, etc.

    # Query database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find similar observations
    query = """
        SELECT flagging_strategy, calibration_success
        FROM observations
        WHERE ABS(center_freq - ?) < 0.1
          AND ABS(hour_utc - ?) < 2
          AND date > datetime('now', '-30 days')
        ORDER BY timestamp DESC
        LIMIT 10
    """

    cursor.execute(query, (metadata['center_freq'], metadata['hour_utc']))
    results = cursor.fetchall()
    conn.close()

    # If recent similar observations needed aggressive flagging
    aggressive_count = sum(1 for r in results if r[0] == 'aggressive')

    if aggressive_count > len(results) * 0.5:  # >50% needed aggressive
        return "aggressive"
    else:
        return "default"
```

**Database schema:**

```sql
CREATE TABLE observations (
    obs_id TEXT PRIMARY KEY,
    timestamp DATETIME,
    center_freq REAL,
    hour_utc INTEGER,
    flagging_strategy TEXT,
    flag_percentage REAL,
    calibration_success BOOLEAN,
    image_rms REAL,
    weather_conditions TEXT
);
```

**Benefits:**

- Learns from experience
- Accounts for seasonal/temporal patterns
- Can identify problematic time windows

---

## Recommended Implementation

### **Hybrid Approach (Combines Multiple Methods)**

```python
def select_flagging_strategy(ms: str, use_history: bool = True) -> str:
    """
    Intelligent flagging strategy selection.

    Priority order:
    1. Check historical database (if available)
    2. Check pre-flagging statistics
    3. Default to conservative mode
    """
    logger.info("Selecting flagging strategy...")

    # Method 1: Historical database
    if use_history:
        try:
            strategy = get_strategy_from_history(ms, DB_PATH)
            logger.info(f"Historical recommendation: {strategy}")
            return strategy
        except Exception as e:
            logger.warning(f"History lookup failed: {e}")

    # Method 2: Pre-flagging statistics
    try:
        strategy, metrics = assess_contamination(ms)
        logger.info(f"Pre-flagging assessment: {strategy}")
        logger.info(f"Metrics: {metrics}")
        return strategy
    except Exception as e:
        logger.warning(f"Pre-assessment failed: {e}")

    # Method 3: Time/frequency heuristics
    try:
        strategy = get_contamination_risk(ms)
        logger.info(f"Time/freq heuristic: {strategy}")
        return strategy
    except Exception as e:
        logger.warning(f"Heuristic failed: {e}")

    # Fallback: Default
    logger.info("Using default strategy (fallback)")
    return "default"


def smart_flag_with_fallback(ms: str, **kwargs):
    """
    Complete smart flagging workflow with fallback.
    """
    # Select initial strategy
    strategy = select_flagging_strategy(ms)

    if strategy == "aggressive":
        strategy_path = "/data/dsa110-contimg/config/dsa110-aggressive.lua"
    else:
        strategy_path = None  # Use default

    # Flag with selected strategy
    logger.info(f"Flagging with {strategy} strategy")
    flag_rfi(ms, backend="aoflagger", strategy=strategy_path, **kwargs)

    # Check results
    stats = get_flag_summary(ms)
    logger.info(f"Flagged {stats['overall_flagged_fraction']*100:.2f}%")

    # Record in database for future learning
    if use_history:
        record_observation(ms, strategy, stats)

    return stats
```

---

## Practical Metrics Summary

### **When to Use Aggressive Mode**

| Indicator                  | Threshold          | Rationale                       |
| -------------------------- | ------------------ | ------------------------------- |
| **Pre-flagging outliers**  | >2% extreme values | Heavy RFI present               |
| **High-variance channels** | >15% of channels   | Frequency-dependent RFI         |
| **Kurtosis**               | >20                | Non-Gaussian (RFI) distribution |
| **Post-default flagging**  | <2% total flagged  | Likely missed RFI               |
| **SPW inconsistency**      | Max-min >13%       | Uneven RFI across band          |
| **Calibration failure**    | >30% SPWs fail     | Residual RFI corrupting cal     |
| **Historical pattern**     | >50% recent obs    | Known problematic time          |

---

## Integration with Pipeline

### **Modify `flag_rfi()` Function**

```python
# In dsa110_contimg/calibration/flagging.py

def flag_rfi(
    ms: str,
    backend: str = "aoflagger",
    strategy: Optional[str] = None,
    adaptive: bool = True,  # NEW parameter
    **kwargs
):
    """
    Flag RFI with optional adaptive strategy selection.

    Parameters
    ----------
    adaptive : bool
        If True, automatically select flagging strategy based on
        data characteristics. If False, use specified strategy.
    """
    if adaptive and strategy is None:
        # Auto-select strategy
        selected = select_flagging_strategy(ms)
        if selected == "aggressive":
            strategy = "/data/dsa110-contimg/config/dsa110-aggressive.lua"
            logger.info("Auto-selected: aggressive flagging strategy")
        else:
            logger.info("Auto-selected: default flagging strategy")

    # Continue with normal flagging...
    if backend == "aoflagger":
        flag_rfi_aoflagger(ms, strategy=strategy, **kwargs)
    elif backend == "casa":
        flag_rfi_casa(ms, **kwargs)
```

---

## Testing & Validation

### **Validation Steps**

1. **Collect ground truth dataset**
   - Manually classify 50-100 observations as "clean" vs "contaminated"
   - Note which ones benefited from aggressive flagging

2. **Test classification accuracy**
   - Run automatic selection on ground truth set
   - Measure: accuracy, false positives, false negatives

3. **Measure calibration/imaging impact**
   - Does automatic selection improve success rates?
   - Does it maintain image quality on clean data?

4. **Monitor false positives**
   - How often does it unnecessarily use aggressive mode?
   - Cost: ~0 (same speed), but might over-flag slightly

---

## Recommended Starting Point

**For DSA-110 operations:**

1. **Start with Approach 3** (Calibration-triggered escalation)
   - Simple to implement
   - Directly tied to science goal (successful calibration)
   - Automatic retry mechanism

2. **Add Approach 5** (Historical database) over time
   - Learn patterns
   - Improve prediction
   - Reduce unnecessary retries

3. **Consider Approach 1** (Pre-statistics) for real-time optimization
   - Avoids wasteful default pass on obviously contaminated data
   - Saves ~4 minutes on contaminated observations

---

## References

- [RFI Backend Comparison](rfi_backend_comparison_testing.md)
- [AOFlagger Strategy Tuning](AOFLAGGER_STRATEGY_TUNING.md)
- [Temporal Flagging System](temporal_flagging_system.md)

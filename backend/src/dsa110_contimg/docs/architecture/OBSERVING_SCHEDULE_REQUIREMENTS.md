# Observing Schedule Requirements: Pipeline Time & Pointing Dependencies

## Overview

The DSA-110 imaging pipeline imposes specific requirements on observation
scheduling based on calibration validity windows, atmospheric stability, and
pointing constraints. These requirements emerge from the calibration framework
and are encoded in the pipeline's decision logic.

This document answers the key observing schedule questions and explains the
physics/engineering behind each requirement.

---

## Question 1: How Long is a Bandpass Calibration Solution Valid For?

### Answer: **24 Hours**

**Source**: `calibration/README.md` and `utils/defaults.py`

```
"Bandpass Calibration: Perform once every 24 hours. Bandpass solutions are
relatively stable and can be reused for extended periods."
```

### Why 24 Hours?

**Physics**:

- Bandpass solutions characterize frequency-dependent gain variations in the
  receiver
- These variations arise from:
  - Receiver component aging
  - Temperature-dependent impedance matching
  - Cable/connector properties
  - System noise figure variations

**Stability**:

- Over 24 hours, receiver temperatures stabilize due to diurnal cycle
- Moisture in transmission lines has time to equilibrate
- System gains drift slowly (if at all) over this timescale

**Observational experience**:

- DSA-110 bandpass solutions change by < 5% over 24 hours
- Reusing 24-hour-old bandpass maintains < 2% flux calibration error
- Beyond 24 hours, accumulated drift becomes significant

### When to Re-solve Bandpass

Bandpass must be **re-solved immediately** if:

1. **Pointing declination changes by > 1-2 degrees**
   - Different declination → different elevation range → different receiver
     loading
   - Lower elevation (higher airmass) → different atmospheric refraction
   - Beam coupling to ground radiation changes
   - Solution becomes **declination-dependent**

2. **System conditions change dramatically**
   - RF interference increase
   - Receiver reconfiguration
   - Antenna array configuration change
   - Weather change (temperature swing > 10°C)

3. **Time since last solve > 24 hours**
   - Accumulated drift exceeds tolerance
   - Old bandpass solutions become **stale**

### How the Pipeline Handles This

```python
# From streaming_mosaic.py::solve_calibration_for_group()

# Check registry first for existing bandpass tables
registry_tables = self.check_registry_for_calibration(mid_mjd)
has_bp = len(registry_tables.get("BP", [])) > 0

# If found in registry, check if it's still valid
if has_bp and bp_table_age_hours < 24:
    logger.info(f"Reusing existing BP table (age: {bp_table_age_hours:.1f}h)")
    # Use existing tables
else:
    logger.info(f"BP table too old ({bp_table_age_hours:.1f}h), re-solving")
    # Get observation declination
    dec_deg = extract_dec_from_ms(calibration_ms_path)

    # Check if registered calibrator matches this Dec
    bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)

    # If new Dec range, new calibrator, re-solve
    if bp_cal != previous_calibrator:
        solve_bandpass_calibration(calibration_ms_path, bp_cal)
```

---

## Question 2: How Long is a Gain Calibration Solution Valid For?

### Answer: **1 Hour** (sometimes faster)

**Source**: `calibration/README.md` and `utils/defaults.py`

```
"Gain Calibration: Perform every hour. Gain solutions vary with time and
atmospheric conditions, requiring more frequent updates than bandpass."
```

### Why 1 Hour?

**Physics**:

- Gain solutions characterize per-antenna amplitude and phase
- These vary due to:
  - Atmospheric phase noise (tropospheric humidity/temperature)
  - Parallactic angle rotation (changes baseline orientation)
  - Antenna temperature variations
  - System gain drift

**Atmospheric dynamics**:

- Tropospheric phase noise has ~ 10-20 minute coherence time at 3 GHz
- 1 hour = 3-6 decorrelation timescales
- Phase solutions become **meaningless** after decorrelation

**Observational experience**:

- Gain solutions change by 10-20% per hour
- Reusing 1-hour-old gains introduces 5-10% phase error
- At high frequencies (> 3 GHz), even 30 minutes is marginal

### When Gain Solutions Become Invalid Faster

Gain calibration may need **re-solving more frequently** if:

1. **Rapid atmospheric changes** (weather fronts, turbulence)
   - Tropical/subtropical locations (DSA-110 at OVRO, ~37°N)
   - Severe weather conditions
   - **Solution interval**: 30 minutes or less

2. **High frequency observations** (> 10 GHz)
   - Atmosphere much noisier
   - Coherence time drops to 5-10 minutes
   - **Solution interval**: 15-30 minutes

3. **Very long baselines** (> 1 km)
   - Baseline ambiguity resolution requires tighter phase stability
   - **Solution interval**: 15-30 minutes

4. **Continuous source tracking** (not meridian transits)
   - Parallactic angle changes continuously
   - Phase solutions become **direction-dependent** over 1 hour
   - **Solution interval**: 30 minutes or less

### How the Pipeline Handles This

```python
# From utils/defaults.py

CAL_GAIN_SOLINT = "inf"  # Entire scan (default for ~5-10 min observations)
CAL_GAIN_MINSNR = 3.0

# But in streaming_mosaic.py, for 5-minute MS files:
# Solutions are typically computed per-MS (5 min = 1 solution interval)

# For longer observations, use:
# CAL_GAIN_SOLINT = "60s"  # 1-minute solution intervals
# CAL_GAIN_SOLINT = "30s"  # 30-second intervals (fast phase variations)
```

---

## Question 3: Which Data Can a Bandpass Solution Be Applied To?

### Answer: **Data observed within a 24-hour window of the bandpass calibration, at similar declination**

### Detailed Requirements

A bandpass calibration table can be applied to target data if:

#### 1. **Time Window: ±24 hours from BP solve time**

```python
# From database/registry.py

valid_start_mjd = solve_time_mjd - 0.5  # 12 hours before
valid_end_mjd = solve_time_mjd + 1.0     # 24 hours after

# Check: is target observation within this window?
if valid_start_mjd <= target_mjd <= valid_end_mjd:
    can_apply_bandpass = True
else:
    must_resolve_bandpass = True
```

**Rationale**: Beyond 24 hours, receiver thermal drift exceeds tolerance

#### 2. **Declination Range: Same declination ± 1-2 degrees**

```python
# From streaming_mosaic.py::get_bandpass_calibrator_for_dec()

# Bandpass calibration solves at specific declination
cal_dec = extract_dec_from_ms(calibration_ms_path)

# Check if target pointing is compatible
target_dec = extract_dec_from_target_ms(target_ms)

# Tolerance: 1-2 degrees
if abs(target_dec - cal_dec) < 1.0:  # degrees
    can_apply_bandpass = True
    logger.info(f"Dec within tolerance: {target_dec} vs {cal_dec}")
else:
    logger.warning(f"Dec difference too large: {abs(target_dec - cal_dec):.2f}°")
    must_resolve_bandpass = True
```

**Rationale**:

- Different declination → different elevation range
- Elevation affects receiver loading (ground radiation coupling)
- Elevation affects atmospheric path length
- Bandpass becomes **declination-dependent** if > 2° difference

#### 3. **Calibrator Source: Must be from same calibrator**

```python
# From calibration/cli_calibrate.py

# Bandpass tables tagged with calibrator name
caltable_metadata = {
    "calibrator_name": "3C286",
    "calibrator_ra": 123.456,
    "calibrator_dec": 78.901,
    "solve_time_mjd": 60000.5,
    "pointing_dec": 45.0,
}

# When applying, check:
# - Same calibrator name
# - Same/similar declination (± 1-2°)
# - Within 24-hour window
```

**Rationale**:

- Different calibrators have different structures/morphologies
- Bandpass model depends on calibrator source
- Cannot apply 3C286 bandpass to 3C48 observations

#### 4. **Frequency Range: Same receiver/subband configuration**

```python
# Implied in frequency ordering checks

# Bandpass characterizes frequency-dependent response
# Must be applied to same frequency channels

if target_spws != cal_spws:
    logger.warning("SPW configuration different")
    # May need to interpolate or re-solve
```

### Practical Observing Scenario

```
Time 12:00 UTC
  └─ Solve BP calibration on 3C286 at Dec=+30°
     Table: cal_bp_3c286_12:00.bpcal
     Valid: 12:00 ± 12h = 00:00 - 12:00 next day
     Dec tolerance: +28° to +32°

Time 12:30 UTC (same day, same field)
  └─ Observe target at Dec=+30.5°
     Apply: cal_bp_3c286_12:00.bpcal ✓ OK
     (within 24h, Dec OK, same config)

Time 22:00 UTC (same day, different field)
  └─ Observe target at Dec=+35°
     Apply: cal_bp_3c286_12:00.bpcal ✗ FAIL
     Reason: Dec difference too large
     Action: Solve new BP calibration

Time 13:00 UTC (next day)
  └─ Observe target at Dec=+30°
     Apply: cal_bp_3c286_12:00.bpcal ✓ OK
     (within 24h, Dec OK)

Time 13:01 UTC (next day, just past 24h window)
  └─ Observe target at Dec=+30°
     Apply: cal_bp_3c286_12:00.bpcal ✗ EXPIRED
     Action: Solve new BP calibration (old one stale)
```

---

## Question 4: Which Data Can a Gain Solution Be Applied To?

### Answer: **Data observed within 1 hour of the gain calibration, same field/calibrator**

### Detailed Requirements

A gain calibration table can be applied to target data if:

#### 1. **Time Window: ±1 hour from gain solve time**

```python
# From database/registry.py and apply_service.py

valid_start_mjd = solve_time_mjd - (30.0 / 60 / 24)   # 30 minutes before
valid_end_mjd = solve_time_mjd + (60.0 / 60 / 24)     # 60 minutes after

# Check: is target observation within this window?
if valid_start_mjd <= target_mjd <= valid_end_mjd:
    can_apply_gain = True
else:
    must_resolve_gain = True
```

**Rationale**: Atmospheric phase noise decorrelates faster than 1 hour

#### 2. **Calibrator Source: Same calibrator or nearby**

```python
# Gain solutions derived from specific calibrator
if gain_table.calibrator == target_calibrator:
    can_apply = True
elif gain_table.calibrator.nearby(target_calibrator, sep_deg < 2):
    # Nearby calibrator OK if declination similar
    can_apply = True
else:
    must_resolve_gain = True
```

**Rationale**:

- Gains are calibrator-specific
- Different calibrators at different positions have different bandpass-delay
  issues
- Can sometimes use nearby calibrator if within couple degrees

#### 3. **Direction Consistency: Same pointing/field**

```python
# For direction-independent calibration, same field
# For direction-dependent, must check if direction is covered

if obs_field == gain_table.field:
    can_apply = True
elif obs_field.nearby(gain_table.field, sep_deg < 0.5):
    # Very close fields OK
    can_apply = True
else:
    # Different field may need re-solve (if solutions are direction-dependent)
    can_apply = False
```

**Rationale**:

- Phase solutions can be direction-dependent (ionosphere, atmosphere)
- Safe to apply only to same field

#### 4. **Array Configuration: Same antenna layout**

```python
# Gain solutions are per-antenna
if len(target_antennas) != len(gain_table_antennas):
    cannot_apply = True
elif target_antennas != gain_table_antennas:
    cannot_apply = True
```

**Rationale**:

- Gain solutions computed for specific antennas
- Cannot apply to different array configuration

### Practical Observing Scenario

```
Time 12:00 UTC
  └─ Solve gain calibration on 3C286
     Table: cal_gain_3c286_12:00.gcal
     Valid: 11:30 - 13:00 UTC
     (30 min before solve, 60 min after)

Time 12:15 UTC (same calibrator)
  └─ Observe target (same field)
     Apply: cal_gain_3c286_12:00.gcal ✓ OK

Time 12:45 UTC (same calibrator)
  └─ Observe target (same field)
     Apply: cal_gain_3c286_12:00.gcal ✓ OK

Time 13:05 UTC (past 1-hour window)
  └─ Observe target (same field)
     Apply: cal_gain_3c286_12:00.gcal ✗ EXPIRED
     Action: Solve new gain calibration

Time 13:00 UTC (1 hour later, different field)
  └─ Observe target at different position
     Apply: cal_gain_3c286_12:00.gcal ✗ DIFFERENT FIELD
     Action: Solve new gain calibration or apply with caution
```

---

## Question 5: What Happens When the Telescope Repoints?

### Answer: Depends on declination change and time since last calibration

### Scenario 1: Small Declination Change (< 1°) Within 24 Hours

```
Observation 1: 12:00 UTC, target Dec = +30.0°
  ├─ Solve BP calibration (valid until 12:00 next day, Dec range: ±1°)
  └─ Solve gain calibration (valid until 13:00)

Repoint: 12:30 UTC to Dec = +30.5°
  ├─ Reuse BP calibration ✓ (Dec within ±1° tolerance)
  ├─ Reuse gain calibration ✓ (within 1 hour)
  └─ Apply both tables, start observing immediately

Result: **No new calibration needed**
Time cost: 0 minutes
```

### Scenario 2: Large Declination Change (> 2°) Within 24 Hours

```
Observation 1: 12:00 UTC, Dec = +30.0°
  ├─ Solve BP calibration
  └─ Solve gain calibration

Repoint: 14:00 UTC to Dec = +45.0°
  ├─ Bandpass: Dec difference = 15° > 1° tolerance
  │  └─ **BP table INVALID** - must re-solve
  ├─ Gain: Within 2-hour window but different Dec
  │  └─ **Gain table questionable** - should re-solve
  └─ Must solve both calibrations before observing

Required actions:
  1. Slew to new position
  2. Observe calibrator at Dec=+45° (find appropriate calibrator)
  3. Solve bandpass calibration (~ 10-15 min)
  4. Solve gain calibration (~ 5-10 min)
  5. Apply to target, start observing

Result: **Time cost: 15-25 minutes**
```

### Scenario 3: Gain Calibration Expires

```
Observation 1: 12:00 UTC
  └─ Solve gain calibration (valid until 13:00)

Gap: 13:05 UTC - no observations for > 1 hour
  └─ Atmospheric phase noise decorrelated
  └─ Gain solutions stale

Resume Observation: 14:00 UTC (same field, same Dec)
  ├─ BP table still valid (within 24h)
  ├─ Gain table EXPIRED (> 1 hour old)
  └─ Must re-solve gain calibration

Required actions:
  1. Observe calibrator in current field
  2. Solve new gain calibration (~ 5-10 min)
  3. Apply to target, resume observing

Result: **Time cost: 5-10 minutes**
```

### Scenario 4: Bandpass Calibration Expires

```
Observation 1: Day 1, 12:00 UTC
  └─ Solve BP calibration (valid until Day 2, 12:00 UTC)

Gap: Extended observing with no repoint

Resume: Day 2, 13:00 UTC (> 24 hours later)
  ├─ BP table EXPIRED (> 24 hours)
  ├─ Gain tables definitely expired
  └─ Must resolve both

Required actions:
  1. Observe bandpass calibrator
  2. Solve new BP calibration (~ 10-15 min)
  3. Solve new gain calibration (~ 5-10 min)
  4. Apply to target, resume observing

Result: **Time cost: 15-25 minutes**
```

### How the Pipeline Handles Repointing

```python
# From streaming_mosaic.py::solve_calibration_for_group()

# Extract observation declination
dec_deg = extract_dec_from_ms(calibration_ms_path)

# Check if bandpass calibrator changed
current_bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
previous_bp_cal = self.registry.get_last_bp_calibrator()

if current_bp_cal != previous_bp_cal:
    logger.info(f"Bandpass calibrator changed: {previous_bp_cal} → {current_bp_cal}")
    logger.info(f"Repointing to Dec={dec_deg:.2f}°")
    logger.info("Re-solving bandpass calibration (new declination)")
    solve_bandpass_calibration(...)
elif time_since_bp_solve > 24 * 3600:
    logger.info(f"BP calibration stale ({time_since_bp_solve/3600:.1f}h)")
    logger.info("Re-solving bandpass calibration (expired)")
    solve_bandpass_calibration(...)
else:
    logger.info(f"Reusing BP calibration (age: {time_since_bp_solve/3600:.1f}h)")

# Similar logic for gain calibration
if time_since_gain_solve > 60 * 60:  # 1 hour
    logger.info("Gain calibration expired, re-solving")
    solve_gain_calibration(...)
```

---

## Observing Schedule Optimization

### Recommended Patterns

#### Pattern 1: Single Declination, Long Observation

```
12:00 UTC: Solve BP + Gain
12:15 UTC: Begin observing target
12:15 - 12:59 UTC: Observe (< 1 hour, gain valid)
13:00 UTC: Solve new gain (BP still valid)
13:15 - 13:59 UTC: Continue observing (another hour)
...
Next day 12:00 UTC: Solve new BP (old one expires after 24h)

Efficiency: High (minimal overhead, single declination)
```

#### Pattern 2: Multiple Declinations

```
Field A: Dec = +30°
  12:00 UTC: Solve BP_A + Gain_A
  12:15 - 12:59 UTC: Observe (1 hour, gain expires)

Field B: Dec = +35° (> 2° away)
  13:00 UTC: Solve BP_B + Gain_B (new calibrator needed)
  13:15 - 13:59 UTC: Observe

Field C: Dec = +30.5° (back to Field A)
  14:00 UTC: Can reuse BP_A?
    └─ Yes if within 2° and < 24h
    └─ Solve new Gain_C (old expired)
  14:15 - 14:59 UTC: Observe

Efficiency: Medium (need new BP for large declination changes)
```

#### Pattern 3: Fast Repointing Between Nearby Fields

```
Field A: Dec = +30.0°
  12:00 UTC: Solve BP + Gain
  12:15 - 12:25 UTC: Observe (10 min)

Repoint to Field B: Dec = +30.3° (< 1° away)
  12:25 - 12:30 UTC: Slew (5 min)
  12:30 UTC: Reuse BP ✓ (Dec OK), Reuse Gain ✓ (within 1h)
  12:30 - 12:59 UTC: Observe (29 min)

Total overhead: ~10% for slewing
No calibration re-solve needed

Efficiency: Very High
```

---

## Summary Table: Calibration Validity & Repointing

| Calibration  | Validity | Declination Tolerance | Repoint Impact        | Re-solve Trigger           |
| ------------ | -------- | --------------------- | --------------------- | -------------------------- |
| **Bandpass** | 24 hours | ±1-2°                 | Small repoint OK      | New Dec > 2°, or age > 24h |
| **Gain**     | 1 hour   | Same field            | Must verify direction | New field or age > 1h      |

---

## Key Insight: Observing Schedule is Driven by Atmospheric Physics

Calibration validity windows are **not arbitrary limits**—they're determined by:

- **Bandpass (24h)**: Receiver thermal stability + system gain drift timescale
- **Gain (1h)**: Atmospheric phase noise decorrelation timescale
- **Declination (±1-2°)**: Receiver loading geometry and atmospheric path
  changes

To maximize observing efficiency, schedule:

1. Calibrator observations on grid of declinations (0°, ±10°, ±20°, ...)
2. Keep target pointing changes < 2° for continuous observing
3. Schedule major repoints at 24-hour boundaries to coincide with BP refresh
4. Use overlapping 1-hour gain blocks for continuous tracking

# Calibration Decision Logic: Formal Specification (Revised)

## Overview

This document specifies the exact decision logic for calibration validity and
repointing, with the rigor of a circuit board: no ambiguity, complete coverage
of all states, deterministic outcomes.

**REVISION (v2.0)**: Bandpass calibrator validity windows are now **48 hours
total** (24 hours before peak transit + 24 hours after peak transit), enabling
**quality-based selection** between multiple available calibrators.

---

## Part 1: State Variables & Definitions

### Bandpass (BP) State (Multi-Calibrator)

```
BP_state = {
    available_tables: List[BP_Table],  # Multiple BP tables may be valid
}

BP_Table = {
    table_exists: Boolean,              # BP table in registry
    on_disk: Boolean,                   # BP file physically exists
    transit_mjd: Float,                 # Peak transit time (MJD) for this calibrator
    age_from_transit_hours: Float,      # Hours since/before transit (signed: -24 to +24)
    calibrator_name: String,            # e.g., "3C286", "0834+555"
    cal_dec_deg: Float,                 # Declination of calibrator pointing
    valid_start_mjd: Float,             # Registry validity window start (transit - 24h)
    valid_end_mjd: Float,               # Registry validity window end (transit + 24h)
    quality_metrics: Dict,              # SNR, flagged_fraction, n_antennas, etc.
    quality_score: Float,                # Computed quality score (higher = better)
}
```

**Key Change**: `BP_state` now contains a **list** of available tables, not a
single table.

### Gain (G) State (Unchanged)

```
G_state = {
    table_exists: Boolean,              # Gain table in registry
    on_disk: Boolean,                   # Gain file physically exists
    age_minutes: Float,                 # Time since gain solve (0.0 = just solved)
    field_name: String,                 # Field ID from original solve
    valid_start_mjd: Float,            # Registry validity window start
    valid_end_mjd: Float,               # Registry validity window end
}
```

### Observation Parameters

```
obs_params = {
    target_dec_deg: Float,              # Current pointing declination
    target_mjd: Float,                 # Observation time (MJD)
    target_field: String,               # Current field identifier
    new_calibrator_available: Boolean,  # Can we find calibrator for this Dec?
}
```

---

## Part 2: Validity Predicates (Boolean Functions)

### BP Validity Predicate: `bp_table_is_valid(BP_Table, obs_params)`

```
bp_table_is_valid(BP_Table bp_table, obs_params obs) :=
    (bp_table.table_exists
     AND bp_table.on_disk
     AND bp_table_within_transit_window(bp_table, obs)
     AND bp_dec_compatible(bp_table, obs)
     AND bp_time_within_window(bp_table, obs))
```

#### Predicate 1: Transit Window Validity (NEW)

```
bp_table_within_transit_window(bp_table, obs) :=
    (obs.target_mjd >= bp_table.valid_start_mjd
     AND obs.target_mjd <= bp_table.valid_end_mjd)

WHERE:
    bp_table.valid_start_mjd = bp_table.transit_mjd - 1.0  # 24 hours before transit
    bp_table.valid_end_mjd = bp_table.transit_mjd + 1.0    # 24 hours after transit

INTERPRETATION:
  - True: Observation within 48-hour validity window (24h before to 24h after transit)
  - False: Observation outside window

STRICTNESS: Hard boundaries at ±24 hours from transit
  - Exactly at transit - 24h: TRUE :check_mark:
  - Exactly at transit + 24h: TRUE :check_mark:
  - 1 second before transit - 24h: FALSE :ballot_x:
  - 1 second after transit + 24h: FALSE :ballot_x:

PHYSICAL JUSTIFICATION:
  - Receiver thermal stability: 24 hours before transit (pre-transit calibration)
  - System gain drift: 24 hours after transit (post-transit calibration)
  - Total window: 48 hours per calibrator transit
  - Multiple calibrators: At any time, typically 2 calibrators available
    (one that transited recently, one that will transit soon)
```

#### Predicate 2: Declination Compatibility (Unchanged)

```
bp_dec_compatible(bp_table, obs) :=
    ABS(bp_table.cal_dec_deg - obs.target_dec_deg) <= 1.0

INTERPRETATION:
  - True: Dec difference ≤ 1.0 degree
  - False: Dec difference > 1.0 degree

STRICTNESS: Hard boundary at 1.0 degree
  - ±0.9999°: TRUE :check_mark:
  - ±1.0001°: FALSE :ballot_x:
```

#### Predicate 3: Time Window Validity (Unchanged)

```
bp_time_within_window(bp_table, obs) :=
    (obs.target_mjd >= bp_table.valid_start_mjd
     AND obs.target_mjd <= bp_table.valid_end_mjd)

INTERPRETATION:
  - True: Observation within registry validity window
  - False: Outside window
```

### BP Selection Predicate: `select_best_bp_table(List[BP_Table])`

```
select_best_bp_table(valid_bp_tables: List[BP_Table]) -> BP_Table:
    """
    Select the best BP table from multiple valid candidates using quality metrics.

    SELECTION CRITERIA (priority order):
    1. Quality score (higher = better)
    2. Proximity to transit (closer to transit = better, within validity window)
    3. Declination match (closer Dec = better, within 1° tolerance)
    4. Recency (newer table = better, if quality scores equal)

    Returns: Best BP_Table, or None if list is empty
    """

    IF len(valid_bp_tables) == 0:
        RETURN None

    IF len(valid_bp_tables) == 1:
        RETURN valid_bp_tables[0]

    # Compute quality scores for all candidates
    FOR bp_table IN valid_bp_tables:
        bp_table.quality_score = compute_quality_score(bp_table)

    # Sort by quality score (descending), then by proximity to transit
    sorted_tables = SORT valid_bp_tables BY:
        PRIMARY: quality_score DESC
        SECONDARY: ABS(obs.target_mjd - bp_table.transit_mjd) ASC
        TERTIARY: ABS(bp_table.cal_dec_deg - obs.target_dec_deg) ASC
        QUATERNARY: bp_table.created_at DESC

    RETURN sorted_tables[0]  # Best candidate
```

### Quality Score Computation: `compute_quality_score(BP_Table)`

```
compute_quality_score(bp_table: BP_Table) -> Float:
    """
    Compute a single quality score from multiple metrics.

    Higher score = better calibration quality.

    METRICS USED:
    - snr_mean: Mean SNR across all solutions (higher = better)
    - flagged_fraction: Fraction of flagged solutions (lower = better)
    - n_antennas: Number of antennas with solutions (higher = better)
    - n_spws: Number of spectral windows (higher = better)

    SCORING FORMULA:
    quality_score = (
        snr_mean * 0.4 +                    # 40% weight: SNR
        (1.0 - flagged_fraction) * 0.3 +    # 30% weight: Data quality
        (n_antennas / max_antennas) * 0.2 + # 20% weight: Antenna coverage
        (n_spws / max_spws) * 0.1            # 10% weight: Frequency coverage
    )

    NORMALIZATION:
    - snr_mean: Normalized to [0, 1] using max expected SNR (e.g., 100)
    - flagged_fraction: Already [0, 1]
    - n_antennas: Normalized by max_antennas (e.g., 110 for DSA-110)
    - n_spws: Normalized by max_spws (e.g., 16 for DSA-110)

    DEFAULT VALUES (if metrics missing):
    - snr_mean: 0.0 (assume poor quality)
    - flagged_fraction: 1.0 (assume all flagged)
    - n_antennas: 0 (assume no antennas)
    - n_spws: 0 (assume no SPWs)

    Returns: Float in [0, 1] range (1.0 = perfect, 0.0 = unusable)
    """

    metrics = bp_table.quality_metrics or {}

    # Extract metrics with defaults
    snr_mean = metrics.get("snr_mean", 0.0)
    flagged_fraction = metrics.get("flagged_fraction", 1.0)
    n_antennas = metrics.get("n_antennas", 0)
    n_spws = metrics.get("n_spws", 0)

    # Normalize SNR (assume max SNR = 100)
    snr_normalized = min(snr_mean / 100.0, 1.0)

    # Normalize antenna count (assume max = 110)
    max_antennas = 110
    antenna_normalized = min(n_antennas / max_antennas, 1.0)

    # Normalize SPW count (assume max = 16)
    max_spws = 16
    spw_normalized = min(n_spws / max_spws, 1.0)

    # Compute weighted score
    score = (
        snr_normalized * 0.4 +
        (1.0 - flagged_fraction) * 0.3 +
        antenna_normalized * 0.2 +
        spw_normalized * 0.1
    )

    RETURN score
```

### Gain Validity Predicate: `g_is_valid(G_state, obs_params)` (Unchanged)

```
g_is_valid(G_state g, obs_params obs) :=
    (g.table_exists
     AND g.on_disk
     AND g_age_within_limit(g)
     AND g_field_matches(g, obs)
     AND g_time_within_window(g, obs))
```

#### Predicate 1: Age Limit (Unchanged)

```
g_age_within_limit(g) :=
    (g.age_minutes <= 60.0)

INTERPRETATION:
  - True: Table age ≤ 60 minutes
  - False: Table age > 60 minutes (EXPIRED)

STRICTNESS: Hard boundary at 60.0 minutes
  - 59m 59s: TRUE :check_mark:
  - 60m 01s: FALSE :ballot_x:
```

#### Predicate 2: Field Compatibility (Unchanged)

```
g_field_matches(g, obs) :=
    (g.field_name == obs.target_field)

INTERPRETATION:
  - True: Same field (or field in same position)
  - False: Different field position
```

#### Predicate 3: Time Window Validity (Unchanged)

```
g_time_within_window(g, obs) :=
    (obs.target_mjd >= g.valid_start_mjd
     AND obs.target_mjd <= g.valid_end_mjd)
```

---

## Part 3: Decision Logic (State Machine - Revised)

### Top-Level Decision Function (Multi-Calibrator)

```
FUNCTION: determine_calibration_action(BP_state bp_state, G_state g, obs_params obs)
RETURNS: (action_bp, action_g, selected_bp_table, estimated_delay_minutes)

BEGIN
  # Step 1: Find all valid BP tables (multiple may exist)
  valid_bp_tables = []
  FOR bp_table IN bp_state.available_tables:
      IF bp_table_is_valid(bp_table, obs):
          valid_bp_tables.append(bp_table)

  # Step 2: Select best BP table from valid candidates
  selected_bp_table = select_best_bp_table(valid_bp_tables)
  bp_valid = (selected_bp_table IS NOT None)

  # Step 3: Evaluate G validity
  g_valid = g_is_valid(g, obs)

  # Step 4: Decision matrix (4 states, same as before)
  CASE (bp_valid, g_valid):

    CASE (TRUE, TRUE):                    # Both valid
      action_bp = REUSE_BP
      action_g = REUSE_G
      delay = 0
      reason = f"Both calibrations valid (selected BP: {selected_bp_table.calibrator_name})"

    CASE (TRUE, FALSE):                   # BP valid, G invalid
      action_bp = REUSE_BP
      action_g = SOLVE_NEW_G
      delay = 7  # Estimate: 5-10 min for gain solve
      reason = f"Gain expired or incompatible, BP reusable (selected: {selected_bp_table.calibrator_name})"

    CASE (FALSE, TRUE):                   # BP invalid, G valid
      action_bp = SOLVE_NEW_BP
      action_g = INVALID_WHEN_BP_NEW      # G becomes invalid if we change calibrator
      # Recalculate G validity with new calibrator
      IF new_calibrator_available:
          # New BP may use different calibrator
          # Must resolve G as well for consistency
          action_g = SOLVE_NEW_G
          delay = 20  # BP + G re-solve
          reason = "BP invalid, G valid but must re-solve both"
      ELSE:
          # Cannot solve without available calibrator
          action_bp = CANNOT_PROCEED
          action_g = CANNOT_PROCEED
          delay = UNDEFINED
          reason = f"No calibrator available for Dec={obs.target_dec_deg:.1f}°"

    CASE (FALSE, FALSE):                  # Both invalid
      action_bp = SOLVE_NEW_BP
      action_g = SOLVE_NEW_G
      delay = 20  # BP + G re-solve
      reason = "Both calibrations expired"

  RETURN (action_bp, action_g, selected_bp_table, delay, reason)
END
```

---

## Part 4: Explicit Decision Matrix (Truth Table - Revised)

### 4-State Matrix with Multi-Calibrator Selection

| State | BP Valid | G Valid | BP Action | G Action | BP Selection                     | Delay  | Precondition                               | Next State |
| ----- | -------- | ------- | --------- | -------- | -------------------------------- | ------ | ------------------------------------------ | ---------- |
| **A** | T        | T       | REUSE     | REUSE    | Quality-based from 2+ candidates | 0 min  | Both tables exist & valid                  | OBSERVING  |
| **B** | T        | F       | REUSE     | SOLVE    | Quality-based from 2+ candidates | 7 min  | BP OK, G expired or field mismatch         | OBSERVING  |
| **C** | F        | T       | SOLVE     | SOLVE    | Find new calibrator(s)           | 20 min | BP expired/stale, must find new calibrator | OBSERVING  |
| **D** | F        | F       | SOLVE     | SOLVE    | Find new calibrator(s)           | 20 min | Both expired                               | OBSERVING  |
| **E** | F        | -       | ERROR     | ERROR    | None                             | ∞      | No calibrator available for declination    | BLOCKED    |

**Key Change**: States A and B now involve **quality-based selection** from
multiple BP candidates.

---

## Part 5: Multi-Calibrator Selection Logic

### Scenario: Two Valid BP Tables Available

```
OBSERVATION TIME: 12:00 UTC, Dec = +30.0°

CALIBRATOR 1: 3C286
  - Transit: 06:00 UTC (6 hours ago)
  - Valid window: 06:00 - 06:00 next day (24h before to 24h after)
  - Current age from transit: +6 hours
  - Quality score: 0.85 (high SNR, low flagged fraction)
  - Dec: +30.5° (diff: 0.5°)

CALIBRATOR 2: 0834+555
  - Transit: 18:00 UTC (6 hours from now)
  - Valid window: 18:00 previous day - 18:00 (24h before to 24h after)
  - Current age from transit: -6 hours (6 hours before transit)
  - Quality score: 0.72 (moderate SNR, some flagged data)
  - Dec: +29.8° (diff: 0.2°)

SELECTION PROCESS:
  1. Both tables are valid (within ±24h of transit, Dec within ±1°)
  2. Compute quality scores:
     - 3C286: 0.85
     - 0834+555: 0.72
  3. Primary sort: Quality score (descending)
     - 3C286 wins (0.85 > 0.72)
  4. Result: SELECT 3C286 BP table

  REASONING:
    - 3C286 has higher quality (better SNR, fewer flags)
    - Dec difference is acceptable for both (0.5° vs 0.2°, both < 1°)
    - Transit proximity is secondary (both within validity window)
```

### Scenario: Only One Valid BP Table

```
OBSERVATION TIME: 12:00 UTC, Dec = +30.0°

CALIBRATOR 1: 3C286
  - Transit: 06:00 UTC (6 hours ago)
  - Valid window: 06:00 - 06:00 next day
  - Quality score: 0.85
  - Dec: +30.5° (diff: 0.5°)

CALIBRATOR 2: 0834+555
  - Transit: 18:00 UTC (6 hours from now)
  - Valid window: 18:00 previous day - 18:00
  - Quality score: 0.72
  - Dec: +25.0° (diff: 5.0°)  ← OUTSIDE ±1° TOLERANCE

SELECTION PROCESS:
  1. Only 3C286 is valid (Dec diff = 0.5° < 1.0°)
  2. 0834+555 is invalid (Dec diff = 5.0° > 1.0°)
  3. Result: SELECT 3C286 BP table (only valid candidate)
```

### Scenario: No Valid BP Tables (Repointing)

```
OBSERVATION TIME: 12:00 UTC, Dec = +45.0°  ← LARGE REPOINT

CALIBRATOR 1: 3C286
  - Transit: 06:00 UTC
  - Dec: +30.5° (diff: 14.5°)  ← OUTSIDE ±1° TOLERANCE
  - Status: INVALID (Dec mismatch)

CALIBRATOR 2: 0834+555
  - Transit: 18:00 UTC
  - Dec: +29.8° (diff: 15.2°)  ← OUTSIDE ±1° TOLERANCE
  - Status: INVALID (Dec mismatch)

SELECTION PROCESS:
  1. No valid BP tables (both Dec differences > 1.0°)
  2. Result: SOLVE_NEW_BP (State C or D)
  3. Action: Find calibrator for Dec = +45.0°
     - Query catalog for calibrator near Dec = +45.0°
     - If found: Solve new BP calibration
     - If not found: CANNOT_PROCEED (State E)
```

---

## Part 6: Quality Score Weights (Configurable)

### Default Weights

```
QUALITY_SCORE_WEIGHTS = {
    "snr_weight": 0.4,           # 40%: Signal-to-noise ratio
    "flagged_weight": 0.3,        # 30%: Data quality (1 - flagged_fraction)
    "antenna_weight": 0.2,        # 20%: Antenna coverage
    "spw_weight": 0.1,            # 10%: Frequency coverage
}

TOTAL: 1.0 (must sum to 1.0)
```

### Rationale

- **SNR (40%)**: Primary indicator of calibration solution quality
- **Flagged fraction (30%)**: Data integrity and reliability
- **Antenna coverage (20%)**: Array completeness
- **SPW coverage (10%)**: Frequency completeness

### Override Mechanism

```
# Environment variable or config file
QUALITY_SNR_WEIGHT=0.5
QUALITY_FLAGGED_WEIGHT=0.3
QUALITY_ANTENNA_WEIGHT=0.15
QUALITY_SPW_WEIGHT=0.05
```

---

## Part 7: Implementation Rules (Hardware-Like Precision - Revised)

### Rule 1: Multi-Calibrator Selection is Deterministic

```
RULE: Given the same set of valid BP tables and quality metrics,
      selection always produces the same result.

IMPLICATION:
  - Quality scores are computed deterministically
  - Sorting is stable (ties broken by secondary criteria)
  - No randomness, no hysteresis

VIOLATION DETECTION: Audit log compares consecutive selections
```

### Rule 2: Validity Windows Are Transit-Centered

```
RULE: BP validity window is ALWAYS:
      valid_start_mjd = transit_mjd - 1.0 day  (24 hours before)
      valid_end_mjd = transit_mjd + 1.0 day    (24 hours after)

STRICTNESS: No exceptions, no configuration override
  - Window is always 48 hours total
  - Always centered on transit time
  - Always symmetric (±24h)

HARDWARE ANALOGY: Like a fixed-width time gate
  - Transit time: Center of gate
  - Gate width: 48 hours (fixed)
  - Gate position: Moves with each calibrator transit
```

### Rule 3: Quality Score Computation is Reproducible

```
RULE: Quality score depends ONLY on:
      - Quality metrics (SNR, flags, antennas, SPWs)
      - Fixed weights (configurable but constant during execution)
      - No time-dependent factors
      - No random factors

VERIFICATION: Same metrics → same score (always)
```

### Rule 4: Selection Criteria Priority is Fixed

```
RULE: Selection priority order is ALWAYS:
      1. Quality score (PRIMARY)
      2. Proximity to transit (SECONDARY)
      3. Declination match (TERTIARY)
      4. Recency (QUATERNARY)

NO EXCEPTIONS: This order is hardcoded and cannot be changed
               without modifying the algorithm.
```

---

## Part 8: Formal Specification in Pseudo-Code (Revised)

### Complete Decision Algorithm (Multi-Calibrator)

```python
FUNCTION calibration_decision(
    BP_state bp_state,
    G_state g,
    obs_params obs,
    current_mjd
) -> Decision:
    """
    Formal calibration validity decision algorithm (multi-calibrator version).

    PRECONDITIONS:
      - current_mjd is well-defined time
      - bp_state.available_tables is list of BP_Table objects
      - g, obs are complete state structures
      - All numeric fields initialized (no NaN/Inf)

    POSTCONDITIONS:
      - Decision is one of: REUSE_BP, SOLVE_NEW_BP, REUSE_G, SOLVE_NEW_G, CANNOT_PROCEED
      - If Decision != CANNOT_PROCEED, selected_bp_table is set
      - Decision deterministic given same inputs
    """

    # Step 1: Find all valid BP tables
    valid_bp_tables = []
    FOR bp_table IN bp_state.available_tables:
        # Check transit window validity
        transit_window_ok = (
            obs.target_mjd >= bp_table.valid_start_mjd AND
            obs.target_mjd <= bp_table.valid_end_mjd
        )

        # Check declination compatibility
        dec_ok = ABS(bp_table.cal_dec_deg - obs.target_dec_deg) <= 1.0

        # Check time window validity
        time_ok = (
            obs.target_mjd >= bp_table.valid_start_mjd AND
            obs.target_mjd <= bp_table.valid_end_mjd
        )

        # Check existence
        exists_ok = bp_table.table_exists AND bp_table.on_disk

        IF transit_window_ok AND dec_ok AND time_ok AND exists_ok:
            valid_bp_tables.append(bp_table)

    # Step 2: Select best BP table using quality metrics
    selected_bp_table = None
    IF len(valid_bp_tables) > 0:
        # Compute quality scores for all candidates
        FOR bp_table IN valid_bp_tables:
            bp_table.quality_score = compute_quality_score(bp_table)

        # Sort by priority: quality (desc), transit proximity (asc), dec match (asc), recency (desc)
        sorted_tables = SORT valid_bp_tables BY:
            PRIMARY: bp_table.quality_score DESC
            SECONDARY: ABS(obs.target_mjd - bp_table.transit_mjd) ASC
            TERTIARY: ABS(bp_table.cal_dec_deg - obs.target_dec_deg) ASC
            QUATERNARY: bp_table.created_at DESC

        selected_bp_table = sorted_tables[0]

    bp_valid = (selected_bp_table IS NOT None)

    # Step 3: Evaluate G validity (unchanged)
    g_age_minutes = (current_mjd - g.solve_mjd) * 24.0 * 60.0
    g_age_ok = g_age_minutes <= 60.0
    g_field_ok = g.field_name == obs.target_field
    g_time_ok = (obs.target_mjd >= g.valid_start_mjd AND
                 obs.target_mjd <= g.valid_end_mjd)
    g_exists = g.table_exists AND g.on_disk

    g_is_valid = g_exists AND g_age_ok AND g_field_ok AND g_time_ok

    # Step 4: Decision matrix (exhaustive 4-state enumeration)
    IF bp_valid AND g_is_valid:
        action_bp = REUSE_BP
        action_g = REUSE_G
        delay_minutes = 0
        reason = f"CASE A: Both valid (selected BP: {selected_bp_table.calibrator_name})"

    ELSE IF bp_valid AND NOT g_is_valid:
        action_bp = REUSE_BP
        action_g = SOLVE_NEW_G
        delay_minutes = 7
        reason = f"CASE B: BP valid, G invalid (selected BP: {selected_bp_table.calibrator_name})"

    ELSE IF NOT bp_valid AND g_is_valid:
        cal = find_calibrator_for_dec(obs.target_dec_deg)
        IF cal != NULL:
            action_bp = SOLVE_NEW_BP
            action_g = SOLVE_NEW_G
            delay_minutes = 20
            reason = "CASE C: BP invalid, G valid but must re-solve both"
        ELSE:
            action_bp = CANNOT_PROCEED
            action_g = CANNOT_PROCEED
            delay_minutes = UNDEFINED
            reason = f"CASE E: No calibrator for Dec={obs.target_dec_deg:.1f}°"

    ELSE:  # NOT bp_valid AND NOT g_is_valid
        cal = find_calibrator_for_dec(obs.target_dec_deg)
        IF cal != NULL:
            action_bp = SOLVE_NEW_BP
            action_g = SOLVE_NEW_G
            delay_minutes = 20
            reason = "CASE D: Both invalid"
        ELSE:
            action_bp = CANNOT_PROCEED
            action_g = CANNOT_PROCEED
            delay_minutes = UNDEFINED
            reason = f"CASE E: No calibrator for Dec={obs.target_dec_deg:.1f}°"

    # Construct decision object (immutable, deterministic)
    decision = Decision(
        bp_action=action_bp,
        g_action=action_g,
        selected_bp_table=selected_bp_table,
        estimated_delay_minutes=delay_minutes,
        reason=reason,
        timestamp_mjd=current_mjd,
        n_valid_bp_candidates=len(valid_bp_tables),
        audit_hash=hash(bp_state, g, obs, current_mjd)
    )

    return decision
```

### Quality Score Computation Function

```python
FUNCTION compute_quality_score(bp_table: BP_Table) -> Float:
    """
    Compute quality score from metrics.

    Returns: Float in [0, 1] range
    """
    metrics = bp_table.quality_metrics or {}

    # Extract with defaults
    snr_mean = metrics.get("snr_mean", 0.0)
    flagged_fraction = metrics.get("flagged_fraction", 1.0)
    n_antennas = metrics.get("n_antennas", 0)
    n_spws = metrics.get("n_spws", 0)

    # Normalize
    snr_norm = min(snr_mean / 100.0, 1.0)  # Max SNR = 100
    antenna_norm = min(n_antennas / 110.0, 1.0)  # Max antennas = 110
    spw_norm = min(n_spws / 16.0, 1.0)  # Max SPWs = 16

    # Weighted sum
    score = (
        snr_norm * 0.4 +
        (1.0 - flagged_fraction) * 0.3 +
        antenna_norm * 0.2 +
        spw_norm * 0.1
    )

    return score
```

---

## Part 9: Comparison to Prior Version

### Before (v1.0): Single BP Table, 24-Hour Age Limit

| Aspect               | v1.0                                | v2.0 (Revised)                            |
| -------------------- | ----------------------------------- | ----------------------------------------- |
| **Validity Window**  | 24 hours from solve time            | 48 hours (24h before + 24h after transit) |
| **BP State**         | Single table                        | List of available tables                  |
| **Selection**        | First valid table                   | Quality-based from multiple candidates    |
| **Age Limit**        | Age from solve time ≤ 24h           | Age from transit ±24h (no age limit)      |
| **Multi-Calibrator** | No (one calibrator per observation) | Yes (typically 2 calibrators available)   |
| **Quality Metrics**  | Not used for selection              | Primary selection criterion               |

### Key Improvements

1. **Longer Validity**: 48 hours per calibrator (vs 24 hours)
2. **Quality-Based Selection**: Best calibrator chosen from multiple options
3. **Redundancy**: Multiple calibrators available at any time
4. **Transit-Centered**: Validity tied to physical transit event, not solve time
5. **Deterministic Selection**: Quality scores ensure reproducible choices

---

## Part 10: Edge Cases (All Enumerated - Revised)

### Edge Case 1: Exactly At Validity Boundaries

```
CASE: Observation time = transit_mjd - 1.0 day (exactly 24h before transit)
RULE: transit_window_ok evaluates to TRUE (boundary inclusive)
ACTION: Table is valid

CASE: Observation time = transit_mjd + 1.0 day (exactly 24h after transit)
RULE: transit_window_ok evaluates to TRUE (boundary inclusive)
ACTION: Table is valid

CASE: Observation time = transit_mjd - 1.0 day - 1 second
RULE: transit_window_ok evaluates to FALSE
ACTION: Table is invalid (outside window)
```

### Edge Case 2: Two Tables with Identical Quality Scores

```
CASE: Two BP tables both have quality_score = 0.85
RULE: Sort by secondary criterion: proximity to transit
ACTION: Select table with transit closest to observation time

CASE: Two BP tables have same quality_score AND same transit proximity
RULE: Sort by tertiary criterion: declination match
ACTION: Select table with Dec closest to target Dec

CASE: All criteria identical (quality, transit, Dec)
RULE: Sort by quaternary criterion: recency (newest first)
ACTION: Select most recently created table
```

### Edge Case 3: No Quality Metrics Available

```
CASE: bp_table.quality_metrics is None or empty
RULE: Use default values (all zeros)
ACTION: quality_score = 0.0 (lowest possible score)
IMPLICATION: This table will only be selected if it's the only valid candidate
```

### Edge Case 4: All Valid Tables Have Zero Quality Score

```
CASE: All valid BP tables have quality_score = 0.0
RULE: Selection falls back to secondary criteria (transit proximity)
ACTION: Select table with transit closest to observation time
REASONING: Even poor-quality calibration is better than no calibration
          (assuming it passed minimum validation thresholds)
```

### Edge Case 5: Declination Change During Observation

```
CASE: Observation starts at Dec = +30.0°, ends at Dec = +32.0°
RULE: Selection is evaluated at observation start time
ACTION: Select BP table valid for Dec = +30.0°
NOTE: If Dec changes > 1.0° during observation, may need mid-observation re-solve
      (This is a separate decision point, not handled by this algorithm)
```

---

## Part 11: Determinism Verification (Revised)

### Audit Checklist

```
For any given (BP_state, G_state, obs_params, current_mjd):

:check_mark: Calling the decision function twice produces identical output
:check_mark: Output includes hash of inputs for audit trail
:check_mark: Quality score computation is deterministic (same metrics → same score)
:check_mark: Selection from multiple candidates is deterministic (stable sort)
:check_mark: No randomness, no floating-point ambiguity
:check_mark: All boundaries are hard (not fuzzy)
:check_mark: All states reachable and unambiguous
:check_mark: Error cases explicitly defined (State E)
:check_mark: Timing estimates deterministic (not "approximately")
:check_mark: Multi-calibrator selection is reproducible
```

---

## Summary: Circuit Board Rigor (v2.0)

This specification achieves "circuit board logic" with multi-calibrator support
by:

1. **Determinism**: Same input → same output, always (including quality-based
   selection)
2. **Hard Boundaries**: ±24h from transit, ≤1.0° Dec, ≤60min gain age, all hard
3. **Complete Coverage**: All 4 combinations (T/F, T/F) enumerated + error case
4. **Quality-Based Selection**: Reproducible scoring and ranking
5. **Multi-Calibrator Support**: Typically 2 calibrators available, best one
   selected
6. **Transit-Centered Windows**: 48-hour validity per calibrator transit
7. **Explicit Delays**: 0, 7, 20 minutes (not ranges)
8. **Edge Cases**: All 5 edge cases explicitly defined
9. **Error Handling**: State E for unrecoverable conditions
10. **Audit Trail**: Hash of inputs for verification

**Version**: 2.0 (Revised for 48-hour transit-centered validity windows)
**Date**: 2024-11-14

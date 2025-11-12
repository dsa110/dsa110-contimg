# Refant Validation Failure Behavior

**Date:** 2025-11-02  
**Question:** What happens when refant validation fails?

## Current Behavior

When refant validation fails (reference antenna has no solutions in calibration table):

### 1. Error Flow

**`validate_caltable_compatibility()` (validate.py:174-178):**
```python
if refant_int not in cal_antennas:
    raise ValueError(
        f"Reference antenna {refant_int} has no solutions in calibration table: "
        f"{caltable_path}. Available antennas: {sorted(cal_antennas)}"
    )
```

**`solve_bandpass()` (calibration.py:274-283):**
```python
warnings = validate_caltable_compatibility(ktable, ms, refant=refant_int)
# ValueError is caught and re-raised:
except (FileNotFoundError, ValueError) as e:
    raise ValueError(
        f"K-table validation failed. This is a required precondition for "
        f"bandpass calibration. Error: {e}"
    ) from e
```

**`solve_gains()` (calibration.py:398-405):**
```python
validate_caltables_for_use(required_tables, ms, require_all=True, refant=refant_int)
# ValueError is caught and re-raised:
except (FileNotFoundError, ValueError) as e:
    raise ValueError(
        f"Calibration table validation failed. This is a required precondition for "
        f"gain calibration. Error: {e}"
    ) from e
```

### 2. Result

**Calibration stops immediately:**
- No calibration tables are created
- No fallback refant selection
- Error propagates to caller (CLI or API)
- Error message includes:
  - Which refant failed
  - Which calibration table was being validated
  - Available antennas in the caltable

### 3. Error Message Example

```
ValueError: K-table validation failed. This is a required precondition for 
bandpass calibration. Error: Reference antenna 103 has no solutions in calibration 
table: /path/to/ms_field_0_kcal. Available antennas: [0, 1, 2, 3, 5, 7]
```

## When This Happens

**Scenario 1: Refant antenna was flagged during K-calibration**
- K-calibration completes, but refant 103 has all solutions flagged
- Bandpass calibration tries to use K-table with refant 103
- Validation fails because refant 103 has no valid solutions

**Scenario 2: Refant antenna not present in calibration data**
- K-calibration was done on a subset of antennas
- Refant 103 was not included in the calibration
- Subsequent calibration steps fail

**Scenario 3: Wrong refant specified**
- User specified refant 999, but calibration table only has antennas 0-7
- Validation fails immediately

## Current Limitations

### No Fallback Behavior

**Current:** Calibration fails immediately with clear error message

**Missing:**
- No automatic refant reselection from available antennas
- No suggestion of alternative refant
- No attempt to find a valid refant from the caltable

### No Refant Validation in `apply_to_target()`

**Current:** `apply_to_target()` doesn't validate refant (because refant is only needed during solve, not apply)

**This is correct:** Refant validation is only needed when using calibration tables in `gaintable` parameter during solve operations.

## Potential Improvements

### Option 1: Suggest Alternative Refant

When refant validation fails, suggest the first available antenna from the caltable:

```python
if refant_int not in cal_antennas:
    if cal_antennas:
        suggested_refant = sorted(cal_antennas)[0]
        raise ValueError(
            f"Reference antenna {refant_int} has no solutions in calibration table: "
            f"{caltable_path}. Available antennas: {sorted(cal_antennas)}. "
            f"Consider using refant={suggested_refant} instead."
        )
    else:
        raise ValueError(...)
```

### Option 2: Auto-Reselect Refant

Automatically select a valid refant from the caltable:

```python
if refant_int not in cal_antennas:
    if cal_antennas:
        new_refant = sorted(cal_antennas)[0]
        logger.warning(
            f"Reference antenna {refant_int} has no solutions. "
            f"Auto-selecting refant={new_refant} from available antennas: {sorted(cal_antennas)}"
        )
        refant_int = new_refant
    else:
        raise ValueError(...)
```

**Problem:** This violates "measure twice, cut once" - we'd be silently changing user input.

### Option 3: Fail Fast (Current Behavior) ✓ RECOMMENDED

**Current behavior is correct:**
- Fails fast with clear error message
- Provides available antennas for user to choose
- Follows "measure twice, cut once" - user must explicitly fix the issue
- Prevents silent failures or unexpected behavior

## Recommendation

**Keep current behavior** (fail fast with clear error), but **enhance error message** to:
1. Suggest a valid refant from available antennas
2. Provide context about why refant might be missing (flagged, not in calibration, etc.)

This gives users actionable information without silently changing their input.


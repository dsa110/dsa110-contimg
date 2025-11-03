# Calibration Reference

## Overview

The DSA-110 calibration pipeline performs bandpass (BP) and gain (G) calibration by default. **K-calibration (delay calibration) is skipped by default** for DSA-110, following VLA/ALMA practice for connected-element arrays with short baselines.

## Calibration Stages

### K-Calibration (Delay) - **Optional**

**Status**: Skipped by default for DSA-110

**Rationale**: 
- DSA-110 is a connected-element array with a 2.6 km maximum baseline
- Following VLA/ALMA practice: residual delays (< 0.5 ns) are absorbed into complex gain calibration
- K-calibration is primarily needed for VLBI arrays (thousands of km baselines, independent atomic clocks)

**When to Enable**:
- Use `--do-k` flag to explicitly enable K-calibration if needed
- Typically only required for VLBI observations or if explicit delay measurements are needed

**Example**:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /path/to/ms \
  --field 0 \
  --refant 103 \
  --do-k  # Explicitly enable K-calibration
```

### Bandpass Calibration (BP) - **Standard**

**Status**: Enabled by default

**Purpose**: Corrects frequency-dependent amplitude and phase variations across the observing band

**Example**:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /path/to/ms \
  --field 0 \
  --refant 103 \
  # BP calibration runs by default
```

### Gain Calibration (G) - **Standard**

**Status**: Enabled by default

**Purpose**: Corrects time-dependent phase and amplitude variations (atmospheric effects, instrumental drifts)

**Example**:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /path/to/ms \
  --field 0 \
  --refant 103 \
  # Gain calibration runs by default
```

## Default Behavior

By default, the calibration CLI performs:
- ✓ Bandpass calibration
- ✓ Gain calibration
- ✗ K-calibration (skipped)

This matches VLA/ALMA practice for connected-element arrays.

## Command-Line Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `--do-k` | Enable K-calibration (delay) | Disabled |
| `--skip-bp` | Skip bandpass calibration | Enabled |
| `--skip-g` | Skip gain calibration | Enabled |
| `--combine-spw` | Combine SPWs during calibration | Separate SPWs |
| `--fast` | Fast path: subset MS, phase-only gains | Full calibration |

## Scientific Background

### Why Skip K-Calibration for DSA-110?

**Connected-Element Array Characteristics**:
- Shared frequency reference (no clock drift delays)
- Short baselines (< 100 km) → atmospheric delays partially cancel
- Known instrumental delays incorporated into correlator model
- Residual delays < 0.5 ns → absorbed into complex gain calibration

**VLBI vs Connected Arrays**:
- **VLBI** (thousands of km baselines): Requires explicit K-calibration (fringe fitting)
- **Connected arrays** (tens of km baselines): K-calibration not necessary

See `docs/reports/K_CAL_VLBI_VS_CONNECTED_ARRAYS.md` for detailed technical explanation.

## Related Documentation

- [Calibration Tutorial](tutorials/calibrate-apply.md) - Step-by-step workflow
- [Memory](reports/memory.md) - Project-specific notes and practices
- [K-Calibration Research](reports/K_CALIBRATION_NEED_REASSESSMENT.md) - Detailed analysis
- [VLBI vs Connected Arrays](reports/K_CAL_VLBI_VS_CONNECTED_ARRAYS.md) - Technical comparison


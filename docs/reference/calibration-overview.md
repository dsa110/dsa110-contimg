# Calibration Reference

## Overview

The DSA-110 calibration pipeline performs bandpass (BP) and gain (G) calibration
by default. **K-calibration (delay calibration) is skipped by default** for
DSA-110, following VLA/ALMA practice for connected-element arrays with short
baselines.

## Calibration Stages

### K-Calibration (Delay) - **Optional**

**Status**: Skipped by default for DSA-110

**Rationale**:

- DSA-110 is a connected-element array with a 2.6 km maximum baseline
- Following VLA/ALMA practice: residual delays (< 0.5 ns) are absorbed into
  complex gain calibration
- K-calibration is primarily needed for VLBI arrays (thousands of km baselines,
  independent atomic clocks)

**When to Enable**:

- Use `--do-k` flag to explicitly enable K-calibration if needed
- Typically only required for VLBI observations or if explicit delay
  measurements are needed

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

**Purpose**: Corrects frequency-dependent amplitude and phase variations across
the observing band

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

**Purpose**: Corrects time-dependent phase and amplitude variations (atmospheric
effects, instrumental drifts)

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

This matches VLA/ALMA practice for connected-element arrays. For bandpass, no
implicit UV range cut is applied; provide `--uvrange` explicitly or set a
site-wide default via `CONTIMG_CAL_BP_UVRANGE`.

## Command-Line Flags

| Flag                 | Purpose                                   | Default                                    |
| -------------------- | ----------------------------------------- | ------------------------------------------ |
| `--do-k`             | Enable K-calibration (delay)              | Disabled                                   |
| `--skip-bp`          | Skip bandpass calibration                 | Enabled                                    |
| `--skip-g`           | Skip gain calibration                     | Enabled                                    |
| `--combine-spw`      | Combine SPWs during calibration           | Separate SPWs                              |
| `--fast`             | Fast path: subset MS, phase-only gains    | Full calibration                           |
| `--bp-combine-field` | Combine selected fields when solving BP/G | Off                                        |
| `--bp-minsnr`        | Bandpass min SNR threshold                | 3.0 (env `CONTIMG_CAL_BP_MINSNR`)          |
| `--uvrange`          | UV range selection for solves             | none (env `CONTIMG_CAL_BP_UVRANGE` if set) |
| `--bp-smooth-type`   | Post-solve BP smoothing type              | none                                       |
| `--bp-smooth-window` | Smoothing window (channels)               | —                                          |
| `--flagging-mode`    | Pre-solve flagging: none, zeros, rfi      | zeros                                      |
| `--prebp-phase`      | Run phase-only solve before bandpass      | Off                                        |
| `--prebp-solint`     | Pre-BP phase solint                       | inf                                        |
| `--prebp-minsnr`     | Pre-BP phase min SNR                      | 5.0                                        |
| `--prebp-uvrange`    | Pre-BP phase uvrange                      | none                                       |
| `--gain-solint`      | Gain solution interval                    | inf                                        |
| `--gain-calmode`     | Gain cal mode: ap, p, a                   | ap                                         |
| `--gain-minsnr`      | Gain min SNR threshold                    | 3.0                                        |

## Scientific Background

### Why Skip K-Calibration for DSA-110?

**Connected-Element Array Characteristics**:

- Shared frequency reference (no clock drift delays)
- Short baselines (< 100 km) → atmospheric delays partially cancel
- Known instrumental delays incorporated into correlator model
- Residual delays < 0.5 ns → absorbed into complex gain calibration

**VLBI vs Connected Arrays**:

- **VLBI** (thousands of km baselines): Requires explicit K-calibration (fringe
  fitting)
- **Connected arrays** (tens of km baselines): K-calibration not necessary

See the calibration procedure documentation for detailed technical explanation.

## Related Documentation

- [Calibration Tutorial](../guides/tutorials/calibrate-apply.md) - Step-by-step
  workflow
- Memory - Project-specific notes and practices
- [Calibration Procedure](CURRENT_CALIBRATION_PROCEDURE.md) - Current
  calibration methodology

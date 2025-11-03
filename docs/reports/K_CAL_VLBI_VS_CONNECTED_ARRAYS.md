# K-Calibration: VLBI vs Connected-Element Arrays

**Date:** 2025-11-03  
**Source:** Perplexity research verification  
**Status:** Research complete

## Executive Summary

**K-calibration (delay calibration) is necessary for VLBI arrays but NOT for connected-element arrays like DSA-110, VLA, or ALMA.** DSA-110 should follow VLA/ALMA practice and skip K-calibration by default.

## Key Distinction

### Connected-Element Arrays (VLA, ALMA, DSA-110):
- **Baseline lengths:** < 100 km (VLA: ~36 km max, ALMA: ~16 km max, DSA-110: 2.6 km max)
- **Frequency reference:** Shared/common reference distributed via cable to all antennas
- **Signal paths:** Known, calibrated, incorporated into correlator model
- **Atmospheric delays:** Partially cancel between nearby antennas
- **Result:** Residual delays typically < 0.5 ns → **absorbed into complex gain calibration**
- **K-calibration:** **NOT necessary** (VLA and ALMA don't do it)

### VLBI Arrays (VLBA, EVN, global VLBI):
- **Baseline lengths:** Thousands of kilometers (VLBA: ~8,611 km max)
- **Frequency reference:** Independent atomic clocks (hydrogen masers) at each station
- **Signal paths:** Recorded separately, brought together post-observation
- **Atmospheric delays:** Don't cancel (stations too far apart)
- **Result:** Delays routinely > 0.5 ns → **explicit K-calibration (fringe fitting) mandatory**
- **K-calibration:** **Essential** (performed multiple times per observation)

## Physical Basis

### 1. Decorrelation Threshold
For GHz-bandwidth observations:
- **Delays > 0.5 ns** cause signal decorrelation when frequencies are averaged
- **Delays < 0.5 ns** are tolerable and absorbed into gain calibration

### 2. Delay Error Sources

**On Short Baselines (Connected Arrays):**
- Atmospheric delays: **Partially cancel** between nearby antennas (< 100 km)
- Clock drift: **Eliminated** by shared frequency reference
- Instrumental delays: **Known and incorporated** into correlator model
- **Result:** Residual delays typically < 0.5 ns

**On Long Baselines (VLBI):**
- Atmospheric delays: **Don't cancel** (stations thousands of km apart)
- Clock drift: **Significant** (independent atomic clocks drift ~1 ns/day)
- Instrumental delays: **Unknown** until post-correlation analysis
- **Result:** Delays routinely > 0.5 ns, often >> 1 ns

### 3. Mathematical Relationship

Delay error decorrelation phase: `Δφ = 2π × bandwidth × delay_error`

For a 1 GHz bandwidth:
- Delay = 0.1 ns → Phase error = 0.63 radians (tolerable)
- Delay = 0.5 ns → Phase error = 3.14 radians (decorrelation threshold)
- Delay = 1.0 ns → Phase error = 6.28 radians (severe decorrelation)

## DSA-110 Characteristics

- **Maximum baseline:** 2.6 km
- **Observing frequency:** 1.4 GHz (1280-1530 MHz)
- **Array type:** Connected-element array
- **Baseline category:** Short baseline (< 100 km threshold)

**Conclusion:** DSA-110 is similar to VLA/ALMA (closely spaced, connected-element), NOT VLBI (very long baseline, independent stations). Therefore, **DSA-110 should skip K-calibration by default**, following VLA/ALMA practice.

## References

Based on Perplexity research verification (2025-11-03) using:
- NRAO VLA Observing Guide
- ALMA Interferometry Documentation  
- VLBI fringe-fitting documentation
- Baseline length comparisons
- Delay calibration thresholds


# Variability Metrics

**Purpose:** Definitions and mathematical formulation of variability metrics
used in the pipeline  
**Last Updated:** 2025-11-18  
**Status:** Production

---

## Overview

The DSA-110 continuum imaging pipeline employs a suite of statistical metrics to
identify variable sources and potential Extreme Scattering Events (ESEs). These
metrics are calculated on a per-source basis using the
`dsa110_contimg.photometry.variability` module.

## Absolute Flux Metrics

These metrics operate on the absolute flux densities (calibrated to the NVSS
scale).

### 1. $\eta$ Metric (Weighted Variance)

The $\eta$ metric measures whether the scatter in a source's light curve is
consistent with the measurement errors. It is adopted from the VAST survey
(Variables and Slow Transients).

**Formula:** $$ \eta = \frac{N}{N-1} \left( \overline{w f^2} -
\frac{(\overline{w f})^2}{\overline{w}} \right) $$

Where:

- $N$: Number of measurements
- $f$: Flux measurements
- $w = 1/\sigma^2$: Weights (inverse variance)

**Interpretation:**

- $\eta \approx 1$: Source is stable (scatter dominated by thermal noise).
- $\eta \gg 1$: Source is variable (intrinsic variability exceeds noise).

### 2. $V_S$ Metric (Two-Epoch Statistic)

The $V_S$ metric is a t-statistic that compares flux measurements between two
specific epochs (e.g., $t_1$ and $t_2$).

**Formula:** $$ V_S = \frac{f_1 - f_2}{\sqrt{\sigma_1^2 + \sigma_2^2}} $$

**Interpretation:**

- $|V_S| > 3$: Significant change (>3$\sigma$) between the two epochs.
- Useful for detecting sudden flares or dropouts.

### 3. Sigma Deviation

This metric quantifies the maximum excursion of a light curve from its mean, in
units of standard deviation.

**Formula:** $$ \sigma*{dev} = \max \left( \frac{|f*{max} - \mu|}{\sigma*{std}},
\frac{|f*{min} - \mu|}{\sigma\_{std}} \right) $$

**Interpretation:**

- High $\sigma_{dev}$ indicates a single outlier epoch (e.g., a fast transient
  event).

---

## Relative Flux Metrics

To mitigate systematic calibration errors (e.g., ionospheric effects, gain
drifts) that affect all sources in a field simultaneously, we utilize **Relative
Flux** metrics.

### 4. Relative Flux Ratio

This method references the target source against a weighted ensemble of stable
neighboring sources in the same field.

**Formula:** $$ F*{rel}(t) = \frac{F*{target}(t)}{\sum*{i=1}^{k} w_i
F*{neighbor, i}(t)} $$

Where:

- $F_{target}(t)$: Flux of the target source at time $t$
- $F_{neighbor, i}(t)$: Flux of the $i$-th neighbor at time $t$
- $w_i$: Normalized weight for the $i$-th neighbor ($\sum w_i = 1$)

**Implementation Details:**

- **Function:** `calculate_relative_flux`
- **Weighted Neighbors:** Neighbors can be weighted by their stability or SNR.
  If weights are not provided, equal weights are used.
- **Robustness:**
  - Handles missing data (`NaN`) by re-normalizing weights for the subset of
    valid neighbors at each epoch.
  - Reduces common-mode systematic noise, allowing for detection of fainter
    intrinsic variability.

**Usage:** This metric is preferred for long-term monitoring campaigns where
systematic stability is the limiting factor for sensitivity.

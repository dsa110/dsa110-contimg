# Quick Start: Reaching 100% Confidence

## Fastest Path to 100% Confidence

This document provides the **minimum viable implementation** to reach 100%
confidence in both pipeline testing and science validation.

---

## Pipeline Testing: 95% → 100% (5% gap)

### Quick Wins (2-3 days)

#### 1. Edge Case Testing Suite (1 day)

**File:** `tests/unit/simulation/test_edge_cases_comprehensive.py`

```python
"""Comprehensive edge case testing for synthetic data generation."""

import pytest
import numpy as np
from dsa110_contimg.simulation.make_synthetic_uvh5 import *
from dsa110_contimg.simulation.visibility_models import *

class TestExtremeParameters:
    """Test extreme parameter values."""

    def test_very_small_flux(self):
        """Test flux near zero."""
        # Test flux = 1e-6 Jy
        pass

    def test_very_large_flux(self):
        """Test very bright sources."""
        # Test flux = 1e6 Jy
        pass

    def test_very_extended_source(self):
        """Test source larger than field of view."""
        # Test size = 1000 arcsec
        pass

    def test_extreme_calibration_errors(self):
        """Test very large calibration errors."""
        # Test gain_std = 1.0, phase_std = 180°
        pass

class TestAntennaConfigurations:
    """Test edge cases in antenna configurations."""

    def test_minimum_antennas(self):
        """Test with 2-3 antennas (minimum for interferometry)."""
        pass

    def test_maximum_antennas(self):
        """Test with 110+ antennas."""
        pass

    def test_single_baseline(self):
        """Test with only one baseline."""
        pass

class TestTimeFrequencyEdgeCases:
    """Test edge cases in time/frequency."""

    def test_single_integration(self):
        """Test with only one time integration."""
        pass

    def test_single_channel(self):
        """Test with only one frequency channel."""
        pass

    def test_very_long_time_series(self):
        """Test with 24+ hours of data."""
        pass

class TestCoordinateEdgeCases:
    """Test edge cases in coordinates."""

    def test_north_pole(self):
        """Test at dec = +90°."""
        pass

    def test_south_pole(self):
        """Test at dec = -90°."""
        pass

    def test_equator(self):
        """Test at dec = 0°."""
        pass
```

**Confidence Gain:** +2% (95% → 97%)

---

#### 2. Performance Testing Suite (1 day)

**File:** `tests/performance/test_synthetic_data_performance.py`

```python
"""Performance testing for synthetic data generation."""

import pytest
import time
import psutil
import numpy as np
from pathlib import Path

class TestGenerationPerformance:
    """Test generation performance with realistic data volumes."""

    def test_large_dataset_generation(self):
        """Test generation with 100+ subbands."""
        # Measure time and memory
        pass

    def test_many_integrations(self):
        """Test with 1000+ time integrations."""
        pass

    def test_memory_usage(self):
        """Profile memory usage for large arrays."""
        pass

    def test_generation_scaling(self):
        """Test how generation time scales with data volume."""
        pass
```

**Confidence Gain:** +2% (97% → 99%)

---

#### 3. Concurrent Generation Test (0.5 day)

**File:** `tests/integration/test_concurrent_generation.py`

```python
"""Test concurrent generation scenarios."""

import pytest
import multiprocessing
from pathlib import Path

def test_concurrent_uvh5_generation():
    """Test generating multiple UVH5 files in parallel."""
    pass

def test_thread_safety():
    """Test random number generator thread safety."""
    pass
```

**Confidence Gain:** +1% (99% → 100%)

---

## Science Validation: 70% → 100% (30% gap)

### Critical Features (10-12 days)

#### 1. Multi-Source Fields (2-3 days) - **START HERE**

**Why First:** Enables crowded field testing, source confusion scenarios, and
realistic source counts.

**Implementation:**

**File:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`

```python
# Add to parse_args():
parser.add_argument(
    "--n-sources",
    type=int,
    default=1,
    help="Number of sources in field (default: 1)",
)
parser.add_argument(
    "--source-distribution",
    type=str,
    choices=["uniform", "clustered", "grid"],
    default="uniform",
    help="Source position distribution (default: uniform)",
)
parser.add_argument(
    "--flux-distribution",
    type=str,
    choices=["powerlaw", "uniform", "custom"],
    default="powerlaw",
    help="Source flux distribution (default: powerlaw)",
)

# Update write_subband_uvh5() to handle multiple sources:
def write_subband_uvh5(
    ...,
    n_sources: int = 1,
    source_distribution: str = "uniform",
    flux_distribution: str = "powerlaw",
    ...
):
    """Generate visibilities for multiple sources."""
    # Generate source positions
    if n_sources > 1:
        source_positions = generate_source_positions(
            n_sources, source_distribution, config
        )
        source_fluxes = generate_source_fluxes(
            n_sources, flux_distribution, amplitude_jy
        )
        # Sum visibilities from all sources
        vis = sum_sources_visibilities(
            source_positions, source_fluxes, u_lambda, v_lambda, ...
        )
    else:
        # Single source (existing code)
        ...
```

**File:** `src/dsa110_contimg/simulation/visibility_models.py`

```python
def sum_sources_visibilities(
    source_positions: List[Tuple[float, float]],
    source_fluxes: List[float],
    u_lambda: np.ndarray,
    v_lambda: np.ndarray,
    source_model: str = "point",
    ...
) -> np.ndarray:
    """Sum visibilities from multiple sources."""
    total_vis = np.zeros_like(u_lambda, dtype=complex)
    for (ra, dec), flux in zip(source_positions, source_fluxes):
        # Calculate u,v offset for this source
        u_offset, v_offset = calculate_uv_offset(ra, dec, phase_center)
        # Generate visibility for this source
        vis = generate_source_visibility(...)
        total_vis += vis
    return total_vis
```

**Tests:** `tests/unit/simulation/test_multi_source.py`

**Confidence Gain:** +5% (70% → 75%)

---

#### 2. Spectral Index (2-3 days)

**Why Second:** Critical for multi-frequency science, flux calibration
validation.

**Implementation:**

**File:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`

```python
parser.add_argument(
    "--spectral-index",
    type=float,
    default=None,
    help="Spectral index α (S ∝ ν^α), default: -0.7 (synchrotron)",
)

# In write_subband_uvh5():
def write_subband_uvh5(
    ...,
    spectral_index: Optional[float] = None,
    ...
):
    """Generate frequency-dependent flux."""
    if spectral_index is None:
        spectral_index = -0.7  # Default synchrotron

    # Calculate flux per frequency channel
    reference_freq = config.reference_frequency_hz
    for freq_idx, freq_hz in enumerate(freq_array):
        flux_ratio = (freq_hz / reference_freq) ** spectral_index
        channel_flux = amplitude_jy * flux_ratio
        # Generate visibility with channel-specific flux
        ...
```

**File:** `src/dsa110_contimg/simulation/visibility_models.py`

```python
def apply_spectral_index(
    visibilities: np.ndarray,
    freq_array: np.ndarray,
    reference_freq: float,
    spectral_index: float,
) -> np.ndarray:
    """Apply spectral index to visibilities."""
    for freq_idx, freq_hz in enumerate(freq_array):
        flux_ratio = (freq_hz / reference_freq) ** spectral_index
        visibilities[:, :, freq_idx, :] *= flux_ratio
    return visibilities
```

**Tests:** `tests/unit/simulation/test_spectral_index.py`

**Confidence Gain:** +5% (75% → 80%)

---

#### 3. Time Variability (2-3 days)

**Why Third:** Important for variability studies, ESE detection testing.

**Implementation:**

**File:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`

```python
parser.add_argument(
    "--variability-model",
    type=str,
    choices=["constant", "linear", "sinusoidal", "exponential", "random_walk"],
    default="constant",
    help="Time variability model (default: constant)",
)
parser.add_argument(
    "--variability-params",
    type=float,
    nargs="+",
    default=None,
    help="Variability model parameters",
)

# In write_subband_uvh5():
def write_subband_uvh5(
    ...,
    variability_model: str = "constant",
    variability_params: Optional[List[float]] = None,
    ...
):
    """Generate time-dependent flux."""
    for time_idx, time_mjd in enumerate(time_array):
        flux_at_time = calculate_flux_at_time(
            amplitude_jy, time_mjd, variability_model, variability_params
        )
        # Generate visibility with time-specific flux
        ...
```

**File:** `src/dsa110_contimg/simulation/visibility_models.py`

```python
def calculate_flux_at_time(
    base_flux: float,
    time_mjd: float,
    model: str,
    params: Optional[List[float]],
) -> float:
    """Calculate flux at specific time based on variability model."""
    if model == "constant":
        return base_flux
    elif model == "linear":
        rate = params[0] if params else 0.0
        return base_flux + rate * (time_mjd - reference_time)
    elif model == "sinusoidal":
        amplitude = params[0] if params else 0.0
        period = params[1] if params else 1.0
        return base_flux + amplitude * np.sin(2 * np.pi * time_mjd / period)
    # ... other models
```

**Tests:** `tests/unit/simulation/test_time_variability.py`

**Confidence Gain:** +5% (80% → 85%)

---

#### 4. Enhanced Catalog Generation (2-3 days)

**Why Fourth:** Realistic source counts and density.

**Implementation:**

**File:** `src/dsa110_contimg/simulation/synthetic_catalog.py`

```python
def create_synthetic_catalog_db(
    ...,
    catalog_density: str = "normal",  # "sparse", "normal", "crowded"
    n_background_sources: Optional[int] = None,
    ...
):
    """Create catalog with realistic source density."""
    if catalog_density == "sparse":
        # Current behavior (few sources)
    elif catalog_density == "normal":
        # ~100 sources per square degree
        n_sources = int(100 * field_area_deg2)
    elif catalog_density == "crowded":
        # ~1000 sources per square degree
        n_sources = int(1000 * field_area_deg2)

    # Generate source positions
    # Generate flux distribution (power law)
    # Create catalog entries
```

**Tests:** `tests/unit/simulation/test_catalog_density.py`

**Confidence Gain:** +5% (85% → 90%)

---

#### 5. Complex Morphologies (3-4 days)

**Why Fifth:** Realistic source shapes beyond point/Gaussian/disk.

**Implementation:**

**File:** `src/dsa110_contimg/simulation/visibility_models.py`

```python
def double_source_visibility(
    u_lambda: np.ndarray,
    v_lambda: np.ndarray,
    amplitude_jy: float,
    separation_arcsec: float,
    position_angle_deg: float,
) -> np.ndarray:
    """Visibility for double source (two point sources)."""
    # Two point sources with separation
    ...

def ring_source_visibility(
    u_lambda: np.ndarray,
    v_lambda: np.ndarray,
    amplitude_jy: float,
    radius_arcsec: float,
) -> np.ndarray:
    """Visibility for uniform ring source."""
    # Bessel function J₀ for ring
    rho = np.sqrt(u_lambda**2 + v_lambda**2)
    radius_rad = np.deg2rad(radius_arcsec / 3600.0)
    arg = 2.0 * np.pi * radius_rad * rho
    return amplitude_jy * j0(arg)  # J₀ Bessel function
```

**Tests:** `tests/unit/simulation/test_complex_morphologies.py`

**Confidence Gain:** +5% (90% → 95%)

---

#### 6. RFI Simulation (3-4 days)

**Why Last:** Important but can be added after core features.

**Implementation:**

**File:** `src/dsa110_contimg/simulation/visibility_models.py`

```python
def add_rfi_contamination(
    visibilities: np.ndarray,
    rfi_type: str = "narrowband",
    rfi_strength: float = 10.0,  # Multiple of noise
    rfi_freq_channels: Optional[List[int]] = None,
    rfi_time_indices: Optional[List[int]] = None,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Add RFI contamination to visibilities."""
    # Inject strong signals at specified channels/times
    ...
```

**Tests:** `tests/unit/simulation/test_rfi_simulation.py`

**Confidence Gain:** +5% (95% → 100%)

---

## Implementation Order

### Week 1: Pipeline Testing → 100%

1. Edge case testing (1 day)
2. Performance testing (1 day)
3. Concurrent generation (0.5 day)

**Result:** Pipeline Testing = 100%

### Week 2-3: Science Validation → 100%

1. Multi-source fields (2-3 days)
2. Spectral index (2-3 days)
3. Time variability (2-3 days)
4. Enhanced catalogs (2-3 days)

**Result:** Science Validation = 85%

### Week 4: Final Features

5. Complex morphologies (3-4 days)
6. RFI simulation (3-4 days)

**Result:** Science Validation = 100%

---

## Quick Validation After Each Feature

```bash
# After each feature implementation:
# 1. Run tests
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/simulation -v

# 2. Generate test dataset
python src/dsa110_contimg/simulation/make_synthetic_uvh5.py \
    --template-free \
    --output /tmp/test_new_feature \
    --[new-feature-flag] \
    --create-catalog

# 3. Run pipeline
python -m dsa110_contimg.pipeline.adapter \
    --input /tmp/test_new_feature/*.uvh5

# 4. Verify results
python -c "
from dsa110_contimg.database.products import get_products_db
import pandas as pd
conn = get_products_db()
# Check results
"
```

---

## Success Metrics

### Pipeline Testing: 100%

- ✅ All edge cases pass
- ✅ Performance benchmarks documented
- ✅ Memory usage acceptable
- ✅ Concurrent generation works

### Science Validation: 100%

- ✅ Multi-source fields work
- ✅ Spectral index implemented
- ✅ Time variability works
- ✅ Complex morphologies available
- ✅ Enhanced catalogs realistic
- ✅ RFI simulation implemented

---

## Related Documentation

- `docs/dev/ROADMAP_TO_100_PERCENT_CONFIDENCE.md` - Full roadmap
- `docs/analysis/SYNTHETIC_DATA_CONFIDENCE_ASSESSMENT.md` - Current confidence
- `docs/analysis/SYNTHETIC_DATA_PIPELINE_STAGE_COVERAGE.md` - Coverage details

# DSA-110 Continuum Imaging - Simulation Suite

This directory contains simulations, test scenarios, and validation notebooks
for the DSA-110 continuum imaging pipeline.

## Directory Structure

```
simulations/
├── README.md                          # This file
├── notebooks/                         # Interactive simulation notebooks
│   ├── 01_uvh5_generation.ipynb       # Generate synthetic UVH5 test data
│   ├── 02_forced_photometry_validation.ipynb  # Validate forced photometry accuracy
│   ├── 03_calibration_scenarios.ipynb # Test calibration with various conditions
│   └── 04_imaging_parameter_sweep.ipynb       # Imaging parameter optimization
├── scripts/                           # Reusable simulation scripts
│   ├── generate_synthetic_obs.py      # CLI tool for synthetic observation generation
│   ├── inject_sources.py              # Source injection for completeness testing
│   └── run_parameter_sweep.py         # Batch parameter sweep runner
├── config/                            # Simulation configurations
│   ├── scenarios/                     # Pre-defined test scenarios
│   │   ├── bright_calibrator.yaml     # Strong calibrator, good conditions
│   │   ├── weak_sources.yaml          # Low SNR source recovery
│   │   ├── crowded_field.yaml         # Blended sources
│   │   └── rfi_contaminated.yaml      # RFI mitigation testing
│   └── defaults.yaml                  # Default simulation parameters
└── data/                              # Simulation outputs (gitignored)
    ├── synthetic_uvh5/                # Generated UVH5 files
    ├── synthetic_ms/                  # Converted Measurement Sets
    ├── synthetic_images/              # Resulting images
    └── results/                       # Analysis results and metrics
```

## Purpose

This suite provides:

1. **End-to-End Testing**: Complete pipeline validation from UVH5 → MS →
   calibration → imaging → photometry
2. **Validation**: Verify pipeline algorithms recover known inputs correctly
3. **Testing**: Generate synthetic data for unit/integration tests
4. **Optimization**: Parameter sweeps to find optimal settings
5. **Regression**: Reference datasets to catch algorithm regressions
6. **Development**: Sandbox for experimenting with new features

## Notebooks Overview

### 02_forced_photometry_validation.ipynb

**Status**: ✅ Active - consistent with pipeline implementation

**Purpose**: Validates that
`dsa110_contimg.photometry.forced.measure_forced_peak()` accurately recovers
fluxes from synthetic sources.

**What it does**:

- Creates synthetic FITS images with Gaussian sources at known positions
- Uses NVSS catalog sources as test cases (around 0834+555 field)
- Performs forced photometry at catalog positions
- Compares measured vs expected fluxes
- Calculates SNR and validates error estimates

**How to run**:

```bash
conda activate casa6
cd /data/dsa110-contimg/simulations/notebooks
jupyter lab 02_forced_photometry_validation.ipynb
```

**Expected outputs**: Validation plots showing measured vs expected fluxes, SNR
distributions, and accuracy metrics.

**Dependencies**:

- `dsa110_contimg.photometry.forced` (pipeline code)
- `dsa110_contimg.catalog.query` (NVSS queries)
- `astropy`, `numpy`, `matplotlib`

## Running Simulations

### Prerequisites

```bash
# Activate casa6 environment (required for all simulations)
conda activate casa6

# Ensure pipeline package is installed in development mode
cd /data/dsa110-contimg/backend
pip install -e .
```

### End-to-End Testing (Recommended)

**Run complete pipeline test with one command:**

```bash
conda activate casa6
cd /data/dsa110-contimg

# Run with pre-defined scenario
python simulations/scripts/run_e2e_test.py --scenario bright_calibrator

# Or with custom config
python simulations/scripts/run_e2e_test.py --config simulations/config/scenarios/weak_sources.yaml
```

This automatically:

1. Generates synthetic UVH5 files (16 subbands)
2. Converts to Measurement Set
3. Runs calibration (auto-field selection)
4. Performs imaging (WSClean)
5. Extracts photometry (forced photometry)
6. Validates outputs against known inputs
7. Saves results to `simulations/data/e2e_tests/results.json`

**Available scenarios:**

- `bright_calibrator.yaml` - Strong calibrator, ideal conditions
- `weak_sources.yaml` - Low SNR source recovery

### Manual Step-by-Step Workflow

1. **Generate synthetic UVH5 data**:

   ```bash
   python -m dsa110_contimg.simulation.make_synthetic_uvh5 \
       --template-free \
       --nants 110 \
       --ntimes 23 \
       --start-time "2025-10-05T12:00:00" \
       --duration-minutes 5.0 \
       --subbands 16 \
       --flux-jy 5.0 \
       --add-noise \
       --output simulations/data/synthetic_uvh5/test01
   ```

2. **Convert to Measurement Set**:

   ```bash
   python -m dsa110_contimg.conversion.cli convert \
       --input-dir simulations/data/synthetic_uvh5/test01 \
       --output-dir simulations/data/synthetic_ms \
       --start-time "2025-10-05T12:00:00" \
       --end-time "2025-10-05T12:10:00"
   ```

3. **Run calibration**:

   ```bash
   python -m dsa110_contimg.calibration.cli_calibrate \
       simulations/data/synthetic_ms/2025-10-05T12:00:00.ms \
       --auto-select-field \
       --output-dir simulations/data/caltables
   ```

4. **Validate results**: Open relevant notebook in `notebooks/`

### Scenario-Based Testing

Use pre-defined scenarios in `config/scenarios/`:

```bash
# Example: Test weak source recovery
python scripts/run_scenario.py config/scenarios/weak_sources.yaml

# Example: Parameter sweep for imaging
python scripts/run_parameter_sweep.py \
    --config config/scenarios/imaging_sweep.yaml \
    --output simulations/data/results/sweep_001
```

## Data Management

**Important**: Simulation data files are **not** committed to the repository.

- All outputs in `simulations/data/` are gitignored
- Keep only configuration files and notebooks in version control
- Document reference datasets in `config/scenarios/` with URLs/paths

**Storage recommendations**:

- Synthetic UVH5 files: ~500 MB per 5-minute observation × 16 subbands
- Measurement Sets: ~2-4 GB per observation group
- Images: ~50-100 MB per image (depending on size)

**Cleanup**:

```bash
# Remove all simulation outputs
rm -rf simulations/data/synthetic_*

# Keep only results (metrics, plots)
find simulations/data -type f ! -path "*/results/*" -delete
```

## Adding New Simulations

### Creating a New Notebook

1. Copy template structure from existing notebook
2. Use pipeline code from `backend/src/dsa110_contimg/`
3. Document expected outputs and validation criteria
4. Add to this README with status and dependencies
5. Strip outputs before committing:
   ```bash
   jupyter nbconvert --clear-output --inplace your_notebook.ipynb
   ```

### Creating a New Scenario

1. Create YAML config in `config/scenarios/`
2. Document parameters and expected behavior
3. Add script in `scripts/` to execute scenario
4. Create corresponding validation notebook if needed

Example scenario structure:

```yaml
# config/scenarios/example.yaml
name: "Example Scenario"
description: "Brief description of what this tests"

observation:
  duration_minutes: 5.0
  num_subbands: 16
  start_time: "2025-10-05T12:00:00"

sources:
  - name: "TestSource1"
    ra_deg: 180.0
    dec_deg: 35.0
    flux_jy: 1.0
    major_arcsec: 5.0
    minor_arcsec: 5.0
    pa_deg: 0.0

imaging:
  size_pix: 512
  pixel_scale_arcsec: 3.6
  niter: 10000
  threshold: "0.001Jy"

validation:
  max_flux_error_percent: 10.0
  min_snr: 5.0
```

## Best Practices

1. **Always use pipeline code**: Import from `backend/src/dsa110_contimg/`, not
   legacy `src/`
2. **Document assumptions**: Note any simplifications or approximations
3. **Validate outputs**: Include quantitative success criteria
4. **Reproducibility**: Use fixed random seeds where applicable
5. **Clean outputs**: Strip notebook outputs before committing
6. **Reference data**: Document where to obtain reference datasets

## Troubleshooting

**Import errors**: Ensure `backend/` package is installed:

```bash
cd /data/dsa110-contimg/backend
pip install -e .
```

**Memory issues**: Reduce image sizes or use smaller test datasets

**CASA errors**: Verify `casa6` environment is activated

**Path issues**: All scripts assume working directory is `/data/dsa110-contimg`

## Related Documentation

- Pipeline architecture: `../docs/SYSTEM_CONTEXT.md`
- Code organization: `../docs/CODE_MAP.md`
- Testing guide: `../backend/tests/README.md`
- Deployment: `../ops/README.md`

## Contributing

When adding simulations:

1. Follow existing notebook structure and naming conventions
2. Update this README with notebook status and dependencies
3. Add scenario configs to `config/scenarios/` with documentation
4. Create reusable scripts in `scripts/` for common workflows
5. Commit notebooks with outputs stripped
6. Add `.gitignore` entries for new data output types

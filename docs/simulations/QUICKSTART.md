# Quick Start: Simulations

## Run Existing Validation

```bash
conda activate casa6
cd /data/dsa110-contimg/simulations/notebooks
jupyter lab 02_forced_photometry_validation.ipynb
```

## Generate Synthetic Test Data

```bash
# 1. Generate UVH5 subbands
python -m dsa110_contimg.simulation.generate_uvh5 \
    --output-dir simulations/data/synthetic_uvh5/test01 \
    --start-time "2025-10-05T12:00:00" \
    --duration-minutes 5.0 \
    --num-subbands 16

# 2. Convert to MS
python -m dsa110_contimg.conversion.cli convert \
    --input-dir simulations/data/synthetic_uvh5/test01 \
    --output-dir simulations/data/synthetic_ms \
    --start-time "2025-10-05T12:00:00" \
    --end-time "2025-10-05T12:10:00"

# 3. Run pipeline
python -m dsa110_contimg.pipeline.cli run \
    --input simulations/data/synthetic_ms/2025-10-05T12:00:00.ms \
    --output-dir simulations/data/synthetic_images
```

## Create New Validation Notebook

```bash
cd simulations/notebooks
cp 02_forced_photometry_validation.ipynb 03_my_test.ipynb
jupyter lab 03_my_test.ipynb

# Before committing:
jupyter nbconvert --clear-output --inplace 03_my_test.ipynb
```

## Structure

```
simulations/
├── notebooks/     # Interactive validation (use pipeline code)
├── scripts/       # Reusable CLI tools
├── config/        # Scenario definitions
└── data/          # Outputs (gitignored)
```

## Documentation

Full docs: [simulations/README.md](../simulations/README.md)

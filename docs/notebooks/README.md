# Notebooks Directory

**Status**: Most notebooks migrated to organized locations.

## Current Status

- :check: **forced_photometry_simulation.ipynb**: Migrated to
  `simulations/notebooks/02_forced_photometry_validation.ipynb`
- :file_cabinet::variation_selector-16: **debug_0834_calibration.ipynb**: Moved to `archive/working/` (ad-hoc
  debugging session)
- :file_cabinet::variation_selector-16: **qa_qa.ipynb**: Moved to `archive/working/qa_qa_stub.ipynb` (incomplete
  stub)

## Where to Find Notebooks

**Active Simulations**: See `docs/simulations/` if it exists, or check `backend/tests/` for simulation code.

- Organized testing and validation notebooks
- Use pipeline code for consistency checks

**QA/Monitoring Examples**: :arrow_right: Coming soon (expand
`simulations/notebooks/03_qa_demo.ipynb`)

- Interactive QA visualization demos
- Calibration quality inspection
- Image quality metrics

**Ad-hoc Work**: :arrow_right: `archive/working/`

- One-off debugging sessions
- Exploratory analysis
- Not maintained or documented

## Creating New Notebooks

**For simulations/validation**:

1. Create in `simulations/notebooks/` with descriptive name
2. Use pipeline code from `backend/src/dsa110_contimg/`
3. Document purpose and expected outputs in markdown cells
4. Add to [simulations/README.md](../simulations/README.md)
5. Strip outputs before committing:
   `jupyter nbconvert --clear-output --inplace notebook.ipynb`

**For quick debugging**:

1. Create in `archive/working/` (not committed)
2. No organization required
3. If becomes useful, migrate to `simulations/` with proper documentation

## Cleanup

This directory intentionally kept minimal. Organized notebooks live elsewhere:

- Simulations :arrow_right: `simulations/notebooks/`
- Examples :arrow_right: `docs/examples/`
- Archived work :arrow_right: `archive/working/`

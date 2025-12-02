# Simulation Toolkit

This directory contains the end-to-end tools for generating synthetic DSA-110
data products (UVH5 subbands, FITS images, placeholder HDF5s, etc.). The
simulation helpers are used by contract tests, local development workflows, and
benchmarks where real telescope data is unavailable.

## What’s New?

The synthetic UVH5 generator (`make_synthetic_uvh5.py`) now supports seeding the
sky with sources pulled directly from the real survey catalogs (NVSS, FIRST,
RACS, VLASS). This enables realistic end-to-end tests that mirror actual sky
fields without requiring sensitive observation data.

### Key Additions

1. **Catalog Source Selection**
   - `simulation/source_selection.py` wraps the catalog query layer and converts
     query rows into `SyntheticSource` dataclasses (RA/Dec/flux/morphology).
   - `SourceSelector` automatically reads the correct SQLite strip via
     `catalog.query.query_sources` and normalizes metadata for the simulator.

2. **Multi-source Visibility Modeling**
   - `simulation/source_models.py` implements spectral scaling and a
     `multi_source_visibility` helper that Fourier transforms arbitrary source
     lists onto the UVW lattice for each subband.
   - Sources inherit their reference frequency and spectral index directly from
     the catalog metadata to ensure frequency-dependent fluxes are physical.

3. **CLI Enhancements**
   - `make_synthetic_uvh5.py` now accepts catalog-focused flags in addition to
     the original single point-source options:

     ```bash
     python -m dsa110_contimg.simulation.make_synthetic_uvh5 \
       --template-free \
       --source-catalog-type nvss \
       --source-region-ra 175.0 \
       --source-region-dec 30.0 \
       --source-region-radius-deg 1.5 \
       --min-source-flux-mjy 5 \
       --max-source-count 32
     ```

   - The generator resolves the requested catalog strip, selects the brightest
     sources within the region, reports their aggregate flux, and feeds them
     into the new visibility pipeline. UVH5 files also encode provenance in
     `extra_keywords` (`synthetic_source_count`, summary JSON, etc.).

4. **Unit Tests**
   - `tests/unit/test_simulation_catalog_sources.py` verifies:
     - DataFrame → `SyntheticSource` conversion
     - Summary/statistics helper
     - Spectral flux evaluation
     - Multi-source visibility accumulation

## Rollout Notes

- **Configuration:** Ensure the catalog SQLite databases are available under
  `state/catalogs/`. The selector uses the same path resolution logic as the
  catalog module (environment variables, declination strips, auto-build hook).
- **Measured Parameters:** Populate `simulation/config/dsa110_measured_parameters.yaml`
  with real system temperature and beam metadata if you want thermal-noise and
  calibration-error modeling to reflect actual instrument performance.
- **Docs/Guides:** Update `docs/GETTING_STARTED.md` or internal runbooks to
  mention the catalog-driven simulation command shown above. Emphasize that the
  classic single-point-source flags still work when no catalog options are
  provided.
- **Future Enhancements:** The new modules provide hooks for:
  - Morphology-aware visibilities (FIRST major/minor axes) and polarization
    modeling.
  - pyuvsim-based primary beam attenuation via the antenna CSV builder.
  - Variability injection using `catalog/flux_monitoring.py` once light curves
    are ingested.

By default the CLI remains backwards compatible—if `--source-catalog-type` is
omitted, the previous behavior (single synthetic source with optional Gaussian
model) is preserved. Begin migrating workflows that rely on more realistic sky
fields by supplying the catalog flags and verifying outputs with
`simulation/validate_synthetic.py`.

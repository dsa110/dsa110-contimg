# DSA-110 Continuum Imaging Pipeline

The main Python package for the DSA-110 continuum imaging pipeline.

## Documentation

Documentation has been consolidated to the top-level `docs/` directory.

**[Go to Main Documentation](../../docs/README.md)**

## Quick Links

- [Architecture](../../docs/architecture/)
- [Operations](../../docs/operations/)
- [Examples](../../docs/examples/)

## Package Structure

- `api/` - FastAPI backend for the dashboard
- `calibration/` - Calibration routines
- `conversion/` - UVH5 to Measurement Set conversion
- `database/` - SQLite database utilities
- `imaging/` - WSClean and tclean wrappers
- `pipeline/` - Pipeline stage architecture
- `scripts/` - Operational and utility scripts
- `utils/` - Shared utilities

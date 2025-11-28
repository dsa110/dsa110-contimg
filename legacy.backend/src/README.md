# DSA-110 Continuum Imaging Source

This directory contains the main Python package source code.

## Structure

- **`dsa110_contimg/`**: The main Python package
  - Core modules: `conversion/`, `calibration/`, `imaging/`, `pipeline/`
  - API backend: `api/`
  - Database utilities: `database/`
  - Scripts: `scripts/` (operational scripts consolidated here)

## Related Directories

See the parent directory (`../`) for:

- **`docs/`**: [Documentation Hub](../docs/README.md)
- **`tests/`**: All test files (unit, integration, e2e)
- **`config/`**: Configuration files (YAML, Lua)
- **`state/`**: SQLite databases and runtime state

## Installation

This project is managed from the parent directory. See `../pyproject.toml`
for build configuration.

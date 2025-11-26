# Environment Setup Guide

This guide explains how to set up the casa6 conda environment using the
`environment.yml` file.

## Location

The environment file is located at: `env/environment.yml`

## Prerequisites

- Miniforge or Miniconda installed
- Access to conda-forge channel

## Installation Steps

### 1. Create the casa6 Environment

```bash
# Navigate to project root
cd /path/to/dsa110-contimg

# Create environment from file
conda env create -f env/environment.yml

# Activate the environment
conda activate casa6
```

### 2. Verify Installation

```bash
# Verify Python version
python --version
# Should show: Python 3.11.x

# Verify CASA tools
python -c "import casatools; print('CASA tools available')"

# Verify development tools
python -c "import pytest, black, flake8, mypy, pylint, bandit; print('All dev tools available')"
```

### 3. Update Environment (if needed)

If the `environment.yml` file is updated:

```bash
# Update existing environment
conda env update -f env/environment.yml --prune

# Or recreate from scratch
conda env remove -n casa6
conda env create -f env/environment.yml
```

## Included Packages

### Core Dependencies

- Python 3.11
- CASA tools (casatools, casatasks, casacore)
- Astropy, NumPy, SciPy
- FastAPI, Uvicorn

### Development Tools

- **Testing**: pytest, pytest-cov, pytest-asyncio, pytest-mock
- **Formatting**: black, isort
- **Linting**: flake8, pylint, pyflakes
- **Type Checking**: mypy
- **Security**: bandit, safety
- **Database**: alembic

## Troubleshooting

### Environment Creation Fails

If environment creation fails:

1. **Check conda version**: `conda --version` (should be >= 4.10)
2. **Update conda**: `conda update conda`
3. **Clear conda cache**: `conda clean --all`
4. **Try with explicit channel**:
   `conda env create -f env/environment.yml -c conda-forge`

### Missing Packages

If packages are missing after installation:

```bash
# Activate environment
conda activate casa6

# Install missing package
conda install -c conda-forge <package-name>
```

### CASA Tools Not Available

If CASA tools are not found:

1. Verify conda-forge channel is enabled: `conda config --show channels`
2. Add conda-forge if missing: `conda config --add channels conda-forge`
3. Recreate environment:
   `conda env remove -n casa6 && conda env create -f env/environment.yml`

## Notes

- The environment file is located in `env/` subdirectory, not the project root
- All Python operations should use: `/opt/miniforge/envs/casa6/bin/python`
- The Makefile defines `CASA6_PYTHON` variable for convenience

## Related Documentation

- [CASA6 Environment Guide](CASA6_ENVIRONMENT_GUIDE.md)
- [Development Setup](../TODO.md)
- [Pre-commit Setup](../PRE_COMMIT_SETUP.md)

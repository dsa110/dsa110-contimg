# Installing Playwright Python via Conda-Forge

This guide explains how to install Playwright Python in the `casa6` conda
environment using conda-forge.

## Installation Steps

### 1. Activate casa6 Environment

```bash
conda activate casa6
```

### 2. Install Playwright from Conda-Forge

```bash
conda install -c conda-forge playwright
```

This installs:

- The `playwright` Python package
- All Python dependencies (greenlet, pyee, etc.)
- System dependencies managed by conda

### 3. Install pytest-playwright

The `pytest-playwright` package is not available on conda-forge, so install it
via pip:

```bash
pip install pytest-playwright
```

### 4. Install Browser Binaries

After installing the Playwright package, you must install the browser binaries:

```bash
# Install Chromium (recommended for most tests)
playwright install chromium

# Or install all browsers
playwright install
```

This downloads and installs:

- Chromium browser binaries
- Firefox browser binaries (if using `playwright install`)
- WebKit browser binaries (if using `playwright install`)

## Verify Installation

```bash
# Check Playwright version
python -c "import playwright; print(playwright.__version__)"

# Check if browsers are installed
playwright --version
```

## Complete Installation Command

For a complete one-time setup:

```bash
conda activate casa6
conda install -c conda-forge playwright
pip install pytest-playwright
playwright install chromium
```

## Why Use Conda-Forge?

1. **Better Dependency Management**: Conda manages system-level dependencies
2. **Environment Consistency**: Keeps all packages in the conda environment
3. **System Compatibility**: Handles library dependencies on Ubuntu 18.x
4. **Integration**: Works seamlessly with casa6 environment

## Notes

- **pytest-playwright**: Must be installed via pip as it's not on conda-forge
- **Browser Binaries**: Always installed via `playwright install` command (not
  via conda/pip)
- **Browser Location**: Binaries are installed in `~/.cache/ms-playwright/` by
  default

## Troubleshooting

### Browser Not Found After Installation

```bash
# Reinstall browsers
playwright install chromium --force
```

### Permission Errors

```bash
# Make sure you have write access to ~/.cache/
# Or set PLAYWRIGHT_BROWSERS_PATH environment variable
export PLAYWRIGHT_BROWSERS_PATH=/path/to/browsers
playwright install chromium
```

### Conda-Forge Channel Not Available

```bash
# Add conda-forge channel
conda config --add channels conda-forge
conda config --set channel_priority strict

# Then install
conda install playwright
```

## Alternative: Environment File

You can also create a conda environment file:

```yaml
# environment.yml
name: casa6
channels:
  - conda-forge
  - defaults
dependencies:
  - playwright
  - pip
  - pip:
      - pytest-playwright
```

Then install with:

```bash
conda env create -f environment.yml
# Or update existing:
conda env update -f environment.yml
```

## See Also

- [Playwright Python Frontend Testing Guide](playwright-python-frontend-testing.md)
- [Quick Start Guide](playwright-python-quick-start.md)

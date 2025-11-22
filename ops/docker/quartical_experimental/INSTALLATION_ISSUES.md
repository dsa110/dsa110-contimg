# CubiCal Installation Issues

## Problem

CubiCal installation fails due to `sharedarray` dependency issue:

```
packaging.version.InvalidVersion: Invalid version: "b'3.1.0-2-gdc90bd2\\n'"
```

This is a known issue with the sharedarray package's version string format.

## Attempted Solutions

1. **With Montblanc support**: Failed (sharedarray issue)
2. **Without Montblanc**: Trying now (may work)

## Alternative Approaches

### Option 1: Install sharedarray separately

```bash
# Try installing sharedarray from a different source or version
pip install git+https://gitlab.com/bennahugo/shared-array.git@<working-version>
```

### Option 2: Use pre-built CubiCal

- Look for conda packages
- Use Docker images with CubiCal pre-installed

### Option 3: Fix sharedarray version

- Clone sharedarray repository
- Fix version string in setup.py
- Install from local source

## Current Status

Trying installation without Montblanc support (CPU-only mode).

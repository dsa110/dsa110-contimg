# CubiCal Installation Blocker

## Issue Summary

CubiCal installation is blocked by `sharedarray` dependency compatibility
issues:

1. Version string parsing error with Python 3.11
2. Syntax errors when trying to fix setup.py
3. Appears to be a Python 3.11 compatibility issue

## Attempted Solutions

1. :check: Direct installation (with/without Montblanc) - Failed
2. :check: Installing sharedarray separately - Failed
3. :check: Fixing sharedarray setup.py - Broke syntax

## Alternative Approaches

### Option 1: Use Python 3.10 Instead

- sharedarray may work better with Python 3.10
- Rebuild Docker image with Python 3.10
- Then try CubiCal installation

### Option 2: Install Older CubiCal Version

- Try CubiCal 1.3.0 or earlier
- May have different dependencies
- Command:
  `pip install 'cubical@git+https://github.com/ratt-ru/CubiCal.git@1.3.0'`

### Option 3: Skip CubiCal for Now

- Focus on CPU calibration optimizations
- Document blocker for future resolution
- Revisit when sharedarray is fixed upstream

### Option 4: Use Pre-built Environment

- Look for official CubiCal Docker images
- Or use conda environment with CubiCal pre-installed

## Recommendation

Given the installation difficulties, I recommend:

**Short-term**: Focus on CPU calibration optimizations (hierarchical
calibration, parallel SPW processing) which provide immediate value without
CubiCal.

**Long-term**:

- Try Python 3.10 in Docker (may resolve sharedarray issue)
- Or wait for sharedarray/CubiCal to fix Python 3.11 compatibility
- Or use alternative GPU calibration tools

## Current Status

- :check: Docker environment ready
- :check: All core packages working
- :cross: CubiCal installation blocked
- ⏸:variation_selector-16: Waiting for resolution or alternative approach

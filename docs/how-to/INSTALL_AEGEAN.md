# Installing Aegean for DSA-110 Pipeline

AegeanTools (which includes Aegean and BANE) is required for Phase 2 WABIFAT integration. Since it's not available via conda-forge, it must be installed from source or via pip.

## Installation Methods

### Method 1: Install from Cloned Repository (Recommended)

If you've cloned the Aegean repository to `~/proj/Aegean/`:

```bash
# Activate casa6 environment
conda activate casa6

# Install from local repository
cd ~/proj/Aegean
pip install .

# Verify installation
python -m AegeanTools.Aegean --version
python -m AegeanTools.BANE --version
```

### Method 2: Install from GitHub (Latest)

```bash
conda activate casa6
pip install git+https://github.com/PaulHancock/Aegean.git
```

### Method 3: Install Stable Release

```bash
conda activate casa6
pip install AegeanTools
```

## Verification

After installation, verify that Aegean and BANE are accessible:

```bash
# Check command-line tools (if installed with scripts)
Aegean --version
BANE --version

# Check Python module (always works)
python -m AegeanTools.Aegean --version
python -m AegeanTools.BANE --version
```

## Usage in DSA-110 Pipeline

The DSA-110 photometry module automatically detects Aegean/BANE using multiple methods:

1. Command-line tools (`Aegean`, `BANE`) if in PATH
2. Python module (`python -m AegeanTools.Aegean`, `python -m AegeanTools.BANE`)
3. Python import (for programmatic use)

**Example:**
```bash
# Use Aegean forced fitting
python -m dsa110_contimg.photometry.cli peak \
  --fits image.pbcor.fits \
  --ra 128.725 --dec 55.573 \
  --use-aegean
```

## Troubleshooting

### "Aegean not found" Error

If you get an error that Aegean is not found:

1. **Check installation:**
   ```bash
   python -c "import AegeanTools; print('OK')"
   ```

2. **Check Python module:**
   ```bash
   python -m AegeanTools.Aegean --version
   ```

3. **If module works but command doesn't:**
   - The Python module method will be used automatically
   - No action needed - the code handles this

### Installation Issues

If `pip install .` fails:

1. **Check Python version:** AegeanTools requires Python 3.10-3.13
   ```bash
   python --version
   ```

2. **Check dependencies:**
   ```bash
   pip install numpy scipy astropy
   ```

3. **Install in development mode:**
   ```bash
   cd ~/proj/Aegean
   pip install -e .
   ```

## References

- **Aegean GitHub:** https://github.com/PaulHancock/Aegean
- **Documentation:** http://aegeantools.readthedocs.io/
- **Paper 1:** Hancock et al 2012, MNRAS, 422, 1812
- **Paper 2:** Hancock et al 2018, PASA, 35, 11H


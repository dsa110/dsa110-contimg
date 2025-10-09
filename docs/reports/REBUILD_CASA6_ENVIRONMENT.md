# Rebuilding the CASA6 Conda Environment

This guide provides multiple methods to recreate the `casa6` conda environment on a different machine.

## Files Created

The following files have been exported from the original `casa6` environment:

1. **`environment.yml`** - Complete conda environment specification (RECOMMENDED)
2. **`casa6_explicit.txt`** - Explicit package URLs for exact reproduction
3. **`casa6_requirements.txt`** - Conda package list with versions
4. **`casa6_pip_requirements.txt`** - Pip-only packages

## Method 1: Using environment.yml (RECOMMENDED)

This is the most reliable and portable method:

```bash
# Create the environment from the yaml file
conda env create -f environment.yml

# Activate the environment
conda activate casa6

# Verify installation
conda list
```

## Method 2: Using Explicit Package List

For exact reproduction with specific package URLs:

```bash
# Create environment from explicit list
conda create --name casa6 --file casa6_explicit.txt

# Activate the environment
conda activate casa6
```

## Method 3: Manual Recreation

If the above methods fail, you can recreate manually:

```bash
# Create new environment with Python 3.11
conda create -n casa6 python=3.11

# Activate environment
conda activate casa6

# Install conda packages
conda install -c conda-forge casatasks casatools casacore casacpp astropy numpy scipy matplotlib pandas h5py

# Install pip packages
pip install -r casa6_pip_requirements.txt
```

## Method 4: Using Conda Pack (Advanced)

For complete environment portability including compiled binaries:

```bash
# Install conda-pack
conda install conda-pack

# Pack the environment (run this on the original machine)
conda pack -n casa6 -o casa6_env.tar.gz

# On the new machine, extract and activate
mkdir -p ~/miniconda3/envs/casa6
tar -xzf casa6_env.tar.gz -C ~/miniconda3/envs/casa6
source ~/miniconda3/envs/casa6/bin/activate
conda-unpack
```

## Environment Details

- **Python Version**: 3.11.13
- **CASA Version**: 6.7.2.32
- **Primary Channel**: conda-forge
- **Key Packages**: 
  - casatasks, casatools, casacore, casacpp
  - astropy, numpy, scipy, matplotlib, pandas
  - h5py, pyuvdata, regions, photutils
  - jupyter, ipython, notebook

## Troubleshooting

### Common Issues:

1. **Channel conflicts**: If you encounter channel conflicts, try:
   ```bash
   conda config --add channels conda-forge
   conda config --set channel_priority strict
   ```

2. **Package not found**: Some packages might not be available on all platforms. Use the explicit method or install manually.

3. **Version conflicts**: If specific versions are not available, the environment.yml will automatically resolve compatible versions.

4. **MPI issues**: The environment includes OpenMPI. If you encounter MPI-related issues:
   ```bash
   conda install -c conda-forge openmpi
   ```

### Verification:

After installation, verify the environment works:

```python
# Test CASA import
import casatasks
import casatools
import casacore

# Test other key packages
import astropy
import numpy as np
import matplotlib.pyplot as plt

print("Environment successfully recreated!")
```

## Notes

- The environment was created on Linux x86_64
- Some packages may have different versions on different platforms
- The explicit method (Method 2) provides the most exact reproduction
- The environment.yml method (Method 1) is the most portable and recommended approach

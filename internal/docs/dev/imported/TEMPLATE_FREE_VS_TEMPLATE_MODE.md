# Template-Free vs Template-Based Generation: Format Compatibility

## What "Template-Free" Means

**Template-free generation** means we can create synthetic UVH5 files **without
requiring an existing UVH5 file as a starting point**. Instead, we build the
UVData structure from:

1. **Configuration files** (`telescope.yaml`, `reference_layout.json`)
2. **Antenna position data** (from `get_itrf()`)
3. **User-specified parameters** (number of antennas, times, etc.)

**Template-based generation** (the original method) requires an existing UVH5
file to:

- Copy the structure (antenna arrays, baseline pairs, time structure)
- Extract metadata (polarizations, frequency structure, etc.)
- Use as a scaffold for new data

## Format Compatibility: YES, Same UVH5 Format

**Both methods produce identical UVH5 format files** that are compatible with
real DSA-110 data. Here's why:

### 1. Same Underlying Library

Both methods use **pyuvdata's UVData class** and write using
**`uv.write_uvh5()`**:

```python
# Template-free mode
uv = build_uvdata_from_scratch(config, ...)
uv.write_uvh5(output_path, ...)  # Same write function

# Template mode
uv = template.copy()
# ... modify data ...
uv.write_uvh5(output_path, ...)  # Same write function
```

### 2. Same Data Structure

Both produce UVData objects with the same structure:

- Same array shapes: `(Nblts, Nspws, Nfreqs, Npols)`
- Same metadata fields: `time_array`, `lst_array`, `uvw_array`, `data_array`,
  etc.
- Same HDF5 structure when written to disk

### 3. Same Configuration Sources

Both methods use the **same configuration files**:

- `telescope.yaml` - Telescope configuration
- `reference_layout.json` - Layout metadata
- Same antenna positions from `get_itrf()`
- Same frequency structure from config

## Key Differences (Structure, Not Format)

The **format is identical**, but there are some **structural differences** in
what gets generated:

### 1. Antenna Selection

**Template mode:**

- Uses **exactly the same antennas** as the template file
- Preserves antenna numbering from template
- Number of antennas = template's `Nants_telescope`

**Template-free mode:**

- Uses **first N antennas** from available stations (default: 110)
- Antenna numbering: stations 1, 2, 3, ... N
- Number of antennas = user-specified `--nants` (default: 110)

**Impact:** Different antenna sets, but **same format structure**

### 2. Time Structure

**Template mode:**

- Uses **same time structure** as template (number of integrations, spacing)
- Preserves template's time array pattern

**Template-free mode:**

- Creates **new time structure** based on:
  - `--duration-minutes` parameter
  - `--ntimes` parameter (default: 30)
  - Integration time from config

**Impact:** Different time coverage, but **same time array format**

### 3. Baseline Pairs

**Template mode:**

- Uses **exact baseline pairs** from template
- Preserves baseline ordering

**Template-free mode:**

- Generates **all pairs** from selected antennas: `(i, j) for i < j`
- Different baseline ordering (but valid)

**Impact:** Different baseline sets, but **same baseline array format**

### 4. Metadata Fields

**Template mode:**

- Preserves **all metadata** from template
- May include extra_keywords from original observation
- History includes template's history

**Template-free mode:**

- Sets **standard metadata** from config
- Adds `synthetic=True` and `template_free=True` keywords
- History indicates template-free generation

**Impact:** Different metadata content, but **same metadata structure**

## Format Verification

Both methods produce files that:

1. ✅ **Read correctly** with `pyuvdata.UVData.read(file, file_type='uvh5')`
2. ✅ **Pass validation** with `validate_uvh5_file()`
3. ✅ **Work in pipeline** - conversion, calibration, imaging all accept them
4. ✅ **Same HDF5 structure** - identical file format on disk

## When to Use Each Mode

### Use Template-Free Mode When:

- ✅ **No template file available** (first-time setup, CI/CD)
- ✅ **Want specific antenna count** (testing with fewer antennas)
- ✅ **Want specific time structure** (custom duration/integrations)
- ✅ **Generating many datasets** (faster, no file I/O for template)

### Use Template Mode When:

- ✅ **Want exact match** to a specific observation's structure
- ✅ **Testing with real antenna configuration** (exact antenna set)
- ✅ **Preserving specific metadata** from real observation
- ✅ **Reproducing exact baseline pattern** from observation

## Example: Both Produce Compatible Files

```python
from pyuvdata import UVData

# Template-free generated file
uv1 = UVData()
uv1.read("template_free_sb00.hdf5", file_type="uvh5")
print(f"Format: {uv1.__class__}")  # <class 'pyuvdata.UVData'>
print(f"Shape: {uv1.data_array.shape}")  # (Nblts, Nspws, Nfreqs, Npols)

# Template-based generated file
uv2 = UVData()
uv2.read("template_based_sb00.hdf5", file_type="uvh5")
print(f"Format: {uv2.__class__}")  # <class 'pyuvdata.UVData'>
print(f"Shape: {uv2.data_array.shape}")  # (Nblts, Nspws, Nfreqs, Npols)

# Both are identical format - can be used interchangeably in pipeline
```

## Pipeline Compatibility

Both generation methods produce files that work identically in:

1. **Conversion:** `hdf5_orchestrator.py` accepts both
2. **Calibration:** `cli_calibrate.py` processes both the same way
3. **Imaging:** `cli_imaging.py` images both identically
4. **Validation:** `validate_synthetic.py` validates both

## Summary

**"Template-free" means:**

- We don't need an existing UVH5 file to start from
- We build the structure from config files instead
- **The output format is identical** to template-based generation
- **Both are compatible** with real DSA-110 UVH5 data format

**The only differences are:**

- Which antennas are included
- Time structure (coverage, number of integrations)
- Baseline pairs (which baselines, ordering)
- Metadata content (but same structure)

**The format is the same** because both use pyuvdata's UVData class and write to
UVH5 format using the same function.

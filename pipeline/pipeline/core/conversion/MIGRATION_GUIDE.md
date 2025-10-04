# Migration Guide: Unified HDF5 Converter

This guide explains how to migrate from the old separate `HDF5toMSConverter` and `SubbandConcatenator` classes to the new unified `UnifiedHDF5Converter`.

## Why Migrate?

The old architecture had several issues:
- **Duplicated functionality** between two classes
- **Inconsistent APIs** for similar operations
- **Mixed responsibilities** in single classes
- **Code duplication** for file reading and error handling
- **Confusing naming** and interfaces

The new `UnifiedHDF5Converter` provides:
- **Single, consistent API** for all conversion tasks
- **Clean separation** of concerns
- **Better error handling** and progress monitoring
- **Convenience functions** for simple use cases
- **Backward compatibility** with existing code

## Migration Examples

### Old Way (Two Classes)

```python
# Old: Single file conversion
from pipeline.core.conversion import HDF5toMSConverter

converter = HDF5toMSConverter()
ms_path = converter.convert_file('file.hdf5')

# Old: Multi-subband conversion
from pipeline.core.conversion import SubbandConcatenator

concatenator = SubbandConcatenator()
result = concatenator.concatenate_and_convert(
    file_paths=['sb01.hdf5', 'sb02.hdf5'],
    output_ms='combined'
)
```

### New Way (Unified Class)

```python
# New: Single file conversion
from pipeline.core.conversion import UnifiedHDF5Converter

converter = UnifiedHDF5Converter()
ms_path = converter.convert_single('file.hdf5')

# New: Multi-subband conversion
result = converter.convert_subbands(
    file_paths=['sb01.hdf5', 'sb02.hdf5'],
    output_name='combined'
)

# New: Convenience functions
from pipeline.core.conversion import convert_single_file, convert_subband_group

ms_path = convert_single_file('file.hdf5')
result = convert_subband_group(['sb01.hdf5', 'sb02.hdf5'], 'combined')
```

## API Comparison

| Old Method | New Method | Notes |
|------------|------------|-------|
| `HDF5toMSConverter.convert_file()` | `UnifiedHDF5Converter.convert_single()` | Same functionality, clearer name |
| `HDF5toMSConverter.convert_batch()` | `UnifiedHDF5Converter.convert_batch()` | Same functionality |
| `HDF5toMSConverter.get_file_info()` | `UnifiedHDF5Converter.get_file_info()` | Same functionality |
| `SubbandConcatenator.concatenate_and_convert()` | `UnifiedHDF5Converter.convert_subbands()` | Same functionality, clearer name |
| `SubbandConcatenator.concatenate_subbands()` | `UnifiedHDF5Converter._concatenate_subbands()` | Internal method, not public |

## New Features

### 1. Consistent Error Handling
```python
# All methods now return consistent error information
result = converter.convert_subbands(file_paths, 'output')
if not result['success']:
    print(f"Error: {result['error']}")
    print(f"Elapsed time: {result['elapsed']:.2f}s")
```

### 2. Better Progress Monitoring
```python
# Real-time progress with unbuffered output
converter = UnifiedHDF5Converter()
# All print statements are automatically flushed
```

### 3. Flexible File Discovery
```python
# Pattern-based file discovery
files = converter.list_files(pattern='*_sb*.hdf5')
files = converter.list_files(pattern='2025-10-03*', subdir=Path('/custom/path'))
```

### 4. Convenience Functions
```python
# Quick single file conversion
from pipeline.core.conversion import convert_single_file
ms_path = convert_single_file('file.hdf5', output_dir='/custom/output')

# Quick subband group conversion
from pipeline.core.conversion import convert_subband_group
result = convert_subband_group(['sb01.hdf5', 'sb02.hdf5'], 'combined')
```

### 5. UVFITS-backed Subband Conversion
`convert_subbands` now writes a temporary UVFITS file before invoking CASA `importuvfits`. This improves interoperability and ensures antenna metadata is reflected exactly in the final MS. You can opt-in to pre-populating the MS `MODEL_DATA` column:
```python
converter.convert_subbands(
    file_paths=subband_files,
    output_name='observation_2025-10-03',
    populate_model=True,          # write unity visibilities into MODEL_DATA
    model_value=1.0 + 0.0j,       # optional complex value (defaults to unity)
)
```

## Backward Compatibility

The old classes (`HDF5toMSConverter` and `SubbandConcatenator`) are still available and will continue to work. However, we recommend migrating to the new unified interface for:

- **New code**: Always use `UnifiedHDF5Converter`
- **Existing code**: Migrate when convenient, no rush
- **Performance**: New interface has the same performance characteristics

## Migration Steps

1. **Update imports**:
   ```python
   # Old
   from pipeline.core.conversion import HDF5toMSConverter, SubbandConcatenator
   
   # New
   from pipeline.core.conversion import UnifiedHDF5Converter
   ```

2. **Update method calls**:
   ```python
   # Old
   converter = HDF5toMSConverter()
   ms_path = converter.convert_file('file.hdf5')
   
   # New
   converter = UnifiedHDF5Converter()
   ms_path = converter.convert_single('file.hdf5')
   ```

3. **Update subband conversion**:
   ```python
   # Old
   concatenator = SubbandConcatenator()
   result = concatenator.concatenate_and_convert(files, 'output')
   
   # New
   converter = UnifiedHDF5Converter()
   result = converter.convert_subbands(files, 'output')
   ```

4. **Test thoroughly**: Run your existing workflows with the new interface to ensure everything works as expected.

## Benefits of Migration

- **Cleaner code**: Single class for all conversion tasks
- **Better maintainability**: Less code duplication
- **Consistent interface**: Same patterns for all operations
- **Enhanced features**: Better error handling and progress monitoring
- **Future-proof**: New features will be added to the unified interface

## Questions?

If you encounter any issues during migration, please check:
1. Method names are updated correctly
2. Return value handling (some methods now return dictionaries)
3. Error handling (new consistent error reporting)

The unified converter maintains the same core functionality while providing a much cleaner and more maintainable interface.

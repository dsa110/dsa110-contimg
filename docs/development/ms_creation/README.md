# MS Creation Documentation

This directory contains comprehensive documentation about Measurement Set (MS) creation in the DSA-110 pipeline.

## Documentation Files

- **[Summary](summary.md)** - Overview of the unified MS creation system
- **[Issues and Fixes](issues_and_fixes.md)** - Detailed catalog of issues encountered and their solutions
- **[HDF5 Conversion Fixes](hdf5_conversion_fixes.md)** - Specific fixes for HDF5 to MS conversion

## MS Creation Overview

The DSA-110 pipeline uses a unified MS creation system that combines:

1. **DSA-110 Specific Fixes** - Handles DSA-110 data format issues
2. **Quality Validation** - Ensures data consistency and completeness
3. **Multi-Subband Processing** - Intelligently combines multiple subbands
4. **Error Recovery** - Graceful handling of missing or corrupted data

## Key Features

### DSA-110 Specific Fixes
- UVW array type conversion (float32 → float64)
- Telescope name correction (OVRO_MMA → DSA-110)
- Visibility units standardization (uncalib → Jy)
- Mount type correction (other → alt-az)

### Quality Validation
- Completeness checks for all required subbands
- Data consistency validation
- Integration time consistency checks
- Quality scoring (0.0 to 1.0)

### Multi-Subband Processing
- Intelligent combination of all subbands for a timestamp
- Error recovery for missing or corrupted subbands
- Quality assessment before and after combination
- Configurable quality thresholds

## Usage Examples

### Single File Processing
```python
from core.data_ingestion.unified_ms_creation import UnifiedMSCreationManager

ms_manager = UnifiedMSCreationManager(config)
result = await ms_manager.create_ms_from_single_file(
    hdf5_path, output_ms_path, quality_checks=True
)
```

### Multi-Subband Processing
```python
hdf5_files = glob.glob(f"{timestamp}_sb*.hdf5")
result = await ms_manager.create_ms_from_multiple_files(
    hdf5_files, output_ms_path, quality_checks=True
)
```

## Configuration

The system is highly configurable through the pipeline configuration:

```yaml
ms_creation:
  same_timestamp_tolerance: 120.0  # seconds
  min_data_quality: 0.8           # 0.0 to 1.0
  max_missing_subbands: 2         # maximum allowed missing sub-bands
  min_integration_time: 10.0      # seconds
  output_antennas: null           # antenna selection (null = all)
```

## Troubleshooting

For common issues and solutions, see:
- [Issues and Fixes](issues_and_fixes.md) - Comprehensive issue catalog
- [HDF5 Conversion Fixes](hdf5_conversion_fixes.md) - Specific conversion issues

## Getting Started

1. **Understanding the System**: Read [Summary](summary.md)
2. **Troubleshooting Issues**: Check [Issues and Fixes](issues_and_fixes.md)
3. **HDF5 Conversion Problems**: See [HDF5 Conversion Fixes](hdf5_conversion_fixes.md)

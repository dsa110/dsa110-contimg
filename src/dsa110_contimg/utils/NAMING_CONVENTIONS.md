# Naming Conventions for DSA-110 Continuum Imaging Pipeline

This document defines all naming conventions used throughout the pipeline. All
conventions are enforced through the `dsa110_contimg.utils.naming` module to
ensure consistency and prevent user errors.

## Core Principles

1. **Database as Source of Truth**: All naming decisions are validated against
   database state first
2. **Filesystem Safety**: All names are sanitized to prevent path traversal and
   invalid characters
3. **Consistency**: All naming follows standardized patterns across the codebase
4. **Validation**: All user-provided names are validated before use

## Naming Patterns

### Group IDs

**Format**: `YYYY-MM-DDTHH:MM:SS` (ISO 8601 format, UTC)

**Examples**:

- `2025-10-02T10:02:45`
- `2025-10-29T13:54:17`

**Validation**:

- Must match regex: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$`
- Date/time components must be valid
- Normalized from filenames: `YYYY-MM-DDTHH:MM:SS_sb##.hdf5`

**Usage**:

- Extracted from HDF5 subband filenames
- Used as primary key in `ingest_queue` and `subband_files` tables
- Used to construct MS filenames, mosaic IDs, and image paths

**Functions**:

- `validate_group_id(group_id, strict=True)` - Validate format
- `normalize_group_id(group_id)` - Normalize to standard format

### Calibrator Names

**Format**: Alphanumeric characters, `+`, `-`, `_` only

**Examples**:

- `0834+555`
- `3C286`
- `J0834+555`

**Validation**:

- Must match regex: `^[a-zA-Z0-9+\-_]+$`
- Maximum length: 50 characters
- Cannot be empty

**Sanitization for File Paths**:

- `+` and `-` replaced with `_`
- Example: `0834+555` → `0834_555` (for filesystem)

**Usage**:

- Stored in `bandpass_calibrators` table
- Used in calibration table prefixes
- Used in MS file organization

**Functions**:

- `validate_calibrator_name(name)` - Validate format
- `sanitize_calibrator_name(name)` - Sanitize for filesystem

### MS (Measurement Set) Files

**Format**: `<group_id>.ms`

**Examples**:

- `2025-10-02T10:02:45.ms`
- `2025-10-29T13:54:17.ms`

**Organization**:

- Science MS: `ms/science/YYYY-MM-DD/<group_id>.ms/`
- Calibrator MS: `ms/calibrators/YYYY-MM-DD/<group_id>.ms/`
- Failed MS: `ms/failed/YYYY-MM-DD/<group_id>.ms/`

**Functions**:

- `construct_ms_filename(group_id)` - Construct MS filename from group ID

### Images

**Format**: `<ms_stem>.img-*`

**Examples**:

- `2025-10-02T10:02:45.img-image-pb.fits` (WSClean FITS)
- `2025-10-02T10:02:45.img.pbcor` (CASA primary beam corrected)
- `2025-10-02T10:02:45.img.image` (CASA image)

**Organization**:

- Base directory: `images/`
- Derived from MS stem (filename without `.ms` extension)

**Functions**:

- `construct_image_basename(ms_path)` - Construct image basename from MS path

### Mosaics

**Format**: `mosaic_<group_id>_<timestamp>.image` or `.fits`

**Examples**:

- `mosaic_2025-10-02T10:02:45_1696234567.image`
- `mosaic_2025-10-02T10:02:45_1696234567.fits`

**Organization**:

- Base directory: `mosaics/`
- Group ID normalized to standard format
- Timestamp is Unix epoch (seconds since 1970-01-01)

**Functions**:

- `construct_mosaic_id(group_id)` - Construct mosaic ID from group ID

### Calibration Tables

**Format**: `<ms_stem>_<type>cal/`

**Types**:

- `bpcal` - Bandpass calibration
- `gpcal` - Gain calibration (GP)
- `2gcal` - Gain calibration (2G)

**Examples**:

- `2025-10-02T10:02:45_bpcal/`
- `2025-10-02T10:02:45_gpcal/`
- `2025-10-02T10:02:45_2gcal/`

**Organization**:

- Stored alongside calibrator MS files
- Path: `ms/calibrators/YYYY-MM-DD/<ms_stem>_<type>cal/`

**Functions**:

- `construct_caltable_prefix(ms_path, cal_type)` - Construct calibration table
  prefix

### Date Strings

**Format**: `YYYY-MM-DD`

**Examples**:

- `2025-10-02`
- `2025-10-29`

**Validation**:

- Must match regex: `^\d{4}-\d{2}-\d{2}$`
- Date components must be valid

**Usage**:

- Extracted from filenames for directory organization
- Used in MS file organization paths

**Functions**:

- `validate_date_string(date_str)` - Validate date format

## File Path Safety

All file paths are validated to prevent:

1. **Path Traversal**: `..` sequences are detected and rejected
2. **Invalid Characters**: Filesystem-invalid characters are removed
3. **Directory Escapes**: Paths are validated to ensure they stay within base
   directories

**Invalid Filename Characters** (Windows + Unix):

- `/ \ < > : " | ? * \x00`

**Functions**:

- `sanitize_filename(filename, max_length=255)` - Sanitize filename
- `validate_path_safe(path, base_dir=None)` - Validate path safety

## Integration Points

### Streaming Converter (`streaming_converter.py`)

- Uses `normalize_group_id()` for group ID normalization
- Validates group IDs extracted from HDF5 filenames

### Streaming Mosaic Manager (`streaming_mosaic.py`)

- Uses `validate_calibrator_name()` when registering calibrators
- Uses `construct_mosaic_id()` for mosaic ID generation
- Uses `construct_image_basename()` for image path construction
- Uses `construct_caltable_prefix()` for calibration table paths

### Calibrator Registration (`lookup_and_register_calibrator.py`)

- Uses `validate_calibrator_name()` before registration
- Ensures calibrator names are valid before database insertion

## Error Handling

All naming functions raise `ValueError` with descriptive error messages when:

- Input format is invalid
- Input contains invalid characters
- Input cannot be normalized
- Input would create unsafe paths

## Best Practices

1. **Always Validate**: Use validation functions before storing names in
   database
2. **Normalize Early**: Normalize group IDs as soon as they're extracted
3. **Sanitize for Filesystem**: Use sanitization functions when constructing
   file paths
4. **Use Constructors**: Use constructor functions (`construct_*`) instead of
   manual string formatting
5. **Check Path Safety**: Validate paths when accepting user input or
   constructing from external data

## Migration Notes

Existing code that manually constructs names should be migrated to use the
naming module functions. The module provides backward compatibility fallbacks
where possible, but validation is now enforced for all new code.

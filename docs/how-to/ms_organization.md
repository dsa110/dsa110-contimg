# MS File Organization

## Overview

The pipeline automatically writes MS files directly to organized, hierarchical, date-based directory structures. Files are written to their final organized locations during conversion (not moved afterward), ensuring consistent file management and eliminating post-conversion file moves.

## Directory Structure

MS files are organized into date-based subdirectories:

```
/stage/dsa110-contimg/ms/
├── calibrators/           # Calibrator observations
│   └── YYYY-MM-DD/        # Organized by date
│       ├── <timestamp>.ms/
│       ├── <timestamp>_bpcal/
│       ├── <timestamp>_gpcal/
│       └── <timestamp>_2gcal/
│
├── science/               # Science observations
│   └── YYYY-MM-DD/       # Organized by date
│       └── <timestamp>.ms/
│
└── failed/                # Failed conversions (quarantine)
    └── YYYY-MM-DD/       # Organized by date
        └── <timestamp>.ms/
```

## Implementation

### Core Utility Module

The organization logic is centralized in `src/dsa110_contimg/utils/ms_organization.py`:

- **`create_path_mapper()`**: Creates a path mapper function for direct-to-organized writing
- **`organize_ms_file()`**: Moves MS files to organized locations (for legacy files or manual organization)
- **`get_organized_ms_path()`**: Computes the target organized path without moving files
- **`determine_ms_type()`**: Determines if an MS is a calibrator or failed observation
- **`extract_date_from_filename()`**: Extracts date from MS filename

### Direct-to-Organized Writing (Preferred)

MS files are written directly to organized locations using a `path_mapper` function:

```python
from dsa110_contimg.utils.ms_organization import create_path_mapper
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import convert_subband_groups_to_ms

# Create path mapper for organized output
ms_base_dir = Path('/stage/dsa110-contimg/ms')
path_mapper = create_path_mapper(ms_base_dir, is_calibrator=False, is_failed=False)

# Convert with direct-to-organized writing
convert_subband_groups_to_ms(
    input_dir='/data/incoming',
    output_dir='/stage/dsa110-contimg/ms',
    start_time='2025-10-25T00:01:54',
    end_time='2025-10-25T00:02:54',
    path_mapper=path_mapper  # MS written directly to organized location
)
```

**Benefits:**
- No file moves: Files written directly to final location
- Single database operation: Register once with correct path
- No race conditions: Database always has correct path
- Better performance: Eliminates move operations

### Integration Points

#### 1. Streaming Converter

The streaming converter writes MS files directly to organized locations using `path_mapper`:

```python
# Create path mapper before conversion
path_mapper = create_path_mapper(ms_base_dir, is_calibrator=False, is_failed=False)

# Convert with direct-to-organized writing
convert_subband_groups_to_ms(
    ...,
    path_mapper=path_mapper  # MS written directly to organized location
)
```

**Location**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py:574-625`

**Note**: In subprocess mode (when `--use-subprocess` is used), files are written to flat locations and organized afterward using `organize_ms_file()`.

#### 2. Pipeline Conversion Stage

The `ConversionStage` writes MS files directly to organized locations using `path_mapper`:

```python
# Create path mapper before conversion
path_mapper = create_path_mapper(ms_base_dir, is_calibrator=False, is_failed=False)

# Convert with direct-to-organized writing
convert_subband_groups_to_ms(
    ...,
    path_mapper=path_mapper
)
```

**Location**: `src/dsa110_contimg/pipeline/stages_impl.py:82-95`

#### 3. Organization Stage

A standalone `OrganizationStage` is available for manual workflows or post-processing:

**Location**: `src/dsa110_contimg/pipeline/stages_impl.py:1185-1296`

**Usage**:
```python
from dsa110_contimg.pipeline.stages_impl import OrganizationStage

stage = OrganizationStage(config)
context = stage.execute(context)
```

#### 4. Streaming Mosaic Manager

The `StreamingMosaicManager` uses the shared utility for consistency:

**Location**: `src/dsa110_contimg/mosaic/streaming_mosaic.py:617-658`

## Database Updates

### Direct-to-Organized Writing

When MS files are written directly to organized locations:
- **Single Registration**: MS is registered in the database with the correct organized path immediately
- **No Path Updates**: No need to update paths since files are already in the correct location
- **Consistent State**: Database always reflects actual file locations

### Post-Conversion Organization (Legacy/Manual)

When organizing existing MS files (via `organize_ms_file()`), the `products.sqlite3` database is automatically updated:

1. **Path Update**: The `ms_index` table is updated with the new organized path
2. **Metadata Preservation**: All existing metadata (start_mjd, end_mjd, mid_mjd, status, stage, etc.) is preserved
3. **Old Path Removal**: The old path entry is removed to prevent duplicates

## Benefits

1. **Direct Writing**: Files written directly to organized locations (no post-conversion moves)
2. **Automatic Organization**: Files are organized without manual intervention
3. **Consistent Structure**: All workflows use the same organization logic
4. **Database Consistency**: Database paths always reflect actual file locations
5. **Date-Based Access**: Easy to locate files by observation date
6. **Type Separation**: Clear separation between calibrators, science, and failed observations
7. **Performance**: Eliminates file move operations, reducing I/O overhead
8. **Reusable**: Single utility used across all pipeline components

## Behavior

### Direct-to-Organized Writing
- **Automatic**: Path mapper automatically creates organized paths during conversion
- **Efficient**: No file moves required - files written directly to final location
- **Consistent**: All conversions use the same organization logic

### Post-Conversion Organization (Legacy/Manual)
- **Idempotent**: Organizing an already-organized file has no effect
- **Safe**: If organization fails, the original path is preserved
- **Non-Blocking**: Organization failures don't stop the pipeline
- **Database-Aware**: Automatically updates database paths when moving files

## Manual Organization

To manually organize existing MS files, use the reorganization script:

```bash
/opt/miniforge/envs/casa6/bin/python \
    scripts/reorganize_ms_directory.py \
    --ms-dir /stage/dsa110-contimg/ms \
    [--dry-run]
```

Or use the OrganizationStage in a pipeline workflow.


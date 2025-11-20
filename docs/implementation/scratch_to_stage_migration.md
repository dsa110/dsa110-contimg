# Scratch to Stage Migration Summary

## Overview

All default paths have been updated from `/stage/dsa110-contimg/` to
`/stage/dsa110-contimg/` to align with the new data organization structure.

## Files Updated

### API Layer

- `src/dsa110_contimg/api/routes.py`: Updated docstrings and default scan
  directories
- `src/dsa110_contimg/api/models.py`: Updated default `output_dir`
- `src/dsa110_contimg/api/streaming_service.py`: Updated default paths

### Calibration

- `src/dsa110_contimg/calibration/cli.py`: Updated temp environment default

### Imaging

- `src/dsa110_contimg/imaging/cli_imaging.py`: Updated default scratch root
- `src/dsa110_contimg/imaging/worker.py`: Updated temp environment default

### Mosaic

- `src/dsa110_contimg/mosaic/cli.py`: Updated default scratch directory

### Conversion

- `src/dsa110_contimg/conversion/config.py`: Updated default output directory
- `src/dsa110_contimg/conversion/streaming/streaming_converter.py`: Updated
  default scratch directory

### Pipeline

- `src/dsa110_contimg/pipeline/config.py`: Updated default output directory

### Utilities

- `src/dsa110_contimg/utils/cli_helpers.py`: Updated default scratch base
- `src/dsa110_contimg/utils/tempdirs.py`: Updated default paths and
  documentation

## Remaining `/scratch/` References

The following references to `/scratch/` are **intentional** and should remain:

1. **Docker volume mounts**:
   - `calibration/flagging.py`: `-v /scratch:/scratch` (mounts host scratch for
     Docker)
   - `calibration/dp3_wrapper.py`: `-v /scratch:/scratch` (mounts host scratch
     for Docker)
   - `imaging/cli_imaging.py`: `-v /scratch:/scratch` (mounts host scratch for
     Docker)
   - These are Docker volume mounts and are correct as-is

2. **Documentation/Examples**:
   - `calibration/skymodels.py`: Example docstring path
   - `conversion/cli.py`: Example command in help text
   - `calibration/cubical_experimental/README.md`: Example paths
   - These are documentation only and don't affect runtime behavior

3. **Path validation**:
   - `calibration/flagging.py`: Checks if strategy file is under `/data` or
     `/scratch` (for Docker mounts)
   - This validation is correct as Docker containers need access to these mounts

## Environment Variables

All defaults now use `/stage/`, but can be overridden with:

- `CONTIMG_OUTPUT_DIR`: Defaults to `/stage/dsa110-contimg/ms`
- `CONTIMG_SCRATCH_DIR`: Defaults to `/stage/dsa110-contimg`
- `CONTIMG_CAL_DIR`: Defaults to `/stage/dsa110-contimg/caltables`

## Migration Complete

All automated pipeline code now defaults to `/stage/` instead of `/scratch/`.
The `/scratch/` directory remains available for:

- Manual testing and development
- Docker volume mounts (which map host paths)
- Temporary files that don't need to be tracked

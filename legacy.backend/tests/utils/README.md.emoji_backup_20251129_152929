# Test Utilities

This directory contains test utilities for the DSA-110 continuum imaging
pipeline.

## Refactored Utilities

### `convert_uvh5_refactored.py`

**Purpose**: Refactored version of old standalone converters that now uses
production modules.

**Status**: ✅ **Use this instead of archived versions**

**Key improvements**:

- Uses production `find_subband_groups` and `convert_subband_groups_to_ms`
- No duplicate code - single source of truth
- Includes validation modes (`--validate-only`, `--validate-calibrator`)
- Demonstrates proper usage of production modules

**Usage**:

```bash
# Normal conversion (use production CLI instead)
python tests/utils/convert_uvh5_refactored.py /data/incoming /data/ms "2025-10-30 10:00:00" "2025-10-30 11:00:00"

# Validation mode
python tests/utils/convert_uvh5_refactored.py /data/incoming /data/ms "2025-10-30 10:00:00" "2025-10-30 11:00:00" --validate-only

# Calibrator validation
python tests/utils/convert_uvh5_refactored.py /data/incoming /data/ms "2025-10-30 10:00:00" "2025-10-30 11:00:00" --validate-calibrator 0834+555
```

**Note**: For most use cases, prefer the production CLI:

```bash
python -m dsa110_contimg.conversion.cli groups ...
python -m dsa110_contimg.conversion.cli validate ...
```

## Archived Utilities

The following utilities have been archived due to duplicate code:

- `convert_uvh5_standalone.py` →
  `archive/tests/utils/convert_uvh5_standalone.py.archived`
- `convert_uvh5_simple.py` →
  `archive/tests/utils/convert_uvh5_simple.py.archived`

**Reason**: These contained duplicate implementations of `find_subband_groups`
and core conversion logic that should use production modules instead.

**Migration**: Use `convert_uvh5_refactored.py` or the production CLI.

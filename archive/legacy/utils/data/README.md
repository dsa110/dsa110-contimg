# Archived Data Files

**Date:** 2025-11-05  
**Reason:** Duplicate antenna coordinate data file

## Archived File

- `DSA110_Station_Coordinates.csv` - Duplicate of `src/dsa110_contimg/utils/antpos_local/data/DSA110_Station_Coordinates.csv`

## Current Location

The canonical version is at:
- `src/dsa110_contimg/utils/antpos_local/data/DSA110_Station_Coordinates.csv`

All code should use `antpos_local` utilities which access this file via `importlib.resources`.

## Migration

If you need this file, use:
```python
from dsa110_contimg.utils.antpos_local import get_itrf
# or
from dsa110_contimg.utils.antpos_local.utils import get_itrf
```


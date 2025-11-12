#!/usr/bin/env python3
"""
Legacy NVSS overlay utility (archived).

This script has been superseded by a simplified version at:
  ops/pipeline/overlay_nvss_on_image.py

The new tool avoids astroquery and uses a cached NVSS catalog via
dsa110_contimg.calibration.catalogs.read_nvss_catalog().

If you need the original astroquery/Vizier behavior, refer to the Git
history for this file or re-enable astroquery-based queries in the new
script.
"""

import sys
print("This legacy script has been archived. Use ops/pipeline/overlay_nvss_on_image.py.")
sys.exit(0)


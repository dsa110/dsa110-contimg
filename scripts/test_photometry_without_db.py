#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test what happens when photometry runs without a populated database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dsa110_contimg.photometry.normalize import query_reference_sources

print("Testing photometry normalization with empty database...")
print("="*70)

try:
    refs = query_reference_sources(
        db_path=Path("/data/dsa110-contimg/state/master_sources.sqlite3"),
        ra_center=105.0,  # 0702+445 field
        dec_center=44.5,
        fov_radius_deg=1.5,
        min_snr=50.0,
        max_sources=20,
    )
    print(f"✓ Query succeeded (should have failed!)")
    print(f"  Found {len(refs)} reference sources")
    
except Exception as e:
    print(f"✗ Query failed as expected: {type(e).__name__}")
    print(f"  Error: {e}")


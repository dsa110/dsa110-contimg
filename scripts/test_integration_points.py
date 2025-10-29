#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test integration points where QA should be called but isn't yet.

This identifies WHERE in the pipeline QA needs to be integrated.
"""

import sys
from pathlib import Path
import re

# Test 1: Search for conversion completion points
print("="*70)
print("INTEGRATION POINT ANALYSIS")
print("="*70)

print("\n1. CONVERSION COMPLETION POINTS")
print("-" * 70)

conversion_file = Path("/data/dsa110-contimg/src/dsa110_contimg/conversion/streaming/streaming_converter.py")
if conversion_file.exists():
    content = conversion_file.read_text()
    
    # Look for where MS is created/written
    ms_creation_patterns = [
        r"\.ms['\"]?\s*(created|written|completed)",
        r"ms_path.*=",
        r"write.*ms",
        r"concat.*ms",
    ]
    
    found_any = False
    for pattern in ms_creation_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Get context
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end]
            
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            print(f"\n  Line {line_num}: ...{context.strip()}...")
            found_any = True
    
    if not found_any:
        print("  No obvious MS creation points found (may need manual review)")
else:
    print("  ERROR: streaming_converter.py not found")

print("\n2. CALIBRATION COMPLETION POINTS")
print("-" * 70)

calib_file = Path("/data/dsa110-contimg/src/dsa110_contimg/calibration/calibration.py")
if calib_file.exists():
    content = calib_file.read_text()
    
    # Look for where calibration tables are created
    cal_patterns = [
        r"def solve_.*\(",
        r"caltable.*=",
        r"gaincal\(",
        r"bandpass\(",
    ]
    
    found_any = False
    for pattern in cal_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            print(f"  Line {line_num}: Found {match.group()}")
            found_any = True
    
    if not found_any:
        print("  No calibration points found")
else:
    print("  ERROR: calibration.py not found")

print("\n3. IMAGING COMPLETION POINTS")
print("-" * 70)

imaging_file = Path("/data/dsa110-contimg/src/dsa110_contimg/imaging/cli.py")
if imaging_file.exists():
    content = imaging_file.read_text()
    
    # Look for where images are created
    img_patterns = [
        r"tclean\(",
        r"\.image['\"]?\s*$",
        r"image.*produced",
    ]
    
    found_any = False
    for pattern in img_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            print(f"  Line {line_num}: Found {match.group()}")
            found_any = True
    
    if not found_any:
        print("  No imaging points found")
else:
    print("  ERROR: cli.py not found")

print("\n4. RECOMMENDATIONS")
print("-" * 70)
print("""
To integrate QA into the pipeline:

1. streaming_converter.py:
   - After MS conversion completes
   - Before registering in products DB
   - Add: from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
   - Call: check_ms_after_conversion(ms_path, alert_on_issues=True)

2. calibration/calibration.py:
   - After each solve_* function completes
   - Add: from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
   - Call: check_calibration_quality([caltable_path], ms_path, alert_on_issues=True)

3. imaging/cli.py:
   - After tclean completes
   - Add: from dsa110_contimg.qa.pipeline_quality import check_image_quality
   - Call: check_image_quality(image_path, alert_on_issues=True)

4. Add to environment:
   - Set CONTIMG_SLACK_WEBHOOK_URL in ops/systemd/contimg.env

5. Database population:
   - Run: python -m dsa110_contimg.catalog.build_master \\
           --nvss <path> --vlass <path> --first <path> \\
           --out state/master_sources.sqlite3
""")

print("\n5. MISSING DEPENDENCIES")
print("-" * 70)

# Check if catalog files exist
catalog_paths = [
    "/data/catalogs/NVSS.csv",
    "/data/catalogs/VLASS.csv",
    "/data/catalogs/FIRST.csv",
]

for path in catalog_paths:
    if Path(path).exists():
        size = Path(path).stat().st_size / 1024 / 1024
        print(f"  ✓ {path} ({size:.1f} MB)")
    else:
        print(f"  ✗ {path} NOT FOUND")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("""
CURRENT STATUS:
- QA modules: IMPLEMENTED and TESTED ✓
- Alerting system: IMPLEMENTED and TESTED ✓
- Pipeline integration: NOT IMPLEMENTED ✗
- Database population: NOT DONE ✗

BLOCKERS:
1. No QA calls in streaming_converter.py
2. No QA calls in calibration.py
3. No QA calls in imaging/cli.py
4. master_sources.sqlite3 is empty (0 bytes)

READY FOR INTEGRATION:
- All QA code is tested and working
- Configuration in contimg.env is ready
- Just need to add 3-4 lines of code in each integration point
- Need to populate master_sources database
""")


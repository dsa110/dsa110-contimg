#!/bin/bash
# Build mosaic only (no visualizations)
# Run this in foreground to see progress

cd /data/dsa110-contimg
export PYTHONPATH=/data/dsa110-contimg/src:$PYTHONPATH

/opt/miniforge/envs/casa6/bin/python << 'PYTHON_EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.mosaic.cli import _fetch_tiles, _build_weighted_mosaic_linearmosaic
from dsa110_contimg.mosaic.validation import TileQualityMetrics

products_db = Path("/data/dsa110-contimg/state/products.sqlite3")

# Fetch tiles from /stage/
all_tiles = _fetch_tiles(products_db, since=None, until=None, pbcor_only=True)
stage_tiles = [t for t in all_tiles if t.startswith('/stage/')]
test_tiles = stage_tiles[:3]

print(f"Using {len(test_tiles)} tiles:")
for i, t in enumerate(test_tiles, 1):
    print(f"  {i}. {Path(t).name}")

# Create metrics dict
metrics_dict = {t: TileQualityMetrics(tile_path=t) for t in test_tiles}

# Build mosaic
output_path = "/stage/dsa110-contimg/tmp/mosaic_test"
print(f"\nBuilding mosaic to: {output_path}")
print("This may take several minutes...\n")

try:
    _build_weighted_mosaic_linearmosaic(
        tiles=test_tiles,
        metrics_dict=metrics_dict,
        output_path=output_path
    )
    print(f"\n✓ Mosaic built successfully at: {output_path}")
except Exception as e:
    print(f"\n✗ Mosaic build failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_EOF

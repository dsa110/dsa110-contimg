#!/bin/bash
# Pre-generate GSM cache for fast sky map rendering
# This only needs to be run once (or after clearing cache)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ":milky_way: Pre-generating GSM cache for sky maps..."
echo "   This will take ~30 seconds but only needs to be done once."
echo ""

# Use casa6 Python environment
PYTHON="/opt/miniforge/envs/casa6/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo ":cross: casa6 Python not found at $PYTHON"
    echo "   Please ensure casa6 environment is installed."
    exit 1
fi

# Pre-generate GSM cache for 1.4 GHz (most common)
echo ":satellite: Generating GSM at 1400 MHz..."
$PYTHON -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')
from dsa110_contimg.pointing.sky_map_generator import get_or_generate_gsm_cache

# Generate cache for 1400 MHz (most common)
print('Generating GSM cache at 1400 MHz...')
get_or_generate_gsm_cache(frequency_mhz=1400.0, force_regenerate=False)
print(':check: GSM cache generated!')
"

echo ""
echo ":check: GSM cache pre-generated successfully!"
echo "   Future sky map generations will now be fast (~3-5 seconds)"
echo ""
echo ":location: Cache location: $PROJECT_ROOT/state/pointing/gsm_cache/"
echo ""
echo "To force regeneration, run:"
echo "  $PYTHON -c 'from dsa110_contimg.pointing.sky_map_generator import get_or_generate_gsm_cache; get_or_generate_gsm_cache(1400.0, force_regenerate=True)'"

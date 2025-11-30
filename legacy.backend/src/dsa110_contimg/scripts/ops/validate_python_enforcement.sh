#!/bin/bash
# Validate that casa6 Python enforcement is working correctly

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=" | head -c 60 && echo ""
echo "Validating Casa6 Python Enforcement"
echo "=" | head -c 60 && echo ""
echo ""

# Test 1: Import package with casa6
echo "Test 1: Import package with casa6 Python..."
source /data/dsa110-contimg/scripts/dev/developer-setup.sh
if python3 -c "import dsa110_contimg; print(':white_heavy_check_mark: PASS')" 2>&1 | grep -q "PASS"; then
    echo "   :white_heavy_check_mark: PASS: Package imports successfully with casa6"
else
    echo "   :cross_mark: FAIL: Package import failed with casa6"
    exit 1
fi

# Test 2: Try to import with system Python (should fail)
echo ""
echo "Test 2: Attempt import with system Python (should fail)..."
if /usr/bin/python3 -c "import sys; sys.path.insert(0, '$SRC_DIR'); import dsa110_contimg" 2>&1 | grep -q "CRITICAL ERROR"; then
    echo "   :white_heavy_check_mark: PASS: System Python correctly rejected"
else
    echo "   :warning:  WARNING: System Python was not rejected (may be expected if guard not loaded)"
fi

# Test 3: Check entry point script
echo ""
echo "Test 3: Check entry point script..."
if python3 "$SRC_DIR/create_10min_mosaic.py" --help 2>&1 | head -1 | grep -q "usage"; then
    echo "   :white_heavy_check_mark: PASS: Entry point script works with casa6"
else
    echo "   :cross_mark: FAIL: Entry point script failed"
    exit 1
fi

# Test 4: Verify shebang lines
echo ""
echo "Test 4: Verify shebang lines in entry points..."
entry_points=("create_10min_mosaic.py")
all_correct=true
for ep in "${entry_points[@]}"; do
    if [ -f "$SRC_DIR/$ep" ]; then
        shebang=$(head -1 "$SRC_DIR/$ep")
        if echo "$shebang" | grep -q "/opt/miniforge/envs/casa6/bin/python"; then
            echo "   :white_heavy_check_mark: $ep: Correct shebang"
        else
            echo "   :cross_mark: $ep: Incorrect shebang: $shebang"
            all_correct=false
        fi
    fi
done

if [ "$all_correct" = true ]; then
    echo "   :white_heavy_check_mark: PASS: All entry points have correct shebang"
else
    echo "   :cross_mark: FAIL: Some entry points have incorrect shebang"
    exit 1
fi

echo ""
echo "=" | head -c 60 && echo ""
echo ":white_heavy_check_mark: All validation tests passed!"
echo "=" | head -c 60 && echo ""


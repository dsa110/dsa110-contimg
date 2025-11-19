#!/bin/bash

# List of modules moved to src/dsa110_contimg
MODULES="database api pipeline photometry mosaic qa beam config pointing simulation"

# Iterate over each module and update imports in all Python files
for mod in $MODULES; do
    echo "Updating imports for $mod..."
    # distinct 'from module' imports
    find src/dsa110_contimg -name "*.py" -print0 | xargs -0 sed -i "s/^from $mod/from dsa110_contimg.$mod/g"
    
    # 'import module' -> 'from dsa110_contimg import module' (to preserve module.member access)
    find src/dsa110_contimg -name "*.py" -print0 | xargs -0 sed -i "s/^import $mod\b/from dsa110_contimg import $mod/g"
done

echo "Refactoring complete."


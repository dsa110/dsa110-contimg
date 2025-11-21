#!/bin/bash
# This helper used to flip CONTIMG_USE_NEW_STRUCTURE.
# The consolidated directory layout is now always enabled, so we keep this
# script only to inform users who might still try to source it.

cat <<'MSG'
The DSA-110 pipeline now always uses the consolidated /stage/dsa110-contimg
layout (raw/ms, calibrated/ms, calibrated/tables, etc.).  No environment
variable is required. You can remove references to enable_new_structure.sh
from your shell startup scripts.
MSG


#!/bin/bash
# Start MkDocs documentation server for DSA-110
# Used by systemd mkdocs.service
#
# Port 8001 is claimed by ExecStartPre in the systemd service.

set -e

cd /data/dsa110-contimg

# Ensure we use the correct Python from casa6 environment
export PATH="/opt/miniforge/envs/casa6/bin:$PATH"

# Run mkdocs serve on port 8001
exec mkdocs serve --dev-addr 127.0.0.1:8001

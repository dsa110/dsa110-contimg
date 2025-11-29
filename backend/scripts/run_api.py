#!/usr/bin/env python3
"""
Entry point for running the DSA-110 API with automatic port reservation.

This mirrors how the frontend uses predev hooks in package.json.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add scripts directory to path for ensure_port import
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from ensure_port import ensure_port_available


def main():
    """Run the API server with port reservation."""
    port = int(os.environ.get("API_PORT", "8000"))
    host = os.environ.get("API_HOST", "0.0.0.0")
    reload_enabled = os.environ.get("API_RELOAD", "1") == "1"
    
    # Ensure port is available (like frontend's predev hook)
    if not ensure_port_available(port):
        print(f"[run-api] ERROR: Could not free port {port}", file=sys.stderr)
        sys.exit(1)
    
    # Start uvicorn
    print(f"[run-api] Starting uvicorn on {host}:{port}...")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "dsa110_contimg.api.app:app",
        "--host", host,
        "--port", str(port),
    ]
    
    if reload_enabled:
        cmd.append("--reload")
    
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()

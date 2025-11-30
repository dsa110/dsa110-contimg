#!/usr/bin/env python3
"""
PRIMARY ENTRY POINT for running the DSA-110 Continuum Imaging API.

This script handles port reservation and starts the FastAPI server.

Usage:
    python scripts/ops/run_api.py

Environment Variables:
    API_PORT   - Port to listen on (default: 8000)
    API_HOST   - Host to bind to (default: 0.0.0.0)
    API_RELOAD - Enable auto-reload (default: 1)

Alternative:
    python -m uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000
"""

import os
import subprocess
import sys
from pathlib import Path

# Add ops directory to path for ensure_port import
ops_dir = Path(__file__).parent
sys.path.insert(0, str(ops_dir))

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

#!/usr/bin/env python3
"""
DSA-110 Streaming Data Pipeline Launcher.

This script provides a simple entry point for running the streaming data
pipeline without needing systemd or shell wrapper scripts. It can be run
directly or installed as a console script via pip.

Usage:
    # Direct execution
    python -m dsa110_contimg.conversion.streaming.launcher --input-dir /data/incoming --output-dir /data/ms
    
    # Or if installed as console script
    dsa110-stream --input-dir /data/incoming --output-dir /data/ms

Environment Variables:
    CASA_LOGDIR: Directory for CASA log files (default: /tmp/casa_logs)
    OMP_NUM_THREADS: Number of OpenMP threads (default: 4)
    
Signals:
    SIGINT (Ctrl+C): Graceful shutdown
    SIGTERM: Graceful shutdown
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Main entry point for the streaming pipeline launcher.
    
    Returns:
        Exit code
    """
    # Set up environment before any imports
    _setup_environment()
    
    # Import and run the CLI
    from dsa110_contimg.conversion.streaming.cli import main as cli_main
    return cli_main()


def _setup_environment() -> None:
    """Set up environment variables for CASA and processing."""
    # Set CASA log directory if not already set
    if "CASA_LOGDIR" not in os.environ:
        log_dir = "/tmp/casa_logs"
        os.makedirs(log_dir, exist_ok=True)
        os.environ["CASA_LOGDIR"] = log_dir
    
    # Set OMP threads if not already set (prevent thread explosion)
    if "OMP_NUM_THREADS" not in os.environ:
        os.environ["OMP_NUM_THREADS"] = "4"
    
    # Set OPENBLAS threads to prevent conflicts
    if "OPENBLAS_NUM_THREADS" not in os.environ:
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
    
    # Disable MKL threading if using Intel MKL
    if "MKL_NUM_THREADS" not in os.environ:
        os.environ["MKL_NUM_THREADS"] = "1"


if __name__ == "__main__":
    sys.exit(main())

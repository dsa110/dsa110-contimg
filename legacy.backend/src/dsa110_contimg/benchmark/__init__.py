"""
DSA-110 Pipeline Performance Benchmarking

This module provides a CLI wrapper for running airspeed-velocity (asv) benchmarks
against the dsa110-contimg pipeline. It simplifies benchmark execution for both
novice and expert users.

Quick Start
-----------
    # Quick benchmark check (single iteration)
    dsa110-benchmark quick

    # Full benchmark suite with statistics
    dsa110-benchmark run

    # Generate HTML report
    dsa110-benchmark report

See Also
--------
- benchmarks/README.md for detailed documentation
- docs/guides/benchmarking.md for comprehensive guide
- https://asv.readthedocs.io/ for ASV documentation
"""

from .cli import main

__all__ = ["main"]

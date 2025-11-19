"""
Experimental CubiCal calibration module.

This module provides a standalone CubiCal-based calibration implementation
that can be tested independently without modifying the existing CASA-based
pipeline.

This is a proof-of-concept implementation to evaluate:
- GPU acceleration performance
- Calibration quality compared to CASA
- Integration feasibility

Usage:
    python -m dsa110_contimg.calibration.cubical_experimental.cubical_cli \
        --ms <ms_path> --auto-fields

Note: This module requires CubiCal to be installed separately.
"""

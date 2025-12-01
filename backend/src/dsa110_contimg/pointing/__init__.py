"""
Pointing Module - Monitors telescope pointing and calibrator transits.

This module provides:
- Calibrator transit prediction based on LST
- Pointing history tracking
- Active observation monitoring
- Transit window calculations for scheduling

The pointing monitor runs as a systemd service that:
1. Tracks upcoming calibrator transits
2. Updates status files for health monitoring
3. Logs transit events for pipeline coordination
"""

from .monitor import (
    PointingMonitor,
    TransitPrediction,
    calculate_lst,
    predict_calibrator_transit,
    get_active_calibrator,
)

__all__ = [
    "PointingMonitor",
    "TransitPrediction",
    "calculate_lst",
    "predict_calibrator_transit",
    "get_active_calibrator",
]

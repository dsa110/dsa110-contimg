"""Lightweight CASA 6.7 calibration helpers (no dsacalib runtime deps).

Modules:
- catalogs: NVSS/VLA calibrator parsing and declination caltable generation
- flagging: CASA flagging wrappers
- calibration: delay, bandpass, gain solving helpers
- applycal: application of calibration tables to target MS
- qa: plotting utilities
- cli: command-line interface to run the pipeline

Notes
- Transit utilities (meridian/HA=0) live in `schedule.py` (e.g., `previous_transits`, `next_transit_time`, `OVRO`).
- Calibrator matching integrates with the streaming pipeline and monitoring API; see docs/README.md “Calibrator Matching & Transits”.
"""

__all__ = [
    "catalogs",
    "flagging",
    "calibration",
    "applycal",
    "qa",
]


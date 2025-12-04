"""
Pipeline stages for streaming converter.

Each stage represents a distinct processing step:
- ConversionStage: HDF5 → MS conversion
- CalibrationStage: Calibration solving and application
- ImagingStage: Image generation from MS
- PhotometryStage: Source measurement
- MosaicStage: Multi-observation mosaic creation

Stages follow the PipelineStage interface from the pipeline module,
enabling composition and reuse.
"""

from __future__ import annotations

from .conversion import ConversionStage
from .calibration import CalibrationStage
from .imaging import ImagingStage
from .photometry import PhotometryStage
from .mosaic import MosaicStage

__all__ = [
    "ConversionStage",
    "CalibrationStage", 
    "ImagingStage",
    "PhotometryStage",
    "MosaicStage",
]

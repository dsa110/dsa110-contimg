"""
Unified configuration system for pipeline execution.

Provides type-safe, validated configuration using Pydantic with support for
multiple configuration sources (environment variables, files, dictionaries).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class PathsConfig(BaseModel):
    """Path configuration for pipeline execution."""
    
    input_dir: Path = Field(..., description="Input directory for UVH5 files")
    output_dir: Path = Field(..., description="Output directory for MS files")
    scratch_dir: Optional[Path] = Field(None, description="Scratch directory for temporary files")
    state_dir: Path = Field(default=Path("state"), description="State directory for databases")
    
    @property
    def products_db(self) -> Path:
        """Path to products database."""
        return self.state_dir / "products.sqlite3"
    
    @property
    def registry_db(self) -> Path:
        """Path to calibration registry database."""
        return self.state_dir / "cal_registry.sqlite3"
    
    @property
    def queue_db(self) -> Path:
        """Path to queue database."""
        return self.state_dir / "ingest.sqlite3"


class ConversionConfig(BaseModel):
    """Configuration for conversion stage (UVH5 → MS)."""
    
    writer: str = Field(default="auto", description="Writer strategy: 'auto', 'parallel-subband', or 'pyuvdata'")
    max_workers: int = Field(default=4, ge=1, le=32, description="Maximum number of parallel workers")
    stage_to_tmpfs: bool = Field(default=True, description="Stage files to tmpfs for faster I/O")
    expected_subbands: int = Field(default=16, ge=1, le=32, description="Expected number of subbands")


class CalibrationConfig(BaseModel):
    """Configuration for calibration stage."""
    
    cal_bp_minsnr: float = Field(default=3.0, ge=1.0, le=10.0, description="Minimum SNR for bandpass calibration")
    cal_gain_solint: str = Field(default="inf", description="Gain solution interval")
    default_refant: str = Field(default="103", description="Default reference antenna")
    auto_select_refant: bool = Field(default=True, description="Automatically select reference antenna")


class ImagingConfig(BaseModel):
    """Configuration for imaging stage."""
    
    field: Optional[str] = Field(None, description="Field name or coordinates")
    refant: Optional[str] = Field(default="103", description="Reference antenna")
    gridder: str = Field(default="wproject", description="Gridding algorithm")
    wprojplanes: int = Field(default=-1, description="W-projection planes (-1 for auto)")


class PipelineConfig(BaseModel):
    """Complete pipeline configuration.
    
    This is the single source of truth for all pipeline configuration.
    Supports loading from environment variables, files, or dictionaries.
    """
    
    paths: PathsConfig
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    imaging: ImagingConfig = Field(default_factory=ImagingConfig)
    
    @classmethod
    def from_env(cls) -> PipelineConfig:
        """Load configuration from environment variables.
        
        Environment variables:
            PIPELINE_INPUT_DIR: Input directory (required)
            PIPELINE_OUTPUT_DIR: Output directory (required)
            PIPELINE_SCRATCH_DIR: Scratch directory (optional)
            PIPELINE_STATE_DIR: State directory (default: "state")
            PIPELINE_WRITER: Writer strategy (default: "auto")
            PIPELINE_MAX_WORKERS: Max workers (default: 4)
            PIPELINE_EXPECTED_SUBBANDS: Expected subbands (default: 16)
            
        Returns:
            PipelineConfig instance
        """
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        
        input_dir = os.getenv("PIPELINE_INPUT_DIR")
        output_dir = os.getenv("PIPELINE_OUTPUT_DIR")
        
        if not input_dir or not output_dir:
            raise ValueError(
                "PIPELINE_INPUT_DIR and PIPELINE_OUTPUT_DIR environment variables required"
            )
        
        scratch_dir = os.getenv("PIPELINE_SCRATCH_DIR")
        
        return cls(
            paths=PathsConfig(
                input_dir=Path(input_dir),
                output_dir=Path(output_dir),
                scratch_dir=Path(scratch_dir) if scratch_dir else None,
                state_dir=base_state,
            ),
            conversion=ConversionConfig(
                writer=os.getenv("PIPELINE_WRITER", "auto"),
                max_workers=int(os.getenv("PIPELINE_MAX_WORKERS", "4")),
                stage_to_tmpfs=os.getenv("PIPELINE_STAGE_TO_TMPFS", "true").lower() == "true",
                expected_subbands=int(os.getenv("PIPELINE_EXPECTED_SUBBANDS", "16")),
            ),
            calibration=CalibrationConfig(
                cal_bp_minsnr=float(os.getenv("PIPELINE_CAL_BP_MINSNR", "3.0")),
                cal_gain_solint=os.getenv("PIPELINE_CAL_GAIN_SOLINT", "inf"),
                default_refant=os.getenv("PIPELINE_DEFAULT_REFANT", "103"),
                auto_select_refant=os.getenv("PIPELINE_AUTO_SELECT_REFANT", "true").lower() == "true",
            ),
            imaging=ImagingConfig(
                field=os.getenv("PIPELINE_FIELD"),
                refant=os.getenv("PIPELINE_REFANT", "103"),
                gridder=os.getenv("PIPELINE_GRIDDER", "wproject"),
                wprojplanes=int(os.getenv("PIPELINE_WPROJPLANES", "-1")),
            ),
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PipelineConfig:
        """Load configuration from dictionary (e.g., API request).
        
        Args:
            data: Dictionary with configuration values
            
        Returns:
            PipelineConfig instance
        """
        # Handle legacy format where paths are at top level
        if "input_dir" in data and "paths" not in data:
            paths_data = {
                "input_dir": data.pop("input_dir", "/data/incoming"),
                "output_dir": data.pop("output_dir", "/scratch/dsa110-contimg/ms"),
                "scratch_dir": data.pop("scratch_dir", None),
                "state_dir": data.pop("state_dir", "state"),
            }
            data["paths"] = paths_data
        
        # Handle nested conversion config
        if "writer" in data and "conversion" not in data:
            conversion_data = {
                "writer": data.pop("writer", "auto"),
                "max_workers": data.pop("max_workers", 4),
                "stage_to_tmpfs": data.pop("stage_to_tmpfs", True),
                "expected_subbands": data.pop("expected_subbands", 16),
            }
            data["conversion"] = conversion_data
        
        # Handle nested imaging config
        if "field" in data and "imaging" not in data:
            imaging_data = {
                "field": data.pop("field", None),
                "refant": data.pop("refant", "103"),
                "gridder": data.pop("gridder", "wproject"),
                "wprojplanes": data.pop("wprojplanes", -1),
            }
            data["imaging"] = imaging_data
        
        return cls.model_validate(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return self.model_dump()


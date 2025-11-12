"""
Unified configuration system for pipeline execution.

Provides type-safe, validated configuration using Pydantic with support for
multiple configuration sources (environment variables, files, dictionaries).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    """Path configuration for pipeline execution."""

    input_dir: Path = Field(..., description="Input directory for UVH5 files")
    output_dir: Path = Field(..., description="Output directory for MS files")
    scratch_dir: Optional[Path] = Field(
        None, description="Scratch directory for temporary files"
    )
    state_dir: Path = Field(
        default=Path("state"), description="State directory for databases"
    )

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

    @property
    def synthetic_images_dir(self) -> Path:
        """Path to synthetic images directory."""
        return self.synthetic_dir / "images"

    @property
    def synthetic_ms_dir(self) -> Path:
        """Path to synthetic MS files directory."""
        return self.synthetic_dir / "ms"


class ConversionConfig(BaseModel):
    """Configuration for conversion stage (UVH5 → MS)."""

    writer: str = Field(
        default="auto",
        description="Writer strategy: 'auto', 'parallel-subband', or 'pyuvdata'",
    )
    max_workers: int = Field(
        default=16, ge=1, le=32, description="Maximum number of parallel workers"
    )
    stage_to_tmpfs: bool = Field(
        default=True, description="Stage files to tmpfs for faster I/O"
    )
    expected_subbands: int = Field(
        default=16, ge=1, le=32, description="Expected number of subbands"
    )
    skip_validation_during_conversion: bool = Field(
        default=True, description="Skip validation checks during conversion (do after)"
    )
    skip_calibration_recommendations: bool = Field(
        default=True, description="Skip writing calibration recommendations JSON files"
    )


class CalibrationConfig(BaseModel):
    """Configuration for calibration stage."""

    cal_bp_minsnr: float = Field(
        default=3.0, ge=1.0, le=10.0, description="Minimum SNR for bandpass calibration"
    )
    cal_gain_solint: str = Field(default="inf", description="Gain solution interval")
    default_refant: str = Field(default="103", description="Default reference antenna")
    auto_select_refant: bool = Field(
        default=True, description="Automatically select reference antenna"
    )


class ImagingConfig(BaseModel):
    """Configuration for imaging stage."""

    field: Optional[str] = Field(None, description="Field name or coordinates")
    refant: Optional[str] = Field(default="103", description="Reference antenna")
    gridder: str = Field(default="wproject", description="Gridding algorithm")
    wprojplanes: int = Field(
        default=-1, description="W-projection planes (-1 for auto)"
    )
    run_catalog_validation: bool = Field(
        default=True,
        description="Run catalog-based flux scale validation after imaging",
    )
    catalog_validation_catalog: str = Field(
        default="nvss", description="Catalog to use for validation ('nvss' or 'vlass')"
    )

    # Masking parameters
    use_nvss_mask: bool = Field(
        default=True, description="Use NVSS-based mask for imaging (2-4x faster)"
    )
    mask_radius_arcsec: float = Field(
        default=60.0,
        ge=10.0,
        le=300.0,
        description="Mask radius around NVSS sources (arcsec)",
    )


class ValidationConfig(BaseModel):
    """Configuration for validation stage."""

    enabled: bool = Field(default=True, description="Enable validation stage")
    catalog: str = Field(
        default="nvss", description="Catalog to use for validation ('nvss' or 'vlass')"
    )
    validation_types: List[str] = Field(
        default=["astrometry", "flux_scale", "source_counts"],
        description="Types of validation to run",
    )
    generate_html_report: bool = Field(
        default=True, description="Generate HTML validation report"
    )
    min_snr: float = Field(default=5.0, description="Minimum SNR for source detection")
    search_radius_arcsec: float = Field(
        default=10.0, description="Search radius for source matching (arcsec)"
    )
    completeness_threshold: float = Field(
        default=0.95, description="Completeness threshold for source counts analysis"
    )


class CrossMatchConfig(BaseModel):
    """Configuration for cross-matching stage."""

    enabled: bool = Field(default=True, description="Enable cross-matching stage")
    catalog_types: List[str] = Field(
        default=["nvss"],
        description="Catalogs to cross-match against ('nvss', 'first', 'rax')",
    )
    radius_arcsec: float = Field(
        default=10.0,
        ge=0.1,
        le=60.0,
        description="Cross-match radius in arcseconds",
    )
    method: str = Field(
        default="basic",
        description="Matching method: 'basic' (nearest neighbor) or 'advanced' (all matches)",
    )
    store_in_database: bool = Field(
        default=True,
        description="Store cross-match results in database",
    )
    min_separation_arcsec: float = Field(
        default=0.1,
        ge=0.0,
        description="Minimum separation to consider a valid match (arcsec)",
    )
    max_separation_arcsec: float = Field(
        default=60.0,
        ge=1.0,
        description="Maximum separation to consider a valid match (arcsec)",
    )


class PhotometryConfig(BaseModel):
    """Configuration for adaptive binning photometry stage."""

    enabled: bool = Field(
        default=False, description="Enable adaptive binning photometry stage"
    )
    target_snr: float = Field(
        default=5.0, ge=1.0, description="Target SNR threshold for detections"
    )
    max_width: int = Field(
        default=16, ge=1, le=32, description="Maximum bin width in channels"
    )
    sources: Optional[List[Dict[str, float]]] = Field(
        default=None,
        description="List of source coordinates [{'ra': 124.526, 'dec': 54.620}, ...]. "
        "If None, queries NVSS catalog for sources in field.",
    )
    min_flux_mjy: float = Field(
        default=10.0, description="Minimum NVSS flux (mJy) for catalog sources"
    )
    parallel: bool = Field(
        default=True, description="Image SPWs in parallel for faster processing"
    )
    max_workers: Optional[int] = Field(
        default=None,
        description="Maximum number of parallel workers (default: CPU count)",
    )
    serialize_ms_access: bool = Field(
        default=True,
        description="Serialize MS access using file locking when processing multiple sources",
    )
    imsize: int = Field(default=1024, ge=256, description="Image size in pixels")
    quality_tier: str = Field(
        default="standard",
        description="Imaging quality tier: 'development', 'standard', or 'high_precision'",
    )
    backend: str = Field(
        default="tclean", description="Imaging backend: 'tclean' or 'wsclean'"
    )


class PipelineConfig(BaseModel):
    """Complete pipeline configuration.

    This is the single source of truth for all pipeline configuration.
    Supports loading from environment variables, files, or dictionaries.
    """

    paths: PathsConfig
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    imaging: ImagingConfig = Field(default_factory=ImagingConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    crossmatch: CrossMatchConfig = Field(default_factory=CrossMatchConfig)
    photometry: PhotometryConfig = Field(default_factory=PhotometryConfig)

    @classmethod
    def from_env(
        cls, validate_paths: bool = True, required_disk_gb: float = 50.0
    ) -> PipelineConfig:
        """Load configuration from environment variables.

        Environment variables:
            PIPELINE_INPUT_DIR: Input directory (required)
            PIPELINE_OUTPUT_DIR: Output directory (required)
            PIPELINE_SCRATCH_DIR: Scratch directory (optional)
            PIPELINE_STATE_DIR: State directory (default: "state")
            PIPELINE_SYNTHETIC_DIR: Synthetic/test data directory (default: "state/synth")
            PIPELINE_WRITER: Writer strategy (default: "auto")
            PIPELINE_MAX_WORKERS: Max workers (default: 4)
            PIPELINE_EXPECTED_SUBBANDS: Expected subbands (default: 16)

        Args:
            validate_paths: If True, validate paths exist and are accessible (default: True)
            required_disk_gb: Required disk space in GB for validation (default: 50.0)

        Returns:
            PipelineConfig instance

        Raises:
            ValueError: If required environment variables are missing or invalid
            HealthCheckError: If path validation fails (when validate_paths=True)
        """
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        synthetic_dir = Path(
            os.getenv("PIPELINE_SYNTHETIC_DIR", str(base_state / "synth"))
        )

        input_dir = os.getenv("PIPELINE_INPUT_DIR")
        output_dir = os.getenv("PIPELINE_OUTPUT_DIR")

        if not input_dir or not output_dir:
            raise ValueError(
                "PIPELINE_INPUT_DIR and PIPELINE_OUTPUT_DIR environment variables required"
            )

        scratch_dir = os.getenv("PIPELINE_SCRATCH_DIR")

        # Helper function for safe integer conversion with validation
        def safe_int(
            env_var: str,
            default: str,
            min_val: Optional[int] = None,
            max_val: Optional[int] = None,
        ) -> int:
            """Safely convert environment variable to integer with validation."""
            value_str = os.getenv(env_var, default)
            try:
                value = int(value_str)
                if min_val is not None and value < min_val:
                    raise ValueError(f"{env_var}={value} is below minimum {min_val}")
                if max_val is not None and value > max_val:
                    raise ValueError(f"{env_var}={value} is above maximum {max_val}")
                return value
            except ValueError as e:
                if "invalid literal" in str(e) or "could not convert" in str(e):
                    raise ValueError(
                        f"Invalid integer value for {env_var}: '{value_str}'. "
                        f"Expected integer between {min_val or 'unbounded'} and {max_val or 'unbounded'}."
                    ) from e
                raise

        # Helper function for safe float conversion with validation
        def safe_float(
            env_var: str,
            default: str,
            min_val: Optional[float] = None,
            max_val: Optional[float] = None,
        ) -> float:
            """Safely convert environment variable to float with validation."""
            value_str = os.getenv(env_var, default)
            try:
                value = float(value_str)
                if min_val is not None and value < min_val:
                    raise ValueError(f"{env_var}={value} is below minimum {min_val}")
                if max_val is not None and value > max_val:
                    raise ValueError(f"{env_var}={value} is above maximum {max_val}")
                return value
            except ValueError as e:
                if "invalid literal" in str(e) or "could not convert" in str(e):
                    raise ValueError(
                        f"Invalid float value for {env_var}: '{value_str}'. "
                        f"Expected float between {min_val or 'unbounded'} and {max_val or 'unbounded'}."
                    ) from e
                raise

        config = cls(
            paths=PathsConfig(
                input_dir=Path(input_dir),
                output_dir=Path(output_dir),
                scratch_dir=Path(scratch_dir) if scratch_dir else None,
                state_dir=base_state,
                synthetic_dir=synthetic_dir,
            ),
            conversion=ConversionConfig(
                writer=os.getenv("PIPELINE_WRITER", "auto"),
                max_workers=safe_int(
                    "PIPELINE_MAX_WORKERS", "4", min_val=1, max_val=32
                ),
                stage_to_tmpfs=os.getenv("PIPELINE_STAGE_TO_TMPFS", "true").lower()
                == "true",
                expected_subbands=safe_int(
                    "PIPELINE_EXPECTED_SUBBANDS", "16", min_val=1, max_val=32
                ),
            ),
            calibration=CalibrationConfig(
                cal_bp_minsnr=safe_float(
                    "PIPELINE_CAL_BP_MINSNR", "3.0", min_val=1.0, max_val=10.0
                ),
                cal_gain_solint=os.getenv("PIPELINE_CAL_GAIN_SOLINT", "inf"),
                default_refant=os.getenv("PIPELINE_DEFAULT_REFANT", "103"),
                auto_select_refant=os.getenv(
                    "PIPELINE_AUTO_SELECT_REFANT", "true"
                ).lower()
                == "true",
            ),
            imaging=ImagingConfig(
                field=os.getenv("PIPELINE_FIELD"),
                refant=os.getenv("PIPELINE_REFANT", "103"),
                gridder=os.getenv("PIPELINE_GRIDDER", "wproject"),
                wprojplanes=safe_int("PIPELINE_WPROJPLANES", "-1"),
                use_nvss_mask=os.getenv("PIPELINE_USE_NVSS_MASK", "true").lower()
                == "true",
                mask_radius_arcsec=safe_float(
                    "PIPELINE_MASK_RADIUS_ARCSEC", "60.0", min_val=10.0, max_val=300.0
                ),
            ),
        )

        # Optional path validation
        if validate_paths:
            from dsa110_contimg.pipeline.health import validate_pipeline_health

            validate_pipeline_health(config, required_disk_gb=required_disk_gb)

        return config

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
                "output_dir": data.pop("output_dir", "/stage/dsa110-contimg/ms"),
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
        # Extract imaging parameters if they exist at top level
        imaging_keys = [
            "field",
            "refant",
            "gridder",
            "wprojplanes",
            "use_nvss_mask",
            "mask_radius_arcsec",
        ]
        has_imaging_params = any(key in data for key in imaging_keys)

        if has_imaging_params and "imaging" not in data:
            imaging_data = {
                "field": data.pop("field", None),
                "refant": data.pop("refant", "103"),
                "gridder": data.pop("gridder", "wproject"),
                "wprojplanes": data.pop("wprojplanes", -1),
                "use_nvss_mask": data.pop("use_nvss_mask", True),
                "mask_radius_arcsec": data.pop("mask_radius_arcsec", 60.0),
            }
            data["imaging"] = imaging_data

        return cls.model_validate(data)

    @classmethod
    def from_yaml(
        cls,
        yaml_path: Path | str,
        validate_paths: bool = True,
        required_disk_gb: float = 50.0,
    ) -> PipelineConfig:
        """Load configuration from YAML file.

        The YAML file should have a structure matching PipelineConfig:

        ```yaml
        paths:
          input_dir: "/data/incoming"
          output_dir: "/stage/dsa110-contimg/ms"
          scratch_dir: "/tmp"
          state_dir: "state"

        validation:
          enabled: true
          catalog: "nvss"
          validation_types:
            - "astrometry"
            - "flux_scale"
            - "source_counts"
          generate_html_report: true
          min_snr: 5.0
          search_radius_arcsec: 10.0
          completeness_threshold: 0.95
        ```

        Args:
            yaml_path: Path to YAML configuration file
            validate_paths: If True, validate paths exist and are accessible
            required_disk_gb: Required disk space in GB for validation

        Returns:
            PipelineConfig instance

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML is invalid or missing required fields
            HealthCheckError: If path validation fails (when validate_paths=True)
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("YAML file must contain a dictionary/mapping")

        # Convert string paths to Path objects for paths section
        if "paths" in data:
            for key in ["input_dir", "output_dir", "scratch_dir", "state_dir"]:
                if key in data["paths"] and isinstance(data["paths"][key], str):
                    data["paths"][key] = Path(data["paths"][key])

        # Create config from dictionary
        config = cls.from_dict(data)

        # Validate paths if requested
        if validate_paths:
            from dsa110_contimg.pipeline.health import validate_pipeline_health

            validate_pipeline_health(config, required_disk_gb=required_disk_gb)

        return config

    def to_yaml(self, yaml_path: Path | str) -> None:
        """Save configuration to YAML file.

        Args:
            yaml_path: Path where YAML file should be written
        """
        yaml_path = Path(yaml_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and handle Path objects
        data = self.to_dict()

        # Convert Path objects to strings for YAML serialization
        def convert_paths(obj):
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            elif isinstance(obj, Path):
                return str(obj)
            else:
                return obj

        data = convert_paths(data)

        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return self.model_dump()

#!/usr/bin/env python3
"""End-to-end pipeline test runner using synthetic data.

This script orchestrates the complete DSA-110 continuum imaging pipeline:
1. Generate synthetic UVH5 subband files
2. Convert to Measurement Set
3. Run calibration
4. Perform imaging
5. Extract photometry
6. Validate outputs against known inputs

Usage:
    python run_e2e_test.py --scenario bright_calibrator
    python run_e2e_test.py --config config/scenarios/weak_sources.yaml
"""

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import yaml

# Add backend to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from dsa110_contimg.calibration.cli_calibrate import main as calibrate_ms
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    convert_subband_groups_to_ms,
)
from dsa110_contimg.imaging.wsclean_wrapper import run_wsclean
from dsa110_contimg.photometry.forced import measure_forced_peak
from dsa110_contimg.simulation.make_synthetic_uvh5 import main as generate_uvh5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class E2ETestResult:
    """Container for end-to-end test results."""

    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.start_time = time.time()
        self.stages = {}
        self.success = False
        self.error_message = None

    def add_stage(self, stage_name: str, duration: float, success: bool, details: Dict):
        """Record stage execution."""
        self.stages[stage_name] = {
            "duration": duration,
            "success": success,
            "details": details,
        }

    def finish(self, success: bool, error_message: Optional[str] = None):
        """Mark test as complete."""
        self.success = success
        self.error_message = error_message
        self.total_duration = time.time() - self.start_time

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario": self.scenario_name,
            "success": self.success,
            "total_duration": self.total_duration,
            "stages": self.stages,
            "error_message": self.error_message,
        }


def load_scenario(scenario_path: Path) -> Dict:
    """Load scenario configuration from YAML file."""
    with scenario_path.open("r") as f:
        return yaml.safe_load(f)


def run_stage_generate_uvh5(config: Dict, output_dir: Path) -> Dict:
    """Generate synthetic UVH5 files."""
    logger.info("Stage 1: Generating synthetic UVH5 files...")
    stage_start = time.time()

    obs = config["observation"]
    sources = config.get("sources", [])

    uvh5_dir = output_dir / "uvh5"
    uvh5_dir.mkdir(parents=True, exist_ok=True)

    # Build arguments for synthetic UVH5 generator
    args = [
        "--template-free",
        "--nants",
        str(config.get("telescope", {}).get("num_antennas", 110)),
        "--ntimes",
        str(int(obs["duration_minutes"] * 60 / 12.88)),  # ~12.88s per integration
        "--start-time",
        obs["start_time"],
        "--duration-minutes",
        str(obs["duration_minutes"]),
        "--subbands",
        str(obs["num_subbands"]),
        "--output",
        str(uvh5_dir),
    ]

    # Add source if specified (single calibrator for now)
    if sources:
        src = sources[0]
        args.extend(
            [
                "--flux-jy",
                str(src["flux_jy"]),
                "--source-model",
                src.get("model", "point"),
            ]
        )
        if src.get("size_arcsec"):
            args.extend(["--source-size-arcsec", str(src["size_arcsec"])])

    # Add noise if requested
    if config.get("noise", {}).get("enabled", True):
        args.append("--add-noise")
        if "system_temp_k" in config["noise"]:
            args.extend(["--system-temp-k", str(config["noise"]["system_temp_k"])])

    # Mock sys.argv and call generator
    old_argv = sys.argv
    try:
        sys.argv = ["make_synthetic_uvh5.py"] + args
        generate_uvh5()
        duration = time.time() - stage_start
        return {
            "success": True,
            "duration": duration,
            "output_dir": str(uvh5_dir),
            "num_files": len(list(uvh5_dir.glob("*.hdf5"))),
        }
    except Exception as e:
        logger.error(f"Failed to generate UVH5: {e}")
        return {
            "success": False,
            "duration": time.time() - stage_start,
            "error": str(e),
        }
    finally:
        sys.argv = old_argv


def run_stage_convert_to_ms(config: Dict, uvh5_dir: Path, output_dir: Path) -> Dict:
    """Convert UVH5 to Measurement Set."""
    logger.info("Stage 2: Converting UVH5 to MS...")
    stage_start = time.time()

    ms_dir = output_dir / "ms"
    ms_dir.mkdir(parents=True, exist_ok=True)

    obs = config["observation"]
    start_time = obs["start_time"]
    duration_min = obs["duration_minutes"]

    # Calculate end time
    import astropy.units as u
    from astropy.time import Time, TimeDelta

    t_start = Time(start_time, format="isot", scale="utc")
    t_end = t_start + TimeDelta(duration_min * 60, format="sec")

    try:
        ms_paths = convert_subband_groups_to_ms(
            str(uvh5_dir),
            str(ms_dir),
            start_time,
            t_end.isot,
            rename_calibrator_fields=config.get("calibration", {}).get(
                "auto_rename_fields", True
            ),
        )

        duration = time.time() - stage_start
        return {
            "success": True,
            "duration": duration,
            "ms_paths": [str(p) for p in ms_paths],
            "num_ms": len(ms_paths),
        }
    except Exception as e:
        logger.error(f"Failed to convert to MS: {e}")
        return {
            "success": False,
            "duration": time.time() - stage_start,
            "error": str(e),
        }


def run_stage_calibrate(config: Dict, ms_path: Path, output_dir: Path) -> Dict:
    """Run calibration on MS."""
    logger.info("Stage 3: Calibrating MS...")
    stage_start = time.time()

    caltables_dir = output_dir / "caltables"
    caltables_dir.mkdir(parents=True, exist_ok=True)

    cal_config = config.get("calibration", {})

    args = [
        str(ms_path),
        "--output-dir",
        str(caltables_dir),
    ]

    if cal_config.get("auto_select_field", True):
        args.append("--auto-select-field")
    elif "field_id" in cal_config:
        args.extend(["--field", str(cal_config["field_id"])])

    # Mock sys.argv and call calibrator
    old_argv = sys.argv
    try:
        sys.argv = ["cli_calibrate.py"] + args
        calibrate_ms()
        duration = time.time() - stage_start
        return {
            "success": True,
            "duration": duration,
            "caltable_dir": str(caltables_dir),
        }
    except Exception as e:
        logger.error(f"Failed to calibrate: {e}")
        return {
            "success": False,
            "duration": time.time() - stage_start,
            "error": str(e),
        }
    finally:
        sys.argv = old_argv


def run_stage_image(config: Dict, ms_path: Path, output_dir: Path) -> Dict:
    """Run imaging with WSClean."""
    logger.info("Stage 4: Imaging MS...")
    stage_start = time.time()

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    img_config = config.get("imaging", {})

    try:
        image_prefix = images_dir / "test_image"
        run_wsclean(
            str(ms_path),
            str(image_prefix),
            size=img_config.get("size_pix", 512),
            scale=f"{img_config.get('pixel_scale_arcsec', 3.6)}asec",
            niter=img_config.get("niter", 10000),
            mgain=img_config.get("mgain", 0.8),
            threshold=img_config.get("threshold", "0.001Jy"),
        )

        duration = time.time() - stage_start
        fits_files = list(images_dir.glob("*.fits"))
        return {
            "success": True,
            "duration": duration,
            "image_prefix": str(image_prefix),
            "fits_files": [str(f) for f in fits_files],
        }
    except Exception as e:
        logger.error(f"Failed to image: {e}")
        return {
            "success": False,
            "duration": time.time() - stage_start,
            "error": str(e),
        }


def run_stage_photometry(config: Dict, images_dir: Path, output_dir: Path) -> Dict:
    """Run forced photometry on images."""
    logger.info("Stage 5: Performing photometry...")
    stage_start = time.time()

    sources = config.get("sources", [])
    validation = config.get("validation", {})

    # Find restored image (WSClean output)
    restored_images = list(Path(images_dir).glob("*-image.fits"))
    if not restored_images:
        return {
            "success": False,
            "duration": time.time() - stage_start,
            "error": "No restored image found",
        }

    image_path = str(restored_images[0])
    results = []

    try:
        for src in sources:
            result = measure_forced_peak(
                image_path,
                src["ra_deg"],
                src["dec_deg"],
                box_size_pix=5,
                annulus_pix=(12, 20),
            )

            expected_flux = src["flux_jy"]
            measured_flux = result.peak_jyb
            flux_error = result.peak_err_jyb

            # Calculate metrics
            if measured_flux and flux_error and flux_error > 0:
                snr = measured_flux / flux_error
                flux_diff_pct = abs(measured_flux - expected_flux) / expected_flux * 100
                meets_criteria = flux_diff_pct <= validation.get(
                    "max_flux_error_percent", 10.0
                ) and snr >= validation.get("min_snr", 5.0)
            else:
                snr = None
                flux_diff_pct = None
                meets_criteria = False

            results.append(
                {
                    "source_name": src.get("name", "unknown"),
                    "expected_flux_jy": expected_flux,
                    "measured_flux_jy": measured_flux,
                    "flux_error_jy": flux_error,
                    "snr": snr,
                    "flux_diff_percent": flux_diff_pct,
                    "meets_validation": meets_criteria,
                }
            )

        duration = time.time() - stage_start
        all_valid = all(r["meets_validation"] for r in results)

        return {
            "success": all_valid,
            "duration": duration,
            "measurements": results,
            "all_sources_valid": all_valid,
        }
    except Exception as e:
        logger.error(f"Failed photometry: {e}")
        return {
            "success": False,
            "duration": time.time() - stage_start,
            "error": str(e),
        }


def run_e2e_test(scenario_config: Dict, output_dir: Path) -> E2ETestResult:
    """Run complete end-to-end test."""
    result = E2ETestResult(scenario_config.get("name", "unknown"))

    try:
        # Stage 1: Generate UVH5
        uvh5_result = run_stage_generate_uvh5(scenario_config, output_dir)
        result.add_stage(
            "generate_uvh5",
            uvh5_result["duration"],
            uvh5_result["success"],
            uvh5_result,
        )
        if not uvh5_result["success"]:
            result.finish(False, "Failed to generate UVH5 files")
            return result

        uvh5_dir = Path(uvh5_result["output_dir"])

        # Stage 2: Convert to MS
        ms_result = run_stage_convert_to_ms(scenario_config, uvh5_dir, output_dir)
        result.add_stage(
            "convert_to_ms", ms_result["duration"], ms_result["success"], ms_result
        )
        if not ms_result["success"]:
            result.finish(False, "Failed to convert to MS")
            return result

        ms_paths = [Path(p) for p in ms_result["ms_paths"]]
        if not ms_paths:
            result.finish(False, "No MS files generated")
            return result

        ms_path = ms_paths[0]  # Use first MS

        # Stage 3: Calibrate
        cal_result = run_stage_calibrate(scenario_config, ms_path, output_dir)
        result.add_stage(
            "calibrate", cal_result["duration"], cal_result["success"], cal_result
        )
        if not cal_result["success"]:
            result.finish(False, "Failed to calibrate")
            return result

        # Stage 4: Image
        img_result = run_stage_image(scenario_config, ms_path, output_dir)
        result.add_stage(
            "image", img_result["duration"], img_result["success"], img_result
        )
        if not img_result["success"]:
            result.finish(False, "Failed to image")
            return result

        # Stage 5: Photometry & Validation
        phot_result = run_stage_photometry(
            scenario_config, Path(img_result["image_prefix"]).parent, output_dir
        )
        result.add_stage(
            "photometry", phot_result["duration"], phot_result["success"], phot_result
        )

        # Overall success
        all_success = all(stage["success"] for stage in result.stages.values())
        result.finish(all_success)

    except Exception as e:
        logger.exception(f"Unexpected error in E2E test: {e}")
        result.finish(False, str(e))

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run end-to-end pipeline test with synthetic data"
    )
    parser.add_argument(
        "--scenario",
        help="Scenario name (looks in simulations/config/scenarios/<name>.yaml)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to scenario config YAML file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("simulations/data/e2e_tests"),
        help="Output directory for test artifacts",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean output directory before running",
    )
    parser.add_argument(
        "--results-file",
        type=Path,
        help="Path to save results JSON (default: <output_dir>/results.json)",
    )

    args = parser.parse_args()

    # Load scenario config
    if args.config:
        config_path = args.config
    elif args.scenario:
        config_path = (
            REPO_ROOT / "simulations" / "config" / "scenarios" / f"{args.scenario}.yaml"
        )
    else:
        parser.error("Must specify either --scenario or --config")

    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    logger.info(f"Loading scenario from: {config_path}")
    scenario_config = load_scenario(config_path)

    # Setup output directory
    output_dir = args.output_dir
    if args.clean and output_dir.exists():
        logger.info(f"Cleaning output directory: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run test
    logger.info(f"Starting E2E test: {scenario_config.get('name', 'unknown')}")
    result = run_e2e_test(scenario_config, output_dir)

    # Save results
    results_file = args.results_file or (output_dir / "results.json")
    with results_file.open("w") as f:
        json.dump(result.to_dict(), f, indent=2)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info(f"E2E Test: {result.scenario_name}")
    logger.info(f"Status: {'✅ PASSED' if result.success else '❌ FAILED'}")
    logger.info(f"Total Duration: {result.total_duration:.2f}s")
    logger.info("=" * 60)
    logger.info("\nStage Summary:")
    for stage_name, stage_data in result.stages.items():
        status = "✅" if stage_data["success"] else "❌"
        logger.info(f"  {status} {stage_name}: {stage_data['duration']:.2f}s")

    if result.error_message:
        logger.error(f"\nError: {result.error_message}")

    logger.info(f"\nResults saved to: {results_file}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()

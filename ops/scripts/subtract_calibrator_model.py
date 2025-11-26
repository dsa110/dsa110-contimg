#!/usr/bin/env python3
"""
Subtract Calibrator Source Model from Visibilities for Noise Validation

This script uses WSClean (consistent with DSA-110 pipeline) to:
1. Image the calibrator observation
2. Predict model visibilities using WSClean
3. Subtract model from observed visibilities
4. Residual visibilities contain only noise (+ calibration errors)

Usage:
    python subtract_calibrator_model.py \\
        --input-ms observation.ms \\
        --output-ms observation_residual.ms \\
        --field-idx 10

Author: DSA-110 Team
Date: 2025-11-25
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
    from casatools import table
except ImportError:
    print("ERROR: Required tools not found. Run in casa6 environment:")
    print("  conda activate casa6")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def subtract_source_model(
    input_ms: str,
    output_ms: str,
    field_idx: int,
    image_size: int = 2048,
    scale: str = "2.5asec",
    niter: int = 100000,
    auto_threshold: float = 3.0,
) -> Path:
    """
    Subtract source model from visibilities using WSClean.

    Parameters
    ----------
    input_ms : str
        Input Measurement Set
    output_ms : str
        Output MS with residuals
    field_idx : int
        Field containing calibrator
    image_size : int
        Image size in pixels (default: 2048)
    scale : str
        Pixel size (default: "2.5asec" for DSA-110)
    niter : int
        Maximum clean iterations (default: 100000)
    auto_threshold : float
        Auto-threshold in sigma (default: 3.0)

    Returns
    -------
    output_path : Path
        Path to residual MS
    """
    input_path = Path(input_ms)
    output_path = Path(output_ms)

    if not input_path.exists():
        raise FileNotFoundError(f"Input MS not found: {input_ms}")

    if output_path.exists():
        logger.warning(f"Output MS exists, removing: {output_ms}")
        shutil.rmtree(output_path)

    logger.info("=" * 60)
    logger.info("STEP 1: Create copy of MS for modification")
    logger.info("=" * 60)

    logger.info(f"Copying {input_ms} -> {output_ms}")
    shutil.copytree(input_path, output_path)

    logger.info("=" * 60)
    logger.info("STEP 2: Image field with WSClean")
    logger.info("=" * 60)

    image_prefix = f"{output_path.stem}_field{field_idx}_model"

    logger.info(f"Imaging field {field_idx} with WSClean...")
    logger.info(f"  Image size: {image_size} x {image_size}")
    logger.info(f"  Pixel scale: {scale}")
    logger.info(f"  Max iterations: {niter}")
    logger.info(f"  Auto-threshold: {auto_threshold} sigma")

    # Find wsclean executable or use Docker
    wsclean_cmd = shutil.which("wsclean")
    use_docker = False

    if not wsclean_cmd:
        docker_cmd = shutil.which("docker")
        if docker_cmd:
            logger.info(
                "Native wsclean not found, using Docker (wsclean-everybeam:0.7.4)"
            )
            use_docker = True
        else:
            raise RuntimeError(
                "wsclean executable not found in PATH and Docker not available"
            )

    # Construct WSClean command
    if use_docker:
        # Docker setup with volume mounts
        ms_dir = os.path.dirname(os.path.abspath(str(output_path)))
        output_dir = os.path.dirname(
            os.path.abspath(str(output_path.parent / image_prefix))
        )

        wsclean_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{ms_dir}:/data",
            "wsclean-everybeam:0.7.4",
            "wsclean",
            "-field",
            str(field_idx),
            "-size",
            str(image_size),
            str(image_size),
            "-scale",
            scale,
            "-niter",
            str(niter),
            "-auto-threshold",
            str(auto_threshold),
            "-mgain",
            "0.8",
            "-weight",
            "briggs",
            "0",
            "-pol",
            "I",
            "-reorder",  # Required for multi-SPW
            "-name",
            f"/data/{output_path.stem}_field{field_idx}_model",
            f"/data/{output_path.name}",
        ]
    else:
        wsclean_cmd = [
            "wsclean",
            "-field",
            str(field_idx),
            "-size",
            str(image_size),
            str(image_size),
            "-scale",
            scale,
            "-niter",
            str(niter),
            "-auto-threshold",
            str(auto_threshold),
            "-mgain",
            "0.8",
            "-weight",
            "briggs",
            "0",
            "-pol",
            "I",
            "-reorder",  # Required for multi-SPW
            "-name",
            str(output_path.parent / image_prefix),
            str(output_path),
        ]

    logger.info(f"Running: {' '.join(wsclean_cmd)}")

    result = subprocess.run(
        wsclean_cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"WSClean failed: {result.stderr}")
        raise RuntimeError(f"WSClean imaging failed with code {result.returncode}")

    logger.info("WSClean imaging complete")

    logger.info("=" * 60)
    logger.info("STEP 3: Predict model visibilities")
    logger.info("=" * 60)

    # Predict model back to visibilities
    if use_docker:
        predict_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{ms_dir}:/data",
            "wsclean-everybeam:0.7.4",
            "wsclean",
            "-field",
            str(field_idx),
            "-size",
            str(image_size),
            str(image_size),
            "-scale",
            scale,
            "-reorder",  # Required for multi-SPW
            "-predict",
            "-name",
            f"/data/{output_path.stem}_field{field_idx}_model",
            f"/data/{output_path.name}",
        ]
    else:
        predict_cmd = [
            "wsclean",
            "-field",
            str(field_idx),
            "-size",
            str(image_size),
            str(image_size),
            "-scale",
            scale,
            "-reorder",  # Required for multi-SPW
            "-predict",
            "-name",
            str(output_path.parent / image_prefix),
            str(output_path),
        ]

    logger.info(f"Running: {' '.join(predict_cmd)}")

    result = subprocess.run(
        predict_cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"WSClean predict failed: {result.stderr}")
        raise RuntimeError(f"WSClean predict failed with code {result.returncode}")

    logger.info("Model prediction complete (written to MODEL_DATA column)")

    logger.info("=" * 60)
    logger.info("STEP 4: Subtract model from visibilities")
    logger.info("=" * 60)

    # Fix permissions if Docker changed ownership to root
    import os as os_module
    import pwd

    current_user = pwd.getpwuid(os_module.getuid()).pw_name
    ms_owner = pwd.getpwuid(
        os_module.stat(str(output_path / "table.dat")).st_uid
    ).pw_name

    if ms_owner != current_user:
        logger.warning(f"MS owned by {ms_owner}, fixing permissions...")
        result = subprocess.run(
            ["sudo", "chown", "-R", f"{current_user}:{current_user}", str(output_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Failed to fix permissions: {result.stderr}")
            raise RuntimeError(
                "Cannot fix MS permissions. Run manually: sudo chown -R $USER:$USER "
                + str(output_path)
            )

    # Subtract MODEL_DATA from DATA using casatools
    logger.info("Subtracting MODEL_DATA from DATA (this may take a few minutes)...")

    tb = table()
    tb.open(str(output_path), nomodify=False)

    try:
        # Read data
        data = tb.getcol("DATA")
        model = tb.getcol("MODEL_DATA")

        logger.info(f"DATA shape: {data.shape}")
        logger.info(f"MODEL_DATA shape: {model.shape}")

        # Subtract: residual = data - model
        residual = data - model

        # Write back to DATA column
        tb.putcol("DATA", residual)

        logger.info("Residuals written to DATA column")

    finally:
        tb.close()

    logger.info("=" * 60)
    logger.info("COMPLETE: Source subtraction successful")
    logger.info("=" * 60)
    logger.info(f"Residual MS: {output_ms}")
    logger.info("Ready for noise validation!")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Subtract calibrator source model for noise validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    # Subtract source model from field 10 using WSClean
    python subtract_calibrator_model.py \\
        --input-ms /stage/dsa110-contimg/ms/0834_555.ms \\
        --output-ms /stage/dsa110-contimg/ms/0834_555_residual.ms \\
        --field-idx 10

    # Then validate noise
    python validate_noise_model.py \\
        --real-ms /stage/dsa110-contimg/ms/0834_555_residual.ms \\
        --output-dir validation/ \\
        --plot
        """,
    )

    parser.add_argument(
        "--input-ms",
        required=True,
        type=str,
        help="Input Measurement Set with calibrator",
    )
    parser.add_argument(
        "--output-ms",
        required=True,
        type=str,
        help="Output MS with residuals (source subtracted)",
    )
    parser.add_argument(
        "--field-idx",
        type=int,
        required=True,
        help="Field index containing calibrator",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=2048,
        help="Image size in pixels (default: 2048)",
    )
    parser.add_argument(
        "--scale",
        type=str,
        default="2.5asec",
        help="Pixel size (default: 2.5asec for DSA-110)",
    )
    parser.add_argument(
        "--niter",
        type=int,
        default=100000,
        help="Maximum clean iterations (default: 100000)",
    )
    parser.add_argument(
        "--auto-threshold",
        type=float,
        default=3.0,
        help="Auto-threshold in sigma (default: 3.0)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        subtract_source_model(
            input_ms=args.input_ms,
            output_ms=args.output_ms,
            field_idx=args.field_idx,
            image_size=args.image_size,
            scale=args.scale,
            niter=args.niter,
            auto_threshold=args.auto_threshold,
        )
    except Exception as e:
        logger.error(f"Source subtraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

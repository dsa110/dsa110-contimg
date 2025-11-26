#!/usr/bin/env python3
"""
DSA-110 System Characterization Orchestrator

Runs complete system characterization workflow:
1. Scans for calibrator observations (MS files) and caltables
2. Measures T_sys and SEFD from calibrator data
3. Analyzes gain/phase stability from caltables
4. Validates noise model against real observations
5. Generates comprehensive report with parameter recommendations

Output: Updated dsa110_measured_parameters.yaml with real measurements

Usage:
    python characterize_dsa110_system.py \\
        --ms-dir /stage/dsa110-contimg/ms \\
        --caltable-dir /data/dsa110-contimg/products/caltables \\
        --output-dir system_characterization/

Author: DSA-110 Team
Date: 2025-11-25
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Known calibrator patterns for filename matching
CALIBRATOR_PATTERNS = [
    "3C286",
    "3C48",
    "3C147",
    "3C138",
    "J1331+3030",  # Alternative name for 3C286
]


def find_calibrator_observations(ms_dir: Path) -> Dict[str, List[Path]]:
    """
    Scan directory for calibrator observations.

    Parameters
    ----------
    ms_dir : Path
        Directory containing MS files

    Returns
    -------
    calibrators : dict
        {calibrator_name: [list of MS paths]}
    """
    logger.info(f"Scanning for calibrator observations in: {ms_dir}")

    calibrators = {cal: [] for cal in CALIBRATOR_PATTERNS}

    # Find all .ms directories
    if not ms_dir.exists():
        logger.warning(f"MS directory does not exist: {ms_dir}")
        return calibrators

    for ms_path in ms_dir.glob("*.ms"):
        ms_name = ms_path.name
        for cal_name in CALIBRATOR_PATTERNS:
            if cal_name.lower() in ms_name.lower():
                calibrators[cal_name].append(ms_path)
                logger.info(f"Found {cal_name} observation: {ms_path}")

    # Summary
    total_found = sum(len(obs_list) for obs_list in calibrators.values())
    logger.info(f"Found {total_found} total calibrator observations:")
    for cal_name, obs_list in calibrators.items():
        if obs_list:
            logger.info(f"  {cal_name}: {len(obs_list)} observations")

    return calibrators


def find_caltables(caltable_dir: Path) -> Dict[str, List[Path]]:
    """
    Scan directory for calibration tables.

    Parameters
    ----------
    caltable_dir : Path
        Directory containing .cal directories

    Returns
    -------
    caltables : dict
        {caltype: [list of caltable paths]}
    """
    logger.info(f"Scanning for caltables in: {caltable_dir}")

    caltables = {"G": [], "B": [], "K": [], "other": []}

    if not caltable_dir.exists():
        logger.warning(f"Caltable directory does not exist: {caltable_dir}")
        return caltables

    for cal_path in caltable_dir.glob("*.G*"):
        caltables["G"].append(cal_path)
    for cal_path in caltable_dir.glob("*.B*"):
        caltables["B"].append(cal_path)
    for cal_path in caltable_dir.glob("*.K*"):
        caltables["K"].append(cal_path)

    logger.info(
        f"Found caltables: G={len(caltables['G'])}, B={len(caltables['B'])}, K={len(caltables['K'])}"
    )

    return caltables


def run_tsys_measurement(
    ms_path: Path,
    calibrator: str,
    output_dir: Path,
) -> Optional[Dict]:
    """
    Run measure_system_parameters.py on calibrator observation.

    Parameters
    ----------
    ms_path : Path
        Path to calibrator MS
    calibrator : str
        Calibrator name
    output_dir : Path
        Output directory

    Returns
    -------
    results : dict or None
        Measurement results if successful
    """
    logger.info(f"Measuring T_sys and SEFD from {ms_path}")

    measurement_output = output_dir / f"tsys_{calibrator}_{ms_path.stem}"
    measurement_output.mkdir(parents=True, exist_ok=True)

    script_path = Path(__file__).parent / "measure_system_parameters.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--ms",
        str(ms_path),
        "--calibrator",
        calibrator,
        "--output-dir",
        str(measurement_output),
        "--plot",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"T_sys measurement complete: {measurement_output}")

        # Load results
        json_path = measurement_output / "system_parameters.json"
        if json_path.exists():
            with open(json_path) as f:
                return json.load(f)
        else:
            logger.warning(f"Results file not found: {json_path}")
            return None

    except subprocess.CalledProcessError as e:
        logger.error(f"T_sys measurement failed: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return None


def run_stability_analysis(
    caltable_path: Path,
    output_dir: Path,
) -> Optional[Dict]:
    """
    Run analyze_calibration_stability.py on caltable.

    Parameters
    ----------
    caltable_path : Path
        Path to calibration table
    output_dir : Path
        Output directory

    Returns
    -------
    results : dict or None
        Analysis results if successful
    """
    logger.info(f"Analyzing stability from {caltable_path}")

    stability_output = output_dir / f"stability_{caltable_path.stem}"
    stability_output.mkdir(parents=True, exist_ok=True)

    script_path = Path(__file__).parent / "analyze_calibration_stability.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--caltable",
        str(caltable_path),
        "--output-dir",
        str(stability_output),
        "--plot",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Stability analysis complete: {stability_output}")

        # Load results
        json_path = stability_output / "calibration_stability.json"
        if json_path.exists():
            with open(json_path) as f:
                return json.load(f)
        else:
            logger.warning(f"Results file not found: {json_path}")
            return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Stability analysis failed: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return None


def run_noise_validation(
    ms_path: Path,
    output_dir: Path,
    system_temp_k: float,
    efficiency: float,
) -> Optional[Dict]:
    """
    Run validate_noise_model.py on observation.

    Parameters
    ----------
    ms_path : Path
        Path to MS file
    output_dir : Path
        Output directory
    system_temp_k : float
        System temperature to test
    efficiency : float
        Efficiency to test

    Returns
    -------
    results : dict or None
        Validation results if successful
    """
    logger.info(f"Validating noise model against {ms_path}")

    validation_output = output_dir / f"noise_validation_{ms_path.stem}"
    validation_output.mkdir(parents=True, exist_ok=True)

    script_path = Path(__file__).parent / "validate_noise_model.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--real-ms",
        str(ms_path),
        "--output-dir",
        str(validation_output),
        "--system-temp-k",
        str(system_temp_k),
        "--efficiency",
        str(efficiency),
        "--n-synthetic",
        "10000",
        "--plot",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Noise validation complete: {validation_output}")

        # Load results
        json_path = validation_output / "noise_validation.json"
        if json_path.exists():
            with open(json_path) as f:
                return json.load(f)
        else:
            logger.warning(f"Results file not found: {json_path}")
            return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Noise validation failed: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return None


def aggregate_results(
    tsys_results: List[Dict],
    stability_results: List[Dict],
    noise_validation_results: List[Dict],
) -> Dict:
    """
    Aggregate results from all measurements.

    Parameters
    ----------
    tsys_results : list
        List of T_sys measurement results
    stability_results : list
        List of stability analysis results
    noise_validation_results : list
        List of noise validation results

    Returns
    -------
    aggregated : dict
        Aggregated statistics and recommendations
    """
    logger.info("Aggregating results from all measurements")

    aggregated = {
        "measurement_date": datetime.utcnow().isoformat(),
        "n_tsys_measurements": len(tsys_results),
        "n_stability_analyses": len(stability_results),
        "n_noise_validations": len(noise_validation_results),
    }

    # Aggregate T_sys
    if tsys_results:
        all_tsys = []
        all_sefd = []
        for result in tsys_results:
            if "summary" in result:
                all_tsys.append(result["summary"]["mean_T_sys_K"])
                all_sefd.append(result["summary"]["mean_SEFD_Jy"])

        if all_tsys:
            aggregated["system_temperature"] = {
                "mean_K": float(np.mean(all_tsys)),
                "std_K": float(np.std(all_tsys)),
                "median_K": float(np.median(all_tsys)),
                "n_measurements": len(all_tsys),
            }
            aggregated["sefd"] = {
                "mean_Jy": float(np.mean(all_sefd)),
                "std_Jy": float(np.std(all_sefd)),
                "median_Jy": float(np.median(all_sefd)),
                "n_measurements": len(all_sefd),
            }

    # Aggregate stability
    if stability_results:
        all_amp_std = []
        all_phase_std = []
        for result in stability_results:
            if "summary" in result:
                all_amp_std.append(
                    result["summary"]["amplitude_stability"][
                        "median_fractional_std_percent"
                    ]
                )
                all_phase_std.append(
                    result["summary"]["phase_stability"]["median_std_deg"]
                )

        if all_amp_std:
            aggregated["calibration_stability"] = {
                "amplitude_std_percent": {
                    "mean": float(np.mean(all_amp_std)),
                    "std": float(np.std(all_amp_std)),
                    "median": float(np.median(all_amp_std)),
                    "n_measurements": len(all_amp_std),
                },
                "phase_std_deg": {
                    "mean": float(np.mean(all_phase_std)),
                    "std": float(np.std(all_phase_std)),
                    "median": float(np.median(all_phase_std)),
                    "n_measurements": len(all_phase_std),
                },
            }

    # Aggregate noise validation
    if noise_validation_results:
        all_validated = [
            result["statistical_comparison"]["summary"]["overall_validation"]
            for result in noise_validation_results
            if "statistical_comparison" in result
        ]
        aggregated["noise_validation"] = {
            "n_validations": len(all_validated),
            "n_passed": sum(all_validated),
            "success_rate": (
                sum(all_validated) / len(all_validated) if all_validated else 0
            ),
        }

    return aggregated


def generate_parameter_recommendations(aggregated: Dict) -> Dict:
    """
    Generate parameter recommendations based on measurements.

    Parameters
    ----------
    aggregated : dict
        Aggregated measurement results

    Returns
    -------
    recommendations : dict
        Parameter values to use in simulations
    """
    logger.info("Generating parameter recommendations")

    recommendations = {
        "generated_at": datetime.utcnow().isoformat(),
        "parameters": {},
    }

    # System temperature
    if "system_temperature" in aggregated:
        tsys_data = aggregated["system_temperature"]
        recommendations["parameters"]["system_temperature"] = {
            "recommended_value": tsys_data["median_K"],
            "uncertainty": tsys_data["std_K"],
            "unit": "K",
            "validation_status": "measured",
            "notes": f"Based on {tsys_data['n_measurements']} calibrator observations",
        }
    else:
        recommendations["parameters"]["system_temperature"] = {
            "recommended_value": 50.0,
            "uncertainty": None,
            "unit": "K",
            "validation_status": "assumed",
            "notes": "No measurements available - using default assumption",
        }

    # SEFD
    if "sefd" in aggregated:
        sefd_data = aggregated["sefd"]
        recommendations["parameters"]["sefd"] = {
            "recommended_value": sefd_data["median_Jy"],
            "uncertainty": sefd_data["std_Jy"],
            "unit": "Jy",
            "validation_status": "measured",
            "notes": f"Based on {sefd_data['n_measurements']} calibrator observations",
        }

    # Gain amplitude stability
    if "calibration_stability" in aggregated:
        amp_data = aggregated["calibration_stability"]["amplitude_std_percent"]
        recommendations["parameters"]["gain_amplitude_std"] = {
            "recommended_value": amp_data["median"] / 100.0,  # Convert % to fraction
            "uncertainty": amp_data["std"] / 100.0,
            "unit": "fractional",
            "validation_status": "measured",
            "notes": f"Based on {amp_data['n_measurements']} caltable analyses",
        }

        # Phase stability
        phase_data = aggregated["calibration_stability"]["phase_std_deg"]
        recommendations["parameters"]["gain_phase_std"] = {
            "recommended_value": phase_data["median"],
            "uncertainty": phase_data["std"],
            "unit": "degrees",
            "validation_status": "measured",
            "notes": f"Based on {phase_data['n_measurements']} caltable analyses",
        }
    else:
        recommendations["parameters"]["gain_amplitude_std"] = {
            "recommended_value": 0.10,
            "uncertainty": None,
            "unit": "fractional",
            "validation_status": "assumed",
            "notes": "No measurements available - using default assumption",
        }
        recommendations["parameters"]["gain_phase_std"] = {
            "recommended_value": 10.0,
            "uncertainty": None,
            "unit": "degrees",
            "validation_status": "assumed",
            "notes": "No measurements available - using default assumption",
        }

    # Noise validation summary
    if "noise_validation" in aggregated:
        val_data = aggregated["noise_validation"]
        recommendations["noise_model_validation"] = {
            "success_rate": val_data["success_rate"],
            "n_passed": val_data["n_passed"],
            "n_total": val_data["n_validations"],
            "status": (
                "VALIDATED" if val_data["success_rate"] >= 0.8 else "NEEDS_CALIBRATION"
            ),
        }

    return recommendations


def save_comprehensive_report(
    aggregated: Dict,
    recommendations: Dict,
    output_dir: Path,
):
    """Save comprehensive characterization report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    report_json = output_dir / "system_characterization_report.json"
    full_report = {
        "aggregated_results": aggregated,
        "parameter_recommendations": recommendations,
    }
    with open(report_json, "w") as f:
        json.dump(full_report, f, indent=2)
    logger.info(f"Saved JSON report: {report_json}")

    # YAML
    report_yaml = output_dir / "system_characterization_report.yaml"
    with open(report_yaml, "w") as f:
        yaml.dump(full_report, f, default_flow_style=False, sort_keys=False)
    logger.info(f"Saved YAML report: {report_yaml}")

    # Text summary
    report_txt = output_dir / "system_characterization_summary.txt"
    with open(report_txt, "w") as f:
        f.write("DSA-110 System Characterization Report\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Generated: {aggregated['measurement_date']}\n")
        f.write(
            f"Measurements: T_sys={aggregated['n_tsys_measurements']}, "
            f"Stability={aggregated['n_stability_analyses']}, "
            f"Noise validation={aggregated['n_noise_validations']}\n\n"
        )

        f.write("Recommended Parameters for Simulation\n")
        f.write("-" * 70 + "\n\n")

        for param_name, param_data in recommendations["parameters"].items():
            f.write(f"{param_name}:\n")
            f.write(f"  Value: {param_data['recommended_value']}")
            if param_data["uncertainty"] is not None:
                f.write(f" ± {param_data['uncertainty']}")
            f.write(f" {param_data['unit']}\n")
            f.write(f"  Status: {param_data['validation_status']}\n")
            f.write(f"  Notes: {param_data['notes']}\n\n")

        if "noise_model_validation" in recommendations:
            val_data = recommendations["noise_model_validation"]
            f.write("Noise Model Validation\n")
            f.write("-" * 70 + "\n")
            f.write(
                f"Status: {val_data['status']} "
                f"({val_data['n_passed']}/{val_data['n_total']} passed, "
                f"{val_data['success_rate']*100:.1f}%)\n\n"
            )

        f.write("Next Steps\n")
        f.write("-" * 70 + "\n")
        f.write("1. Review parameter recommendations above\n")
        f.write(
            "2. Update backend/src/dsa110_contimg/simulation/config/dsa110_measured_parameters.yaml\n"
        )
        f.write("3. Update visibility_models.py to load parameters from YAML\n")
        f.write("4. Re-run simulations with measured parameters\n")
        f.write("5. Document changes in SYSTEM_CHARACTERIZATION.md\n")

    logger.info(f"Saved text summary: {report_txt}")


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate complete DSA-110 system characterization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Full characterization
    python characterize_dsa110_system.py \\
        --ms-dir /stage/dsa110-contimg/ms \\
        --caltable-dir /data/dsa110-contimg/products/caltables \\
        --output-dir system_characterization/

    # Only T_sys measurement
    python characterize_dsa110_system.py \\
        --ms-dir /stage/dsa110-contimg/ms \\
        --output-dir characterization/ \\
        --skip-stability --skip-noise-validation
        """,
    )

    parser.add_argument(
        "--ms-dir",
        type=str,
        required=True,
        help="Directory containing Measurement Sets",
    )
    parser.add_argument(
        "--caltable-dir",
        type=str,
        help="Directory containing calibration tables",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="system_characterization",
        help="Output directory for all results",
    )
    parser.add_argument(
        "--skip-tsys",
        action="store_true",
        help="Skip T_sys/SEFD measurement",
    )
    parser.add_argument(
        "--skip-stability",
        action="store_true",
        help="Skip calibration stability analysis",
    )
    parser.add_argument(
        "--skip-noise-validation",
        action="store_true",
        help="Skip noise model validation",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tsys_results = []
    stability_results = []
    noise_validation_results = []

    # Find observations
    ms_dir = Path(args.ms_dir)
    calibrator_obs = find_calibrator_observations(ms_dir)

    # T_sys measurements
    if not args.skip_tsys:
        for cal_name, obs_list in calibrator_obs.items():
            if not obs_list:
                continue
            # Use first observation for each calibrator
            ms_path = obs_list[0]
            result = run_tsys_measurement(ms_path, cal_name, output_dir)
            if result:
                tsys_results.append(result)

    # Stability analysis
    if not args.skip_stability and args.caltable_dir:
        caltable_dir = Path(args.caltable_dir)
        caltables = find_caltables(caltable_dir)

        # Analyze up to 5 gain tables
        for caltable_path in caltables["G"][:5]:
            result = run_stability_analysis(caltable_path, output_dir)
            if result:
                stability_results.append(result)

    # Noise validation
    if not args.skip_noise_validation:
        # Use first available calibrator observation
        for cal_name, obs_list in calibrator_obs.items():
            if obs_list:
                ms_path = obs_list[0]
                # Use measured T_sys if available, else default
                system_temp = (
                    tsys_results[0]["summary"]["mean_T_sys_K"] if tsys_results else 50.0
                )
                result = run_noise_validation(
                    ms_path, output_dir, system_temp, efficiency=0.7
                )
                if result:
                    noise_validation_results.append(result)
                break

    # Aggregate and generate report
    aggregated = aggregate_results(
        tsys_results, stability_results, noise_validation_results
    )
    recommendations = generate_parameter_recommendations(aggregated)
    save_comprehensive_report(aggregated, recommendations, output_dir)

    logger.info("\n" + "=" * 70)
    logger.info("System characterization complete!")
    logger.info(f"Results saved to: {output_dir}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

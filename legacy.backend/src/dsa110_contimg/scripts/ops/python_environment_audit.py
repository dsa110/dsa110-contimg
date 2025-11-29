#!/opt/miniforge/envs/casa6/bin/python
"""Audit script to verify Python 3.11.13 (CASA6) is the only environment used."""

import os
import subprocess
import sys
from pathlib import Path

# Colors for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
NC = "\033[0m"  # No Color

CASA6_PYTHON = "/opt/miniforge/envs/casa6/bin/python"
REQUIRED_VERSION = "3.11.13"
SYSTEM_PYTHON = "/usr/bin/python3"

issues = []
warnings = []
passes = []


def check_casa6_exists():
    """Check if CASA6 Python exists and verify version"""
    if not os.path.exists(CASA6_PYTHON):
        issues.append(f"CASA6 Python not found at {CASA6_PYTHON}")
        return False

    try:
        result = subprocess.run(
            [CASA6_PYTHON, "--version"], capture_output=True, text=True, timeout=5
        )
        version = result.stdout.strip()
        if REQUIRED_VERSION in version:
            passes.append(f"CASA6 Python exists: {version}")
            return True
        else:
            warnings.append(
                f"CASA6 Python version mismatch: {version} (expected {REQUIRED_VERSION})"
            )
            return True
    except Exception as e:
        issues.append(f"Failed to check CASA6 Python version: {e}")
        return False


def check_systemd_services():
    """Check systemd service files for Python usage"""
    service_files = [
        "ops/systemd/contimg-api.service",
        "ops/systemd/contimg-pointing-monitor.service",
        "ops/systemd/contimg-stream.service",
        "ops/systemd/contimg-test-monitor.service",
        "ops/systemd/dsa110-contimg-api.service",
        "scripts/services/casa-log-daemon.service",
        "scripts/services/casa-log-daemon-inotify-python.service",
    ]

    project_root = Path(__file__).parent.parent

    for service_file in service_files:
        path = project_root / service_file
        if not path.exists():
            warnings.append(f"Service file not found: {service_file}")
            continue

        try:
            content = path.read_text()
            if SYSTEM_PYTHON in content:
                issues.append(f"{service_file}: Uses {SYSTEM_PYTHON} (should use {CASA6_PYTHON})")
            elif CASA6_PYTHON in content:
                passes.append(f"{service_file}: Correctly uses CASA6 Python")
            elif "python3" in content and CASA6_PYTHON not in content:
                warnings.append(
                    f"{service_file}: Uses 'python3' (should explicitly use {CASA6_PYTHON})"
                )
        except Exception as e:
            warnings.append(f"Failed to read {service_file}: {e}")


def check_python_scripts():
    """Check Python scripts for shebang lines"""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    scripts_dir = project_root / "scripts"

    python_files = []

    # Find all .py files
    for directory in [src_dir, scripts_dir]:
        if directory.exists():
            python_files.extend(directory.rglob("*.py"))

    shebang_issues = []
    shebang_warnings = []
    shebang_passes = []

    for py_file in python_files:
        try:
            with open(py_file, "rb") as f:
                first_line = f.readline().decode("utf-8", errors="ignore").strip()

                if first_line.startswith("#!"):
                    if first_line.startswith("#!/usr/bin/env python3") or first_line.startswith(
                        "#!/usr/bin/python3"
                    ):
                        shebang_issues.append(
                            f"{py_file.relative_to(project_root)}: Uses generic python3 shebang (should use CASA6 Python)"
                        )
                    elif CASA6_PYTHON in first_line:
                        shebang_passes.append(
                            f"{py_file.relative_to(project_root)}: Uses CASA6 Python shebang"
                        )
                    elif SYSTEM_PYTHON in first_line:
                        shebang_issues.append(
                            f"{py_file.relative_to(project_root)}: Uses system Python shebang"
                        )
        except Exception as e:
            warnings.append(f"Failed to read {py_file}: {e}")

    return shebang_issues, shebang_warnings, shebang_passes


def check_makefile():
    """Check Makefile for Python usage"""
    project_root = Path(__file__).parent.parent
    makefile = project_root / "Makefile"

    if not makefile.exists():
        warnings.append("Makefile not found")
        return

    try:
        content = makefile.read_text()
        if CASA6_PYTHON in content:
            passes.append("Makefile: Uses CASA6_PYTHON variable")
        else:
            warnings.append("Makefile: Does not use CASA6_PYTHON variable")
    except Exception as e:
        warnings.append(f"Failed to read Makefile: {e}")


def check_job_runner():
    """Check job runner for Python environment configuration"""
    project_root = Path(__file__).parent.parent
    job_runner = project_root / "src" / "dsa110_contimg" / "api" / "job_runner.py"

    if not job_runner.exists():
        warnings.append("job_runner.py not found")
        return

    try:
        content = job_runner.read_text()
        if "CONTIMG_JOB_PY" in content or "CONTIMG_CONDA_ENV" in content:
            passes.append(
                "job_runner.py: Supports environment configuration via CONTIMG_JOB_PY/CONTIMG_CONDA_ENV"
            )
        else:
            warnings.append("job_runner.py: Does not configure Python environment explicitly")
    except Exception as e:
        warnings.append(f"Failed to read job_runner.py: {e}")


def main():
    """Run all checks"""
    print("=" * 70)
    print("Python Environment Audit - CASA6 (Python 3.11.13) Verification")
    print("=" * 70)
    print()

    # Run checks
    check_casa6_exists()
    check_systemd_services()
    check_makefile()
    check_job_runner()
    shebang_issues, shebang_warnings, shebang_passes = check_python_scripts()

    # Report results
    print(f"{GREEN}:check_mark: PASSES ({len(passes) + len(shebang_passes)}):{NC}")
    for item in passes[:10]:  # Show first 10
        print(f"  {GREEN}:check_mark:{NC} {item}")
    if len(passes) > 10:
        print(f"  ... and {len(passes) - 10} more")
    print()

    print(f"{YELLOW}:warning_sign: WARNINGS ({len(warnings) + len(shebang_warnings)}):{NC}")
    for item in warnings[:10]:  # Show first 10
        print(f"  {YELLOW}:warning_sign:{NC} {item}")
    for item in shebang_warnings[:10]:  # Show first 10
        print(f"  {YELLOW}:warning_sign:{NC} {item}")
    if len(warnings) + len(shebang_warnings) > 10:
        shown = min(10, len(warnings)) + min(10, len(shebang_warnings))
        print(f"  ... and {len(warnings) + len(shebang_warnings) - shown} more")
    print()

    print(f"{RED}:ballot_x: ISSUES ({len(issues) + len(shebang_issues)}):{NC}")
    for item in issues:
        print(f"  {RED}:ballot_x:{NC} {item}")
    for item in shebang_issues[:20]:  # Show first 20
        print(f"  {RED}:ballot_x:{NC} {item}")
    if len(shebang_issues) > 20:
        print(f"  ... and {len(shebang_issues) - 20} more")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total_checks = (
        len(passes)
        + len(warnings)
        + len(issues)
        + len(shebang_passes)
        + len(shebang_warnings)
        + len(shebang_issues)
    )
    print(f"Total checks: {total_checks}")
    print(f"{GREEN}Passes: {len(passes) + len(shebang_passes)}{NC}")
    print(f"{YELLOW}Warnings: {len(warnings) + len(shebang_warnings)}{NC}")
    print(f"{RED}Issues: {len(issues) + len(shebang_issues)}{NC}")
    print()

    if len(issues) + len(shebang_issues) == 0:
        print(f"{GREEN}:check_mark: All issues resolved! All Python scripts use CASA6 Python 3.11.13.{NC}")
        return 0
    else:
        print(
            f"{RED}:ballot_x: Found {len(issues) + len(shebang_issues)} critical issues that need to be fixed.{NC}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

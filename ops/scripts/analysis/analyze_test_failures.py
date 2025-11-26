#!/usr/bin/env python3
"""
Comprehensive test failure analysis tool.
Categorizes failures by type and provides actionable insights.
"""
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


def run_pytest_with_json():
    """Run pytest and capture JSON output."""
    cmd = [
        "/opt/miniforge/envs/casa6/bin/python",
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--json-report",
        "--json-report-file=/tmp/pytest_report.json",
    ]
    try:
        result = subprocess.run(
            cmd, cwd="/data/dsa110-contimg", capture_output=True, text=True, timeout=600
        )
        return result
    except subprocess.TimeoutExpired:
        print("Test run timed out after 10 minutes")
        return None


def parse_pytest_output(output):
    """Parse pytest output to extract failure information."""
    failures = defaultdict(list)
    errors = defaultdict(list)
    current_test = None

    lines = output.split("\n")
    for i, line in enumerate(lines):
        # Match test names
        test_match = re.match(r"tests/([^:]+)::([^:]+)::(.+)$", line)
        if test_match:
            module = test_match.group(1)
            class_name = test_match.group(2) if test_match.group(2) else None
            test_name = test_match.group(3)
            current_test = {
                "module": module,
                "class": class_name,
                "test": test_name,
                "full_path": line.strip(),
            }

        # Match FAILED or ERROR status
        if "FAILED" in line and current_test:
            failures[current_test["module"]].append(current_test.copy())
        elif "ERROR" in line and current_test:
            errors[current_test["module"]].append(current_test.copy())

    return failures, errors


def categorize_error(error_msg):
    """Categorize error by type."""
    error_lower = error_msg.lower()

    if "attributeerror" in error_lower:
        return "AttributeError"
    elif "keyerror" in error_lower:
        return "KeyError"
    elif "assertionerror" in error_lower:
        return "AssertionError"
    elif "importerror" in error_lower or "modulenotfounderror" in error_lower:
        return "ImportError"
    elif "typeerror" in error_lower:
        return "TypeError"
    elif "valueerror" in error_lower:
        return "ValueError"
    elif "filenotfounderror" in error_lower or "oserror" in error_lower:
        return "FileNotFoundError"
    elif "timeout" in error_lower:
        return "Timeout"
    elif "connection" in error_lower or "network" in error_lower:
        return "ConnectionError"
    else:
        return "Other"


def get_detailed_failures():
    """Get detailed failure information by running tests individually."""
    cmd = [
        "/opt/miniforge/envs/casa6/bin/python",
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "-q",
    ]

    result = subprocess.run(
        cmd, cwd="/data/dsa110-contimg", capture_output=True, text=True, timeout=600
    )

    failures = []
    errors = []
    current_failure = None

    output_lines = result.stdout.split("\n") + result.stderr.split("\n")

    for i, line in enumerate(output_lines):
        # Match FAILED tests
        if "FAILED" in line:
            test_match = re.search(r"tests/([^:]+)::([^::]+)::(.+?)\s+FAILED", line)
            if test_match:
                current_failure = {
                    "module": test_match.group(1),
                    "class": test_match.group(2) if "::" in test_match.group(2) else None,
                    "test": test_match.group(3),
                    "type": "FAILED",
                    "error": None,
                }

        # Match ERROR tests
        elif "ERROR" in line and "FAILED" not in line:
            test_match = re.search(r"tests/([^:]+)::([^::]+)::(.+?)\s+ERROR", line)
            if test_match:
                current_failure = {
                    "module": test_match.group(1),
                    "class": test_match.group(2) if "::" in test_match.group(2) else None,
                    "test": test_match.group(3),
                    "type": "ERROR",
                    "error": None,
                }

        # Capture error messages
        if current_failure and (
            "Error:" in line
            or "Exception:" in line
            or "AssertionError" in line
            or "AttributeError" in line
            or "KeyError" in line
            or "TypeError" in line
        ):
            if current_failure["error"] is None:
                current_failure["error"] = line.strip()
                if current_failure["type"] == "FAILED":
                    failures.append(current_failure)
                else:
                    errors.append(current_failure)
                current_failure = None

    return failures, errors


def generate_report():
    """Generate comprehensive failure report."""
    print("=" * 80)
    print("TEST FAILURE ANALYSIS REPORT")
    print("=" * 80)
    print()

    # Get basic counts
    cmd = ["/opt/miniforge/envs/casa6/bin/python", "-m", "pytest", "tests/", "-v", "--co", "-q"]

    result = subprocess.run(cmd, cwd="/data/dsa110-contimg", capture_output=True, text=True)

    # Count failures and errors from the original output
    all_output = result.stdout + result.stderr
    failed_count = len(re.findall(r"FAILED", all_output))
    error_count = len(re.findall(r"ERROR", all_output))
    passed_count = len(re.findall(r"PASSED", all_output))
    skipped_count = len(re.findall(r"SKIPPED", all_output))

    print(f"SUMMARY:")
    print(f"  Total Tests: {failed_count + error_count + passed_count + skipped_count}")
    print(f"  PASSED: {passed_count}")
    print(f"  FAILED: {failed_count}")
    print(f"  ERROR: {error_count}")
    print(f"  SKIPPED: {skipped_count}")
    print()

    # Get detailed failures
    print("Analyzing detailed failure information...")
    failures, errors = get_detailed_failures()

    # Categorize by module
    module_failures = defaultdict(list)
    module_errors = defaultdict(list)

    for f in failures:
        module_failures[f["module"]].append(f)
    for e in errors:
        module_errors[e["module"]].append(e)

    print()
    print("=" * 80)
    print("FAILURES BY MODULE")
    print("=" * 80)

    all_modules = set(list(module_failures.keys()) + list(module_errors.keys()))
    for module in sorted(all_modules):
        fail_count = len(module_failures.get(module, []))
        error_count = len(module_errors.get(module, []))
        if fail_count > 0 or error_count > 0:
            print(f"\n{module}:")
            print(f"  FAILED: {fail_count}")
            print(f"  ERROR: {error_count}")

            # Show sample failures
            if module_failures.get(module):
                print(f"  Sample failures:")
                for f in module_failures[module][:3]:
                    print(
                        f"    - {f.get('test', 'unknown')}: {f.get('error', 'No error message')[:100]}"
                    )

    # Categorize by error type
    print()
    print("=" * 80)
    print("FAILURES BY ERROR TYPE")
    print("=" * 80)

    error_types = defaultdict(int)
    for f in failures + errors:
        error_msg = f.get("error", "")
        error_type = categorize_error(error_msg)
        error_types[error_type] += 1

    for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
        print(f"  {error_type}: {count}")

    # Identify common patterns
    print()
    print("=" * 80)
    print("COMMON PATTERNS")
    print("=" * 80)

    # Check for common issues
    attribute_errors = [f for f in failures + errors if "AttributeError" in str(f.get("error", ""))]
    key_errors = [f for f in failures + errors if "KeyError" in str(f.get("error", ""))]
    assertion_errors = [f for f in failures + errors if "AssertionError" in str(f.get("error", ""))]

    if attribute_errors:
        print(f"\nAttributeError issues ({len(attribute_errors)}):")
        print("  Common causes: Missing attributes, wrong object types, mock issues")
        for f in attribute_errors[:5]:
            print(f"    - {f.get('module', 'unknown')}::{f.get('test', 'unknown')}")

    if key_errors:
        print(f"\nKeyError issues ({len(key_errors)}):")
        print("  Common causes: Missing dictionary keys, DataFrame column issues")
        for f in key_errors[:5]:
            print(f"    - {f.get('module', 'unknown')}::{f.get('test', 'unknown')}")

    if assertion_errors:
        print(f"\nAssertionError issues ({len(assertion_errors)}):")
        print("  Common causes: Test expectations not met, logic errors")
        for f in assertion_errors[:5]:
            print(f"    - {f.get('module', 'unknown')}::{f.get('test', 'unknown')}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("1. Start with AttributeError and KeyError fixes - these are often")
    print("   quick wins that can resolve multiple test failures.")
    print()
    print("2. Check for common root causes:")
    print("   - Missing database files or test fixtures")
    print("   - Mock objects not properly configured")
    print("   - API/interface changes not reflected in tests")
    print("   - Missing dependencies or environment setup")
    print()
    print("3. Focus on high-impact modules first:")
    for module, count in sorted(module_failures.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"   - {module}: {len(module_failures[module])} failures")
    print()
    print("4. Consider using pytest-xdist for parallel test execution")
    print("   to speed up debugging cycles.")
    print()


if __name__ == "__main__":
    generate_report()

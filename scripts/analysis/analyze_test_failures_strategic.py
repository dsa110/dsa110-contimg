#!/usr/bin/env python3
"""
Strategic test failure analysis tool.
Categorizes failures by error type, environment issues, and code issues.
"""
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


def run_pytest_with_detailed_output():
    """Run pytest and capture detailed failure information."""
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
        cmd, cwd="/data/dsa110-contimg", capture_output=True, text=True, timeout=900  # 15 minutes
    )

    return result.stdout + result.stderr


def check_environment():
    """Check if tests are running in the correct environment."""
    import os
    import sys

    env_info = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "Not set"),
        "path_includes_casa6": "casa6" in sys.executable,
        "environment_variables": {
            "CASA6_ENV": os.environ.get("CASA6_ENV", "Not set"),
            "PATH": os.environ.get("PATH", "Not set")[:200] + "...",
        },
    }

    return env_info


def categorize_error(error_msg, test_path):
    """Categorize error by type and likely cause."""
    error_lower = error_msg.lower()
    test_lower = test_path.lower()

    categories = {
        "environment": False,
        "import_error": False,
        "missing_file": False,
        "database": False,
        "mock_setup": False,
        "assertion": False,
        "type_error": False,
        "attribute_error": False,
        "key_error": False,
        "network": False,
        "timeout": False,
        "frontend_e2e": False,
    }

    # Environment issues
    if any(x in error_lower for x in ["modulenotfound", "importerror", "no module named"]):
        categories["import_error"] = True
        categories["environment"] = True

    # Missing files/databases
    if any(
        x in error_lower
        for x in ["filenotfound", "no such file", "does not exist", "database", "sqlite"]
    ):
        categories["missing_file"] = True
        if "database" in error_lower or "sqlite" in error_lower:
            categories["database"] = True

    # Mock issues
    if any(x in error_lower for x in ["magicmock", "mock", "patch", "fixture"]):
        categories["mock_setup"] = True

    # Type errors
    if "attributeerror" in error_lower:
        categories["attribute_error"] = True
    if "keyerror" in error_lower:
        categories["key_error"] = True
    if "typeerror" in error_lower:
        categories["type_error"] = True

    # Assertion errors (test logic issues)
    if "assertionerror" in error_lower or "assert" in error_lower:
        categories["assertion"] = True

    # Network/timeout issues
    if any(x in error_lower for x in ["timeout", "connection", "network", "http"]):
        categories["network"] = True
        if "timeout" in error_lower:
            categories["timeout"] = True

    # Frontend/e2e tests
    if any(
        x in test_lower
        for x in ["e2e", "frontend", "test_all_pages", "test_control", "test_dashboard"]
    ):
        categories["frontend_e2e"] = True

    return categories


def parse_test_output(output):
    """Parse pytest output to extract failure information."""
    failures = []
    errors = []

    lines = output.split("\n")
    current_test = None
    current_error = []
    in_error_block = False

    for i, line in enumerate(lines):
        # Match test names with FAILED
        failed_match = re.search(r"tests/([^:]+)::([^::]+)::(.+?)\s+FAILED", line)
        if failed_match:
            if current_test:
                # Save previous test
                if current_error:
                    current_test["error_message"] = "\n".join(current_error)
                    failures.append(current_test)
            current_test = {
                "module": failed_match.group(1),
                "class": failed_match.group(2) if "::" in failed_match.group(2) else None,
                "test": failed_match.group(3),
                "type": "FAILED",
                "error_message": "",
                "full_path": line.strip(),
            }
            current_error = []
            in_error_block = False

        # Match test names with ERROR
        error_match = re.search(r"tests/([^:]+)::([^::]+)::(.+?)\s+ERROR", line)
        if error_match and "FAILED" not in line:
            if current_test:
                if current_error:
                    current_test["error_message"] = "\n".join(current_error)
                    errors.append(current_test)
            current_test = {
                "module": error_match.group(1),
                "class": error_match.group(2) if "::" in error_match.group(2) else None,
                "test": error_match.group(3),
                "type": "ERROR",
                "error_message": "",
                "full_path": line.strip(),
            }
            current_error = []
            in_error_block = False

        # Collect error messages
        if current_test and (
            line.strip().startswith("E ")
            or "Error:" in line
            or "Exception:" in line
            or "AssertionError" in line
            or "AttributeError" in line
            or "KeyError" in line
            or "TypeError" in line
            or "ImportError" in line
            or "ModuleNotFoundError" in line
            or "FileNotFoundError" in line
        ):
            if len(current_error) < 10:  # Limit error message length
                current_error.append(line.strip())
            in_error_block = True
        elif current_test and in_error_block and line.strip() and not line.startswith(" "):
            # End of error block
            in_error_block = False

    # Save last test
    if current_test:
        if current_error:
            current_test["error_message"] = "\n".join(current_error)
        if current_test["type"] == "FAILED":
            failures.append(current_test)
        else:
            errors.append(current_test)

    return failures, errors


def analyze_failures():
    """Main analysis function."""
    print("=" * 80)
    print("STRATEGIC TEST FAILURE ANALYSIS")
    print("=" * 80)
    print()

    # Check environment
    print("1. ENVIRONMENT CHECK")
    print("-" * 80)
    env_info = check_environment()
    print(f"Python executable: {env_info['python_executable']}")
    print(f"Python version: {env_info['python_version'].split()[0]}")
    print(f"Conda environment: {env_info['conda_env']}")
    print(f"Running in casa6 env: {env_info['path_includes_casa6']}")

    if not env_info["path_includes_casa6"]:
        print("⚠️  WARNING: Tests may not be running in casa6 environment!")
    else:
        print("✓ Tests are running in casa6 environment")
    print()

    # Run tests and parse output
    print("2. RUNNING TESTS AND COLLECTING FAILURES")
    print("-" * 80)
    print("This may take several minutes...")
    output = run_pytest_with_detailed_output()

    # Parse failures
    failures, errors = parse_test_output(output)

    print(f"Found {len(failures)} FAILED tests")
    print(f"Found {len(errors)} ERROR tests")
    print()

    # Categorize failures
    print("3. CATEGORIZING FAILURES")
    print("-" * 80)

    category_counts = defaultdict(int)
    category_examples = defaultdict(list)

    all_issues = failures + errors

    for issue in all_issues:
        test_path = issue.get("full_path", "")
        error_msg = issue.get("error_message", "").lower()
        categories = categorize_error(error_msg, test_path)

        for category, is_match in categories.items():
            if is_match:
                category_counts[category] += 1
                if len(category_examples[category]) < 5:
                    category_examples[category].append(
                        {
                            "test": issue.get("test", "unknown"),
                            "module": issue.get("module", "unknown"),
                            "error": error_msg[:150],
                        }
                    )

    # Print categorized results
    print("\nFailure Categories (sorted by frequency):")
    print()
    for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {category.upper()}: {count} tests")
        if category_examples[category]:
            print(f"    Examples:")
            for ex in category_examples[category][:3]:
                print(f"      - {ex['module']}::{ex['test']}")
                print(f"        {ex['error'][:100]}...")
        print()

    # Group by module
    print("4. FAILURES BY MODULE")
    print("-" * 80)
    module_failures = defaultdict(int)
    for issue in all_issues:
        module_failures[issue.get("module", "unknown")] += 1

    for module, count in sorted(module_failures.items(), key=lambda x: -x[1])[:15]:
        print(f"  {module}: {count} failures")
    print()

    # Recommendations
    print("5. RECOMMENDATIONS")
    print("-" * 80)

    if category_counts["frontend_e2e"] > 50:
        print("⚠️  Frontend/E2E tests: Many failures likely due to missing browser/server setup")
        print("   Action: Check if Playwright/Selenium browsers are installed")
        print()

    if category_counts["environment"] > 20:
        print("⚠️  Environment issues: Missing dependencies or wrong environment")
        print("   Action: Verify casa6 conda environment has all required packages")
        print()

    if category_counts["database"] > 10:
        print("⚠️  Database issues: Missing test databases or fixtures")
        print("   Action: Check if test database fixtures are properly set up")
        print()

    if category_counts["mock_setup"] > 20:
        print("⚠️  Mock setup issues: Tests need proper mocking/fixtures")
        print("   Action: Review and fix test fixtures and mocks")
        print()

    if category_counts["assertion"] > 50:
        print("⚠️  Assertion failures: Test expectations may need updating")
        print("   Action: Review failing assertions - may be due to code changes")
        print()

    # Save detailed report
    report_file = Path("/tmp/test_failure_analysis.json")
    report_data = {
        "environment": env_info,
        "summary": {
            "total_failures": len(failures),
            "total_errors": len(errors),
            "category_counts": dict(category_counts),
        },
        "failures": failures[:100],  # Limit to first 100
        "errors": errors[:100],
    }

    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\nDetailed report saved to: {report_file}")
    print()

    return category_counts, failures, errors


if __name__ == "__main__":
    analyze_failures()

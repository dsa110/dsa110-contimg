#!/usr/bin/env python3
"""
Test Organization Validator

Enforces test organization rules automatically. This script:
1. Validates test file locations match their purpose
2. Checks for required pytest markers
3. Ensures tests are in appropriate directories
4. Provides actionable feedback

Run this in CI/CD or as a pre-commit hook.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

# Test taxonomy mapping
TAXONOMY = {
    "smoke": {
        "path": "tests/smoke/",
        "marker": "smoke",
        "description": "Quick sanity checks (< 10s)",
    },
    "unit": {
        "path": "tests/unit/",
        "marker": "unit",
        "description": "Fast, isolated, mocked tests",
        "subdirs": [
            "api",
            "calibration",
            "catalog",
            "conversion",
            "database",
            "imaging",
            "mosaic",
            "photometry",
            "pipeline",
            "qa",
            "simulation",
            "visualization",
        ],
    },
    "integration": {
        "path": "tests/integration/",
        "marker": "integration",
        "description": "Component interaction tests",
    },
    "science": {
        "path": "tests/science/",
        "marker": "science",
        "description": "Science validation tests",
    },
    "e2e": {
        "path": "tests/e2e/",
        "marker": "e2e",
        "description": "End-to-end workflow tests",
    },
}

# Allowed test locations (outside main taxonomy)
ALLOWED_SPECIAL_LOCATIONS = [
    "tests/docs/",  # Documentation tests
    "tests/scripts/",  # Script tests
    "tests/utils/",  # Utility tests
    "tests/validation/",  # Validation framework tests
]


@dataclass
class TestFile:
    path: Path
    category: str = None
    has_marker: bool = False
    marker_type: str = None
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


def find_all_test_files(root: Path) -> List[Path]:
    """Find all test files in the tests directory."""
    test_files = []
    for test_file in root.rglob("test_*.py"):
        # Skip __pycache__ and .pyc files
        if "__pycache__" not in str(test_file) and test_file.suffix == ".py":
            test_files.append(test_file)
    return sorted(test_files)


def read_test_file(path: Path) -> Tuple[str, bool, str]:
    """Read test file and check for markers."""
    try:
        content = path.read_text()

        # Check for pytest markers
        marker_pattern = r"@pytest\.mark\.(\w+)"
        markers = re.findall(marker_pattern, content)

        # Check if file has any test functions or test classes
        has_tests = bool(
            re.search(r"^(def|class)\s+test_", content, re.MULTILINE)
            or re.search(r"^class\s+Test\w+", content, re.MULTILINE)
        )

        primary_marker = markers[0] if markers else None

        return content, has_tests, primary_marker
    except Exception as e:
        return "", False, None


def determine_expected_category(test_path: Path, root: Path) -> Tuple[str, List[str]]:
    """Determine expected category based on file path."""
    rel_path = test_path.relative_to(root)
    path_str = str(rel_path)

    issues = []

    # Check if in special allowed locations
    for allowed in ALLOWED_SPECIAL_LOCATIONS:
        if path_str.startswith(allowed):
            return "special", issues

    # Check taxonomy
    for category, config in TAXONOMY.items():
        expected_path = config["path"]
        if path_str.startswith(expected_path):
            # For unit tests, check if in appropriate subdirectory
            if category == "unit":
                subdirs = config.get("subdirs", [])
                # Check if in a subdirectory
                parts = path_str.split("/")
                if len(parts) > 3:  # tests/unit/<subdir>/test_*.py
                    subdir = parts[2]
                    if subdir not in subdirs and subdir != "unit":
                        issues.append(
                            f"Unit test in unexpected subdirectory: {subdir}. "
                            f"Expected one of: {', '.join(subdirs)}"
                        )
            return category, issues

    # Not in expected location
    issues.append(
        f"Test file not in expected location. Expected one of: "
        f"{', '.join([c['path'] for c in TAXONOMY.values()])}"
    )
    return "unknown", issues


def validate_test_file(test_path: Path, root: Path) -> TestFile:
    """Validate a single test file."""
    test_file = TestFile(path=test_path)

    # Determine expected category
    category, path_issues = determine_expected_category(test_path, root)
    test_file.category = category
    test_file.issues.extend(path_issues)

    # Read file and check markers
    content, has_tests, marker = read_test_file(test_path)

    if not has_tests:
        test_file.issues.append("File contains no test functions (def test_* or class Test*)")
        return test_file

    if marker:
        test_file.has_marker = True
        test_file.marker_type = marker

        # Check if marker matches location
        if category != "special" and category != "unknown":
            expected_marker = TAXONOMY[category]["marker"]
            if marker != expected_marker:
                test_file.issues.append(
                    f"Marker mismatch: has @pytest.mark.{marker} but location suggests "
                    f"@pytest.mark.{expected_marker}"
                )
    else:
        # No marker found - this is a warning for unit/integration/science/e2e
        if category in TAXONOMY:
            test_file.issues.append(
                f"Missing pytest marker. Expected @pytest.mark.{TAXONOMY[category]['marker']} "
                f"for tests in {TAXONOMY[category]['path']}"
            )

    return test_file


def main():
    """Main validation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate test organization")
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Only validate staged test files (for pre-commit)",
    )
    parser.add_argument("--strict", action="store_true", help="Strict mode: warnings become errors")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    tests_dir = root / "tests"

    if not tests_dir.exists():
        print(f"ERROR: tests directory not found at {tests_dir}")
        sys.exit(1)

    if args.staged_only:
        # Get staged test files from git
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                capture_output=True,
                text=True,
                cwd=root,
            )
            staged_files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
            test_files = [
                root / f
                for f in staged_files
                if "test_" in f and f.endswith(".py") and f.startswith("tests/")
            ]
            if not test_files:
                print("No staged test files to validate")
                sys.exit(0)
            print(f"Validating {len(test_files)} staged test files...")
        except Exception as e:
            print(f"ERROR: Could not get staged files: {e}")
            sys.exit(1)
    else:
        test_files = find_all_test_files(tests_dir)

    if not test_files:
        print("WARNING: No test files found")
        sys.exit(0)

    print(f"Validating {len(test_files)} test files...")
    print()

    validated = []
    errors = []
    warnings = []

    for test_file in test_files:
        result = validate_test_file(test_file, root)
        validated.append(result)

        if result.issues:
            for issue in result.issues:
                if "ERROR" in issue or "not in expected location" in issue:
                    errors.append((result.path, issue))
                else:
                    warnings.append((result.path, issue))

    # Report results
    if errors:
        print("=" * 80)
        print("ERRORS (must be fixed):")
        print("=" * 80)
        for path, issue in errors:
            rel_path = path.relative_to(root)
            print(f"  {rel_path}")
            print(f"    {issue}")
            print()

    if warnings:
        print("=" * 80)
        print("WARNINGS (should be fixed):")
        print("=" * 80)
        for path, issue in warnings:
            rel_path = path.relative_to(root)
            print(f"  {rel_path}")
            print(f"    {issue}")
            print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total test files: {len(test_files)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Valid: {len(test_files) - len(errors) - len(warnings)}")
    print()

    # In strict mode, treat warnings as errors
    if args.strict and warnings:
        print("FAILED: Test organization has warnings (strict mode).")
        sys.exit(1)

    if errors:
        print("FAILED: Test organization has errors that must be fixed.")
        sys.exit(1)
    elif warnings:
        print("PASSED with warnings: Test organization is mostly correct but has warnings.")
        if args.staged_only:
            print("NOTE: Some warnings may be from other files. Fix staged files first.")
        sys.exit(0)
    else:
        print("PASSED: All tests are properly organized.")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Quick failure analysis focusing on error patterns."""
import re
import subprocess
from collections import defaultdict


def analyze_failures():
    """Run tests and categorize failures quickly."""
    print("=" * 80)
    print("QUICK FAILURE ANALYSIS")
    print("=" * 80)
    print()

    # Run tests with limited output
    cmd = [
        "/opt/miniforge/envs/casa6/bin/python",
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=line",
        "-q",
    ]

    result = subprocess.run(
        cmd, cwd="/data/dsa110-contimg", capture_output=True, text=True, timeout=600
    )

    output = result.stdout + result.stderr

    # Categorize by error type
    categories = {
        "playwright_browser": [],
        "mock_setup": [],
        "database_missing": [],
        "assertion_failures": [],
        "import_errors": [],
        "attribute_errors": [],
        "key_errors": [],
        "type_errors": [],
        "other": [],
    }

    lines = output.split("\n")
    current_test = None

    for line in lines:
        # Match test names
        test_match = re.search(r"tests/([^:]+)::([^::]+)::(.+?)\s+(FAILED|ERROR)", line)
        if test_match:
            current_test = {
                "module": test_match.group(1),
                "test": test_match.group(3),
                "type": test_match.group(4),
                "line": line,
            }

        # Categorize errors
        if current_test:
            line_lower = line.lower()

            if "playwright" in line_lower and "executable" in line_lower:
                categories["playwright_browser"].append(current_test.copy())
                current_test = None
            elif "magicmock" in line_lower or "mock" in line_lower and "assertion" in line_lower:
                categories["mock_setup"].append(current_test.copy())
                current_test = None
            elif "database" in line_lower or "sqlite" in line_lower or "filenotfound" in line_lower:
                categories["database_missing"].append(current_test.copy())
                current_test = None
            elif "assertionerror" in line_lower:
                categories["assertion_failures"].append(current_test.copy())
                current_test = None
            elif "importerror" in line_lower or "modulenotfound" in line_lower:
                categories["import_errors"].append(current_test.copy())
                current_test = None
            elif "attributeerror" in line_lower:
                categories["attribute_errors"].append(current_test.copy())
                current_test = None
            elif "keyerror" in line_lower:
                categories["key_errors"].append(current_test.copy())
                current_test = None
            elif "typeerror" in line_lower:
                categories["type_errors"].append(current_test.copy())
                current_test = None

    # Print summary
    print("FAILURE CATEGORIES:")
    print("-" * 80)

    total = sum(len(v) for v in categories.values())

    for category, tests in sorted(categories.items(), key=lambda x: -len(x[1])):
        if tests:
            count = len(tests)
            percentage = (count / total * 100) if total > 0 else 0
            print(f"\n{category.upper()}: {count} tests ({percentage:.1f}%)")

            # Show examples
            for test in tests[:3]:
                print(f"  - {test['module']}::{test['test']}")

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)

    if categories["playwright_browser"]:
        print("\n1. PLAYWRIGHT BROWSER SETUP (Environment Issue)")
        print(f"   {len(categories['playwright_browser'])} tests failing")
        print("   Fix: Run 'playwright install chromium' in casa6 environment")
        print("   Command: /opt/miniforge/envs/casa6/bin/python -m playwright install chromium")

    if categories["mock_setup"]:
        print("\n2. MOCK SETUP ISSUES (Test Code Issue)")
        print(f"   {len(categories['mock_setup'])} tests failing")
        print("   Fix: Review and fix mock configurations in test files")
        print("   Affected modules:")
        modules = set(t["module"] for t in categories["mock_setup"])
        for mod in sorted(modules)[:5]:
            print(f"     - {mod}")

    if categories["database_missing"]:
        print("\n3. DATABASE/FILE MISSING (Test Fixture Issue)")
        print(f"   {len(categories['database_missing'])} tests failing")
        print("   Fix: Ensure test fixtures create required databases/files")

    if categories["assertion_failures"]:
        print("\n4. ASSERTION FAILURES (Test Logic Issue)")
        print(f"   {len(categories['assertion_failures'])} tests failing")
        print("   Fix: Review assertions - may need updating after code changes")

    print("\n" + "=" * 80)
    print(f"TOTAL FAILURES ANALYZED: {total}")
    print("=" * 80)


if __name__ == "__main__":
    analyze_failures()

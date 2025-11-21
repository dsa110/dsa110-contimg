#!/opt/miniforge/envs/casa6/bin/python
"""
Test File Template Generator

Creates a properly organized test file with correct markers and structure.

Usage:
    python scripts/test-template.py unit api new_feature
    python scripts/test-template.py integration new_workflow
    python scripts/test-template.py smoke critical_path
"""

import sys
from pathlib import Path

TEMPLATES = {
    "unit": """#!/usr/bin/env python3
\"\"\"
Unit tests for {module_description}.

Tests:
- {feature} functionality
\"\"\"
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
def test_{feature}_basic():
    \"\"\"Test basic {feature} functionality.\"\"\"
    # TODO: Implement test
    pass

@pytest.mark.unit
class Test{Feature}:
    \"\"\"Test class for {feature}.\"\"\"
    
    def test_{feature}_success(self):
        \"\"\"Test successful {feature} operation.\"\"\"
        # TODO: Implement test
        pass
""",
    "integration": """#!/usr/bin/env python3
\"\"\"
Integration tests for {workflow_description}.

Tests:
- {workflow} workflow execution
- Component interactions
\"\"\"
import pytest

@pytest.mark.integration
class Test{Workflow}:
    \"\"\"Integration tests for {workflow} workflow.\"\"\"
    
    def test_{workflow}_completes(self):
        \"\"\"Test that {workflow} workflow completes successfully.\"\"\"
        # TODO: Implement test
        pass
""",
    "smoke": """#!/usr/bin/env python3
\"\"\"
Smoke test for {critical_path_description}.

Quick sanity check for {critical_path}.
\"\"\"
import pytest

@pytest.mark.smoke
def test_{critical_path}_works():
    \"\"\"Quick check that {critical_path} is functional.\"\"\"
    # TODO: Implement test
    pass
""",
}


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/test-template.py <type> <module> <feature>")
        print("       python scripts/test-template.py <type> <name>")
        print()
        print("Types: unit, integration, smoke, science, e2e")
        print()
        print("Examples:")
        print("  python scripts/test-template.py unit api new_endpoint")
        print("  python scripts/test-template.py integration new_workflow")
        print("  python scripts/test-template.py smoke critical_imports")
        sys.exit(1)

    test_type = sys.argv[1]
    if test_type not in TEMPLATES:
        print(f"ERROR: Unknown test type '{test_type}'")
        print(f"Valid types: {', '.join(TEMPLATES.keys())}")
        sys.exit(1)

    if test_type == "unit":
        if len(sys.argv) < 4:
            print("ERROR: Unit tests require module and feature name")
            print("Usage: python scripts/test-template.py unit <module> <feature>")
            sys.exit(1)
        module = sys.argv[2]
        feature = sys.argv[3]

        # Validate module
        valid_modules = [
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
        ]
        if module not in valid_modules:
            print(f"ERROR: Invalid module '{module}'")
            print(f"Valid modules: {', '.join(valid_modules)}")
            sys.exit(1)

        output_path = Path(f"tests/unit/{module}/test_{module}_{feature}.py")
        content = TEMPLATES[test_type].format(
            module_description=f"{module} module",
            feature=feature,
            Feature=feature.replace("_", " ").title().replace(" ", ""),
        )
    else:
        name = sys.argv[2]
        output_path = Path(f"tests/{test_type}/test_{name}.py")
        content = TEMPLATES[test_type].format(
            workflow_description=f"{name} workflow",
            workflow=name,
            Workflow=name.replace("_", " ").title().replace(" ", ""),
            critical_path_description=f"{name} critical path",
            critical_path=name,
        )

    if output_path.exists():
        print(f"ERROR: File already exists: {output_path}")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    print(f"Created test file: {output_path}")
    print()
    print("Next steps:")
    print(f"  1. Edit {output_path} to implement tests")
    print(f"  2. Run: ./scripts/validate-test-organization.py")
    print(f"  3. Run: pytest {output_path} -v")


if __name__ == "__main__":
    main()

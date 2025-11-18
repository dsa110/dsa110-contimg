#!/opt/miniforge/envs/casa6/bin/python
"""Script to enforce casa6 Python in all pipeline scripts.

This script:
1. Fixes all shebang lines to point to casa6 Python
2. Adds Python version guards to critical entry points
3. Validates that all scripts use casa6 Python
"""

import re
from pathlib import Path

# Casa6 Python path
CASA6_PYTHON = "/opt/miniforge/envs/casa6/bin/python"
REQUIRED_VERSION = "3.11.13"

# Patterns to match
SHEBANG_PATTERNS = [
    r"^#!/usr/bin/python3?$",
    r"^#!/usr/bin/env python3?$",
    r"^#!/bin/env python3?$",
]

# Files to update (entry points)
ENTRY_POINTS = [
    "create_10min_mosaic.py",
    # Add other entry points here
]

# Directories to scan
SCAN_DIRS = [
    "dsa110_contimg",
    "scripts",
]


def fix_shebang(file_path: Path) -> bool:
    """Fix shebang line in a Python file.

    Returns:
        True if file was modified, False otherwise.
    """
    try:
        content = file_path.read_text()
        lines = content.splitlines()

        if not lines or not lines[0].startswith("#!"):
            return False

        # Check if already correct
        if CASA6_PYTHON in lines[0]:
            return False

        # Fix shebang
        for pattern in SHEBANG_PATTERNS:
            if re.match(pattern, lines[0]):
                lines[0] = f"#!{CASA6_PYTHON}"
                file_path.write_text("\n".join(lines) + "\n")
                print(f"✅ Fixed: {file_path}")
                return True

        return False
    except Exception as e:
        print(f"⚠️  Error fixing {file_path}: {e}")
        return False


def add_version_guard(file_path: Path) -> bool:
    """Add Python version guard to entry point.

    Returns:
        True if guard was added, False otherwise.
    """
    try:
        content = file_path.read_text()

        # Check if guard already exists
        if "python_version_guard" in content or "enforce_casa6_python" in content:
            return False

        # Find insertion point (after shebang and docstring)
        lines = content.splitlines()
        insert_idx = 0

        # Skip shebang
        if lines and lines[0].startswith("#!"):
            insert_idx = 1

        # Skip docstring
        if insert_idx < len(lines) and lines[insert_idx].startswith('"""'):
            # Find end of docstring
            for i in range(insert_idx + 1, len(lines)):
                if '"""' in lines[i]:
                    insert_idx = i + 1
                    break

        # Insert guard
        guard_code = [
            "",
            "# Enforce casa6 Python version - MUST be first import",
            "import sys",
            "from pathlib import Path",
            "sys.path.insert(0, str(Path(__file__).parent))",
            "from dsa110_contimg.utils.python_version_guard import enforce_casa6_python",
            "enforce_casa6_python()",
            "",
        ]

        new_lines = lines[:insert_idx] + guard_code + lines[insert_idx:]
        file_path.write_text("\n".join(new_lines))
        print(f"✅ Added guard to: {file_path}")
        return True
    except Exception as e:
        print(f"⚠️  Error adding guard to {file_path}: {e}")
        return False


def main():
    """Main function."""
    src_dir = Path(__file__).parent.parent

    print("=" * 60)
    print("Enforcing Casa6 Python in Pipeline Scripts")
    print("=" * 60)
    print()

    fixed_count = 0
    guard_count = 0

    # Fix entry points
    print("Fixing entry points...")
    for entry_point in ENTRY_POINTS:
        file_path = src_dir / entry_point
        if file_path.exists():
            if fix_shebang(file_path):
                fixed_count += 1
            if add_version_guard(file_path):
                guard_count += 1

    # Scan directories for Python files
    print("\nScanning directories for Python files...")
    for scan_dir in SCAN_DIRS:
        dir_path = src_dir / scan_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Skip tests and cache
            if "test" in str(py_file) or "__pycache__" in str(py_file):
                continue

            # Only fix scripts (executable files with shebang)
            if py_file.is_file() and py_file.read_bytes()[:2] == b"#!":
                if fix_shebang(py_file):
                    fixed_count += 1

    print()
    print("=" * 60)
    print(f"Summary: Fixed {fixed_count} shebangs, added {guard_count} guards")
    print("=" * 60)


if __name__ == "__main__":
    main()

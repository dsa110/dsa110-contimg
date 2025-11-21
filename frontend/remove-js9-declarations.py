#!/usr/bin/env python3
"""Remove conflicting window.JS9 declarations from source files"""
import os
import re
from pathlib import Path

# Pattern to match the declare global block
pattern = re.compile(
    r"^declare global \{\s*\n\s*interface Window \{\s*\n\s*JS9:.*?\n\s*\}\s*\n\}\s*\n", re.MULTILINE
)


def process_file(filepath):
    """Remove declare global blocks from a file"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if file has the pattern
    if "declare global" in content and "JS9:" in content:
        # Remove the pattern
        new_content = pattern.sub("", content)

        # Only write if changed
        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Fixed: {filepath}")
            return True
    return False


def main():
    """Process all TypeScript files"""
    src_dir = Path("src")
    count = 0

    for ext in ["*.ts", "*.tsx"]:
        for filepath in src_dir.rglob(ext):
            if process_file(filepath):
                count += 1

    print(f"\nProcessed {count} files")


if __name__ == "__main__":
    main()

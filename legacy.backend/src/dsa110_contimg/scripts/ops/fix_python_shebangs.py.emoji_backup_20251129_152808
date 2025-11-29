#!/opt/miniforge/envs/casa6/bin/python
"""Script to fix generic python3 shebangs to use CASA6 Python explicitly."""

import sys
from pathlib import Path

CASA6_PYTHON = "#!/opt/miniforge/envs/casa6/bin/python"
GENERIC_SHEBANGS = [
    "#!/usr/bin/env python3",
    "#!/usr/bin/python3",
    "#!/usr/bin/env python",
    "#!/usr/bin/python",
]

project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
scripts_dir = project_root / "scripts"

files_to_fix = []

# Find all Python files with generic shebangs
for directory in [src_dir, scripts_dir]:
    if directory.exists():
        for py_file in directory.rglob("*.py"):
            try:
                with open(py_file, "rb") as f:
                    first_line = f.readline().decode("utf-8", errors="ignore").strip()

                    if first_line in GENERIC_SHEBANGS:
                        files_to_fix.append(py_file)
            except Exception as e:
                print(f"Error reading {py_file}: {e}", file=sys.stderr)

print(f"Found {len(files_to_fix)} files with generic python3 shebangs")
print()

if not files_to_fix:
    print("No files need updating!")
    sys.exit(0)

# Show what will be updated
print("Files to update:")
for f in sorted(files_to_fix)[:20]:
    rel_path = f.relative_to(project_root)
    print(f"  {rel_path}")
if len(files_to_fix) > 20:
    print(f"  ... and {len(files_to_fix) - 20} more")
print()

# Update files
updated_count = 0
for py_file in files_to_fix:
    try:
        with open(py_file, "rb") as f:
            lines = f.readlines()

        # Get first line and check if it's a generic shebang
        first_line = lines[0].decode("utf-8", errors="ignore").rstrip("\n\r")

        if first_line in GENERIC_SHEBANGS:
            # Replace with CASA6 Python shebang
            lines[0] = (CASA6_PYTHON + "\n").encode("utf-8")

            # Write back
            with open(py_file, "wb") as f:
                f.writelines(lines)

            updated_count += 1
            rel_path = py_file.relative_to(project_root)
            print(f"✓ Updated: {rel_path}")
    except Exception as e:
        rel_path = py_file.relative_to(project_root)
        print(f"✗ Error updating {rel_path}: {e}", file=sys.stderr)

print()
print(f"Updated {updated_count}/{len(files_to_fix)} files")

#!/usr/bin/env python3
"""
Script to add ensure_casa_path() initialization to files that import CASA modules.
This ensures CASAPATH is set before CASA modules are imported.
"""

import sys
import re
from pathlib import Path

def add_casa_init_to_file(filepath: Path) -> bool:
    """Add ensure_casa_path() before first CASA import. Returns True if modified."""
    try:
        content = filepath.read_text()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return False
    
    # Skip if already has ensure_casa_path
    if 'ensure_casa_path' in content:
        return False
    
    # Find first CASA import
    casa_import_patterns = [
        r'from casacore',
        r'from casatools',
        r'from casatasks',
        r'import.*casaimage',
        r'import.*casatasks',
        r'import.*casatools',
    ]
    
    lines = content.split('\n')
    first_casa_line = None
    
    for i, line in enumerate(lines):
        for pattern in casa_import_patterns:
            if re.search(pattern, line):
                first_casa_line = i
                break
        if first_casa_line is not None:
            break
    
    if first_casa_line is None:
        # No CASA imports found (shouldn't happen if file is in list)
        return False
    
    # Find insertion point: before the try block or before the import
    insert_line = first_casa_line
    
    # If there's a try block before, insert before try
    for i in range(max(0, first_casa_line - 5), first_casa_line):
        if 'try:' in lines[i] and 'except' not in lines[i]:
            insert_line = i
            break
    
    # Prepare insertion
    indent = ''
    if insert_line > 0:
        # Match indentation of next non-empty line
        for i in range(insert_line, min(insert_line + 5, len(lines))):
            if lines[i].strip():
                indent = re.match(r'^(\s*)', lines[i]).group(1)
                break
    
    # Insert ensure_casa_path
    init_lines = [
        f"{indent}# Ensure CASAPATH is set before importing CASA modules",
        f"{indent}from dsa110_contimg.utils.casa_init import ensure_casa_path",
        f"{indent}ensure_casa_path()",
        ""
    ]
    
    # Insert before insert_line
    new_lines = lines[:insert_line] + init_lines + lines[insert_line:]
    new_content = '\n'.join(new_lines)
    
    # Write back
    filepath.write_text(new_content)
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: add_casa_init.py <file1> [file2] ...", file=sys.stderr)
        sys.exit(1)
    
    modified = 0
    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)
        if add_casa_init_to_file(filepath):
            print(f"Modified: {filepath}")
            modified += 1
        else:
            print(f"Skipped: {filepath} (already has init or no CASA imports)")
    
    print(f"\nModified {modified} files")

